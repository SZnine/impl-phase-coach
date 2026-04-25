from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from review_gate.full_live_workflow_smoke import (
    build_full_live_workflow_smoke_artifact,
    classify_full_live_workflow_smoke_issues,
    format_full_live_workflow_smoke_report,
    resolve_first_generated_transport_question_id,
)
from review_gate.http_api import create_app, create_default_workspace_api


def main() -> int:
    args = _parse_args()
    repo_root = REPO_ROOT
    root_dir = Path(args.root_dir) if args.root_dir else repo_root
    output_dir = Path(args.output_dir) if args.output_dir else repo_root / "artifacts" / "full-live-workflow-smoke"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    db_path = output_dir / f"{timestamp}.sqlite3"
    session_path = output_dir / f"{timestamp}-session.json"
    project_model = args.project_model or args.model
    evaluator_model = args.evaluator_model or args.model

    client = TestClient(
        create_app(
            api=create_default_workspace_api(
                db_path=db_path,
                session_path=session_path,
                use_local_project_agent=True,
                project_agent_root_dir=root_dir,
                project_agent_model=project_model,
                use_local_evaluator_agent=True,
                evaluator_agent_root_dir=root_dir,
                evaluator_agent_model=evaluator_model,
            )
        )
    )
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    generation_response = client.post(
        "/api/actions/generate-question-set",
        json={
            "request_id": f"req-full-live-qgen-{timestamp}",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "full_live_workflow_smoke",
            "actor_id": "local-user",
            "created_at": created_at,
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "Run a minimum live workflow from project-agent questions to graph read surface.",
            "stage_artifacts": ["HTTP generation action", "generated question checkpoint", "graph revision"],
            "stage_exit_criteria": ["generated question submitted", "graph-main selected cluster exists"],
            "current_decisions": [
                "Question generation is exposed as an HTTP action.",
                "Submit uses generated question context when a generated chain exists.",
                "Graph read APIs consume the active submit-side graph revision.",
            ],
            "key_logic_points": [
                "transport question ids remain stable across generation and submit",
                "checkpoint records carry prompt, intent, expected signals, and source context",
                "facts and signals project into graph nodes and optional support relations",
            ],
            "known_weak_points": [
                "provider output may omit relation-supporting tags",
                "live smoke is observational and must not gate default pytest",
            ],
            "boundary_focus": [
                "Project Agent output contract",
                "generated question checkpoint",
                "Evaluator Agent assessment contract",
                "Facts to Graph projection",
            ],
            "question_strategy": "full_depth",
            "max_questions": args.max_questions,
            "source_refs": [
                "docs/superpowers/specs/2026-04-09-terminal-business-architecture-design.md",
                "docs/superpowers/specs/2026-04-21-full-live-workflow-smoke-design.md",
            ],
        },
    ).json()
    selected_question_id = resolve_first_generated_transport_question_id(
        generation_response=generation_response,
        question_set_id="set-1",
    )
    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": f"req-full-live-submit-{timestamp}",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "full_live_workflow_smoke",
            "actor_id": "local-user",
            "created_at": created_at,
            "question_set_id": "set-1",
            "question_id": selected_question_id,
            "answer_text": (
                "I understand the generated workflow should preserve the question boundary, "
                "but I did not fully specify malformed provider output handling, transaction rollback, "
                "or how relation-support evidence should be verified in regression tests."
            ),
            "draft_id": None,
        },
    ).json()
    graph_revision = client.get(
        "/api/knowledge/graph-revision",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    ).json()
    assessment_review = client.get(
        "/api/assessments/latest-review",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    ).json()
    question_set_view = client.get(
        "/api/projects/proj-1/stages/stage-1/questions/set-1",
    ).json()
    graph_main = client.get(
        "/api/knowledge/graph-main",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    ).json()

    issues = classify_full_live_workflow_smoke_issues(
        generation_response=generation_response,
        submit_response=submit_response,
        assessment_review=assessment_review,
        question_set_view=question_set_view,
        graph_revision=graph_revision,
        graph_main=graph_main,
        strict=args.strict,
    )
    artifact = build_full_live_workflow_smoke_artifact(
        generation_response=generation_response,
        selected_question_id=selected_question_id,
        submit_response=submit_response,
        assessment_review=assessment_review,
        question_set_view=question_set_view,
        graph_revision=graph_revision,
        graph_main=graph_main,
        issues=issues,
        db_path=str(db_path),
        project_model=project_model,
        evaluator_model=evaluator_model,
    )
    json_path = output_dir / f"{timestamp}.json"
    md_path = output_dir / f"{timestamp}.md"
    json_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    report = format_full_live_workflow_smoke_report(artifact)
    md_path.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nSaved JSON artifact to: {json_path}")
    print(f"Saved Markdown report to: {md_path}")
    return 1 if issues else 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run opt-in live workflow smoke through Project Agent, Evaluator Agent, and graph reads."
    )
    parser.add_argument("--root-dir", help="Repository root or config root that contains .env/api_key.md or key/api_key.md")
    parser.add_argument("--model", default="gpt-5.4-mini", help="Default provider model for both agents")
    parser.add_argument("--project-model", help="Project Agent provider model override")
    parser.add_argument("--evaluator-model", help="Evaluator Agent provider model override")
    parser.add_argument("--max-questions", type=int, default=4, help="Number of live generated questions to request")
    parser.add_argument("--output-dir", help="Directory for JSON/Markdown artifacts and temporary SQLite DB")
    parser.add_argument("--strict", action="store_true", help="Fail when the live output does not produce a relation")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
