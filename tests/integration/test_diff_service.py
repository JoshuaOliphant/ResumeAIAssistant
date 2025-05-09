"""
Tests for the resume diff service.
"""
import os
import tempfile
import json
import pytest
from app.services.diff_service import (
    generate_resume_diff, 
    generate_markdown_diff,
    generate_word_level_diff,
    get_diff_statistics,
    generate_side_by_side_diff,
    analyze_section_changes,
    extract_keywords,
    analyze_keyword_changes,
    generate_diff_html_document,
    create_diff_json,
    export_diff_to_files
)

@pytest.fixture
def resume_samples():
    """Fixture providing sample resume data for testing."""
    original_resume = """# John Doe
## Python Developer

### Summary
Python developer with 3 years of experience in web development and data analysis.

### Skills
- Python
- Django
- Flask
- SQL
- Git

### Experience
**Software Developer, ABC Tech**
*2020 - Present*
- Developed web applications using Django
- Implemented RESTful APIs
- Worked with PostgreSQL databases

### Education
**Bachelor of Science in Computer Science**
*University of Technology, 2019*
"""

    customized_resume = """# John Doe
## Senior Python Developer

### Summary
Experienced Python developer with 5 years of expertise in web development, data analysis, and machine learning.

### Skills
- Python
- Django
- Flask
- FastAPI
- SQL
- Git
- Docker
- Machine Learning

### Experience
**Senior Software Developer, ABC Tech**
*2020 - Present*
- Developed and maintained scalable web applications using Django and FastAPI
- Designed and implemented RESTful APIs with comprehensive documentation
- Optimized PostgreSQL databases for performance
- Mentored junior developers and conducted code reviews

### Education
**Bachelor of Science in Computer Science**
*University of Technology, 2019*
"""
    return {"original": original_resume, "customized": customized_resume}


def test_generate_resume_diff_no_changes():
    """Test diff generation with identical texts."""
    original = "This is a test resume."
    customized = "This is a test resume."
    
    diff = generate_resume_diff(original, customized)
    
    # No styling should be added for identical texts
    assert diff == "This is a test resume."


def test_generate_resume_diff_with_addition():
    """Test diff generation with added content."""
    original = "Python developer."
    customized = "Experienced Python developer."
    
    diff = generate_resume_diff(original, customized)
    
    # Should highlight the added word
    assert '<span class="addition"' in diff
    assert 'Experienced ' in diff
    assert 'Python developer.' in diff


def test_generate_resume_diff_with_deletion():
    """Test diff generation with deleted content."""
    original = "Senior Python developer with 5 years experience."
    customized = "Python developer with 5 years experience."
    
    diff = generate_resume_diff(original, customized)
    
    # Should show deleted word with strikethrough
    assert '<span class="deletion"' in diff
    assert '<del>Senior </del>' in diff
    assert 'Python developer with 5 years experience.' in diff


def test_generate_resume_diff_with_replacement():
    """Test diff generation with replaced content."""
    original = "Python developer with 3 years experience."
    customized = "Python developer with 5 years experience."
    
    diff = generate_resume_diff(original, customized)
    
    # Should show deleted and added content
    assert '<span class="deletion"' in diff
    assert '<del>3</del>' in diff
    assert '<span class="addition"' in diff
    assert '5' in diff


def test_generate_markdown_diff():
    """Test markdown diff generation."""
    original = "Python developer with 3 years experience."
    customized = "Python developer with 5 years experience."
    
    diff = generate_markdown_diff(original, customized)
    
    # Should use markdown syntax for diff
    assert '**~~3~~**' in diff
    assert '**++5++**' in diff


def test_word_level_diff():
    """Test word-level diff generation."""
    original = "Python developer with experience in Django."
    customized = "Python developer with extensive experience in Django and Flask."
    
    diff = generate_word_level_diff(original, customized)
    
    # Should highlight the word-level changes
    assert 'with ' in diff
    assert '<span class="addition"' in diff
    assert 'extensive ' in diff
    # The exact output format might vary depending on the diff algorithm
    # Just check for key parts
    assert 'experience in' in diff
    assert 'Django' in diff
    assert 'Flask' in diff


def test_diff_statistics():
    """Test diff statistics calculation."""
    original = "Python developer with experience in Django."
    customized = "Python developer with extensive experience in Django and Flask."
    
    stats = get_diff_statistics(original, customized)
    
    # Should count additions correctly
    assert stats["additions"] > 0
    assert stats["deletions"] == 0
    assert stats["unchanged"] > 0


def test_side_by_side_diff():
    """Test side-by-side diff generation."""
    original = "First line\nSecond line\nThird line"
    customized = "First line\nModified second line\nThird line\nFourth line"
    
    result = generate_side_by_side_diff(original, customized)
    
    # Should have the expected structure
    assert "diff_data" in result
    assert "statistics" in result
    
    # Check diff data structure
    diff_data = result["diff_data"]
    assert isinstance(diff_data, list)
    assert len(diff_data) == 4  # 4 lines total
    
    # Check specific line types
    assert diff_data[0]["type"] == "unchanged"
    assert diff_data[1]["type"] == "modified"
    assert diff_data[2]["type"] == "unchanged"
    assert diff_data[3]["type"] == "added"
    
    # Check line content
    assert diff_data[0]["original"] == "First line"
    assert diff_data[0]["customized"] == "First line"
    assert diff_data[1]["original"] == "Second line"
    assert diff_data[1]["customized"] == "Modified second line"


def test_analyze_section_changes(resume_samples):
    """Test section analysis."""
    result = analyze_section_changes(resume_samples["original"], resume_samples["customized"])
    
    # Should have all expected sections
    assert "Python Developer" in result
    assert "Senior Python Developer" in result
    assert "Summary" in result
    assert "Skills" in result
    assert "Experience" in result
    assert "Education" in result
    
    # Check section statistics and analysis
    summary_section = result["Summary"]
    assert "status" in summary_section
    assert "change_percentage" in summary_section
    assert "additions" in summary_section
    assert "deletions" in summary_section
    assert "changes" in summary_section
    assert "rationale" in summary_section
    assert "impact" in summary_section
    
    # Check that content was recognized as changed
    assert summary_section["status"] != "unchanged"
    assert summary_section["change_percentage"] > 0
    
    # Education section should be unchanged or minor changes
    education_section = result["Education"]
    assert education_section["status"] in ["unchanged", "minor_changes"]


def test_extract_keywords(resume_samples):
    """Test keyword extraction."""
    keywords = extract_keywords(resume_samples["original"])
    
    # Should extract relevant keywords
    common_keywords = ["python", "developer", "experience", "django"]
    for keyword in common_keywords:
        assert keyword in keywords


def test_analyze_keyword_changes(resume_samples):
    """Test keyword change analysis."""
    result = analyze_keyword_changes(resume_samples["original"], resume_samples["customized"])
    
    # Should have the expected structure
    assert "added_keywords" in result
    assert "removed_keywords" in result
    assert "common_keywords" in result
    
    # Check for expected keywords
    added_keywords = result["added_keywords"]
    common_keywords = result["common_keywords"]
    
    # Should find new keywords like "docker", "machine", "learning", "senior"
    new_keywords = ["docker", "machine", "learning", "senior"]
    for keyword in new_keywords:
        # Check if keyword is in added_keywords or is part of an added keyword
        assert (keyword in added_keywords or 
                any(keyword in kw for kw in added_keywords))
    
    # Should keep common keywords like "python", "developer", "django"
    expected_common = ["python", "developer", "django"]
    for keyword in expected_common:
        # Check if keyword is in common_keywords or is part of a common keyword
        assert (keyword in common_keywords or 
                any(keyword in kw for kw in common_keywords))


def test_generate_diff_html_document(resume_samples):
    """Test HTML document generation."""
    html = generate_diff_html_document(
        resume_samples["original"], 
        resume_samples["customized"],
        "Test Resume Comparison"
    )
    
    # Should be a valid HTML document
    assert html.startswith("<!DOCTYPE html>")
    assert "<html" in html
    assert "<head>" in html
    assert "<body>" in html
    assert "</html>" in html
    
    # Should contain the title
    assert "<title>Test Resume Comparison</title>" in html
    
    # Should include all diff components
    assert "Change Summary" in html
    assert "Keyword Analysis" in html
    assert "Section-by-Section Analysis" in html
    assert "Full Resume Comparison" in html
    
    # Should have tabs for different views
    assert "Inline Changes" in html
    assert "Side by Side" in html
    assert "Original" in html
    assert "Customized" in html


def test_create_diff_json(resume_samples):
    """Test JSON data creation."""
    result = create_diff_json(resume_samples["original"], resume_samples["customized"])
    
    # Should have all required fields
    expected_fields = [
        "original_text", "customized_text", "diff_html",
        "side_by_side_diff", "statistics", "section_analysis",
        "keyword_analysis"
    ]
    for field in expected_fields:
        assert field in result
    
    # Should have valid content
    assert result["original_text"] == resume_samples["original"]
    assert result["customized_text"] == resume_samples["customized"]
    assert len(result["diff_html"]) > 0
    assert isinstance(result["side_by_side_diff"], list)
    assert isinstance(result["statistics"], dict)
    assert isinstance(result["section_analysis"], dict)
    assert isinstance(result["keyword_analysis"], dict)


def test_export_diff_to_files(resume_samples):
    """Test exporting diff to files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result = export_diff_to_files(
            resume_samples["original"],
            resume_samples["customized"],
            temp_dir
        )
        
        # Should return file paths
        assert "html_file" in result
        assert "json_file" in result
        assert "stats_file" in result
        
        # Files should exist
        assert os.path.exists(result["html_file"])
        assert os.path.exists(result["json_file"])
        assert os.path.exists(result["stats_file"])
        
        # Check content
        with open(result["json_file"], "r") as f:
            json_data = json.load(f)
            assert "original_text" in json_data
            assert "customized_text" in json_data
        
        with open(result["stats_file"], "r") as f:
            stats_data = json.load(f)
            assert "additions" in stats_data
            assert "deletions" in stats_data
            assert "modifications" in stats_data
            assert "unchanged" in stats_data
