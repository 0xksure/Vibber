"""
Tests for Ralph Wiggum Agent

Tests the core components:
- Task models
- Completion detection
- Context building
- Tool execution
- Loop agent
"""

import asyncio
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.ralph.models import (
    BackpressureResult,
    CompletionResult,
    FileChange,
    IterationStatus,
    RalphIteration,
    RalphTask,
    RalphTaskConfig,
    TaskStatus,
    ToolCall,
)
from src.ralph.completion import CompletionDetector
from src.ralph.context import ContextBuilder
from src.ralph.tools import RalphToolkit


class TestRalphModels:
    """Tests for Ralph data models"""

    def test_task_creation(self):
        """Test creating a Ralph task"""
        task = RalphTask(
            prompt="Fix the bug in auth.py",
            description="Authentication issue causing login failures",
        )

        assert task.id is not None
        assert task.prompt == "Fix the bug in auth.py"
        assert task.status == TaskStatus.PENDING
        assert task.current_iteration == 0
        assert len(task.iterations) == 0

    def test_task_start(self):
        """Test starting a task"""
        task = RalphTask(prompt="Test prompt")
        task.start()

        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_task_complete(self):
        """Test completing a task"""
        task = RalphTask(prompt="Test prompt")
        task.start()

        result = CompletionResult(
            is_complete=True,
            reason="Task completed successfully",
            confidence=1.0,
        )
        task.complete(result, "Final output here")

        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.completion_result.is_complete
        assert task.final_output == "Final output here"

    def test_task_fail(self):
        """Test failing a task"""
        task = RalphTask(prompt="Test prompt")
        task.start()
        task.fail("Something went wrong")

        assert task.status == TaskStatus.FAILED
        assert task.error == "Something went wrong"

    def test_add_iteration(self):
        """Test adding iterations to a task"""
        task = RalphTask(prompt="Test prompt")

        iteration = RalphIteration(
            iteration_number=1,
            status=IterationStatus.COMPLETED,
            agent_response="Made changes to file.py",
            tool_calls=[
                ToolCall(
                    tool_name="write_file",
                    arguments={"path": "test.py", "content": "print('hello')"},
                )
            ],
            file_changes=[
                FileChange(path="test.py", action="create"),
            ],
        )

        task.add_iteration(iteration)

        assert task.current_iteration == 1
        assert len(task.iterations) == 1
        assert task.total_tool_calls == 1
        assert task.total_file_changes == 1

    def test_task_config_defaults(self):
        """Test task config defaults"""
        config = RalphTaskConfig()

        assert config.completion_promise == "<promise>COMPLETE</promise>"
        assert config.max_iterations == 50
        assert config.run_tests is True
        assert config.run_lint is True
        assert config.model == "claude-sonnet-4-20250514"


class TestCompletionDetector:
    """Tests for completion detection"""

    def test_detect_default_promise(self):
        """Test detecting default completion promise"""
        detector = CompletionDetector()

        task = RalphTask(prompt="Test")
        iteration = RalphIteration(
            iteration_number=1,
            agent_response="Task done! <promise>COMPLETE</promise>",
        )

        result = detector.check_completion(task, iteration)

        assert result.is_complete
        assert result.promise_detected
        assert result.confidence == 1.0

    def test_detect_custom_promise(self):
        """Test detecting custom completion promise"""
        detector = CompletionDetector(completion_promise="[DONE]")

        task = RalphTask(
            prompt="Test",
            config=RalphTaskConfig(completion_promise="[DONE]"),
        )
        iteration = RalphIteration(
            iteration_number=1,
            agent_response="All finished! [DONE]",
        )

        result = detector.check_completion(task, iteration)

        assert result.is_complete
        assert result.promise_detected

    def test_detect_alternative_patterns(self):
        """Test detecting alternative completion patterns"""
        detector = CompletionDetector()

        patterns = [
            "TASK_COMPLETE",
            "LOOP_COMPLETE",
            "[COMPLETE]",
        ]

        for pattern in patterns:
            task = RalphTask(prompt="Test")
            iteration = RalphIteration(
                iteration_number=1,
                agent_response=f"Done! {pattern}",
            )

            result = detector.check_completion(task, iteration)
            assert result.is_complete, f"Failed to detect: {pattern}"

    def test_no_completion(self):
        """Test when task is not complete"""
        detector = CompletionDetector()

        task = RalphTask(prompt="Test")
        iteration = RalphIteration(
            iteration_number=1,
            agent_response="Working on it...",
        )

        result = detector.check_completion(task, iteration)

        assert not result.is_complete
        assert not result.promise_detected

    def test_backpressure_check(self):
        """Test backpressure validation"""
        detector = CompletionDetector()

        # All tests pass
        results = [
            BackpressureResult(check_type="test", passed=True),
            BackpressureResult(check_type="lint", passed=True),
        ]
        check = detector._check_backpressure(results)
        assert check["all_passed"]
        assert check["no_errors"]

        # Some tests fail
        results = [
            BackpressureResult(check_type="test", passed=False, errors=["Error 1"]),
            BackpressureResult(check_type="lint", passed=True),
        ]
        check = detector._check_backpressure(results)
        assert not check["all_passed"]

    def test_should_stop_max_iterations(self):
        """Test stopping at max iterations"""
        detector = CompletionDetector()

        task = RalphTask(
            prompt="Test",
            config=RalphTaskConfig(max_iterations=3),
        )
        task.current_iteration = 3

        result = CompletionResult(is_complete=False)
        should_stop, reason = detector.should_stop(task, result)

        assert should_stop
        assert "Max iterations" in reason

    def test_should_stop_consecutive_errors(self):
        """Test stopping after consecutive errors"""
        detector = CompletionDetector()

        task = RalphTask(prompt="Test")
        # Add 5 iterations with errors
        for i in range(5):
            iteration = RalphIteration(
                iteration_number=i + 1,
                status=IterationStatus.FAILED,
                error="Some error",
            )
            task.iterations.append(iteration)
            task.current_iteration = i + 1

        result = CompletionResult(is_complete=False)
        should_stop, reason = detector.should_stop(task, result)

        assert should_stop
        assert "consecutive errors" in reason.lower()


class TestRalphToolkit:
    """Tests for Ralph toolkit"""

    @pytest.fixture
    def toolkit(self, tmp_path):
        """Create toolkit with temp directory"""
        return RalphToolkit(
            working_directory=str(tmp_path),
            allow_shell_commands=True,
        )

    def test_get_tool_definitions(self, toolkit):
        """Test getting tool definitions"""
        tools = toolkit.get_tool_definitions()

        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert "run_command" in tool_names
        assert "complete_task" in tool_names

    @pytest.mark.asyncio
    async def test_read_file(self, toolkit, tmp_path):
        """Test reading a file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        result = await toolkit.execute_tool(
            "read_file",
            {"path": "test.txt"}
        )

        assert result.error is None
        assert result.result["content"] == "Hello, World!"

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, toolkit):
        """Test reading non-existent file"""
        result = await toolkit.execute_tool(
            "read_file",
            {"path": "nonexistent.txt"}
        )

        assert "error" in result.result

    @pytest.mark.asyncio
    async def test_write_file(self, toolkit, tmp_path):
        """Test writing a file"""
        result = await toolkit.execute_tool(
            "write_file",
            {"path": "new_file.txt", "content": "New content"}
        )

        assert result.error is None
        assert result.result["success"]
        assert (tmp_path / "new_file.txt").read_text() == "New content"

    @pytest.mark.asyncio
    async def test_edit_file(self, toolkit, tmp_path):
        """Test editing a file"""
        test_file = tmp_path / "edit_test.txt"
        test_file.write_text("Hello, World!")

        result = await toolkit.execute_tool(
            "edit_file",
            {
                "path": "edit_test.txt",
                "old_text": "World",
                "new_text": "Universe",
            }
        )

        assert result.error is None
        assert result.result["success"]
        assert test_file.read_text() == "Hello, Universe!"

    @pytest.mark.asyncio
    async def test_list_files(self, toolkit, tmp_path):
        """Test listing files"""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.py").touch()

        result = await toolkit.execute_tool(
            "list_files",
            {"path": "."}
        )

        assert result.error is None
        assert result.result["total"] == 2

    @pytest.mark.asyncio
    async def test_run_command(self, toolkit):
        """Test running a command"""
        result = await toolkit.execute_tool(
            "run_command",
            {"command": "echo 'hello'"}
        )

        assert result.error is None
        assert "hello" in result.result["stdout"]

    @pytest.mark.asyncio
    async def test_complete_task_tool(self, toolkit):
        """Test complete_task tool"""
        result = await toolkit.execute_tool(
            "complete_task",
            {"summary": "Task completed successfully"}
        )

        assert result.error is None
        assert result.result["signal"] == "COMPLETE"
        assert "<promise>COMPLETE</promise>" in result.result["completion_promise"]

    @pytest.mark.asyncio
    async def test_path_security(self, toolkit, tmp_path):
        """Test that paths outside working directory are blocked"""
        result = await toolkit.execute_tool(
            "read_file",
            {"path": "/etc/passwd"}
        )

        # Should either error or return path validation error
        assert result.error is not None or "error" in result.result

    def test_file_changes_tracking(self, toolkit):
        """Test that file changes are tracked"""
        # Initially empty
        assert len(toolkit.get_file_changes()) == 0


class TestContextBuilder:
    """Tests for context building"""

    @pytest.fixture
    def context_builder(self, tmp_path):
        """Create context builder with temp directory"""
        return ContextBuilder(str(tmp_path))

    @pytest.mark.asyncio
    async def test_build_task_info(self, context_builder):
        """Test building task info"""
        task = RalphTask(
            prompt="Fix the bug",
            config=RalphTaskConfig(max_iterations=10),
        )
        task.current_iteration = 3

        info = context_builder._build_task_info(task)

        assert info["original_prompt"] == "Fix the bug"
        assert info["current_iteration"] == 3
        assert info["max_iterations"] == 10
        assert info["iterations_remaining"] == 7

    @pytest.mark.asyncio
    async def test_build_iteration_history(self, context_builder):
        """Test building iteration history"""
        task = RalphTask(prompt="Test")

        # Add some iterations
        for i in range(3):
            iteration = RalphIteration(
                iteration_number=i + 1,
                status=IterationStatus.COMPLETED,
                reasoning=f"Iteration {i + 1} reasoning",
                tool_calls=[
                    ToolCall(
                        tool_name="write_file",
                        arguments={},
                        result={"success": True},
                    )
                ],
            )
            task.iterations.append(iteration)

        history = context_builder._build_iteration_history(task)

        assert len(history) == 3
        assert history[0]["iteration"] == 1
        assert history[0]["status"] == "completed"
        assert len(history[0]["tool_calls"]) == 1

    @pytest.mark.asyncio
    async def test_build_backpressure_feedback(self, context_builder):
        """Test building backpressure feedback"""
        task = RalphTask(prompt="Test")

        iteration = RalphIteration(
            iteration_number=1,
            backpressure_results=[
                BackpressureResult(
                    check_type="test",
                    passed=False,
                    errors=["Test failed"],
                ),
                BackpressureResult(
                    check_type="lint",
                    passed=True,
                ),
            ],
        )
        task.iterations.append(iteration)

        feedback = context_builder._build_backpressure_feedback(task)

        assert feedback["has_feedback"]
        assert not feedback["all_passed"]
        assert "test" in feedback["results"]
        assert not feedback["results"]["test"]["passed"]

    @pytest.mark.asyncio
    async def test_format_context_for_prompt(self, context_builder):
        """Test formatting context as prompt string"""
        task = RalphTask(prompt="Test task")
        context = await context_builder.build_context(
            task,
            include_git_history=False,
            include_file_contents=False,
        )

        formatted = context_builder.format_context_for_prompt(context)

        assert "TASK CONTEXT" in formatted
        assert "Iteration:" in formatted
        assert "Completion signal:" in formatted


class TestRalphLoopAgent:
    """Tests for the Ralph loop agent"""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization"""
        from src.ralph.loop_agent import RalphLoopAgent

        with patch('src.ralph.loop_agent.AsyncAnthropic'):
            agent = RalphLoopAgent(
                model="claude-sonnet-4-20250514",
            )

            assert agent.model == "claude-sonnet-4-20250514"
            assert agent._tasks == {}

    @pytest.mark.asyncio
    async def test_task_runner_initialization(self):
        """Test task runner initialization"""
        from src.ralph.loop_agent import RalphTaskRunner

        with patch('src.ralph.loop_agent.AsyncAnthropic'):
            runner = RalphTaskRunner(max_concurrent_tasks=3)

            assert runner.max_concurrent == 3


class TestRalphAPI:
    """Tests for Ralph API endpoints"""

    @pytest.mark.asyncio
    async def test_create_task_request_validation(self):
        """Test task creation request validation"""
        from src.ralph.models import TaskCreateRequest

        # Valid request
        request = TaskCreateRequest(
            prompt="This is a valid prompt with enough characters",
        )
        assert len(request.prompt) >= 10

    @pytest.mark.asyncio
    async def test_task_status_response(self):
        """Test task status response model"""
        from src.ralph.models import TaskStatusResponse, TaskStatus

        response = TaskStatusResponse(
            id="test-id",
            status=TaskStatus.RUNNING,
            current_iteration=5,
            max_iterations=50,
            duration_seconds=120.5,
            is_complete=False,
        )

        assert response.id == "test-id"
        assert response.status == TaskStatus.RUNNING
        assert response.current_iteration == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
