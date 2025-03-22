"""
Test script for the ATS analysis endpoint
"""
import requests
import json
import sys
import time
import nltk

def initialize_nlp():
    """Ensure NLP resources are available"""
    try:
        nltk.corpus.stopwords.words('english')
        print("NLTK resources already initialized")
    except:
        print("Initializing NLP resources...")
        import app.core.nltk_init
        app.core.nltk_init.initialize_nlp()

def test_ats_analysis():
    """Test the ATS analysis endpoint"""
    # Ensure NLP resources are initialized
    initialize_nlp()
    
    base_url = "http://localhost:5000"
    
    # 1. Create a test resume
    print("\nCreating test resume...")
    resume_data = {
        "title": "Test Resume",
        "content": """# John Doe
Software Engineer

## Experience
**Senior Software Engineer** | ABC Tech | 2020-Present
- Developed and maintained Python backend services
- Implemented CI/CD pipelines using GitHub Actions
- Optimized database queries resulting in 40% performance improvement

**Software Engineer** | XYZ Corp | 2018-2020
- Built RESTful APIs using Node.js and Express
- Collaborated with UX team on front-end development with React
- Participated in agile development process with daily standups

## Education
**Bachelor of Science in Computer Science** | University of Technology | 2018

## Skills
- Programming: Python, JavaScript, TypeScript, Java
- Frameworks: Django, Flask, React, Express
- Database: PostgreSQL, MongoDB
- DevOps: Docker, Kubernetes, AWS
"""
    }
    
    response = requests.post(
        f"{base_url}/api/v1/resumes/",
        json=resume_data
    )
    
    print(f"Resume creation response status: {response.status_code}")
    
    if response.status_code not in (200, 201):
        print(f"Failed to create resume: {response.status_code}, {response.text}")
        sys.exit(1)
    
    resume_data = response.json()
    resume_id = resume_data["id"]
    print(f"Resume created with ID: {resume_id}")
    
    # 2. Create a test job description
    print("\nCreating test job description...")
    job_data = {
        "title": "Senior Python Developer",
        "company": "Tech Innovations Inc",
        "description": """
We are looking for a Senior Python Developer to join our growing team.

Responsibilities:
- Design and implement high-performance, reliable Python applications
- Optimize existing systems for maximum speed and scalability
- Collaborate with cross-functional teams to define, design, and ship new features
- Write clean, maintainable, and efficient code

Requirements:
- 3+ years experience with Python
- Experience with web frameworks such as Django or Flask
- Strong knowledge of SQL and NoSQL databases
- Familiarity with AWS or other cloud services
- Experience with CI/CD pipelines
- Bachelor's degree in Computer Science or equivalent
"""
    }
    
    response = requests.post(
        f"{base_url}/api/v1/jobs/",
        json=job_data
    )
    
    print(f"Job creation response status: {response.status_code}")
    
    if response.status_code not in (200, 201):
        print(f"Failed to create job description: {response.status_code}, {response.text}")
        sys.exit(1)
    
    job_data = response.json()
    job_id = job_data["id"]
    print(f"Job description created with ID: {job_id}")
    
    # 3. Test ATS analysis
    print("\nTesting ATS analysis...")
    analysis_data = {
        "resume_id": resume_id,
        "job_description_id": job_id
    }
    
    # Try the analysis multiple times in case of initialization issues
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = requests.post(
                f"{base_url}/api/v1/ats/analyze",
                json=analysis_data
            )
            
            print(f"ATS analysis response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("\nATS Analysis Results:")
                print(f"Match Score: {result['match_score']}%")
                print("\nMatching Keywords (top 5):")
                for kw in result["matching_keywords"][:5]:
                    print(f"- {kw['keyword']} (Resume: {kw['count_in_resume']}, Job: {kw['count_in_job']})")
                
                print("\nMissing Keywords (top 5):")
                for kw in result["missing_keywords"][:5]:
                    print(f"- {kw['keyword']} (Job: {kw['count_in_job']})")
                
                print("\nImprovement Suggestions:")
                for imp in result["improvements"]:
                    print(f"- [{imp['priority']}] {imp['category']}: {imp['suggestion']}")
                
                print("\nATS analysis completed successfully")
                return True
            else:
                error_text = response.text
                print(f"Attempt {attempt+1}/{max_attempts} failed with status code {response.status_code}")
                print(f"Error response: {error_text}")
                # Allow a short time for possible initialization to complete
                time.sleep(2)
        except Exception as e:
            print(f"Attempt {attempt+1}/{max_attempts} error: {str(e)}")
            # Allow a short time for possible initialization to complete
            time.sleep(2)
    
    print("All attempts failed to analyze resume for ATS compatibility")
    return False

if __name__ == "__main__":
    test_ats_analysis()