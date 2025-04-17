"""
Resume diff service for generating visual diffs between original and customized resumes.
"""
from difflib import SequenceMatcher
import html
import re
from typing import Dict, List, Tuple, Union

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
            diff_html.append(f'<span class="addition">{html.escape(customized_text[j1:j2])}</span>')
        elif op == 'delete':
            diff_html.append(f'<span class="deletion"><del>{html.escape(original_text[i1:i2])}</del></span>')
        elif op == 'replace':
            diff_html.append(f'<span class="deletion"><del>{html.escape(original_text[i1:i2])}</del></span>')
            diff_html.append(f'<span class="addition">{html.escape(customized_text[j1:j2])}</span>')
    
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
                diff_html.append(f'<span class="addition">{html.escape(line)}</span>')
        elif op == 'delete':
            for line in original_lines[i1:i2]:
                diff_html.append(f'<span class="deletion"><del>{html.escape(line)}</del></span>')
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
                    diff_html.append(f'<span class="addition">{html.escape("".join(cust_words[wj1:wj2]))}</span>')
                elif word_op == 'delete':
                    diff_html.append(f'<span class="deletion"><del>{html.escape("".join(orig_words[wi1:wi2]))}</del></span>')
                elif word_op == 'replace':
                    diff_html.append(f'<span class="deletion"><del>{html.escape("".join(orig_words[wi1:wi2]))}</del></span>')
                    diff_html.append(f'<span class="addition">{html.escape("".join(cust_words[wj1:wj2]))}</span>')
    
    return ''.join(diff_html)

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

def analyze_section_changes(original_text: str, customized_text: str) -> Dict[str, Dict[str, Union[str, float]]]:
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
                "deletions": 0
            }
        elif orig_content and not cust_content:
            # Section removed
            section_analysis[section_name] = {
                "status": "removed",
                "change_percentage": 100.0,
                "content_length": len(orig_content),
                "changes": 0,
                "additions": 0,
                "deletions": len(orig_content)
            }
        else:
            # Section exists in both - calculate differences
            stats = get_diff_statistics(orig_content, cust_content)
            total_chars = stats["unchanged"] + stats["additions"] + stats["deletions"] + stats["modifications"]
            change_percentage = 0
            if total_chars > 0:
                change_percentage = ((stats["additions"] + stats["deletions"] + stats["modifications"]) / total_chars) * 100
            
            status = "unchanged"
            if change_percentage > 75:
                status = "major_changes"
            elif change_percentage > 25:
                status = "moderate_changes"
            elif change_percentage > 0:
                status = "minor_changes"
            
            section_analysis[section_name] = {
                "status": status,
                "change_percentage": round(change_percentage, 1),
                "stats": stats,
                "content_length": len(cust_content),
                # Add these properties that the frontend component expects
                "changes": stats["modifications"],
                "additions": stats["additions"],
                "deletions": stats["deletions"]
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
