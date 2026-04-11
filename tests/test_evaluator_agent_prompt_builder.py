from review_gate.evaluator_agent_prompt_builder import EvaluatorAgentPromptBuilder


def test_evaluator_agent_prompt_builder_includes_request_context_and_answer_text() -> None:
    builder = EvaluatorAgentPromptBuilder()

    prompt = builder.build(
        {
            "request_id": "req-17",
            "project_context": "review_gate evaluator rollout",
            "stage_context": "phase 1 evaluator prompt builder",
            "question_context": "Should the evaluator flag answer drift before persistence?",
            "answer_text": "It should inspect the answer against the actual implementation boundaries.",
            "current_decisions": ["keep prompt builder provider-free", "keep output contract structured"],
            "boundary_focus": ["prompt construction", "evaluation scope"],
        }
    )

    assert "Request id: req-17" in prompt.user_prompt
    assert "Project context: review_gate evaluator rollout" in prompt.user_prompt
    assert "Stage context: phase 1 evaluator prompt builder" in prompt.user_prompt
    assert "Question context: Should the evaluator flag answer drift before persistence?" in prompt.user_prompt
    assert "Answer text: It should inspect the answer against the actual implementation boundaries." in prompt.user_prompt
    assert "Current decisions: keep prompt builder provider-free, keep output contract structured" in prompt.user_prompt
    assert "Boundary focus: prompt construction, evaluation scope" in prompt.user_prompt


def test_evaluator_agent_prompt_builder_allows_grounded_lower_level_issues() -> None:
    builder = EvaluatorAgentPromptBuilder()

    prompt = builder.build(
        {
            "request_id": "req-18",
            "project_context": "review_gate evaluator rollout",
            "stage_context": "phase 1 evaluator prompt builder",
            "question_context": "What should the evaluator inspect?",
            "answer_text": "It should cover implementation details and test coverage.",
        }
    )

    assert "library/API misuse" in prompt.system_prompt
    assert "method misuse" in prompt.system_prompt
    assert "test gaps" in prompt.system_prompt
    assert "boundary confusion" in prompt.system_prompt
    assert "migration/compatibility risk" in prompt.system_prompt


def test_evaluator_agent_prompt_builder_exposes_structured_output_contract() -> None:
    builder = EvaluatorAgentPromptBuilder()

    prompt = builder.build(
        {
            "request_id": "req-19",
            "project_context": "review_gate evaluator rollout",
            "stage_context": "phase 1 evaluator prompt builder",
            "question_context": "What should the evaluator return?",
            "answer_text": "A structured assessment.",
        }
    )

    assert prompt.output_contract["verdict"] == "pass|continue_probing|redirect_to_learning"
    assert prompt.output_contract["dimension_scores"] == {
        "correctness": "0-5",
        "boundary_awareness": "0-5",
        "implementation_depth": "0-5",
        "test_quality": "0-5",
        "migration_compatibility": "0-5",
    }
    assert prompt.output_contract["core_gaps"] == ["string"]
    assert prompt.output_contract["misconceptions"] == ["string"]
    assert prompt.output_contract["evidence"] == ["string"]
    assert prompt.output_contract["action_recommendation"] == "string"
