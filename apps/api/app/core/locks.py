"""Distributed locking using Redis."""
from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator

import redis

if TYPE_CHECKING:
    from redis.client import Redis


class DistributedLock:
    """Redis-backed distributed lock with timeout."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        timeout: int = 30,
        auto_release: bool = True,
    ):
        self.redis_url = redis_url
        self.redis_client: Redis = redis.from_url(redis_url, decode_responses=True)
        self.timeout = timeout
        self.auto_release = auto_release
        self.lock_id = str(uuid.uuid4())

    @contextmanager
    def acquire(self, resource_id: str, ttl: int = 30) -> Generator[bool, None, None]:
        """
        Acquire a distributed lock.

        Args:
            resource_id: Identifier for the locked resource (e.g., workflow_id)
            ttl: Lock time-to-live in seconds

        Yields:
            True if lock acquired, False otherwise
        """
        lock_key = f"lock:{resource_id}"
        max_attempts = self.timeout // 1  # Poll every 1 second
        attempts = 0

        # Try to acquire lock
        while attempts < max_attempts:
            result = self.redis_client.set(
                lock_key,
                self.lock_id,
                nx=True,  # Only set if not exists
                ex=ttl,  # Expiration time
            )

            if result:
                try:
                    yield True
                finally:
                    if self.auto_release:
                        self._release(lock_key)
                return

            attempts += 1
            time.sleep(1)

        # Lock acquisition failed after timeout
        yield False

    def _release(self, lock_key: str) -> None:
        """Release the lock."""
        # Use Lua script to ensure atomicity
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.redis_client.eval(lua_script, 1, lock_key, self.lock_id)

    def is_locked(self, resource_id: str) -> bool:
        """Check if a resource is locked."""
        lock_key = f"lock:{resource_id}"
        return self.redis_client.exists(lock_key) > 0

    def get_lock_owner(self, resource_id: str) -> str | None:
        """Get the ID of the lock holder."""
        lock_key = f"lock:{resource_id}"
        return self.redis_client.get(lock_key)

    def force_release(self, resource_id: str) -> bool:
        """Force release a lock (use with caution)."""
        lock_key = f"lock:{resource_id}"
        result = self.redis_client.delete(lock_key)
        return result > 0

    def health_check(self) -> bool:
        """Check if Redis is accessible."""
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False


@contextmanager
def workflow_lock(redis_url: str, workflow_id: str, timeout: int = 30) -> Generator[bool, None, None]:
    """
    Context manager for workflow-level locking.

    Usage:
        with workflow_lock(redis_url, workflow_id) as acquired:
            if acquired:
                # Perform workflow state changes
                pass
    """
    lock = DistributedLock(redis_url=redis_url, timeout=timeout)
    with lock.acquire(workflow_id, ttl=timeout) as acquired:
        yield acquired
