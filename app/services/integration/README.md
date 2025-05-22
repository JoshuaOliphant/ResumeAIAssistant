# Integration Framework for ResumeAIAssistant

This directory contains the integration framework that unifies the four key components of the ResumeAIAssistant system:

1. **Micro-Task Orchestration Framework**
2. **Resume Section Analyzer Framework**
3. **Key Requirements Extractor**
4. **Smart Request Chunking System**

## Integration Architecture

The integration framework provides standardized interfaces and implementations that connect these components while maintaining loose coupling and high cohesion. This architecture ensures that components can evolve independently while still functioning together seamlessly.

```
┌───────────────────────┐
│                       │
│  API Endpoints        │
│  (customize.py)       │
│                       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐       ┌───────────────────────┐
│                       │       │                       │
│  Enhanced             │◀──────▶  Key Requirements     │
│  Customization        │       │  Extractor            │
│  Service              │       │                       │
│                       │       └───────────────────────┘
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│                       │
│  Micro-Task           │
│  Orchestration        │
│                       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐       ┌───────────────────────┐
│                       │       │                       │
│  Smart Request        │◀──────▶  Resume Section       │
│  Chunking System      │       │  Analyzers            │
│                       │       │                       │
└───────────────────────┘       └───────────────────────┘
```

## Key Components

### 1. Unified Interfaces (`interfaces.py`)

Defines the core interfaces that all integrated components must implement:

- `Task` - Base interface for all tasks in the system
- `TaskOrchestrator` - Manages task execution with dependencies
- `ProgressTracker` - Tracks and reports operation progress
- `ErrorHandler` - Provides error recovery mechanisms
- `CircuitBreaker` - Implements service protection patterns
- `SectionAnalyzer` - Interface for resume section analyzers
- `RequirementsExtractor` - Interface for extracting job requirements
- `ContentChunkingService` - Interface for content chunking

### 2. Task Orchestration (`orchestrator.py`)

Implements the `TaskOrchestrator` interface using the parallel processor architecture:

- `IntegratedTaskOrchestrator` - Main orchestrator implementation
- `OrchestratorTask` - Task implementation that integrates with the orchestrator

### 3. Progress Tracking (`progress_tracking.py`)

Implements the `ProgressTracker` interface for real-time progress updates:

- `IntegratedProgressTracker` - Tracks progress across multi-stage operations
- `ProgressStageModel` - Represents a stage in processing with its own progress

### 4. Error Handling (`error_handling.py`)

Implements error handling and recovery mechanisms:

- `IntegratedErrorHandler` - Handles errors with appropriate recovery strategies
- `IntegratedCircuitBreaker` - Protects system from cascading failures
- `RecoveryStrategy` - Base class for error recovery strategies
- `PartialResultsHandler` - Assembles best results when some tasks fail

### 5. Section Analyzer Integration (`section_analyzer.py`)

Integrates specialized section analyzers:

- `IntegratedSectionAnalyzer` - Wraps base analyzers with the unified interface
- `SectionAnalyzerFactory` - Creates appropriate analyzers for section types

### 6. Requirements Extractor (`requirements_extractor.py`) 

Integrates the key requirements extractor:

- `IntegratedRequirementsExtractor` - Wraps the requirements extraction functionality
- `MockRequirementsExtractor` - Provides fallback functionality for testing

### 7. Content Chunking (`content_chunking.py`)

Implements intelligent content chunking:

- `IntegratedContentChunker` - Chunks content based on section type and constraints
- Specialized chunking strategies for different resume sections

## Usage Examples

### Task Orchestration

```python
# Create orchestrator
orchestrator = IntegratedTaskOrchestrator()

# Create tasks
task_a = OrchestratorTask("analyze_requirements")
task_b = OrchestratorTask("analyze_resume")
task_c = OrchestratorTask("generate_plan", Priority.HIGH)

# Add tasks with dependencies
await orchestrator.add_task(task_a)
await orchestrator.add_task(task_b)
await orchestrator.add_task(task_c, dependencies=[task_a.id, task_b.id])

# Execute all tasks respecting dependencies
results = await orchestrator.execute_all(context={"job_id": "12345"})
```

### Section Analysis

```python
# Create analyzer for experience section
analyzer = SectionAnalyzerFactory.create_analyzer(
    SectionType.EXPERIENCE, 
    customization_level="extensive"
)

# Analyze section
result = await analyzer.analyze(
    section_content="Experience section content...",
    job_requirements=extracted_requirements,
    context={"resume_id": "12345"}
)
```

### Content Chunking

```python
# Create content chunker
chunker = IntegratedContentChunker(default_max_chunk_size=8000)

# Chunk content
chunks = chunker.chunk_content(
    content=large_section_content,
    section_type=SectionType.EXPERIENCE
)

# Process chunks and combine results
chunk_results = []
for chunk in chunks:
    result = await process_chunk(chunk)
    chunk_results.append(result)
    
combined_result = chunker.combine_results(chunk_results)
```

## Testing

Unit and integration tests are provided in the `tests/integration/test_integration_components.py` file to ensure proper functionality of all integrated components.

## Error Handling Strategy

The integration framework includes robust error handling with:

1. **Circuit Breakers**: Automatically detect failing services and prevent cascading failures
2. **Retry Strategies**: Automatically retry failed operations with exponential backoff
3. **Fallback Implementations**: Provide degraded but functional service when primary methods fail
4. **Partial Results**: When some parts of an operation fail, still return useful partial results

## Progress Tracking

Real-time progress tracking is implemented with WebSocket updates to keep users informed during long-running operations. The progress tracker breaks operations into logical stages and provides estimated completion times.

## Extending the Framework

To add new components to the integration framework:

1. Define a new interface in `interfaces.py` if needed
2. Implement the interface with an integrated wrapper class
3. Create any necessary factory methods
4. Add tests for the new component
5. Update this README with usage examples