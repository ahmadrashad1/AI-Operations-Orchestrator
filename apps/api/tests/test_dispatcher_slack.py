"""Connector dispatcher delivery tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from app.core.config import Settings
from app.services.queue import Job, JobStatus
from app.workers.dispatcher import process_connector_job


def test_process_slack_connector_posts_webhook(monkeypatch) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post = MagicMock(return_value=mock_response)

    monkeypatch.setattr(httpx, "Client", MagicMock(return_value=mock_client))

    settings = Settings(
        slack_webhook_url="https://hooks.slack.com/services/TEST/WEBHOOK",
        jwt_secret_key="x" * 32,
    )

    job = Job(
        job_id="j1",
        job_type="connector_dispatch",
        payload={
            "connector": "slack",
            "workflow_id": "w1",
            "approval_id": "a1",
            "dispatch_payload": {
                "workflow_id": "w1",
                "approval_id": "a1",
                "role": "Manager",
                "request_text": "Need laptops",
                "estimated_cost": 1234.5,
            },
        },
        status=JobStatus.PROCESSING,
    )

    process_connector_job(job, settings)

    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == settings.slack_webhook_url
    assert "json" in kwargs
    assert "Need laptops" in kwargs["json"]["text"]
