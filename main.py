import os
import logging
from app.api.api import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database on startup
try:
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")
    
# This exposes the ASGI app for gunicorn to use with the uvicorn worker

if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
