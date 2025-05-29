# Test Datasets Documentation

This directory contains curated test datasets for evaluating resume-job matching algorithms.

## Overview

The test datasets provide diverse resume-job pairs with ground truth annotations to evaluate the accuracy and effectiveness of matching algorithms. Each test case includes:

- Resume content
- Job description
- Expected match score
- Ground truth annotations explaining the match rationale
- Key skills and technologies identified

## Dataset Structure

### Main Dataset: `curated_test_dataset.yaml`

The main curated dataset contains 15 test cases covering various scenarios:

#### Test Case Categories

1. **Perfect Matches (90-100%)**
   - `test_001`: Senior Software Engineer - exact skills match
   - `test_007`: Full Stack Developer - balanced frontend/backend skills
   - `test_013`: Junior DevOps Engineer - recent graduate perfect fit

2. **Good Matches (70-89%)**
   - `test_002`: Junior Developer - growth potential
   - `test_005`: DevOps Engineer - strong infrastructure skills
   - `test_009`: Backend Developer - missing some specific technologies
   - `test_010`: Bootcamp Graduate - entry level match

3. **Partial Matches (50-69%)**
   - `test_003`: Career Transition - Data Analyst to Software Engineer
   - `test_008`: Overqualified - Senior Architect for mid-level position
   - `test_012`: QA to Developer transition

4. **Poor Matches (<50%)**
   - `test_004`: Mobile Developer for Backend position
   - `test_006`: Data Scientist for Frontend role
   - `test_014`: Hardware Engineer for Software role

#### Special Cases

- **Career Transitions**: Test cases showing professionals switching domains
- **Overqualified Candidates**: Senior professionals applying for junior roles
- **Skills Gaps**: Strong candidates missing specific requirements
- **Wrong Specializations**: Candidates from different technical domains

### YAML Schema

Each test case follows this structure:

```yaml
- id: "unique_test_id"
  name: "Human-readable test name"
  description: "Brief description of the test scenario"
  category: "technical|management|etc"
  difficulty: "easy|medium|hard"
  tags: ["tag1", "tag2"]
  
  resume_content: |
    Full resume text in markdown format
    
  job_description: |
    Complete job description
    
  expected_match_score: 85.0  # 0-100
  expected_skills: ["skill1", "skill2"]
  expected_technologies: ["tech1", "tech2"]
  
  ground_truth:
    match_rationale: "Explanation of why this score is expected"
    strength_areas: ["area1", "area2"]
    gap_areas: ["gap1", "gap2"]
```

## Using the Test Datasets

### Loading Datasets

```python
from evaluation.test_data.loaders import DatasetLoader

# Load the main curated dataset
loader = DatasetLoader()
dataset = loader.load_yaml_dataset("evaluation/test_data/datasets/curated_test_dataset.yaml")

# Access test cases
for test_case in dataset.test_cases:
    print(f"Test: {test_case.name}")
    print(f"Expected Score: {test_case.expected_match_score}")
```

### Validating Datasets

Before using a dataset, validate its structure:

```bash
# Validate from command line
python evaluation/test_data/validation/dataset_validator.py evaluation/test_data/datasets/curated_test_dataset.yaml

# Validate programmatically
from evaluation.test_data.validation.dataset_validator import DatasetValidator

validator = DatasetValidator()
is_valid, dataset = validator.validate_dataset_file(dataset_path)
validator.print_validation_report()
```

## Creating New Test Cases

When adding new test cases:

1. **Ensure Diversity**: Add cases that cover new scenarios not already represented
2. **Provide Complete Annotations**: Include all ground truth fields
3. **Use Realistic Content**: Resume and job descriptions should be realistic
4. **Document Rationale**: Clearly explain why the expected score is appropriate
5. **Validate**: Run the validator after adding new cases

## Ground Truth Guidelines

### Match Score Ranges

- **90-100%**: Near-perfect match, candidate meets all requirements
- **70-89%**: Good match, missing minor requirements or slightly over/underqualified
- **50-69%**: Partial match, significant gaps but some relevant experience
- **0-49%**: Poor match, wrong domain or missing critical requirements

### Annotation Best Practices

1. **Match Rationale**: Explain the score considering:
   - Required vs nice-to-have skills
   - Years of experience alignment
   - Domain expertise match
   - Educational requirements

2. **Strength Areas**: List candidate's advantages:
   - Matching technical skills
   - Relevant experience
   - Certifications or education
   - Soft skills alignment

3. **Gap Areas**: Identify what's missing:
   - Required skills not present
   - Experience level mismatch
   - Domain knowledge gaps
   - Missing certifications

## Maintenance

- Review and update test cases quarterly
- Add new cases as matching algorithms evolve
- Remove outdated technology references
- Ensure balanced distribution across score ranges

## Contributing

To contribute new test cases:

1. Create test cases following the schema
2. Ensure unique IDs and descriptive names
3. Run validation before submitting
4. Document any special considerations
5. Submit PR with explanation of added value