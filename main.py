from app.api.api import app

# This exposes the ASGI app for gunicorn to use with the uvicorn worker

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
