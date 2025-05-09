"""
Synthesis mechanism for combining section analyzer results.

This module provides functionality to run multiple section analyzers asynchronously
and combine their results into a comprehensive analysis with prioritized recommendations.
"""
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
import logfire

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.core.config import settings
from app.schemas.customize import CustomizationLevel, CustomizationPlan, RecommendationItem
from app.services.model_selector import ModelProvider, select_model_for_task
from app.services.section_analyzers.base import BaseSectionAnalyzer, SectionType, SectionAnalysisResult
from app.schemas.section_analyzers import (
    SkillsAnalysisResult,
    ExperienceAnalysisResult,
    EducationAnalysisResult,
    AchievementAnalysisResult,
    LanguageToneAnalysisResult,
    CombinedAnalysisResult,
    SectionRecommendation,
    SectionIssue
)
from app.services.section_analyzers.skills_analyzer import SkillsQualificationsAnalyzer
from app.services.section_analyzers.experience_analyzer import ExperienceAlignmentAnalyzer
from app.services.section_analyzers.education_analyzer import EducationCertificationAnalyzer
from app.services.section_analyzers.achievement_analyzer import AchievementQuantificationAnalyzer
from app.services.section_analyzers.language_tone_optimizer import LanguageToneOptimizer


class ResumeAnalysisSynthesizer:
    """
    Synthesizes results from multiple section analyzers into a comprehensive analysis.
    
    This class orchestrates the execution of multiple section analyzers in parallel
    and combines their results into a unified analysis with prioritized recommendations.
    """
    
    def __init__(
        self,
        preferred_model_provider: Optional[ModelProvider] = None,
        customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
        enabled_analyzers: Optional[List[SectionType]] = None
    ):
        """
        Initialize the resume analysis synthesizer.
        
        Args:
            preferred_model_provider: Optional preferred AI model provider
            customization_level: Customization level affecting analysis depth
            enabled_analyzers: Optional list of section analyzers to enable
                              (defaults to all if not specified)
        """
        self.preferred_model_provider = preferred_model_provider
        self.customization_level = customization_level
        self.enabled_analyzers = enabled_analyzers or [
            SectionType.SKILLS,
            SectionType.EXPERIENCE,
            SectionType.EDUCATION,
            SectionType.ACHIEVEMENTS,
            SectionType.ALL  # For language and tone
        ]
        self.logger = logfire.logger.getChild(self.__class__.__name__)
        self.logger.info(
            "Resume analysis synthesizer initialized",
            preferred_provider=self.preferred_model_provider,
            customization_level=self.customization_level,
            enabled_analyzers=self.enabled_analyzers
        )
    
    def _create_analyzers(self) -> Dict[SectionType, BaseSectionAnalyzer]:
        """
        Create the enabled section analyzers.
        
        Returns:
            Dictionary mapping section types to their analyzers
        """
        analyzers = {}
        
        if SectionType.SKILLS in self.enabled_analyzers:
            analyzers[SectionType.SKILLS] = SkillsQualificationsAnalyzer(
                preferred_model_provider=self.preferred_model_provider,
                customization_level=self.customization_level
            )
            
        if SectionType.EXPERIENCE in self.enabled_analyzers:
            analyzers[SectionType.EXPERIENCE] = ExperienceAlignmentAnalyzer(
                preferred_model_provider=self.preferred_model_provider,
                customization_level=self.customization_level
            )
            
        if SectionType.EDUCATION in self.enabled_analyzers:
            analyzers[SectionType.EDUCATION] = EducationCertificationAnalyzer(
                preferred_model_provider=self.preferred_model_provider,
                customization_level=self.customization_level
            )
            
        if SectionType.ACHIEVEMENTS in self.enabled_analyzers:
            analyzers[SectionType.ACHIEVEMENTS] = AchievementQuantificationAnalyzer(
                preferred_model_provider=self.preferred_model_provider,
                customization_level=self.customization_level
            )
            
        if SectionType.ALL in self.enabled_analyzers:
            analyzers[SectionType.ALL] = LanguageToneOptimizer(
                preferred_model_provider=self.preferred_model_provider,
                customization_level=self.customization_level
            )
            
        return analyzers
    
    async def analyze_resume(
        self,
        resume_content: str,
        job_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CombinedAnalysisResult:
        """
        Run all enabled section analyzers and synthesize their results.
        
        Args:
            resume_content: Full resume content
            job_description: Full job description
            context: Optional additional context for analysis
            
        Returns:
            CombinedAnalysisResult with synthesized analysis from all analyzers
        """
        start_time = time.time()
        self.logger.info(
            "Starting comprehensive resume analysis",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            analyzer_count=len(self.enabled_analyzers)
        )
        
        # Create all the enabled analyzers
        analyzers = self._create_analyzers()
        
        # Run all analyzers in parallel
        analysis_tasks = []
        for section_type, analyzer in analyzers.items():
            self.logger.info(f"Queuing analysis task for {section_type.value}")
            task = asyncio.create_task(
                analyzer.analyze(
                    resume_content=resume_content,
                    job_description=job_description,
                    context=context
                )
            )
            analysis_tasks.append((section_type, task))
        
        # Wait for all analyzers to complete
        results = {}
        for section_type, task in analysis_tasks:
            try:
                result = await task
                results[section_type] = result
                self.logger.info(f"Completed analysis for {section_type.value}", score=result.score)
            except Exception as e:
                self.logger.error(
                    f"Error in {section_type.value} analysis",
                    error=str(e)
                )
        
        # Synthesize all the results
        combined_result = await self._synthesize_results(results, resume_content, job_description)
        
        # Log completion
        elapsed_time = time.time() - start_time
        self.logger.info(
            "Comprehensive resume analysis completed",
            elapsed_seconds=round(elapsed_time, 2),
            overall_score=combined_result.overall_score,
            recommendation_count=len(combined_result.integrated_recommendations)
        )
        
        return combined_result
    
    async def _synthesize_results(
        self,
        section_results: Dict[SectionType, SectionAnalysisResult],
        resume_content: str,
        job_description: str
    ) -> CombinedAnalysisResult:
        """
        Synthesize results from multiple analyzers into a unified analysis.
        
        Args:
            section_results: Dictionary mapping section types to their analysis results
            resume_content: Full resume content
            job_description: Full job description
            
        Returns:
            CombinedAnalysisResult with synthesized analysis
        """
        self.logger.info(
            "Synthesizing results from section analyzers",
            section_count=len(section_results)
        )
        
        # Calculate overall score as weighted average of section scores
        # Define weights for each section type
        weights = {
            SectionType.SKILLS: 0.25,
            SectionType.EXPERIENCE: 0.35,
            SectionType.EDUCATION: 0.15,
            SectionType.ACHIEVEMENTS: 0.15,
            SectionType.ALL: 0.10  # Language and tone
        }
        
        # Calculate weighted average score
        total_weight = 0
        weighted_score_sum = 0
        
        for section_type, result in section_results.items():
            weight = weights.get(section_type, 0.1)  # Default weight for unknown section types
            weighted_score_sum += result.score * weight
            total_weight += weight
        
        # Avoid division by zero
        overall_score = round(weighted_score_sum / total_weight) if total_weight > 0 else 50
        
        # Prepare a combined result with all section analyses
        skills_result = section_results.get(SectionType.SKILLS)
        experience_result = section_results.get(SectionType.EXPERIENCE)
        education_result = section_results.get(SectionType.EDUCATION)
        achievement_result = section_results.get(SectionType.ACHIEVEMENTS)
        language_tone_result = section_results.get(SectionType.ALL)
        
        # Merge and prioritize recommendations across all analyzers
        integrated_recommendations = []
        priority_improvements = []
        
        # Helper function to add recommendations with source tracking
        def add_recommendations(source: str, recommendations: List[SectionRecommendation]):
            for rec in recommendations:
                # Add source to the recommendation
                integrated_recommendations.append({
                    "source": source,
                    "section": rec.what.split(":")[0] if ":" in rec.what else "General",
                    "what": rec.what,
                    "why": rec.why,
                    "how": rec.how if hasattr(rec, "how") else "",
                    "priority": rec.priority if hasattr(rec, "priority") else 5,
                    "before_text": rec.before_text,
                    "after_text": rec.after_text
                })
                
                # Add high-priority improvements to the priority list
                if hasattr(rec, "priority") and rec.priority >= 8:
                    priority_improvements.append({
                        "source": source,
                        "section": rec.what.split(":")[0] if ":" in rec.what else "General",
                        "what": rec.what,
                        "why": rec.why,
                        "priority": rec.priority
                    })
        
        # Add recommendations from each analyzer
        if skills_result:
            add_recommendations("Skills Analysis", skills_result.recommendations)
            
        if experience_result:
            add_recommendations("Experience Analysis", experience_result.recommendations)
            
        if education_result:
            add_recommendations("Education Analysis", education_result.recommendations)
            
        if achievement_result:
            add_recommendations("Achievement Analysis", achievement_result.recommendations)
            
        if language_tone_result:
            add_recommendations("Language/Tone Analysis", language_tone_result.recommendations)
        
        # Sort integrated recommendations by priority (highest first)
        integrated_recommendations.sort(key=lambda x: x["priority"] if isinstance(x, dict) and "priority" in x else getattr(x, "priority", 5), reverse=True)
        priority_improvements.sort(key=lambda x: x["priority"] if isinstance(x, dict) and "priority" in x else getattr(x, "priority", 5), reverse=True)
        
        # Create an improvement plan structure based on customization level
        improvement_plan = self._create_improvement_plan(
            section_results, 
            integrated_recommendations, 
            priority_improvements,
            overall_score
        )
        
        # Combine all the results into a final analysis
        return CombinedAnalysisResult(
            overall_score=overall_score,
            skills_analysis=skills_result,
            experience_analysis=experience_result,
            education_analysis=education_result,
            achievement_analysis=achievement_result,
            language_tone_analysis=language_tone_result,
            integrated_recommendations=[
                SectionRecommendation(
                    what=rec["what"],
                    why=rec["why"],
                    how=rec["how"],
                    priority=rec.get("priority", 5),
                    before_text=rec["before_text"],
                    after_text=rec["after_text"]
                ) for rec in integrated_recommendations
            ],
            priority_improvements=priority_improvements,
            improvement_plan=improvement_plan
        )
    
    def _create_improvement_plan(
        self,
        section_results: Dict[SectionType, SectionAnalysisResult],
        integrated_recommendations: List[Dict[str, Any]],
        priority_improvements: List[Dict[str, Any]],
        overall_score: int
    ) -> Dict[str, Any]:
        """
        Create a structured improvement plan based on analyzer results.
        
        Args:
            section_results: Dictionary mapping section types to their analysis results
            integrated_recommendations: Combined list of recommendations
            priority_improvements: List of high-priority improvements
            overall_score: Overall resume match score
            
        Returns:
            Dictionary containing the structured improvement plan
        """
        # Tailor the plan based on customization level
        if self.customization_level == CustomizationLevel.CONSERVATIVE:
            # Conservative plan focuses only on critical improvements
            max_recommendations = 5
            improvement_focus = "critical improvements only"
        elif self.customization_level == CustomizationLevel.BALANCED:
            # Balanced plan includes a moderate number of improvements
            max_recommendations = 10
            improvement_focus = "balanced improvements"
        else:
            # Extensive plan includes all recommended improvements
            max_recommendations = 20
            improvement_focus = "comprehensive improvements"
            
        # Group recommendations by section
        recommendations_by_section = {}
        for rec in integrated_recommendations:
            section = rec.get("section", "General")
            if section not in recommendations_by_section:
                recommendations_by_section[section] = []
            recommendations_by_section[section].append(rec)
        
        # Select the top recommendations for each section based on priority
        top_recommendations_by_section = {}
        for section, recs in recommendations_by_section.items():
            # Sort by priority (highest first)
            sorted_recs = sorted(recs, key=lambda x: x.get("priority", 5), reverse=True)
            # Take the top recommendations based on customization level
            section_max = max(1, round(max_recommendations * 0.25))  # Allocate 25% of max to each section
            top_recommendations_by_section[section] = sorted_recs[:section_max]
        
        # Create the improvement plan
        improvement_plan = {
            "summary": f"Resume currently has an ATS match score of {overall_score}/100. This plan provides {improvement_focus} to enhance the match score.",
            "approach": f"This {self.customization_level.name.lower()} plan focuses on {max_recommendations} key improvements across different resume sections.",
            "sections": {},
            "priority_focus_areas": [imp["what"] for imp in priority_improvements[:3]],  # Top 3 priority areas
            "estimated_score_improvement": min(25, 100 - overall_score)  # Conservative estimate
        }
        
        # Add section-specific plans
        for section, recs in top_recommendations_by_section.items():
            improvement_plan["sections"][section] = {
                "recommendations": recs,
                "count": len(recs)
            }
        
        return improvement_plan
    
    async def convert_to_customization_plan(
        self,
        combined_result: CombinedAnalysisResult,
        resume_content: str,
        job_description: str
    ) -> CustomizationPlan:
        """
        Convert the combined analysis result to a CustomizationPlan.
        
        Args:
            combined_result: Combined analysis result from all analyzers
            resume_content: Full resume content
            job_description: Full job description
            
        Returns:
            CustomizationPlan compatible with existing resume customization system
        """
        # Extract all keywords to add from the skills analysis
        keywords_to_add = []
        if combined_result.skills_analysis:
            for gap in combined_result.skills_analysis.missing_skills:
                if hasattr(gap, "term"):
                    keywords_to_add.append(gap.term)
                elif isinstance(gap, dict) and "term" in gap:
                    keywords_to_add.append(gap["term"])
        
        # Extract formatting suggestions
        formatting_suggestions = []
        
        # From language/tone analysis
        if combined_result.language_tone_analysis:
            formatting_suggestions.extend([
                issue.fix_suggestion 
                for issue in combined_result.language_tone_analysis.issues 
                if "format" in issue.issue_type.lower()
            ])
        
        # From achievement analysis
        if combined_result.achievement_analysis:
            formatting_suggestions.extend([
                "Quantify achievements with specific metrics and percentages",
                "Use strong action verbs at the beginning of achievement statements"
            ])
        
        # From all analyzers' improvement suggestions
        for rec in combined_result.integrated_recommendations:
            if "format" in rec.what.lower() or "structure" in rec.what.lower():
                formatting_suggestions.append(rec.what)
        
        # Deduplicate formatting suggestions
        formatting_suggestions = list(set(formatting_suggestions))
        
        # Create recommendations from the integrated recommendations
        recommendations = []
        for rec in combined_result.integrated_recommendations:
            recommendations.append(
                RecommendationItem(
                    section=rec.what.split(":")[0] if ":" in rec.what else "General",
                    what=rec.what,
                    why=rec.why,
                    before_text=rec.before_text,
                    after_text=rec.after_text,
                    description=rec.how if hasattr(rec, "how") else ""
                )
            )
        
        # Create the customization plan
        customization_plan = CustomizationPlan(
            summary=combined_result.improvement_plan.get("summary", ""),
            job_analysis=f"The job requires specific skills and experience that match {combined_result.overall_score}% with your current resume. This plan focuses on highlighting your relevant qualifications and addressing key gaps.",
            keywords_to_add=keywords_to_add,
            formatting_suggestions=formatting_suggestions,
            authenticity_statement="All recommended changes preserve your original experience and qualifications while improving the presentation and ATS optimization.",
            experience_preservation_statement="This plan ensures that all your original experience is preserved while optimizing the resume for better ATS matching.",
            recommendations=recommendations
        )
        
        return customization_plan