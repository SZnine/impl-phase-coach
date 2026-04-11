# 2026-04-11 Project Agent / LLM Question Generation Implementation Plan

## Why This Stage Exists

We have already completed two critical preconditions:

1. The first migration checkpoint is running:
   - `Workflow -> Question -> Answer -> Evaluation -> Facts`
2. The heaviest generation-side and submit-side orchestration has been split once out of `ReviewFlowService`.

That means the current bottleneck is no longer schema or checkpoint plumbing.
The next highest-value move is to replace test-stub question generation with a real LLM-backed `Project Agent`, so the system starts receiving more realistic prompts and more realistic variation in question shape.

This stage is not about “adding AI because it sounds advanced”.
It is about making the development environment more truthful earlier, so the next problems surface now instead of after Graph / Maintenance work has already started.

---

## Stage Goal

Introduce a real LLM-backed question generation path for `generate_question_set`, while keeping the existing checkpoint chain and transport contract stable.

The generated questions must no longer be only abstract architecture prompts.
They must intentionally mix:

1. project-specific questions
2. interview-style fundamentals
3. mid-level design and implementation questions
4. higher-level tradeoff / migration / failure-mode questions

---

## Stage Deliverables

1. A new LLM-backed `ProjectAgentQuestionGenerationClient` or equivalent adapter
2. A prompt contract for question generation
3. A response normalization layer that preserves the current `generate_question_set` response shape
4. Focused tests that prove:
   - the LLM path can be called safely
   - malformed LLM output is normalized or rejected cleanly
   - checkpoint persistence still works unchanged

---

## Stage Exit Conditions

1. `ReviewFlowService.generate_question_set` can run with a real LLM-backed generation client
2. Existing checkpoint persistence and event publishing still pass
3. Generated questions are not purely abstract; they include project + interview-layer structure
4. HTTP / workspace DTO shape is unchanged

---

## Relevant Boundaries

This stage is only about:

1. generation client replacement
2. prompt and output normalization
3. preserving the current checkpoint chain

This stage is not about:

1. evaluator LLM integration
2. Graph / Maintenance
3. schema changes
4. focus / explanation
5. changing the response shape of `generate_question_set`

The most important boundary is:

`LLM output is not allowed to directly redefine transport or storage contracts.`

It must be normalized into the already-stable generation/checkpoint pipeline.

---

## Knowledge Priorities

### High priority

1. Prompt contract design
   - because the model must produce questions that are both project-relevant and interview-useful
2. Output normalization
   - because raw LLM output is not trustworthy enough to flow directly into checkpoint persistence
3. Fault-tolerant adapter design
   - because the first LLM integration should fail safely without corrupting the main generation chain

### Medium priority

1. Prompt templating
2. retry / fallback strategy
3. model-specific client wiring

### Low priority for this stage

1. token optimization
2. advanced retrieval
3. long-term prompt governance
4. Graph-aware question planning

---

## Target Question Mix

The default question set should intentionally contain a mix of four categories.

### 1. Project-grounded questions

Questions tied directly to the current project and branch reality.

Examples:

- Why was `ReviewFlowService` too heavy before the recent orchestration split?
- What problem is solved by extracting `QuestionCheckpointWriter` and `QuestionSetGenerationPublisher`?
- Why is the first migration checkpoint intentionally stopping at `Facts` instead of going straight to `Graph`?

### 2. Interview fundamentals

Questions an interviewer could reasonably ask about the code or architecture choices.

Examples:

- Why use append-only records for evaluation and facts?
- What is the difference between a real foreign key and a logical reference in this system?
- Why should `UserNodeState` be current-state data instead of append-only history?

### 3. Mid-level implementation / design questions

Questions that require explaining design and engineering tradeoffs beyond textbook basics.

Examples:

- Why split orchestration owners before introducing real LLM generation?
- How do you preserve transport compatibility while changing internal persistence owners?
- Why is `GraphRevision` versioned derived state instead of mutable current state?

### 4. Higher-level tradeoff / failure-mode questions

Questions that force reasoning about migration, risk, compatibility, and long-term maintainability.

Examples:

- What can go wrong if semantic ids and durable ids are mixed in a migration?
- Why is a strangler-style migration safer here than a big-bang rewrite?
- When should a system introduce a dedicated maintenance agent instead of extending an existing service?

---

## Output Contract

The LLM-backed generation client must normalize into the current shape already consumed by the system.

Minimum normalized response:

```json
{
  "questions": [
    {
      "id": "q-1",
      "prompt": "string",
      "type": "open",
      "intent": "string",
      "difficulty": "basic|intermediate|advanced"
    }
  ]
}
```

Notes:

1. The LLM is allowed to emit richer structure internally.
2. The adapter is responsible for coercing that richer structure into the stable response shape.
3. If the output cannot be normalized safely, the adapter must fail clearly before checkpoint writing starts.

---

## Proposed Module Boundary

### Keep

- `ReviewFlowService.generate_question_set`
  - remains transport-facing orchestration owner

### Add

- `review_gate/project_agent_question_generation_client.py`
  - LLM-backed client / adapter
- `review_gate/project_agent_prompt_builder.py`
  - prompt assembly for project + interview question mix
- `review_gate/project_agent_response_normalizer.py`
  - normalization and validation before the existing checkpoint chain

This keeps the LLM-specific variability out of `ReviewFlowService`.

---

## Minimal Implementation Strategy

### Task 1: Add the prompt builder

Files:

- New: `review_gate/project_agent_prompt_builder.py`
- New: `tests/test_project_agent_prompt_builder.py`

Goal:

Build a deterministic prompt input from:

1. project id
2. stage id
3. current branch / implementation context if already available
4. explicit question-mix rules

Key requirement:

The prompt must explicitly instruct the model to produce:

1. project-grounded questions
2. fundamental interview questions
3. mid-level design questions
4. higher-level tradeoff questions

It must also explicitly forbid producing only abstract questions.

---

### Task 2: Add the LLM client adapter

Files:

- New: `review_gate/project_agent_question_generation_client.py`
- New: `tests/test_project_agent_question_generation_client.py`

Goal:

Call the real LLM and return raw output to the normalizer layer.

This layer should own:

1. API key loading
2. provider call
3. model invocation
4. minimal transport error handling

This layer should not own:

1. checkpoint writing
2. event publishing
3. response shape normalization into final checkpoint records

---

### Task 3: Add the response normalizer

Files:

- New: `review_gate/project_agent_response_normalizer.py`
- New: `tests/test_project_agent_response_normalizer.py`

Goal:

Normalize raw LLM output into the stable `questions` response shape.

This layer must:

1. reject empty / malformed output
2. coerce question fields where safe
3. enforce a bounded stable shape for downstream persistence

This is the main protection boundary between LLM variability and the checkpoint chain.

---

### Task 4: Wire the LLM client into `ReviewFlowService`

Files:

- Modify: `review_gate/review_flow_service.py`
- Modify: `tests/test_review_flow_service.py`

Goal:

Allow `generate_question_set` to use the new Project Agent path while preserving:

1. response shape
2. checkpoint persistence
3. question-set event publishing

At this step, `ReviewFlowService` should still orchestrate:

1. call client
2. normalize output
3. delegate checkpoint writer
4. delegate event publisher

---

### Task 5: Add transport-level regression

Files:

- Modify: `tests/test_http_api.py`
- Modify: `tests/test_workspace_api.py` only if needed

Goal:

Prove the system still behaves correctly when a real LLM-backed generation path is plugged in.

The test focus is:

1. response shape compatibility
2. checkpoint persistence continuity
3. malformed output handling

---

## API Key Handling

You said the key is already available under `key/`.
That lowers adoption friction, but this stage should still keep the key boundary explicit.

Rules:

1. The adapter may read the key from the project key location or env wiring
2. The key file itself must not be moved into business logic
3. Tests must not depend on the real key unless we explicitly run an opt-in live test

So the first implementation should support:

1. mocked/injected client tests by default
2. an optional live smoke path later

---

## Frozen Boundary For This Plan

1. This plan only introduces real LLM-backed question generation
2. It does not yet introduce evaluator LLM integration
3. It does not yet introduce Graph / Maintenance work
4. It does not change the checkpoint schema
5. It does not change HTTP / workspace DTO shape

---

## Review Checkpoints

1. After Task 1, verify the prompt explicitly enforces the mixed question set
2. After Task 2, verify the LLM client adapter is isolated from checkpoint logic
3. After Task 3, verify malformed LLM output cannot corrupt the stable generation chain
4. After Task 4, verify `ReviewFlowService` still looks like transport orchestration, not LLM parsing logic
5. After Task 5, verify transport and checkpoint regressions still pass

---

## Commit Sequence

Recommended commit sequence:

1. `feat: add project agent prompt builder`
2. `feat: add llm question generation adapter`
3. `feat: normalize project agent question output`
4. `refactor: wire project agent generation into review flow`
5. `test: freeze llm-backed generation boundary`

---

## Completion Standard

This stage is complete when:

1. the system can call a real LLM-backed Project Agent for question generation
2. the generated set includes both project-grounded and interview-style questions
3. the normalized output still fits the current generation/checkpoint pipeline
4. existing downstream persistence and transport shape remain stable
