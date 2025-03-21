import os
from app.api.api import app

# This exposes the ASGI app for gunicorn to use with the uvicorn worker

if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
