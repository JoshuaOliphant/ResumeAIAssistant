import os
import logfire
import traceback
from app.api.api import app
from app.db.session import engine
from app.core.logging import (
    configure_logging, 
    setup_fastapi_instrumentation,
    setup_sqlalchemy_instrumentation,
    setup_httpx_instrumentation,
)

# Import smart request handler setup function
try:
    from app.services.smart_request_handler import setup_smart_request_handling
    SMART_REQUEST_AVAILABLE = True
except ImportError:
    SMART_REQUEST_AVAILABLE = False

# Configure Logfire with more detailed options
configure_logging(
    service_name="resume-ai-assistant",
    environment=os.getenv("ENVIRONMENT", "development"),
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    capture_headers=False,  # Set to True to capture headers (be careful with sensitive data)
    enable_system_metrics=True
)

# Initialize all instrumentation
try:
    # Set up FastAPI instrumentation
    setup_fastapi_instrumentation(
        app,
        exclude_urls=[
            # Exclude health check and static files to reduce noise
            "/health",
            "/static/*",
            "/favicon.ico"
        ]
    )

    # Set up SQLAlchemy instrumentation
    setup_sqlalchemy_instrumentation(engine)
    
    # Set up HTTPX instrumentation for all clients
    setup_httpx_instrumentation(
        client=None,  # Instrument all clients
        capture_headers=False  # Avoid capturing potentially sensitive headers
    )
    
    # Set up smart request handling
    if SMART_REQUEST_AVAILABLE:
        try:
            setup_smart_request_handling(app)
            logfire.info("Smart request handling initialized successfully")
        except Exception as e:
            logfire.error(
                "Error setting up smart request handling",
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exception(type(e), e, e.__traceback__)
            )
    
    logfire.info("All instrumentations set up successfully")
except Exception as e:
    logfire.error(
        "Error setting up instrumentations", 
        error=str(e), 
        error_type=type(e).__name__,
        traceback=traceback.format_exception(type(e), e, e.__traceback__)
    )

# Initialize database on startup
try:
    # Import Base and all models to ensure they're registered
    from app.db.session import Base
    from app.models import *  # This imports all models
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    logfire.info("Database initialized successfully")
except Exception as e:
    logfire.error(
        "Error initializing database", 
        error=str(e), 
        error_type=type(e).__name__,
        traceback=traceback.format_exception(type(e), e, e.__traceback__)
    )
    
# This exposes the ASGI app for gunicorn to use with the uvicorn worker

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or use 5001 as default
    port = int(os.environ.get("PORT", 5001))
    
    # Log server startup with more details
    logfire.info(
        "Starting server", 
        host="0.0.0.0", 
        port=port, 
        environment=os.getenv("ENVIRONMENT", "development"),
        logfire_project=os.getenv("LOGFIRE_PROJECT", "resume-ai-assistant"),
        python_version=os.getenv("PYTHON_VERSION", "3.x")
    )
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=port)
