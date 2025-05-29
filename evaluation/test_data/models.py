# ABOUTME: Pydantic models for test data structures
# ABOUTME: Defines TestCase, EvaluationResult, and TestDataset models
"""
Test Data Models

Pydantic models for representing test cases, evaluation results, and datasets
used throughout the evaluation framework.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TestCase(BaseModel):
    """Represents a single test case for evaluation."""
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique test case identifier")
    name: str = Field(..., description="Human-readable test case name")
    description: Optional[str] = Field(None, description="Detailed description of the test case")
    
    # Input data
    resume_content: str = Field(..., description="Resume content for testing")
    job_description: str = Field(..., description="Job description for testing")
    
    # Expected outputs
    expected_match_score: Optional[float] = Field(None, ge=0, le=100, description="Expected match score (0-100)")
    expected_skills: Optional[List[str]] = Field(None, description="Expected skills to be extracted")
    expected_technologies: Optional[List[str]] = Field(None, description="Expected technologies to be identified")
    
    # Metadata
    category: str = Field("general", description="Test case category (e.g., 'technical', 'management')")
    difficulty: str = Field("medium", description="Test case difficulty (easy, medium, hard)")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    
    # Ground truth data
    ground_truth: Dict[str, Any] = Field(default_factory=dict, description="Ground truth annotations")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('expected_match_score')
    @classmethod
    def validate_match_score(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Match score must be between 0 and 100')
        return v
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class EvaluationResult(BaseModel):
    """Represents the result of an evaluation run."""
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique result identifier")
    test_case_id: str = Field(..., description="ID of the test case that was evaluated")
    evaluator_name: str = Field(..., description="Name of the evaluator that produced this result")
    
    # Scores and metrics
    overall_score: float = Field(..., ge=0, le=1, description="Overall evaluation score (0-1)")
    detailed_scores: Dict[str, float] = Field(default_factory=dict, description="Detailed scores by metric")
    
    # Results data
    actual_output: Any = Field(None, description="Actual output from the system being evaluated")
    expected_output: Any = Field(None, description="Expected output for comparison")
    
    # Performance metrics
    execution_time: float = Field(0.0, ge=0, description="Execution time in seconds")
    api_calls_made: int = Field(0, ge=0, description="Number of API calls made")
    tokens_used: int = Field(0, ge=0, description="Total tokens used")
    
    # Analysis
    passed: bool = Field(False, description="Whether the evaluation passed")
    error_message: Optional[str] = Field(None, description="Error message if evaluation failed")
    notes: Optional[str] = Field(None, description="Additional notes about the evaluation")
    
    # Metadata
    evaluation_model: str = Field("", description="Model used for evaluation")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Configuration used")
    
    # Timestamps
    evaluated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class TestDataset(BaseModel):
    """Represents a collection of test cases."""
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique dataset identifier")
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    version: str = Field("1.0", description="Dataset version")
    
    # Test cases
    test_cases: List[TestCase] = Field(default_factory=list, description="List of test cases")
    
    # Metadata
    category: str = Field("general", description="Dataset category")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    author: Optional[str] = Field(None, description="Dataset author")
    
    # Statistics
    total_cases: int = Field(0, description="Total number of test cases")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.total_cases = len(self.test_cases)
    
    def add_test_case(self, test_case: TestCase) -> None:
        """Add a test case to the dataset."""
        self.test_cases.append(test_case)
        self.total_cases = len(self.test_cases)
        self.updated_at = datetime.now()
    
    def get_test_case(self, test_case_id: str) -> Optional[TestCase]:
        """Get a test case by ID."""
        for case in self.test_cases:
            if case.id == test_case_id:
                return case
        return None
    
    def filter_by_category(self, category: str) -> List[TestCase]:
        """Filter test cases by category."""
        return [case for case in self.test_cases if case.category == category]
    
    def filter_by_tags(self, tags: List[str]) -> List[TestCase]:
        """Filter test cases by tags."""
        return [case for case in self.test_cases if any(tag in case.tags for tag in tags)]
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )