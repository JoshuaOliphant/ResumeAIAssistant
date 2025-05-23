"""
Resume diff service for generating visual diffs between original and customized resumes.
Enhanced with improved visualization and analysis features.
"""
from difflib import SequenceMatcher
import html
import json
import re
from typing import Dict, List, Tuple, Union, Optional

import logfire


class DiffGenerator:
    """Utility class for generating visual diffs between resume versions."""

    def line_diff(self, original_text: str, customized_text: str) -> str:
        """Return an inline HTML diff for the two texts."""
        try:
            return generate_resume_diff(original_text, customized_text)
        except Exception as exc:  # pragma: no cover - unexpected
            logfire.error("Line diff generation failed", error=str(exc), exc_info=True)
            raise

    def section_diff(self, original_text: str, customized_text: str) -> Dict[str, Dict[str, Union[str, float, Dict, int]]]:
        """Analyze section level changes between the two texts."""
        try:
            return analyze_section_changes(original_text, customized_text)
        except Exception as exc:  # pragma: no cover - unexpected
            logfire.error("Section diff analysis failed", error=str(exc), exc_info=True)
            return {}

    def html_diff_view(self, original_text: str, customized_text: str) -> str:
        """Generate a full HTML diff document with highlights."""
        try:
            return generate_diff_html_document(original_text, customized_text)
        except Exception as exc:  # pragma: no cover - unexpected
            logfire.error("HTML diff generation failed", error=str(exc), exc_info=True)
            raise

def generate_resume_diff(original_text: str, customized_text: str) -> str:
    """
    Generate a diff between original and customized resume texts.
    Returns HTML with appropriate styling for changes.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        
    Returns:
        HTML string with styled differences
    """
    # Use SequenceMatcher to find differences
    matcher = SequenceMatcher(None, original_text, customized_text)
    
    # Generate HTML with styled differences
    diff_html = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            diff_html.append(html.escape(original_text[i1:i2]))
        elif op == 'insert':
            diff_html.append(f'<span class="addition" title="Added content">{html.escape(customized_text[j1:j2])}</span>')
        elif op == 'delete':
            diff_html.append(f'<span class="deletion" title="Removed content"><del>{html.escape(original_text[i1:i2])}</del></span>')
        elif op == 'replace':
            diff_html.append(f'<span class="deletion" title="Original content"><del>{html.escape(original_text[i1:i2])}</del></span>')
            diff_html.append(f'<span class="addition" title="Modified content">{html.escape(customized_text[j1:j2])}</span>')
    
    return ''.join(diff_html)

def generate_markdown_diff(original_text: str, customized_text: str) -> str:
    """
    Generate a diff between original and customized resume texts in Markdown format.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        
    Returns:
        Markdown string with styled differences
    """
    # Use SequenceMatcher to find differences
    matcher = SequenceMatcher(None, original_text, customized_text)
    
    # Generate Markdown with styled differences
    diff_md = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            diff_md.append(original_text[i1:i2])
        elif op == 'insert':
            diff_md.append(f'**++{customized_text[j1:j2]}++**')
        elif op == 'delete':
            diff_md.append(f'**~~{original_text[i1:i2]}~~**')
        elif op == 'replace':
            diff_md.append(f'**~~{original_text[i1:i2]}~~**')
            diff_md.append(f'**++{customized_text[j1:j2]}++**')
    
    return ''.join(diff_md)

def generate_word_level_diff(original_text: str, customized_text: str) -> str:
    """
    Generate a more granular word-level diff between original and customized resume texts.
    This provides a more readable diff for resume content.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        
    Returns:
        HTML string with styled differences at word level
    """
    # Split text into lines
    original_lines = original_text.splitlines(True)  # Keep line endings
    customized_lines = customized_text.splitlines(True)
    
    # Compare line by line
    diff_html = []
    matcher = SequenceMatcher(None, original_lines, customized_lines)
    
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            for line in original_lines[i1:i2]:
                diff_html.append(html.escape(line))
        elif op == 'insert':
            for line in customized_lines[j1:j2]:
                diff_html.append(f'<span class="addition" title="Added content">{html.escape(line)}</span>')
        elif op == 'delete':
            for line in original_lines[i1:i2]:
                diff_html.append(f'<span class="deletion" title="Removed content"><del>{html.escape(line)}</del></span>')
        elif op == 'replace':
            # For replaced blocks, try to do word-level diff
            orig_block = ''.join(original_lines[i1:i2])
            cust_block = ''.join(customized_lines[j1:j2])
            
            # Split into words, preserving whitespace
            orig_words = re.findall(r'\S+|\s+', orig_block)
            cust_words = re.findall(r'\S+|\s+', cust_block)
            
            # Compare words
            word_matcher = SequenceMatcher(None, orig_words, cust_words)
            for word_op, wi1, wi2, wj1, wj2 in word_matcher.get_opcodes():
                if word_op == 'equal':
                    diff_html.append(html.escape(''.join(orig_words[wi1:wi2])))
                elif word_op == 'insert':
                    diff_html.append(f'<span class="addition" title="Added content">{html.escape("".join(cust_words[wj1:wj2]))}</span>')
                elif word_op == 'delete':
                    diff_html.append(f'<span class="deletion" title="Removed content"><del>{html.escape("".join(orig_words[wi1:wi2]))}</del></span>')
                elif word_op == 'replace':
                    diff_html.append(f'<span class="deletion" title="Original content"><del>{html.escape("".join(orig_words[wi1:wi2]))}</del></span>')
                    diff_html.append(f'<span class="addition" title="Modified content">{html.escape("".join(cust_words[wj1:wj2]))}</span>')
    
    return ''.join(diff_html)

def generate_side_by_side_diff(original_text: str, customized_text: str) -> Dict[str, Union[List[Dict[str, str]], Dict[str, int]]]:
    """
    Generate a side-by-side line-by-line diff between original and customized texts.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        
    Returns:
        Dictionary with line-by-line diff data and statistics
    """
    original_lines = original_text.splitlines()
    customized_lines = customized_text.splitlines()
    
    # Use SequenceMatcher for line-by-line comparison
    matcher = SequenceMatcher(None, original_lines, customized_lines)
    
    side_by_side = []
    line_count = 1
    
    stats = {
        "additions": 0,
        "deletions": 0,
        "modifications": 0,
        "unchanged": 0
    }
    
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            # Add unchanged lines with same line number on both sides
            for i, j in zip(range(i1, i2), range(j1, j2)):
                side_by_side.append({
                    "line_number": line_count,
                    "type": "unchanged",
                    "original": original_lines[i],
                    "customized": customized_lines[j]
                })
                line_count += 1
                stats["unchanged"] += 1
        
        elif op == 'replace':
            # Lines were changed, show them side by side
            max_lines = max(i2 - i1, j2 - j1)
            for k in range(max_lines):
                orig_idx = i1 + k if k < (i2 - i1) else None
                cust_idx = j1 + k if k < (j2 - j1) else None
                
                side_by_side.append({
                    "line_number": line_count,
                    "type": "modified",
                    "original": original_lines[orig_idx] if orig_idx is not None else "",
                    "customized": customized_lines[cust_idx] if cust_idx is not None else ""
                })
                line_count += 1
                stats["modifications"] += 1
        
        elif op == 'delete':
            # Lines were deleted from original
            for i in range(i1, i2):
                side_by_side.append({
                    "line_number": line_count,
                    "type": "deleted",
                    "original": original_lines[i],
                    "customized": ""
                })
                line_count += 1
                stats["deletions"] += 1
        
        elif op == 'insert':
            # Lines were added in customized
            for j in range(j1, j2):
                side_by_side.append({
                    "line_number": line_count,
                    "type": "added",
                    "original": "",
                    "customized": customized_lines[j]
                })
                line_count += 1
                stats["additions"] += 1
    
    return {
        "diff_data": side_by_side,
        "statistics": stats
    }

def get_diff_statistics(original_text: str, customized_text: str) -> Dict[str, int]:
    """
    Calculate statistics about the changes made between original and customized texts.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        
    Returns:
        Dictionary with statistics about additions, deletions, and modifications
    """
    matcher = SequenceMatcher(None, original_text, customized_text)
    
    stats = {
        "additions": 0,
        "deletions": 0,
        "modifications": 0,
        "unchanged": 0
    }
    
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            stats["unchanged"] += i2 - i1
        elif op == 'insert':
            stats["additions"] += j2 - j1
        elif op == 'delete':
            stats["deletions"] += i2 - i1
        elif op == 'replace':
            stats["modifications"] += max(i2 - i1, j2 - j1)
    
    return stats

def analyze_section_changes(original_text: str, customized_text: str) -> Dict[str, Dict[str, Union[str, float, Dict, int]]]:
    """
    Analyze which sections of the resume were modified and to what extent.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        
    Returns:
        Dictionary with section names as keys and change statistics as values
    """
    # Extract sections from both texts
    original_sections = extract_resume_sections(original_text)
    customized_sections = extract_resume_sections(customized_text)
    
    # Compare sections
    section_analysis = {}
    all_section_names = set(original_sections.keys()) | set(customized_sections.keys())
    
    for section_name in all_section_names:
        orig_content = original_sections.get(section_name, "")
        cust_content = customized_sections.get(section_name, "")
        
        if not orig_content and cust_content:
            # New section added
            section_analysis[section_name] = {
                "status": "added",
                "change_percentage": 100.0,
                "content_length": len(cust_content),
                "changes": 0,
                "additions": len(cust_content),
                "deletions": 0,
                "rationale": "Added new section to highlight additional qualifications or information",
                "impact": "high"
            }
        elif orig_content and not cust_content:
            # Section removed
            section_analysis[section_name] = {
                "status": "removed",
                "change_percentage": 100.0,
                "content_length": len(orig_content),
                "changes": 0,
                "additions": 0,
                "deletions": len(orig_content),
                "rationale": "Removed section that wasn't relevant to this job application",
                "impact": "medium"
            }
        else:
            # Section exists in both - calculate differences
            stats = get_diff_statistics(orig_content, cust_content)
            total_chars = stats["unchanged"] + stats["additions"] + stats["deletions"] + stats["modifications"]
            change_percentage = 0
            if total_chars > 0:
                change_percentage = ((stats["additions"] + stats["deletions"] + stats["modifications"]) / total_chars) * 100
            
            status = "unchanged"
            impact = "low"
            rationale = "No significant changes were needed for this section"
            
            if change_percentage > 75:
                status = "major_changes"
                impact = "high"
                rationale = "Significant customization to better align with job requirements"
            elif change_percentage > 25:
                status = "moderate_changes"
                impact = "medium"
                rationale = "Enhanced section with targeted improvements for better job alignment"
            elif change_percentage > 0:
                status = "minor_changes"
                impact = "low"
                rationale = "Made minor adjustments to improve clarity or keyword matching"
            
            # Get section-specific diff
            section_diff = ""
            if orig_content and cust_content:
                section_diff = generate_word_level_diff(orig_content, cust_content)
            
            section_analysis[section_name] = {
                "status": status,
                "change_percentage": round(change_percentage, 1),
                "stats": stats,
                "content_length": len(cust_content),
                "changes": stats["modifications"],
                "additions": stats["additions"],
                "deletions": stats["deletions"],
                "section_diff": section_diff,
                "rationale": rationale,
                "impact": impact
            }
    
    return section_analysis

def extract_resume_sections(text: str) -> Dict[str, str]:
    """
    Extract sections from a markdown resume.
    
    Args:
        text: The resume text in markdown format
        
    Returns:
        Dictionary with section names as keys and section content as values
    """
    # Pattern to match markdown headings (# Heading, ## Heading, etc.)
    heading_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
    
    # Find all headings with their positions
    headings = [(match.group(2).strip(), match.start(), len(match.group(1))) 
                for match in heading_pattern.finditer(text)]
    
    if not headings:
        return {"Full Resume": text}
    
    # Sort headings by their position in the text
    headings.sort(key=lambda x: x[1])
    
    # Extract sections based on heading positions
    sections = {}
    for i, (heading, start, level) in enumerate(headings):
        # For each heading, the section content goes until the next heading or the end of the text
        if i < len(headings) - 1:
            next_start = headings[i + 1][1]
            section_content = text[start:next_start].strip()
        else:
            section_content = text[start:].strip()
        
        # Remove the heading itself from the content
        heading_line_end = section_content.find('\n')
        if heading_line_end != -1:
            section_content = section_content[heading_line_end:].strip()
        else:
            section_content = ""
        
        # Use heading as section name, prefixed with level for sorting
        section_key = heading
        sections[section_key] = section_content
    
    return sections

def extract_keywords(text: str) -> List[str]:
    """
    Extract important keywords from text.
    
    Args:
        text: The text to extract keywords from
        
    Returns:
        List of keywords
    """
    # Simple implementation - split by whitespace and filter common words
    common_words = {
        "and", "the", "a", "an", "in", "on", "at", "to", "for", "with", "by",
        "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "of", "from", "as", "i", "you", "he", "she", "it",
        "we", "they", "this", "that", "these", "those", "my", "your", "his", "her",
        "its", "our", "their", "what", "which", "who", "whom", "whose"
    }
    
    words = re.findall(r'\b\w+\b', text.lower())
    keywords = [word for word in words if word not in common_words and len(word) > 3]
    
    # Get unique keywords
    unique_keywords = []
    for keyword in keywords:
        if keyword not in unique_keywords:
            unique_keywords.append(keyword)
    
    # Sort by frequency (could be enhanced with better algorithms like TF-IDF)
    keyword_freq = {k: keywords.count(k) for k in unique_keywords}
    sorted_keywords = sorted(unique_keywords, key=lambda k: keyword_freq[k], reverse=True)
    
    return sorted_keywords[:20]  # Return top 20 keywords

def analyze_keyword_changes(original_text: str, customized_text: str) -> Dict[str, List[str]]:
    """
    Analyze keyword changes between original and customized texts.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        
    Returns:
        Dictionary with lists of added, removed, and common keywords
    """
    original_keywords = set(extract_keywords(original_text))
    customized_keywords = set(extract_keywords(customized_text))
    
    return {
        "added_keywords": list(customized_keywords - original_keywords),
        "removed_keywords": list(original_keywords - customized_keywords),
        "common_keywords": list(original_keywords & customized_keywords)
    }

def generate_diff_html_document(original_text: str, customized_text: str, 
                                title: str = "Resume Diff Comparison", 
                                description: str = "Comparison between original and customized resume") -> str:
    """
    Generate a complete HTML document with diff comparison.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        title: The title of the HTML document
        description: A description of the comparison
        
    Returns:
        Complete HTML document as a string
    """
    # Generate various diff formats
    inline_diff = generate_word_level_diff(original_text, customized_text)
    stats = get_diff_statistics(original_text, customized_text)
    section_analysis = analyze_section_changes(original_text, customized_text)
    keyword_analysis = analyze_keyword_changes(original_text, customized_text)
    
    # Generate the side-by-side diff data
    side_by_side = generate_side_by_side_diff(original_text, customized_text)
    
    # Create HTML template as a raw string (note the 'r' prefix)
    html_template_str = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --addition-bg: #e6ffed;
            --addition-text: #22863a;
            --deletion-bg: #ffeef0;
            --deletion-text: #cb2431;
            --unchanged-bg: #f6f8fa;
            --border-color: #e1e4e8;
            --header-bg: #f1f8ff;
            --line-number-color: #6a737d;
            --section-header-bg: #f6f8fa;
            --dark-mode-bg: #0d1117;
            --dark-mode-text: #c9d1d9;
            --dark-mode-addition-bg: #0d4a26;
            --dark-mode-addition-text: #7ee787;
            --dark-mode-deletion-bg: #5d0f12;
            --dark-mode-deletion-text: #ffa198;
            --dark-mode-unchanged-bg: #161b22;
            --dark-mode-border-color: #30363d;
            --dark-mode-header-bg: #0d1117;
            --dark-mode-line-number-color: #8b949e;
            --dark-mode-section-header-bg: #161b22;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.5;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #24292e;
            background-color: #fff;
        }}
        
        @media (prefers-color-scheme: dark) {{
            body {{
                background-color: var(--dark-mode-bg);
                color: var(--dark-mode-text);
            }}
            .addition {{
                background-color: var(--dark-mode-addition-bg);
                color: var(--dark-mode-addition-text);
            }}
            .deletion {{
                background-color: var(--dark-mode-deletion-bg);
                color: var(--dark-mode-deletion-text);
            }}
            .section-header {{
                background-color: var(--dark-mode-section-header-bg);
                border-color: var(--dark-mode-border-color);
            }}
            .stats-card, .keyword-card, .diff-card, .side-by-side-diff {{
                background-color: var(--dark-mode-unchanged-bg);
                border-color: var(--dark-mode-border-color);
            }}
            .unchanged-line {{
                background-color: var(--dark-mode-unchanged-bg);
            }}
            .added-line {{
                background-color: var(--dark-mode-addition-bg);
            }}
            .deleted-line {{
                background-color: var(--dark-mode-deletion-bg);
            }}
            .modified-line {{
                background-color: var(--dark-mode-header-bg);
            }}
            .line-number {{
                color: var(--dark-mode-line-number-color);
                border-color: var(--dark-mode-border-color);
            }}
            .tabs button {{
                color: var(--dark-mode-text);
                border-color: var(--dark-mode-border-color);
            }}
            .tabs button.active {{
                background-color: var(--dark-mode-unchanged-bg);
                border-bottom-color: var(--dark-mode-addition-text);
            }}
            .keyword {{
                border-color: var(--dark-mode-border-color);
            }}
            .keyword.added {{
                background-color: var(--dark-mode-addition-bg);
            }}
            .keyword.removed {{
                background-color: var(--dark-mode-deletion-bg);
            }}
            .keyword.common {{
                background-color: var(--dark-mode-unchanged-bg);
            }}
        }}
        
        h1, h2, h3, h4 {{
            margin-top: 24px;
            margin-bottom: 16px;
        }}
        
        .addition {{
            background-color: var(--addition-bg);
            color: var(--addition-text);
            padding: 0 2px;
            border-radius: 2px;
        }}
        
        .deletion {{
            background-color: var(--deletion-bg);
            color: var(--deletion-text);
            padding: 0 2px;
            border-radius: 2px;
        }}
        
        .stats-container {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }}
        
        .stats-card {{
            flex: 1;
            min-width: 200px;
            padding: 15px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background-color: var(--unchanged-bg);
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .stats-card h3 {{
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 16px;
        }}
        
        .stats-number {{
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .additions-text {{
            color: var(--addition-text);
        }}
        
        .deletions-text {{
            color: var(--deletion-text);
        }}
        
        .section-header {{
            background-color: var(--section-header-bg);
            padding: 10px 15px;
            margin-top: 20px;
            margin-bottom: 10px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
        }}
        
        .section-header:hover {{
            background-color: #eef2f6;
        }}
        
        .section-content {{
            display: none;
            padding: 0 15px;
            margin-bottom: 20px;
        }}
        
        .keyword-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }}
        
        .keyword {{
            padding: 5px 10px;
            border-radius: 20px;
            border: 1px solid var(--border-color);
            font-size: 14px;
            white-space: nowrap;
        }}
        
        .keyword.added {{
            background-color: var(--addition-bg);
            color: var(--addition-text);
        }}
        
        .keyword.removed {{
            background-color: var(--deletion-bg);
            color: var(--deletion-text);
            text-decoration: line-through;
        }}
        
        .keyword.common {{
            background-color: var(--unchanged-bg);
        }}
        
        .diff-card {{
            border: 1px solid var(--border-color);
            border-radius: 6px;
            overflow: hidden;
            margin-top: 20px;
            background-color: #fff;
        }}
        
        .tabs {{
            display: flex;
            border-bottom: 1px solid var(--border-color);
            background-color: var(--header-bg);
        }}
        
        .tabs button {{
            padding: 10px 15px;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 14px;
            border-bottom: 2px solid transparent;
            color: #24292e;
        }}
        
        .tabs button.active {{
            border-bottom-color: #0366d6;
            font-weight: 600;
        }}
        
        .tab-content {{
            display: none;
            padding: 15px;
            overflow: auto;
            max-height: 500px;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .side-by-side-diff {{
            border: 1px solid var(--border-color);
            border-radius: 6px;
            overflow: hidden;
            margin-top: 20px;
            font-family: monospace;
            font-size: 14px;
            background-color: #fff;
        }}
        
        .diff-line {{
            display: flex;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .line-number {{
            width: 40px;
            text-align: right;
            padding: 0 8px;
            color: var(--line-number-color);
            border-right: 1px solid var(--border-color);
            user-select: none;
        }}
        
        .line-content {{
            flex: 1;
            padding: 0 8px;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        
        .unchanged-line {{
            background-color: var(--unchanged-bg);
        }}
        
        .added-line {{
            background-color: var(--addition-bg);
        }}
        
        .deleted-line {{
            background-color: var(--deletion-bg);
        }}
        
        .modified-line {{
            background-color: #fafbfc;
        }}
        
        .diff-column {{
            display: flex;
            width: 50%;
        }}
        
        .section-content pre {{
            white-space: pre-wrap;
            word-break: break-word;
            margin: 0;
            padding: 10px;
            background-color: var(--unchanged-bg);
            border-radius: 6px;
            overflow: auto;
            font-family: monospace;
            font-size: 14px;
        }}
        
        @media (max-width: 768px) {{
            .stats-container {{
                flex-direction: column;
            }}
            
            .diff-column {{
                width: 100%;
            }}
            
            .side-by-side-diff {{
                font-size: 12px;
            }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>{description}</p>
    
    <!-- Summary Stats -->
    <h2>Change Summary</h2>
    <div class="stats-container">
        <div class="stats-card">
            <h3>Additions</h3>
            <div class="stats-number additions-text">+{stats[additions]}</div>
            <div>Characters added</div>
        </div>
        <div class="stats-card">
            <h3>Deletions</h3>
            <div class="stats-number deletions-text">-{stats[deletions]}</div>
            <div>Characters removed</div>
        </div>
        <div class="stats-card">
            <h3>Modifications</h3>
            <div class="stats-number">{stats[modifications]}</div>
            <div>Characters modified</div>
        </div>
        <div class="stats-card">
            <h3>Unchanged</h3>
            <div class="stats-number">{stats[unchanged]}</div>
            <div>Characters unchanged</div>
        </div>
    </div>
    
    <!-- Keywords Analysis -->
    <h2>Keyword Analysis</h2>
    <div class="stats-card">
        <h3>Added Keywords</h3>
        <div class="keyword-container">
            {added_keywords}
        </div>
        
        <h3>Removed Keywords</h3>
        <div class="keyword-container">
            {removed_keywords}
        </div>
        
        <h3>Common Keywords</h3>
        <div class="keyword-container">
            {common_keywords}
        </div>
    </div>
    
    <!-- Section Analysis -->
    <h2>Section-by-Section Analysis</h2>
    
    {section_analysis_html}
    
    <!-- Diff Views -->
    <h2>Full Resume Comparison</h2>
    <div class="diff-card">
        <div class="tabs">
            <button class="tab-button active" onclick="showTab('inline-diff')">Inline Changes</button>
            <button class="tab-button" onclick="showTab('side-by-side')">Side by Side</button>
            <button class="tab-button" onclick="showTab('original')">Original</button>
            <button class="tab-button" onclick="showTab('customized')">Customized</button>
        </div>
        
        <div id="inline-diff" class="tab-content active">
            {inline_diff}
        </div>
        
        <div id="side-by-side" class="tab-content">
            <div class="side-by-side-diff">
                <!-- Table header -->
                <div class="diff-line">
                    <div class="diff-column">
                        <div class="line-number">Line</div>
                        <div class="line-content"><strong>Original</strong></div>
                    </div>
                    <div class="diff-column">
                        <div class="line-number">Line</div>
                        <div class="line-content"><strong>Customized</strong></div>
                    </div>
                </div>
                
                <!-- Diff lines -->
                {side_by_side_rows}
            </div>
        </div>
        
        <div id="original" class="tab-content">
            <pre>{original_text_escaped}</pre>
        </div>
        
        <div id="customized" class="tab-content">
            <pre>{customized_text_escaped}</pre>
        </div>
    </div>
    
    <script>
        // Toggle section display
        function toggleSection(sectionName) {{
            const sectionId = 'section-' + sectionName.replace(/ /g, '-');
            const section = document.getElementById(sectionId);
            if (section.style.display === 'block') {{
                section.style.display = 'none';
            }} else {{
                section.style.display = 'block';
            }}
        }}
        
        // Tab switching functionality
        function showTab(tabId) {{
            // Hide all tab contents
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(tab => {{
                tab.classList.remove('active');
            }});
            
            // Show the selected tab
            document.getElementById(tabId).classList.add('active');
            
            // Update tab button states
            const tabButtons = document.querySelectorAll('.tab-button');
            tabButtons.forEach(button => {{
                button.classList.remove('active');
            }});
            
            // Highlight the clicked button
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>"""

    # Prepare data for the template
    added_keywords = ' '.join([f'<span class="keyword added">{k}</span>' for k in keyword_analysis['added_keywords']])
    removed_keywords = ' '.join([f'<span class="keyword removed">{k}</span>' for k in keyword_analysis['removed_keywords']])
    common_keywords = ' '.join([f'<span class="keyword common">{k}</span>' for k in keyword_analysis['common_keywords']])
    
    # Section analysis HTML
    section_analysis_parts = []
    for section, analysis in section_analysis.items():
        escaped_section = section.replace("'", "\\'")
        section_analysis_parts.append(f'''
    <div class="section-header" onclick="toggleSection('{escaped_section}')">
        {section}
        <span class="section-stats">
            +{analysis.get('additions', 0)} -{analysis.get('deletions', 0)} ~{analysis.get('changes', 0)}
        </span>
    </div>
    <div id="section-{section.replace(' ', '-')}" class="section-content">
        <p><strong>Status:</strong> {analysis.get('status', 'unknown').replace('_', ' ')}</p>
        <p><strong>Changes:</strong> {analysis.get('change_percentage', 0)}%</p>
        <p><strong>Rationale:</strong> {analysis.get('rationale', 'No rationale provided')}</p>
        <p><strong>Impact:</strong> {analysis.get('impact', 'unknown')}</p>
        <div class="section-diff">
            <h4>Section Changes</h4>
            <pre>{analysis.get('section_diff', 'No diff available')}</pre>
        </div>
    </div>
    ''')
    section_analysis_html = ''.join(section_analysis_parts)
    
    # Side by side rows
    side_by_side_rows_parts = []
    for row in side_by_side['diff_data']:
        side_by_side_rows_parts.append(f'''
                <div class="diff-line {row['type']}-line">
                    <div class="diff-column">
                        <div class="line-number">{row['line_number']}</div>
                        <div class="line-content">{html.escape(row['original'])}</div>
                    </div>
                    <div class="diff-column">
                        <div class="line-number">{row['line_number']}</div>
                        <div class="line-content">{html.escape(row['customized'])}</div>
                    </div>
                </div>
                ''')
    side_by_side_rows = ''.join(side_by_side_rows_parts)
    
    # Create the final HTML by formatting the template with the data
    html_template = html_template_str.format(
        title=title,
        description=description,
        stats=stats,
        inline_diff=inline_diff,
        added_keywords=added_keywords,
        removed_keywords=removed_keywords,
        common_keywords=common_keywords,
        section_analysis_html=section_analysis_html,
        side_by_side_rows=side_by_side_rows,
        original_text_escaped=html.escape(original_text),
        customized_text_escaped=html.escape(customized_text)
    )
    
    return html_template

def create_diff_json(original_text: str, customized_text: str) -> Dict:
    """
    Create a JSON structure with all diff data for frontend consumption.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        
    Returns:
        Dictionary with all diff data
    """
    # Get all the diff data
    diff_html = generate_word_level_diff(original_text, customized_text)
    side_by_side = generate_side_by_side_diff(original_text, customized_text)
    stats = get_diff_statistics(original_text, customized_text)
    section_analysis = analyze_section_changes(original_text, customized_text)
    keyword_analysis = analyze_keyword_changes(original_text, customized_text)
    
    # Combine into a single JSON structure
    diff_data = {
        "original_text": original_text,
        "customized_text": customized_text,
        "diff_html": diff_html,
        "side_by_side_diff": side_by_side["diff_data"],
        "statistics": stats,
        "section_analysis": section_analysis,
        "keyword_analysis": keyword_analysis
    }
    
    return diff_data

def export_diff_to_files(original_text: str, customized_text: str, output_dir: str, 
                          html_filename: str = "diff_output.html",
                          json_filename: str = "diff_data.json",
                          stats_filename: str = "diff_stats.json") -> Dict[str, str]:
    """
    Export diff output to files.
    
    Args:
        original_text: The original resume text
        customized_text: The customized resume text
        output_dir: Directory to save output files
        html_filename: Filename for HTML output
        json_filename: Filename for JSON output
        stats_filename: Filename for stats output
        
    Returns:
        Dictionary with paths to created files
    """
    import os
    
    # Create directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate the HTML document
    html_output = generate_diff_html_document(original_text, customized_text)
    html_path = os.path.join(output_dir, html_filename)
    
    # Generate JSON data
    json_data = create_diff_json(original_text, customized_text)
    json_path = os.path.join(output_dir, json_filename)
    
    # Get stats for simple stats file
    stats = get_diff_statistics(original_text, customized_text)
    stats_path = os.path.join(output_dir, stats_filename)
    
    # Write files
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
    
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    
    return {
        "html_file": html_path,
        "json_file": json_path,
        "stats_file": stats_path
    }

