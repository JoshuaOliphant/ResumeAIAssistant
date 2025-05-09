"""
Example script to demonstrate the improved diff visualization.
"""
import os
from app.services.diff_service import (
    export_diff_to_files, 
    generate_diff_html_document,
    create_diff_json
)

# Sample resumes for demonstration
ORIGINAL_RESUME = """# John Doe
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

CUSTOMIZED_RESUME = """# John Doe
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

def main():
    """Generate and export diff files for demonstration."""
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), "demo_output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Export diff files
    print("Generating diff files...")
    result = export_diff_to_files(
        ORIGINAL_RESUME,
        CUSTOMIZED_RESUME,
        output_dir,
        html_filename="diff_output.html",
        json_filename="diff_data.json",
        stats_filename="diff_stats.json"
    )
    
    print("Files generated:")
    for file_type, file_path in result.items():
        print(f"- {file_type}: {file_path}")
    
    print("\nOpen the HTML file in a browser to see the visual diff.")

if __name__ == "__main__":
    main()