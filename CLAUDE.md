# CLAUDE.md - Guidelines for ResumeAI Assistant

## Backend Development
- Setup: `uv sync` (installs from pyproject.toml)
- Run unit tests: `uv run pytest tests/unit`
- This project uses `uv`, not `pip` for dependency management.
- Add new dependencies with `uv add <dependency-name>`.
- This project has a virtual environment that needs to be sourced.
- After sourcing the virtual environment, `uv sync` can be used to sync the dependencies.
- Use uv to start the application with `uv run uvicorn main:app --host 0.0.0.0 --port 5001 --reload`
- Always source the virtual environment and use `uv sync` to install existing dependencies in pyproject.toml. If you need to install a new dependency, use `uv add`, never use pip.

## Resume Customization Workflow

This document defines guidelines for Claude Code when customizing resumes for the ResumeAI Assistant application.

### Architecture Principles

1. Follow the evaluator-optimizer workflow pattern:
   - First evaluate the match between resume and job description
   - Then optimize the resume based on evaluation findings
   - Verify that optimizations maintain truthfulness

2. Use parallelization through resume section decomposition:
   - Process different resume sections independently
   - Coordinate results through centralized evidence tracking

3. Use strict verification protocols:
   - Never fabricate experiences, skills, or achievements
   - Only reorganize and reframe existing content
   - Track all changes with evidence from original resume

### File Outputs

When running resume customization, generate and output these files:

1. `new_customized_resume.md`: The final customized resume in Markdown format
2. `customized_resume_output.md`: A detailed change summary including:
   - Before/after match scores
   - Key changes made with evidence sources
   - Remaining gaps between resume and job requirements
   - Interview preparation suggestions

3. Intermediate analysis files:
   - `job_analysis.json`: Structured analysis of job requirements
   - `resume_parsed.json`: Structured extraction of resume content
   - `evidence_tracker.json`: Database of verified information
   - `match_evaluation.json`: Analysis of resume-job fit with scores
   - `enhancement_plan.md`: Prioritized plan for resume improvements
   - `verification_results.json`: Verification of final customization

### Verification Rules

Follow these strict rules for truthfulness verification:

1. **Acceptable Without Verification**:
   - Reorganizing existing content
   - Rephrasing for clarity/impact
   - Highlighting relevant parts of verified experience

2. **Requiring Explicit Verification**:
   - Any quantitative metrics or percentages
   - Specific technical skills not in original resume
   - Project details not in original resume
   - Leadership roles or responsibilities

3. **Verification Sources**:
   - Original resume (primary source)
   - LinkedIn profile (if provided)
   - GitHub repositories (if provided)
   - Personal website (if provided)
   - Company websites describing work (if provided)

4. **Never Permitted**:
   - Fabricating experiences or achievements
   - Adding unverified skills
   - Exaggerating metrics or impact
   - Creating fictional projects

### Implementation Guidelines

1. For job_analysis.json schema:
   ```json
   {
     "required_skills": [
       {"skill": "Python", "confidence": 0.9},
       {"skill": "Leadership", "confidence": 0.7}
     ],
     "preferred_skills": [
       {"skill": "Machine Learning", "confidence": 0.8}
     ],
     "company_values": ["Innovation", "Collaboration"],
     "industry_terminology": ["AI", "Machine Learning"],
     "technologies_mentioned": ["Python", "TensorFlow"],
     "key_responsibilities": ["Build APIs", "Lead team"]
   }
   ```

2. For evidence_tracker.json schema:
   ```json
   {
     "verified_skills": [
       {"skill": "Python", "source": "Original resume", "confidence": 1.0}
     ],
     "verified_experiences": [
       {"company": "Example Corp", "achievements": [
         {"achievement": "Led team of 5 developers", "source": "Original resume"}
       ]}
     ],
     "verified_projects": [...],
     "job_requirements": [
       {"requirement": "Python experience", "matched": true, "source": "Original resume"}
     ]
   }
   ```

3. For match_evaluation.json schema:
   ```json
   {
     "match_score": 75,
     "skills_match": {
       "score": 80,
       "strong_matches": ["Python", "Leadership"],
       "weak_matches": ["Data Science"],
       "gaps": ["Machine Learning"]
     },
     "experience_match": {
       "score": 70,
       "strong_points": ["5+ years experience", "Team leadership"],
       "improvement_areas": ["Domain-specific experience"]
     },
     "enhancement_opportunities": [
       {
         "area": "Skills Section",
         "recommendation": "Highlight Python expertise",
         "priority": "High"
       }
     ]
   }
   ```

### Code Style and Format

1. Output files should follow these guidelines:
   - JSON files should be properly formatted with indentation
   - Markdown files should use standard Markdown syntax
   - Use consistent formatting throughout all outputs

2. Customized resume should:
   - Maintain professional formatting
   - Use clear section headers
   - Include all expected resume sections
   - Be optimized for ATS compatibility

## Project Planning
- Project planning is documented in `planning_scratchpad.md`
- Issues are organized into epics in GitHub
- Critical issues are addressed sequentially to keep efforts focused
- Each issue has clear sections for description, tasks, dependencies, and estimates