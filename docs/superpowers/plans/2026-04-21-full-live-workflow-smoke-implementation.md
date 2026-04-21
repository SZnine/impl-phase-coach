# Full Live Workflow Smoke Implementation Plan

Goal: add an opt-in live workflow smoke that exercises live Project Agent generation, live Evaluator Agent assessment, durable checkpoint writes, graph projection, and graph read APIs.

## Task 1: Expose Generation as an HTTP Action

- Add a request DTO for question-set generation in `review_gate/action_dtos.py`.
- Add `WorkspaceAPI.generate_question_set_action`.
- Add `POST /api/actions/generate-question-set` in `review_gate/http_api.py`.
- Add a deterministic HTTP test with a fake generation client.

Exit condition: focused HTTP test proves the route returns normalized generated questions and persists the generated chain.

## Task 2: Add Pure Full-Smoke Helpers

- Create `review_gate/full_live_workflow_smoke.py`.
- Classify issues for generation, submit, graph revision, and graph-main payloads.
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
