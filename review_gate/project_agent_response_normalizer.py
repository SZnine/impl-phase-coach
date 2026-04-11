from __future__ import annotations

import json
import re
from typing import Any, Mapping


class ProjectAgentResponseNormalizer:
    _CANONICAL_QUESTION_ID_PATTERN = re.compile(r"^q-\d+$")
    _DIFFICULTY_TO_LEVEL = {
        "basic": "core",
        "intermediate": "why",
        "advanced": "abstract",
    }

    _LEVEL_DEFAULT_INTENT = {
        "core": "Check project-grounded understanding.",
        "why": "Check reasoning about implementation trade-offs.",
        "abstract": "Check higher-level transfer and trade-off reasoning.",
    }

    def normalize(self, *, request: Mapping[str, Any], raw_result: Mapping[str, Any]) -> dict[str, Any]:
        raw_content = str(raw_result.get("raw_content", "")).strip()
        if not raw_content:
            raise ValueError("Project Agent raw content is empty")

        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError("Project Agent raw content is not valid JSON") from exc

        questions = payload.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("Project Agent response missing questions")

        normalized_questions = [
            self._normalize_question(
                item=item,
                index=index,
                request=request,
            )
            for index, item in enumerate(questions, start=1)
        ]

        return {
            "request_id": str(raw_result.get("request_id") or request["request_id"]),
            "questions": normalized_questions,
            "generation_summary": str(
                payload.get("generation_summary")
                or raw_result.get("generation_summary")
                or f"Generated {len(normalized_questions)} structured questions."
            ),
            "coverage_notes": self._coerce_str_list(payload.get("coverage_notes") or raw_result.get("coverage_notes")),
            "warnings": self._coerce_str_list(payload.get("warnings") or raw_result.get("warnings")),
            "confidence": float(payload.get("confidence", raw_result.get("confidence", 0.7))),
        }

    def _normalize_question(
        self,
        *,
        item: Any,
        index: int,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(item, Mapping):
            raise ValueError("Project Agent question item must be an object")

        prompt = str(item.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("Project Agent question item missing prompt")

        level = self._resolve_question_level(item)
        question_id = self._normalize_question_id(item=item, index=index)
        intent = str(item.get("intent") or self._LEVEL_DEFAULT_INTENT[level]).strip()

        expected_signals = self._coerce_str_list(item.get("expected_signals"))
        if not expected_signals:
            expected_signals = self._coerce_str_list(request.get("current_decisions")) or self._coerce_str_list(
                request.get("boundary_focus")
            )

        source_context = self._coerce_str_list(item.get("source_context"))
        if not source_context:
            source_context = self._coerce_str_list(request.get("source_refs"))

        return {
            "question_id": question_id,
            "question_level": level,
            "prompt": prompt,
            "intent": intent,
            "expected_signals": expected_signals,
            "source_context": source_context,
        }

    def _resolve_question_level(self, item: Mapping[str, Any]) -> str:
        explicit_level = str(item.get("question_level", "")).strip().lower()
        if explicit_level in {"core", "why", "abstract"}:
            return explicit_level

        difficulty = str(item.get("difficulty", "")).strip().lower()
        if difficulty in self._DIFFICULTY_TO_LEVEL:
            return self._DIFFICULTY_TO_LEVEL[difficulty]

        return "core"

    def _normalize_question_id(self, *, item: Mapping[str, Any], index: int) -> str:
        raw_question_id = str(item.get("question_id") or item.get("id") or "").strip().lower()
        if self._CANONICAL_QUESTION_ID_PATTERN.fullmatch(raw_question_id):
            return raw_question_id
        return f"q-{index}"

    @staticmethod
    def _coerce_str_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []
