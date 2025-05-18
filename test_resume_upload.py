#!/usr/bin/env python

import requests
import json
import uuid

# API base URL
BASE_URL = "http://localhost:5001"

# Test resume upload
def test_resume_upload():
    # Create a test resume
    resume_data = {
        "title": "Test Resume",
        "content": "# Test Resume\n\nThis is a test resume content."
    }
    
    # Make the POST request
    response = requests.post(f"{BASE_URL}/api/v1/resumes/", json=resume_data)
    
    # Print status code and response
    print(f"Status code: {response.status_code}")
    
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Check if needed fields are present
        if response.status_code == 201:
            # These are the fields that were previously missing
            required_fields = ["created_at", "updated_at"]
            version_fields = ["created_at"]
            
            missing_fields = []
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if "current_version" in data and data["current_version"]:
                for field in version_fields:
                    if field not in data["current_version"]:
                        missing_fields.append(f"current_version.{field}")
            
            if missing_fields:
                print(f"\nValidation error: Still missing fields: {', '.join(missing_fields)}")
            else:
                print("\nSuccess! All required fields are present.")
    except json.JSONDecodeError:
        print("Could not parse JSON response")
        print(f"Raw response: {response.text}")

if __name__ == "__main__":
    test_resume_upload()