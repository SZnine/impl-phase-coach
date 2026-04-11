import pytest

from review_gate.project_agent_response_normalizer import ProjectAgentResponseNormalizer


def test_response_normalizer_maps_llm_output_to_stable_question_shape() -> None:
    normalizer = ProjectAgentResponseNormalizer()

    response = normalizer.normalize(
        request={
            "request_id": "req-1",
            "current_decisions": ["split generation orchestration"],
            "source_refs": ["docs/spec.md"],
        },
        raw_result={
            "request_id": "req-1",
            "raw_content": """
            {
              "questions": [
                {
                  "id": "q-1",
                  "prompt": "Why did we split generation-side orchestration first?",
                  "intent": "Check migration reasoning.",
                  "difficulty": "intermediate"
                }
              ],
              "generation_summary": "Generated 1 mixed question.",
              "coverage_notes": ["project-grounded"],
              "warnings": [],
              "confidence": 0.88
            }
            """,
        },
    )

    assert response["request_id"] == "req-1"
    assert response["generation_summary"] == "Generated 1 mixed question."
    assert response["coverage_notes"] == ["project-grounded"]
    assert response["confidence"] == 0.88
    assert response["questions"] == [
        {
            "question_id": "q-1",
            "question_level": "why",
            "prompt": "Why did we split generation-side orchestration first?",
            "intent": "Check migration reasoning.",
            "expected_signals": ["split generation orchestration"],
            "source_context": ["docs/spec.md"],
        }
    ]


def test_response_normalizer_prefers_explicit_question_level_and_source_fields() -> None:
    normalizer = ProjectAgentResponseNormalizer()

    response = normalizer.normalize(
        request={
            "request_id": "req-2",
            "current_decisions": ["unused fallback"],
            "source_refs": ["docs/ignored.md"],
        },
        raw_result={
            "raw_content": """
            {
              "questions": [
                {
                  "question_id": "custom-q",
                  "question_level": "abstract",
                  "prompt": "What migration failure happens if transport and durable ids are mixed?",
                  "expected_signals": ["transport ids", "durable ids"],
                  "source_context": ["review_flow_service.py"]
                }
              ]
            }
            """,
        },
    )

    assert response["questions"][0]["question_id"] == "q-1"
    assert response["questions"][0]["question_level"] == "abstract"
    assert response["questions"][0]["expected_signals"] == ["transport ids", "durable ids"]
    assert response["questions"][0]["source_context"] == ["review_flow_service.py"]


def test_response_normalizer_rejects_invalid_json() -> None:
    normalizer = ProjectAgentResponseNormalizer()

    with pytest.raises(ValueError, match="not valid JSON"):
        normalizer.normalize(
            request={"request_id": "req-3"},
            raw_result={"raw_content": "not-json"},
        )


def test_response_normalizer_rejects_missing_questions_list() -> None:
    normalizer = ProjectAgentResponseNormalizer()

    with pytest.raises(ValueError, match="missing questions"):
        normalizer.normalize(
            request={"request_id": "req-4"},
            raw_result={"raw_content": '{"questions": []}'},
        )


def test_response_normalizer_rejects_question_without_prompt() -> None:
    normalizer = ProjectAgentResponseNormalizer()

    with pytest.raises(ValueError, match="missing prompt"):
        normalizer.normalize(
            request={"request_id": "req-5"},
            raw_result={"raw_content": '{"questions":[{"id":"q-1"}]}'},
        )
