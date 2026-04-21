# Live Graph Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in live evaluator graph smoke that submits one answer through the real HTTP/API/service path and records whether the new Graph Layer produces nodes, relations, and a selected cluster.

**Architecture:** Keep the live network call out of default tests by adding a command-line script under `scripts/`. Put reusable check/report helpers in `review_gate/live_graph_smoke.py` so default tests can validate behavior without contacting a provider. The script builds `create_default_workspace_api(..., use_local_evaluator_agent=True)`, submits a fixed answer through FastAPI `TestClient`, reads `graph-revision` and `graph-main`, then writes JSON and Markdown artifacts.

**Tech Stack:** Python, FastAPI TestClient, SQLiteStore through existing app factory, existing `EvaluatorAgentAssessmentClient`, pytest for pure helper tests.

---

## File Structure

- Create `review_gate/live_graph_smoke.py`: pure data helpers for checks, artifact payload, and Markdown report formatting.
- Create `tests/test_live_graph_smoke.py`: deterministic tests for helper behavior; no live network.
- Create `scripts/run_live_graph_smoke.py`: opt-in command that uses live evaluator provider config and writes artifacts.
- Do not modify default pytest config.
- Do not read or print API keys.

---

### Task 1: Add Pure Smoke Check Helpers

**Files:**
- Create: `review_gate/live_graph_smoke.py`
- Test: `tests/test_live_graph_smoke.py`

- [ ] **Step 1: Write failing helper tests**

Create `tests/test_live_graph_smoke.py` with:

```python
from review_gate.live_graph_smoke import (
    build_live_graph_smoke_artifact,
    classify_live_graph_smoke_issues,
    format_live_graph_smoke_report,
)


def test_classify_live_graph_smoke_issues_requires_graph_node_and_cluster() -> None:
    issues = classify_live_graph_smoke_issues(
        submit_response={"success": True},
        graph_revision={
            "has_active_revision": True,
            "revision": {"node_count": 1, "relation_count": 0},
            "nodes": [{"knowledge_node_id": "kn-1"}],
            "relations": [],
        },
        graph_main={
            "nodes": [{"node_id": "kn-1"}],
            "relations": [],
            "selected_cluster": {"center_node_id": "kn-1"},
        },
        strict=False,
    )

    assert issues == []


def test_classify_live_graph_smoke_issues_treats_missing_relation_as_strict_only() -> None:
    base_kwargs = {
        "submit_response": {"success": True},
        "graph_revision": {
            "has_active_revision": True,
            "revision": {"node_count": 1, "relation_count": 0},
            "nodes": [{"knowledge_node_id": "kn-1"}],
            "relations": [],
        },
        "graph_main": {
            "nodes": [{"node_id": "kn-1"}],
            "relations": [],
            "selected_cluster": {"center_node_id": "kn-1"},
        },
    }

    assert classify_live_graph_smoke_issues(**base_kwargs, strict=False) == []
    assert classify_live_graph_smoke_issues(**base_kwargs, strict=True) == ["missing_relation_in_strict_mode"]


def test_build_live_graph_smoke_artifact_omits_sensitive_provider_config() -> None:
    artifact = build_live_graph_smoke_artifact(
        submit_response={"success": True},
        graph_revision={"has_active_revision": True},
        graph_main={"nodes": []},
        issues=[],
        db_path="C:/tmp/smoke.sqlite3",
        model="gpt-5.4-mini",
    )

    assert artifact["model"] == "gpt-5.4-mini"
    assert artifact["db_path"] == "C:/tmp/smoke.sqlite3"
    assert "api_key" not in str(artifact).lower()
    assert "authorization" not in str(artifact).lower()


def test_format_live_graph_smoke_report_surfaces_graph_counts_and_cluster() -> None:
    report = format_live_graph_smoke_report(
        {
            "model": "gpt-5.4-mini",
            "issues": [],
            "submit_response": {"success": True},
            "graph_revision": {
                "revision": {"node_count": 2, "relation_count": 1},
            },
            "graph_main": {
                "selected_cluster": {
                    "center_node_id": "kn-target",
                    "neighbor_node_ids": ["kn-source"],
                    "focus_reason_codes": ["weak_signal_active", "relation_connected"],
                }
            },
        }
    )

    assert "model: gpt-5.4-mini" in report
    assert "node_count: 2" in report
    assert "relation_count: 1" in report
    assert "issues: none" in report
    assert "center_node_id: kn-target" in report
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_live_graph_smoke.py -q
```

Expected: FAIL because `review_gate.live_graph_smoke` does not exist.

- [ ] **Step 3: Implement helper module**

Create `review_gate/live_graph_smoke.py` with:

```python
from __future__ import annotations

from typing import Any


def classify_live_graph_smoke_issues(
    *,
    submit_response: dict[str, Any],
    graph_revision: dict[str, Any],
    graph_main: dict[str, Any],
    strict: bool,
) -> list[str]:
    issues: list[str] = []
    if submit_response.get("success") is not True:
        issues.append("submit_failed")
    if graph_revision.get("has_active_revision") is not True:
        issues.append("missing_active_graph_revision")
    revision = graph_revision.get("revision")
    if not isinstance(revision, dict) or int(revision.get("node_count", 0) or 0) < 1:
        issues.append("missing_graph_nodes")
    if not graph_main.get("nodes"):
        issues.append("missing_graph_main_nodes")
    if graph_main.get("selected_cluster") is None:
        issues.append("missing_selected_cluster")
    relation_count = 0
    if isinstance(revision, dict):
        relation_count = int(revision.get("relation_count", 0) or 0)
    if strict and relation_count < 1:
        issues.append("missing_relation_in_strict_mode")
    return issues


def build_live_graph_smoke_artifact(
    *,
    submit_response: dict[str, Any],
    graph_revision: dict[str, Any],
    graph_main: dict[str, Any],
    issues: list[str],
    db_path: str,
    model: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "db_path": db_path,
        "issues": list(issues),
        "submit_response": submit_response,
        "graph_revision": graph_revision,
        "graph_main": graph_main,
    }


def format_live_graph_smoke_report(artifact: dict[str, Any]) -> str:
    graph_revision = artifact.get("graph_revision", {})
    revision = graph_revision.get("revision", {}) if isinstance(graph_revision, dict) else {}
    graph_main = artifact.get("graph_main", {})
    selected_cluster = graph_main.get("selected_cluster", {}) if isinstance(graph_main, dict) else {}
    issues = artifact.get("issues") or []
    lines = [
        "# Live Graph Smoke Report",
        "",
        f"model: {artifact.get('model', '')}",
        f"db_path: {artifact.get('db_path', '')}",
        f"issues: {', '.join(issues) if issues else 'none'}",
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
```

- [ ] **Step 4: Run helper tests and verify they pass**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_live_graph_smoke.py -q
```

Expected: PASS.

---

### Task 2: Add Opt-In Live Script

**Files:**
- Create: `scripts/run_live_graph_smoke.py`

- [ ] **Step 1: Create script**

Create `scripts/run_live_graph_smoke.py` with:

```python
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

from review_gate.http_api import create_app
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
            db_path=db_path,
            session_path=session_path,
            use_local_evaluator_agent=True,
            evaluator_agent_root_dir=root_dir,
            evaluator_agent_model=args.model,
        )
    )
    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": f"req-live-graph-smoke-{timestamp}",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "live_graph_smoke",
            "actor_id": "local-user",
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
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
```

- [ ] **Step 2: Run focused helper tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_live_graph_smoke.py -q
```

Expected: PASS.

- [ ] **Step 3: Run script help without network**

Run:

```powershell
python scripts/run_live_graph_smoke.py --help
```

Expected: exits 0 and shows script arguments.

---

### Task 3: Run Verification and Commit

**Files:**
- Modify: none beyond Task 1 and Task 2 files.

- [ ] **Step 1: Run focused regression**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_live_graph_smoke.py tests/test_evaluator_agent_assessment_client.py tests/test_http_api.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full regression**

Run:

```powershell
$env:PYTHONPATH='.'; pytest -q
```

Expected: PASS.

- [ ] **Step 3: Commit implementation**

Run:

```powershell
git add review_gate/live_graph_smoke.py tests/test_live_graph_smoke.py scripts/run_live_graph_smoke.py docs/superpowers/plans/2026-04-21-live-graph-smoke-implementation.md
git commit -m "feat: add opt-in live graph smoke"
```

---

## Optional Manual Live Command

This command is not part of default regression and may require network access:

```powershell
python scripts/run_live_graph_smoke.py --root-dir . --model gpt-5.4-mini
```

Use `--strict` only when relation generation quality is being evaluated:

```powershell
python scripts/run_live_graph_smoke.py --root-dir . --model gpt-5.4-mini --strict
```

