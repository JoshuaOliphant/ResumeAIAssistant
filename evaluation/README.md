# Resume Optimization Evaluation Framework

This framework provides systematic evaluation capabilities for the resume optimization system, enabling automated testing, prompt improvement, and performance monitoring.

## Overview

The evaluation framework is designed to:
- Test accuracy of job requirement parsing
- Verify truthfulness of resume optimizations
- Assess quality of generated content
- Measure relevance improvements
- Enable systematic prompt optimization
- Support parallel evaluation execution
- Integrate with PydanticAI evaluation capabilities

## Architecture

### Core Components

1. **BaseEvaluator**: Enhanced abstract base class for all evaluators
   - Supports both sync and async evaluation methods
   - Batch evaluation capabilities
   - Resource tracking (tokens, API calls, execution time)

2. **TestRunner**: Orchestrates evaluation execution
   - Parallel execution strategies (asyncio, thread pool, adaptive)
   - Circuit breaker pattern for fault tolerance
   - Progress tracking with ETA calculations
   - Comprehensive error handling and retry logic

3. **Test Data Models**: Structured data for evaluation
   - `TestCase`: Individual test scenarios with validation
   - `EvaluationResult`: Evaluation outcomes with detailed metrics
   - `TestDataset`: Collections of test cases with utility methods

4. **PydanticAI Integration**: Seamless integration with PydanticAI
   - Case/Dataset conversion adapters
   - Custom evaluator wrappers
   - OpenTelemetry/Logfire tracing support

## Directory Structure

```
evaluation/
├── __init__.py              # Main package initialization
├── config.py                # Configuration management
├── README.md               # This file
├── test_runner.py          # TestRunner orchestration
├── runner_config.py        # Runner configuration options
├── progress.py             # Progress tracking with ETA
├── test_data/              # Test data management
│   ├── __init__.py
│   ├── models.py           # Pydantic models for test data
│   └── loaders.py          # Data loading utilities
├── evaluators/             # Evaluation components
│   ├── __init__.py
│   ├── base.py             # Enhanced base evaluator class
│   ├── accuracy.py         # Accuracy evaluators
│   └── quality.py          # Quality evaluators
├── adapters/               # External framework adapters
│   ├── __init__.py
│   └── pydantic_ai.py     # PydanticAI integration
├── results/                # Result processing
│   ├── __init__.py
│   ├── aggregator.py       # Result aggregation
│   ├── reporter.py         # Report generation
│   └── analyzer.py         # Performance analysis
└── utils/                  # Shared utilities
    ├── __init__.py
    ├── config.py           # Configuration helpers
    ├── logger.py           # Logging utilities
    └── helpers.py          # Common helper functions
```

## Configuration

The framework uses environment variables for configuration:

```bash
# Required
export ANTHROPIC_API_KEY="your-api-key"

# Optional
export EVALUATION_MODEL="haiku"
export EVALUATION_LOG_LEVEL="INFO"
export EVALUATION_PARALLEL="true"
export EVALUATION_MAX_WORKERS="5"
```

## Quick Start

### Basic Evaluation

```python
from evaluation import EvaluationConfig, get_evaluation_logger
from evaluation.test_data import TestCase, TestDataset
from evaluation.evaluators import JobParsingAccuracyEvaluator

# Initialize configuration
config = EvaluationConfig()
logger = get_evaluation_logger()

# Create a test case
test_case = TestCase(
    name="Test Job Parsing",
    resume_content="...",
    job_description="...",
    expected_match_score=85.0
)

# Run evaluation
evaluator = JobParsingAccuracyEvaluator()
result = await evaluator.evaluate(test_case, actual_output)

logger.info(f"Evaluation score: {result.overall_score}")
```

### Using TestRunner for Orchestrated Evaluation

```python
from evaluation.test_runner import TestRunner
from evaluation.test_data.models import TestDataset, TestCase
from evaluation.evaluators import MatchScoreEvaluator, TruthfulnessEvaluator
from evaluation.runner_config import get_default_config

# Create test dataset
dataset = TestDataset(name="Resume Optimization Tests")
dataset.add_test_case(TestCase(
    name="Senior Python Developer",
    resume_content="[Resume content...]",
    job_description="[Job description...]",
    expected_match_score=85.0
))

# Initialize evaluators
evaluators = [
    MatchScoreEvaluator(),
    TruthfulnessEvaluator()
]

# Configure and run evaluation
config = get_default_config()
runner = TestRunner(evaluators, config)

# Run evaluation with progress tracking
report = await runner.run_evaluation(dataset)
print(f"Average score: {report.average_score}")
print(f"Success rate: {report.successful_cases}/{report.total_cases}")
```

### Parallel Execution Example

```python
from evaluation.runner_config import TestRunnerConfig, ParallelismStrategy

# Configure for maximum parallelism
config = TestRunnerConfig()
config.parallelism_strategy = ParallelismStrategy.ASYNCIO
config.max_workers = 10
config.resource_limits.max_concurrent_evaluations = 20

runner = TestRunner(evaluators, config)
report = await runner.run_evaluation(dataset)
```

### PydanticAI Integration Example

```python
from evaluation.adapters import PydanticAIAdapter
from pydantic_evals import MatchAnswer

# Create adapter
adapter = PydanticAIAdapter()

# Wrap PydanticAI evaluator
pydantic_eval = MatchAnswer()
wrapped_eval = adapter.create_evaluator_wrapper(
    pydantic_eval, 
    name="match_answer",
    config={"threshold": 0.8}
)

# Use in TestRunner alongside custom evaluators
from evaluation.evaluators.accuracy import JobParsingAccuracyEvaluator

evaluators = [wrapped_eval, JobParsingAccuracyEvaluator()]
runner = TestRunner(evaluators)
```

## Dependencies

- **pydantic-ai**: Core evaluation framework
- **pytest-asyncio**: Async testing support  
- **pyyaml**: YAML data format support
- **aiofiles**: Async file operations

## Development Status

### Completed Components

- ✅ **Phase 1.1**: Evaluation configuration and logging setup (Issue #106)
- ✅ **Phase 1.2**: Basic test data models (Issue #107)
- ✅ **Phase 2.1**: Basic evaluator infrastructure (Issue #109)
  - Enhanced BaseEvaluator with sync/async support
  - TestRunner with parallel execution
  - Progress tracking with ETA
  - PydanticAI integration adapter
  - Comprehensive error handling

### Upcoming Components

Individual evaluators will be implemented in subsequent issues:

- Issue #110: JobParsingAccuracyEvaluator
- Issue #111: MatchScoreEvaluator  
- Issue #112: TruthfulnessEvaluator
- Issue #113: ContentQualityEvaluator
- Issue #114: RelevanceImpactEvaluator
- Issue #115: Integration pipeline

## Testing

Run tests with:

```bash
# Run all evaluation framework tests
pytest tests/unit/test_evaluation_framework.py

# Run evaluator infrastructure tests
pytest tests/unit/test_evaluator_infrastructure.py

# Run all evaluation tests with async support
pytest tests/unit/test_evaluation*.py -v --asyncio-mode=auto

# Run with coverage
pytest tests/unit/test_evaluation*.py --cov=evaluation --cov-report=html
```

## Contributing

When adding new evaluators:

1. Extend the `BaseEvaluator` class
2. Implement the async `evaluate()` method
3. Consider implementing `evaluate_batch()` for efficiency
4. Add resource tracking (tokens, API calls, execution time)
5. Create comprehensive test cases
6. Update the main `__init__.py` imports
7. Document the evaluator's purpose and metrics

When using the TestRunner:

1. Configure parallelism based on evaluator type (I/O vs CPU bound)
2. Set appropriate resource limits to avoid rate limiting
3. Use circuit breakers for unreliable evaluators
4. Enable progress tracking for long-running evaluations
5. Test with both sync and async execution modes

## License

Part of the ResumeAI Assistant project.