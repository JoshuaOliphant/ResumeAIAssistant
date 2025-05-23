"""
Requirements Extractor Integration for ResumeAIAssistant.

This module implements the RequirementsExtractor interface to provide a unified
integration layer for the key requirements extractor.
"""

from typing import Dict, List, Any, Optional
import logfire

from app.services.integration.interfaces import RequirementsExtractor
from app.schemas.requirements import KeyRequirements, RequirementCategory, Requirement


class IntegratedRequirementsExtractor(RequirementsExtractor):
    """Implementation of the RequirementsExtractor interface using existing extractor."""
    
    async def extract(self, job_description: str, 
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract key requirements from a job description.
        
        Args:
            job_description: The job description text
            context: Optional additional context
            
        Returns:
            Extracted key requirements
        """
        context = context or {}
        
        try:
            # Import the function only when needed to avoid circular imports
            from app.api.endpoints.requirements import extract_key_requirements
            
            # Call the existing requirements extraction function
            requirements = await extract_key_requirements(job_description)
            
            # Convert to dictionary if it's a Pydantic model
            if hasattr(requirements, "dict"):
                return requirements.dict()
                
            return requirements
            
        except Exception as e:
            logfire.error(f"Error extracting requirements: {str(e)}")
            
            # Return a basic fallback structure
            return {
                "job_title": context.get("job_title", "Unknown"),
                "company": context.get("company", "Unknown"),
                "categories": [],
                "keywords": {},
                "confidence": 0.0,
                "total_requirements_count": 0,
                "error": str(e)
            }
    
    async def categorize(self, requirements: List[str]) -> Dict[str, List[str]]:
        """
        Categorize requirements into types.
        
        Args:
            requirements: List of requirement strings
            
        Returns:
            Dictionary mapping category names to lists of requirements
        """
        if not requirements:
            return {}
            
        # Basic categorization logic - in a real implementation this would use
        # more sophisticated NLP techniques
        categories = {
            "skills": [],
            "experience": [],
            "education": [],
            "other": []
        }
        
        skill_keywords = ["skill", "proficient", "knowledge", "experience with", "ability to"]
        experience_keywords = ["year", "experience", "background", "history", "worked"]
        education_keywords = ["degree", "bachelor", "master", "phd", "certification", "diploma"]
        
        for req in requirements:
            req_lower = req.lower()
            
            # Check which category this requirement best fits
            if any(keyword in req_lower for keyword in skill_keywords):
                categories["skills"].append(req)
            elif any(keyword in req_lower for keyword in experience_keywords):
                categories["experience"].append(req)
            elif any(keyword in req_lower for keyword in education_keywords):
                categories["education"].append(req)
            else:
                categories["other"].append(req)
                
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}


class MockRequirementsExtractor(RequirementsExtractor):
    """Mock implementation for testing and fallback."""
    
    async def extract(self, job_description: str, 
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract key requirements from a job description.
        
        Args:
            job_description: The job description text
            context: Optional additional context
            
        Returns:
            Extracted key requirements
        """
        # Extract basic keywords from job description
        words = job_description.lower().split()
        keywords = {}
        
        # Simple keyword extraction (for demonstration)
        for word in set(words):
            if len(word) > 4 and not word.isdigit():
                frequency = words.count(word) / len(words)
                keywords[word] = min(frequency * 10, 1.0)
        
        # Sort keywords by importance and take top 20
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:20]
        keywords = {k: v for k, v in sorted_keywords}
        
        # Create basic requirements
        requirements = []
        for keyword, importance in sorted_keywords[:10]:
            requirements.append(f"Experience with {keyword}")
        
        # Categorize requirements
        categorized = await self.categorize(requirements)
        
        # Create structured result
        categories = []
        for category_name, reqs in categorized.items():
            category_reqs = []
            for i, req_text in enumerate(reqs):
                category_reqs.append({
                    "text": req_text,
                    "priority": min(i + 1, 5),
                    "category": category_name,
                    "is_required": i < 3  # First 3 are required
                })
            
            categories.append({
                "category": category_name,
                "requirements": category_reqs,
                "weight": 1.0
            })
        
        return {
            "job_title": context.get("job_title", "Unknown"),
            "company": context.get("company", "Unknown"),
            "categories": categories,
            "keywords": keywords,
            "confidence": 0.7,
            "total_requirements_count": len(requirements)
        }
    
    async def categorize(self, requirements: List[str]) -> Dict[str, List[str]]:
        """
        Categorize requirements into types.
        
        Args:
            requirements: List of requirement strings
            
        Returns:
            Dictionary mapping category names to lists of requirements
        """
        if not requirements:
            return {}
            
        # Simple categorization with fixed categories
        num_reqs = len(requirements)
        
        return {
            "skills": requirements[:num_reqs // 3],
            "experience": requirements[num_reqs // 3:2 * num_reqs // 3],
            "education": requirements[2 * num_reqs // 3:]
        }
