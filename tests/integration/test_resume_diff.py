"""
Tests for the resume diff view feature.
"""
import unittest
from unittest.mock import patch, MagicMock
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.api import app
from app.models.resume import Resume, ResumeVersion
from app.services.diff_service import generate_resume_diff, get_diff_statistics

client = TestClient(app)

class TestResumeDiffView(unittest.TestCase):
    """Test cases for the resume diff view feature."""
    
    def setUp(self):
        """Set up test data."""
        # Mock resume and version data
        self.resume_id = str(uuid.uuid4())
        self.original_version_id = str(uuid.uuid4())
        self.customized_version_id = str(uuid.uuid4())
        
        self.original_content = "Python developer with 3 years of experience."
        self.customized_content = "Python developer with 5 years of experience in Django."
        
        # Mock resume object
        self.mock_resume = Resume(
            id=self.resume_id,
            title="Test Resume"
        )
        
        # Mock original version
        self.mock_original_version = ResumeVersion(
            id=self.original_version_id,
            resume_id=self.resume_id,
            content=self.original_content,
            version_number=1,
            is_customized=0
        )
        
        # Mock customized version
        self.mock_customized_version = ResumeVersion(
            id=self.customized_version_id,
            resume_id=self.resume_id,
            content=self.customized_content,
            version_number=2,
            is_customized=1
        )
    
    @patch('app.api.endpoints.resumes.get_db')
    def test_get_resume_version_diff(self, mock_get_db):
        """Test the resume diff view endpoint."""
        # Set up mock database session
        mock_db = MagicMock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Create mock query objects
        mock_resume_query = MagicMock()
        mock_version_query = MagicMock()
        mock_original_query = MagicMock()
        
        # Set up the query chain for resume
        mock_db.query.side_effect = lambda model: {
            Resume: mock_resume_query,
            ResumeVersion: mock_version_query
        }.get(model, MagicMock())
        
        # Set up filter and first for resume query
        mock_resume_query.filter.return_value.first.return_value = self.mock_resume
        
        # Set up filter and first for version query (customized version)
        mock_version_query.filter.return_value.first.return_value = self.mock_customized_version
        
        # Set up filter, order_by, and first for original version query
        mock_version_query.filter.return_value.order_by.return_value.first.return_value = self.mock_original_version
        
        # Call the endpoint
        response = client.get(f"/api/v1/resumes/{self.resume_id}/versions/{self.customized_version_id}/diff")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response data
        self.assertEqual(data["id"], self.resume_id)
        self.assertEqual(data["title"], "Test Resume")
        self.assertEqual(data["original_content"], self.original_content)
        self.assertEqual(data["customized_content"], self.customized_content)
        self.assertTrue(data["is_diff_view"])
        
        # Verify diff content contains expected HTML
        self.assertIn("Python developer with ", data["diff_content"])
        
        # Verify diff statistics
        self.assertIn("additions", data["diff_statistics"])
        self.assertIn("deletions", data["diff_statistics"])
        self.assertIn("modifications", data["diff_statistics"])
        self.assertIn("unchanged", data["diff_statistics"])
    
    @patch('app.api.endpoints.resumes.get_db')
    def test_get_resume_version_diff_with_specified_original(self, mock_get_db):
        """Test the resume diff view endpoint with a specified original version."""
        # Set up mock database session
        mock_db = MagicMock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Create mock query objects
        mock_resume_query = MagicMock()
        mock_version_query = MagicMock()
        
        # Set up the query chain for resume
        mock_db.query.side_effect = lambda model: {
            Resume: mock_resume_query,
            ResumeVersion: mock_version_query
        }.get(model, MagicMock())
        
        # Set up filter and first for resume query
        mock_resume_query.filter.return_value.first.return_value = self.mock_resume
        
        # Set up filter and first for version queries
        mock_version_query.filter.return_value.first.side_effect = [
            self.mock_customized_version,  # First call - customized version
            self.mock_original_version      # Second call - original version
        ]
        
        # Call the endpoint with original_version_id
        response = client.get(
            f"/api/v1/resumes/{self.resume_id}/versions/{self.customized_version_id}/diff",
            params={"original_version_id": self.original_version_id}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response data
        self.assertEqual(data["id"], self.resume_id)
        self.assertEqual(data["original_content"], self.original_content)
        self.assertEqual(data["customized_content"], self.customized_content)
    
    @patch('app.api.endpoints.resumes.get_db')
    def test_get_resume_version_diff_non_customized(self, mock_get_db):
        """Test the resume diff view endpoint with a non-customized version."""
        # Set up mock database session
        mock_db = MagicMock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Create a non-customized version
        non_customized_version = ResumeVersion(
            id=str(uuid.uuid4()),
            resume_id=self.resume_id,
            content=self.original_content,
            version_number=1,
            is_customized=0
        )
        
        # Create mock query objects
        mock_resume_query = MagicMock()
        mock_version_query = MagicMock()
        
        # Set up the query chain for resume
        mock_db.query.side_effect = lambda model: {
            Resume: mock_resume_query,
            ResumeVersion: mock_version_query
        }.get(model, MagicMock())
        
        # Set up filter and first for resume query
        mock_resume_query.filter.return_value.first.return_value = self.mock_resume
        
        # Set up filter and first for version query (non-customized version)
        mock_version_query.filter.return_value.first.return_value = non_customized_version
        
        # Call the endpoint
        response = client.get(f"/api/v1/resumes/{self.resume_id}/versions/{non_customized_version.id}/diff")
        
        # Check response - should be a 400 error
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Diff view is only available for customized resume versions", data["detail"])
    
    def test_generate_resume_diff(self):
        """Test the diff generation function."""
        original = "Python developer."
        customized = "Experienced Python developer."
        
        diff = generate_resume_diff(original, customized)
        
        # Should highlight the added word
        self.assertIn('<span class="addition">Experienced </span>', diff)
        self.assertIn('Python developer.', diff)
    
    def test_get_diff_statistics(self):
        """Test the diff statistics function."""
        original = "Python developer with 3 years experience."
        customized = "Python developer with 5 years experience in Django."
        
        stats = get_diff_statistics(original, customized)
        
        # Should have some additions and no deletions
        self.assertGreater(stats["additions"], 0)
        self.assertEqual(stats["deletions"], 0)
        self.assertGreater(stats["unchanged"], 0)


if __name__ == "__main__":
    unittest.main()
