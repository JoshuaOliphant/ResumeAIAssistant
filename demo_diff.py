#!/usr/bin/env python
"""
Demo script to test the resume diff functionality.
"""
from app.services.diff_service import generate_resume_diff, get_diff_statistics
import json
import os
from pathlib import Path

# Create output directory for HTML files
output_dir = Path("./demo_output")
output_dir.mkdir(exist_ok=True)

# Sample resume texts
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

# Generate diff content
diff_html = generate_resume_diff(original_resume, customized_resume)
diff_stats = get_diff_statistics(original_resume, customized_resume)

# Save diff HTML to file
with open(output_dir / "diff_output.html", "w") as f:
    f.write(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Diff Demo</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .addition {{ background-color: #e6ffed; color: #22863a; }}
            .deletion {{ background-color: #ffeef0; color: #cb2431; text-decoration: line-through; }}
            .modification {{ background-color: #fff5b1; }}
            .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
            .stat-item {{ padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            h1, h2 {{ color: #333; }}
            .toggle-container {{ margin: 20px 0; }}
            #original-content, #customized-content {{ display: none; padding: 20px; border: 1px solid #ddd; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Resume Diff Demo</h1>
            
            <div class="stats">
                <div class="stat-item">
                    <strong>Additions:</strong> <span style="color: #22863a">+{diff_stats['additions']}</span>
                </div>
                <div class="stat-item">
                    <strong>Deletions:</strong> <span style="color: #cb2431">-{diff_stats['deletions']}</span>
                </div>
                <div class="stat-item">
                    <strong>Modifications:</strong> <span style="color: #dbab09">{diff_stats['modifications']}</span>
                </div>
                <div class="stat-item">
                    <strong>Unchanged:</strong> <span style="color: #0366d6">{diff_stats['unchanged']}</span>
                </div>
            </div>
            
            <div class="toggle-container">
                <button onclick="showDiff()">Show Diff</button>
                <button onclick="showOriginal()">Show Original</button>
                <button onclick="showCustomized()">Show Customized</button>
            </div>
            
            <div id="diff-content">{diff_html}</div>
            <pre id="original-content">{original_resume}</pre>
            <pre id="customized-content">{customized_resume}</pre>
            
            <script>
                function showDiff() {{
                    document.getElementById('diff-content').style.display = 'block';
                    document.getElementById('original-content').style.display = 'none';
                    document.getElementById('customized-content').style.display = 'none';
                }}
                
                function showOriginal() {{
                    document.getElementById('diff-content').style.display = 'none';
                    document.getElementById('original-content').style.display = 'block';
                    document.getElementById('customized-content').style.display = 'none';
                }}
                
                function showCustomized() {{
                    document.getElementById('diff-content').style.display = 'none';
                    document.getElementById('original-content').style.display = 'none';
                    document.getElementById('customized-content').style.display = 'block';
                }}
            </script>
        </div>
    </body>
    </html>
    """)

# Save stats to JSON file
with open(output_dir / "diff_stats.json", "w") as f:
    json.dump(diff_stats, f, indent=2)

print(f"Diff demo generated successfully!")
print(f"HTML output: {os.path.abspath(output_dir / 'diff_output.html')}")
print(f"Stats output: {os.path.abspath(output_dir / 'diff_stats.json')}")
print("\nDiff Statistics:")
print(f"- Additions: {diff_stats['additions']}")
print(f"- Deletions: {diff_stats['deletions']}")
print(f"- Modifications: {diff_stats['modifications']}")
print(f"- Unchanged: {diff_stats['unchanged']}")
