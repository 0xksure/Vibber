"""
Credentials Client - Fetches OAuth credentials from the backend service
"""

from typing import Dict, Optional
from uuid import UUID
import httpx
import structlog

from src.config import settings

logger = structlog.get_logger()


class CredentialsClient:
    """
    Client for fetching organization OAuth credentials from the backend.
    Uses the internal service key for authentication.
    """

    def __init__(self):
        self.backend_url = settings.backend_url
        self.service_key = settings.internal_service_key
        self._cache: Dict[str, Dict] = {}

    async def get_credentials(
        self,
        org_id: UUID,
        provider: str,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Fetch credentials for a specific organization and provider.

        Args:
            org_id: Organization UUID
            provider: Provider name (slack, github, jira, etc.)
            use_cache: Whether to use cached credentials

        Returns:
            Dictionary containing credentials or None if not found
        """
        cache_key = f"{org_id}:{provider}"

        # Check cache first
        if use_cache and cache_key in self._cache:
            logger.debug("Returning cached credentials", org_id=str(org_id), provider=provider)
            return self._cache[cache_key]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/v1/internal/credentials",
                    params={
                        "org_id": str(org_id),
                        "provider": provider
                    },
                    headers={
                        "X-Service-Key": self.service_key
                    }
                )

                if response.status_code == 200:
                    credentials = response.json()
                    # Cache the credentials
                    self._cache[cache_key] = credentials
                    logger.info(
                        "Fetched credentials from backend",
                        org_id=str(org_id),
                        provider=provider
                    )
                    return credentials

                elif response.status_code == 404:
                    logger.warning(
                        "Credentials not found",
                        org_id=str(org_id),
                        provider=provider
                    )
                    return None

                else:
                    logger.error(
                        "Failed to fetch credentials",
                        status_code=response.status_code,
                        org_id=str(org_id),
                        provider=provider
                    )
                    return None

        except httpx.RequestError as e:
            logger.error(
                "Request error fetching credentials",
                error=str(e),
                org_id=str(org_id),
                provider=provider
            )
            return None

    async def get_all_credentials(self, org_id: UUID) -> Dict[str, Dict]:
        """
        Fetch all credentials for an organization.

        Args:
            org_id: Organization UUID

        Returns:
            Dictionary mapping provider names to credentials
        """
        providers = ["slack", "github", "jira", "confluence", "elastic", "google"]
        credentials = {}

        for provider in providers:
            creds = await self.get_credentials(org_id, provider, use_cache=False)
            if creds:
                credentials[provider] = creds

        return credentials

    def clear_cache(self, org_id: Optional[UUID] = None, provider: Optional[str] = None):
        """
        Clear cached credentials.

        Args:
            org_id: Optional organization ID to clear (clears all if not specified)
            provider: Optional provider to clear
        """
        if org_id is None:
            self._cache.clear()
            logger.info("Cleared all cached credentials")
        elif provider is None:
            # Clear all credentials for this org
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{org_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info("Cleared cached credentials for org", org_id=str(org_id))
        else:
            cache_key = f"{org_id}:{provider}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info("Cleared cached credentials", org_id=str(org_id), provider=provider)

    async def verify_service_connection(self) -> bool:
        """
        Verify that the backend service is reachable.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.backend_url}/health")
                return response.status_code == 200
        except httpx.RequestError:
            return False
