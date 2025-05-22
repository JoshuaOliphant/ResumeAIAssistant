# Analysis of PydanticAI Examples

This document explores insights and patterns from PydanticAI's example applications that are relevant to our resume customization service.

## Weather Agent Example

The Weather Agent example demonstrates several key patterns applicable to our project:

### Multi-Stage Workflow
The weather agent follows a sequential workflow:
1. Convert a location description to geographic coordinates
2. Use the coordinates to fetch weather data
3. Format and present the results

This aligns with our 4-stage resume customization approach.

### Tool Usage
The example shows effective use of tools for external data access:

```python
async def get_lat_lng(
    ctx: RunContext[Deps], location: str
) -> tuple[float, float]:
    """
    Get the latitude and longitude for a location.
    
    Args:
        location: A location like "New York" or "Paris, France"
    
    Returns:
        A tuple of (latitude, longitude)
    """
    # Access dependencies via context
    if not ctx.deps.geocoding_api_key:
        # Fallback when no API key is available
        return DUMMY_COORDS.get(location.lower(), (0, 0))

    # Use external API to get coordinates
    client = ctx.deps.http_client
    url = "https://api.geocoding-service.com/api/geocode"
    response = await client.get(
        url, 
        params={"q": location, "key": ctx.deps.geocoding_api_key}
    )
    
    # Process and return results
    data = response.json()
    return data["results"][0]["geometry"]["lat"], data["results"][0]["geometry"]["lng"]
```

### Error Handling and Fallbacks
The example implements graceful fallbacks when external services are unavailable:

```python
# Fallback when API keys aren't available
if not ctx.deps.api_key:
    # Return dummy data with a note about missing credentials
    return {
        "temp": 72,
        "conditions": "Sunny",
        "note": "⚠️ Using dummy data (missing API credentials)"
    }
```

This is crucial for our service, where we must handle potential API failures.

## Bank Support Example

This example shows how to build a customer support agent with contextual awareness:

### Structured Response Generation
The bank example demonstrates using structured types for standardized responses:

```python
class SupportResponse(BaseModel):
    answer: str = Field(description="Answer to the customer question")
    confidence: int = Field(description="Confidence score (1-100)")
    references: List[str] = Field(description="Reference documents supporting the answer")
    needs_escalation: bool = Field(description="Whether this should be escalated to a human")
```

This is similar to how we'll structure our ResumeEvaluation and ImprovementPlan models.

### Context Management
The example shows managing customer context through a session object:

```python
class CustomerContext:
    def __init__(self, customer_id):
        self.customer_id = customer_id
        self.transaction_history = []
        self.previous_interactions = []
    
    def add_interaction(self, question, answer):
        self.previous_interactions.append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })
```

We can apply this pattern to track customization progress and maintain state across workflow stages.

## RAG (Retrieval-Augmented Generation) Example

The RAG example demonstrates knowledge-base integration, which has parallels to our evidence tracking:

### Knowledge Base Integration
The example shows how to integrate with a vector database for relevant content retrieval:

```python
async def retrieve_relevant_documents(query: str, top_k: int = 3) -> List[str]:
    """
    Retrieve the top-k most relevant documents for a query.
    
    Args:
        query: The search query
        top_k: Number of results to return
        
    Returns:
        List of relevant document contents
    """
    # Convert query to embedding
    embedding = await get_embedding(query)
    
    # Search vector database
    results = vector_db.search(
        embedding,
        top_k=top_k,
        namespace="resume_knowledge"
    )
    
    # Return document contents
    return [doc.page_content for doc in results]
```

We could implement similar functionality for retrieving relevant industry standards or job-specific resume patterns.

### Evidence-Based Responses
The RAG example ensures responses are grounded in retrieved evidence:

```python
@agent.instructions()
def provide_instructions(ctx: RunContext[None]) -> str:
    return """
    Answer questions based ONLY on the provided content.
    If you cannot answer from the provided content, say:
    "I don't have enough information to answer this question."
    
    ALWAYS cite your sources using the document ID.
    """
```

This aligns with our need to ensure truthfulness in resume customizations by grounding changes in evidence from the original resume.

## Chat Application Example

The chat application demonstrates effective progress reporting and streaming:

### Streaming Responses
The example shows how to stream responses for better user experience:

```python
async def stream_response(prompt, chat_history):
    # Create streaming agent
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=str,
        system_prompt="You are a helpful assistant."
    )
    
    # Stream the response
    async for partial_response in agent.run_stream(
        f"Context: {chat_history}\n\nUser: {prompt}"
    ):
        yield partial_response
```

This is similar to how we'll implement real-time progress updates via WebSockets.

### Stateful Chat History
The example demonstrates managing conversation history:

```python
def update_chat_history(chat_history, user_message, assistant_message):
    chat_history.append({"role": "user", "content": user_message})
    chat_history.append({"role": "assistant", "content": assistant_message})
    return chat_history
```

We'll use a similar approach for tracking the state of our 4-stage workflow.

## SQL Generation Example

This example demonstrates using an agent to generate structured output (SQL queries):

### Schema-Based Validation
The example uses schema information to validate generated SQL queries:

```python
async def validate_query(query: str, schema: Dict) -> bool:
    """
    Validate that a SQL query is valid against the provided schema.
    
    Args:
        query: The SQL query to validate
        schema: Database schema information
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Parse the SQL query
        parsed = sqlparse.parse(query)[0]
        
        # Verify tables and columns exist in schema
        tables = extract_tables(parsed)
        columns = extract_columns(parsed)
        
        for table in tables:
            if table not in schema:
                return False
        
        for column, table in columns:
            if table not in schema or column not in schema[table]:
                return False
        
        return True
    except Exception:
        return False
```

We can apply similar validation to ensure our resume customizations maintain required formatting and structure.

## Application to Resume Customization

Based on these examples, we can implement several enhanced features in our service:

1. **Multi-Stage Workflow with Tools**: Like the Weather Agent, implement separate tools for each stage of our workflow.

2. **Structured Response Types**: Like the Bank Support example, use well-defined Pydantic models for each workflow stage.

3. **Evidence-Based Customization**: Like the RAG example, implement evidence tracking to ensure truthfulness in customizations.

4. **Real-Time Progress Streaming**: Like the Chat Application, use WebSockets for real-time progress updates.

5. **Schema Validation**: Like the SQL example, validate that customized resumes maintain proper structure.

Example implementation combining these patterns:

```python
async def customize_resume_with_evidence(resume_content: str, job_description: str):
    # Stage 1: Evaluation (like Weather Agent location lookup)
    evaluation = await evaluate_resume(resume_content, job_description)
    
    # Stage 2: Extract evidence (like RAG document retrieval)
    evidence = await extract_evidence(resume_content)
    
    # Stage 3: Generate improvement plan (like SQL query generation)
    improvement_plan = await generate_improvement_plan(
        resume_content, 
        job_description,
        evaluation,
        evidence
    )
    
    # Stage 4: Implement changes with validation (like SQL validation)
    customized_resume = await implement_customizations(
        resume_content,
        improvement_plan,
        evidence
    )
    
    # Stage 5: Verify changes (like Bank Support confidence scoring)
    verification = await verify_customizations(
        resume_content,
        customized_resume,
        evidence
    )
    
    return {
        "customized_resume": customized_resume,
        "evaluation": evaluation,
        "improvement_plan": improvement_plan,
        "verification": verification
    }
```

By incorporating these patterns from the PydanticAI examples, we can build a more robust, maintainable, and effective resume customization service.