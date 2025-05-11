"""
Integration package for ResumeAIAssistant components.

This package provides the integration layer between:
1. Micro-Task Orchestration Framework 
2. Resume Section Analyzer Framework
3. Key Requirements Extractor
4. Smart Request Chunking System
"""

from app.services.integration.interfaces import (
    Task, TaskOrchestrator, ProgressTracker, ErrorHandler, CircuitBreaker,
    SectionAnalyzer, RequirementsExtractor, ContentChunkingService,
    Priority, TaskStatus, TaskResult, SectionType
)