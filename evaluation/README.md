# Resume Optimization Evaluation Framework

This framework provides systematic evaluation capabilities for the resume optimization system, enabling automated testing, prompt improvement, and performance monitoring.

## Overview

The evaluation framework is designed to:
- Test accuracy of job requirement parsing
- Verify truthfulness of resume optimizations
- Assess quality of generated content
- Measure relevance improvements
- Enable systematic prompt optimization

## Directory Structure

```
evaluation/
├── __init__.py              # Main package initialization
├── config.py                # Configuration management
├── README.md               # This file
├── test_data/              # Test data management
│   ├── __init__.py
│   ├── models.py           # Pydantic models for test data
│   └── loaders.py          # Data loading utilities
├── evaluators/             # Evaluation components
│   ├── __init__.py
│   ├── base.py             # Base evaluator class
│   ├── accuracy.py         # Accuracy evaluators
│   └── quality.py          # Quality evaluators
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

## Dependencies

- **pydantic-ai**: Core evaluation framework
- **pytest-asyncio**: Async testing support  
- **pyyaml**: YAML data format support
- **aiofiles**: Async file operations

## Development Status

This is the initial setup for the evaluation framework. Individual evaluators will be implemented in subsequent issues:

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

# Run with async support
pytest tests/unit/test_evaluation_framework.py -v --asyncio-mode=auto
```

## Contributing

When adding new evaluators:

1. Extend the `BaseEvaluator` class
2. Implement the `evaluate()` method
3. Add appropriate test cases
4. Update the main `__init__.py` imports
5. Document the evaluator's purpose and metrics

## License

Part of the ResumeAI Assistant project.