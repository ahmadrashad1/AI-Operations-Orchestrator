"""Redis-based job queue for async dispatch."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import redis

if TYPE_CHECKING:
    from redis.client import Redis


class JobStatus(StrEnum):
    """Job status states."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class Job:
    """Background job."""

    def __init__(
        self,
        job_id: str,
        job_type: str,
        payload: dict[str, Any],
        status: JobStatus = JobStatus.PENDING,
        retry_count: int = 0,
        max_retries: int = 5,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        error: str | None = None,
    ):
        self.job_id = job_id
        self.job_type = job_type
        self.payload = payload
        self.status = status
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.created_at = created_at or datetime.now(UTC)
        self.updated_at = updated_at or datetime.now(UTC)
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Serialize for Redis HASH fields (flat string values only)."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "payload": json.dumps(self.payload),
            "status": self.status.value,
            "retry_count": str(self.retry_count),
            "max_retries": str(self.max_retries),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error": self.error if self.error is not None else "",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        """Restore from Redis HASH (string values)."""
        raw_payload = data.get("payload")
        if isinstance(raw_payload, str):
            payload: dict[str, Any] = json.loads(raw_payload)
        else:
            payload = raw_payload  # type: ignore[assignment]

        err = data.get("error")
        if err == "":
            err = None

        return cls(
            job_id=data["job_id"],
            job_type=data["job_type"],
            payload=payload,
            status=JobStatus(data.get("status", "pending")),
            retry_count=int(data.get("retry_count", 0)),
            max_retries=int(data.get("max_retries", 5)),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else None,
            error=err,
        )


class RedisJobQueue:
    """Redis-backed job queue."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client: Redis = redis.from_url(redis_url, decode_responses=True)
        self.queue_key = "job_queue"
        self.processing_key = "job_processing"
        self.dead_letter_key = "job_dead_letter"

    def enqueue(self, job_type: str, payload: dict[str, Any], job_id: str | None = None) -> Job:
        """Enqueue a job."""
        job_id = job_id or str(uuid.uuid4())
        job = Job(job_id=job_id, job_type=job_type, payload=payload)

        # Store job metadata
        self.redis_client.hset(f"job:{job_id}", mapping=job.to_dict())
        self.redis_client.expire(f"job:{job_id}", 86400 * 7)  # 7 days TTL

        # Add to queue
        self.redis_client.rpush(self.queue_key, job_id)

        return job

    def dequeue(self) -> Job | None:
        """Dequeue next pending job."""
        job_id = self.redis_client.lpop(self.queue_key)
        if not job_id:
            return None

        # Move to processing
        self.redis_client.rpush(self.processing_key, job_id)
        job_data = self.redis_client.hgetall(f"job:{job_id}")

        if not job_data:
            return None

        job = Job.from_dict(job_data)
        job.status = JobStatus.PROCESSING
        self._update_job(job)

        return job

    def mark_completed(self, job_id: str) -> None:
        """Mark job as completed."""
        job_data = self.redis_client.hgetall(f"job:{job_id}")
        if not job_data:
            return

        job = Job.from_dict(job_data)
        job.status = JobStatus.COMPLETED
        job.updated_at = datetime.now(UTC)
        self._update_job(job)
        self.redis_client.lrem(self.processing_key, 1, job_id)

    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed."""
        job_data = self.redis_client.hgetall(f"job:{job_id}")
        if not job_data:
            return

        job = Job.from_dict(job_data)
        job.retry_count += 1
        job.error = error
        job.updated_at = datetime.now(UTC)

        if job.retry_count >= job.max_retries:
            job.status = JobStatus.FAILED
            # Move to dead letter queue
            self.redis_client.rpush(self.dead_letter_key, job_id)
        else:
            job.status = JobStatus.RETRYING
            # Re-enqueue with exponential backoff
            backoff_seconds = min(2**job.retry_count, 3600)  # Max 1 hour
            self.redis_client.rpush(self.queue_key, job_id)
            self.redis_client.expire(f"job:{job_id}", backoff_seconds)

        self._update_job(job)
        self.redis_client.lrem(self.processing_key, 1, job_id)

    def get_job(self, job_id: str) -> Job | None:
        """Retrieve job by ID."""
        job_data = self.redis_client.hgetall(f"job:{job_id}")
        if not job_data:
            return None
        return Job.from_dict(job_data)

    def get_queue_size(self) -> int:
        """Get number of pending jobs."""
        return self.redis_client.llen(self.queue_key)

    def get_processing_count(self) -> int:
        """Get number of processing jobs."""
        return self.redis_client.llen(self.processing_key)

    def get_dead_letter_count(self) -> int:
        """Get number of failed jobs."""
        return self.redis_client.llen(self.dead_letter_key)

    def list_dead_letter_jobs(self, limit: int = 100) -> list[Job]:
        """List jobs in dead letter queue."""
        job_ids = self.redis_client.lrange(self.dead_letter_key, 0, limit - 1)
        jobs = []
        for job_id in job_ids:
            job = self.get_job(job_id)
            if job:
                jobs.append(job)
        return jobs

    def clear_queue(self) -> None:
        """Clear all queues (for testing)."""
        self.redis_client.delete(self.queue_key)
        self.redis_client.delete(self.processing_key)
        self.redis_client.delete(self.dead_letter_key)

    def _update_job(self, job: Job) -> None:
        """Update job data in Redis."""
        self.redis_client.hset(f"job:{job.job_id}", mapping=job.to_dict())
        self.redis_client.expire(f"job:{job.job_id}", 86400 * 7)  # 7 days TTL

    def health_check(self) -> bool:
        """Check if Redis is accessible."""
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False
