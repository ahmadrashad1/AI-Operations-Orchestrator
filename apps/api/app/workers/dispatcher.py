"""Background worker: consume Redis jobs and execute connector dispatches."""

from __future__ import annotations

import logging
import sys
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.integrations.slack import slack_incoming_webhook_body
from app.services.queue import Job, RedisJobQueue

logger = logging.getLogger(__name__)

POLL_SECONDS = 2


def _deliver_slack(webhook_url: str, dispatch_payload: dict[str, Any]) -> None:
    body = slack_incoming_webhook_body(dispatch_payload)
    with httpx.Client(timeout=30.0) as client:
        response = client.post(webhook_url, json=body)
        response.raise_for_status()


def process_connector_job(job: Job, settings: Settings) -> None:
    if job.job_type != "connector_dispatch":
        raise ValueError(f"Unsupported job_type {job.job_type!r}")

    payload = job.payload
    connector = payload.get("connector")
    dispatch_payload = payload.get("dispatch_payload")

    if not isinstance(dispatch_payload, dict):
        raise ValueError("dispatch_payload must be a dict")

    if connector == "slack":
        _deliver_slack(settings.slack_webhook_url, dispatch_payload)
        return

    raise ValueError(f"Unsupported connector {connector!r}")


def run_loop(queue: RedisJobQueue | None, settings: Settings) -> None:
    if queue is None:
        logger.error("Redis job queue unavailable; exiting dispatcher.")
        sys.exit(1)

    logger.info("Dispatcher started (poll every %ss)", POLL_SECONDS)
    while True:
        job = queue.dequeue()
        if job is None:
            time.sleep(POLL_SECONDS)
            continue

        try:
            process_connector_job(job, settings)
            queue.mark_completed(job.job_id)
            logger.info("Job %s completed (%s)", job.job_id, job.job_type)
        except Exception as exc:
            logger.exception("Job %s failed: %s", job.job_id, exc)
            queue.mark_failed(job.job_id, str(exc))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = get_settings()
    try:
        queue = RedisJobQueue(redis_url=settings.redis_url)
        if not queue.health_check():
            logger.error("Redis ping failed for %s", settings.redis_url)
            sys.exit(1)
    except Exception as exc:
        logger.error("Could not connect to Redis: %s", exc)
        sys.exit(1)

    run_loop(queue, settings)


if __name__ == "__main__":
    main()
