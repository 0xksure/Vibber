"""
GitHub Tool - Handles GitHub interactions
"""

from typing import Any, Dict, List, Optional
import structlog
from github import Github, GithubException
from github.PullRequest import PullRequest

from src.config import settings
from src.tools.base import BaseTool

logger = structlog.get_logger()


class GitHubTool(BaseTool):
    """
    Tool for interacting with GitHub.

    Capabilities:
    - Review pull requests
    - Comment on PRs and issues
    - Approve/request changes on PRs
    - Manage issues
    - Add labels
    """

    name = "github"
    description = "Interact with GitHub repositories"

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        self.client = Github(self.token) if self.token else None

    async def execute(
        self,
        action: str,
        response_text: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a GitHub action"""
        if not self.client:
            return {"success": False, "error": "GitHub client not configured"}

        try:
            if action == "comment":
                return await self._add_comment(input_data, response_text)

            elif action == "review_code":
                return await self._review_pr(input_data, response_text)

            elif action == "approve":
                return await self._approve_pr(input_data, response_text)

            elif action == "request_changes":
                return await self._request_changes(input_data, response_text)

            elif action == "triage":
                return await self._triage_issue(input_data, response_text)

            elif action == "add_label":
                return await self._add_label(input_data, response_text)

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except GithubException as e:
            logger.error(f"GitHub API error: {e}")
            return {"success": False, "error": str(e)}

        except Exception as e:
            logger.error(f"GitHub tool error: {e}")
            return {"success": False, "error": str(e)}

    async def _add_comment(
        self,
        input_data: Dict[str, Any],
        text: str
    ) -> Dict[str, Any]:
        """Add a comment to a PR or issue"""
        repo_name = self._get_repo_name(input_data)
        if not repo_name:
            return {"success": False, "error": "Repository not specified"}

        repo = self.client.get_repo(repo_name)

        # Check if it's a PR or issue
        if "pull_request" in input_data:
            pr_number = input_data["pull_request"]["number"]
            pr = repo.get_pull(pr_number)
            comment = pr.create_issue_comment(text)
        elif "issue" in input_data:
            issue_number = input_data["issue"]["number"]
            issue = repo.get_issue(issue_number)
            comment = issue.create_comment(text)
        else:
            return {"success": False, "error": "No PR or issue in input"}

        return {
            "success": True,
            "comment_id": comment.id,
            "comment_url": comment.html_url
        }

    async def _review_pr(
        self,
        input_data: Dict[str, Any],
        review_body: str
    ) -> Dict[str, Any]:
        """Submit a code review on a PR"""
        repo_name = self._get_repo_name(input_data)
        if not repo_name:
            return {"success": False, "error": "Repository not specified"}

        repo = self.client.get_repo(repo_name)
        pr_number = input_data.get("pull_request", {}).get("number")

        if not pr_number:
            return {"success": False, "error": "PR number not found"}

        pr = repo.get_pull(pr_number)

        # Create a review with COMMENT event (doesn't approve or request changes)
        review = pr.create_review(body=review_body, event="COMMENT")

        return {
            "success": True,
            "review_id": review.id,
            "state": review.state
        }

    async def _approve_pr(
        self,
        input_data: Dict[str, Any],
        comment: str
    ) -> Dict[str, Any]:
        """Approve a pull request"""
        repo_name = self._get_repo_name(input_data)
        if not repo_name:
            return {"success": False, "error": "Repository not specified"}

        repo = self.client.get_repo(repo_name)
        pr_number = input_data.get("pull_request", {}).get("number")

        if not pr_number:
            return {"success": False, "error": "PR number not found"}

        pr = repo.get_pull(pr_number)
        review = pr.create_review(body=comment, event="APPROVE")

        return {
            "success": True,
            "review_id": review.id,
            "state": "APPROVED"
        }

    async def _request_changes(
        self,
        input_data: Dict[str, Any],
        comment: str
    ) -> Dict[str, Any]:
        """Request changes on a pull request"""
        repo_name = self._get_repo_name(input_data)
        if not repo_name:
            return {"success": False, "error": "Repository not specified"}

        repo = self.client.get_repo(repo_name)
        pr_number = input_data.get("pull_request", {}).get("number")

        if not pr_number:
            return {"success": False, "error": "PR number not found"}

        pr = repo.get_pull(pr_number)
        review = pr.create_review(body=comment, event="REQUEST_CHANGES")

        return {
            "success": True,
            "review_id": review.id,
            "state": "CHANGES_REQUESTED"
        }

    async def _triage_issue(
        self,
        input_data: Dict[str, Any],
        comment: str
    ) -> Dict[str, Any]:
        """Triage an issue (add labels, comment, assign)"""
        repo_name = self._get_repo_name(input_data)
        if not repo_name:
            return {"success": False, "error": "Repository not specified"}

        repo = self.client.get_repo(repo_name)
        issue_number = input_data.get("issue", {}).get("number")

        if not issue_number:
            return {"success": False, "error": "Issue number not found"}

        issue = repo.get_issue(issue_number)

        # Add comment
        issue.create_comment(comment)

        return {
            "success": True,
            "issue_number": issue_number
        }

    async def _add_label(
        self,
        input_data: Dict[str, Any],
        label: str
    ) -> Dict[str, Any]:
        """Add a label to an issue or PR"""
        repo_name = self._get_repo_name(input_data)
        if not repo_name:
            return {"success": False, "error": "Repository not specified"}

        repo = self.client.get_repo(repo_name)

        if "pull_request" in input_data:
            number = input_data["pull_request"]["number"]
            item = repo.get_issue(number)  # PRs are issues in GitHub API
        elif "issue" in input_data:
            number = input_data["issue"]["number"]
            item = repo.get_issue(number)
        else:
            return {"success": False, "error": "No PR or issue in input"}

        item.add_to_labels(label)

        return {
            "success": True,
            "label": label
        }

    def _get_repo_name(self, input_data: Dict[str, Any]) -> Optional[str]:
        """Extract repository name from input data"""
        if "repository" in input_data:
            return input_data["repository"].get("full_name")
        return None

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate GitHub credentials"""
        try:
            token = credentials.get("access_token")
            if not token:
                return False

            client = Github(token)
            user = client.get_user()
            _ = user.login  # Trigger API call

            return True

        except Exception as e:
            logger.error(f"GitHub credential validation failed: {e}")
            return False

    def get_capabilities(self) -> list:
        """Return GitHub capabilities"""
        return [
            "comment",
            "review_code",
            "approve",
            "request_changes",
            "triage",
            "add_label"
        ]

    async def get_pr_diff(self, repo_name: str, pr_number: int) -> Optional[str]:
        """Get the diff of a pull request"""
        if not self.client:
            return None

        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # Get files changed
            files = pr.get_files()
            diff_parts = []

            for file in files:
                diff_parts.append(f"--- {file.filename}")
                diff_parts.append(f"+++ {file.filename}")
                if file.patch:
                    diff_parts.append(file.patch)
                diff_parts.append("")

            return "\n".join(diff_parts)

        except Exception as e:
            logger.error(f"Failed to get PR diff: {e}")
            return None
