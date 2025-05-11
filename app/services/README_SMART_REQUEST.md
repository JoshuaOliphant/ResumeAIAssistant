# Smart Request Handler

## Overview

The Smart Request Handler provides intelligent request handling capabilities to enhance the performance, reliability, and cost-effectiveness of API requests. It offers a comprehensive system for optimizing API requests based on complexity, priority, and resource requirements.

## Key Features

### 1. Request Prioritization
Automatically prioritize requests based on importance:
- **Critical**: User-facing requests that block UI
- **High**: Important requests that affect user experience
- **Medium**: Standard requests
- **Low**: Background or non-critical requests

### 2. Context-Aware Model Selection
Choose optimal AI models based on request context:
- Analyze request content to determine complexity
- Select appropriate AI model tier based on task complexity and importance
- Support for dynamic timeouts based on request complexity

### 3. Request Batching and Queueing
Improve throughput by batching similar requests:
- Batch requests to the same endpoint to reduce overhead
- Queue prioritization by importance level
- Background processing for non-critical requests

### 4. Intelligent Timeout Management
Optimize timeouts based on request complexity:
- Automatic timeout setting based on historical performance
- Dynamic adjustment of timeouts based on request complexity
- Proper error handling for timed-out requests

### 5. Resource Optimization
Distribute requests based on system load:
- Limit concurrent requests per endpoint
- Throttle requests during high load situations
- Circuit breaker pattern to avoid overloading AI providers

### 6. Monitoring and Statistics
Comprehensive monitoring of requests:
- Track request status, duration, and errors
- Generate detailed statistics per endpoint
- Health metrics for system monitoring

## Usage

### Middleware Setup

The Smart Request Middleware is set up in `main.py`:

```python
from app.services.smart_request_handler import setup_smart_request_handling

# Set up smart request handling
setup_smart_request_handling(app)
```

### Endpoint Decorator

Use the `@smart_request` decorator to add smart handling to individual endpoints:

```python
from app.services.smart_request_handler import smart_request, TaskComplexity, RequestPriority

@router.post("/analyze")
@smart_request(complexity=TaskComplexity.MODERATE, priority=RequestPriority.HIGH)
async def analyze_data(request_data: AnalysisRequest, request_id: str = None):
    # Process request with smart handling
    result = await your_processing_function(request_data)
    return {"result": result, "request_id": request_id}
```

## API

### Configuration

The system allows for configuration of:
- Maximum concurrent requests per endpoint
- Default timeouts per complexity level
- Circuit breaker thresholds and recovery times

### Decorator Options

The `@smart_request` decorator accepts:
- `complexity`: TaskComplexity enum value (SIMPLE, MODERATE, COMPLEX, VERY_COMPLEX, CRITICAL)
- `priority`: RequestPriority enum value (CRITICAL, HIGH, MEDIUM, LOW)
- `timeout`: Optional manual timeout in seconds

### Monitoring Endpoints

Access monitoring and statistics via:
- `/api/v1/stats/requests` - Get overall request statistics
- `/api/v1/stats/request/{request_id}` - Get individual request details
- `/api/v1/stats/health` - Get system health metrics

## Architecture

### Components

1. **SmartRequestMiddleware**: FastAPI middleware that handles all incoming requests
2. **RequestTracker**: Tracks and manages request status and statistics
3. **RequestQueue**: Prioritizes and batches requests
4. **CircuitBreaker**: Prevents calls to failing services

### Request Lifecycle

1. **Classification**: Analyze request to determine complexity and priority
2. **Tracking**: Register request in the tracking system
3. **Processing**: Process request with appropriate timeout and error handling
4. **Statistics**: Update statistics and monitoring data
5. **Response**: Return result to client with tracking information

## Performance Impact

Smart Request Handling significantly improves system performance:
- Reduced timeouts for simpler requests
- Better handling of concurrent requests
- Increased overall throughput
- Improved system stability under load

## Example

An example of an endpoint using smart request handling:

```python
@router.post("/analyze", response_model=ATSAnalysisResponse)
@smart_request(complexity=TaskComplexity.MODERATE, priority=RequestPriority.HIGH)
async def analyze_resume(
    analysis_request: ATSAnalysisRequest,
    db: Session = Depends(get_db),
    request_id: str = None  # Added for smart request handling
):
    # Function implementation
    
    # Log request with detailed information for monitoring
    logfire.info(
        "Starting analysis with smart request handling",
        request_id=request_id,
        other_metadata=value
    )
    
    # Main processing
    result = await your_processing_function()
    
    # Add request ID to response for tracking
    response = {
        "result": result,
        "request_id": request_id  
    }
    
    return response
```

## Dependencies

- FastAPI for the web framework
- Logfire for logging and monitoring
- Asyncio for asynchronous processing
- Psutil for system metrics