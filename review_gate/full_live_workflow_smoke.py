from __future__ import annotations

from typing import Any


def resolve_first_generated_transport_question_id(
    *,
    generation_response: dict[str, Any],
    question_set_id: str,
) -> str:
    questions = generation_response.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("generation_response must contain at least one question")
    first_question = questions[0]
    if not isinstance(first_question, dict):
        raise ValueError("generation_response question item must be an object")
    raw_question_id = str(first_question.get("question_id") or first_question.get("id") or "").strip()
    if not raw_question_id:
        raise ValueError("generation_response first question missing question_id")
    if raw_question_id.startswith(f"{question_set_id}-"):
        return raw_question_id
    return f"{question_set_id}-{raw_question_id}"


def classify_full_live_workflow_smoke_issues(
    *,
    generation_response: dict[str, Any],
    submit_response: dict[str, Any],
    assessment_review: dict[str, Any],
    question_set_view: dict[str, Any],
    graph_revision: dict[str, Any],
    graph_main: dict[str, Any],
    strict: bool,
) -> list[str]:
    issues: list[str] = []
    questions = generation_response.get("questions")
    if not isinstance(questions, list) or not questions:
        issues.append("missing_generated_questions")
    elif not _has_readable_generated_question_prompt(questions):
        issues.append("missing_readable_generated_question_prompt")
    if submit_response.get("success") is not True:
        issues.append("submit_failed")
    refresh_targets = submit_response.get("refresh_targets")
    if isinstance(refresh_targets, list) and "question_set" not in refresh_targets:
        issues.append("missing_question_set_refresh_target")
    if assessment_review.get("has_assessment") is not True:
        issues.append("missing_assessment_review")
    elif not _is_readable_text(assessment_review.get("review_summary")):
        issues.append("missing_readable_assessment_review_summary")
    if _answered_question_count(question_set_view) < 1:
        issues.append("missing_answered_question_progress")
    if graph_revision.get("has_active_revision") is not True:
        issues.append("missing_active_graph_revision")

    revision = graph_revision.get("revision")
    if not isinstance(revision, dict) or _coerce_int(revision.get("node_count")) < 1:
        issues.append("missing_graph_nodes")
    if not graph_main.get("nodes"):
        issues.append("missing_graph_main_nodes")
    if graph_main.get("selected_cluster") is None:
        issues.append("missing_selected_cluster")

    relation_count = _coerce_int(revision.get("relation_count")) if isinstance(revision, dict) else 0
    if strict and relation_count < 1:
        issues.append("missing_relation_in_strict_mode")
    return issues


def build_full_live_workflow_smoke_artifact(
    *,
    generation_response: dict[str, Any],
    selected_question_id: str,
    submit_response: dict[str, Any],
    assessment_review: dict[str, Any],
    question_set_view: dict[str, Any],
    graph_revision: dict[str, Any],
    graph_main: dict[str, Any],
    issues: list[str],
    db_path: str,
    project_model: str,
    evaluator_model: str,
) -> dict[str, Any]:
    return {
        "project_model": project_model,
        "evaluator_model": evaluator_model,
        "db_path": db_path,
        "selected_question_id": selected_question_id,
        "issues": list(issues),
        "generation_response": generation_response,
        "submit_response": submit_response,
        "assessment_review": assessment_review,
        "question_set_view": question_set_view,
        "graph_revision": graph_revision,
        "graph_main": graph_main,
    }


def format_full_live_workflow_smoke_report(artifact: dict[str, Any]) -> str:
    generation_response = artifact.get("generation_response", {})
    questions = generation_response.get("questions", []) if isinstance(generation_response, dict) else []
    generated_question_count = len(questions) if isinstance(questions, list) else 0
    graph_revision = artifact.get("graph_revision", {})
    revision = graph_revision.get("revision", {}) if isinstance(graph_revision, dict) else {}
    graph_main = artifact.get("graph_main", {})
    selected_cluster = graph_main.get("selected_cluster", {}) if isinstance(graph_main, dict) else {}
    assessment_review = artifact.get("assessment_review", {})
    question_set_view = artifact.get("question_set_view", {})
    knowledge_updates = (
        assessment_review.get("knowledge_updates", [])
        if isinstance(assessment_review, dict)
        else []
    )
    issues = artifact.get("issues") or []
    lines = [
        "# Full Live Workflow Smoke Report",
        "",
        f"project_model: {artifact.get('project_model', '')}",
        f"evaluator_model: {artifact.get('evaluator_model', '')}",
        f"db_path: {artifact.get('db_path', '')}",
        f"issues: {', '.join(issues) if issues else 'none'}",
        "",
        "## Generation",
        f"generated_question_count: {generated_question_count}",
        f"selected_question_id: {artifact.get('selected_question_id', '')}",
        *_format_generated_question_lines(questions),
        "",
        "## Question Set Progress",
        f"answered_question_count: {_answered_question_count(question_set_view)}",
        f"current_question_id: {question_set_view.get('current_question_id', '') if isinstance(question_set_view, dict) else ''}",
        "",
        "## Assessment Review",
        f"review_title: {assessment_review.get('review_title', '') if isinstance(assessment_review, dict) else ''}",
        f"review_summary: {assessment_review.get('review_summary', '') if isinstance(assessment_review, dict) else ''}",
        f"verdict_label: {assessment_review.get('verdict_label', '') if isinstance(assessment_review, dict) else ''}",
        f"knowledge_update_count: {len(knowledge_updates) if isinstance(knowledge_updates, list) else 0}",
        "",
        "## Graph Revision",
        f"node_count: {revision.get('node_count', 0)}",
        f"relation_count: {revision.get('relation_count', 0)}",
        "",
        "## Selected Cluster",
        f"center_node_id: {selected_cluster.get('center_node_id', '')}",
        f"neighbor_node_ids: {selected_cluster.get('neighbor_node_ids', [])}",
        f"focus_reason_codes: {selected_cluster.get('focus_reason_codes', [])}",
    ]
    return "\n".join(lines)


def _format_generated_question_lines(questions: object) -> list[str]:
    if not isinstance(questions, list) or not questions:
        return []

    lines = ["", "generated_questions:"]
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            continue
        question_id = str(question.get("question_id") or question.get("id") or f"q-{index}")
        question_level = str(question.get("question_level") or question.get("difficulty") or "unknown")
        prompt = str(question.get("prompt") or "").strip()
        intent = str(question.get("intent") or "").strip()
        lines.append(f"- {question_id} [{question_level}]: {prompt}")
        if intent:
            lines.append(f"  intent: {intent}")
    return lines


def _coerce_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _has_readable_generated_question_prompt(questions: list[object]) -> bool:
    return any(
        isinstance(question, dict) and _is_readable_text(question.get("prompt"))
        for question in questions
    )


def _is_readable_text(value: object) -> bool:
    return isinstance(value, str) and len(value.strip()) >= 24


def _answered_question_count(question_set_view: object) -> int:
    if not isinstance(question_set_view, dict):
        return 0
    questions = question_set_view.get("questions")
    if not isinstance(questions, list):
        return 0
    return sum(
        1
        for question in questions
        if isinstance(question, dict) and str(question.get("status", "")).strip() == "answered"
    )
