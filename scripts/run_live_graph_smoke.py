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

from review_gate.http_api import create_app, create_default_workspace_api
from review_gate.live_graph_smoke import (
    build_live_graph_smoke_artifact,
    classify_live_graph_smoke_issues,
    format_live_graph_smoke_report,
)


def main() -> int:
    args = _parse_args()
    repo_root = REPO_ROOT
    root_dir = Path(args.root_dir) if args.root_dir else repo_root
    output_dir = Path(args.output_dir) if args.output_dir else repo_root / "artifacts" / "live-graph-smoke"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    db_path = output_dir / f"{timestamp}.sqlite3"
    session_path = output_dir / f"{timestamp}-session.json"

    client = TestClient(
        create_app(
            api=create_default_workspace_api(
                db_path=db_path,
                session_path=session_path,
                use_local_evaluator_agent=True,
                evaluator_agent_root_dir=root_dir,
                evaluator_agent_model=args.model,
            )
        )
    )
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": f"req-live-graph-smoke-{timestamp}",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "live_graph_smoke",
            "actor_id": "local-user",
            "created_at": created_at,
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": (
                "The API boundary exists, but I did not define the request/response contract, "
                "the persistence boundary, or malformed provider-output regression clearly."
            ),
            "draft_id": None,
        },
    )
    graph_revision_response = client.get(
        "/api/knowledge/graph-revision",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    )
    graph_main_response = client.get(
        "/api/knowledge/graph-main",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    )

    submit_payload = submit_response.json()
    graph_revision_payload = graph_revision_response.json()
    graph_main_payload = graph_main_response.json()
    issues = classify_live_graph_smoke_issues(
        submit_response=submit_payload,
        graph_revision=graph_revision_payload,
        graph_main=graph_main_payload,
        strict=args.strict,
    )
    artifact = build_live_graph_smoke_artifact(
        submit_response=submit_payload,
        graph_revision=graph_revision_payload,
        graph_main=graph_main_payload,
        issues=issues,
        db_path=str(db_path),
        model=args.model,
    )
    json_path = output_dir / f"{timestamp}.json"
    md_path = output_dir / f"{timestamp}.md"
    json_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    report = format_live_graph_smoke_report(artifact)
    md_path.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nSaved JSON artifact to: {json_path}")
    print(f"Saved Markdown report to: {md_path}")
    return 1 if issues else 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run opt-in live graph smoke through evaluator + graph read APIs.")
    parser.add_argument("--root-dir", help="Repository root or config root that contains .env/api_key.md or key/api_key.md")
    parser.add_argument("--model", default="gpt-5.4-mini", help="Evaluator provider model to use")
    parser.add_argument("--output-dir", help="Directory for JSON/Markdown artifacts and temporary SQLite DB")
    parser.add_argument("--strict", action="store_true", help="Fail when the live output does not produce a relation")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
