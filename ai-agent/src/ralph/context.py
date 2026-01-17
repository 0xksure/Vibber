"""
Context Builder for Ralph Wiggum Agent

Builds context from git history, modified files, and previous iterations
to feed back into the agent loop.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from src.ralph.models import RalphIteration, RalphTask

logger = structlog.get_logger()


class ContextBuilder:
    """
    Builds context for the Ralph loop agent.

    Context includes:
    - Git history (recent commits, diffs)
    - Modified files since task started
    - Previous iteration results
    - Current file contents
    - Backpressure feedback (test/lint results)
    """

    def __init__(self, working_directory: str = "."):
        self.working_dir = Path(working_directory).resolve()

    async def build_context(
        self,
        task: RalphTask,
        include_git_history: bool = True,
        include_file_contents: bool = True,
        max_files: int = 20,
    ) -> Dict[str, Any]:
        """Build complete context for the agent"""
        context = {
            "task_info": self._build_task_info(task),
            "iteration_history": self._build_iteration_history(task),
            "git_context": {},
            "file_context": {},
            "backpressure_feedback": self._build_backpressure_feedback(task),
        }

        if include_git_history:
            context["git_context"] = await self._build_git_context()

        if include_file_contents:
            context["file_context"] = await self._build_file_context(
                task, max_files
            )

        return context

    def _build_task_info(self, task: RalphTask) -> Dict[str, Any]:
        """Build task information section"""
        return {
            "original_prompt": task.prompt,
            "description": task.description,
            "current_iteration": task.current_iteration,
            "max_iterations": task.config.max_iterations,
            "completion_promise": task.config.completion_promise,
            "iterations_remaining": task.config.max_iterations - task.current_iteration,
        }

    def _build_iteration_history(self, task: RalphTask) -> List[Dict[str, Any]]:
        """Build history of previous iterations"""
        history = []

        for iteration in task.iterations[-10:]:  # Last 10 iterations
            entry = {
                "iteration": iteration.iteration_number,
                "status": iteration.status.value,
                "duration_ms": iteration.duration_ms,
                "reasoning": iteration.reasoning,
                "tool_calls": [
                    {
                        "tool": tc.tool_name,
                        "result_preview": str(tc.result)[:200] if tc.result else None,
                        "error": tc.error,
                    }
                    for tc in iteration.tool_calls
                ],
                "file_changes": [
                    {
                        "path": fc.path,
                        "action": fc.action,
                    }
                    for fc in iteration.file_changes
                ],
                "backpressure": {
                    bp.check_type: {
                        "passed": bp.passed,
                        "errors": bp.errors[:3],  # First 3 errors
                    }
                    for bp in iteration.backpressure_results
                },
                "completion_promise_found": iteration.completion_promise_found,
                "error": iteration.error,
            }
            history.append(entry)

        return history

    def _build_backpressure_feedback(self, task: RalphTask) -> Dict[str, Any]:
        """Build feedback from last backpressure check"""
        if not task.iterations:
            return {"has_feedback": False}

        last_iteration = task.iterations[-1]
        if not last_iteration.backpressure_results:
            return {"has_feedback": False}

        feedback = {
            "has_feedback": True,
            "all_passed": all(
                bp.passed for bp in last_iteration.backpressure_results
            ),
            "results": {},
        }

        for bp in last_iteration.backpressure_results:
            feedback["results"][bp.check_type] = {
                "passed": bp.passed,
                "errors": bp.errors,
                "warnings": bp.warnings,
                "output_preview": bp.output[:500] if bp.output else "",
            }

        return feedback

    async def _build_git_context(self) -> Dict[str, Any]:
        """Build git context (history, diffs, status)"""
        context = {
            "is_git_repo": False,
            "recent_commits": [],
            "uncommitted_changes": [],
            "current_branch": "",
        }

        try:
            # Check if it's a git repo
            is_git = await self._run_command("git rev-parse --git-dir")
            if not is_git or "fatal" in is_git.lower():
                return context

            context["is_git_repo"] = True

            # Get current branch
            branch = await self._run_command("git branch --show-current")
            context["current_branch"] = branch.strip() if branch else ""

            # Get recent commits
            commits = await self._run_command(
                "git log --oneline -20 --format='%h %s'"
            )
            if commits:
                context["recent_commits"] = [
                    line.strip() for line in commits.strip().split("\n")
                    if line.strip()
                ]

            # Get uncommitted changes (git status)
            status = await self._run_command("git status --porcelain")
            if status:
                changes = []
                for line in status.strip().split("\n"):
                    if line.strip():
                        status_code = line[:2]
                        filepath = line[3:].strip()
                        changes.append({
                            "status": status_code,
                            "path": filepath,
                        })
                context["uncommitted_changes"] = changes

            # Get diff of uncommitted changes
            diff = await self._run_command("git diff --stat HEAD")
            if diff:
                context["diff_summary"] = diff.strip()

        except Exception as e:
            logger.warning(f"Error building git context: {e}")

        return context

    async def _build_file_context(
        self,
        task: RalphTask,
        max_files: int = 20
    ) -> Dict[str, Any]:
        """Build context from relevant files"""
        context = {
            "modified_files": [],
            "relevant_files": [],
        }

        # Get files modified in this task
        modified_paths = set()
        for iteration in task.iterations:
            for fc in iteration.file_changes:
                modified_paths.add(fc.path)

        # Read modified files
        for path in list(modified_paths)[:max_files]:
            content = await self._read_file(path)
            if content is not None:
                context["modified_files"].append({
                    "path": path,
                    "content": content[:5000],  # Limit content size
                    "truncated": len(content) > 5000,
                })

        return context

    async def _run_command(self, cmd: str) -> Optional[str]:
        """Run a shell command and return output"""
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=30
            )
            return stdout.decode("utf-8") if stdout else ""
        except asyncio.TimeoutError:
            logger.warning(f"Command timed out: {cmd}")
            return None
        except Exception as e:
            logger.warning(f"Command failed: {cmd}, error: {e}")
            return None

    async def _read_file(self, path: str) -> Optional[str]:
        """Read file contents"""
        try:
            full_path = self.working_dir / path
            if full_path.exists() and full_path.is_file():
                return full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Error reading file {path}: {e}")
        return None

    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Format context into a string for the prompt"""
        parts = []

        # Task info
        task_info = context.get("task_info", {})
        parts.append("=" * 60)
        parts.append("TASK CONTEXT")
        parts.append("=" * 60)
        parts.append(f"Iteration: {task_info.get('current_iteration', 0)} of {task_info.get('max_iterations', '?')}")
        parts.append(f"Iterations remaining: {task_info.get('iterations_remaining', '?')}")
        parts.append(f"Completion signal: Include '{task_info.get('completion_promise', '')}' when task is fully complete")
        parts.append("")

        # Previous iteration feedback
        history = context.get("iteration_history", [])
        if history:
            parts.append("-" * 40)
            parts.append("PREVIOUS ITERATIONS:")
            parts.append("-" * 40)
            for h in history[-3:]:  # Last 3 iterations
                parts.append(f"\nIteration {h['iteration']}:")
                parts.append(f"  Status: {h['status']}")
                if h.get('reasoning'):
                    parts.append(f"  Reasoning: {h['reasoning'][:200]}")
                if h.get('error'):
                    parts.append(f"  Error: {h['error']}")
                if h.get('file_changes'):
                    parts.append(f"  Files changed: {[fc['path'] for fc in h['file_changes']]}")

                # Backpressure feedback
                bp = h.get('backpressure', {})
                for check_type, result in bp.items():
                    status = "PASSED" if result['passed'] else "FAILED"
                    parts.append(f"  {check_type}: {status}")
                    if result.get('errors'):
                        for err in result['errors'][:2]:
                            parts.append(f"    - {err}")
            parts.append("")

        # Git context
        git = context.get("git_context", {})
        if git.get("is_git_repo"):
            parts.append("-" * 40)
            parts.append("GIT STATUS:")
            parts.append("-" * 40)
            parts.append(f"Branch: {git.get('current_branch', 'unknown')}")

            changes = git.get("uncommitted_changes", [])
            if changes:
                parts.append("Uncommitted changes:")
                for c in changes[:10]:
                    parts.append(f"  [{c['status']}] {c['path']}")

            if git.get("diff_summary"):
                parts.append("\nDiff summary:")
                parts.append(git["diff_summary"][:500])
            parts.append("")

        # Backpressure feedback
        bp_feedback = context.get("backpressure_feedback", {})
        if bp_feedback.get("has_feedback"):
            parts.append("-" * 40)
            parts.append("LAST VALIDATION RESULTS:")
            parts.append("-" * 40)
            all_passed = bp_feedback.get("all_passed", False)
            parts.append(f"Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")

            for check_type, result in bp_feedback.get("results", {}).items():
                status = "PASSED" if result["passed"] else "FAILED"
                parts.append(f"\n{check_type.upper()}: {status}")
                if result.get("errors"):
                    parts.append("Errors:")
                    for err in result["errors"][:5]:
                        parts.append(f"  - {err}")
                if result.get("output_preview") and not result["passed"]:
                    parts.append(f"Output:\n{result['output_preview'][:300]}")
            parts.append("")

        # Modified files
        file_ctx = context.get("file_context", {})
        modified = file_ctx.get("modified_files", [])
        if modified:
            parts.append("-" * 40)
            parts.append("FILES MODIFIED IN THIS TASK:")
            parts.append("-" * 40)
            for f in modified[:5]:
                parts.append(f"\n--- {f['path']} ---")
                content = f["content"]
                if f.get("truncated"):
                    parts.append(f"(truncated, showing first 5000 chars)")
                parts.append(content[:2000])  # Further limit for prompt
            parts.append("")

        return "\n".join(parts)
