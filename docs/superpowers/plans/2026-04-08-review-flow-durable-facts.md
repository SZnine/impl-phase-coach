# Review Flow Durable Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Answer`, `Assessment`, and `Decision` durable facts in SQLite so stage mastery survives a fresh service instance, while keeping `WorkspaceSession` as location-only state.

**Architecture:** Keep `ReviewFlowService` as the orchestration owner for submit-answer flow. Add durable fact models and SQLite tables for the question-flow records, then read those facts back when computing stage mastery and stage summaries. Preserve the current HTTP/API facade and do not move session state into the facts path.

**Tech Stack:** Python dataclasses, SQLite, FastAPI, pytest

---

### Task 1: Add durable fact models and tables

**Files:**
- Modify: `review_gate/domain.py`
- Modify: `review_gate/storage_sqlite.py`
- Test: `tests/test_workbench_storage.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from review_gate.domain import AnswerFact, AssessmentFact, DecisionFact
from review_gate.storage_sqlite import SQLiteStore


def test_sqlite_store_round_trips_durable_facts(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()

    answer = AnswerFact(
        answer_id="answer-1",
        request_id="req-1",
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        question_id="q-1",
        actor_id="local-user",
        source_page="question_detail",
        created_at="2026-04-08T12:00:00Z",
        answer_text="The boundary is stable.",
        draft_id=None,
    )
    assessment = AssessmentFact(
        assessment_id="assessment-1",
        request_id="req-1",
        answer_id="answer-1",
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        question_id="q-1",
        verdict="partial",
        score_total=0.72,
        dimension_scores={"correctness": 3},
        core_gaps=["Decision awareness"],
        misconceptions=[],
        confidence=0.8,
    )
    decision = DecisionFact(
        decision_id="decision-1",
        request_id="req-1",
        assessment_id="assessment-1",
        project_id="proj-1",
        stage_id="stage-1",
        decision_type="stage_mastery",
        decision_value="partially_verified",
        reason_summary="partial verdict promotes stage mastery",
        created_at="2026-04-08T12:00:01Z",
    )

    store.upsert_answer_fact(answer)
    store.upsert_assessment_fact(assessment)
    store.upsert_decision_fact(decision)

    assert store.get_answer_fact("answer-1") == answer
    assert store.get_assessment_fact("assessment-1") == assessment
    assert store.get_decision_fact("decision-1") == decision
```

- [ ] **Step 2: Run the failing test**

Run: `pytest tests/test_workbench_storage.py::test_sqlite_store_round_trips_durable_facts -q`
Expected: FAIL because the new fact models and SQLite methods do not exist yet.

- [ ] **Step 3: Implement the minimum**

```python
@dataclass(slots=True)
class AnswerFact(JsonSerializable):
    answer_id: str
    request_id: str
    project_id: str
    stage_id: str
    question_set_id: str
    question_id: str
    actor_id: str
    source_page: str
    created_at: str
    answer_text: str
    draft_id: str | None = None


@dataclass(slots=True)
class AssessmentFact(JsonSerializable):
    assessment_id: str
    request_id: str
    answer_id: str
    project_id: str
    stage_id: str
    question_set_id: str
    question_id: str
    verdict: str
    score_total: float
    dimension_scores: dict[str, int]
    core_gaps: list[str]
    misconceptions: list[str]
    confidence: float


@dataclass(slots=True)
class DecisionFact(JsonSerializable):
    decision_id: str
    request_id: str
    assessment_id: str
    project_id: str
    stage_id: str
    decision_type: str
    decision_value: str
    reason_summary: str
    created_at: str
```

Add `answer_fact_store`, `assessment_fact_store`, and `decision_fact_store` tables plus `upsert_*` / `get_*` / `list_*` helpers in `SQLiteStore`.

- [ ] **Step 4: Re-run the test**

Run: `pytest tests/test_workbench_storage.py::test_sqlite_store_round_trips_durable_facts -q`
Expected: PASS.

---

### Task 2: Persist submit-answer flow and recover mastery

**Files:**
- Modify: `review_gate/review_flow_service.py`
- Modify: `review_gate/workspace_api.py`
- Test: `tests/test_review_flow_service.py`
- Test: `tests/test_http_api.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.review_flow_service import ReviewFlowService
from review_gate.storage_sqlite import SQLiteStore


def test_submit_answer_persists_facts_and_recovers_mastery_after_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "review.sqlite3"
    first_service = ReviewFlowService.with_store(SQLiteStore(db_path))
    first_service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-08T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to avoid the weak fallback verdict.",
            draft_id=None,
        )
    )

    second_service = ReviewFlowService.with_store(SQLiteStore(db_path))
    assert second_service.get_stage_view("proj-1", "stage-1").mastery_status == "partially_verified"
```

- [ ] **Step 2: Run the failing test**

Run: `pytest tests/test_review_flow_service.py::test_submit_answer_persists_facts_and_recovers_mastery_after_restart -q`
Expected: FAIL because submit-answer still only updates in-memory state.

- [ ] **Step 3: Implement the minimum**

```python
answer_fact = AnswerFact(...)
assessment_fact = AssessmentFact(...)
self._store.upsert_answer_fact(answer_fact)
self._store.upsert_assessment_fact(assessment_fact)
if verdict in {"partial", "strong"}:
    self._store.upsert_decision_fact(DecisionFact(...))
```

Read mastery back from the latest durable decision when a store is available; keep in-memory caches as fallback only.

- [ ] **Step 4: Re-run the flow test**

Run: `pytest tests/test_review_flow_service.py::test_submit_answer_persists_facts_and_recovers_mastery_after_restart -q`
Expected: PASS.

- [ ] **Step 5: Re-run the HTTP regression**

Run: `pytest tests/test_http_api.py::test_http_api_submit_answer_returns_assessment_and_refreshes_stage_mastery -q`
Expected: PASS with the same response shape as before.

---

### Task 3: Lock boundary regressions

**Files:**
- Modify: `tests/test_http_api.py`
- Modify: `tests/test_workbench_storage.py`
- Modify: `tests/test_workspace_api.py` only if a narrower backend assertion is needed

- [ ] **Step 1: Add the regression**

Keep one test that proves `WorkspaceSession` still stores only location state, and one test that proves `create_default_workspace_api(db_path)` can be rebuilt from the same SQLite file and still return the same stage mastery and knowledge summary.

- [ ] **Step 2: Run the package-level regression set**

Run: `pytest tests/test_workbench_storage.py tests/test_review_flow_service.py tests/test_http_api.py -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add review_gate/domain.py review_gate/storage_sqlite.py review_gate/review_flow_service.py review_gate/workspace_api.py tests/test_workbench_storage.py tests/test_review_flow_service.py tests/test_http_api.py tests/test_workspace_api.py
git commit -m "feat: persist durable review facts"
```

---

### Iteration 2 / 3 Frozen Boundary Summary

- `Iteration 2` only covers `WorkspaceSession` recovery completion: filters, draft, pause, and finer-grained page position.
- `Iteration 3` only covers real usage testing and stability hardening: cross-instance replay, failure-mode replay, and regression matrix expansion.
- Neither later iteration should absorb the durable-facts work from this plan.

---

### Execution Log

- `2026-04-08`: Implemented the iter-1 durable facts slice.
- Added `AnswerFact`, `AssessmentFact`, and `DecisionFact` to `review_gate/domain.py`.
- Added SQLite persistence helpers and tables for answer, assessment, and decision facts in `review_gate/storage_sqlite.py`.
- Updated `review_gate/review_flow_service.py` so `submit_answer` persists durable facts and `get_latest_assessment_snapshot` / stage mastery can recover from the stored records.
- Kept `WorkspaceSession` as location-only state; no question-flow facts moved into session storage.
- Tightened regression coverage in `tests/test_workbench_storage.py`, `tests/test_review_flow_service.py`, and `tests/test_http_api.py`.
- Verification completed with:
  - `pytest tests/test_workbench_storage.py -q`
  - `pytest tests/test_review_flow_service.py -q`
  - `pytest tests/test_http_api.py -q`
  - `pytest tests/test_workbench_storage.py tests/test_review_flow_service.py tests/test_http_api.py -q`
- Current working rule: `Answer / Assessment / Decision` are durable facts; `WorkspaceSession` remains a location-only record; API shape stays unchanged.
