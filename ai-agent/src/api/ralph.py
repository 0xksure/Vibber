"""
Ralph Wiggum API Endpoints

Provides REST API for:
- Submitting tasks
- Checking task status
- Cancelling tasks
- Viewing task history
"""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.ralph.models import (
    RalphTask,
    RalphTaskConfig,
    TaskCreateRequest,
    TaskStatus,
    TaskStatusResponse,
)
from src.ralph.loop_agent import RalphLoopAgent, RalphTaskRunner

logger = structlog.get_logger()

router = APIRouter()

# Global task runner instance
_task_runner: Optional[RalphTaskRunner] = None


def get_task_runner() -> RalphTaskRunner:
    """Dependency to get the task runner"""
    global _task_runner
    if _task_runner is None:
        _task_runner = RalphTaskRunner(max_concurrent_tasks=5)
    return _task_runner


class CreateTaskRequest(BaseModel):
    """Request body for creating a new Ralph task"""
    prompt: str = Field(
        ...,
        min_length=10,
        description="The task description - what should the AI accomplish?"
    )
    description: str = Field(
        default="",
        description="Optional human-readable description"
    )

    # Config overrides
    completion_promise: Optional[str] = Field(
        default=None,
        description="Custom completion signal (default: <promise>COMPLETE</promise>)"
    )
    max_iterations: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum iterations before timeout (default: 50)"
    )
    working_directory: Optional[str] = Field(
        default=None,
        description="Working directory for the task (default: current directory)"
    )

    # Backpressure options
    run_tests: bool = Field(
        default=True,
        description="Run tests after each iteration"
    )
    test_command: Optional[str] = Field(
        default=None,
        description="Custom test command (auto-detected if not provided)"
    )
    run_lint: bool = Field(
        default=True,
        description="Run linting after each iteration"
    )
    lint_command: Optional[str] = Field(
        default=None,
        description="Custom lint command"
    )
    run_typecheck: bool = Field(
        default=False,
        description="Run type checking after each iteration"
    )
    typecheck_command: Optional[str] = Field(
        default=None,
        description="Custom typecheck command"
    )

    # Model settings
    model: Optional[str] = Field(
        default=None,
        description="Claude model to use (default: claude-sonnet-4-20250514)"
    )

    # User context
    user_id: Optional[str] = Field(
        default=None,
        description="User ID for tracking"
    )
    organization_id: Optional[str] = Field(
        default=None,
        description="Organization ID for tracking"
    )


class TaskResponse(BaseModel):
    """Response for task operations"""
    id: str
    status: str
    message: str


class TaskDetailResponse(BaseModel):
    """Detailed task response"""
    id: str
    status: str
    prompt_preview: str
    description: str
    current_iteration: int
    max_iterations: int
    duration_seconds: float
    total_tool_calls: int
    total_file_changes: int
    is_complete: bool
    error: Optional[str] = None
    final_output: Optional[str] = None
    iterations: List[Dict[str, Any]] = []


class TaskListResponse(BaseModel):
    """Response for listing tasks"""
    tasks: List[Dict[str, Any]]
    total: int


@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    runner: RalphTaskRunner = Depends(get_task_runner),
):
    """
    Create and start a new Ralph task.

    The task will run in the background, iterating until completion
    or the maximum iterations limit is reached.

    Returns the task ID which can be used to check status.
    """
    # Build config
    config = RalphTaskConfig(
        run_tests=request.run_tests,
        run_lint=request.run_lint,
        run_typecheck=request.run_typecheck,
    )

    if request.completion_promise:
        config.completion_promise = request.completion_promise
    if request.max_iterations:
        config.max_iterations = request.max_iterations
    if request.working_directory:
        config.working_directory = request.working_directory
    if request.test_command:
        config.test_command = request.test_command
    if request.lint_command:
        config.lint_command = request.lint_command
    if request.typecheck_command:
        config.typecheck_command = request.typecheck_command
    if request.model:
        config.model = request.model

    # Create task
    task = RalphTask(
        prompt=request.prompt,
        description=request.description,
        config=config,
        user_id=UUID(request.user_id) if request.user_id else None,
        organization_id=UUID(request.organization_id) if request.organization_id else None,
    )

    # Submit task (runs in background)
    await runner.submit_task(task)

    logger.info(
        "Ralph task created",
        task_id=str(task.id),
        prompt_preview=request.prompt[:50],
    )

    return TaskResponse(
        id=str(task.id),
        status="started",
        message="Task started successfully. Use the task ID to check status.",
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: str,
    include_iterations: bool = Query(
        default=False,
        description="Include iteration details in response"
    ),
    runner: RalphTaskRunner = Depends(get_task_runner),
):
    """
    Get the status and details of a Ralph task.
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    status = runner.get_status(task_uuid)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get full task if available
    task = runner._completed_tasks.get(task_uuid)

    response = TaskDetailResponse(
        id=status["id"],
        status=status["status"],
        prompt_preview=status.get("prompt_preview", ""),
        description="",
        current_iteration=status.get("iterations_completed", 0),
        max_iterations=status.get("max_iterations", 0),
        duration_seconds=status.get("duration_seconds", 0),
        total_tool_calls=status.get("total_tool_calls", 0),
        total_file_changes=status.get("total_file_changes", 0),
        is_complete=status.get("is_complete", False),
        error=status.get("error"),
        iterations=[],
    )

    if task:
        response.description = task.description
        response.final_output = task.final_output

        if include_iterations:
            response.iterations = [
                {
                    "number": i.iteration_number,
                    "status": i.status.value,
                    "duration_ms": i.duration_ms,
                    "tool_calls": len(i.tool_calls),
                    "file_changes": [fc.path for fc in i.file_changes],
                    "completion_promise_found": i.completion_promise_found,
                    "error": i.error,
                }
                for i in task.iterations
            ]

    return response


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    runner: RalphTaskRunner = Depends(get_task_runner),
):
    """
    Cancel a running Ralph task.
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    success = runner.cancel_task(task_uuid)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Task not found or already completed"
        )

    return TaskResponse(
        id=task_id,
        status="cancelling",
        message="Task cancellation requested. It will stop after the current iteration.",
    )


@router.get("/tasks/{task_id}/wait", response_model=TaskDetailResponse)
async def wait_for_task(
    task_id: str,
    timeout: int = Query(
        default=300,
        ge=1,
        le=3600,
        description="Maximum time to wait in seconds"
    ),
    runner: RalphTaskRunner = Depends(get_task_runner),
):
    """
    Wait for a task to complete and return the result.

    This is a blocking call that will wait up to the specified timeout.
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    try:
        task = await asyncio.wait_for(
            runner.wait_for_task(task_uuid),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail=f"Task did not complete within {timeout} seconds"
        )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskDetailResponse(
        id=str(task.id),
        status=task.status.value,
        prompt_preview=task.prompt[:100],
        description=task.description,
        current_iteration=task.current_iteration,
        max_iterations=task.config.max_iterations,
        duration_seconds=task.get_duration_seconds(),
        total_tool_calls=task.total_tool_calls,
        total_file_changes=task.total_file_changes,
        is_complete=task.completion_result.is_complete if task.completion_result else False,
        error=task.error,
        final_output=task.final_output,
        iterations=[
            {
                "number": i.iteration_number,
                "status": i.status.value,
                "duration_ms": i.duration_ms,
                "tool_calls": len(i.tool_calls),
                "file_changes": [fc.path for fc in i.file_changes],
                "completion_promise_found": i.completion_promise_found,
                "error": i.error,
            }
            for i in task.iterations
        ],
    )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status (pending, running, completed, failed)"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    runner: RalphTaskRunner = Depends(get_task_runner),
):
    """
    List Ralph tasks.
    """
    tasks = []

    # Add completed tasks
    for task in runner._completed_tasks.values():
        if status and task.status.value != status:
            continue
        tasks.append(task.get_summary())

    # Add running tasks
    for task_id in runner._running_tasks:
        task_status = runner.get_status(task_id)
        if task_status:
            if status and task_status["status"] != status:
                continue
            tasks.append(task_status)

    # Sort by most recent first (assuming id is roughly chronological)
    tasks = sorted(tasks, key=lambda t: t.get("id", ""), reverse=True)[:limit]

    return TaskListResponse(
        tasks=tasks,
        total=len(tasks),
    )


@router.post("/tasks/sync", response_model=TaskDetailResponse)
async def create_and_run_task_sync(
    request: CreateTaskRequest,
    timeout: int = Query(
        default=600,
        ge=60,
        le=3600,
        description="Maximum time to wait for completion"
    ),
    runner: RalphTaskRunner = Depends(get_task_runner),
):
    """
    Create a task and wait for it to complete synchronously.

    This is a convenience endpoint that combines create + wait.
    For long-running tasks, use the async endpoints instead.
    """
    # Build config
    config = RalphTaskConfig(
        run_tests=request.run_tests,
        run_lint=request.run_lint,
        run_typecheck=request.run_typecheck,
    )

    if request.completion_promise:
        config.completion_promise = request.completion_promise
    if request.max_iterations:
        config.max_iterations = request.max_iterations
    if request.working_directory:
        config.working_directory = request.working_directory
    if request.test_command:
        config.test_command = request.test_command
    if request.lint_command:
        config.lint_command = request.lint_command
    if request.typecheck_command:
        config.typecheck_command = request.typecheck_command
    if request.model:
        config.model = request.model

    # Create task
    task = RalphTask(
        prompt=request.prompt,
        description=request.description,
        config=config,
        user_id=UUID(request.user_id) if request.user_id else None,
        organization_id=UUID(request.organization_id) if request.organization_id else None,
    )

    # Run the agent directly
    agent = RalphLoopAgent()

    try:
        completed_task = await asyncio.wait_for(
            agent.run_task(task),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail=f"Task did not complete within {timeout} seconds"
        )

    return TaskDetailResponse(
        id=str(completed_task.id),
        status=completed_task.status.value,
        prompt_preview=completed_task.prompt[:100],
        description=completed_task.description,
        current_iteration=completed_task.current_iteration,
        max_iterations=completed_task.config.max_iterations,
        duration_seconds=completed_task.get_duration_seconds(),
        total_tool_calls=completed_task.total_tool_calls,
        total_file_changes=completed_task.total_file_changes,
        is_complete=completed_task.completion_result.is_complete if completed_task.completion_result else False,
        error=completed_task.error,
        final_output=completed_task.final_output,
        iterations=[
            {
                "number": i.iteration_number,
                "status": i.status.value,
                "duration_ms": i.duration_ms,
                "tool_calls": len(i.tool_calls),
                "file_changes": [fc.path for fc in i.file_changes],
                "completion_promise_found": i.completion_promise_found,
                "error": i.error,
            }
            for i in completed_task.iterations
        ],
    )


# Health check for Ralph service
@router.get("/health")
async def ralph_health():
    """Health check for Ralph Wiggum service"""
    runner = get_task_runner()
    return {
        "status": "healthy",
        "service": "ralph-wiggum",
        "running_tasks": len(runner._running_tasks),
        "completed_tasks": len(runner._completed_tasks),
    }
