from __future__ import annotations

import json
from typing import Any, Mapping


class EvaluatorAgentResponseNormalizer:
    _DIMENSION_KEYS = (
        "correctness",
        "reasoning",
        "decision_awareness",
        "boundary_awareness",
        "stability",
    )
    _DIMENSION_ALIASES = {
        "current_stage_boundary_alignment": "boundary_awareness",
        "concrete_implementation_risk_identification": "decision_awareness",
        "implementation_grounding": "correctness",
        "context_fit": "reasoning",
        "completeness": "stability",
    }
    _VERDICT_ALIASES = {
        "pass": "strong",
        "passed": "strong",
        "strong": "strong",
        "strong_accept": "strong",
        "pass_with_minor_gaps": "strong",
        "satisfactory": "strong",
        "partial": "partial",
        "partially_satisfactory": "partial",
        "partially_sufficient": "partial",
        "continue_probing": "partial",
        "weak": "weak",
        "reject": "weak",
        "fail": "weak",
        "failed": "weak",
        "insufficient": "weak",
        "does_not_meet_request": "weak",
        "unsatisfactory": "weak",
        "redirect_to_learning": "weak",
    }

    def normalize(self, *, request: Mapping[str, Any], raw_result: Mapping[str, Any]) -> dict[str, Any]:
        raw_content = str(raw_result.get("raw_content", "")).strip()
        if not raw_content:
            raise ValueError("Evaluator Agent raw content is empty")

        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError("Evaluator Agent raw content is not valid JSON") from exc

        assessment_payload = payload.get("assessment")
        if not isinstance(assessment_payload, Mapping) and self._looks_like_flat_assessment_payload(payload):
            assessment_payload = payload
        if not isinstance(assessment_payload, Mapping):
            raise ValueError("Evaluator Agent response missing assessment")

        verdict = self._normalize_verdict(
            assessment_payload.get("verdict", payload.get("verdict"))
        )
        if not verdict:
            raise ValueError("Evaluator Agent response missing assessment verdict")

        return {
            "request_id": str(raw_result.get("request_id") or request["request_id"]),
            "assessment": {
                "score_total": self._normalize_score_total(
                    assessment_payload.get("score_total", payload.get("score_total")),
                    assessment_payload.get("dimension_scores", payload.get("dimension_scores")),
                ),
                "dimension_scores": self._normalize_dimension_scores(assessment_payload.get("dimension_scores")),
                "verdict": verdict,
                "core_gaps": self._normalize_core_gaps(assessment_payload, payload),
                "misconceptions": self._normalize_text_collection(
                    assessment_payload.get("misconceptions"),
                    payload.get("misconceptions"),
                ),
                "evidence": self._normalize_text_collection(
                    assessment_payload.get("evidence"),
                    payload.get("evidence"),
                ),
                "support_basis_tags": self._coerce_dict_list(assessment_payload.get("support_basis_tags")),
            },
            "recommended_action": self._normalize_recommended_action(
                payload.get("recommended_action", payload.get("action_recommendation")),
                verdict,
            ),
            "recommended_follow_up_questions": self._coerce_text_list(payload.get("recommended_follow_up_questions")),
            "learning_recommendations": self._coerce_text_list(payload.get("learning_recommendations")),
            "warnings": self._coerce_text_list(payload.get("warnings")),
            "confidence": self._normalize_confidence(
                payload.get("confidence", raw_result.get("confidence")),
                assessment_payload.get("score_total", payload.get("score_total")),
                assessment_payload.get("dimension_scores", payload.get("dimension_scores")),
            ),
        }

    def _normalize_dimension_scores(self, value: Any) -> dict[str, int]:
        payload = value if isinstance(value, Mapping) else {}
        normalized = {key: 0 for key in self._DIMENSION_KEYS}
        use_ratio_scale = self._should_treat_dimension_scores_as_ratio(payload)

        for key in self._DIMENSION_KEYS:
            if key in payload:
                normalized[key] = self._coerce_dimension_value(payload.get(key), use_ratio_scale=use_ratio_scale)

        for alias, canonical in self._DIMENSION_ALIASES.items():
            if normalized[canonical]:
                continue
            if alias in payload:
                normalized[canonical] = self._coerce_dimension_value(
                    payload.get(alias),
                    use_ratio_scale=use_ratio_scale,
                )

        return normalized

    def _normalize_core_gaps(self, assessment_payload: Mapping[str, Any], payload: Mapping[str, Any]) -> list[str]:
        direct = self._normalize_text_collection(
            assessment_payload.get("core_gaps"),
            payload.get("core_gaps"),
        )
        grounded = self._normalize_text_collection(
            assessment_payload.get("grounded_issues"),
            payload.get("grounded_issues"),
        )
        return self._dedupe_preserve_order([*direct, *grounded])

    def _normalize_text_collection(self, primary: Any, fallback: Any) -> list[str]:
        direct = self._coerce_text_list(primary)
        if direct:
            return direct
        return self._coerce_text_list(fallback)

    @staticmethod
    def _coerce_text_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            items = value
        else:
            items = [value]

        normalized: list[str] = []
        for item in items:
            if isinstance(item, Mapping):
                direct_text = EvaluatorAgentResponseNormalizer._extract_text(item)
                if direct_text:
                    normalized.append(direct_text)
                    continue
                nested_values = [
                    candidate
                    for candidate in item.values()
                    if isinstance(candidate, (list, tuple))
                ]
                for candidate in nested_values:
                    normalized.extend(EvaluatorAgentResponseNormalizer._coerce_text_list(candidate))
                continue
            text = EvaluatorAgentResponseNormalizer._extract_text(item)
            if text:
                normalized.append(text)
        return normalized

    @staticmethod
    def _extract_text(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, Mapping):
            for key in (
                "summary",
                "text",
                "quote",
                "title",
                "message",
                "gap",
                "item",
                "why_it_matters",
                "expected_reference",
                "assessment",
            ):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            return ""
        text = str(value).strip()
        return text if text and text != "None" else ""

    @staticmethod
    def _coerce_dict_list(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, Mapping)]
        return []

    @staticmethod
    def _coerce_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @classmethod
    def _coerce_dimension_value(cls, value: Any, *, use_ratio_scale: bool) -> int:
        numeric = cls._coerce_float(value, 0.0)
        if use_ratio_scale:
            return max(0, min(5, int(round(numeric * 5))))
        return max(0, min(5, int(round(numeric))))

    @classmethod
    def _should_treat_dimension_scores_as_ratio(cls, payload: Mapping[str, Any]) -> bool:
        numeric_values: list[float] = []
        for raw in payload.values():
            try:
                numeric_values.append(float(raw))
            except (TypeError, ValueError):
                continue
        return bool(numeric_values) and max(numeric_values) <= 1.0

    @classmethod
    def _normalize_verdict(cls, value: Any) -> str:
        verdict = str(value or "").strip().lower()
        return cls._VERDICT_ALIASES.get(verdict, verdict)

    @classmethod
    def _normalize_score_total(cls, score_total: Any, dimension_scores: Any) -> float:
        numeric = cls._coerce_float(score_total, -1.0)
        if numeric >= 0.0:
            if numeric > 1.0:
                return max(0.0, min(1.0, numeric / 5.0))
            return numeric

        if not isinstance(dimension_scores, Mapping):
            return 0.0

        use_ratio_scale = cls._should_treat_dimension_scores_as_ratio(dimension_scores)
        values = [
            cls._coerce_dimension_value(value, use_ratio_scale=use_ratio_scale)
            for value in dimension_scores.values()
        ]
        if not values:
            return 0.0
        return round(sum(values) / (len(values) * 5.0), 4)

    @staticmethod
    def _normalize_recommended_action(value: Any, verdict: str) -> str:
        if isinstance(value, (list, tuple)):
            texts = EvaluatorAgentResponseNormalizer._coerce_text_list(value)
            if texts:
                return texts[0]
        text = str(value or "").strip()
        if text:
            return text
        if verdict == "weak":
            return "redirect_to_learning"
        return "continue_answering"

    @classmethod
    def _normalize_confidence(cls, confidence: Any, score_total: Any, dimension_scores: Any) -> float:
        numeric = cls._coerce_float(confidence, -1.0)
        if numeric >= 0.0:
            if numeric > 1.0:
                return max(0.0, min(1.0, numeric / 5.0))
            return numeric
        return cls._normalize_score_total(score_total, dimension_scores)

    @staticmethod
    def _looks_like_flat_assessment_payload(payload: Mapping[str, Any]) -> bool:
        return any(
            key in payload
            for key in ("verdict", "dimension_scores", "core_gaps", "misconceptions", "evidence")
        )

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered
