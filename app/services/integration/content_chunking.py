"""
Content Chunking Service for ResumeAIAssistant.

This module implements the ContentChunkingService interface to provide intelligent 
content chunking capabilities for more reliable AI processing.
"""

import re
import nltk
from typing import List, Dict, Any, Optional
import logfire

from app.services.integration.interfaces import ContentChunkingService, SectionType


class IntegratedContentChunker(ContentChunkingService):
    """Implementation of the ContentChunkingService interface."""
    
    def __init__(self, default_max_chunk_size: int = 8000):
        """
        Initialize the content chunker.
        
        Args:
            default_max_chunk_size: Default maximum chunk size in characters
        """
        self.default_max_chunk_size = default_max_chunk_size
        self._ensure_nltk_resources()
        
    def _ensure_nltk_resources(self) -> None:
        """Ensure required NLTK resources are available."""
        try:
            # Try to load necessary NLTK resources
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            # Download if not available
            try:
                nltk.download('punkt', quiet=True)
            except Exception as e:
                logfire.warning(f"Could not download NLTK resources: {str(e)}")
    
    def chunk_content(self, content: str, section_type: Optional[SectionType] = None,
                     max_chunk_size: Optional[int] = None) -> List[str]:
        """
        Chunk content intelligently based on type and size limits.
        
        Args:
            content: The content to chunk
            section_type: Optional section type to inform chunking strategy
            max_chunk_size: Maximum chunk size (overrides default)
            
        Returns:
            List of content chunks
        """
        if not content:
            return []
            
        # Use provided max size or default
        chunk_size = max_chunk_size or self.default_max_chunk_size
        
        # Select chunking strategy based on section type
        if section_type == SectionType.EXPERIENCE:
            return self._chunk_experience_section(content, chunk_size)
        elif section_type == SectionType.EDUCATION:
            return self._chunk_education_section(content, chunk_size)
        elif section_type == SectionType.SKILLS:
            return self._chunk_skills_section(content, chunk_size)
        elif section_type == SectionType.SUMMARY:
            # Summary sections are typically short, keep them as a single chunk
            return [content] if len(content) <= chunk_size else self._chunk_by_paragraphs(content, chunk_size)
        else:
            # Default chunking strategy
            return self._chunk_by_paragraphs(content, chunk_size)
    
    def combine_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine results from multiple chunks into a single result.
        
        Args:
            chunk_results: List of results from processing chunks
            
        Returns:
            Combined result
        """
        if not chunk_results:
            return {}
            
        # Start with an empty combined result
        combined = {}
        
        # Strategy depends on the structure of results
        # Detect if results are scores, lists, or complex objects
        first_result = chunk_results[0]
        
        # Handle different result types
        if isinstance(first_result, dict):
            # Combine dictionaries
            return self._combine_dict_results(chunk_results)
        elif isinstance(first_result, list):
            # Combine lists
            return {"combined_results": sum(chunk_results, [])}
        elif isinstance(first_result, (int, float)):
            # Combine numeric values (average)
            return {"average": sum(chunk_results) / len(chunk_results)}
        else:
            # Default handling
            return {"chunks": chunk_results}
    
    def _chunk_by_paragraphs(self, content: str, max_size: int) -> List[str]:
        """
        Chunk content by paragraphs, respecting max size.
        
        Args:
            content: The content to chunk
            max_size: Maximum chunk size
            
        Returns:
            List of content chunks
        """
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', content)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # If this paragraph alone exceeds max size, split it by sentences
            if len(paragraph) > max_size:
                for sentence_chunk in self._chunk_by_sentences(paragraph, max_size):
                    chunks.append(sentence_chunk)
                continue
                
            # If adding this paragraph would exceed max size, start a new chunk
            if current_size + len(paragraph) > max_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0
                
            current_chunk.append(paragraph)
            current_size += len(paragraph) + 2  # +2 for newlines
        
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks
    
    def _chunk_by_sentences(self, content: str, max_size: int) -> List[str]:
        """
        Chunk content by sentences, respecting max size.
        
        Args:
            content: The content to chunk
            max_size: Maximum chunk size
            
        Returns:
            List of content chunks
        """
        try:
            # Use NLTK to split into sentences
            sentences = nltk.sent_tokenize(content)
        except Exception as e:
            # Fallback to basic sentence splitting
            logfire.warning(f"NLTK sentence tokenization failed: {str(e)}")
            sentences = re.split(r'(?<=[.!?])\s+', content)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If a single sentence is longer than max size, split it by words
            if len(sentence) > max_size:
                words = sentence.split()
                word_chunk = []
                word_chunk_size = 0
                
                for word in words:
                    if word_chunk_size + len(word) + 1 > max_size and word_chunk:
                        chunks.append(" ".join(word_chunk))
                        word_chunk = []
                        word_chunk_size = 0
                        
                    word_chunk.append(word)
                    word_chunk_size += len(word) + 1  # +1 for space
                
                if word_chunk:
                    chunks.append(" ".join(word_chunk))
                continue
                
            # If adding this sentence would exceed max size, start a new chunk
            if current_size + len(sentence) > max_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_size = 0
                
            current_chunk.append(sentence)
            current_size += len(sentence) + 1  # +1 for space
        
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks
    
    def _chunk_experience_section(self, content: str, max_size: int) -> List[str]:
        """
        Chunk experience section by job entries.
        
        Args:
            content: The content to chunk
            max_size: Maximum chunk size
            
        Returns:
            List of content chunks
        """
        # Try to identify job entries (typically start with company/title/date)
        # Common patterns in experience sections
        job_separators = [
            r'\n\s*\d{4}\s*[-–—]\s*\d{4}',  # Date ranges
            r'\n\s*\d{4}\s*[-–—]\s*present',  # Date to present
            r'\n\s*[A-Z][a-z]+\s+\d{4}',  # Month Year
            r'\n\s*[A-Z][A-Z]+',  # All caps company names
            r'\n\s*•\s+[A-Z]',  # Bullet points starting new job
            r'\n\s*\*\s+[A-Z]',  # Star bullet points
            r'\n\s*[-–—]\s+[A-Z]'  # Dash bullet points
        ]
        
        # Join patterns with OR
        pattern = '|'.join(job_separators)
        
        # Split content using the pattern (keep the separator with the following content)
        parts = re.split(f'({pattern})', content)
        
        # Pair separators with their content
        job_entries = []
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                job_entries.append(parts[i] + parts[i + 1])
            else:
                job_entries.append(parts[i])
        
        # If no job entries detected or only one entry, fall back to paragraph chunking
        if len(job_entries) <= 1:
            return self._chunk_by_paragraphs(content, max_size)
        
        # Group job entries into chunks respecting max size
        return self._group_entries(job_entries, max_size)
    
    def _chunk_education_section(self, content: str, max_size: int) -> List[str]:
        """
        Chunk education section by education entries.
        
        Args:
            content: The content to chunk
            max_size: Maximum chunk size
            
        Returns:
            List of content chunks
        """
        # Similar to experience, but with education-specific patterns
        education_separators = [
            r'\n\s*\d{4}\s*[-–—]\s*\d{4}',  # Date ranges
            r'\n\s*\d{4}\s*[-–—]\s*present',  # Date to present
            r'\n\s*[A-Z][a-z]+\s+\d{4}',  # Month Year
            r'\n\s*[A-Z][A-Z]+',  # All caps school names
            r'\n\s*Bachelor',  # Degree names
            r'\n\s*Master',
            r'\n\s*Ph\\.?D'
        ]
        
        # Join patterns with OR
        pattern = '|'.join(education_separators)
        
        # Split content using the pattern
        parts = re.split(f'({pattern})', content)
        
        # Pair separators with their content
        education_entries = []
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                education_entries.append(parts[i] + parts[i + 1])
            else:
                education_entries.append(parts[i])
        
        # If no education entries detected or only one entry, fall back to paragraph chunking
        if len(education_entries) <= 1:
            return self._chunk_by_paragraphs(content, max_size)
        
        # Group education entries into chunks respecting max size
        return self._group_entries(education_entries, max_size)
    
    def _chunk_skills_section(self, content: str, max_size: int) -> List[str]:
        """
        Chunk skills section intelligently.
        
        Args:
            content: The content to chunk
            max_size: Maximum chunk size
            
        Returns:
            List of content chunks
        """
        # Skills are often in lists or comma-separated, try to group by skill categories
        # Look for common skill category headers
        skill_categories = [
            "Technical Skills",
            "Soft Skills",
            "Languages",
            "Tools",
            "Frameworks",
            "Programming Languages",
            "Software",
            "Certifications"
        ]
        
        # Try to split by skill categories
        pattern = '|'.join(re.escape(category) for category in skill_categories)
        parts = re.split(f'(\\b(?:{pattern})\\b)', content)
        
        # Group categories with their content
        skill_groups = []
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                skill_groups.append(parts[i] + parts[i + 1])
            else:
                skill_groups.append(parts[i])
        
        # If no categories detected, split by lines or commas
        if len(skill_groups) <= 1:
            # Check if skills are listed line by line
            lines = content.split('\n')
            if len(lines) > 3:  # Multiple lines suggest a list
                return self._group_entries(lines, max_size)
                
            # Check if skills are comma separated
            if ',' in content:
                skill_items = [s.strip() for s in content.split(',')]
                if len(skill_items) > 3:  # Multiple skills
                    return self._group_entries(skill_items, max_size)
            
            # Fall back to paragraph chunking
            return self._chunk_by_paragraphs(content, max_size)
        
        # Group skill categories into chunks respecting max size
        return self._group_entries(skill_groups, max_size)
    
    def _group_entries(self, entries: List[str], max_size: int) -> List[str]:
        """
        Group entries into chunks respecting max size.
        
        Args:
            entries: List of content entries
            max_size: Maximum chunk size
            
        Returns:
            List of content chunks
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
                
            # If this entry alone exceeds max size, chunk it further
            if len(entry) > max_size:
                # Add any existing chunk
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Chunk the large entry separately
                entry_chunks = self._chunk_by_paragraphs(entry, max_size)
                chunks.extend(entry_chunks)
                continue
                
            # If adding this entry would exceed max size, start a new chunk
            if current_size + len(entry) > max_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0
                
            current_chunk.append(entry)
            current_size += len(entry) + 2  # +2 for newlines
        
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks
    
    def _combine_dict_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine dictionary results from multiple chunks.
        
        Args:
            results: List of dictionary results
            
        Returns:
            Combined dictionary result
        """
        if not results:
            return {}
            
        # Check for common result structure
        common_keys = set(results[0].keys())
        for result in results[1:]:
            common_keys &= set(result.keys())
            
        combined = {}
        
        # Process each common key
        for key in common_keys:
            # Get all values for this key
            values = [result[key] for result in results]
            
            # Combine based on value type
            if all(isinstance(v, (int, float)) for v in values):
                # For numeric values, use average
                combined[key] = sum(values) / len(values)
            elif all(isinstance(v, list) for v in values):
                # For lists, concatenate them
                combined[key] = sum(values, [])
            elif all(isinstance(v, dict) for v in values):
                # For dictionaries, recursively combine
                combined[key] = self._combine_dict_results(values)
            elif all(isinstance(v, str) for v in values):
                # For strings, join with newlines
                combined[key] = "\n".join(values)
            else:
                # For mixed types, use a list
                combined[key] = values
                
        # Add any non-common keys from the first chunk
        for key, value in results[0].items():
            if key not in common_keys:
                combined[key] = value
                
        return combined