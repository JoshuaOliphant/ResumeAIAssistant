from pprint import pprint

import requests

BASE_URL = "http://localhost:5000/api/v1"


def test_health():
    """Test the health endpoint"""
    response = requests.get("http://localhost:5000/health")
    print("Health Check Response:")
    pprint(response.json())
    print(f"Status Code: {response.status_code}")
    print("=" * 50)
    return response.status_code == 200


def test_create_resume():
    """Test creating a resume"""
    resume_data = {
        "title": "My Test Resume",
        "content": "# John Doe\n\n## Experience\n\n### Software Engineer\nABC Company (2020 - Present)\n- Developed web applications using Python and JavaScript",
    }
    response = requests.post(f"{BASE_URL}/resumes", json=resume_data)
    print("Create Resume Response:")
    try:
        pprint(response.json())
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response Content: {response.text}")
    print(f"Status Code: {response.status_code}")
    print("=" * 50)

    if response.status_code == 200 or response.status_code == 201:
        return response.json()
    return None


def test_get_resumes():
    """Test getting all resumes"""
    response = requests.get(f"{BASE_URL}/resumes")
    print("Get Resumes Response:")
    try:
        pprint(response.json())
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response Content: {response.text}")
    print(f"Status Code: {response.status_code}")
    print("=" * 50)
    return response.status_code == 200


def test_create_job():
    """Test creating a job description"""
    job_data = {
        "title": "Software Engineer",
        "company": "XYZ Corp",
        "description": "We are looking for a software engineer with experience in Python and JavaScript. \
                       The ideal candidate will have at least 2 years of experience in web development \
                       and be familiar with modern frameworks.",
    }
    response = requests.post(f"{BASE_URL}/jobs", json=job_data)
    print("Create Job Description Response:")
    try:
        pprint(response.json())
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response Content: {response.text}")
    print(f"Status Code: {response.status_code}")
    print("=" * 50)

    if response.status_code == 200 or response.status_code == 201:
        return response.json()
    return None


def test_get_jobs():
    """Test getting all job descriptions"""
    response = requests.get(f"{BASE_URL}/jobs")
    print("Get Jobs Response:")
    try:
        pprint(response.json())
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response Content: {response.text}")
    print(f"Status Code: {response.status_code}")
    print("=" * 50)
    return response.status_code == 200


def test_analyze_resume(resume_id, job_id):
    """Test analyzing a resume against a job description"""
    if not resume_id or not job_id:
        print("Cannot analyze: missing resume_id or job_id")
        return None

    analysis_data = {"resume_id": resume_id, "job_description_id": job_id}
    response = requests.post(f"{BASE_URL}/ats/analyze", json=analysis_data)
    print("Analyze Resume Response:")
    try:
        pprint(response.json())
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response Content: {response.text}")
    print(f"Status Code: {response.status_code}")
    print("=" * 50)

    if response.status_code == 200:
        return response.json()
    return None


def test_customize_resume(resume_id, job_id):
    """Test customizing a resume for a job description"""
    if not resume_id or not job_id:
        print("Cannot customize: missing resume_id or job_id")
        return None

    customization_data = {
        "resume_id": resume_id,
        "job_description_id": job_id,
        "customization_strength": 2,
        "focus_areas": "technical skills, experience",
    }
    response = requests.post(f"{BASE_URL}/customize", json=customization_data)
    print("Customize Resume Response:")
    try:
        pprint(response.json())
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response Content: {response.text}")
    print(f"Status Code: {response.status_code}")
    print("=" * 50)

    if response.status_code == 200:
        return response.json()
    return None


def test_generate_cover_letter(resume_id, job_id):
    """Test generating a cover letter"""
    if not resume_id or not job_id:
        print("Cannot generate cover letter: missing resume_id or job_id")
        return None

    cover_letter_data = {
        "resume_id": resume_id,
        "job_description_id": job_id,
        "applicant_name": "John Doe",
        "company_name": "XYZ Corp",
        "tone": "professional",
    }
    response = requests.post(
        f"{BASE_URL}/cover-letter/generate", json=cover_letter_data
    )
    print("Generate Cover Letter Response:")
    try:
        pprint(response.json())
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response Content: {response.text}")
    print(f"Status Code: {response.status_code}")
    print("=" * 50)

    if response.status_code == 200:
        return response.json()
    return None


def run_basic_tests():
    """Run basic API tests without Anthropic integration"""
    print("Running basic API tests...")

    health_ok = test_health()
    if not health_ok:
        print("Health check failed. Stopping tests.")
        return False

    # Test resume endpoints
    resume = test_create_resume()
    resumes_ok = test_get_resumes()

    # Test job endpoints
    job = test_create_job()
    jobs_ok = test_get_jobs()

    if not (resume and job and resumes_ok and jobs_ok):
        print("Basic API tests failed. Please check the server logs.")
        return False

    print("Basic API tests passed!")
    return True, resume, job


def run_ai_tests(resume, job):
    """Run AI-powered tests requiring Anthropic integration"""
    print("Running AI-powered tests...")

    resume_id = resume.get("id")
    job_id = job.get("id")

    if not resume_id or not job_id:
        print("Missing resume_id or job_id. Cannot run AI tests.")
        return False

    # Test ATS analysis
    ats_result = test_analyze_resume(resume_id, job_id)

    # Test resume customization
    custom_result = test_customize_resume(resume_id, job_id)

    # Test cover letter generation
    cover_letter = test_generate_cover_letter(resume_id, job_id)

    if not (ats_result and custom_result and cover_letter):
        print(
            "AI-powered tests failed. Please check if Anthropic API is properly configured."
        )
        return False

    print("AI-powered tests passed!")
    return True


if __name__ == "__main__":
    print("Starting API Tests")
    print("=" * 50)

    # Run basic tests first
    basic_results = run_basic_tests()

    if isinstance(basic_results, tuple) and len(basic_results) == 3:
        success, resume, job = basic_results
        if success:
            # If basic tests passed, run AI tests
            ai_success = run_ai_tests(resume, job)
            if ai_success:
                print("All API tests passed successfully!")
            else:
                print(
                    "AI-powered tests failed. The application might still work without AI features."
                )
    else:
        print("Tests completed with issues. Please check the output for details.")
