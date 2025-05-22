"""
Factory for creating integrated components for ResumeAIAssistant.

This module provides a unified factory for creating and configuring all 
integrated components, ensuring proper initialization and dependency management.
"""

from typing import Dict, Any, Optional

from app.services.integration.interfaces import (
    TaskOrchestrator, ProgressTracker, ErrorHandler, CircuitBreaker, 
    SectionAnalyzer, RequirementsExtractor, ContentChunkingService,
    SectionType
)

from app.services.integration.orchestrator import IntegratedTaskOrchestrator
from app.services.integration.progress_tracking import IntegratedProgressTracker
from app.services.integration.error_handling import (
    IntegratedErrorHandler, IntegratedCircuitBreaker
)
from app.services.integration.section_analyzer import SectionAnalyzerFactory
from app.services.integration.requirements_extractor import (
    IntegratedRequirementsExtractor, MockRequirementsExtractor
)
from app.services.integration.content_chunking import IntegratedContentChunker


class IntegrationFactory:
    """Factory for creating and configuring all integrated components."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the integration factory.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._components = {}
    
    def create_orchestrator(self, max_concurrent_tasks: Optional[int] = None) -> TaskOrchestrator:
        """
        Create a task orchestrator instance.
        
        Args:
            max_concurrent_tasks: Optional maximum number of concurrent tasks
            
        Returns:
            Configured task orchestrator
        """
        # Use config value or default
        if max_concurrent_tasks is None:
            max_concurrent_tasks = self.config.get("max_concurrent_tasks", 5)
            
        # Create orchestrator if not already created
        if "orchestrator" not in self._components:
            orchestrator = IntegratedTaskOrchestrator(
                max_concurrent_tasks=max_concurrent_tasks
            )
            self._components["orchestrator"] = orchestrator
            
        return self._components["orchestrator"]
    
    def create_progress_tracker(self) -> ProgressTracker:
        """
        Create a progress tracker instance.
        
        Returns:
            Configured progress tracker
        """
        if "progress_tracker" not in self._components:
            progress_tracker = IntegratedProgressTracker()
            self._components["progress_tracker"] = progress_tracker
            
        return self._components["progress_tracker"]
    
    def create_error_handler(self) -> ErrorHandler:
        """
        Create an error handler instance.
        
        Returns:
            Configured error handler
        """
        if "error_handler" not in self._components:
            error_handler = IntegratedErrorHandler()
            self._components["error_handler"] = error_handler
            
        return self._components["error_handler"]
    
    def create_circuit_breaker(
        self, 
        failure_threshold: Optional[int] = None,
        recovery_time_seconds: Optional[int] = None
    ) -> CircuitBreaker:
        """
        Create a circuit breaker instance.
        
        Args:
            failure_threshold: Optional failure threshold
            recovery_time_seconds: Optional recovery time
            
        Returns:
            Configured circuit breaker
        """
        # Use config values or defaults
        if failure_threshold is None:
            failure_threshold = self.config.get("circuit_breaker_threshold", 3)
            
        if recovery_time_seconds is None:
            recovery_time_seconds = self.config.get("circuit_breaker_recovery_time", 60)
            
        if "circuit_breaker" not in self._components:
            circuit_breaker = IntegratedCircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_time_seconds=recovery_time_seconds
            )
            self._components["circuit_breaker"] = circuit_breaker
            
        return self._components["circuit_breaker"]
    
    def create_section_analyzer(
        self, 
        section_type: SectionType,
        customization_level: str = "balanced"
    ) -> SectionAnalyzer:
        """
        Create a section analyzer for the specified section type.
        
        Args:
            section_type: Type of section to analyze
            customization_level: Level of customization
            
        Returns:
            Configured section analyzer
        """
        # Create a new analyzer each time since they're stateless
        return SectionAnalyzerFactory.create_analyzer(
            section_type=section_type,
            customization_level=customization_level
        )
    
    def create_requirements_extractor(self, use_mock: bool = False) -> RequirementsExtractor:
        """
        Create a requirements extractor instance.
        
        Args:
            use_mock: Whether to use the mock implementation
            
        Returns:
            Configured requirements extractor
        """
        if use_mock:
            return MockRequirementsExtractor()
        
        if "requirements_extractor" not in self._components:
            requirements_extractor = IntegratedRequirementsExtractor()
            self._components["requirements_extractor"] = requirements_extractor
            
        return self._components["requirements_extractor"]
    
    def create_content_chunker(self, max_chunk_size: Optional[int] = None) -> ContentChunkingService:
        """
        Create a content chunking service instance.
        
        Args:
            max_chunk_size: Optional maximum chunk size
            
        Returns:
            Configured content chunker
        """
        # Use config value or default
        if max_chunk_size is None:
            max_chunk_size = self.config.get("max_chunk_size", 8000)
            
        if "content_chunker" not in self._components:
            content_chunker = IntegratedContentChunker(
                default_max_chunk_size=max_chunk_size
            )
            self._components["content_chunker"] = content_chunker
            
        return self._components["content_chunker"]
    
    def create_all_components(self) -> Dict[str, Any]:
        """
        Create all components at once.
        
        Returns:
            Dictionary of all components
        """
        components = {
            "orchestrator": self.create_orchestrator(),
            "progress_tracker": self.create_progress_tracker(),
            "error_handler": self.create_error_handler(),
            "circuit_breaker": self.create_circuit_breaker(),
            "requirements_extractor": self.create_requirements_extractor(),
            "content_chunker": self.create_content_chunker()
        }
        
        # Section analyzers are created on demand
        
        return components


# Singleton factory instance
default_factory = IntegrationFactory()


def get_integration_factory(config: Optional[Dict[str, Any]] = None) -> IntegrationFactory:
    """
    Get the integration factory instance.
    
    Args:
        config: Optional configuration to apply
        
    Returns:
        Integration factory instance
    """
    global default_factory
    
    if config is not None:
        default_factory = IntegrationFactory(config)
        
    return default_factory