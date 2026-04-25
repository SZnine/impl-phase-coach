# Live Graph Smoke Design

> This spec defines the opt-in live LLM smoke for proving that real agent output can flow into the graph read surfaces. It is intentionally not part of default `pytest`, because it depends on the local provider configuration and network access.

## 1. Current Position

The original live graph smoke only needed to prove:

```text
submit-answer
  -> Evaluator Agent assessment
  -> facts / signals
  -> graph revision
  -> graph-main read surface
```

The project has since moved one step closer to real product usage. The stronger smoke now exercises the full learning loop:

```text
Project Agent generates questions
  -> durable question checkpoint
  -> user submits an answer
  -> Evaluator Agent returns assessment review
  -> facts / signals / graph revision
  -> graph-main read surface
  -> question set progress updates
```

This does not replace deterministic tests. It gives an inspectable real-run artifact so we can judge whether the workflow is usable with actual LLM output.

## 2. Goal

The live smoke should answer three questions:

1. Can the Project Agent generate readable, project-grounded questions?
2. Can the Evaluator Agent produce a readable assessment summary from a submitted answer?
3. Can the resulting facts and signals enter the graph read model without breaking question progress?

The minimum successful run must produce:

1. at least one generated question;
2. at least one answered question in the question set read surface;
3. an assessment review with a readable summary;
4. an active graph revision with at least one node;
5. a graph-main response with a selected cluster.

Relations are quality signals, not a default hard requirement. `--strict` may make missing relations fail.

## 3. Non-Goals

This stage does not:

1. put live provider calls into default tests;
2. print API keys, provider headers, or raw provider configuration;
3. require every live run to produce graph relations;
4. tune the UI layout;
5. expand graph schema;
6. treat one live success as proof of product quality.

The smoke is a regression and observability tool. Product quality still needs repeated real usage.

## 4. Command Entry

The current full workflow smoke entry is:

```powershell
python scripts/run_full_live_workflow_smoke.py --max-questions 2
```

Useful options:

```text
--root-dir
--model
--project-model
--evaluator-model
--max-questions
--output-dir
--strict
```

Defaults:

1. `root-dir` is the repository root.
2. `model` is `gpt-5.4-mini`.
3. `output-dir` is `artifacts/full-live-workflow-smoke`.
4. `strict` is off.

The script reads OpenAI-compatible provider config from `.env/api_key.md` or `key/api_key.md`, but it must never echo secrets into artifacts or logs.

## 5. Generation Request Quality

The generation request must carry learning-oriented context, not only engineering-stage fields:

```text
learning_goal: practice realistic project questions, interview fundamentals, and misconception diagnosis
target_user_level: intermediate
question_mix:
  - project implementation
  - interview fundamentals
  - mistake diagnosis
  - failure scenario
preferred_question_style: concrete study-app question list with direct prompts and reviewable answers
```

This keeps Project Agent output closer to a real study workflow instead of abstract architecture discussion.

## 6. Issue Classification

The smoke currently classifies these hard issues:

1. `missing_generated_questions`
2. `missing_readable_generated_question_prompt`
3. `submit_failed`
4. `missing_question_set_refresh_target`
5. `missing_assessment_review`
6. `missing_readable_assessment_review_summary`
7. `missing_answered_question_progress`
8. `missing_active_graph_revision`
9. `missing_graph_nodes`
10. `missing_graph_main_nodes`
11. `missing_selected_cluster`
12. `missing_relation_in_strict_mode`

The content quality gates are deliberately simple:

1. at least one generated question prompt must be readable;
2. the assessment review summary must be readable.

These gates catch obvious provider drift without pretending to fully grade question quality.

## 7. Artifact Shape

Each run writes:

```text
artifacts/full-live-workflow-smoke/YYYYMMDD-HHMMSS.json
artifacts/full-live-workflow-smoke/YYYYMMDD-HHMMSS.md
```

The JSON artifact includes:

1. generation response;
2. selected question id;
3. submit response;
4. assessment review;
5. question set read surface after submit;
6. graph revision;
7. graph-main response;
8. issue list;
9. model names and artifact DB path.

The Markdown report must be readable without opening JSON. It includes:

1. generated question count;
2. selected question id;
3. generated question prompts and intents;
4. answered question count and current question id;
5. assessment review title and summary;
6. graph node and relation counts;
7. selected cluster summary;
8. issues.

## 8. Verification Boundary

Default deterministic tests cover helper behavior only:

```powershell
python -m pytest tests/test_full_live_workflow_smoke.py -q
```

The full test suite remains network-free:

```powershell
python -m pytest -q
```

Manual live verification is explicit:

```powershell
python scripts/run_full_live_workflow_smoke.py --max-questions 2
```

## 9. Latest Checkpoint

The current checkpoint has been verified with:

1. `python -m pytest tests/test_full_live_workflow_smoke.py -q`: 11 passed.
2. `python -m pytest -q`: 249 passed.
3. `python scripts/run_full_live_workflow_smoke.py --max-questions 2`: issues none.

Latest successful live artifact example:

```text
artifacts/full-live-workflow-smoke/20260425-072953.json
artifacts/full-live-workflow-smoke/20260425-072953.md
```

The observed live run generated readable questions, produced a readable assessment summary, marked one question as answered, and produced a graph revision plus selected cluster.
