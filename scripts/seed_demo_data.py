from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.domain import AssessmentFact, FocusCluster, FocusExplanation, current_utc_timestamp
from review_gate.http_api import create_default_workspace_api
from review_gate.view_dtos import WorkspaceSessionDTO


def _reset_demo_targets(*, db_path: Path, session_path: Path) -> None:
    for target in (db_path, session_path):
        if target.exists():
            target.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.parent.mkdir(parents=True, exist_ok=True)


def _submit_demo_answer(api, *, request_id: str, question_id: str, answer_text: str) -> None:
    api.submit_answer_action(
        SubmitAnswerRequest(
            request_id=request_id,
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="demo-user",
            created_at="2026-04-09T00:00:00Z",
            question_set_id="set-1",
            question_id=question_id,
            answer_text=answer_text,
            draft_id=None,
        )
    )


def _augment_latest_assessment_with_supports(api) -> None:
    assessment = api._flow.get_latest_assessment_snapshot("proj-1", "stage-1")
    if assessment is None:
        return

    augmented = dict(assessment)
    support_basis_tags = [
        {
            "basis_key": "state_modeling",
            "source_label": "State machine",
            "source_node_type": "foundation",
            "target_label": "Review flow control",
            "target_node_type": "concept",
        },
        {
            "basis_key": "boundary_awareness",
            "source_label": "Boundary discipline",
            "source_node_type": "foundation",
            "target_label": "Service/API boundary discipline",
            "target_node_type": "method",
        },
    ]
    augmented["support_basis_tags"] = support_basis_tags
    augmented["core_gaps"] = ["Review flow control"]
    augmented["support_signals"] = api._flow._derive_support_signals(augmented)

    store = getattr(api._flow, "_store", None)
    if store is not None:
        store.upsert_assessment_fact(AssessmentFact.from_dict(augmented))
    api._profile_space.sync_from_assessment("proj-1", "stage-1", augmented)


def _seed_support_showcase_cluster(api) -> None:
    profile_space = api._profile_space
    store = getattr(profile_space, "_store", None)
    if store is None:
        return

    project_id = "proj-1"
    stage_id = "stage-1"
    profile_space_id = profile_space._profile_space_id(project_id)
    center_node_id = profile_space._stable_node_id(profile_space_id, "concept", "Review flow control")
    neighbor_node_ids = [
        profile_space._stable_node_id(profile_space_id, "foundation", "State machine"),
        profile_space._stable_node_id(profile_space_id, "foundation", "Boundary discipline"),
        profile_space._stable_node_id(profile_space_id, "method", "Service/API boundary discipline"),
    ]
    cluster = {
        "cluster_id": f"{project_id}:{stage_id}:focus:demo-support-showcase",
        "profile_space_id": profile_space_id,
        "title": "Support relationships hotspot",
        "center_node_id": center_node_id,
        "neighbor_node_ids": neighbor_node_ids,
        "focus_reason_codes": ["current_project_hit", "foundation_hot"],
        "focus_reason_summary": "This area matters now because the current stage already shows explicit support relationships.",
        "generated_from": "current_project",
        "confidence": 0.85,
        "last_generated_at": current_utc_timestamp(),
        "is_pinned": False,
        "status": "active",
    }
    store.upsert_focus_cluster(FocusCluster.from_dict(cluster))
    explanation = profile_space._build_focus_explanation(profile_space_id=profile_space_id, cluster=cluster)
    store.upsert_focus_explanation(FocusExplanation.from_dict(explanation))


def _seed_workspace_session(api) -> None:
    api.save_workspace_session(
        WorkspaceSessionDTO(
            workspace_session_id="local-workspace-session",
            active_project_id="proj-1",
            active_stage_id="stage-1",
            active_panel="knowledge_graph",
            active_question_set_id=None,
            active_question_id=None,
            active_profile_space_id=None,
            active_proposal_center_id=None,
            last_opened_at="2026-04-09T00:00:00Z",
            filters={},
        )
    )


def seed_demo_workspace(*, db_path: Path, session_path: Path) -> None:
    _reset_demo_targets(db_path=db_path, session_path=session_path)
    api = create_default_workspace_api(db_path=db_path, session_path=session_path)

    _submit_demo_answer(
        api,
        request_id="req-demo-weak",
        question_id="set-1-q-1",
        answer_text="Boundary is fuzzy.",
    )
    _submit_demo_answer(
        api,
        request_id="req-demo-strong",
        question_id="set-1-q-2",
        answer_text=(
            "The review flow keeps question facts, assessment facts, and durable projection separate so that "
            "session restore, proposal actions, and the knowledge map can evolve without rewriting the raw evidence."
        ),
    )
    _augment_latest_assessment_with_supports(api)
    _seed_support_showcase_cluster(api)
    _seed_workspace_session(api)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed an isolated demo workspace for the review workbench.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=ROOT / ".workbench" / "demo" / "review-workbench-demo.sqlite3",
    )
    parser.add_argument(
        "--session-path",
        type=Path,
        default=ROOT / ".workbench" / "demo" / "workspace-session-demo.json",
    )
    args = parser.parse_args()

    seed_demo_workspace(db_path=args.db_path, session_path=args.session_path)
    print(f"DEMO_DB={args.db_path.resolve()}")
    print(f"DEMO_SESSION={args.session_path.resolve()}")


if __name__ == "__main__":
    main()
