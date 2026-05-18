from app.core.config import Settings
from app.domain.models import ExtractedRequest, PolicyEvaluation


class PolicyEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, extraction: ExtractedRequest) -> PolicyEvaluation:
        reasons: list[str] = []
        needs_manager_approval = extraction.estimated_cost >= self.settings.manager_approval_threshold
        needs_finance_approval = extraction.estimated_cost >= self.settings.finance_approval_threshold
        requires_human_review = extraction.category == "services" or extraction.urgency == "high"

        if needs_manager_approval:
            reasons.append(
                f"Estimated cost {extraction.estimated_cost:.2f} meets or exceeds the manager threshold."
            )
        if needs_finance_approval:
            reasons.append(
                f"Estimated cost {extraction.estimated_cost:.2f} meets or exceeds the finance threshold."
            )
        if requires_human_review:
            reasons.append("Urgent or service-oriented requests require an explicit human checkpoint.")

        return PolicyEvaluation(
            needs_manager_approval=needs_manager_approval,
            needs_finance_approval=needs_finance_approval,
            requires_human_review=requires_human_review,
            reasons=reasons,
        )

