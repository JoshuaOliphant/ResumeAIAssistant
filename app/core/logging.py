import os
import logfire
import httpx
import anthropic
import traceback
from fastapi import FastAPI
from sqlalchemy import Engine
from typing import Optional, Dict, Any, Callable, List, Union
from app.core.config import settings
from functools import wraps
import openai
from openai import OpenAI

def configure_logging(
    service_name: str = "resume-ai-assistant", 
    environment: Optional[str] = None,
    log_level: str = "INFO",
    capture_headers: bool = False,
    enable_system_metrics: bool = True
) -> None:
    """
    Configure Logfire for the application
    
    Args:
        service_name: Name of the service
        environment: Optional environment name (dev, prod, etc.)
        log_level: Logging level to use
        capture_headers: Whether to capture HTTP headers (may contain sensitive info)
        enable_system_metrics: Whether to enable system metrics collection
    """
    # Get environment from env var or default to development
    env = environment or os.getenv("ENVIRONMENT", "development")
    
    # Check if Logfire is enabled (allow disabling via env var)
    enabled = os.getenv("LOGFIRE_ENABLED", "true").lower() in ("true", "1", "yes")
    if not enabled:
        print("Logfire is disabled via LOGFIRE_ENABLED environment variable")
        return None
    
    # Configure Logfire
    console_options = {
        "colors": "auto",
        "span_style": "show-parents",
        "include_timestamps": True,
        "verbose": log_level.lower() == "debug",
        "min_log_level": log_level.lower()
    }
    
    logfire.configure(
        service_name=service_name,
        environment=env,
        token=os.getenv("LOGFIRE_API_KEY"),
        console=console_options
    )
    
    # Log configuration details
    if log_level.lower() == "debug":
        logfire.info("Debug logging enabled", level=log_level)
    
    # Enable system metrics if requested
    if enable_system_metrics:
        try:
            logfire.instrument_system_metrics()
            logfire.info("System metrics instrumentation enabled")
        except Exception as e:
            logfire.warning(
                "Failed to enable system metrics instrumentation", 
                error=str(e),
                error_type=type(e).__name__
            )
    
    # Log initial configuration
    logfire.info(
        "Logfire initialized", 
        service_name=service_name, 
        environment=env,
        log_level=log_level,
        capture_headers=capture_headers,
        system_metrics_enabled=enable_system_metrics
    )
    
    # Return the configured logger
    return logfire

def setup_fastapi_instrumentation(app: FastAPI, exclude_urls: Optional[List[str]] = None) -> None:
    """
    Set up FastAPI instrumentation with Logfire
    
    Args:
        app: FastAPI application instance
        exclude_urls: Optional list of URL patterns to exclude from instrumentation
    """
    try:
        # Configure request attributes mapping function
        def request_attributes_mapper(request, response=None):
            attributes = {
                "http.url": str(request.url),
                "http.method": request.method,
                "http.client_ip": request.client.host if request.client else None,
            }
            
            # Add response attributes if available
            if response:
                # Handle both response object and dictionary cases
                if isinstance(response, dict):
                    # If response is a dictionary, access attributes as dictionary keys
                    attributes["http.status_code"] = response.get("status_code")
                    attributes["http.content_length"] = response.get("content_length", 0)
                else:
                    # If response is an object, access attributes as properties
                    attributes["http.status_code"] = getattr(response, "status_code", None)
                    attributes["http.content_length"] = response.headers.get("content-length", 0) if hasattr(response, "headers") else 0
            
            return attributes
        
        # Instrument FastAPI
        logfire.instrument_fastapi(
            app, 
            request_attributes_mapper=request_attributes_mapper,
            excluded_urls=exclude_urls or []
        )
        
        logfire.info("FastAPI instrumentation set up successfully")
    except Exception as e:
        logfire.error(
            "Failed to set up FastAPI instrumentation",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__)
        )

def setup_sqlalchemy_instrumentation(engine: Engine) -> None:
    """
    Set up SQLAlchemy instrumentation with Logfire
    
    Args:
        engine: SQLAlchemy engine instance
    """
    try:
        logfire.instrument_sqlalchemy(engine=engine)
        logfire.info("SQLAlchemy instrumentation set up successfully", engine_url=str(engine.url))
    except Exception as e:
        logfire.error(
            "Failed to set up SQLAlchemy instrumentation",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__)
        )

def setup_httpx_instrumentation(
    client: Optional[httpx.Client] = None, 
    capture_headers: bool = False,
    request_hook: Optional[Callable] = None,
    response_hook: Optional[Callable] = None
) -> None:
    """
    Set up HTTPX instrumentation with Logfire
    
    Args:
        client: Optional HTTPX client instance (if None, instrument all clients)
        capture_headers: Whether to capture HTTP headers
        request_hook: Optional hook for processing request data
        response_hook: Optional hook for processing response data
    """
    try:
        # Define default hooks if not provided
        if capture_headers and not request_hook:
            def default_request_hook(span, request):
                # Get headers but exclude potential sensitive information
                safe_headers = {
                    k: v for k, v in request.headers.items() 
                    if k.lower() not in ("authorization", "cookie", "x-api-key")
                }
                span.set_attribute("http.request.headers", str(safe_headers))
            
            request_hook = default_request_hook
        
        if capture_headers and not response_hook:
            def default_response_hook(span, request, response):
                # Get response headers
                safe_headers = {
                    k: v for k, v in response.headers.items()
                    if k.lower() not in ("set-cookie", "authorization", "x-api-key")
                }
                span.set_attribute("http.response.headers", str(safe_headers))
                span.set_attribute("http.response.size", len(response.content) if hasattr(response, "content") else 0)
            
            response_hook = default_response_hook
        
        # Instrument HTTPX
        logfire.instrument_httpx(
            client=client,
            request_hook=request_hook,
            response_hook=response_hook
        )
        
        logfire.info(
            "HTTPX instrumentation set up successfully",
            global_instrumentation=client is None,
            capture_headers=capture_headers
        )
    except Exception as e:
        logfire.error(
            "Failed to set up HTTPX instrumentation",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__)
        )

def setup_anthropic_instrumentation(client: Optional[anthropic.Anthropic] = None) -> None:
    """
    Set up Anthropic instrumentation with Logfire
    
    Args:
        client: Optional Anthropic client instance (if None, instrument all clients)
    """
    try:
        # Using the correct parameter name and allowing context manager to complete
        with logfire.instrument_anthropic(anthropic_client=client):
            pass
        
        logfire.info(
            "Anthropic instrumentation set up successfully",
            global_instrumentation=client is None
        )
    except Exception as e:
        logfire.error(
            "Failed to set up Anthropic instrumentation",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__)
        )

def setup_openai_instrumentation(client: Optional[OpenAI] = None) -> None:
    """
    Set up OpenAI instrumentation with Logfire
    
    Args:
        client: Optional OpenAI client instance (if None, instrument all clients)
    """
    try:
        # Instrument OpenAI client
        logfire.instrument_openai(openai_client=client)
        
        logfire.info(
            "OpenAI instrumentation set up successfully",
            global_instrumentation=client is None,
            agent_support=True,
            models=[settings.OPENAI_MODEL, settings.OPENAI_EVALUATOR_MODEL, settings.OPENAI_OPTIMIZER_MODEL]
        )
    except Exception as e:
        logfire.error(
            "Failed to set up OpenAI instrumentation",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__)
        )

def log_function_call(func):
    """
    Decorator to log function calls with input arguments and return values
    
    Args:
        func: Function to decorate
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Prepare args for logging - avoid logging huge objects
        safe_args = [f"<{type(arg).__name__}>" if isinstance(arg, (dict, list)) and len(str(arg)) > 100 
                     else arg for arg in args]
        safe_kwargs = {k: f"<{type(v).__name__}>" if isinstance(v, (dict, list)) and len(str(v)) > 100 
                       else v for k, v in kwargs.items()}
        
        # Create a span for this function call
        with logfire.span(f"function.{func.__name__}") as span:
            span.set_attribute("function.name", func.__name__)
            span.set_attribute("function.module", func.__module__)
            
            # Set span attributes for arguments (safely)
            for i, arg in enumerate(safe_args):
                if i == 0 and arg == 'self':
                    continue  # Skip 'self' for methods
                try:
                    span.set_attribute(f"function.arg.{i}", str(arg))
                except:
                    span.set_attribute(f"function.arg.{i}", f"<unprintable {type(arg).__name__}>")
            
            # Set span attributes for keyword arguments (safely)
            for k, v in safe_kwargs.items():
                if k in ('self', 'cls'):
                    continue  # Skip 'self'/'cls' for methods
                try:
                    span.set_attribute(f"function.kwarg.{k}", str(v))
                except:
                    span.set_attribute(f"function.kwarg.{k}", f"<unprintable {type(v).__name__}>")
            
            try:
                # Log function entry
                logfire.info(
                    f"Function call: {func.__name__}",
                    function=func.__name__,
                    module=func.__module__,
                    args=safe_args,
                    kwargs=safe_kwargs,
                    event="function_entry"
                )
                
                # Call the function
                result = func(*args, **kwargs)
                
                # Prepare result for logging
                safe_result = f"<{type(result).__name__}>" if isinstance(result, (dict, list)) and len(str(result)) > 100 else result
                
                # Log function exit
                logfire.info(
                    f"Function return: {func.__name__}",
                    function=func.__name__,
                    result=safe_result,
                    event="function_exit"
                )
                
                # Set result attribute on span
                try:
                    span.set_attribute("function.result", str(safe_result))
                except:
                    span.set_attribute("function.result", f"<unprintable {type(result).__name__}>")
                
                return result
            except Exception as e:
                # Log exception
                logfire.error(
                    f"Function exception: {func.__name__}",
                    function=func.__name__,
                    exception_type=type(e).__name__,
                    exception=str(e),
                    event="function_exception",
                    traceback=traceback.format_exception(type(e), e, e.__traceback__)
                )
                
                # Set exception attributes on span
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                
                raise
    
    return wrapper

def get_logger(name: str):
    """
    Get a logger for a specific module
    
    Args:
        name: Name to use for the logger, typically __name__
    """
    # Return the logfire instance (it's already configured globally)
    return logfire