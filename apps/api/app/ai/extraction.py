from __future__ import annotations

import re

from app.domain.models import ExtractedRequest


class RequestExtractionAgent:
    PRICE_BOOK: dict[str, tuple[str, float]] = {
        "macbook": ("hardware", 1800.0),
        "laptop": ("hardware", 1400.0),
        "monitor": ("hardware", 350.0),
        "license": ("software", 120.0),
        "seat": ("software", 80.0),
        "vendor": ("services", 2500.0),
    }

    def extract(self, request_text: str) -> ExtractedRequest:
        normalized = request_text.lower()
        quantity = self._extract_quantity(normalized)
        item_name, category, unit_cost = self._resolve_item(normalized)
        urgency = (
            "high"
            if any(word in normalized for word in ("urgent", "asap", "immediately"))
            else "normal"
        )
        department = self._resolve_department(normalized)
        estimated_cost = quantity * unit_cost

        return ExtractedRequest(
            category=category,
            item_name=item_name,
            quantity=quantity,
            urgency=urgency,
            estimated_unit_cost=unit_cost,
            estimated_cost=estimated_cost,
            department=department,
        )

    def _extract_quantity(self, request_text: str) -> int:
        match = re.search(r"\b(\d+)\b", request_text)
        return int(match.group(1)) if match else 1

    def _resolve_item(self, request_text: str) -> tuple[str, str, float]:
        for keyword, (category, unit_cost) in self.PRICE_BOOK.items():
            if keyword in request_text:
                return keyword, category, unit_cost
        return "general_request", "operations", 500.0

    def _resolve_department(self, request_text: str) -> str:
        department_map = {
            "engineering": "engineering",
            "finance": "finance",
            "sales": "sales",
            "marketing": "marketing",
            "security": "security",
        }
        for keyword, department in department_map.items():
            if keyword in request_text:
                return department
        return "operations"
