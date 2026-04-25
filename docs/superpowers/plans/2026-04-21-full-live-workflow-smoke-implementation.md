# Full Live Workflow Smoke Implementation Plan

Goal: add an opt-in live workflow smoke that exercises live Project Agent generation, live Evaluator Agent assessment, durable checkpoint writes, graph projection, and graph read APIs.

## Current Answering Loop Checkpoint

The current workbench loop is intentionally centered on the user-facing learning workflow, not on graph polish:

1. `generate_question_set` writes durable question checkpoints that the Question Set and Question Detail read surfaces consume directly.
2. `submit_answer` writes answer / assessment / fact / graph artifacts and marks the resolved question item as `answered`.
3. `submit_answer.refresh_targets` includes `question_set`; the frontend refreshes the question set only when this target is present.
4. `QuestionSetPage` renders progress from question status (`已完成 / 当前题 / 待完成`) and advances the main CTA to the first unfinished question.
5. The full live smoke artifact and issue classifier now include the post-submit question-set read surface, so live runs fail visibly when submitted questions do not become `answered`.

This checkpoint protects the minimum real user loop: generate questions -> answer -> receive assessment review -> accumulate knowledge -> continue with the next question. Further UI work should improve this loop before expanding the star-map or graph surfaces.

## Task 1: Expose Generation as an HTTP Action

- Add a request DTO for question-set generation in `review_gate/action_dtos.py`.
- Add `WorkspaceAPI.generate_question_set_action`.
- Add `POST /api/actions/generate-question-set` in `review_gate/http_api.py`.
- Add a deterministic HTTP test with a fake generation client.

Exit condition: focused HTTP test proves the route returns normalized generated questions and persists the generated chain.

## Task 2: Add Pure Full-Smoke Helpers

- Create `review_gate/full_live_workflow_smoke.py`.
- Classify issues for generation, submit, graph revision, and graph-main payloads.
- Classify post-submit question-set progress, including the `question_set` refresh target and at least one `answered` question.
- Build artifact payloads without provider secrets.
- Format a compact Markdown report.
- Add deterministic unit tests.

Exit condition: helper tests pass without network.

## Task 3: Add Opt-In Script

- Create `scripts/run_full_live_workflow_smoke.py`.
- Build `create_default_workspace_api` with both local agents enabled.
- POST generation action.
- Submit an answer to the first generated transport question id.
- Read graph revision and graph main.
- Write timestamped JSON and Markdown artifacts under `artifacts/full-live-workflow-smoke`.

Exit condition: `--help` works without network, and the script code path is covered by pure helper tests.

## Task 4: Verification

- Run focused tests for HTTP generation action and full-smoke helpers.
- Run full `pytest -q`.
- Run the live script manually with network access.
- Commit implementation after deterministic tests pass.

Exit condition: deterministic test suite passes; live run produces an inspectable artifact or a clear provider error artifact.

## Verification Checkpoint

- `pytest -q`: 244 passed, with existing `datetime.utcnow()` deprecation warnings.
- `npm run test -- --run` in `frontend/`: 41 passed, with existing React Router future-flag and test `act(...)` warnings.
- `python scripts/run_full_live_workflow_smoke.py --help`: passed without network.
- `python scripts/run_full_live_workflow_smoke.py --max-questions 2`: passed with `issues: none`; generated 2 questions, marked 1 answered, advanced `current_question_id` to `set-1-q-2`, returned an assessment review, and produced graph revision data with 11 nodes and 6 relations.
- Live artifacts: `artifacts/full-live-workflow-smoke/20260425-054505.json` and `artifacts/full-live-workflow-smoke/20260425-054505.md`.
