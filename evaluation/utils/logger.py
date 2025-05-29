# ABOUTME: Logging utilities for the evaluation framework
# ABOUTME: Provides structured logging with appropriate levels and formatting
"""
Evaluation Framework Logging

Provides structured logging capabilities for the evaluation framework with
appropriate levels, formatting, and output management.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class EvaluationFormatter(logging.Formatter):
    """Custom formatter for evaluation framework logs."""
    
    def __init__(self):
        # Define colors for different log levels
        self.colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        self.reset = '\033[0m'
        
        # Define format string
        fmt = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        super().__init__(fmt, datefmt='%Y-%m-%d %H:%M:%S')
    
    def format(self, record):
        # Add color to level name for console output
        if hasattr(record, '_console_output') and record._console_output:
            level_color = self.colors.get(record.levelname, '')
            record.levelname = f"{level_color}{record.levelname}{self.reset}"
        
        return super().format(record)


def setup_logging(
    name: str = "evaluation",
    level: str = "INFO",
    log_to_file: bool = True,
    log_file_path: Optional[Path] = None
) -> logging.Logger:
    """
    Set up logging for the evaluation framework.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_file_path: Path to log file (auto-generated if None)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    formatter = EvaluationFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    # Mark records for console coloring
    console_handler.addFilter(lambda record: setattr(record, '_console_output', True) or True)
    logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        if log_file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file_path = Path(f"evaluation_{timestamp}.log")
        
        # Ensure log directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)  # File gets all messages
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to file: {log_file_path}")
    
    return logger


def get_evaluation_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger for evaluation framework components.
    
    Args:
        name: Component name (will be prefixed with 'evaluation.')
        
    Returns:
        Logger instance
    """
    from ..config import get_config
    
    config = get_config()
    
    if name:
        logger_name = f"evaluation.{name}"
    else:
        logger_name = "evaluation"
    
    return setup_logging(
        name=logger_name,
        level=config.log_level,
        log_to_file=config.log_to_file,
        log_file_path=config.log_file_path
    )