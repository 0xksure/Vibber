"""
Slack Tool - Handles Slack interactions
"""

from typing import Any, Dict, Optional
import structlog
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from src.config import settings
from src.tools.base import BaseTool

logger = structlog.get_logger()


class SlackTool(BaseTool):
    """
    Tool for interacting with Slack.

    Capabilities:
    - Send messages
    - Reply in threads
    - Add reactions
    - Update messages
    """

    name = "slack"
    description = "Interact with Slack workspaces"

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.slack_bot_token
        self.client = AsyncWebClient(token=self.token) if self.token else None

    async def execute(
        self,
        action: str,
        response_text: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Slack action"""
        if not self.client:
            return {"success": False, "error": "Slack client not configured"}

        try:
            if action == "reply" or action == "respond":
                return await self._send_message(input_data, response_text)

            elif action == "react":
                return await self._add_reaction(input_data, response_text)

            elif action == "update":
                return await self._update_message(input_data, response_text)

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            return {"success": False, "error": str(e)}

        except Exception as e:
            logger.error(f"Slack tool error: {e}")
            return {"success": False, "error": str(e)}

    async def _send_message(
        self,
        input_data: Dict[str, Any],
        text: str
    ) -> Dict[str, Any]:
        """Send a message or reply in thread"""
        channel = input_data.get("channel") or input_data.get("channel_id")
        thread_ts = input_data.get("thread_ts") or input_data.get("ts")

        if not channel:
            return {"success": False, "error": "No channel specified"}

        response = await self.client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts  # Reply in thread if original was in thread
        )

        return {
            "success": True,
            "message_ts": response["ts"],
            "channel": response["channel"]
        }

    async def _add_reaction(
        self,
        input_data: Dict[str, Any],
        emoji: str
    ) -> Dict[str, Any]:
        """Add a reaction to a message"""
        channel = input_data.get("channel") or input_data.get("channel_id")
        timestamp = input_data.get("ts") or input_data.get("message_ts")

        if not channel or not timestamp:
            return {"success": False, "error": "Missing channel or timestamp"}

        # Clean emoji name (remove colons if present)
        emoji = emoji.strip(":")

        await self.client.reactions_add(
            channel=channel,
            timestamp=timestamp,
            name=emoji
        )

        return {"success": True, "reaction": emoji}

    async def _update_message(
        self,
        input_data: Dict[str, Any],
        text: str
    ) -> Dict[str, Any]:
        """Update an existing message"""
        channel = input_data.get("channel") or input_data.get("channel_id")
        timestamp = input_data.get("ts") or input_data.get("message_ts")

        if not channel or not timestamp:
            return {"success": False, "error": "Missing channel or timestamp"}

        response = await self.client.chat_update(
            channel=channel,
            ts=timestamp,
            text=text
        )

        return {
            "success": True,
            "message_ts": response["ts"]
        }

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Slack credentials"""
        try:
            token = credentials.get("access_token")
            if not token:
                return False

            client = AsyncWebClient(token=token)
            response = await client.auth_test()

            return response["ok"]

        except Exception as e:
            logger.error(f"Slack credential validation failed: {e}")
            return False

    def get_capabilities(self) -> list:
        """Return Slack capabilities"""
        return [
            "reply",
            "respond",
            "react",
            "update"
        ]

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a Slack user"""
        if not self.client:
            return None

        try:
            response = await self.client.users_info(user=user_id)
            if response["ok"]:
                return response["user"]
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")

        return None

    async def get_channel_history(
        self,
        channel: str,
        limit: int = 10
    ) -> list:
        """Get recent messages from a channel"""
        if not self.client:
            return []

        try:
            response = await self.client.conversations_history(
                channel=channel,
                limit=limit
            )
            if response["ok"]:
                return response["messages"]
        except Exception as e:
            logger.error(f"Failed to get channel history: {e}")

        return []
