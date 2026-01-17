"""
Completion Detection for Ralph Wiggum Agent

Detects when a task is complete based on:
1. Completion promise in agent response
2. All backpressure checks passing
3. No errors in recent iterations
4. Semantic analysis of progress
"""

import re
from typing import List, Optional

import structlog

from src.ralph.models import (
    BackpressureResult,
    CompletionResult,
    RalphIteration,
    RalphTask,
)

logger = structlog.get_logger()


class CompletionDetector:
    """
    Detects when a Ralph task is complete.

    Uses multiple signals:
    - Explicit completion promise
    - Backpressure results (tests, lint, etc.)
    - Error patterns
    - Iteration patterns
    """

    def __init__(self, completion_promise: str = "<promise>COMPLETE</promise>"):
        self.completion_promise = completion_promise
        # Alternative completion patterns
        self.completion_patterns = [
            r"<promise>COMPLETE</promise>",
            r"TASK[_\s]?COMPLETE",
            r"LOOP[_\s]?COMPLETE",
            r"DONE[_\s]?COMPLETE",
            r"\[COMPLETE\]",
            r"\[DONE\]",
        ]

    def check_completion(
        self,
        task: RalphTask,
        current_iteration: RalphIteration,
    ) -> CompletionResult:
        """Check if the task is complete"""
        result = CompletionResult()

        # Check 1: Explicit completion promise
        promise_check = self._check_completion_promise(
            current_iteration.agent_response,
            task.config.completion_promise
        )
        result.promise_detected = promise_check["found"]
        if promise_check["found"]:
            result.is_complete = True
            result.reason = f"Completion promise detected: {promise_check['match']}"
            result.confidence = 1.0
            return result

        # Check 2: Backpressure results
        bp_check = self._check_backpressure(current_iteration.backpressure_results)
        result.all_tests_passed = bp_check["all_passed"]
        result.no_errors = bp_check["no_errors"]

        # Check 3: Error patterns in response
        error_check = self._check_for_errors(current_iteration)
        if error_check["has_critical_error"]:
            result.no_errors = False

        # Check 4: Analyze progress patterns
        progress_check = self._analyze_progress(task, current_iteration)

        # Determine completion based on all signals
        if (result.all_tests_passed and
            result.no_errors and
            progress_check["appears_complete"]):
            result.is_complete = True
            result.reason = "All tests passed, no errors, task appears complete"
            result.confidence = progress_check["confidence"]
        elif not result.no_errors:
            result.is_complete = False
            result.reason = "Errors detected in iteration"
            result.confidence = 0.0
        else:
            result.is_complete = False
            result.reason = "Task still in progress"
            result.confidence = progress_check["confidence"]

        return result

    def _check_completion_promise(
        self,
        response: str,
        custom_promise: Optional[str] = None
    ) -> dict:
        """Check for completion promise in response"""
        # Check custom promise first
        if custom_promise and custom_promise in response:
            return {"found": True, "match": custom_promise}

        # Check default promise
        if self.completion_promise in response:
            return {"found": True, "match": self.completion_promise}

        # Check alternative patterns
        for pattern in self.completion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return {"found": True, "match": match.group()}

        return {"found": False, "match": None}

    def _check_backpressure(
        self,
        results: List[BackpressureResult]
    ) -> dict:
        """Check backpressure validation results"""
        if not results:
            return {"all_passed": True, "no_errors": True, "details": {}}

        all_passed = all(r.passed for r in results)
        no_errors = all(len(r.errors) == 0 for r in results)

        details = {}
        for r in results:
            details[r.check_type] = {
                "passed": r.passed,
                "error_count": len(r.errors),
                "warning_count": len(r.warnings),
            }

        return {
            "all_passed": all_passed,
            "no_errors": no_errors,
            "details": details,
        }

    def _check_for_errors(self, iteration: RalphIteration) -> dict:
        """Check for error patterns in the iteration"""
        critical_error = False
        errors_found = []

        # Check iteration error
        if iteration.error:
            critical_error = True
            errors_found.append(iteration.error)

        # Check tool call errors
        for tc in iteration.tool_calls:
            if tc.error:
                critical_error = True
                errors_found.append(f"Tool {tc.tool_name}: {tc.error}")

        # Check for error patterns in response
        error_patterns = [
            r"error:?\s*(.{10,100})",
            r"failed:?\s*(.{10,100})",
            r"exception:?\s*(.{10,100})",
            r"cannot\s+(.{10,50})",
            r"unable\s+to\s+(.{10,50})",
        ]

        response = iteration.agent_response.lower()
        for pattern in error_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                # Don't count as critical unless we see real errors
                for match in matches[:3]:
                    if not any(
                        skip in match.lower()
                        for skip in ["no error", "without error", "error handling"]
                    ):
                        errors_found.append(match)

        return {
            "has_critical_error": critical_error,
            "errors_found": errors_found,
        }

    def _analyze_progress(
        self,
        task: RalphTask,
        current_iteration: RalphIteration
    ) -> dict:
        """Analyze if the task appears to be making progress toward completion"""
        confidence = 0.0
        appears_complete = False
        indicators = []

        response = current_iteration.agent_response.lower()

        # Positive completion indicators
        completion_phrases = [
            "task is complete",
            "completed successfully",
            "all done",
            "finished implementing",
            "implementation complete",
            "changes have been made",
            "everything is working",
            "tests pass",
            "all tests pass",
        ]

        for phrase in completion_phrases:
            if phrase in response:
                confidence += 0.15
                indicators.append(f"Found: '{phrase}'")

        # Check if agent is asking for verification rather than doing work
        verification_phrases = [
            "please review",
            "ready for review",
            "let me know if",
            "should i",
            "would you like",
        ]

        for phrase in verification_phrases:
            if phrase in response:
                confidence += 0.1
                indicators.append(f"Verification phrase: '{phrase}'")

        # Check for no further changes needed
        no_change_phrases = [
            "no changes needed",
            "no further changes",
            "nothing left to do",
            "all requirements met",
        ]

        for phrase in no_change_phrases:
            if phrase in response:
                confidence += 0.2
                indicators.append(f"No changes: '{phrase}'")

        # Check tool call patterns
        if current_iteration.tool_calls:
            # If only read operations, might be verifying completion
            read_only = all(
                "read" in tc.tool_name.lower() or "get" in tc.tool_name.lower()
                for tc in current_iteration.tool_calls
            )
            if read_only:
                confidence += 0.1
                indicators.append("Read-only operations (verification)")

        # Check iteration patterns
        if len(task.iterations) >= 2:
            prev = task.iterations[-2]
            # Decreasing file changes might indicate convergence
            if (len(current_iteration.file_changes) <
                len(prev.file_changes)):
                confidence += 0.05
                indicators.append("Decreasing file changes")

        # Cap confidence at 0.7 without explicit promise
        confidence = min(confidence, 0.7)

        # Determine if appears complete
        appears_complete = (
            confidence >= 0.5 and
            not current_iteration.error and
            all(
                bp.passed
                for bp in current_iteration.backpressure_results
            )
        )

        return {
            "appears_complete": appears_complete,
            "confidence": confidence,
            "indicators": indicators,
        }

    def should_stop(
        self,
        task: RalphTask,
        completion_result: CompletionResult
    ) -> tuple[bool, str]:
        """Determine if the loop should stop"""
        # Stop if complete
        if completion_result.is_complete:
            return True, completion_result.reason

        # Stop if max iterations reached
        if task.current_iteration >= task.config.max_iterations:
            return True, f"Max iterations ({task.config.max_iterations}) reached"

        # Stop if too many consecutive errors
        if len(task.iterations) >= 5:
            recent_errors = sum(
                1 for i in task.iterations[-5:]
                if i.error is not None
            )
            if recent_errors >= 4:
                return True, "Too many consecutive errors"

        # Stop if stuck in a loop (same response multiple times)
        if len(task.iterations) >= 3:
            recent_responses = [
                i.agent_response[:500]
                for i in task.iterations[-3:]
            ]
            if len(set(recent_responses)) == 1:
                return True, "Agent appears stuck (identical responses)"

        return False, ""
