import pytest

from app.services.diff_service import (
    generate_resume_diff,
    generate_word_level_diff,
    generate_side_by_side_diff,
    get_diff_statistics,
    analyze_section_changes,
)


@pytest.fixture
def simple_pair():
    return "Hello world", "Hello brave world"


def test_generate_resume_diff_addition(simple_pair):
    orig, cust = simple_pair
    html = generate_resume_diff(orig, cust)
    expected = (
        "Hello <span class=\"addition\" title=\"Added content\">brave </span>world"
    )
    assert html == expected


def test_generate_word_level_diff_same_as_char(simple_pair):
    orig, cust = simple_pair
    html = generate_word_level_diff(orig, cust)
    assert "<span class=\"addition\"" in html
    assert "brave" in html


def test_side_by_side_diff_line_stats():
    orig = "A\nB\nC\n"
    cust = "A\nC\nD\n"
    result = generate_side_by_side_diff(orig, cust)
    assert result["statistics"] == {
        "additions": 1,
        "deletions": 1,
        "modifications": 0,
        "unchanged": 2,
    }
    diff_types = [item["type"] for item in result["diff_data"]]
    assert diff_types == ["unchanged", "deleted", "unchanged", "added"]


def test_get_diff_statistics_counts():
    orig = "A\nB\nC\n"
    cust = "A\nC\nD\n"
    stats = get_diff_statistics(orig, cust)
    assert stats == {
        "additions": 2,
        "deletions": 2,
        "modifications": 0,
        "unchanged": 4,
    }


def test_analyze_section_changes_returns_sections():
    orig = "# Sec1\nA\nB\n\n# Sec2\nC\n"
    cust = "# Sec1\nA\nB new\n\n# Sec2\nC\nD\n# Sec3\nE\n"
    analysis = analyze_section_changes(orig, cust)
    assert set(analysis) == {"Sec1", "Sec2", "Sec3"}
    assert analysis["Sec3"]["status"] == "added"
    assert analysis["Sec3"]["additions"] == 1
    assert analysis["Sec3"]["deletions"] == 0
    assert "<span class=\"addition\"" in analysis["Sec1"]["section_diff"]
