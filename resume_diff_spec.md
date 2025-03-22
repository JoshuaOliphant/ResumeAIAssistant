# Resume Diff View Feature Specification

## Overview

This document outlines the implementation plan for adding a "diff view" feature to the ResumeAIAssistant application. This feature will allow users to toggle between a regular view of their customized resume and a view that highlights the differences between the original and customized versions.

## Feature Requirements

1. Create a toggle mechanism to switch between regular and diff views
2. Generate a visual representation of changes that clearly shows:
   - Added content (highlighted in green)
   - Removed content (in red with strikethrough)
   - Modified content (highlighted in yellow)
3. Ensure the diff view is readable and intuitive
4. Maintain compatibility with existing resume customization features

## Implementation Plan

### Backend Changes

#### 1. Create Diff Generation Service

Create a new service in `app/services/diff_service.py` that:
- Takes original and customized resume text as input
- Uses a diff algorithm to identify changes
- Generates HTML or Markdown with appropriate styling for changes
- Returns a formatted diff output

```python
# Pseudocode for diff_service.py
from difflib import SequenceMatcher
import html

def generate_resume_diff(original_text, customized_text):
    """
    Generate a diff between original and customized resume texts.
    Returns HTML with appropriate styling for changes.
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
```

#### 2. Update API Endpoints

Modify the existing resume customization endpoint or add a new endpoint in `app/api/routes/resume.py`:

```python
# Pseudocode for API endpoint
@router.get("/resume/customized/{resume_id}", response_model=ResumeResponse)
async def get_customized_resume(
    resume_id: int, 
    show_diff: bool = Query(False, description="Show diff view of changes"),
    db: Session = Depends(get_db)
):
    # Get original and customized resumes
    original_resume = get_original_resume(db, resume_id)
    customized_resume = get_customized_resume(db, resume_id)
    
    if show_diff:
        # Generate diff view
        from app.services.diff_service import generate_resume_diff
        diff_content = generate_resume_diff(original_resume.content, customized_resume.content)
        return {
            "id": resume_id,
            "content": diff_content,
            "is_diff_view": True
        }
    else:
        # Return regular customized resume
        return {
            "id": resume_id,
            "content": customized_resume.content,
            "is_diff_view": False
        }
```

### Frontend Changes

#### 1. Add Toggle UI Component

Add a toggle button in the resume view component:

```jsx
// Pseudocode for React component
function ResumeView({ resumeId }) {
    const [showDiff, setShowDiff] = useState(false);
    const [resumeContent, setResumeContent] = useState('');
    
    useEffect(() => {
        // Fetch resume content with diff parameter
        fetchResume(resumeId, showDiff).then(data => {
            setResumeContent(data.content);
        });
    }, [resumeId, showDiff]);
    
    return (
        <div className="resume-container">
            <div className="controls">
                <label className="toggle">
                    <input 
                        type="checkbox" 
                        checked={showDiff} 
                        onChange={() => setShowDiff(!showDiff)} 
                    />
                    <span className="slider"></span>
                    <span className="label">Show changes</span>
                </label>
            </div>
            
            <div className={`resume-content ${showDiff ? 'diff-view' : ''}`}>
                {/* Render resume content, potentially as HTML if diff view */}
                {showDiff ? (
                    <div dangerouslySetInnerHTML={{ __html: resumeContent }} />
                ) : (
                    <MarkdownRenderer content={resumeContent} />
                )}
            </div>
        </div>
    );
}
```

#### 2. Add CSS Styling for Diff View

Add CSS styles to highlight the differences:

```css
/* Diff view styling */
.diff-view .addition {
    background-color: #e6ffed;
    color: #22863a;
}

.diff-view .deletion {
    background-color: #ffeef0;
    color: #cb2431;
}

.diff-view .modification {
    background-color: #fff5b1;
}

/* Toggle button styling */
.toggle {
    position: relative;
    display: inline-block;
    width: 60px;
    height: 34px;
}

.toggle input {
    opacity: 0;
    width: 0;
    height: 0;
}

.slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #ccc;
    transition: .4s;
    border-radius: 34px;
}

.slider:before {
    position: absolute;
    content: "";
    height: 26px;
    width: 26px;
    left: 4px;
    bottom: 4px;
    background-color: white;
    transition: .4s;
    border-radius: 50%;
}

input:checked + .slider {
    background-color: #2196F3;
}

input:checked + .slider:before {
    transform: translateX(26px);
}

.label {
    margin-left: 70px;
}
```

## Testing Plan

1. **Unit Tests**:
   - Test the diff generation algorithm with various resume scenarios
   - Verify correct HTML generation for different types of changes

2. **Integration Tests**:
   - Test the API endpoint with and without the diff parameter
   - Verify correct response format and content

3. **UI Tests**:
   - Test the toggle functionality
   - Verify correct rendering of diff view
   - Test with various resume formats and content types

## Implementation Timeline

- Backend implementation: 2-3 days
- Frontend implementation: 2-3 days
- Testing and refinement: 1-2 days
- Total estimated time: 5-8 days

## Future Enhancements

1. Add section-level diff views to focus on specific resume sections
2. Implement a side-by-side comparison view
3. Add the ability to accept/reject individual changes
4. Provide statistics on the number and types of changes made
