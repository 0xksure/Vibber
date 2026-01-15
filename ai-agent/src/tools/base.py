"""
Base Tool Classes - Foundation for integration tools
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


class BaseTool(ABC):
    """
    Base class for all integration tools.

    Tools are responsible for executing actions on external services
    like Slack, GitHub, Jira, etc.
    """

    name: str = "base"
    description: str = "Base tool"

    @abstractmethod
    async def execute(
        self,
        action: str,
        response_text: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an action using this tool.

        Args:
            action: The action to perform (reply, comment, update, etc.)
            response_text: The text/content to use
            input_data: Original input data for context

        Returns:
            Result of the action
        """
        pass

    @abstractmethod
    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Validate that credentials are working.

        Args:
            credentials: OAuth tokens or API keys

        Returns:
            True if credentials are valid
        """
        pass

    def get_capabilities(self) -> List[str]:
        """Return list of actions this tool can perform"""
        return []


class ToolRegistry:
    """
    Registry for managing available tools.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Register a tool"""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tools"""
        return list(self._tools.keys())

    def get_all_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all tools"""
        return {
            name: tool.get_capabilities()
            for name, tool in self._tools.items()
        }
