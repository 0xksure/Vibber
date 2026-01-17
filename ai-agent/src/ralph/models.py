"""
Ralph Wiggum Data Models

Defines the core data structures for task tracking, iteration history,
and completion status.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a Ralph task"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class IterationStatus(str, Enum):
    """Status of a single iteration"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class ToolCall(BaseModel):
    """Record of a tool call made during an iteration"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FileChange(BaseModel):
    """Record of a file change made during an iteration"""
    path: str
    action: str  # create, modify, delete
    content_preview: Optional[str] = None
    lines_added: int = 0
    lines_removed: int = 0


class BackpressureResult(BaseModel):
    """Result of backpressure validation (tests, lint, etc.)"""
    check_type: str  # test, lint, typecheck, build
    passed: bool
    output: str = ""
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    duration_ms: int = 0


class RalphIteration(BaseModel):
    """A single iteration in the Ralph loop"""
    iteration_number: int
    status: IterationStatus = IterationStatus.RUNNING

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0

    # Agent interaction
    prompt_sent: str = ""
    agent_response: str = ""
    reasoning: str = ""

    # Tool usage
    tool_calls: List[ToolCall] = Field(default_factory=list)

    # Changes made
    file_changes: List[FileChange] = Field(default_factory=list)
    git_commits: List[str] = Field(default_factory=list)

    # Backpressure results
    backpressure_results: List[BackpressureResult] = Field(default_factory=list)

    # Completion check
    completion_promise_found: bool = False
    completion_message: Optional[str] = None

    # Errors
    error: Optional[str] = None

    def complete(self, status: IterationStatus = IterationStatus.COMPLETED):
        """Mark iteration as complete"""
        self.status = status
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )


class CompletionResult(BaseModel):
    """Result of completion detection"""
    is_complete: bool = False
    reason: str = ""
    confidence: float = 0.0
    promise_detected: bool = False
    all_tests_passed: bool = False
    no_errors: bool = True


class RalphTaskConfig(BaseModel):
    """Configuration for a Ralph task"""
    # Completion settings
    completion_promise: str = "<promise>COMPLETE</promise>"
    max_iterations: int = 50
    iteration_timeout_seconds: int = 300

    # Backpressure settings
    run_tests: bool = True
    run_lint: bool = True
    run_typecheck: bool = True
    run_build: bool = False
    test_command: Optional[str] = None
    lint_command: Optional[str] = None
    typecheck_command: Optional[str] = None
    build_command: Optional[str] = None

    # Context settings
    include_git_history: bool = True
    include_file_contents: bool = True
    max_context_files: int = 20

    # Working directory
    working_directory: str = "."

    # Model settings
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 16000
    temperature: float = 0.7


class RalphTask(BaseModel):
    """A Ralph Wiggum task to be executed"""
    id: UUID = Field(default_factory=uuid4)

    # Task definition
    prompt: str
    description: str = ""
    config: RalphTaskConfig = Field(default_factory=RalphTaskConfig)

    # Ownership
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None

    # Status
    status: TaskStatus = TaskStatus.PENDING
    current_iteration: int = 0

    # History
    iterations: List[RalphIteration] = Field(default_factory=list)

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    completion_result: Optional[CompletionResult] = None
    final_output: Optional[str] = None
    error: Optional[str] = None

    # Metrics
    total_tool_calls: int = 0
    total_file_changes: int = 0
    total_tokens_used: int = 0

    def start(self):
        """Mark task as started"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, result: CompletionResult, final_output: str = ""):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.completion_result = result
        self.final_output = final_output

    def fail(self, error: str):
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error

    def timeout(self):
        """Mark task as timed out"""
        self.status = TaskStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.error = f"Task timed out after {self.current_iteration} iterations"

    def cancel(self):
        """Cancel the task"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def add_iteration(self, iteration: RalphIteration):
        """Add a completed iteration"""
        self.iterations.append(iteration)
        self.current_iteration = len(self.iterations)
        self.total_tool_calls += len(iteration.tool_calls)
        self.total_file_changes += len(iteration.file_changes)

    def get_duration_seconds(self) -> float:
        """Get total task duration in seconds"""
        if not self.started_at:
            return 0
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the task"""
        return {
            "id": str(self.id),
            "status": self.status.value,
            "prompt_preview": self.prompt[:100] + "..." if len(self.prompt) > 100 else self.prompt,
            "iterations_completed": self.current_iteration,
            "max_iterations": self.config.max_iterations,
            "duration_seconds": self.get_duration_seconds(),
            "total_tool_calls": self.total_tool_calls,
            "total_file_changes": self.total_file_changes,
            "is_complete": self.completion_result.is_complete if self.completion_result else False,
            "error": self.error,
        }


class TaskCreateRequest(BaseModel):
    """Request to create a new Ralph task"""
    prompt: str = Field(..., min_length=10, description="The task description")
    description: str = Field(default="", description="Optional human-readable description")

    # Optional config overrides
    completion_promise: Optional[str] = None
    max_iterations: Optional[int] = Field(default=None, ge=1, le=1000)
    working_directory: Optional[str] = None

    # Backpressure options
    run_tests: Optional[bool] = None
    test_command: Optional[str] = None
    run_lint: Optional[bool] = None
    lint_command: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """Response for task status queries"""
    id: str
    status: TaskStatus
    current_iteration: int
    max_iterations: int
    duration_seconds: float
    is_complete: bool
    completion_message: Optional[str] = None
    error: Optional[str] = None
    iterations_summary: List[Dict[str, Any]] = Field(default_factory=list)
