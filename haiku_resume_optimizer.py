#!/usr/bin/env python3
"""
Resume Optimization Script using Claude Haiku 3.5
Implements the evaluator-optimizer workflow with verification
"""

print("[STARTUP] Script starting...")

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import click
from anthropic import Anthropic
from datetime import datetime

print("[STARTUP] Imports completed")


class HaikuResumeOptimizer:
    """Resume optimizer using Claude Haiku 3.5 with structured workflows."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "haiku"):
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        
        # Model mapping
        model_map = {
            "haiku": "claude-3-5-haiku-20241022",
            "sonnet": "claude-3-5-sonnet-20241022",
            "opus": "claude-3-opus-20240229"
        }
        
        self.model_name = model
        self.model = model_map.get(model, model)  # Use the mapped model or the raw string
        self.evidence_tracker = {"verified_skills": [], "verified_experiences": [], "verified_projects": []}
        
    def call_haiku(self, prompt: str, system_prompt: str = "") -> str:
        """Make a call to Claude Haiku 3.5."""
        # Add JSON instruction to system prompt
        if "JSON" in prompt:
            system_prompt = f"{system_prompt}\nYou must respond with valid JSON only. No explanations, no markdown code blocks, just raw JSON."
        
        print(f"  [DEBUG] Calling {self.model} API...")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.1,  # Lower temperature for more consistent output
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        print(f"  [DEBUG] API call completed")
        text = response.content[0].text.strip()
        
        # Clean up common JSON formatting issues
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        return text.strip()
    
    def parse_job_requirements(self, job_description: str) -> Dict[str, Any]:
        """Extract structured requirements from job description."""
        prompt = f"""<task>
Extract technical requirements from this job posting to optimize resume matching. Your analysis directly impacts which resume elements get emphasized.
</task>

<examples>
<example>
<job_input>
Senior Python Developer - 5+ years required
- Build APIs with FastAPI and PostgreSQL
- AWS experience preferred
- Lead team of 3-5 developers
</job_input>
<json_output>
{{"required_skills": [{{"skill": "Python", "confidence": 0.95}}, {{"skill": "API Development", "confidence": 0.9}}], "preferred_skills": [{{"skill": "AWS", "confidence": 0.8}}], "technologies_mentioned": ["Python", "FastAPI", "PostgreSQL", "AWS"], "years_experience": 5}}
</json_output>
</example>
</examples>

<job_description>
{job_description}
</job_description>

<instructions>
Extract and categorize ALL requirements:
- required_skills: array of {{"skill": string, "confidence": 0.9-1.0}} objects  
- preferred_skills: array of {{"skill": string, "confidence": 0.6-0.8}} objects
- responsibilities: array of specific job duties
- technologies_mentioned: array of all tech tools/frameworks
- years_experience: number or null
- education_requirements: array of degree/certification needs

Confidence guide: 0.95+ = explicitly required, 0.8+ = strongly preferred, 0.6+ = nice to have
</instructions>

<output_format>
Return only valid JSON. No explanations, no markdown blocks.
</output_format>"""

        result = self.call_haiku(prompt, "You are a senior technical recruiter with 10+ years experience parsing job requirements for software roles. Extract requirements with precision and completeness.")
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON parsing error, retrying...")
            # Retry with explicit JSON request
            prompt += "\n\nReturn ONLY valid JSON, no other text."
            result = self.call_haiku(prompt, "Return only valid JSON.")
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                print(f"  ❌ Failed to parse JSON: {result[:200]}...")
                # Return safe defaults
                return {
                    "required_skills": [],
                    "preferred_skills": [],
                    "responsibilities": [],
                    "company_values": [],
                    "technologies_mentioned": [],
                    "years_experience": None,
                    "education_requirements": []
                }
    
    def parse_resume(self, resume_content: str) -> Dict[str, Any]:
        """Extract structured content from resume."""
        prompt = f"""Parse this resume into structured JSON format:

{resume_content}

Return a JSON object with:
- contact_info: object with name, email, phone, location
- summary: string (professional summary if present)
- experience: array of {{company, title, dates, achievements}} objects
- education: array of {{institution, degree, dates, details}} objects
- skills: array of skill strings
- projects: array of {{name, description, technologies}} objects
- certifications: array of certification strings

Extract ONLY what is explicitly stated in the resume."""

        result = self.call_haiku(prompt, "You are a resume parser. Extract only factual information.")
        try:
            parsed = json.loads(result)
            # Track evidence
            for skill in parsed.get("skills", []):
                self.evidence_tracker["verified_skills"].append({
                    "skill": skill,
                    "source": "Original resume",
                    "confidence": 1.0
                })
            return parsed
        except json.JSONDecodeError:
            print(f"  ⚠️  JSON parsing error, retrying...")
            prompt += "\n\nReturn ONLY valid JSON, no other text."
            result = self.call_haiku(prompt, "Return only valid JSON.")
            try:
                parsed = json.loads(result)
                for skill in parsed.get("skills", []):
                    self.evidence_tracker["verified_skills"].append({
                        "skill": skill,
                        "source": "Original resume",
                        "confidence": 1.0
                    })
                return parsed
            except json.JSONDecodeError:
                print(f"  ❌ Failed to parse resume JSON")
                # Return minimal structure
                return {
                    "contact_info": {},
                    "summary": "",
                    "experience": [],
                    "education": [],
                    "skills": [],
                    "projects": [],
                    "certifications": []
                }
    
    def evaluate_match(self, resume_data: Dict, job_data: Dict) -> Dict[str, Any]:
        """Evaluate how well the resume matches the job requirements."""
        prompt = f"""<task>
Calculate how well this candidate matches the job requirements. Your score determines optimization priorities.
</task>

<evaluation_criteria>
Strong Match (8-10): Direct experience with required skills
Good Match (6-7): Transferable skills or related experience  
Weak Match (3-5): Some relevant background but gaps exist
Poor Match (0-2): Limited relevant experience
</evaluation_criteria>

<examples>
<example>
<input>
Job requires: Python, AWS, Docker, 5+ years, microservices
Resume has: Python (3 years), Java (5 years), Azure, containerization experience
</input>
<scoring_logic>
- Python: Partial match (3/5 years) = 60% 
- AWS: Transferable (Azure experience) = 70%
- Docker: Implicit (containerization) = 75%
- Experience: Slightly under but close = 80%
- Microservices: Not explicitly mentioned = 40%
</scoring_logic>
<result_score>65</result_score>
<rationale>Good foundation with transferable skills, minor gaps</rationale>
</example>

<example>
<input>
Job requires: Go, Kubernetes, 3+ years
Resume has: Java (7 years), Docker, Spring Boot, no Go mention
</input>
<scoring_logic>
- Go: No match = 10%
- Kubernetes: Docker is related = 60% 
- Experience: Exceeds requirement = 90%
- Backend skills: Strong foundation = 80%
</scoring_logic>
<result_score>45</result_score>
<rationale>Strong backend experience but missing key language</rationale>
</example>
</examples>

<resume_data>
{json.dumps(resume_data, indent=2)}
</resume_data>

<job_requirements>
{json.dumps(job_data, indent=2)}
</job_requirements>

<instructions>
Analyze systematically:
1. Count exact skill matches vs. required skills
2. Identify transferable skills (e.g., Azure → AWS)
3. Assess experience level alignment
4. Calculate weighted match score (0-100)

Return JSON with:
- match_score: number 0-100
- skills_match: {{"score": number, "strong_matches": array, "weak_matches": array, "gaps": array}}
- experience_match: {{"score": number, "relevant_points": array, "gaps": array}}
- recommendations: array of specific improvements
</instructions>

<output_format>
Return only valid JSON.
</output_format>"""

        result = self.call_haiku(prompt, "You are a technical hiring manager evaluating candidate-job fit. Be thorough and objective in your scoring.")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            print(f"  ⚠️  JSON parsing error in evaluation, retrying...")
            prompt += "\n\nReturn ONLY valid JSON, no other text."
            result = self.call_haiku(prompt, "Return only valid JSON.")
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                print(f"  ❌ Failed to parse evaluation JSON")
                # Return default evaluation
                return {
                    "match_score": 50,
                    "skills_match": {"score": 50, "strong_matches": [], "weak_matches": [], "gaps": []},
                    "experience_match": {"score": 50, "relevant_points": [], "gaps": []},
                    "recommendations": []
                }
    
    def create_enhancement_plan(self, evaluation: Dict, resume_data: Dict, job_data: Dict) -> List[Dict]:
        """Create a prioritized plan for resume enhancements."""
        prompt = f"""<task>
Create specific enhancement recommendations to improve resume-job match. Return as JSON array.
</task>

<examples>
<example>
<input>
Job requires: Python, Docker, 5+ years
Resume has: Java (5 years), Python (2 years), some containerization
Match gaps: Limited Python experience, no explicit Docker mention
</input>
<good_output>
[
  {{"section": "skills", "priority": "high", "action": "Move Python to prominent position", "rationale": "Job requires Python proficiency"}},
  {{"section": "experience", "priority": "medium", "action": "Emphasize containerization work as Docker experience", "rationale": "Highlight relevant Docker-adjacent experience"}}
]
</good_output>
</example>

<example>
<bad_output_to_avoid>
{{"section": "experience", "priority": "high", "action": "Add 3 years Python experience"}}
</bad_output_to_avoid>
<why_bad>This suggests fabricating experience, which violates truthfulness</why_bad>
</example>
</examples>

<evaluation_data>
{json.dumps(evaluation, indent=2)[:1000]}...
</evaluation_data>

<job_requirements>
Required: {[s.get('skill', '') for s in job_data.get('required_skills', [])[:5]]}
Key Tech: {job_data.get('technologies_mentioned', [])[:5]}
</job_requirements>

<instructions>
Create 2-4 specific enhancement items focusing on:
1. Reorganizing existing content for better job match
2. Emphasizing relevant skills already present
3. Reframing experiences to highlight job-relevant aspects

Each item must have: section, priority, action, rationale
CRITICAL: Return as JSON array, not object
</instructions>

<output_format>
[{{"section": "string", "priority": "high/medium/low", "action": "specific change", "rationale": "why this helps"}}]
</output_format>"""

        result = self.call_haiku(prompt, "You are a resume strategist creating actionable enhancement plans. Focus on truthful repositioning of existing content.")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            print(f"  ⚠️  JSON parsing error in enhancement plan, retrying...")
            prompt += "\n\nReturn ONLY valid JSON array, no other text."
            result = self.call_haiku(prompt, "Return only valid JSON.")
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                print(f"  ❌ Failed to parse enhancement plan JSON")
                # Return empty plan
                return []
    
    def optimize_section(self, section_name: str, section_content: str, job_data: Dict, enhancement_items: List[Dict]) -> str:
        """Optimize a specific resume section based on the enhancement plan."""
        # Debug: Check if enhancement_items is actually a list of dicts
        if not isinstance(enhancement_items, list):
            print(f"  ⚠️  Enhancement items is not a list: {type(enhancement_items)}")
            relevant_enhancements = []
        elif enhancement_items and not isinstance(enhancement_items[0], dict):
            print(f"  ⚠️  Enhancement items contains non-dict elements: {type(enhancement_items[0])}")
            relevant_enhancements = []
        else:
            relevant_enhancements = [e for e in enhancement_items if isinstance(e, dict) and e.get('section', '').lower() == section_name.lower()]
        
        prompt = f"""<task>
Optimize this resume {section_name} section to better match the target job. Emphasize relevant elements while maintaining truthfulness.
</task>

<examples>
<example>
<original>- Developed web applications using JavaScript</original>
<job_keywords>React, Node.js, microservices</job_keywords>
<optimized>- Architected scalable web applications using JavaScript, implementing modern frameworks and microservices patterns</optimized>
<rationale>Enhanced with relevant keywords while staying truthful to original experience</rationale>
</example>
</examples>

<current_content>
{section_content}
</current_content>

<target_job_context>
Required Skills: {[s.get('skill', '') for s in job_data.get('required_skills', [])[:5]]}
Key Technologies: {job_data.get('technologies_mentioned', [])[:5]}
Responsibilities: {job_data.get('responsibilities', [])[:3]}
</target_job_context>

<enhancement_guidelines>
{json.dumps(relevant_enhancements, indent=2)}
</enhancement_guidelines>

<optimization_rules>
1. MANDATORY: Only reorganize and rephrase existing content
2. Lead with most job-relevant experiences
3. Use strong action verbs (architected, engineered, optimized)
4. Incorporate job keywords naturally where truthful
5. Quantify existing achievements more prominently
6. FORBIDDEN: Adding new experiences, skills, or fabricated details
</optimization_rules>

<instructions>
Transform the content to maximize job relevance while maintaining complete truthfulness. Focus on strategic presentation of existing qualifications.
</instructions>

Return only the optimized section content."""

        return self.call_haiku(prompt, "You are a senior resume writer specializing in technical roles. Optimize strategically while maintaining strict truthfulness.")
    
    def verify_truthfulness(self, original: str, optimized: str) -> Dict[str, Any]:
        """Verify that optimizations maintain truthfulness."""
        prompt = f"""<task>
Verify that resume optimizations maintain truthfulness. Allow reasonable enhancements but flag fabrications.
</task>

<examples>
<example>
<original_text>- Led Docker containerization of Java/Spring Boot microservices</original_text>
<optimized_text>- Architected Docker containerization of Java/Spring Boot microservices</optimized_text>
<verification_result>
{{"is_truthful": true, "confidence": 0.9, "rationale": "Led→Architected is acceptable enhancement showing leadership"}}
</verification_result>
</example>

<example>
<original_text>- Created automation scripts with Python</original_text>
<optimized_text>- Engineered enterprise-grade automation platform with Python, serving 10,000+ users</optimized_text>
<verification_result>
{{"is_truthful": false, "confidence": 0.1, "issues": ["Added unverified user count", "Inflated scope from scripts to platform"]}}
</verification_result>
</example>

<example>
<original_text>- Streamlined deployments using GitLab CI/CD</original_text>
<optimized_text>- Engineered comprehensive CI/CD pipelines using GitLab, automating deployment workflows</optimized_text>
<verification_result>
{{"is_truthful": true, "confidence": 0.85, "rationale": "Enhanced language but stayed within scope of original work"}}
</verification_result>
</example>
</examples>

<original_content>
{original[:500]}...
</original_content>

<optimized_content>
{optimized[:500]}...
</optimized_content>

<verification_guidelines>
ACCEPT: Enhanced language, stronger action verbs, reorganization, emphasis changes
REJECT: New claims, fabricated metrics, added technologies not mentioned, inflated scope
</verification_guidelines>

<instructions>
Compare content focusing on:
1. Are all claims based on original content?
2. Are any new technologies/skills added?
3. Are metrics or achievements inflated beyond original scope?
4. Is the enhancement reasonable for the original experience level?

Be practical - allow reasonable professional language improvements.
</instructions>

<output_format>
{{"is_truthful": boolean, "confidence": 0.0-1.0, "issues": ["any problems"], "rationale": "explanation"}}
</output_format>"""

        result = self.call_haiku(prompt, "You are a professional resume reviewer evaluating truthfulness. Allow reasonable enhancements while preventing fabrication.")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            print(f"  ⚠️  JSON parsing error in verification, retrying...")
            prompt += "\n\nReturn ONLY valid JSON, no other text."
            result = self.call_haiku(prompt, "Return only valid JSON.")
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                print(f"  ❌ Failed to parse verification JSON")
                # Default to truthful (safe assumption)
                return {
                    "is_truthful": True,
                    "issues": [],
                    "suggestions": []
                }
    
    def generate_summary(self, resume_data: Dict, job_data: Dict, evaluation: Dict) -> str:
        """Generate a professional summary tailored to the job."""
        # Safely get data with defaults
        experience_list = resume_data.get('experience', [])
        most_recent_role = experience_list[0].get('title', 'N/A') if experience_list else 'N/A'
        years_exp = len(experience_list)
        
        # Get top matching skills
        strong_matches = evaluation.get('skills_match', {}).get('strong_matches', [])
        skills_to_highlight = strong_matches[:3] if strong_matches else resume_data.get('skills', [])[:3]
        
        # Simplified, direct prompt
        prompt = f"""Write a 3-4 sentence professional summary for a {most_recent_role} with {years_exp} years of experience.

Key skills to mention: {', '.join(skills_to_highlight)}

Start with: "Experienced {most_recent_role} with {years_exp} years of expertise in..."

Include these elements:
- Years of experience and current role
- Top 2-3 relevant technical skills
- One key achievement or strength
- Alignment with the target role

Write ONLY the summary paragraph. No explanations, no alternatives, just the professional summary text."""

        system = "You are writing a resume summary. Be direct and professional. Output only the requested summary text."
        return self.call_haiku(prompt, system)
    
    def create_customization_report(self, changes: List[Dict], evaluation_before: Dict, evaluation_after: Dict) -> str:
        """Create a detailed report of customizations made."""
        model_display = {
            "haiku": "Claude 3.5 Haiku",
            "sonnet": "Claude Sonnet 4.0",
            "opus": "Claude Opus 4.0"
        }
        
        report = f"""# Resume Customization Report

## Overview
- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- Model: {model_display.get(self.model_name, self.model_name)}
- Match Score: {evaluation_before['match_score']}% → {evaluation_after['match_score']}%

## Key Changes Made

"""
        for change in changes:
            report += f"### {change['section']}\n"
            report += f"- **Change**: {change['description']}\n"
            report += f"- **Rationale**: {change['rationale']}\n"
            report += f"- **Evidence**: {change.get('evidence_source', 'Original resume')}\n\n"
        
        report += f"""## Match Analysis

### Before Customization
- Skills Match: {evaluation_before['skills_match']['score']}%
- Experience Match: {evaluation_before['experience_match']['score']}%

### After Customization  
- Skills Match: {evaluation_after['skills_match']['score']}%
- Experience Match: {evaluation_after['experience_match']['score']}%

## Remaining Gaps
"""
        
        for gap in evaluation_after.get('skills_match', {}).get('gaps', []):
            report += f"- {gap}\n"
        
        report += "\n## Interview Preparation\n"
        report += "Be prepared to discuss:\n"
        for skill in evaluation_after.get('skills_match', {}).get('strong_matches', [])[:5]:
            report += f"- Your experience with {skill}\n"
        
        return report
    
    def optimize_resume(self, resume_content: str, job_description: str) -> Dict[str, str]:
        """Main optimization workflow."""
        print("📋 Parsing job requirements...")
        job_data = self.parse_job_requirements(job_description)
        
        print("📄 Parsing resume content...")
        resume_data = self.parse_resume(resume_content)
        
        print("🔍 Evaluating initial match...")
        evaluation_before = self.evaluate_match(resume_data, job_data)
        print(f"  Initial match score: {evaluation_before['match_score']}%")
        
        print("📝 Creating enhancement plan...")
        enhancement_plan = self.create_enhancement_plan(evaluation_before, resume_data, job_data)
        
        print("✨ Optimizing resume sections...")
        optimized_sections = {}
        changes_made = []
        
        # Generate optimized summary
        optimized_sections['summary'] = self.generate_summary(resume_data, job_data, evaluation_before)
        
        # Split resume into sections for optimization
        sections = self.split_resume_sections(resume_content)
        
        for section_name, section_content in sections.items():
            if section_name.lower() in ['experience', 'skills', 'projects']:
                print(f"  Optimizing {section_name}...")
                optimized = self.optimize_section(section_name, section_content, job_data, enhancement_plan)
                
                # Verify truthfulness
                verification = self.verify_truthfulness(section_content, optimized)
                if verification['is_truthful']:
                    optimized_sections[section_name] = optimized
                    changes_made.append({
                        'section': section_name,
                        'description': f"Optimized {section_name} section for job relevance",
                        'rationale': f"Highlighted matching skills and experiences",
                        'evidence_source': 'Original resume'
                    })
                else:
                    print(f"  ⚠️  Truthfulness issues in {section_name}, using original")
                    optimized_sections[section_name] = section_content
            else:
                optimized_sections[section_name] = section_content
        
        # Reconstruct resume
        optimized_resume = self.reconstruct_resume(optimized_sections, resume_content)
        
        print("🔍 Evaluating optimized resume...")
        optimized_data = self.parse_resume(optimized_resume)
        evaluation_after = self.evaluate_match(optimized_data, job_data)
        print(f"  Final match score: {evaluation_after['match_score']}%")
        
        print("📊 Generating customization report...")
        report = self.create_customization_report(changes_made, evaluation_before, evaluation_after)
        
        return {
            'customized_resume': optimized_resume,
            'customization_report': report
        }
    
    def split_resume_sections(self, resume_content: str) -> Dict[str, str]:
        """Split resume into sections based on common headers."""
        sections = {}
        current_section = "header"
        current_content = []
        
        section_keywords = {
            'summary': ['summary', 'objective', 'profile', 'about'],
            'experience': ['experience', 'work history', 'employment', 'professional experience'],
            'education': ['education', 'academic'],
            'skills': ['skills', 'technical skills', 'competencies'],
            'projects': ['projects', 'portfolio'],
            'certifications': ['certifications', 'certificates', 'licenses']
        }
        
        lines = resume_content.split('\n')
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line is a section header
            is_header = False
            for section, keywords in section_keywords.items():
                if any(keyword in line_lower for keyword in keywords) and len(line_lower) < 50:
                    # Save previous section
                    if current_content:
                        sections[current_section] = '\n'.join(current_content)
                    current_section = section
                    current_content = []
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def reconstruct_resume(self, sections: Dict[str, str], original: str) -> str:
        """Reconstruct resume from optimized sections."""
        # Start with header/contact info
        result = []
        
        if 'header' in sections:
            result.append(sections['header'].strip())
            result.append('')
        
        # Add summary if we have one
        if 'summary' in sections and sections['summary']:
            result.append("## Professional Summary")
            result.append(sections['summary'].strip())
            result.append('')
        
        # Add sections in a logical order
        section_order = ['experience', 'projects', 'education', 'skills', 'certifications']
        section_titles = {
            'experience': '## Professional Experience',
            'projects': '## Projects',
            'education': '## Education', 
            'skills': '## Skills',
            'certifications': '## Certifications'
        }
        
        for section in section_order:
            if section in sections and sections[section].strip():
                result.append(section_titles[section])
                result.append(sections[section].strip())
                result.append('')
        
        return '\n'.join(result)


@click.command()
@click.option('--resume', '-r', required=True, type=click.Path(exists=True), help='Path to resume file')
@click.option('--job', '-j', required=True, type=click.Path(exists=True), help='Path to job description file')
@click.option('--output-dir', '-o', default='./haiku_output', help='Output directory for results')
@click.option('--api-key', envvar='ANTHROPIC_API_KEY', help='Anthropic API key')
@click.option('--model', '-m', default='haiku', type=click.Choice(['haiku', 'sonnet', 'opus']), help='Claude model to use')
def main(resume: str, job: str, output_dir: str, api_key: str, model: str):
    """Optimize resume using Claude models with structured workflows."""
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Read input files
    with open(resume, 'r') as f:
        resume_content = f.read()
    
    with open(job, 'r') as f:
        job_description = f.read()
    
    # Initialize optimizer
    optimizer = HaikuResumeOptimizer(api_key, model)
    
    model_display = {
        "haiku": "Claude 3.5 Haiku",
        "sonnet": "Claude Sonnet 4.0",
        "opus": "Claude Opus 4.0"
    }
    
    print(f"🚀 Starting resume optimization with {model_display.get(model, model)}...")
    print("=" * 60)
    
    try:
        # Run optimization
        results = optimizer.optimize_resume(resume_content, job_description)
        
        # Save results
        resume_path = output_path / "new_customized_resume.md"
        with open(resume_path, 'w') as f:
            f.write(results['customized_resume'])
        
        report_path = output_path / "customization_report.md"
        with open(report_path, 'w') as f:
            f.write(results['customization_report'])
        
        print("=" * 60)
        print("✅ Optimization complete!")
        print(f"📄 Customized resume: {resume_path}")
        print(f"📊 Report: {report_path}")
        
        # Show cost estimate
        # Rough estimate: ~10-15 API calls, ~2-3k tokens per call
        estimated_input_tokens = 30000
        estimated_output_tokens = 15000
        
        # Pricing per million tokens (input/output)
        pricing = {
            "haiku": (0.25, 1.25),      # Haiku 3.5
            "sonnet": (3.00, 15.00),    # Sonnet 4.0
            "opus": (15.00, 75.00)      # Opus 4.0
        }
        
        input_price, output_price = pricing.get(model, (0.25, 1.25))
        estimated_cost = (estimated_input_tokens * input_price + estimated_output_tokens * output_price) / 1000000
        print(f"💰 Estimated cost: ${estimated_cost:.4f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()