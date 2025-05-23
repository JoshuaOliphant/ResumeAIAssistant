"""
Integration tests for Claude SDK features and enhancements.

This module tests the new SDK-specific features including:
- MCP configuration generation
- System prompt file creation
- Enhanced stream parsing with stream-json format
- Progress tracking enhancements
- End-to-end SDK feature integration
"""

import os
import sys
import json
import uuid
import pytest
import tempfile
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.claude_code.executor import ClaudeCodeExecutor, ClaudeCodeExecutionError
from app.services.claude_code.progress_tracker import ProgressTracker, Task, progress_tracker
from app.services.claude_code.log_streamer import get_log_streamer
from app.services.claude_code import prompt_manager, output_parser
from app.core.config import settings


class TestClaudeSDKFeatures:
    """Test class for Claude SDK specific features"""
    
    def setup_method(self):
        """Set up test environment for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = tempfile.mkdtemp()
        self.prompt_template_path = os.path.join(self.temp_dir, "prompt_template.txt")
        
        # Create a basic prompt template
        with open(self.prompt_template_path, 'w') as f:
            f.write("Test prompt template for resume customization")
        
        # Initialize executor
        self.executor = ClaudeCodeExecutor(
            working_dir=self.working_dir,
            prompt_template_path=self.prompt_template_path,
            claude_cmd="claude"
        )
    
    def teardown_method(self):
        """Clean up after each test"""
        # Clean up temporary directories
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
            shutil.rmtree(self.working_dir)
        except:
            pass


class TestSystemPromptGeneration(TestClaudeSDKFeatures):
    """Test system prompt file creation functionality"""
    
    def test_system_prompt_creation_default(self):
        """Test creating system prompt with default content"""
        with patch('app.core.config.settings') as mock_settings:
            # Configure mock settings without custom system prompt
            mock_settings.CLAUDE_SYSTEM_PROMPT = None
            
            # Create system prompt
            system_prompt_path = prompt_manager.prepare_system_prompt(self.temp_dir)
            
            # Verify file was created
            assert system_prompt_path is not None
            assert os.path.exists(system_prompt_path)
            
            # Verify content contains default system prompt
            with open(system_prompt_path, 'r') as f:
                content = f.read()
                
            assert "expert resume customization assistant" in content
            assert "Never fabricate experiences" in content
            assert "evaluator-optimizer workflow" in content
    
    def test_system_prompt_creation_custom(self):
        """Test creating system prompt with custom content"""
        custom_prompt = "Custom system prompt for testing"
        
        with patch('app.core.config.settings') as mock_settings:
            # Configure mock settings with custom system prompt
            mock_settings.CLAUDE_SYSTEM_PROMPT = custom_prompt
            
            # Create system prompt
            system_prompt_path = prompt_manager.prepare_system_prompt(self.temp_dir)
            
            # Verify file was created with custom content
            assert system_prompt_path is not None
            assert os.path.exists(system_prompt_path)
            
            with open(system_prompt_path, 'r') as f:
                content = f.read()
                
            assert content == custom_prompt
    
    def test_system_prompt_creation_failure(self):
        """Test system prompt creation with I/O failure"""
        # Use non-writable directory to simulate failure
        readonly_dir = "/nonexistent/readonly"
        
        # Should return None on failure, not raise exception
        system_prompt_path = prompt_manager.prepare_system_prompt(readonly_dir)
        assert system_prompt_path is None


class TestMCPConfigGeneration(TestClaudeSDKFeatures):
    """Test MCP configuration generation functionality"""
    
    def test_mcp_config_disabled(self):
        """Test MCP config when disabled"""
        with patch('app.core.config.settings') as mock_settings:
            # Configure MCP as disabled
            mock_settings.CLAUDE_MCP_ENABLED = False
            
            # Create MCP config
            mcp_config_path = prompt_manager.prepare_mcp_config(self.temp_dir)
            
            # Should return None when disabled
            assert mcp_config_path is None
    
    def test_mcp_config_enabled_default(self):
        """Test MCP config creation with default configuration"""
        with patch('app.core.config.settings') as mock_settings:
            # Configure MCP as enabled with no custom servers
            mock_settings.CLAUDE_MCP_ENABLED = True
            mock_settings.CLAUDE_MCP_SERVERS = {}
            
            # Create MCP config
            mcp_config_path = prompt_manager.prepare_mcp_config(self.temp_dir)
            
            # Verify file was created
            assert mcp_config_path is not None
            assert os.path.exists(mcp_config_path)
            
            # Verify content contains default filesystem server
            with open(mcp_config_path, 'r') as f:
                config = json.load(f)
                
            assert "mcpServers" in config
            assert "filesystem" in config["mcpServers"]
            assert config["mcpServers"]["filesystem"]["command"] == "uvx"
            assert "mcp-server-filesystem" in config["mcpServers"]["filesystem"]["args"]
    
    def test_mcp_config_enabled_custom(self):
        """Test MCP config creation with custom servers"""
        custom_servers = {
            "custom_server": {
                "command": "python",
                "args": ["-m", "custom_mcp_server"],
                "env": {"CUSTOM_VAR": "value"}
            }
        }
        
        with patch('app.core.config.settings') as mock_settings:
            # Configure MCP with custom servers
            mock_settings.CLAUDE_MCP_ENABLED = True
            mock_settings.CLAUDE_MCP_SERVERS = custom_servers
            
            # Create MCP config
            mcp_config_path = prompt_manager.prepare_mcp_config(self.temp_dir)
            
            # Verify file was created with custom configuration
            assert mcp_config_path is not None
            assert os.path.exists(mcp_config_path)
            
            with open(mcp_config_path, 'r') as f:
                config = json.load(f)
                
            assert "mcpServers" in config
            assert "custom_server" in config["mcpServers"]
            assert config["mcpServers"]["custom_server"]["command"] == "python"
            assert config["mcpServers"]["custom_server"]["env"]["CUSTOM_VAR"] == "value"
    
    def test_mcp_config_creation_failure(self):
        """Test MCP config creation with I/O failure"""
        with patch('app.core.config.settings') as mock_settings:
            # Configure MCP as enabled
            mock_settings.CLAUDE_MCP_ENABLED = True
            mock_settings.CLAUDE_MCP_SERVERS = {}
            
            # Use non-writable directory
            readonly_dir = "/nonexistent/readonly"
            
            # Should return None on failure, not raise exception
            mcp_config_path = prompt_manager.prepare_mcp_config(readonly_dir)
            assert mcp_config_path is None


class TestStreamJSONProcessing(TestClaudeSDKFeatures):
    """Test enhanced stream-json parsing functionality"""
    
    def setup_method(self):
        """Set up test environment with log streamer"""
        super().setup_method()
        
        # Create a test task ID for logging
        self.test_task_id = f"test-{uuid.uuid4().hex}"
        self.log_streamer = get_log_streamer()
        self.log_streamer.create_log_stream(self.test_task_id)
    
    def test_process_content_event(self):
        """Test processing content events from stream-json"""
        content_json = '{"type": "content", "content": "This is test content from Claude"}'
        
        result = output_parser.process_stream_json(content_json, self.test_task_id, self.log_streamer)
        
        # Verify parsing
        assert isinstance(result, dict)
        assert result["type"] == "content"
        assert result["content"] == "This is test content from Claude"
        
        # Verify logging
        logs = self.log_streamer.get_logs(self.test_task_id)
        assert any("Claude output: This is test content from Claude" in log for log in logs)
    
    def test_process_tool_use_event(self):
        """Test processing tool_use events from stream-json"""
        tool_use_json = '{"type": "tool_use", "name": "Write", "input": {"file_path": "/tmp/test.md", "content": "test"}}'
        
        result = output_parser.process_stream_json(tool_use_json, self.test_task_id, self.log_streamer)
        
        # Verify parsing
        assert result["type"] == "tool_use"
        assert result["name"] == "Write"
        assert result["input"]["file_path"] == "/tmp/test.md"
        
        # Verify logging
        logs = self.log_streamer.get_logs(self.test_task_id)
        assert any("Using tool: Write" in log for log in logs)
    
    def test_process_tool_result_success(self):
        """Test processing successful tool_result events"""
        tool_result_json = '{"type": "tool_result", "tool_name": "Write", "is_error": false, "content": "File written successfully"}'
        
        result = output_parser.process_stream_json(tool_result_json, self.test_task_id, self.log_streamer)
        
        # Verify parsing
        assert result["type"] == "tool_result"
        assert result["tool_name"] == "Write"
        assert result["is_error"] is False
        
        # Verify logging
        logs = self.log_streamer.get_logs(self.test_task_id)
        assert any("Tool Write completed successfully" in log for log in logs)
    
    def test_process_tool_result_error(self):
        """Test processing error tool_result events"""
        tool_result_json = '{"type": "tool_result", "tool_name": "Write", "is_error": true, "content": "Permission denied"}'
        
        result = output_parser.process_stream_json(tool_result_json, self.test_task_id, self.log_streamer)
        
        # Verify parsing
        assert result["type"] == "tool_result"
        assert result["tool_name"] == "Write"
        assert result["is_error"] is True
        
        # Verify logging
        logs = self.log_streamer.get_logs(self.test_task_id)
        assert any("Tool error in Write: Permission denied" in log for log in logs)
    
    def test_process_progress_event(self):
        """Test processing progress update events"""
        progress_json = '{"type": "progress", "progress": 45, "message": "Analyzing job requirements"}'
        
        result = output_parser.process_stream_json(progress_json, self.test_task_id, self.log_streamer)
        
        # Verify parsing
        assert result["type"] == "progress"
        assert result["progress"] == 45
        assert result["message"] == "Analyzing job requirements"
        
        # Verify logging
        logs = self.log_streamer.get_logs(self.test_task_id)
        assert any("Progress: 45% - Analyzing job requirements" in log for log in logs)
    
    def test_process_status_event(self):
        """Test processing status update events"""
        status_json = '{"type": "status", "status": "in_progress", "message": "Customizing resume sections"}'
        
        result = output_parser.process_stream_json(status_json, self.test_task_id, self.log_streamer)
        
        # Verify parsing
        assert result["type"] == "status"
        assert result["status"] == "in_progress"
        assert result["message"] == "Customizing resume sections"
        
        # Verify logging
        logs = self.log_streamer.get_logs(self.test_task_id)
        assert any("Status: in_progress - Customizing resume sections" in log for log in logs)
    
    def test_process_completion_event(self):
        """Test processing completion events"""
        completion_json = '{"type": "completion", "success": true, "message": "Resume customization completed"}'
        
        result = output_parser.process_stream_json(completion_json, self.test_task_id, self.log_streamer)
        
        # Verify parsing
        assert result["type"] == "completion"
        assert result["success"] is True
        assert result["message"] == "Resume customization completed"
        
        # Verify logging
        logs = self.log_streamer.get_logs(self.test_task_id)
        assert any("Completion: Resume customization completed" in log for log in logs)
    
    def test_process_invalid_json(self):
        """Test processing invalid JSON gracefully"""
        invalid_json = '{"type": "content", "content": invalid json'
        
        result = output_parser.process_stream_json(invalid_json, self.test_task_id, self.log_streamer)
        
        # Should return empty dict on invalid JSON
        assert result == {}
    
    def test_process_unknown_event_type(self):
        """Test processing unknown event types"""
        unknown_json = '{"type": "unknown_event", "data": "some data", "message": "Unknown message"}'
        
        result = output_parser.process_stream_json(unknown_json, self.test_task_id, self.log_streamer)
        
        # Should still parse but log as message
        assert result["type"] == "unknown_event"
        assert result["message"] == "Unknown message"
        
        # Verify logging fallback
        logs = self.log_streamer.get_logs(self.test_task_id)
        assert any("Message: Unknown message" in log for log in logs)


class TestProgressTrackingEnhancements(TestClaudeSDKFeatures):
    """Test enhanced progress tracking with detailed information"""
    
    def test_task_creation_and_tracking(self):
        """Test creating and tracking tasks"""
        # Create a new task
        task = progress_tracker.create_task()
        
        # Verify task creation
        assert task is not None
        assert task.task_id is not None
        assert task.status == "initializing"
        assert task.progress == 0
        assert "starting" in task.message.lower()
        
        # Verify task is tracked
        retrieved_task = progress_tracker.get_task(task.task_id)
        assert retrieved_task is task
    
    def test_task_progress_updates(self):
        """Test updating task progress with detailed information"""
        task = progress_tracker.create_task()
        
        # Update task progress
        task.update("in_progress", progress=25, message="Analyzing job description")
        
        # Verify updates
        assert task.status == "in_progress"
        assert task.progress == 25
        assert task.message == "Analyzing job description"
        assert task.updated_at > task.created_at
        
        # Test progress clamping
        task.update_progress(150, "Over 100%")  # Should clamp to 100
        assert task.progress == 100
        
        task.update_progress(-10, "Under 0%")  # Should clamp to 0
        assert task.progress == 0
    
    def test_task_completion(self):
        """Test task completion handling"""
        task = progress_tracker.create_task()
        
        # Mark as completed
        task.update("completed", message="Resume customization finished")
        
        # Verify completion
        assert task.status == "completed"
        assert task.progress == 100  # Should auto-set to 100%
        assert task.message == "Resume customization finished"
    
    def test_task_error_handling(self):
        """Test task error handling"""
        task = progress_tracker.create_task()
        
        # Set error
        task.set_error("Claude Code execution failed")
        
        # Verify error state
        assert task.status == "error"
        assert task.error == "Claude Code execution failed"
        assert "failed" in task.message.lower()
    
    def test_log_processing(self):
        """Test automatic task status updates from log messages"""
        task = progress_tracker.create_task()
        
        # Process completion log
        task.process_log("Claude Code execution completed successfully")
        
        # Should automatically mark as completed
        assert task.status == "completed"
    
    def test_task_subscribers(self):
        """Test task subscriber functionality"""
        task = progress_tracker.create_task()
        
        # Create mock subscriber
        mock_queue = Mock()
        mock_queue.full.return_value = False
        mock_queue.put_nowait = Mock()
        
        # Add subscriber
        task.add_subscriber(mock_queue)
        
        # Update task (should notify subscribers)
        task.update("in_progress", progress=50, message="Processing")
        
        # Verify subscriber was notified
        assert mock_queue.put_nowait.called
        call_args = mock_queue.put_nowait.call_args[0][0]
        assert call_args["status"] == "in_progress"
        assert call_args["progress"] == 50
    
    def test_task_list_filtering(self):
        """Test listing tasks with filtering"""
        # Create tasks with different statuses
        task1 = progress_tracker.create_task()
        task1.update("completed")
        
        task2 = progress_tracker.create_task()
        task2.update("in_progress")
        
        task3 = progress_tracker.create_task()
        task3.set_error("Test error")
        
        # Test listing all tasks
        all_tasks = progress_tracker.list_tasks()
        assert len(all_tasks) >= 3
        
        # Test filtering by status
        completed_tasks = progress_tracker.list_tasks(status="completed")
        assert len(completed_tasks) >= 1
        assert all(task["status"] == "completed" for task in completed_tasks)
        
        error_tasks = progress_tracker.list_tasks(status="error")
        assert len(error_tasks) >= 1
        assert all(task["status"] == "error" for task in error_tasks)


class TestSDKFeatureIntegration(TestClaudeSDKFeatures):
    """Test end-to-end integration of SDK features"""
    
    @patch('subprocess.Popen')
    @patch('app.core.config.settings')
    def test_sdk_features_enabled_execution(self, mock_settings, mock_popen):
        """Test execution with SDK features enabled"""
        # Configure settings for SDK features
        mock_settings.CLAUDE_MCP_ENABLED = True
        mock_settings.CLAUDE_MCP_SERVERS = {"filesystem": {"command": "uvx", "args": ["mcp-server-filesystem"], "env": {}}}
        mock_settings.CLAUDE_SYSTEM_PROMPT = "Custom system prompt"
        mock_settings.CLAUDE_CODE_TIMEOUT = 300
        
        # Mock process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Running initially
        mock_process.returncode = 0  # Success
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_popen.return_value = mock_process
        
        # Create test files
        resume_path = os.path.join(self.temp_dir, "resume.md")
        job_path = os.path.join(self.temp_dir, "job.txt")
        output_path = os.path.join(self.temp_dir, "output.md")
        
        with open(resume_path, 'w') as f:
            f.write("# Test Resume\nSkills: Python")
        with open(job_path, 'w') as f:
            f.write("Python Developer position")
        
        # Mock threading and queue for output handling
        with patch('threading.Thread'), \
             patch('queue.Queue'), \
             patch('app.services.claude_code.output_parser.save_results') as mock_save, \
             patch('app.services.claude_code.output_parser.process_output') as mock_process_output:
            
            # Configure mocks
            mock_process_output.return_value = {
                "customized_resume": "# Customized Resume\nSkills: Python (3+ years)",
                "customization_summary": "Enhanced Python skills section",
                "intermediate_files": {}
            }
            
            mock_save.return_value = {
                "customized_resume_path": output_path,
                "customization_summary_path": os.path.join(self.temp_dir, "summary.md")
            }
            
            # Simulate process completion
            def side_effect(*args, **kwargs):
                # Simulate process finishing
                mock_process.poll.return_value = 0
                return None
            
            mock_process.poll.side_effect = [None] * 5 + [0]  # Running then completed
            
            # Execute customization
            result = self.executor.customize_resume(
                resume_path=resume_path,
                job_description_path=job_path,
                output_path=output_path,
                timeout=60
            )
            
            # Verify command was called with SDK features
            assert mock_popen.called
            command_args = mock_popen.call_args[0][0]
            
            # Check for SDK-specific arguments
            assert "--output-format" in command_args
            assert "stream-json" in command_args
            assert "--system-prompt-file" in command_args
            assert "--mcp-config" in command_args
            
            # Verify result structure
            assert "customized_resume_path" in result
            assert "customization_summary_path" in result
    
    def test_sdk_features_disabled_execution(self):
        """Test execution with SDK features disabled"""
        with patch('app.core.config.settings') as mock_settings:
            # Configure settings with SDK features disabled
            mock_settings.CLAUDE_MCP_ENABLED = False
            mock_settings.CLAUDE_SYSTEM_PROMPT = None
            
            # Test MCP config creation (should return None)
            mcp_config_path = prompt_manager.prepare_mcp_config(self.temp_dir)
            assert mcp_config_path is None
            
            # Test system prompt creation (should create default)
            system_prompt_path = prompt_manager.prepare_system_prompt(self.temp_dir)
            assert system_prompt_path is not None
            
            # Verify default system prompt content
            with open(system_prompt_path, 'r') as f:
                content = f.read()
            assert "expert resume customization assistant" in content
    
    def test_sdk_feature_validation(self):
        """Test SDK feature validation functionality"""
        # Test the validation method
        results = self.executor.validate_sdk_features()
        
        # Should return validation results
        assert isinstance(results, dict)
        assert "system_prompt_creation" in results
        assert "mcp_config_creation" in results
        assert "stream_json_processing" in results
        
        # System prompt and stream JSON should work
        assert results["system_prompt_creation"] is True
        assert results["mcp_config_creation"] is True
        assert results["stream_json_processing"] is True
    
    @pytest.mark.asyncio
    async def test_progress_tracking_with_sdk_features(self):
        """Test progress tracking integration with SDK features"""
        # Create task for tracking
        task = progress_tracker.create_task()
        task_id = task.task_id
        
        # Create log streamer
        log_streamer = get_log_streamer()
        log_streamer.create_log_stream(task_id)
        
        # Simulate stream-json events with progress tracking
        events = [
            '{"type": "status", "status": "initializing", "message": "Starting customization"}',
            '{"type": "progress", "progress": 25, "message": "Analyzing job description"}',
            '{"type": "tool_use", "name": "Write", "input": {"file_path": "resume.md"}}',
            '{"type": "progress", "progress": 50, "message": "Customizing resume sections"}',
            '{"type": "tool_result", "tool_name": "Write", "is_error": false}',
            '{"type": "progress", "progress": 75, "message": "Generating summary"}',
            '{"type": "completion", "success": true, "message": "Customization completed"}'
        ]
        
        # Process each event
        for event_json in events:
            result = output_parser.process_stream_json(event_json, task_id, log_streamer)
            assert isinstance(result, dict)
        
        # Verify logs were created
        logs = log_streamer.get_logs(task_id)
        assert len(logs) > 0
        
        # Check for specific log types
        log_text = "\n".join(logs)
        assert "Progress: 25%" in log_text
        assert "Using tool: Write" in log_text
        assert "Tool Write completed successfully" in log_text
        assert "Completion: Customization completed" in log_text
    
    def test_error_handling_with_sdk_features(self):
        """Test error handling when SDK features fail"""
        # Test stream JSON processing with malformed data
        malformed_json = '{"type": "content", "content": malformed'
        
        log_streamer = get_log_streamer()
        task_id = f"test-{uuid.uuid4().hex}"
        log_streamer.create_log_stream(task_id)
        
        # Should handle gracefully
        result = output_parser.process_stream_json(malformed_json, task_id, log_streamer)
        assert result == {}
        
        # Test system prompt creation failure
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            system_prompt_path = prompt_manager.prepare_system_prompt(self.temp_dir)
            assert system_prompt_path is None
        
        # Test MCP config creation failure
        with patch('app.core.config.settings') as mock_settings, \
             patch('builtins.open', side_effect=PermissionError("Access denied")):
            mock_settings.CLAUDE_MCP_ENABLED = True
            mock_settings.CLAUDE_MCP_SERVERS = {}
            
            mcp_config_path = prompt_manager.prepare_mcp_config(self.temp_dir)
            assert mcp_config_path is None


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])