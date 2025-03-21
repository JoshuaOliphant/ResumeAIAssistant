import requests
import json
import os
import time
import sys

BASE_URL = "http://localhost:5000"
API_V1 = "/api/v1"
# Set a reasonable timeout for requests (10 seconds)
REQUEST_TIMEOUT = 10

def test_health():
    """Test the health endpoint"""
    print("\n⚙️ Testing API health...")
    response = requests.get(f"{BASE_URL}/health", timeout=REQUEST_TIMEOUT)
    assert response.status_code == 200
    assert response.json()["message"] == "Resume Customization API is running"
    print("✅ Health check passed")
    return True

def test_create_resume():
    """Test creating a resume"""
    print("\n📄 Testing resume creation...")
    sample_resume = {
        "title": "Software Engineer Resume",
        "content": """# John Doe
## Software Engineer

**Email:** john.doe@example.com | **Phone:** (123) 456-7890 | **Location:** New York, NY

### Summary
Experienced software engineer with 5+ years in full-stack development, cloud services, and DevOps. Passionate about creating scalable solutions and optimizing performance.

### Experience
#### Senior Software Engineer | Tech Solutions Inc. | 2020 - Present
- Redesigned the company's primary web application, improving load times by 40%
- Implemented CI/CD pipelines, reducing deployment time by 60%
- Led a team of 5 engineers in developing new product features

#### Software Developer | Digital Innovations | 2018 - 2020
- Developed RESTful APIs used by over 50,000 users daily
- Optimized database queries, reducing response time by 30%
- Collaborated with UX designers to implement intuitive user interfaces

### Education
**Bachelor of Science in Computer Science** | New York University | 2018

### Skills
- Languages: Python, JavaScript, TypeScript, Java
- Frameworks: React, Node.js, Django, FastAPI
- Tools: Docker, Kubernetes, AWS, Git
- Databases: PostgreSQL, MongoDB, Redis
"""
    }
    
    response = requests.post(f"{BASE_URL}{API_V1}/resumes/", json=sample_resume, timeout=REQUEST_TIMEOUT)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {response.json()}")
    except:
        print(f"Response text: {response.text}")
    
    assert response.status_code == 200 or response.status_code == 201
    resume_data = response.json()
    assert resume_data["title"] == sample_resume["title"]
    assert "id" in resume_data
    print(f"✅ Resume created with ID: {resume_data['id']}")
    return resume_data["id"]

def test_create_job():
    """Test creating a job description"""
    print("\n💼 Testing job description creation...")
    sample_job = {
        "title": "Senior Software Engineer",
        "company": "Innovative Tech Solutions",
        "description": """# Senior Software Engineer

## About Us
Innovative Tech Solutions is a fast-growing tech company focused on creating cutting-edge web applications and services. We're looking for a talented Senior Software Engineer to join our team.

## Job Description
We are seeking an experienced Senior Software Engineer with expertise in Python and cloud technologies. The ideal candidate will have a strong background in developing scalable applications and working with modern frameworks.

## Responsibilities
- Design and develop high-quality, scalable software solutions
- Lead technical projects and mentor junior engineers
- Collaborate with cross-functional teams to define and implement new features
- Optimize applications for maximum performance and scalability
- Implement automated testing to ensure code quality
- Participate in code reviews and contribute to engineering best practices

## Requirements
- Bachelor's degree in Computer Science, Engineering, or related field
- 5+ years of experience in software development
- Strong proficiency in Python, JavaScript, and web technologies
- Experience with modern frameworks like Django, FastAPI, or Flask
- Knowledge of cloud services (AWS, Azure, or GCP)
- Experience with containerization tools like Docker and Kubernetes
- Strong understanding of database design and optimization
- Excellent problem-solving skills and attention to detail

## Benefits
- Competitive salary and benefits package
- Remote-friendly work environment
- Professional development opportunities
- Flexible working hours
- Collaborative and innovative team culture
"""
    }
    
    response = requests.post(f"{BASE_URL}{API_V1}/jobs/", json=sample_job, timeout=REQUEST_TIMEOUT)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {response.json()}")
    except:
        print(f"Response text: {response.text}")
    
    assert response.status_code == 200 or response.status_code == 201
    job_data = response.json()
    assert job_data["title"] == sample_job["title"]
    assert "id" in job_data
    print(f"✅ Job description created with ID: {job_data['id']}")
    return job_data["id"]

def test_ats_analysis(resume_id, job_id):
    """Test ATS analysis"""
    print("\n🔍 Testing ATS Analysis...")
    analysis_request = {
        "resume_id": resume_id,
        "job_description_id": job_id
    }
    
    response = requests.post(f"{BASE_URL}{API_V1}/ats/analyze", json=analysis_request, timeout=REQUEST_TIMEOUT)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {response.json()}")
    except:
        print(f"Response text: {response.text}")
        
    assert response.status_code == 200
    analysis_data = response.json()
    assert "match_score" in analysis_data
    assert "matching_keywords" in analysis_data
    assert "missing_keywords" in analysis_data
    assert "improvements" in analysis_data
    print(f"✅ ATS analysis completed with match score: {analysis_data['match_score']}%")
    print(f"  - Matching keywords: {len(analysis_data['matching_keywords'])}")
    print(f"  - Missing keywords: {len(analysis_data['missing_keywords'])}")
    print(f"  - Improvement suggestions: {len(analysis_data['improvements'])}")
    return analysis_data

def run_basic_tests():
    """Run basic API tests without Claude integration"""
    try:
        # Check if the API is running
        if not test_health():
            print("❌ Health check failed, make sure the API is running")
            return False, None, None
        
        # Create a resume and job description
        resume_id = test_create_resume()
        job_id = test_create_job()
        
        # Run ATS analysis
        test_ats_analysis(resume_id, job_id)
        
        print("\n✅ All basic tests completed successfully!")
        return True, resume_id, job_id
    
    except Exception as e:
        import traceback
        print(f"\n❌ Test failed: {str(e)}")
        print(traceback.format_exc())
        return False, None, None

if __name__ == "__main__":
    run_basic_tests()