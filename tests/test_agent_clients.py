from review_gate.agent_clients import AssessmentAgentClient, QuestionGenerationAgentClient


def test_question_generation_client_returns_structured_response() -> None:
    client = QuestionGenerationAgentClient.for_testing()
    response = client.generate(
        {
            "request_id": "req-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "Task 4 adapter shell",
            "stage_artifacts": [],
            "stage_exit_criteria": [],
            "current_decisions": ["Question, Assessment, Decision split"],
            "key_logic_points": ["structured DTOs"],
            "known_weak_points": [],
            "boundary_focus": ["module vs interface"],
            "question_strategy": "core_and_why",
            "max_questions": 2,
            "source_refs": [],
        }
    )

    assert response["request_id"] == "req-1"
    assert response["questions"]
    assert response["questions"][0]["question_level"] in {"core", "why", "abstract"}
    assert response["generation_summary"]
    assert response["confidence"] > 0


def test_assessment_client_returns_structured_verdict() -> None:
    client = AssessmentAgentClient.for_testing()
    response = client.assess(
        {
            "request_id": "req-2",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "question_id": "q-1",
            "question_level": "core",
            "question_prompt": "Explain the split.",
            "question_intent": "Check current-stage understanding.",
            "expected_signals": ["Question", "Assessment", "Decision"],
            "user_answer": "We split objects to keep state and scoring separate.",
            "source_context": [],
            "current_stage_decisions": [],
            "current_stage_logic_points": [],
            "current_boundary_focus": [],
            "assessment_policy": {"mode": "simple"},
            "history_signals": [],
        }
    )

    assessment = response["assessment"]
    assert response["request_id"] == "req-2"
    assert assessment["verdict"] in {"strong", "partial", "weak"}
    assert "dimension_scores" in assessment
    assert assessment["evidence"]
    assert response["recommended_action"] in {"continue_answering", "deepen", "redirect_to_learning"}