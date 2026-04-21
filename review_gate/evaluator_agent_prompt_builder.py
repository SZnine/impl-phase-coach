from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(slots=True)
class EvaluatorAgentPromptPackage:
    system_prompt: str
    user_prompt: str
    output_contract: dict[str, Any]


class EvaluatorAgentPromptBuilder:
    def build(self, request: Mapping[str, Any]) -> EvaluatorAgentPromptPackage:
        request_id = str(request["request_id"])
        project_context = str(request.get("project_context", ""))
        stage_context = str(request.get("stage_context", ""))
        question_context = str(request.get("question_context", ""))
        answer_text = str(request.get("answer_text", ""))
        current_decisions = self._coerce_str_list(request.get("current_decisions"))
        boundary_focus = self._coerce_str_list(request.get("boundary_focus"))

        system_prompt = "\n".join(
            [
                "You are the Evaluator Agent.",
                "Assess the answer against the request context and current implementation boundaries.",
                "Favor concrete, grounded concerns over abstract architecture critique when they are supported by the context.",
                "You may judge lower-level implementation issues such as library/API misuse, method misuse, test gaps, boundary confusion, and migration/compatibility risk.",
                "Do not return a freeform essay without structured assessment fields.",
                "Return one JSON object only. Do not add markdown fences or explanatory prose.",
                "Keep verdict and dimension_scores inside the nested assessment object, not at the top level.",
                "Use only the canonical dimension keys: correctness, reasoning, decision_awareness, boundary_awareness, stability.",
                "Core gaps, misconceptions, and evidence should be arrays of strings whenever possible.",
                "When a core gap can be supported by a foundation, concept, or method, return assessment.support_basis_tags.",
                "Each support basis tag must connect a source_label to a target_label; target_label must match one item from assessment.core_gaps.",
                "Use only these support basis keys when applicable: state_modeling, boundary_awareness, decision_awareness.",
                "Return only structured output that matches the requested output contract.",
            ]
        )

        user_prompt = "\n".join(
            [
                f"Request id: {request_id}",
                f"Project context: {project_context}",
                f"Stage context: {stage_context}",
                f"Question context: {question_context}",
                f"Answer text: {answer_text}",
                f"Current decisions: {', '.join(current_decisions) if current_decisions else '(none)'}",
                f"Boundary focus: {', '.join(boundary_focus) if boundary_focus else '(none)'}",
                "Evaluation requirements:",
                "- Return a verdict.",
                "- Provide dimension scores for the answer.",
                "- Identify core gaps.",
                "- Identify misconceptions.",
                "- Cite evidence from the answer and context.",
                "- End with an action recommendation.",
                "- Put verdict inside assessment.verdict.",
                "- Put dimension scores inside assessment.dimension_scores with the canonical keys only.",
                "- Put graph-support provenance inside assessment.support_basis_tags when a stable foundation, concept, or method can support a core gap.",
                "- For each support_basis_tags item include basis_key, source_label, source_node_type, target_label, and target_node_type.",
                "- Make support_basis_tags.target_label exactly match one string from assessment.core_gaps.",
                "- Do not invent alternative keys such as current_stage_boundary_alignment or implementation_grounding.",
            ]
        )

        output_contract = {
            "request_id": "string",
            "assessment": {
                "score_total": "0-1",
                "dimension_scores": {
                    "correctness": "0-5",
                    "reasoning": "0-5",
                    "decision_awareness": "0-5",
                    "boundary_awareness": "0-5",
                    "stability": "0-5",
                },
                "verdict": "pass|continue_probing|redirect_to_learning",
                "core_gaps": ["string"],
                "misconceptions": ["string"],
                "evidence": ["string"],
                "support_basis_tags": [
                    {
                        "basis_key": "state_modeling|boundary_awareness|decision_awareness",
                        "source_label": "string",
                        "source_node_type": "foundation|concept|method",
                        "target_label": "string matching one core_gaps item",
                        "target_node_type": "concept|method|decision",
                    }
                ],
            },
            "recommended_action": "string",
            "recommended_follow_up_questions": ["string"],
            "learning_recommendations": ["string"],
            "warnings": ["string"],
            "confidence": "0-1",
        }

        return EvaluatorAgentPromptPackage(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_contract=output_contract,
        )

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
