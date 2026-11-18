import json
import logging
from typing import Any, Optional
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """
        Initialize the Redis connection pool.
        """
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            # Ping to verify connection
            await self.redis_client.ping()
            logger.info(f"Successfully connected to Redis at {settings.REDIS_URL}")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}); caching disabled, rate limits in-memory.")
            self.redis_client = None

    async def disconnect(self):
        """
        Close the Redis connection pool safely.
        """
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info("Disconnected from Redis.")

    async def get_cache(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the Redis cache.
        """
        if not self.redis_client:
            return None
            
        try:
            val = await self.redis_client.get(key)
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Error fetching cache key '{key}': {e}")
            return None

    async def delete_prefix(self, prefix: str):
        if not self.redis_client:
            return
        try:
            async for key in self.redis_client.scan_iter(f"{prefix}*"):
                await self.redis_client.delete(key)
        except Exception:
            pass

    async def set_cache(self, key: str, value: Any, expire_seconds: int = 300) -> bool:
        """
        Save a value to the Redis cache with an expiration time.
        """
        if not self.redis_client:
            return False
            
        try:
            val_str = json.dumps(value)
            await self.redis_client.set(name=key, value=val_str, ex=expire_seconds)
            return True
        except Exception as e:
            logger.error(f"Error setting cache key '{key}': {e}")
            return False

# Singleton instance
redis_service = RedisService()
