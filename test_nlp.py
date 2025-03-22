"""
Test script for the NLP functionality
"""
import unittest
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.nltk_init import initialize_nlp
from app.services.ats_service import extract_keywords


class TestNLPFunctionality(unittest.TestCase):
    """Test the NLP functionality used in the ATS analysis"""

    def setUp(self):
        """Initialize NLP resources before tests"""
        self.nltk_initialized, self.spacy_model = initialize_nlp()
        
    def test_nlp_initialization(self):
        """Test that NLP resources are properly initialized"""
        self.assertTrue(self.nltk_initialized, "NLTK should be initialized")
        # We don't strictly require spaCy to be loaded, as we have a fallback
        if self.spacy_model is None:
            print("NOTE: spaCy model not loaded, using fallback NLTK implementation")
        
    def test_extract_keywords_basic(self):
        """Test basic keyword extraction functionality"""
        text = """
        Python developer with 5 years of experience in web development.
        Skilled in Django, Flask, and FastAPI frameworks.
        """
        keywords = extract_keywords(text)
        print(f"Extracted keywords: {keywords}")
        
        # Check that common technical terms are extracted
        self.assertIn("python", keywords)
        
        # These tests might fail if we're using the fallback implementation
        # and the technical terms are not frequent enough
        if self.spacy_model is not None:
            self.assertIn("django", keywords)
            self.assertIn("flask", keywords)
            self.assertIn("fastapi", keywords)
            self.assertIn("web development", keywords)
        else:
            # For fallback implementation, just check that we have some keywords
            self.assertTrue(len(keywords) > 2, "Should extract at least a few keywords")
        
    def test_extract_keywords_with_entities(self):
        """Test that entity recognition works in keyword extraction"""
        text = """
        Worked at Microsoft and Google developing cloud solutions.
        Implemented machine learning models using TensorFlow and PyTorch.
        """
        keywords = extract_keywords(text)
        print(f"Extracted keywords with entities: {keywords}")
        
        # Entity extraction works best with spaCy
        if self.spacy_model is not None:
            # Check that organizations are extracted
            self.assertIn("microsoft", keywords)
            self.assertIn("google", keywords)
            
            # Check that technical terms are extracted
            self.assertIn("machine learning", keywords)
            self.assertIn("tensorflow", keywords)
            self.assertIn("pytorch", keywords)
        else:
            # For fallback implementation, just check for technical terms
            self.assertIn("machine learning", keywords)
            # At least one of these should be present
            self.assertTrue("tensorflow" in keywords or "pytorch" in keywords, 
                          "Should extract at least one technical term")
        
    def test_extract_keywords_with_skills(self):
        """Test that skill-related keywords are properly extracted"""
        text = """
        Proficient in JavaScript, TypeScript, and React.
        Experienced with CI/CD pipelines and Docker containerization.
        """
        keywords = extract_keywords(text)
        print(f"Extracted skills keywords: {keywords}")
        
        # Basic skills should be extracted in both implementations
        self.assertIn("javascript", keywords)
        
        if self.spacy_model is not None:
            # These should work better with spaCy
            self.assertIn("typescript", keywords)
            self.assertIn("react", keywords)
            self.assertIn("docker", keywords)
            self.assertIn("ci/cd", keywords)
        else:
            # For fallback implementation, check for at least some skills
            self.assertTrue(any(skill in keywords for skill in 
                             ["typescript", "react", "docker"]), 
                          "Should extract at least one skill")
        
    def test_extract_keywords_fallback(self):
        """Test that keyword extraction works even if spaCy is not available"""
        # Temporarily set the spaCy model to None to test fallback
        from app.core.spacy_init import initialize_spacy
        original_model = initialize_spacy.nlp
        initialize_spacy.nlp = None
        
        try:
            text = "Python developer with experience in Django and Flask."
            keywords = extract_keywords(text)
            print(f"Fallback extracted keywords: {keywords}")
            
            # Check that basic extraction still works
            self.assertIn("python", keywords)
            
            # The fallback might not extract these if they only appear once
            # So we'll check that we have at least some keywords
            self.assertTrue(len(keywords) > 0, "Should extract at least some keywords")
            
            # Add Django and Flask multiple times to ensure they're extracted
            text = "Python Django Flask Django Flask developer with Django and Flask experience."
            keywords = extract_keywords(text)
            print(f"Fallback extracted keywords (repeated terms): {keywords}")
            
            # Now they should be extracted because they appear multiple times
            self.assertIn("django", keywords)
            self.assertIn("flask", keywords)
        finally:
            # Restore the original model
            initialize_spacy.nlp = original_model


if __name__ == "__main__":
    unittest.main()
