"""
Redis Cache - Fast caching layer for agent state and sessions
"""

from typing import Any, Optional
import json
import structlog
import redis.asyncio as redis

from src.config import settings

logger = structlog.get_logger()


class RedisCache:
    """
    Redis-based caching for agent state and session data.
    """

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connected = False

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )

            # Test connection
            await self.client.ping()
            self._connected = True

            logger.info("Redis cache initialized")

        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
            self._connected = False
            self._fallback_cache = {}

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[str]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            if self._connected:
                return await self.client.get(key)
            else:
                return self._fallback_cache.get(key)

        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            Success boolean
        """
        try:
            if self._connected:
                if ttl:
                    await self.client.setex(key, ttl, value)
                else:
                    await self.client.set(key, value)
            else:
                self._fallback_cache[key] = value

            return True

        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            Success boolean
        """
        try:
            if self._connected:
                await self.client.delete(key)
            else:
                self._fallback_cache.pop(key, None)

            return True

        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return False

    async def get_json(self, key: str) -> Optional[Any]:
        """Get and parse JSON value"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value as JSON"""
        try:
            json_str = json.dumps(value)
            return await self.set(key, json_str, ttl)
        except (TypeError, json.JSONEncodeError):
            return False

    async def incr(self, key: str) -> int:
        """Increment a counter"""
        try:
            if self._connected:
                return await self.client.incr(key)
            else:
                self._fallback_cache[key] = self._fallback_cache.get(key, 0) + 1
                return self._fallback_cache[key]

        except Exception as e:
            logger.error(f"Cache incr failed: {e}")
            return 0

    async def lpush(self, key: str, *values: str) -> int:
        """Push values to a list"""
        try:
            if self._connected:
                return await self.client.lpush(key, *values)
            else:
                if key not in self._fallback_cache:
                    self._fallback_cache[key] = []
                self._fallback_cache[key] = list(values) + self._fallback_cache[key]
                return len(self._fallback_cache[key])

        except Exception as e:
            logger.error(f"Cache lpush failed: {e}")
            return 0

    async def lrange(self, key: str, start: int, end: int) -> list:
        """Get range from list"""
        try:
            if self._connected:
                return await self.client.lrange(key, start, end)
            else:
                lst = self._fallback_cache.get(key, [])
                return lst[start:end + 1 if end >= 0 else None]

        except Exception as e:
            logger.error(f"Cache lrange failed: {e}")
            return []

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key"""
        try:
            if self._connected:
                return await self.client.expire(key, ttl)
            return True  # No expiration in fallback

        except Exception as e:
            logger.error(f"Cache expire failed: {e}")
            return False
