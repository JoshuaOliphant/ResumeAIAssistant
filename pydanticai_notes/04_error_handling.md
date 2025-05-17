# Error Handling and Timeouts in PydanticAI

Proper error handling is critical for building robust AI-powered applications, especially when dealing with external API calls that may fail or take too long.

## Common Error Types

When working with PydanticAI, you might encounter these types of errors:

1. **ConnectionErrors**: Network-related issues when connecting to the AI provider
2. **TimeoutErrors**: Requests that take too long to complete
3. **AuthenticationErrors**: Issues with API keys or authentication
4. **ValidationErrors**: Generated content doesn't match the output schema
5. **RateLimitErrors**: Provider rate limits exceeded
6. **ContentFilterErrors**: Content flagged as inappropriate by the provider

## Timeout Management

PydanticAI allows setting timeouts to prevent requests from hanging indefinitely:

```python
agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=MyModel
)

# Set timeout when calling run
result = await agent.run(prompt, timeout=60)  # Timeout in seconds
```

This is particularly important for resume customization, where previous issues included API calls hanging.

## Comprehensive Error Handling

A comprehensive approach to error handling includes:

```python
async def safe_agent_execution(agent, prompt, fallback_result=None):
    """Execute an agent with robust error handling."""
    try:
        # Attempt to run the agent
        result = await agent.run(prompt, timeout=60)
        return result
    except TimeoutError as e:
        logfire.error(f"Agent execution timed out: {str(e)}")
        # Handle timeout specifically
        return fallback_result or handle_timeout()
    except ValidationError as e:
        logfire.error(f"Output validation failed: {str(e)}")
        # Handle validation failure - could retry with modified prompt
        return fallback_result or handle_validation_error(e)
    except AuthenticationError as e:
        logfire.error(f"Authentication error: {str(e)}")
        # Critical error - notify administrators
        notify_admin("Authentication error with AI provider")
        raise  # Re-raise as this needs immediate attention
    except Exception as e:
        logfire.error(f"Unexpected error during agent execution: {str(e)}")
        # Generic fallback
        return fallback_result or handle_generic_error()
```

## Circuit Breaker Pattern

For even more robust error handling, the circuit breaker pattern prevents cascading failures:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=3, reset_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_failure_time = None
    
    async def execute(self, func, *args, **kwargs):
        """Execute a function with circuit breaker protection."""
        # Check if circuit is OPEN
        if self.state == "OPEN":
            # Check if reset timeout has elapsed
            if self.last_failure_time and time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF-OPEN"
                logfire.info("Circuit breaker transitioning from OPEN to HALF-OPEN")
            else:
                # Circuit is still OPEN
                logfire.warn("Circuit breaker is OPEN - failing fast")
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            # Execute the function
            result = await func(*args, **kwargs)
            
            # If HALF-OPEN and successful, reset
            if self.state == "HALF-OPEN":
                self.reset()
                logfire.info("Circuit breaker reset to CLOSED after successful execution")
            
            return result
        except Exception as e:
            # Record failure
            self.record_failure()
            logfire.error(f"Circuit breaker recorded failure: {str(e)}")
            
            # Check if threshold exceeded
            if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_failure_time = time.time()
                logfire.warn(f"Circuit breaker transitioned to OPEN after {self.failure_count} failures")
            
            # Re-raise the exception
            raise
    
    def record_failure(self):
        """Record a failure and update state."""
        self.failure_count += 1
        self.last_failure_time = time.time()
    
    def reset(self):
        """Reset the circuit breaker."""
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None

# Usage with PydanticAI
circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=300)

async def execute_agent_with_circuit_breaker(agent, prompt):
    try:
        return await circuit_breaker.execute(agent.run, prompt)
    except CircuitBreakerOpenError:
        # Handle circuit breaker open - use fallback or inform user
        return {"error": "Service temporarily unavailable, please try again later"}
    except Exception as e:
        # Handle other exceptions
        return {"error": f"Error processing request: {str(e)}"}
```

## Application to Resume Customization

For resume customization, implement timeout and error handling at each workflow stage:

```python
# In resume_customizer.py
async def _evaluate_resume_job_match(self, resume_content, job_description):
    """Evaluate how well the resume matches the job description."""
    try:
        # Create evaluation agent with appropriate timeout
        agent = await self.agent_factory.create_agent(
            output_schema=ResumeEvaluation,
            system_prompt="...",
        )
        
        # Run evaluation with timeout
        evaluation_result = await self.agent_factory.run_agent(
            agent,
            "Evaluate the resume against the job description",
            timeout=60  # Reasonable timeout for evaluation
        )
        
        return evaluation_result
    except TimeoutError:
        logfire.error("Resume evaluation timed out")
        # Create a basic evaluation to allow the process to continue
        return create_basic_evaluation(resume_content, job_description)
    except Exception as e:
        logfire.error(f"Resume evaluation failed: {str(e)}")
        raise EvaluationError(f"Failed to evaluate resume: {str(e)}")
```

Using these error handling techniques will dramatically improve the reliability of the resume customization service.