from __future__ import annotations

from typing import Any

from app.integrations.base import BaseConnector, ConnectorDispatch


def slack_incoming_webhook_body(dispatch_payload: dict[str, Any]) -> dict[str, Any]:
    """JSON body for Slack Incoming Webhooks (message-centric payloads)."""
    wf = dispatch_payload.get("workflow_id", "")
    aid = dispatch_payload.get("approval_id", "")
    role = dispatch_payload.get("role", "")
    text = dispatch_payload.get("request_text", "")
    cost = dispatch_payload.get("estimated_cost")
    cost_line = ""
    if cost is not None:
        try:
            cost_line = f"*Estimated cost:* ${float(cost):,.2f}\n"
        except (TypeError, ValueError):
            cost_line = f"*Estimated cost:* {cost}\n"
    return {
        "text": (
            f"Approval needed ({role})\n"
            f"*Workflow:* `{wf}`  •  *Approval:* `{aid}`\n"
            f"{cost_line}"
            f"*Request:* {text}"
        )
    }


class SlackApprovalConnector(BaseConnector):
    name = "slack"

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def authenticate(self) -> bool:
        return self.webhook_url.startswith("http")

    def validate(self, payload: dict[str, Any]) -> bool:
        return "workflow_id" in payload and "approval_id" in payload

    def execute(self, payload: dict[str, Any], idempotency_key: str) -> ConnectorDispatch:
        return ConnectorDispatch(
            connector=self.name,
            status="queued",
            payload={
                "webhook_url": self.webhook_url,
                "message": payload,
            },
            idempotency_key=idempotency_key,
        )
