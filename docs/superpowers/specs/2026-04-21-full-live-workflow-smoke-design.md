# Full Live Workflow Smoke Design

> This spec defines an opt-in live smoke that runs the smallest realistic user workflow through both live LLM agents and the graph read surface.

## Current Position

The project already has a working submit-side graph path:

```text
submit-answer
  -> Evaluator Agent
  -> durable assessment facts
  -> knowledge signals
  -> graph revision
  -> graph-main read model
```

The current live smoke proves the evaluator-to-graph segment. It does not yet prove that a live Project Agent generated question can become the submitted question context before evaluation.

## Goal

Add a manual command that executes:

```text
Project Agent live question generation
  -> generated question checkpoint
  -> submit one generated question answer
  -> Evaluator Agent live assessment
  -> facts/signals/graph projection
  -> graph-revision and graph-main reads
  -> JSON/Markdown artifact
```

This is a minimum real loop, not a production UI workflow.

## Non-Goals

1. Do not add the live workflow to default `pytest`.
2. Do not print API keys, Authorization headers, provider config files, or raw secret-bearing request data.
3. Do not add Maintenance Agent behavior.
4. Do not add UI automation.
5. Do not require relation generation unless `--strict` is explicitly enabled.
6. Do not redesign the graph schema in this step.

## API Boundary

Expose the existing service capability as a small HTTP action:

```text
POST /api/actions/generate-question-set
```

The route delegates to `WorkspaceAPI.generate_question_set_action`, which delegates to `ReviewFlowService.generate_question_set`.

The response remains the existing normalized generation payload. The route exists so the smoke exercises the same HTTP action boundary style as `submit-answer`.

## Script Boundary

Add:

```text
scripts/run_full_live_workflow_smoke.py
```

Default behavior:

1. Create a timestamped temporary SQLite workspace under `artifacts/full-live-workflow-smoke`.
2. Build `create_default_workspace_api` with both `use_local_project_agent=True` and `use_local_evaluator_agent=True`.
3. POST `/api/actions/generate-question-set`.
4. Select the first generated transport question id from the generated question set.
5. POST `/api/actions/submit-answer` with a fixed answer that is intentionally incomplete enough for evaluator feedback.
6. GET `/api/knowledge/graph-revision`.
7. GET `/api/knowledge/graph-main`.
8. Write JSON and Markdown artifacts.

## Checks

Hard checks:

1. generation response contains at least one question.
2. submit response has `success == true`.
3. graph revision has an active revision.
4. graph revision has at least one node.
5. graph main has nodes.
6. graph main has a selected cluster.

Strict-only check:

1. graph revision has at least one relation.

## Success Criteria

This stage is complete when a developer can run one explicit command and inspect an artifact proving that live generated questions can flow into live evaluated answers and then into the graph read surface.
