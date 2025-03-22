"""
Tests for the resume diff service.
"""
import unittest
from app.services.diff_service import (
    generate_resume_diff, 
    generate_markdown_diff,
    generate_word_level_diff,
    get_diff_statistics
)

class TestDiffService(unittest.TestCase):
    """Test cases for the diff service."""
    
    def test_generate_resume_diff_no_changes(self):
        """Test diff generation with identical texts."""
        original = "This is a test resume."
        customized = "This is a test resume."
        
        diff = generate_resume_diff(original, customized)
        
        # No styling should be added for identical texts
        self.assertEqual(diff, "This is a test resume.")
    
    def test_generate_resume_diff_with_addition(self):
        """Test diff generation with added content."""
        original = "Python developer."
        customized = "Experienced Python developer."
        
        diff = generate_resume_diff(original, customized)
        
        # Should highlight the added word
        self.assertIn('<span class="addition">Experienced </span>', diff)
        self.assertIn('Python developer.', diff)
    
    def test_generate_resume_diff_with_deletion(self):
        """Test diff generation with deleted content."""
        original = "Senior Python developer with 5 years experience."
        customized = "Python developer with 5 years experience."
        
        diff = generate_resume_diff(original, customized)
        
        # Should show deleted word with strikethrough
        self.assertIn('<span class="deletion"><del>Senior </del></span>', diff)
        self.assertIn('Python developer with 5 years experience.', diff)
    
    def test_generate_resume_diff_with_replacement(self):
        """Test diff generation with replaced content."""
        original = "Python developer with 3 years experience."
        customized = "Python developer with 5 years experience."
        
        diff = generate_resume_diff(original, customized)
        
        # Should show deleted and added content
        self.assertIn('<span class="deletion"><del>3</del></span>', diff)
        self.assertIn('<span class="addition">5</span>', diff)
    
    def test_generate_markdown_diff(self):
        """Test markdown diff generation."""
        original = "Python developer with 3 years experience."
        customized = "Python developer with 5 years experience."
        
        diff = generate_markdown_diff(original, customized)
        
        # Should use markdown syntax for diff
        self.assertIn('**~~3~~**', diff)
        self.assertIn('**++5++**', diff)
    
    def test_word_level_diff(self):
        """Test word-level diff generation."""
        original = "Python developer with experience in Django."
        customized = "Python developer with extensive experience in Django and Flask."
        
        diff = generate_word_level_diff(original, customized)
        
        # Should highlight the word-level changes
        self.assertIn('with ', diff)
        self.assertIn('<span class="addition">extensive </span>', diff)
        # The exact output format might vary depending on the diff algorithm
        # Just check for key parts
        self.assertIn('experience in', diff)
        self.assertIn('Django', diff)
        self.assertIn('Flask', diff)
    
    def test_diff_statistics(self):
        """Test diff statistics calculation."""
        original = "Python developer with experience in Django."
        customized = "Python developer with extensive experience in Django and Flask."
        
        stats = get_diff_statistics(original, customized)
        
        # Should count additions correctly
        self.assertGreater(stats["additions"], 0)
        self.assertEqual(stats["deletions"], 0)
        self.assertGreater(stats["unchanged"], 0)

if __name__ == "__main__":
    unittest.main()
