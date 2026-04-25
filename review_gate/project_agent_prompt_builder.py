from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(slots=True)
class ProjectAgentPromptPackage:
    system_prompt: str
    user_prompt: str
    output_contract: dict[str, Any]


class ProjectAgentPromptBuilder:
    _QUESTION_MIX_RULES = (
        "Include project-grounded questions tied to the current codebase and migration work.",
        "Include interview-style fundamentals that an interviewer could reasonably ask about the current implementation.",
        "Include mid-level design and implementation questions about boundaries, persistence, migration, and trade-offs.",
        "Include higher-level trade-off or failure-mode questions that test reasoning under change or risk.",
        "Do not generate a question set made only of abstract architecture prompts.",
        "Do not let all questions collapse into the same difficulty or the same category when max_questions allows variety.",
        "Use concrete module, persistence, migration, id-boundary, or failure-mode references whenever the current project context supports them.",
    )

    def build(self, request: Mapping[str, Any]) -> ProjectAgentPromptPackage:
        project_id = str(request["project_id"])
        stage_id = str(request["stage_id"])
        stage_label = str(request.get("stage_label", ""))
        stage_goal = str(request.get("stage_goal", ""))
        stage_summary = str(request.get("stage_summary", ""))
        learning_goal = str(request.get("learning_goal", ""))
        target_user_level = str(request.get("target_user_level", ""))
        question_mix = self._coerce_str_list(request.get("question_mix"))
        preferred_question_style = str(request.get("preferred_question_style", ""))
        max_questions = int(request.get("max_questions", 3))
        boundary_focus = self._coerce_str_list(request.get("boundary_focus"))
        current_decisions = self._coerce_str_list(request.get("current_decisions"))
        key_logic_points = self._coerce_str_list(request.get("key_logic_points"))
        known_weak_points = self._coerce_str_list(request.get("known_weak_points"))

        system_prompt = "\n".join(
            [
                "You are the Project Agent for question generation.",
                "Generate a mixed question set that helps both project progress and interview readiness.",
                *self._QUESTION_MIX_RULES,
                "Return only structured question data that matches the requested output contract.",
            ]
        )

        user_prompt_lines = [
            f"Project id: {project_id}",
            f"Stage id: {stage_id}",
            f"Stage label: {stage_label}",
            f"Stage goal: {stage_goal}",
            f"Stage summary: {stage_summary}",
            f"Learning goal: {learning_goal}",
            f"Target user level: {target_user_level}",
            f"Question mix: {', '.join(question_mix) if question_mix else '(none)'}",
            f"Preferred question style: {preferred_question_style}",
            f"Max questions: {max_questions}",
            f"Boundary focus: {', '.join(boundary_focus) if boundary_focus else '(none)'}",
            f"Current decisions: {', '.join(current_decisions) if current_decisions else '(none)'}",
            f"Key logic points: {', '.join(key_logic_points) if key_logic_points else '(none)'}",
            f"Known weak points: {', '.join(known_weak_points) if known_weak_points else '(none)'}",
            "Question set requirements:",
            "- Include at least one project-grounded question.",
            "- Include at least one interview-style fundamentals question.",
            "- Include at least one mid-level design or implementation question when max_questions >= 3.",
            "- Include at least one higher-level trade-off or failure-mode question when max_questions >= 4.",
            "- Use at least one concrete module name, persistence concern, migration boundary, or compatibility risk from the current project context when possible.",
            "- Make at least one question something a real backend/system-design interviewer could directly ask in an interview.",
            "- Prefer direct, answerable questions over vague architecture discussion.",
            "- Include at least one question that exposes a likely user misconception or wrong mental model.",
            "- Avoid letting every question sit at the same layer of abstraction.",
            "- Avoid making the entire set abstract.",
            "Bad output examples to avoid:",
            "- A set where every question is a generic architecture question.",
            "- A set where every question is effectively the same 'explain the design' prompt.",
            "- A set with no fundamentals question and no migration/failure-mode question.",
        ]

        output_contract = {
            "questions": [
                {
                    "id": "q-1",
                    "prompt": "string",
                    "type": "open",
                    "intent": "string",
                    "difficulty": "basic|intermediate|advanced",
                }
            ]
        }

        return ProjectAgentPromptPackage(
            system_prompt=system_prompt,
            user_prompt="\n".join(user_prompt_lines),
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
