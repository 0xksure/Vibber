"""
MCP Service - Model Context Protocol integration for dynamic tool servers
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID
import structlog

from src.config import settings
from src.services.credentials import CredentialsClient

logger = structlog.get_logger()


class MCPTool:
    """Represents an MCP tool with its schema and handler"""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler


class MCPServer:
    """
    MCP Server implementation for a specific provider.
    Implements the Model Context Protocol for AI tool integration.
    """

    def __init__(
        self,
        provider: str,
        credentials: Dict[str, str],
        org_id: UUID
    ):
        self.provider = provider
        self.credentials = credentials
        self.org_id = org_id
        self.tools: Dict[str, MCPTool] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the MCP server with provider-specific tools"""
        if self._initialized:
            return

        logger.info("Initializing MCP server", provider=self.provider)

        # Register provider-specific tools
        if self.provider == "slack":
            await self._register_slack_tools()
        elif self.provider == "github":
            await self._register_github_tools()
        elif self.provider == "jira":
            await self._register_jira_tools()

        self._initialized = True
        logger.info(
            "MCP server initialized",
            provider=self.provider,
            tools=list(self.tools.keys())
        )

    async def _register_slack_tools(self):
        """Register Slack-specific MCP tools"""
        from slack_sdk.web.async_client import AsyncWebClient

        client = AsyncWebClient(token=self.credentials.get("clientSecret"))

        # Send Message tool
        self.tools["slack_send_message"] = MCPTool(
            name="slack_send_message",
            description="Send a message to a Slack channel",
            input_schema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel ID or name"},
                    "text": {"type": "string", "description": "Message text"},
                    "thread_ts": {"type": "string", "description": "Thread timestamp for replies"}
                },
                "required": ["channel", "text"]
            },
            handler=lambda params: self._slack_send_message(client, params)
        )

        # Get Channel History tool
        self.tools["slack_get_history"] = MCPTool(
            name="slack_get_history",
            description="Get recent messages from a Slack channel",
            input_schema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel ID"},
                    "limit": {"type": "integer", "description": "Number of messages", "default": 10}
                },
                "required": ["channel"]
            },
            handler=lambda params: self._slack_get_history(client, params)
        )

        # Get User Info tool
        self.tools["slack_get_user"] = MCPTool(
            name="slack_get_user",
            description="Get information about a Slack user",
            input_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Slack user ID"}
                },
                "required": ["user_id"]
            },
            handler=lambda params: self._slack_get_user(client, params)
        )

    async def _slack_send_message(self, client, params: Dict) -> Dict:
        """Send a Slack message"""
        try:
            response = await client.chat_postMessage(
                channel=params["channel"],
                text=params["text"],
                thread_ts=params.get("thread_ts")
            )
            return {"success": True, "ts": response["ts"], "channel": response["channel"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _slack_get_history(self, client, params: Dict) -> Dict:
        """Get Slack channel history"""
        try:
            response = await client.conversations_history(
                channel=params["channel"],
                limit=params.get("limit", 10)
            )
            return {"success": True, "messages": response["messages"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _slack_get_user(self, client, params: Dict) -> Dict:
        """Get Slack user info"""
        try:
            response = await client.users_info(user=params["user_id"])
            return {"success": True, "user": response["user"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _register_github_tools(self):
        """Register GitHub-specific MCP tools"""
        import httpx

        token = self.credentials.get("clientSecret")
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # List Issues tool
        self.tools["github_list_issues"] = MCPTool(
            name="github_list_issues",
            description="List issues in a GitHub repository",
            input_schema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"}
                },
                "required": ["owner", "repo"]
            },
            handler=lambda params: self._github_list_issues(headers, params)
        )

        # Create Issue tool
        self.tools["github_create_issue"] = MCPTool(
            name="github_create_issue",
            description="Create a new issue in a GitHub repository",
            input_schema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "title": {"type": "string", "description": "Issue title"},
                    "body": {"type": "string", "description": "Issue body"}
                },
                "required": ["owner", "repo", "title"]
            },
            handler=lambda params: self._github_create_issue(headers, params)
        )

        # Comment on Issue tool
        self.tools["github_comment_issue"] = MCPTool(
            name="github_comment_issue",
            description="Add a comment to a GitHub issue",
            input_schema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "issue_number": {"type": "integer", "description": "Issue number"},
                    "body": {"type": "string", "description": "Comment body"}
                },
                "required": ["owner", "repo", "issue_number", "body"]
            },
            handler=lambda params: self._github_comment_issue(headers, params)
        )

        # List Pull Requests tool
        self.tools["github_list_prs"] = MCPTool(
            name="github_list_prs",
            description="List pull requests in a GitHub repository",
            input_schema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"}
                },
                "required": ["owner", "repo"]
            },
            handler=lambda params: self._github_list_prs(headers, params)
        )

    async def _github_list_issues(self, headers: Dict, params: Dict) -> Dict:
        """List GitHub issues"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/repos/{params['owner']}/{params['repo']}/issues",
                    headers=headers,
                    params={"state": params.get("state", "open")}
                )
                return {"success": True, "issues": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _github_create_issue(self, headers: Dict, params: Dict) -> Dict:
        """Create a GitHub issue"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.github.com/repos/{params['owner']}/{params['repo']}/issues",
                    headers=headers,
                    json={
                        "title": params["title"],
                        "body": params.get("body", "")
                    }
                )
                return {"success": True, "issue": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _github_comment_issue(self, headers: Dict, params: Dict) -> Dict:
        """Comment on a GitHub issue"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.github.com/repos/{params['owner']}/{params['repo']}/issues/{params['issue_number']}/comments",
                    headers=headers,
                    json={"body": params["body"]}
                )
                return {"success": True, "comment": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _github_list_prs(self, headers: Dict, params: Dict) -> Dict:
        """List GitHub pull requests"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/repos/{params['owner']}/{params['repo']}/pulls",
                    headers=headers,
                    params={"state": params.get("state", "open")}
                )
                return {"success": True, "pull_requests": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _register_jira_tools(self):
        """Register Jira-specific MCP tools"""
        import httpx
        from base64 import b64encode

        client_id = self.credentials.get("clientId")
        client_secret = self.credentials.get("clientSecret")

        # Jira cloud uses OAuth, but for simplicity we'll use basic auth pattern
        # In production, this would use proper OAuth token flow

        # Search Issues tool
        self.tools["jira_search_issues"] = MCPTool(
            name="jira_search_issues",
            description="Search for Jira issues using JQL",
            input_schema={
                "type": "object",
                "properties": {
                    "jql": {"type": "string", "description": "JQL query string"},
                    "max_results": {"type": "integer", "description": "Maximum results", "default": 50}
                },
                "required": ["jql"]
            },
            handler=lambda params: self._jira_search(params)
        )

        # Create Issue tool
        self.tools["jira_create_issue"] = MCPTool(
            name="jira_create_issue",
            description="Create a new Jira issue",
            input_schema={
                "type": "object",
                "properties": {
                    "project_key": {"type": "string", "description": "Project key"},
                    "summary": {"type": "string", "description": "Issue summary"},
                    "description": {"type": "string", "description": "Issue description"},
                    "issue_type": {"type": "string", "description": "Issue type", "default": "Task"}
                },
                "required": ["project_key", "summary"]
            },
            handler=lambda params: self._jira_create_issue(params)
        )

        # Add Comment tool
        self.tools["jira_add_comment"] = MCPTool(
            name="jira_add_comment",
            description="Add a comment to a Jira issue",
            input_schema={
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string", "description": "Issue key (e.g., PROJ-123)"},
                    "comment": {"type": "string", "description": "Comment text"}
                },
                "required": ["issue_key", "comment"]
            },
            handler=lambda params: self._jira_add_comment(params)
        )

        # Transition Issue tool
        self.tools["jira_transition_issue"] = MCPTool(
            name="jira_transition_issue",
            description="Transition a Jira issue to a new status",
            input_schema={
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string", "description": "Issue key (e.g., PROJ-123)"},
                    "transition_id": {"type": "string", "description": "Transition ID"}
                },
                "required": ["issue_key", "transition_id"]
            },
            handler=lambda params: self._jira_transition_issue(params)
        )

    async def _jira_search(self, params: Dict) -> Dict:
        """Search Jira issues"""
        # Placeholder - would use actual Jira API
        return {"success": True, "issues": [], "message": "Jira integration requires site URL configuration"}

    async def _jira_create_issue(self, params: Dict) -> Dict:
        """Create Jira issue"""
        return {"success": True, "message": "Jira integration requires site URL configuration"}

    async def _jira_add_comment(self, params: Dict) -> Dict:
        """Add comment to Jira issue"""
        return {"success": True, "message": "Jira integration requires site URL configuration"}

    async def _jira_transition_issue(self, params: Dict) -> Dict:
        """Transition Jira issue"""
        return {"success": True, "message": "Jira integration requires site URL configuration"}

    def list_tools(self) -> List[Dict]:
        """Return list of available tools with their schemas"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for tool in self.tools.values()
        ]

    async def call_tool(self, name: str, arguments: Dict) -> Dict:
        """Execute an MCP tool"""
        if name not in self.tools:
            return {"error": f"Tool '{name}' not found"}

        tool = self.tools[name]
        try:
            result = await tool.handler(arguments)
            return result
        except Exception as e:
            logger.error("Tool execution failed", tool=name, error=str(e))
            return {"error": str(e)}


class MCPService:
    """
    Service for managing MCP servers across organizations.
    Dynamically creates and manages MCP server instances based on credentials.
    """

    def __init__(self, credentials_client: Optional[CredentialsClient] = None):
        self.credentials_client = credentials_client or CredentialsClient()
        self._servers: Dict[str, MCPServer] = {}
        self._lock = asyncio.Lock()

    async def get_server(self, org_id: UUID, provider: str) -> Optional[MCPServer]:
        """
        Get or create an MCP server for an organization and provider.

        Args:
            org_id: Organization UUID
            provider: Provider name

        Returns:
            MCPServer instance or None if credentials not found
        """
        server_key = f"{org_id}:{provider}"

        async with self._lock:
            # Return existing server if available
            if server_key in self._servers:
                return self._servers[server_key]

            # Fetch credentials
            credentials = await self.credentials_client.get_credentials(org_id, provider)
            if not credentials:
                logger.warning(
                    "No credentials found for MCP server",
                    org_id=str(org_id),
                    provider=provider
                )
                return None

            # Create and initialize new server
            server = MCPServer(provider, credentials, org_id)
            await server.initialize()

            self._servers[server_key] = server
            return server

    async def get_available_tools(self, org_id: UUID) -> List[Dict]:
        """
        Get all available MCP tools for an organization.

        Args:
            org_id: Organization UUID

        Returns:
            List of tool definitions
        """
        tools = []
        providers = ["slack", "github", "jira"]

        for provider in providers:
            server = await self.get_server(org_id, provider)
            if server:
                tools.extend(server.list_tools())

        return tools

    async def execute_tool(
        self,
        org_id: UUID,
        tool_name: str,
        arguments: Dict
    ) -> Dict:
        """
        Execute an MCP tool.

        Args:
            org_id: Organization UUID
            tool_name: Full tool name (e.g., slack_send_message)
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        # Determine provider from tool name
        provider = tool_name.split("_")[0]

        server = await self.get_server(org_id, provider)
        if not server:
            return {"error": f"No MCP server available for provider: {provider}"}

        return await server.call_tool(tool_name, arguments)

    def invalidate_server(self, org_id: UUID, provider: Optional[str] = None):
        """
        Invalidate cached MCP servers when credentials change.

        Args:
            org_id: Organization UUID
            provider: Optional specific provider to invalidate
        """
        if provider:
            server_key = f"{org_id}:{provider}"
            if server_key in self._servers:
                del self._servers[server_key]
                logger.info("Invalidated MCP server", org_id=str(org_id), provider=provider)
        else:
            # Invalidate all servers for this org
            keys_to_remove = [k for k in self._servers.keys() if k.startswith(f"{org_id}:")]
            for key in keys_to_remove:
                del self._servers[key]
            logger.info("Invalidated all MCP servers for org", org_id=str(org_id))

        # Also clear credentials cache
        self.credentials_client.clear_cache(org_id, provider)

    async def shutdown(self):
        """Cleanup all MCP servers"""
        self._servers.clear()
        logger.info("MCP service shutdown complete")
