# Resume Optimization Evaluation Framework Specification

## Overview

This specification outlines a systematic evaluation framework for improving the resume optimization prompts in `haiku_resume_optimizer.py` using PydanticAI's evaluation patterns. The goal is to create an automated feedback loop that continuously improves prompt quality through structured testing and refinement.

## Core Evaluation Dimensions

### 1. Accuracy
- **Definition**: Does the method correctly extract and identify information from inputs?
- **Measurement**: Precision/recall against ground truth annotations
- **Application**: Job requirement extraction, resume parsing, skill identification

### 2. Completeness
- **Definition**: Are important elements or requirements missed in the analysis?
- **Measurement**: Coverage metrics, missing element detection
- **Application**: Ensuring all job requirements are captured, no resume sections ignored

### 3. Truthfulness
- **Definition**: Are optimizations based solely on verifiable original content?
- **Measurement**: Factual accuracy verification, fabrication detection
- **Application**: Preventing addition of unverified skills, experiences, or achievements

### 4. Relevance
- **Definition**: Do changes actually improve the resume-job match score?
- **Measurement**: Before/after match score improvements, keyword alignment
- **Application**: Validating that optimizations target the right areas

### 5. Quality
- **Definition**: Is the output professional, readable, and ATS-compatible?
- **Measurement**: Human evaluation scores, readability metrics
- **Application**: Ensuring optimized content maintains professional standards

## Method-Specific Evaluation Plans

### `parse_job_requirements()` Evaluation

**Test Case Categories:**
- **Simple Requirements**: Clear, explicit skill lists and experience requirements
- **Complex Requirements**: Multiple skill categories, implicit requirements, industry jargon
- **Ambiguous Requirements**: Conflicting information, unclear priority levels
- **Edge Cases**: No explicit requirements, overly detailed descriptions

**Evaluation Metrics:**
- Precision/recall on required vs preferred skills classification
- Accuracy of confidence score assignments (0.6-1.0 range)
- Completeness of technology stack extraction
- Proper categorization of years of experience

**Ground Truth Creation:**
- Manual annotation of 50+ diverse job descriptions
- Expert validation of skill categorization
- Confidence score calibration against recruiter assessments

### `evaluate_match()` Evaluation

**Test Case Categories:**
- **Perfect Matches**: Resume exactly matches job requirements
- **Clear Mismatches**: Major skill gaps, insufficient experience
- **Transferable Skills**: Azure→AWS, similar frameworks, related technologies
- **Experience Level Misalignment**: Over/under qualified candidates

**Evaluation Metrics:**
- Correlation with human expert match scores
- Consistency across similar candidate profiles
- Accuracy of skill gap identification
- Reliability of transferable skill recognition

**Validation Approach:**
- Compare against hiring manager assessments
- Test score stability with minor resume variations
- Validate transferable skill mappings with industry experts

### `optimize_section()` Evaluation

**Test Case Categories:**
- **Minor Optimizations**: Sections needing keyword emphasis, reordering
- **Major Restructuring**: Sections requiring significant reorganization
- **Truthfulness Boundaries**: Content at the edge of acceptable enhancement
- **No-Change Cases**: Already optimal sections that shouldn't be modified

**Evaluation Metrics:**
- Improvement in keyword density and relevance
- Maintenance of factual accuracy (truthfulness score)
- Professional quality assessment (human evaluation)
- ATS compatibility score

**Quality Assurance:**
- Professional resume writer evaluations
- ATS parsing verification
- Before/after readability comparisons

## Test Dataset Strategy

### Dataset Composition

**Job Description Variety:**
- **Technical Roles**: Software engineering, data science, DevOps, cybersecurity
- **Management Positions**: Team leads, project managers, technical directors
- **Industry Variations**: Startups, enterprise, consulting, government
- **Experience Levels**: Entry-level, mid-career, senior, executive

**Resume Diversity:**
- **Career Stages**: New graduates, career changers, experienced professionals
- **Background Types**: Traditional paths, non-traditional backgrounds, career gaps
- **Skill Profiles**: Deep specialists, generalists, emerging skill sets
- **Geographic Variations**: Different regional job market expectations

### Ground Truth Creation

**Expert Annotations:**
- Professional recruiters evaluate resume-job matches
- Industry experts validate skill categorizations
- Resume writers assess optimization quality
- ATS specialists verify parsing accuracy

**Known Good/Bad Examples:**
- Curated pairs of resumes and jobs with known match scores
- Examples of excellent vs poor optimizations
- Documented failure cases with root cause analysis

## Iterative Improvement Process

### Phase 1: Baseline Evaluation
1. Run comprehensive evaluation on current prompts
2. Identify systematic failure patterns and biases
3. Categorize errors by type and frequency
4. Establish performance benchmarks

### Phase 2: Prompt Engineering
1. Analyze failure modes to understand root causes
2. Design targeted improvements for specific weaknesses
3. Update few-shot examples with successful/failure cases
4. Refine system prompts and instructions

### Phase 3: A/B Testing
1. Compare prompt variations against baseline
2. Measure improvements across all evaluation dimensions
3. Test for unintended side effects or regressions
4. Validate improvements with held-out test set

### Phase 4: Continuous Monitoring
1. Monitor performance on new resume/job combinations
2. Detect performance drift or emerging failure patterns
3. Automatically trigger re-evaluation when needed
4. Update training examples with new edge cases

## Implementation Architecture

### Core Components

**Evaluation Engine:**
- PydanticAI Dataset and Case structures
- Custom evaluators for each quality dimension
- Parallel evaluation execution for efficiency
- OpenTelemetry integration for detailed tracing

**Test Data Management:**
- YAML/JSON serialization for test cases
- Version control for dataset evolution
- Metadata tracking for test case provenance
- Easy addition of new test scenarios

**Prompt Optimization Loop:**
- Automated experiment tracking
- Performance comparison across prompt versions
- Statistical significance testing
- Automated rollback for performance regressions

### Integration Points

**Existing Codebase:**
- Minimal changes to `HaikuResumeOptimizer` class
- Wrapper functions for evaluation harness
- Configurable prompt injection for A/B testing
- Logging integration for performance monitoring

**Development Workflow:**
- Pre-commit hooks for evaluation on prompt changes
- CI/CD integration for continuous testing
- Dashboard for monitoring prompt performance trends
- Alerts for significant performance degradations

## Success Metrics

### Quantitative Goals
- **Accuracy Improvement**: 15% reduction in parsing errors
- **Match Score Reliability**: 90% correlation with human expert scores
- **Truthfulness Maintenance**: <1% fabrication rate in optimizations
- **Quality Consistency**: 95% of outputs meet professional standards

### Qualitative Outcomes
- More reliable skill gap identification
- Better preservation of candidate authenticity
- Improved optimization targeting
- Reduced manual review requirements

## Risk Mitigation

### Potential Issues
- **Overfitting**: Optimizing for test cases rather than real-world performance
- **Evaluation Bias**: Test cases not representative of actual usage
- **Quality Regression**: Improvements in one area causing degradation in others
- **Cost Management**: Evaluation overhead impacting development velocity

### Mitigation Strategies
- Regular test set refresh with new real-world examples
- Multiple independent evaluation approaches
- Comprehensive regression testing across all dimensions
- Efficient evaluation strategies to minimize API costs

## Future Extensions

### Advanced Capabilities
- **Multi-Model Comparison**: Evaluate different Claude models systematically
- **Dynamic Prompt Generation**: Use LLMs to generate improved prompts
- **Personalization**: Adapt prompts based on specific industries or roles
- **Real-Time Learning**: Incorporate user feedback for continuous improvement

### Integration Opportunities
- **Human-in-the-Loop**: Incorporate expert feedback into evaluation
- **Active Learning**: Identify and prioritize uncertain cases for manual review
- **Federated Learning**: Share improvements across different resume optimization instances