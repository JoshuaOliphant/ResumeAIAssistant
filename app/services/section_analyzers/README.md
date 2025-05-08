# Specialized Resume Section Analyzers

This module implements specialized analyzers for different resume sections to provide more detailed and focused analysis of resumes against job descriptions. Each analyzer focuses on a specific aspect of the resume, allowing for more targeted recommendations and customization.

## Architecture

The section analyzers use a modular design based on a common interface defined in `base.py`. The architecture follows these key principles:

1. **Specialized Analysis**: Each analyzer focuses on a specific section or aspect of the resume
2. **Common Interface**: All analyzers implement the same base interface for consistency
3. **Model-Agnostic**: Analyzers work with different AI models through the model selector
4. **Parallel Execution**: Analyzers can run in parallel for better performance
5. **Synthesis Mechanism**: Results from all analyzers are combined into unified recommendations

## Available Analyzers

### Skills and Qualifications Analyzer
- Analyzes skills and qualifications section of resumes
- Identifies matching skills between resume and job description
- Finds missing skills required by the job
- Categorizes skills by type (technical, soft, domain-specific, etc.)
- Provides recommendations for improving skills presentation

### Experience Alignment Analyzer
- Analyzes professional experience sections
- Evaluates relevance of experience to job requirements
- Identifies experience gaps compared to job requirements
- Suggests ways to better highlight relevant experience
- Recommends terminology alignment for better ATS matching

### Education and Certification Analyzer
- Analyzes education and certification sections
- Evaluates relevance of qualifications to job requirements
- Identifies education/certification gaps
- Suggests ways to better highlight relevant qualifications
- Recommends mentioning relevant coursework or academic projects

### Achievement Quantification Analyzer
- Analyzes achievement statements throughout the resume
- Identifies quantified and unquantified achievements
- Evaluates impact and relevance of achievements
- Suggests ways to better quantify achievements with metrics
- Recommends strengthening achievement statements

### Language and Tone Optimizer
- Analyzes language and tone used throughout the resume
- Evaluates action verb usage and effectiveness
- Assesses language alignment with industry terminology
- Identifies passive voice and weak language patterns
- Recommends more impactful phrasing and terminology

## Integration

The section analyzers are integrated with the existing resume customization system through the `SectionAnalysisService`, which:

1. Orchestrates running multiple analyzers in parallel
2. Combines results using the `ResumeAnalysisSynthesizer`
3. Converts the combined analysis to a `CustomizationPlan` compatible with the existing system

The existing `CustomizationService` has been updated to use the section analyzers when generating customization plans, while maintaining backward compatibility through a feature flag.

## Usage

### Direct Usage

```python
from app.services.section_analyzers.skills_analyzer import SkillsQualificationsAnalyzer
from app.schemas.customize import CustomizationLevel

# Create analyzer
analyzer = SkillsQualificationsAnalyzer(
    customization_level=CustomizationLevel.BALANCED
)

# Run analysis
result = await analyzer.analyze(
    resume_content="...",
    job_description="..."
)

# Process results
for recommendation in result.recommendations:
    print(f"- {recommendation.what}: {recommendation.why}")
```

### Using the Synthesizer

```python
from app.services.section_analyzers.synthesis import ResumeAnalysisSynthesizer
from app.services.section_analyzers.base import SectionType
from app.schemas.customize import CustomizationLevel

# Create synthesizer with specific analyzers
synthesizer = ResumeAnalysisSynthesizer(
    customization_level=CustomizationLevel.BALANCED,
    enabled_analyzers=[
        SectionType.SKILLS,
        SectionType.EXPERIENCE,
        SectionType.EDUCATION
    ]
)

# Run full analysis
result = await synthesizer.analyze_resume(
    resume_content="...",
    job_description="..."
)

# Convert to customization plan
plan = await synthesizer.convert_to_customization_plan(
    combined_result=result,
    resume_content="...",
    job_description="..."
)
```

### Using the Service Layer

```python
from app.services.section_analysis_service import get_section_analysis_service
from app.db.session import get_db
from app.schemas.customize import CustomizationPlanRequest, CustomizationLevel

# Get service
db = next(get_db())
service = get_section_analysis_service(db)

# Create request
request = CustomizationPlanRequest(
    resume_id="...",
    job_description_id="...",
    customization_strength=CustomizationLevel.BALANCED,
    industry="technology"
)

# Generate plan
plan = await service.generate_customization_plan(request)
```

## Performance Considerations

- Each analyzer can be resource-intensive due to the AI model usage
- The synthesizer runs analyzers in parallel to improve performance
- You can selectively enable only the analyzers you need
- Analyzer selection can be based on customization level:
  - Conservative: Skills + Experience
  - Balanced: Skills + Experience + Education + Achievements
  - Extensive: All analyzers including Language/Tone

## Testing

Test coverage for section analyzers includes:
- Unit tests for individual analyzers
- Integration tests for the synthesizer
- End-to-end tests with the section analysis service

Run tests with:
```
python -m pytest tests/integration/test_section_analyzers.py -v
```

## Extending the System

To add a new section analyzer:
1. Create a new class that inherits from `BaseSectionAnalyzer`
2. Implement the required methods (`analyze` and `section_type`)
3. Define the appropriate result schema in `app/schemas/section_analyzers.py`
4. Add the new analyzer to `ResumeAnalysisSynthesizer._create_analyzers`
5. Update tests for the new analyzer

## Future Improvements

Potential areas for enhancement:
- Caching analysis results for better performance
- Implementing more specialized analyzers (projects, publications, etc.)
- Enhanced extraction of sections from unstructured resume formats
- Analyzer selection based on resume content and job requirements
- Progressive enhancement with user feedback