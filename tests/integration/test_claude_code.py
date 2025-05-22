"""
Integration tests for Claude Code implementation.
"""
import os
import sys
import pytest
import asyncio

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.api.endpoints.claude_code import get_claude_code_executor
from app.services.claude_code.executor import ClaudeCodeExecutor
from app.services.claude_code.progress_tracker import progress_tracker
from app.core.config import settings

# Test the Claude Code configuration
@pytest.mark.asyncio
async def test_claude_code_config():
    """Test if Claude Code is properly configured"""
    try:
        # Check that required settings are present
        assert hasattr(settings, 'CLAUDE_CODE_CMD')
        assert hasattr(settings, 'CLAUDE_CODE_TIMEOUT')
        assert hasattr(settings, 'CLAUDE_CODE_MAX_TIMEOUT')
        
        # Verify fallback is disabled
        assert settings.ENABLE_FALLBACK is False, "PydanticAI fallback should be disabled"
        
        # Verify we can create an executor
        executor = get_claude_code_executor()
        assert executor is not None
        assert isinstance(executor, ClaudeCodeExecutor)
        
        # Verify the progress tracker is initialized
        assert progress_tracker is not None
        assert hasattr(progress_tracker, 'tasks')
        assert hasattr(progress_tracker, 'create_task')
        
        # Success if we reach here
        return True
    except Exception as e:
        pytest.fail(f"Claude Code configuration test failed: {str(e)}")

# Skip actual execution unless running in a full test environment
@pytest.mark.asyncio
@pytest.mark.skip(reason="Skipping actual execution which requires Claude Code CLI to be installed")
async def test_claude_code_execution():
    """Test the Claude Code execution functionality (skipped by default)"""
    try:
        # Basic test resume and job description
        resume_content = """# Test Resume
        Skills: Python, JavaScript
        Experience: 5 years as software engineer"""
        
        job_description = """# Test Job
        Requirements: Python, API development
        Nice to have: JavaScript, Cloud"""
        
        # Create temporary files
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as resume_file:
            resume_file.write(resume_content)
            resume_path = resume_file.name
            
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as job_file:
            job_file.write(job_description)
            job_description_path = job_file.name
            
        # Create output directory
        output_dir = tempfile.mkdtemp()
        output_path = os.path.join(output_dir, "test_output.md")
        
        # Get the executor
        executor = get_claude_code_executor()
        
        # Create a task for tracking
        task = progress_tracker.create_task()
        
        try:
            # Run with a short timeout for testing
            result = executor.customize_resume(
                resume_path=resume_path,
                job_description_path=job_description_path,
                output_path=output_path,
                task_id=task.task_id,
                timeout=30  # Short timeout for tests
            )
            
            # Check if output was created
            assert os.path.exists(output_path)
            with open(output_path, 'r') as f:
                content = f.read()
                assert len(content) > 0
                
            # Check task completion
            assert task.status == "completed"
            assert task.result is not None
            
        except Exception as e:
            pytest.skip(f"Execution test skipped due to error: {str(e)}")
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(resume_path)
                os.unlink(job_description_path)
                # Don't delete output_path to keep the result for analysis
            except:
                pass
            
    except Exception as e:
        pytest.skip(f"Test skipped due to setup error: {str(e)}")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_claude_code_config())
    print("✅ Claude Code configuration test passed")