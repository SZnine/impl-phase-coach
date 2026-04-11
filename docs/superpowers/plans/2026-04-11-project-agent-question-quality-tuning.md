# 2026-04-11 Project Agent Question Quality Tuning Plan

## Why This Stage Exists

The Project Agent is now truly connected to a live provider-backed generation path.
The main problem has shifted:

1. question generation is no longer blocked by runtime integration
2. the remaining weakness is question quality
3. the current output still tends to collapse toward overly similar `core`-style questions

That means the next highest-value work is no longer provider integration.
It is quality shaping:

1. stronger project grounding
2. stronger interview realism
3. clearer difficulty layering
4. less abstract drift

---

## Stage Goal

Tune the Project Agent so that generated question sets feel closer to a real interviewer plus a real project-driving coach.

The generated set should reliably contain a mix of:

1. project-grounded questions
2. interview fundamentals
3. mid-level implementation / design questions
4. higher-level tradeoff / failure-mode questions

This stage is not about adding more infrastructure.
It is about improving the quality and shape of the already-live generation path.

---

## Stage Deliverables

1. Improved prompt rules for question mix and coverage
2. Improved normalization rules for question-level classification
3. Regression tests that lock question quality expectations more tightly
4. A small evaluation rubric for generated question sets

---

## Stage Exit Conditions

1. generated question sets no longer collapse into mostly one level
2. question sets reliably include project-specific content
3. question sets reliably include interview-style fundamentals
4. at least one mid-level or higher-level question appears when `max_questions >= 3`
5. the existing generation/checkpoint pipeline remains stable

---

## Relevant Boundaries

This stage is only about:

1. prompt quality
2. output shaping
3. question-level assignment quality
4. quality regressions

This stage is not about:

1. evaluator LLM integration
2. Graph / Maintenance
3. schema changes
4. checkpoint ownership changes
5. transport DTO redesign

The key boundary is:

`We are improving the quality of generated questions, not redesigning the generation pipeline.`

---

## Knowledge Priorities

### High priority

1. Prompt contract tuning
   - because the current quality problem starts with model instruction strength
2. Layered question taxonomy
   - because the system needs project + interview + mid/high-level coverage, not just arbitrary variation
3. Output-level classification heuristics
   - because live model responses will not always label difficulty or type cleanly

### Medium priority

1. lightweight quality scoring
2. anti-collapse prompt patterns
3. coverage-gap detection

### Low priority for this stage

1. evaluator integration
2. graph-aware generation
3. advanced retrieval
4. token optimization

---

## Quality Problems To Fix

### 1. Level collapse

Current issue:

- multiple generated questions can normalize to the same `core` level

Desired behavior:

- the set should spread across `core`, `why`, and `abstract` more intentionally
- not every question needs a different level, but there should be meaningful layering

### 2. Too much abstraction

Current issue:

- even good prompts can drift toward generic architecture discussion

Desired behavior:

- at least part of the set must directly reference the current project, code boundaries, migration choices, or concrete implementation tradeoffs

### 3. Weak interview realism

Current issue:

- current prompts still over-index on architecture coaching tone

Desired behavior:

- include questions a real interviewer would plausibly ask:
  - fundamentals
  - implementation detail
  - tradeoff reasoning
  - failure-mode follow-ups

### 4. Weak category observability

Current issue:

- we currently check response shape better than question quality

Desired behavior:

- test fixtures should prove that the set contains the intended category mix

---

## Target Question Taxonomy

The Project Agent should target four categories explicitly.

### A. Project-grounded

Examples:

- Why was `ReviewFlowService` split in two phases instead of one?
- Why does the first migration checkpoint stop at `Facts`?
- What breaks if generated-chain resolution and checkpoint writing are mixed again?

### B. Interview fundamentals

Examples:

- What is the difference between append-only records and mutable current state?
- Why separate transport ids from durable ids?
- When should a system use real foreign keys versus logical references?

### C. Mid-level implementation / design

Examples:

- Why extract orchestration owners before expanding Graph?
- How do you protect a checkpoint pipeline from malformed LLM output?
- Why is response normalization a separate layer from provider calling?

### D. Higher-level tradeoff / failure-mode

Examples:

- What migration risks appear when a new LLM provider is introduced into a partially refactored system?
- How would you detect that a provider is returning schema-drifting output before it corrupts persisted records?
- When should a system stop extending a transitional owner and introduce a new application service boundary?

---

## Quality Rubric

The generated question set should be evaluated against a simple rubric.

### 1. Project grounding

Questions should mention one or more of:

- the current migration checkpoint
- concrete module names
- current branch decisions
- real persistence / orchestration / compatibility tradeoffs

### 2. Interview realism

Questions should sound plausibly askable by an interviewer, not only by an architecture planner.

### 3. Level spread

The set should not collapse into a single level unless `max_questions` is very small.

### 4. Actionability

Questions should be answerable against:

1. current code
2. current architecture decisions
3. standard backend/system design knowledge

### 5. Safety for current pipeline

The questions still need to normalize into the current stable shape without widening downstream schema.

---

## Planned Implementation Tasks

### Task 1: Strengthen the prompt builder

Files:

- Modify: `review_gate/project_agent_prompt_builder.py`
- Modify: `tests/test_project_agent_prompt_builder.py`

Goal:

Make the prompt more forceful about:

1. category mix
2. level spread
3. project specificity
4. avoiding generic-only outputs

Expected direction:

- add explicit category quotas or minimums
- add stronger “bad output” examples
- make interview realism a first-class rule

---

### Task 2: Upgrade the normalizer’s question-level mapping

Files:

- Modify: `review_gate/project_agent_response_normalizer.py`
- Modify: `tests/test_project_agent_response_normalizer.py`

Goal:

Reduce level collapse by improving how question level is inferred.

Expected direction:

1. prefer explicit question metadata when present
2. use stronger mapping rules for `difficulty`
3. optionally infer category/level from lexical cues when safe

Constraint:

- do not widen the stable output shape yet unless truly necessary

---

### Task 3: Add question quality regressions at the service layer

Files:

- Modify: `tests/test_review_flow_service.py`

Goal:

Prove that a live-like Project Agent response can produce:

1. at least one project-grounded question
2. at least one fundamentals-style question
3. at least one mid-level or high-level question when the set is large enough

This does not mean testing the live provider itself every time.
It means adding more realistic raw provider fixtures and validating the normalized result.

---

### Task 4: Add a small opt-in live quality smoke

Files:

- Optional new test helper or script under `scripts/` or `tests/` if needed

Goal:

Use the real provider path to spot-check whether the tuned prompt produces a better layered set.

This should remain:

1. opt-in
2. not part of default regression
3. focused on human inspection plus a few basic assertions

---

## Frozen Boundary For This Plan

1. This plan only improves Project Agent question quality
2. It does not introduce evaluator LLM integration
3. It does not change checkpoint schema
4. It does not add Graph or Maintenance work
5. It does not redesign HTTP or workspace DTOs

---

## Review Checkpoints

1. After Task 1, verify the prompt explicitly demands category mix and interview realism
2. After Task 2, verify the normalizer no longer collapses most outputs into `core`
3. After Task 3, verify the service-layer regressions reflect realistic quality expectations
4. After Task 4, verify live smoke improves perceived question quality without breaking the stable pipeline

---

## Recommended Commit Sequence

1. `refactor: strengthen project agent prompt contract`
2. `fix: improve project agent question level normalization`
3. `test: add project agent quality regressions`
4. `test: add opt-in live quality smoke`

---

## Completion Standard

This stage is complete when:

1. live Project Agent generation still works
2. generated sets are noticeably more project-grounded and interview-realistic
3. question-level spread is visibly improved
4. the stable generation/checkpoint pipeline still holds
