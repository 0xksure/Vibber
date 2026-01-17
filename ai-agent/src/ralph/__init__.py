"""
Ralph Wiggum Agent Module

Implements the Ralph Wiggum technique for autonomous AI task iteration.
Named after the Simpsons character who is perpetually confused, always
makes mistakes, but never stops trying.

The technique repeatedly feeds an AI agent the same prompt until a stop
condition is met. The agent sees its previous work (via git history and
modified files), learns from it, and iteratively improves.

Philosophy: "The technique is deterministically bad in an undeterministic
world. It's better to fail predictably than succeed unpredictably."
"""

from src.ralph.loop_agent import RalphLoopAgent
from src.ralph.models import (
    RalphTask,
    RalphIteration,
    TaskStatus,
    CompletionResult,
)
from src.ralph.completion import CompletionDetector
from src.ralph.context import ContextBuilder

__all__ = [
    "RalphLoopAgent",
    "RalphTask",
    "RalphIteration",
    "TaskStatus",
    "CompletionResult",
    "CompletionDetector",
    "ContextBuilder",
]
