"""
Ralph Wiggum Loop Agent

The core agent that implements the Ralph Wiggum technique:
- Repeatedly feeds the AI the same prompt until completion
- Agent sees previous work via git history and modified files
- Iteratively improves until stop condition is met

"The technique is deterministically bad in an undeterministic world.
It's better to fail predictably than succeed unpredictably."
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic

from src.config import settings
from src.ralph.models import (
    BackpressureResult,
    CompletionResult,
    IterationStatus,
    RalphIteration,
    RalphTask,
    TaskStatus,
)
from src.ralph.completion import CompletionDetector
from src.ralph.context import ContextBuilder
from src.ralph.tools import RalphToolkit

logger = structlog.get_logger()


class RalphLoopAgent:
    """
    Ralph Wiggum Loop Agent

    Implements iterative task completion using the Ralph Wiggum technique.
    The agent keeps working on a task until:
    1. A completion promise is detected
    2. Max iterations is reached
    3. An unrecoverable error occurs
    4. The task is cancelled
    """

    def __init__(
        self,
        anthropic_client: Optional[AsyncAnthropic] = None,
        model: str = "claude-sonnet-4-20250514",
        on_iteration_complete: Optional[Callable[[RalphIteration], None]] = None,
        on_task_complete: Optional[Callable[[RalphTask], None]] = None,
    ):
        self.anthropic = anthropic_client or AsyncAnthropic(
            api_key=settings.anthropic_api_key
        )
        self.model = model
        self.on_iteration_complete = on_iteration_complete
        self.on_task_complete = on_task_complete

        # Active tasks
        self._tasks: Dict[UUID, RalphTask] = {}
        self._cancelled: set = set()

    async def run_task(self, task: RalphTask) -> RalphTask:
        """
        Run a Ralph task to completion.

        This is the main loop that keeps iterating until the task
        is complete or a stop condition is met.
        """
        logger.info(
            "Starting Ralph task",
            task_id=str(task.id),
            max_iterations=task.config.max_iterations,
        )

        # Initialize components
        toolkit = RalphToolkit(
            working_directory=task.config.working_directory,
            allow_shell_commands=True,
            command_timeout=task.config.iteration_timeout_seconds,
        )
        context_builder = ContextBuilder(task.config.working_directory)
        completion_detector = CompletionDetector(task.config.completion_promise)

        # Store task reference
        self._tasks[task.id] = task
        task.start()

        try:
            # Main loop
            while True:
                # Check cancellation
                if task.id in self._cancelled:
                    task.cancel()
                    break

                # Check max iterations
                if task.current_iteration >= task.config.max_iterations:
                    task.timeout()
                    break

                # Run iteration
                iteration = await self._run_iteration(
                    task=task,
                    toolkit=toolkit,
                    context_builder=context_builder,
                    completion_detector=completion_detector,
                )

                task.add_iteration(iteration)

                # Callback
                if self.on_iteration_complete:
                    try:
                        self.on_iteration_complete(iteration)
                    except Exception as e:
                        logger.warning(f"Iteration callback error: {e}")

                # Check completion
                completion_result = completion_detector.check_completion(
                    task, iteration
                )

                should_stop, stop_reason = completion_detector.should_stop(
                    task, completion_result
                )

                if should_stop:
                    if completion_result.is_complete:
                        task.complete(
                            completion_result,
                            iteration.agent_response
                        )
                    else:
                        task.fail(stop_reason)
                    break

                # Small delay between iterations
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Task execution error: {e}", exc_info=True)
            task.fail(str(e))

        finally:
            # Cleanup
            self._tasks.pop(task.id, None)
            self._cancelled.discard(task.id)

            # Callback
            if self.on_task_complete:
                try:
                    self.on_task_complete(task)
                except Exception as e:
                    logger.warning(f"Task callback error: {e}")

        logger.info(
            "Ralph task completed",
            task_id=str(task.id),
            status=task.status.value,
            iterations=task.current_iteration,
        )

        return task

    async def _run_iteration(
        self,
        task: RalphTask,
        toolkit: RalphToolkit,
        context_builder: ContextBuilder,
        completion_detector: CompletionDetector,
    ) -> RalphIteration:
        """Run a single iteration of the loop"""
        iteration = RalphIteration(
            iteration_number=task.current_iteration + 1,
        )

        try:
            # Build context
            context = await context_builder.build_context(
                task,
                include_git_history=task.config.include_git_history,
                include_file_contents=task.config.include_file_contents,
                max_files=task.config.max_context_files,
            )

            # Build prompt
            prompt = self._build_iteration_prompt(task, context, context_builder)
            iteration.prompt_sent = prompt

            # Call Claude with tools
            response = await self._call_claude(
                prompt=prompt,
                toolkit=toolkit,
                model=task.config.model,
                max_tokens=task.config.max_tokens,
            )

            iteration.agent_response = response["response"]
            iteration.reasoning = response.get("reasoning", "")
            iteration.tool_calls = response.get("tool_calls", [])

            # Get file changes from toolkit
            iteration.file_changes = toolkit.get_file_changes()

            # Check for completion promise in response
            promise_check = completion_detector._check_completion_promise(
                iteration.agent_response,
                task.config.completion_promise
            )
            iteration.completion_promise_found = promise_check["found"]
            if promise_check["found"]:
                iteration.completion_message = promise_check["match"]

            # Run backpressure checks
            if task.config.run_tests or task.config.run_lint or task.config.run_typecheck:
                iteration.backpressure_results = await self._run_backpressure(
                    task, toolkit
                )

            iteration.complete(IterationStatus.COMPLETED)

        except Exception as e:
            logger.error(f"Iteration error: {e}", exc_info=True)
            iteration.error = str(e)
            iteration.complete(IterationStatus.FAILED)

        return iteration

    def _build_iteration_prompt(
        self,
        task: RalphTask,
        context: Dict[str, Any],
        context_builder: ContextBuilder,
    ) -> str:
        """Build the prompt for this iteration"""
        context_str = context_builder.format_context_for_prompt(context)

        prompt = f"""You are an AI coding agent working on a task. You will iterate on this task until it is complete.

YOUR TASK:
{task.prompt}

{context_str}

INSTRUCTIONS:
1. Analyze the current state based on the context above
2. Determine what needs to be done next
3. Use the available tools to make progress
4. If you encounter errors, analyze them and try a different approach
5. When ALL requirements are met and tests pass, call the complete_task tool with a summary

IMPORTANT:
- Learn from previous iterations - don't repeat the same mistakes
- If tests are failing, read the error messages carefully and fix the issues
- Make small, incremental changes rather than large rewrites
- When the task is truly complete, signal completion with: {task.config.completion_promise}

What is your next action?"""

        return prompt

    async def _call_claude(
        self,
        prompt: str,
        toolkit: RalphToolkit,
        model: str,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Call Claude API with tools"""
        messages = [{"role": "user", "content": prompt}]
        tools = toolkit.get_tool_definitions()
        tool_calls = []
        full_response = ""
        reasoning = ""

        # Allow multiple tool calls in a loop
        max_tool_rounds = 10
        for _ in range(max_tool_rounds):
            response = await self.anthropic.messages.create(
                model=model,
                max_tokens=max_tokens,
                tools=tools,
                messages=messages,
            )

            # Process response
            assistant_content = []
            has_tool_use = False

            for block in response.content:
                if block.type == "text":
                    full_response += block.text + "\n"
                    # Extract reasoning if present
                    if "reasoning:" in block.text.lower():
                        reasoning = block.text
                    assistant_content.append({
                        "type": "text",
                        "text": block.text,
                    })
                elif block.type == "tool_use":
                    has_tool_use = True
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

                    # Execute tool
                    tool_call = await toolkit.execute_tool(
                        block.name,
                        block.input
                    )
                    tool_calls.append(tool_call)

                    # Build tool result
                    if tool_call.error:
                        tool_result = {"error": tool_call.error}
                    else:
                        tool_result = tool_call.result

                    # Add to messages for next round
                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(tool_result),
                        }]
                    })
                    assistant_content = []

                    # Check if this was a completion tool
                    if block.name == "complete_task":
                        full_response += f"\n<promise>COMPLETE</promise>\nSummary: {block.input.get('summary', '')}"

            # If no tool use, we're done
            if not has_tool_use:
                break

            # Check stop reason
            if response.stop_reason == "end_turn":
                break

        return {
            "response": full_response.strip(),
            "reasoning": reasoning,
            "tool_calls": tool_calls,
        }

    async def _run_backpressure(
        self,
        task: RalphTask,
        toolkit: RalphToolkit,
    ) -> List[BackpressureResult]:
        """Run backpressure validation checks"""
        results = []

        # Tests
        if task.config.run_tests:
            test_cmd = task.config.test_command or self._detect_test_command(
                task.config.working_directory
            )
            if test_cmd:
                result = await self._run_check("test", test_cmd, toolkit)
                results.append(result)

        # Lint
        if task.config.run_lint:
            lint_cmd = task.config.lint_command or self._detect_lint_command(
                task.config.working_directory
            )
            if lint_cmd:
                result = await self._run_check("lint", lint_cmd, toolkit)
                results.append(result)

        # Typecheck
        if task.config.run_typecheck:
            typecheck_cmd = task.config.typecheck_command or self._detect_typecheck_command(
                task.config.working_directory
            )
            if typecheck_cmd:
                result = await self._run_check("typecheck", typecheck_cmd, toolkit)
                results.append(result)

        # Build
        if task.config.run_build:
            build_cmd = task.config.build_command or self._detect_build_command(
                task.config.working_directory
            )
            if build_cmd:
                result = await self._run_check("build", build_cmd, toolkit)
                results.append(result)

        return results

    async def _run_check(
        self,
        check_type: str,
        command: str,
        toolkit: RalphToolkit,
    ) -> BackpressureResult:
        """Run a single backpressure check"""
        start_time = time.time()

        try:
            result = await toolkit._run_shell_command(command, timeout=120)

            passed = result.get("success", False) or result.get("exit_code", 1) == 0
            output = result.get("stdout", "") + result.get("stderr", "")
            errors = self._extract_errors(output, check_type)
            warnings = self._extract_warnings(output)

            return BackpressureResult(
                check_type=check_type,
                passed=passed,
                output=output[:5000],
                errors=errors,
                warnings=warnings,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            return BackpressureResult(
                check_type=check_type,
                passed=False,
                output=str(e),
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )

    def _extract_errors(self, output: str, check_type: str) -> List[str]:
        """Extract error messages from output"""
        errors = []
        lines = output.split("\n")

        error_patterns = [
            r"error[:\s]",
            r"Error[:\s]",
            r"ERROR[:\s]",
            r"failed",
            r"FAILED",
            r"✗",
            r"✖",
        ]

        for line in lines:
            for pattern in error_patterns:
                if pattern in line or (len(pattern) > 3 and pattern.lower() in line.lower()):
                    error = line.strip()[:200]
                    if error and error not in errors:
                        errors.append(error)
                        if len(errors) >= 20:
                            return errors

        return errors

    def _extract_warnings(self, output: str) -> List[str]:
        """Extract warning messages from output"""
        warnings = []
        lines = output.split("\n")

        for line in lines:
            if "warning" in line.lower() or "warn" in line.lower():
                warning = line.strip()[:200]
                if warning and warning not in warnings:
                    warnings.append(warning)
                    if len(warnings) >= 10:
                        return warnings

        return warnings

    def _detect_test_command(self, working_dir: str) -> Optional[str]:
        """Auto-detect test command based on project type"""
        from pathlib import Path
        path = Path(working_dir)

        # Python
        if (path / "pytest.ini").exists() or (path / "pyproject.toml").exists():
            return "pytest -v"
        if (path / "setup.py").exists():
            return "python -m pytest"

        # Node.js
        if (path / "package.json").exists():
            return "npm test"

        # Go
        if (path / "go.mod").exists():
            return "go test ./..."

        # Rust
        if (path / "Cargo.toml").exists():
            return "cargo test"

        return None

    def _detect_lint_command(self, working_dir: str) -> Optional[str]:
        """Auto-detect lint command"""
        from pathlib import Path
        path = Path(working_dir)

        # Python
        if (path / "pyproject.toml").exists() or (path / ".flake8").exists():
            return "ruff check . || flake8 ."

        # Node.js
        if (path / "package.json").exists():
            return "npm run lint 2>/dev/null || eslint ."

        # Go
        if (path / "go.mod").exists():
            return "golangci-lint run 2>/dev/null || go vet ./..."

        return None

    def _detect_typecheck_command(self, working_dir: str) -> Optional[str]:
        """Auto-detect typecheck command"""
        from pathlib import Path
        path = Path(working_dir)

        # Python
        if (path / "pyproject.toml").exists():
            return "mypy . 2>/dev/null || true"

        # TypeScript
        if (path / "tsconfig.json").exists():
            return "tsc --noEmit"

        return None

    def _detect_build_command(self, working_dir: str) -> Optional[str]:
        """Auto-detect build command"""
        from pathlib import Path
        path = Path(working_dir)

        # Node.js
        if (path / "package.json").exists():
            return "npm run build"

        # Go
        if (path / "go.mod").exists():
            return "go build ./..."

        # Rust
        if (path / "Cargo.toml").exists():
            return "cargo build"

        return None

    def cancel_task(self, task_id: UUID) -> bool:
        """Request cancellation of a running task"""
        if task_id in self._tasks:
            self._cancelled.add(task_id)
            return True
        return False

    def get_task_status(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """Get status of a task"""
        task = self._tasks.get(task_id)
        if task:
            return task.get_summary()
        return None


class RalphTaskRunner:
    """
    High-level task runner for managing Ralph tasks.

    Provides:
    - Task persistence
    - Concurrent task execution
    - Status tracking
    - Event callbacks
    """

    def __init__(
        self,
        anthropic_client: Optional[AsyncAnthropic] = None,
        max_concurrent_tasks: int = 5,
    ):
        self.agent = RalphLoopAgent(
            anthropic_client=anthropic_client,
            on_iteration_complete=self._on_iteration,
            on_task_complete=self._on_task_complete,
        )
        self.max_concurrent = max_concurrent_tasks
        self._running_tasks: Dict[UUID, asyncio.Task] = {}
        self._completed_tasks: Dict[UUID, RalphTask] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def submit_task(self, task: RalphTask) -> UUID:
        """Submit a task for execution"""
        async def run_with_semaphore():
            async with self._semaphore:
                return await self.agent.run_task(task)

        # Create async task
        async_task = asyncio.create_task(run_with_semaphore())
        self._running_tasks[task.id] = async_task

        logger.info(f"Task submitted: {task.id}")
        return task.id

    async def wait_for_task(self, task_id: UUID) -> Optional[RalphTask]:
        """Wait for a task to complete"""
        if task_id in self._running_tasks:
            try:
                result = await self._running_tasks[task_id]
                return result
            except Exception as e:
                logger.error(f"Task failed: {e}")
                return None
        elif task_id in self._completed_tasks:
            return self._completed_tasks[task_id]
        return None

    def get_status(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """Get task status"""
        if task_id in self._completed_tasks:
            return self._completed_tasks[task_id].get_summary()
        return self.agent.get_task_status(task_id)

    def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a running task"""
        return self.agent.cancel_task(task_id)

    def _on_iteration(self, iteration: RalphIteration):
        """Called when an iteration completes"""
        logger.debug(
            f"Iteration {iteration.iteration_number} complete",
            status=iteration.status.value,
            tool_calls=len(iteration.tool_calls),
        )

    def _on_task_complete(self, task: RalphTask):
        """Called when a task completes"""
        self._running_tasks.pop(task.id, None)
        self._completed_tasks[task.id] = task
        logger.info(
            f"Task complete: {task.id}",
            status=task.status.value,
            iterations=task.current_iteration,
        )
