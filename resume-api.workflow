run = ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
language = "python"
onboot = ["echo Starting Resume Customization API server on port 8080..."]
hidden = ["**/node_modules", ".pytest_cache", "**/__pycache__"]