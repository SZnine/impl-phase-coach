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
    assert "Do not return a freeform essay without structured assessment fields." in prompt.system_prompt


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

    assert prompt.output_contract == {
        "request_id": "string",
        "assessment": {
            "score_total": "0-1",
            "dimension_scores": {
                "correctness": "0-5",
                "reasoning": "0-5",
                "decision_awareness": "0-5",
                "boundary_awareness": "0-5",
                "stability": "0-5",
            },
            "verdict": "pass|continue_probing|redirect_to_learning",
            "core_gaps": ["string"],
            "misconceptions": ["string"],
            "evidence": ["string"],
            "support_basis_tags": [
                {
                    "basis_key": "state_modeling|boundary_awareness|decision_awareness",
                    "source_label": "string",
                    "source_node_type": "foundation|concept|method",
                    "target_label": "string matching one core_gaps item",
                    "target_node_type": "concept|method|decision",
                }
            ],
        },
        "recommended_action": "string",
        "recommended_follow_up_questions": ["string"],
        "learning_recommendations": ["string"],
        "warnings": ["string"],
        "confidence": "0-1",
    }


def test_evaluator_agent_prompt_builder_explicitly_forbids_flat_or_alternative_dimension_shapes() -> None:
    builder = EvaluatorAgentPromptBuilder()

    prompt = builder.build(
        {
            "request_id": "req-20",
            "project_context": "review_gate evaluator rollout",
            "stage_context": "phase 2 live provider alignment",
            "question_context": "How should the evaluator shape its JSON?",
            "answer_text": "Return the canonical nested assessment envelope.",
        }
    )

    assert "Keep verdict and dimension_scores inside the nested assessment object" in prompt.system_prompt
    assert "Use only the canonical dimension keys" in prompt.system_prompt
    assert "Do not invent alternative keys such as current_stage_boundary_alignment" in prompt.user_prompt


def test_evaluator_agent_prompt_builder_requests_support_basis_tags_for_graph_relations() -> None:
    builder = EvaluatorAgentPromptBuilder()

    prompt = builder.build(
        {
            "request_id": "req-21",
            "project_context": "review_gate graph smoke",
            "stage_context": "live evaluator should produce graph-support provenance",
            "question_context": "What structured fields should support graph relations?",
            "answer_text": "The API boundary is weak but boundary discipline can support it.",
        }
    )

    assert "assessment.support_basis_tags" in prompt.system_prompt
    assert "target_label must match one item from assessment.core_gaps" in prompt.system_prompt
    assert "support_basis_tags" in prompt.user_prompt
    assert "source_label" in prompt.user_prompt
    assert "target_node_type" in prompt.user_prompt


def test_evaluator_agent_prompt_builder_requests_chinese_learner_visible_text() -> None:
    builder = EvaluatorAgentPromptBuilder()

    prompt = builder.build(
        {
            "request_id": "req-22",
            "project_context": "review_gate full live workflow",
            "stage_context": "Chinese learner-facing assessment output",
            "question_context": "Why must transport question ids stay stable?",
            "answer_text": "They must stay stable across generation and submit.",
        }
    )

    assert "Write core_gaps, misconceptions, follow-up questions, learning recommendations, and warnings in Simplified Chinese." in prompt.system_prompt
    assert "Keep code identifiers, module names, API paths, command snippets, and established technical terms unchanged." in prompt.system_prompt
