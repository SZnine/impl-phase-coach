# Evaluator Agent / LLM Assessment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the testing-only assessment stub with a real LLM-backed Evaluator Agent while keeping the current `Question -> Answer -> Evaluation -> Facts` checkpoint chain stable.

**Architecture:** Keep `ReviewFlowService.submit_answer` as the transport-facing orchestration owner, but move real evaluator variability behind a dedicated prompt builder, provider client, and response normalizer. The existing `AssessmentSynthesizer` and checkpoint persistence path stay in place; only the assessment input source changes.

**Tech Stack:** Python, requests-based third-party OpenAI-compatible provider access, pytest, current SQLite-backed checkpoint pipeline

---

## Why This Stage Exists

We have already completed:

1. the first migration checkpoint:
   - `Workflow -> Question -> Answer -> Evaluation -> Facts`
2. the first orchestration split on both generation and submit sides
3. real Project Agent integration for question generation
4. a first round of Project Agent quality tuning

The next highest-value move is to make the evaluation side equally real.

Right now the weakest remaining fake segment in the main business loop is:

`submit_answer -> assessment_client.assess(...) -> evaluation/facts`

Until that becomes provider-backed, the system still hides real problems in:

1. answer evaluation contract shape
2. evidence and gap extraction quality
3. facts synthesis realism
4. downstream resilience to noisy LLM output

This stage is not about Graph or Maintenance.
It is about finishing the real-agent replacement for the minimal business loop.

---

## Scope

### In scope

1. LLM-backed evaluator prompt contract
2. provider-backed evaluator client
3. response normalizer for evaluator output
4. wiring into `ReviewFlowService.submit_answer`
5. fake-regression and opt-in live-smoke testing

### Out of scope

1. Graph / Maintenance
2. schema changes
3. checkpoint ownership changes
4. focus/explanation
5. retrieval augmentation
6. evaluator-driven follow-up question planning beyond current DTO shape

---

## File Map

### Create

- `review_gate/evaluator_agent_prompt_builder.py`
  - builds the evaluation prompt from question context, user answer, and current stage context
- `review_gate/evaluator_agent_assessment_client.py`
  - provider-backed evaluator adapter using the same third-party OpenAI-compatible runtime style as Project Agent
- `review_gate/evaluator_agent_response_normalizer.py`
  - validates and normalizes raw evaluator output into the current stable assessment response shape
- `tests/test_evaluator_agent_prompt_builder.py`
- `tests/test_evaluator_agent_assessment_client.py`
- `tests/test_evaluator_agent_response_normalizer.py`

### Modify

- `review_gate/review_flow_service.py`
  - allow `submit_answer` to consume raw evaluator output through the normalizer before using the existing checkpoint chain
- `review_gate/http_api.py`
  - optional default workspace wiring for local evaluator agent
- `tests/test_review_flow_service.py`
  - service-layer evaluator regression
- `tests/test_http_api.py`
  - transport-level evaluator regression

### Keep unchanged in responsibility

- `review_gate/assessment_synthesizer.py`
  - still owns `Evaluation -> Facts`
- `review_gate/answer_checkpoint_writer.py`
  - still owns submit-side checkpoint writes
- `review_gate/storage_sqlite.py`
  - no schema widening in this stage

---

## Current Relevant Boundaries

1. `PromptBuilder` owns what the evaluator is asked to judge.
2. `AssessmentClient` owns provider calling only.
3. `ResponseNormalizer` owns coercion into the current stable assessment shape.
4. `ReviewFlowService` owns orchestration only.
5. `AssessmentSynthesizer` still owns `Evaluation -> Facts`.

The key boundary for this stage is:

`Raw evaluator output must not directly define persisted evaluation/fact records.`

It must first be normalized into the stable assessment shape that the current checkpoint chain already consumes.

---

## Knowledge Priorities

### High priority

1. evaluation prompt contract design
2. structured output normalization
3. noisy LLM output containment
4. keeping transport ids, durable ids, and evaluator semantics separate

### Medium priority

1. lightweight evidence extraction heuristics
2. failure-mode oriented evaluation prompts
3. mixed fake/live test strategy

### Low priority for this stage

1. token optimization
2. graph-aware evaluation
3. long-term scoring governance
4. retrieval or memory augmentation

---

## Target Evaluator Output Shape

The LLM-backed evaluator must normalize into the same top-level structure already expected by `ReviewFlowService.submit_answer`.

Minimum stable shape after normalization:

```json
{
  "request_id": "req-1",
  "assessment": {
    "score_total": 0.72,
    "dimension_scores": {
      "correctness": 3,
      "reasoning": 3,
      "decision_awareness": 2,
      "boundary_awareness": 3,
      "stability": 2
    },
    "verdict": "partial",
    "core_gaps": ["Need deeper boundary explanation."],
    "misconceptions": [],
    "evidence": ["quoted or paraphrased evidence"]
  },
  "recommended_action": "continue_answering",
  "recommended_follow_up_questions": [],
  "learning_recommendations": [],
  "warnings": [],
  "confidence": 0.8
}
```

Rules:

1. raw provider output may be richer
2. only the normalized shape may enter `ReviewFlowService`
3. malformed evaluator output must fail before checkpoint writing starts

---

## Evaluation Quality Direction

The evaluator should not only judge abstract correctness.
It should also surface more grounded downstream issues when the answer supports them.

Examples of allowed evaluator concerns:

1. wrong library or API usage
2. method-level misuse
3. test strategy gaps
4. boundary confusion
5. migration/failure-mode blind spots

This does **not** mean turning the evaluator into an unrestricted reviewer.
It means allowing assessment output to reflect:

1. architecture-level problems
2. implementation-level problems
3. testing-level problems
4. persistence and compatibility problems

That direction should be reflected in prompt examples and normalization tests.

---

## Testing Strategy

Two test lanes are required.

### 1. Stable regression lane

Always-on tests using fake transport:

1. prompt builder unit tests
2. client transport-shape tests
3. normalizer unit tests
4. service regression
5. http/workspace regression

This lane must never require real network access or real keys.

### 2. Opt-in live smoke lane

Manual or opt-in runs using the real provider config from local machine state:

1. one real evaluation request
2. one real normalized assessment
3. one end-to-end submit flow validation

This lane exists to validate realism and provider compatibility, not to replace stable regression.

---

## Planned Tasks

### Task 1: Add evaluator prompt builder

**Files:**
- Create: `review_gate/evaluator_agent_prompt_builder.py`
- Create: `tests/test_evaluator_agent_prompt_builder.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert the prompt:

1. includes current question context
2. includes user answer text
3. asks for both conceptual and implementation-grounded judgment
4. allows lower-level issues such as library/method/test misuse to be surfaced
5. forbids freeform essay output without structured assessment fields

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_evaluator_agent_prompt_builder.py -q`

Expected: FAIL because the prompt builder file does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create a builder that accepts:

1. request id
2. project/stage/question context
3. answer text
4. current decisions and boundary focus when available

And outputs:

1. `system_prompt`
2. `user_prompt`
3. `output_contract`

The prompt must explicitly request:

1. verdict
2. dimension scores
3. core gaps
4. misconceptions
5. evidence
6. action recommendation

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_evaluator_agent_prompt_builder.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add review_gate/evaluator_agent_prompt_builder.py tests/test_evaluator_agent_prompt_builder.py
git commit -m "feat: add evaluator agent prompt builder"
```

### Task 2: Add provider-backed evaluator assessment client

**Files:**
- Create: `review_gate/evaluator_agent_assessment_client.py`
- Create: `tests/test_evaluator_agent_assessment_client.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:

1. local config can be loaded from `.env/api_key.md` or `key/api_key.md`
2. provider request shape uses the expected base URL + model + streaming transport style
3. tests can inject fake transport and do not require live network

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_evaluator_agent_assessment_client.py -q`

Expected: FAIL because the client file does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Mirror the Project Agent runtime boundary:

1. `from_local_config(...)`
2. provider-backed `assess(...)`
3. fake transport injection for tests
4. raw provider result returned without checkpoint semantics

Use the same provider compatibility style already proven on Project Agent:

1. `requests`
2. third-party OpenAI-compatible base URL
3. streaming content assembly if required by this provider

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_evaluator_agent_assessment_client.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add review_gate/evaluator_agent_assessment_client.py tests/test_evaluator_agent_assessment_client.py
git commit -m "feat: add evaluator agent assessment client"
```

### Task 3: Add evaluator response normalizer

**Files:**
- Create: `review_gate/evaluator_agent_response_normalizer.py`
- Create: `tests/test_evaluator_agent_response_normalizer.py`

- [ ] **Step 1: Write the failing tests**

Add tests that cover:

1. valid raw JSON normalizes into the current stable assessment shape
2. malformed JSON is rejected
3. missing required fields are rejected
4. evidence is normalized into a string list
5. dimension scores are coerced into the current five-dimension structure
6. grounded issues such as library/test/method misuse can map into `core_gaps` or `misconceptions`

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_evaluator_agent_response_normalizer.py -q`

Expected: FAIL because the normalizer file does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement normalization order:

1. parse raw content
2. validate assessment object
3. coerce dimension scores
4. coerce evidence list
5. coerce `recommended_action`, `warnings`, `follow_up`, and `learning_recommendations`
6. return current stable shape

Do not let this layer:

1. write checkpoint rows
2. synthesize facts
3. infer graph semantics

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_evaluator_agent_response_normalizer.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add review_gate/evaluator_agent_response_normalizer.py tests/test_evaluator_agent_response_normalizer.py
git commit -m "feat: add evaluator agent response normalizer"
```

### Task 4: Wire evaluator path into ReviewFlowService

**Files:**
- Modify: `review_gate/review_flow_service.py`
- Modify: `tests/test_review_flow_service.py`

- [ ] **Step 1: Write the failing tests**

Add service tests that prove:

1. `submit_answer` can consume raw evaluator output via the normalizer
2. malformed evaluator output fails before checkpoint writes
3. existing checkpoint chain still writes `EvaluationBatch`, `EvaluationItem`, `EvidenceSpan`, and `AssessmentFact*`
4. downstream facts synthesis still works on normalized evaluator output

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_review_flow_service.py -q`

Expected: FAIL because service does not yet route raw evaluator output through a normalizer-backed path.

- [ ] **Step 3: Write minimal implementation**

Update `ReviewFlowService` so that:

1. testing client path still works
2. evaluator raw-output path is detected cleanly
3. raw output is normalized before existing assessment/checkpoint handling
4. no checkpoint ownership is moved in this stage

Keep:

1. `AnswerCheckpointWriter`
2. `AssessmentSynthesizer`
3. existing DTO shapes

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_review_flow_service.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add review_gate/review_flow_service.py tests/test_review_flow_service.py
git commit -m "feat: wire evaluator agent into review flow service"
```

### Task 5: Add default workspace/API evaluator wiring regression

**Files:**
- Modify: `review_gate/http_api.py`
- Modify: `tests/test_http_api.py`

- [ ] **Step 1: Write the failing tests**

Add transport-level regression that proves:

1. default workspace wiring can opt into local evaluator agent
2. fake transport keeps tests offline
3. submit flow response shape stays stable
4. checkpoint continuity still holds

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_http_api.py -q`

Expected: FAIL because default workspace assembly does not yet support local evaluator wiring.

- [ ] **Step 3: Write minimal implementation**

Add optional wiring similar to Project Agent:

1. constructor parameters
2. environment variable switches
3. fake-transport compatibility for tests

Do not make live evaluator usage the default yet.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_http_api.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add review_gate/http_api.py tests/test_http_api.py
git commit -m "feat: add evaluator agent workspace wiring"
```

### Task 6: Run focused regression and optional live smoke

**Files:**
- No new source files required
- Reuse current tests plus a one-off local smoke command

- [ ] **Step 1: Run focused stable regression**

Run:

```bash
python -m pytest tests/test_evaluator_agent_prompt_builder.py tests/test_evaluator_agent_assessment_client.py tests/test_evaluator_agent_response_normalizer.py tests/test_review_flow_service.py tests/test_http_api.py -q
```

Expected: PASS

- [ ] **Step 2: Run broader checkpoint regression**

Run:

```bash
python -m pytest tests/test_project_agent_prompt_builder.py tests/test_project_agent_question_generation_client.py tests/test_project_agent_response_normalizer.py tests/test_evaluator_agent_prompt_builder.py tests/test_evaluator_agent_assessment_client.py tests/test_evaluator_agent_response_normalizer.py tests/test_review_flow_service.py tests/test_http_api.py -q
```

Expected: PASS

- [ ] **Step 3: Run one opt-in live smoke**

Use local runtime config only.
Run a one-off script or REPL command that:

1. constructs the local evaluator client
2. sends a real answer evaluation request
3. normalizes the provider output
4. verifies the normalized structure is consumable by `ReviewFlowService`

Expected:

1. live provider returns content successfully
2. output can be normalized
3. no schema/DTO widening is required

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "test: verify evaluator agent llm assessment path"
```

Before committing, remove any accidental additions from:

1. `.env/`
2. temporary review directories
3. personal scratch files

---

## Risks To Watch

1. provider compatibility may differ slightly from Project Agent even on the same gateway
2. raw evaluator output may be much noisier than question generation output
3. evidence strings may drift into formats that downstream checkpoint code does not expect
4. normalizer may overfit to one prompt version and become brittle
5. service wiring may accidentally re-thicken `ReviewFlowService`

---

## Minimal Success Definition

This stage is successful when:

1. `submit_answer` can use a real LLM-backed evaluator path
2. malformed evaluator output is stopped before checkpoint persistence
3. facts synthesis still works without schema changes
4. fake regression remains stable
5. one opt-in live smoke succeeds with the local provider config

---

## Self-Review

### Spec coverage

This plan covers:

1. Evaluator Agent 接入
2. continued `Evaluation -> Facts` boundary
3. fake regression + opt-in live smoke
4. more grounded downstream issue surfacing

No Graph or Maintenance work was included.

### Placeholder scan

No `TODO`, `TBD`, or “similar to above” placeholders remain.

### Type consistency

The plan keeps the current stable assessment shape and does not introduce a parallel evaluator DTO contract.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-12-evaluator-agent-llm-assessment-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
