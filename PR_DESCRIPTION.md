# Smart Request Handling Implementation

## Summary

This PR implements a comprehensive smart request handling system that optimizes API requests based on complexity, priority, and resource requirements. The system significantly enhances the performance, reliability, and cost-effectiveness of API requests, particularly for AI-intensive endpoints.

## Key Features

- **Request Classification**: Automatically categorizes requests by complexity and priority
- **Dynamic Timeouts**: Sets timeouts based on request complexity and historical performance
- **Priority Queuing**: Ensures critical requests are processed first during high load
- **Circuit Breaker Pattern**: Prevents cascading failures when services are degraded (with thread safety)
- **Comprehensive Monitoring**: Tracks request status, duration, and resource usage
- **Resource Optimization**: Distributes load to prevent system overload

## Implementation Details

The implementation includes:

1. **Core Components**:
   - `SmartRequestMiddleware`: FastAPI middleware for global request handling
   - `RequestTracker`: Tracks request status, duration, and statistics (thread-safe)
   - `RequestQueue`: Prioritizes and batches requests based on importance
   - `CircuitBreaker`: Thread-safe implementation to prevent calls to failing services

2. **Decorator API**:
   - `@smart_request` decorator for simple integration with existing endpoints
   - Configurable complexity and priority levels
   - Automatic request ID generation and tracking

3. **Monitoring Endpoints**:
   - `/api/v1/stats/requests`: Overall request statistics
   - `/api/v1/stats/request/{request_id}`: Individual request details
   - `/api/v1/stats/health`: System health metrics

4. **Testing and Demo Utilities**:
   - Integration tests to verify functionality
   - Demo script for showcasing capabilities

## Performance Benefits

- **Reduced Timeouts**: Dynamic timeout adjustment based on request complexity
- **Improved Stability**: Thread-safe circuit breaker prevents cascading failures
- **Better Prioritization**: Critical user-facing requests processed first
- **Resource Efficiency**: Batching and queuing reduce overall system load
- **Enhanced Monitoring**: Detailed metrics for performance optimization
- **Thread Safety**: All components are thread-safe for concurrent request handling

## Files Changed

- New Files:
  - `/app/services/smart_request_handler.py`: Core implementation
  - `/app/services/README_SMART_REQUEST.md`: Documentation
  - `/tests/integration/test_smart_request.py`: Integration tests
  - `/scripts/demo_smart_request.py`: Demo utility

- Modified Files:
  - `/app/api/endpoints/ats.py`: Added smart request decorator
  - `/app/api/endpoints/stats.py`: Added monitoring endpoints
  - `/app/schemas/ats.py`: Updated for request tracking
  - `/main.py`: Initialized smart request middleware
  - `/pyproject.toml`: Added dependencies
  - `/requirements-cli.txt`: Added demo dependencies
  - `/app/api/api.py`: Added support for smart request handling

## Breaking Changes

None. The implementation is backward compatible and only enhances existing endpoints.

## Future Enhancements

- Rate limiting per user/client
- Machine learning for predicting optimal timeouts
- More sophisticated load balancing strategies
- Enhanced caching for repeated requests

## How to Use

### Basic Usage (Automatic)

The middleware automatically handles requests to configured endpoints.

### Decorator Usage (Explicit)

```python
from app.services.smart_request_handler import smart_request, TaskComplexity, RequestPriority

@router.post("/analyze")
@smart_request(complexity=TaskComplexity.MODERATE, priority=RequestPriority.HIGH)
async def analyze_data(request_data: AnalysisRequest, request_id: str = None):
    # Your implementation here
    return {"result": result, "request_id": request_id}
```

### Monitoring

Access the monitoring dashboard at `/api/v1/stats/requests` (requires admin privileges).

## Testing

Run the tests with:
```
pytest tests/integration/test_smart_request.py -v
```

Run the demo with:
```
python scripts/demo_smart_request.py --show-stats
```

## Related Issues

Resolves #8