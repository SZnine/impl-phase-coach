from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class EvaluatorLiveQualitySample:
    sample_id: str
    question_context: str
    answer_text: str
    expected_verdicts: set[str]
    score_band: tuple[float, float]
    required_gap_keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvaluatorLiveQualitySmokeResult:
    sample: EvaluatorLiveQualitySample
    normalized: dict[str, Any]
    issues: list[str] = field(default_factory=list)


def default_evaluator_live_quality_samples() -> list[EvaluatorLiveQualitySample]:
    return [
        EvaluatorLiveQualitySample(
            sample_id="strong_concrete",
            question_context="Explain the current-stage boundary and concrete implementation risks in evaluator-agent integration.",
            answer_text=(
                "The current-stage boundary is evaluator-agent LLM assessment integration only. "
                "Graph and Maintenance are explicitly out of scope. "
                "The key risk is letting provider-shaped output reach checkpoint writes before normalization, "
                "because that would destabilize the Evaluation -> Facts contract. "
                "Another concrete risk is accepting malformed SSE chunks without regression coverage. "
                "The client should own provider transport, the normalizer should own shape recovery, "
                "and the service should stay orchestration-only."
            ),
            expected_verdicts={"strong", "partial"},
            score_band=(0.7, 1.0),
            required_gap_keywords=(),
        ),
        EvaluatorLiveQualitySample(
            sample_id="abstract_handwavy",
            question_context="Explain the current-stage boundary and concrete implementation risks in evaluator-agent integration.",
            answer_text=(
                "We should design the system carefully and keep boundaries clean. "
                "Good architecture matters and we should think about future extensibility, maintainability, and modularity."
            ),
            expected_verdicts={"weak"},
            score_band=(0.0, 0.45),
            required_gap_keywords=("boundary", "normalization"),
        ),
        EvaluatorLiveQualitySample(
            sample_id="low_level_partial",
            question_context="Explain the current-stage boundary and concrete implementation risks in evaluator-agent integration.",
            answer_text=(
                "I switched to requests with stream=True and added some tests, but I did not clearly separate "
                "provider contract handling from service logic, and I still have not added a malformed-chunk regression."
            ),
            expected_verdicts={"partial", "weak"},
            score_band=(0.35, 0.85),
            required_gap_keywords=("boundary", "normalization", "sse"),
        ),
    ]


def classify_quality_issues(result: EvaluatorLiveQualitySmokeResult) -> list[str]:
    issues: list[str] = []
    normalized = result.normalized
    assessment = normalized.get("assessment", {})
    verdict = str(assessment.get("verdict", "")).strip()
    score_total = _coerce_float(assessment.get("score_total"))
    core_gaps = _coerce_text_list(assessment.get("core_gaps"))
    misconceptions = _coerce_text_list(assessment.get("misconceptions"))
    evidence = _coerce_text_list(assessment.get("evidence"))

    if verdict not in result.sample.expected_verdicts:
        issues.append("unexpected_verdict")

    low, high = result.sample.score_band
    if score_total < low or score_total > high:
        issues.append("score_out_of_expected_band")

    haystack = " ".join([*core_gaps, *misconceptions]).lower()
    missing_keywords = [
        keyword for keyword in result.sample.required_gap_keywords if keyword.lower() not in haystack
    ]
    if missing_keywords:
        issues.append("missing_required_gap_keywords")

    if not evidence:
        issues.append("empty_evidence")

    return issues


def run_evaluator_live_quality_smoke(
    *,
    samples: list[EvaluatorLiveQualitySample],
    builder: Any,
    client: Any,
    normalizer: Any,
    project_context: str,
    stage_context: str,
    current_decisions: list[str],
    boundary_focus: list[str],
) -> list[EvaluatorLiveQualitySmokeResult]:
    results: list[EvaluatorLiveQualitySmokeResult] = []

    for sample in samples:
        request = {
            "request_id": sample.sample_id,
            "project_context": project_context,
            "stage_context": stage_context,
            "question_context": sample.question_context,
            "answer_text": sample.answer_text,
            "current_decisions": current_decisions,
            "boundary_focus": boundary_focus,
        }
        prompt = builder.build(request)
        raw_result = client.assess(
            {
                "request_id": sample.sample_id,
                "messages": [
                    {"role": "system", "content": prompt.system_prompt},
                    {"role": "user", "content": prompt.user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "output_contract": prompt.output_contract,
            }
        )
        normalized = normalizer.normalize(request=request, raw_result=raw_result)
        result = EvaluatorLiveQualitySmokeResult(
            sample=sample,
            normalized=normalized,
            issues=[],
        )
        result = EvaluatorLiveQualitySmokeResult(
            sample=result.sample,
            normalized=result.normalized,
            issues=classify_quality_issues(result),
        )
        results.append(result)

    return results


def format_live_quality_report(results: list[EvaluatorLiveQualitySmokeResult]) -> str:
    lines: list[str] = []
    for result in results:
        assessment = result.normalized.get("assessment", {})
        verdict = str(assessment.get("verdict", "")).strip()
        score_total = _coerce_float(assessment.get("score_total"))
        confidence = _coerce_float(result.normalized.get("confidence"))
        issues = ",".join(result.issues) if result.issues else "none"
        lines.append(
            f"{result.sample.sample_id}: verdict={verdict} score={score_total:.2f} confidence={confidence:.2f} issues={issues}"
        )
    return "\n".join(lines)


def _coerce_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
