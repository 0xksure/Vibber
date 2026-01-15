"""
Jira Tool - Handles Jira interactions
"""

from typing import Any, Dict, List, Optional
import structlog
from atlassian import Jira

from src.config import settings
from src.tools.base import BaseTool

logger = structlog.get_logger()


class JiraTool(BaseTool):
    """
    Tool for interacting with Jira.

    Capabilities:
    - Add comments to issues
    - Update issue status
    - Assign issues
    - Create subtasks
    - Update fields
    """

    name = "jira"
    description = "Interact with Jira projects"

    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        api_token: Optional[str] = None
    ):
        self.url = url
        self.username = username
        self.api_token = api_token or settings.jira_api_token
        self.client = None

        if self.url and self.username and self.api_token:
            self.client = Jira(
                url=self.url,
                username=self.username,
                password=self.api_token
            )

    async def execute(
        self,
        action: str,
        response_text: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Jira action"""
        if not self.client:
            return {"success": False, "error": "Jira client not configured"}

        try:
            if action == "comment" or action == "respond":
                return await self._add_comment(input_data, response_text)

            elif action == "update_status":
                return await self._update_status(input_data, response_text)

            elif action == "assign":
                return await self._assign_issue(input_data, response_text)

            elif action == "acknowledge":
                return await self._acknowledge(input_data, response_text)

            elif action == "triage_and_update":
                return await self._triage(input_data, response_text)

            elif action == "update_field":
                return await self._update_field(input_data, response_text)

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"Jira tool error: {e}")
            return {"success": False, "error": str(e)}

    async def _add_comment(
        self,
        input_data: Dict[str, Any],
        text: str
    ) -> Dict[str, Any]:
        """Add a comment to an issue"""
        issue_key = self._get_issue_key(input_data)
        if not issue_key:
            return {"success": False, "error": "Issue key not found"}

        self.client.issue_add_comment(issue_key, text)

        return {
            "success": True,
            "issue_key": issue_key
        }

    async def _update_status(
        self,
        input_data: Dict[str, Any],
        status: str
    ) -> Dict[str, Any]:
        """Update issue status through transition"""
        issue_key = self._get_issue_key(input_data)
        if not issue_key:
            return {"success": False, "error": "Issue key not found"}

        # Get available transitions
        transitions = self.client.get_issue_transitions(issue_key)

        # Find matching transition
        target_transition = None
        for t in transitions:
            if t["name"].lower() == status.lower():
                target_transition = t
                break

        if not target_transition:
            available = [t["name"] for t in transitions]
            return {
                "success": False,
                "error": f"Transition '{status}' not available. Available: {available}"
            }

        # Execute transition
        self.client.issue_transition(issue_key, target_transition["id"])

        return {
            "success": True,
            "issue_key": issue_key,
            "new_status": status
        }

    async def _assign_issue(
        self,
        input_data: Dict[str, Any],
        assignee: str
    ) -> Dict[str, Any]:
        """Assign an issue to a user"""
        issue_key = self._get_issue_key(input_data)
        if not issue_key:
            return {"success": False, "error": "Issue key not found"}

        self.client.assign_issue(issue_key, assignee)

        return {
            "success": True,
            "issue_key": issue_key,
            "assignee": assignee
        }

    async def _acknowledge(
        self,
        input_data: Dict[str, Any],
        comment: str
    ) -> Dict[str, Any]:
        """Acknowledge an issue with a comment"""
        issue_key = self._get_issue_key(input_data)
        if not issue_key:
            return {"success": False, "error": "Issue key not found"}

        # Add acknowledgment comment
        ack_comment = f"Acknowledged. {comment}"
        self.client.issue_add_comment(issue_key, ack_comment)

        return {
            "success": True,
            "issue_key": issue_key,
            "action": "acknowledged"
        }

    async def _triage(
        self,
        input_data: Dict[str, Any],
        analysis: str
    ) -> Dict[str, Any]:
        """Triage an issue - analyze and update with findings"""
        issue_key = self._get_issue_key(input_data)
        if not issue_key:
            return {"success": False, "error": "Issue key not found"}

        # Add triage comment
        triage_comment = f"**Triage Analysis:**\n\n{analysis}"
        self.client.issue_add_comment(issue_key, triage_comment)

        return {
            "success": True,
            "issue_key": issue_key,
            "action": "triaged"
        }

    async def _update_field(
        self,
        input_data: Dict[str, Any],
        field_update: str
    ) -> Dict[str, Any]:
        """Update a specific field on an issue"""
        issue_key = self._get_issue_key(input_data)
        if not issue_key:
            return {"success": False, "error": "Issue key not found"}

        # Parse field update (expected format: "field_name:value")
        if ":" not in field_update:
            return {"success": False, "error": "Invalid field update format"}

        field_name, value = field_update.split(":", 1)

        self.client.update_issue_field(
            issue_key,
            {field_name.strip(): value.strip()}
        )

        return {
            "success": True,
            "issue_key": issue_key,
            "field": field_name.strip(),
            "value": value.strip()
        }

    def _get_issue_key(self, input_data: Dict[str, Any]) -> Optional[str]:
        """Extract issue key from input data"""
        # Try direct key
        if "issue_key" in input_data:
            return input_data["issue_key"]

        # Try nested issue object
        if "issue" in input_data:
            issue = input_data["issue"]
            if isinstance(issue, dict):
                return issue.get("key")

        # Try key field
        if "key" in input_data:
            return input_data["key"]

        return None

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Jira credentials"""
        try:
            url = credentials.get("url")
            username = credentials.get("username")
            api_token = credentials.get("access_token")

            if not all([url, username, api_token]):
                return False

            client = Jira(url=url, username=username, password=api_token)
            # Try to get current user
            client.myself()

            return True

        except Exception as e:
            logger.error(f"Jira credential validation failed: {e}")
            return False

    def get_capabilities(self) -> list:
        """Return Jira capabilities"""
        return [
            "comment",
            "respond",
            "update_status",
            "assign",
            "acknowledge",
            "triage_and_update",
            "update_field"
        ]

    async def get_issue_details(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get full details of an issue"""
        if not self.client:
            return None

        try:
            issue = self.client.issue(issue_key)
            return {
                "key": issue["key"],
                "summary": issue["fields"]["summary"],
                "description": issue["fields"].get("description"),
                "status": issue["fields"]["status"]["name"],
                "priority": issue["fields"]["priority"]["name"] if issue["fields"].get("priority") else None,
                "assignee": issue["fields"]["assignee"]["displayName"] if issue["fields"].get("assignee") else None,
                "reporter": issue["fields"]["reporter"]["displayName"] if issue["fields"].get("reporter") else None,
                "created": issue["fields"]["created"],
                "updated": issue["fields"]["updated"]
            }
        except Exception as e:
            logger.error(f"Failed to get issue details: {e}")
            return None
