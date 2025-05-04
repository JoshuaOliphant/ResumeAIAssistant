"""
Test script for the task-based model selection utility.

This script tests the functionality of selecting appropriate models for different tasks
based on task requirements, available providers, and cost considerations.
"""

import asyncio
import logfire
from typing import List, Optional, Dict, Any
import os
from unittest.mock import patch

# Set up logging
try:
    logfire.configure(min_level="INFO", sinks=["console"])
except Exception as e:
    print(f"Warning: Unable to configure logfire: {str(e)}")

# Import the model selector module
from app.services.model_selector import (
    ModelTier,
    ModelProvider,
    ModelCapability,
    get_available_models,
    select_model_for_task,
    get_fallback_chain,
    get_model_config_for_task
)

# Sample resume content for testing
SAMPLE_RESUME = """
# John Doe
Software Engineer | johndoe@example.com | (123) 456-7890

## Summary
Experienced software engineer with 8+ years of experience in full-stack development, 
specializing in React, Node.js, and cloud infrastructure.

## Experience
### Senior Software Engineer | ABC Tech | 2019 - Present
- Led a team of 5 engineers in developing a high-traffic e-commerce platform
- Implemented microservices architecture using Node.js, resulting in 40% improved scalability
- Reduced page load time by 60% through optimization of React components and server-side rendering

### Software Engineer | XYZ Inc. | 2015 - 2019
- Developed and maintained RESTful APIs for mobile and web applications
- Implemented automated testing, increasing code coverage from 65% to 95%
- Participated in agile development workflows, including daily stand-ups and sprint planning

## Education
### Bachelor of Science in Computer Science | State University | 2015
- GPA: 3.8/4.0
- Senior Thesis: "Optimizing Database Performance in Distributed Systems"

## Skills
**Programming Languages**: JavaScript, TypeScript, Python, Java, SQL
**Frameworks/Libraries**: React, Node.js, Express, Django, Spring Boot
**Tools & Platforms**: AWS, Docker, Kubernetes, Git, Jenkins, MongoDB, PostgreSQL
"""

# Sample job description for testing
SAMPLE_JOB = """
# Senior Full Stack Engineer

## About Us
We're a fast-growing technology company building innovative solutions for the healthcare sector.

## Job Description
We are looking for a Senior Full Stack Engineer to join our engineering team. The ideal candidate will 
have expertise in building complex web applications and will collaborate with cross-functional teams 
to deliver high-quality software solutions.

## Requirements
- 5+ years of experience in full-stack web development
- Strong proficiency in JavaScript/TypeScript, React, and Node.js
- Experience with database design and SQL/NoSQL databases
- Understanding of cloud services (AWS, Azure, or GCP)
- Knowledge of containerization tools like Docker and Kubernetes
- Experience with agile development methodologies
- Bachelor's degree in Computer Science or related field

## Responsibilities
- Design and implement new features for our healthcare platform
- Write clean, maintainable, and efficient code
- Collaborate with product managers, designers, and other engineers
- Participate in code reviews and mentor junior developers
- Troubleshoot and debug issues in production environments
- Implement automated tests and deployment pipelines

## Benefits
- Competitive salary and equity package
- Health, dental, and vision insurance
- Flexible work hours and remote work options
- Professional development budget
- Generous vacation policy
"""

def test_model_selection_with_mocked_api_keys():
    """Test model selection with mocked API keys for all providers."""
    print("\n=== Testing Model Selection with All Providers Available ===")
    
    # Mock environment variables to simulate all API keys being available
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "mock-anthropic-key",
        "OPENAI_API_KEY": "mock-openai-key",
        "GEMINI_API_KEY": "mock-gemini-key"
    }):
        # Mock the settings object
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "mock-anthropic-key"
            mock_settings.OPENAI_API_KEY = "mock-openai-key"
            mock_settings.GEMINI_API_KEY = "mock-gemini-key"
            mock_settings.PYDANTICAI_TEMPERATURE = 0.7
            mock_settings.PYDANTICAI_MAX_TOKENS = 4000
            
            # Test getting available models
            models = get_available_models()
            print(f"Available models: {len(models)}")
            for provider in [ModelProvider.ANTHROPIC, ModelProvider.OPENAI, ModelProvider.GOOGLE]:
                provider_models = [name for name, config in models.items() if config["provider"] == provider]
                print(f"{provider.value} models: {len(provider_models)} ({', '.join(provider_models)})")
            
            # Test model selection for different tasks
            test_tasks = [
                "resume_evaluation",
                "keyword_extraction",
                "optimization_plan",
                "cover_letter_generation",
                "job_classifier"
            ]
            
            print("\n=== Model Selection by Task ===")
            for task in test_tasks:
                model, config = select_model_for_task(task)
                print(f"{task}: {model} (Provider: {config['provider'].value}, Tier: {config['tier'].value})")
                
                # Test fallback chain
                fallbacks = get_fallback_chain(model, task)
                print(f"  Fallbacks: {', '.join(fallbacks)}")
                
                # Test with different cost sensitivities
                budget_model, _ = select_model_for_task(task, cost_sensitivity=2.0)  # Cost-sensitive
                premium_model, _ = select_model_for_task(task, cost_sensitivity=0.2)  # Premium-focused
                
                print(f"  Cost-sensitive choice: {budget_model}")
                print(f"  Premium choice: {premium_model}")
            
            print("\n=== Complete Configuration Example ===")
            # Test getting complete configuration
            config = get_model_config_for_task(
                task_name="resume_evaluation",
                content=SAMPLE_RESUME,
                job_description=SAMPLE_JOB,
                industry="technology"
            )
            
            print(f"Complete config for resume_evaluation:")
            print(f"Model: {config['model']}")
            print(f"Temperature: {config['temperature']}")
            print(f"Max tokens: {config['max_tokens']}")
            print(f"Fallbacks: {config['fallback_config']}")
            if 'thinking_config' in config:
                print(f"Thinking config: {config['thinking_config']}")

def test_model_selection_with_limited_providers():
    """Test model selection with only some providers available."""
    print("\n=== Testing Model Selection with Limited Providers ===")
    
    # Test with only Anthropic available
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "mock-anthropic-key",
        "OPENAI_API_KEY": "",
        "GEMINI_API_KEY": ""
    }):
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "mock-anthropic-key"
            mock_settings.OPENAI_API_KEY = None
            mock_settings.GEMINI_API_KEY = None
            mock_settings.PYDANTICAI_TEMPERATURE = 0.7
            mock_settings.PYDANTICAI_MAX_TOKENS = 4000
            
            print("\nWith only Anthropic available:")
            models = get_available_models()
            print(f"Available models: {len(models)}")
            
            # Test model selection for a premium task
            model, config = select_model_for_task("resume_evaluation")
            print(f"resume_evaluation: {model} (Provider: {config['provider'].value})")
            
            # Test model selection for an economy task
            model, config = select_model_for_task("keyword_extraction")
            print(f"keyword_extraction: {model} (Provider: {config['provider'].value})")
    
    # Test with only Google available
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "",
        "OPENAI_API_KEY": "",
        "GEMINI_API_KEY": "mock-gemini-key"
    }):
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = None
            mock_settings.OPENAI_API_KEY = None
            mock_settings.GEMINI_API_KEY = "mock-gemini-key"
            mock_settings.PYDANTICAI_TEMPERATURE = 0.7
            mock_settings.PYDANTICAI_MAX_TOKENS = 4000
            
            print("\nWith only Google available:")
            models = get_available_models()
            print(f"Available models: {len(models)}")
            
            # Test model selection for a premium task
            model, config = select_model_for_task("resume_evaluation")
            print(f"resume_evaluation: {model} (Provider: {config['provider'].value})")
            
            # Test model selection for an economy task
            model, config = select_model_for_task("keyword_extraction")
            print(f"keyword_extraction: {model} (Provider: {config['provider'].value})")

def test_provider_preference():
    """Test model selection with provider preferences."""
    print("\n=== Testing Model Selection with Provider Preferences ===")
    
    # Mock environment variables to simulate all API keys being available
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "mock-anthropic-key",
        "OPENAI_API_KEY": "mock-openai-key",
        "GEMINI_API_KEY": "mock-gemini-key"
    }):
        # Mock the settings object
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "mock-anthropic-key"
            mock_settings.OPENAI_API_KEY = "mock-openai-key"
            mock_settings.GEMINI_API_KEY = "mock-gemini-key"
            mock_settings.PYDANTICAI_TEMPERATURE = 0.7
            mock_settings.PYDANTICAI_MAX_TOKENS = 4000
            
            # Test with different provider preferences
            for provider in [ModelProvider.ANTHROPIC, ModelProvider.OPENAI, ModelProvider.GOOGLE]:
                print(f"\nWith {provider.value} preference:")
                
                # Test for complex task
                model, config = select_model_for_task(
                    "resume_evaluation", 
                    preferred_provider=provider
                )
                print(f"resume_evaluation: {model} (Provider: {config['provider'].value})")
                
                # Test for simple task
                model, config = select_model_for_task(
                    "keyword_extraction", 
                    preferred_provider=provider
                )
                print(f"keyword_extraction: {model} (Provider: {config['provider'].value})")
            
            # Test with unavailable provider preference
            # First, remove ANTHROPIC API key
            mock_settings.ANTHROPIC_API_KEY = None
            
            # Now test selecting with Anthropic preference
            print("\nWith unavailable provider preference:")
            model, config = select_model_for_task(
                "resume_evaluation", 
                preferred_provider=ModelProvider.ANTHROPIC
            )
            print(f"resume_evaluation: {model} (Provider: {config['provider'].value}, " + 
                  f"despite requesting {ModelProvider.ANTHROPIC.value})")

def test_cost_sensitivity():
    """Test the effect of cost sensitivity on model selection."""
    print("\n=== Testing Cost Sensitivity ===")
    
    # Mock environment variables to simulate all API keys being available
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "mock-anthropic-key",
        "OPENAI_API_KEY": "mock-openai-key",
        "GEMINI_API_KEY": "mock-gemini-key"
    }):
        # Mock the settings object
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "mock-anthropic-key"
            mock_settings.OPENAI_API_KEY = "mock-openai-key"
            mock_settings.GEMINI_API_KEY = "mock-gemini-key"
            mock_settings.PYDANTICAI_TEMPERATURE = 0.7
            mock_settings.PYDANTICAI_MAX_TOKENS = 4000
            
            # Test with different cost sensitivity values
            sensitivity_levels = [0.0, 0.5, 1.0, 1.5, 2.0]
            
            for sensitivity in sensitivity_levels:
                print(f"\nCost sensitivity {sensitivity}:")
                
                # Test for premium tasks
                model, config = select_model_for_task(
                    "resume_evaluation", 
                    cost_sensitivity=sensitivity
                )
                print(f"resume_evaluation: {model} (Provider: {config['provider'].value}, " + 
                      f"Tier: {config['tier'].value})")
                
                # Test for economy tasks
                model, config = select_model_for_task(
                    "keyword_extraction", 
                    cost_sensitivity=sensitivity
                )
                print(f"keyword_extraction: {model} (Provider: {config['provider'].value}, " + 
                      f"Tier: {config['tier'].value})")

def run_tests():
    """Run all tests."""
    try:
        test_model_selection_with_mocked_api_keys()
        test_model_selection_with_limited_providers()
        test_provider_preference()
        test_cost_sensitivity()
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing Task-Based Model Selection utility...")
    run_tests()
    print("\nTests completed.")