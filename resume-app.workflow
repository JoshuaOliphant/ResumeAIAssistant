run = ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]
language = "python"
onboot = ["echo Starting Resume Customization API server on port 5000..."]