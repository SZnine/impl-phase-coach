import pytest

from review_gate.evaluator_agent_response_normalizer import EvaluatorAgentResponseNormalizer


def test_evaluator_response_normalizer_maps_raw_json_to_stable_assessment_shape() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    response = normalizer.normalize(
        request={"request_id": "req-1"},
        raw_result={
            "request_id": "req-1",
            "raw_content": """
            {
              "assessment": {
                "score_total": "0.72",
                "dimension_scores": {
                  "correctness": "3",
                  "reasoning": 2,
                  "decision_awareness": "2",
                  "boundary_awareness": 3,
                  "stability": "2"
                },
                "verdict": "partial",
                "core_gaps": ["Needs deeper boundary explanation."],
                "misconceptions": [],
                "evidence": ["Quoted answer sentence."],
                "support_basis_tags": [
                  {
                    "source_label": "Boundary discipline",
                    "source_node_type": "foundation",
                    "target_label": "Needs deeper boundary explanation.",
                    "target_node_type": "method"
                  }
                ]
              },
              "recommended_action": "continue_answering",
              "recommended_follow_up_questions": ["Explain the why again."],
              "learning_recommendations": ["Revisit the stage boundary."],
              "warnings": [],
              "confidence": 0.83
            }
            """,
        },
    )

    assert response == {
        "request_id": "req-1",
        "assessment": {
            "score_total": 0.72,
            "dimension_scores": {
                "correctness": 3,
                "reasoning": 2,
                "decision_awareness": 2,
                "boundary_awareness": 3,
                "stability": 2,
            },
            "verdict": "partial",
            "core_gaps": ["Needs deeper boundary explanation."],
            "misconceptions": [],
            "evidence": ["Quoted answer sentence."],
            "support_basis_tags": [
                {
                    "source_label": "Boundary discipline",
                    "source_node_type": "foundation",
                    "target_label": "Needs deeper boundary explanation.",
                    "target_node_type": "method",
                }
            ],
        },
        "recommended_action": "continue_answering",
        "recommended_follow_up_questions": ["Explain the why again."],
        "learning_recommendations": ["Revisit the stage boundary."],
        "warnings": [],
        "confidence": 0.83,
    }


def test_evaluator_response_normalizer_rejects_invalid_json() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    with pytest.raises(ValueError, match="not valid JSON"):
        normalizer.normalize(
            request={"request_id": "req-2"},
            raw_result={"raw_content": "not-json"},
        )


def test_evaluator_response_normalizer_rejects_missing_required_fields() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    with pytest.raises(ValueError, match="missing assessment"):
        normalizer.normalize(
            request={"request_id": "req-3"},
            raw_result={"raw_content": '{"recommended_action":"continue_answering"}'},
        )


def test_evaluator_response_normalizer_coerces_evidence_to_string_list() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    response = normalizer.normalize(
        request={"request_id": "req-4"},
        raw_result={
            "raw_content": """
            {
              "assessment": {
                "score_total": 0.4,
                "dimension_scores": {
                  "correctness": 1,
                  "reasoning": 1,
                  "decision_awareness": 1,
                  "boundary_awareness": 1,
                  "stability": 1
                },
                "verdict": "weak",
                "core_gaps": ["Wrong transaction boundary."],
                "misconceptions": [],
                "evidence": [
                  {"summary": "Used sqlite connection outside transaction scope."},
                  {"text": "No rollback path was shown."},
                  "Missed negative-path test."
                ]
              },
              "recommended_action": "redirect_to_learning"
            }
            """,
        },
    )

    assert response["assessment"]["evidence"] == [
        "Used sqlite connection outside transaction scope.",
        "No rollback path was shown.",
        "Missed negative-path test.",
    ]


def test_evaluator_response_normalizer_coerces_dimension_scores_to_canonical_five_dimensions() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    response = normalizer.normalize(
        request={"request_id": "req-5"},
        raw_result={
            "raw_content": """
            {
              "assessment": {
                "score_total": 0.61,
                "dimension_scores": {
                  "correctness": "4",
                  "reasoning": "3",
                  "boundary_awareness": 2,
                  "extra_dimension": 99
                },
                "verdict": "partial",
                "core_gaps": [],
                "misconceptions": [],
                "evidence": []
              },
              "recommended_action": "continue_answering"
            }
            """,
        },
    )

    assert response["assessment"]["dimension_scores"] == {
        "correctness": 4,
        "reasoning": 3,
        "decision_awareness": 0,
        "boundary_awareness": 2,
        "stability": 0,
    }


def test_evaluator_response_normalizer_maps_grounded_issues_into_core_gaps_and_misconceptions() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    response = normalizer.normalize(
        request={"request_id": "req-6"},
        raw_result={
            "raw_content": """
            {
              "assessment": {
                "score_total": 0.33,
                "dimension_scores": {
                  "correctness": 1,
                  "reasoning": 1,
                  "decision_awareness": 1,
                  "boundary_awareness": 1,
                  "stability": 1
                },
                "verdict": "weak",
                "grounded_issues": [
                  "Misused sqlite transaction handling.",
                  "No regression test for malformed SSE chunks."
                ],
                "misconceptions": [
                  "Treats response_format as optional provider contract."
                ],
                "evidence": ["Used provider call without stable JSON contract."]
              },
              "recommended_action": "redirect_to_learning",
              "warnings": ["Needs more concrete evidence."]
            }
            """,
        },
    )

    assert response["assessment"]["core_gaps"] == [
        "Misused sqlite transaction handling.",
        "No regression test for malformed SSE chunks.",
    ]
    assert response["assessment"]["misconceptions"] == [
        "Treats response_format as optional provider contract."
    ]


def test_evaluator_response_normalizer_accepts_flat_live_provider_shape() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    response = normalizer.normalize(
        request={"request_id": "req-live-1"},
        raw_result={
            "request_id": "req-live-1",
            "raw_content": """
            {
              "request_id": "req-live-1",
              "verdict": "partially_satisfactory",
              "dimension_scores": {
                "current_stage_boundary_alignment": 0.78,
                "concrete_implementation_risk_identification": 0.83,
                "context_fit": 0.74,
                "completeness": 0.58,
                "implementation_grounding": 0.87
              },
              "core_gaps": [
                {
                  "gap": "Does not explicitly state the current-stage boundary.",
                  "why_it_matters": "The question asked for the current-stage boundary."
                },
                {
                  "gap": "Does not mention normalization-before-checkpoint-writes."
                }
              ],
              "misconceptions": [
                {
                  "item": "No major misconception detected.",
                  "assessment": "Directionally consistent."
                }
              ],
              "evidence": {
                "from_answer": [
                  "Used requests stream=True.",
                  "Mixed provider contract handling into the service."
                ],
                "from_context": [
                  "Graph and Maintenance should be excluded."
                ]
              },
              "action_recommendation": "continue_answering"
            }
            """,
        },
    )

    assert response["assessment"]["verdict"] == "partial"
    assert response["assessment"]["dimension_scores"] == {
        "correctness": 4,
        "reasoning": 4,
        "decision_awareness": 4,
        "boundary_awareness": 4,
        "stability": 3,
    }
    assert response["assessment"]["core_gaps"] == [
        "Does not explicitly state the current-stage boundary.",
        "Does not mention normalization-before-checkpoint-writes.",
    ]
    assert response["assessment"]["misconceptions"] == ["No major misconception detected."]
    assert response["assessment"]["evidence"] == [
        "Used requests stream=True.",
        "Mixed provider contract handling into the service.",
        "Graph and Maintenance should be excluded.",
    ]
    assert response["recommended_action"] == "continue_answering"
    assert response["request_id"] == "req-live-1"


def test_evaluator_response_normalizer_maps_fail_verdict_and_uses_score_total_as_confidence_fallback() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    response = normalizer.normalize(
        request={"request_id": "req-live-2"},
        raw_result={
            "request_id": "req-live-2",
            "raw_content": """
            {
              "verdict": "fail",
              "score_total": 0.41,
              "dimension_scores": {
                "correctness": 2,
                "reasoning": 2,
                "decision_awareness": 1,
                "boundary_awareness": 1,
                "stability": 2
              },
              "core_gaps": ["Missed malformed chunk regression."],
              "misconceptions": [],
              "evidence": ["Skipped provider failure-path testing."]
            }
            """,
        },
    )

    assert response["assessment"]["verdict"] == "weak"
    assert response["recommended_action"] == "redirect_to_learning"
    assert response["confidence"] == 0.41


def test_evaluator_response_normalizer_maps_insufficient_verdict_to_weak() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    response = normalizer.normalize(
        request={"request_id": "req-live-2b"},
        raw_result={
            "request_id": "req-live-2b",
            "raw_content": """
            {
              "assessment": {
                "verdict": "insufficient",
                "dimension_scores": {
                  "correctness": 0.4,
                  "reasoning": 0.4,
                  "decision_awareness": 0.2,
                  "boundary_awareness": 0.2,
                  "stability": 0.4
                }
              }
            }
            """,
        },
    )

    assert response["assessment"]["verdict"] == "weak"
    assert response["recommended_action"] == "redirect_to_learning"


def test_evaluator_response_normalizer_treats_integer_dimension_scores_as_five_point_scale() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    response = normalizer.normalize(
        request={"request_id": "req-live-2c"},
        raw_result={
            "request_id": "req-live-2c",
            "raw_content": """
            {
              "assessment": {
                "verdict": "reject",
                "dimension_scores": {
                  "correctness": 1,
                  "reasoning": 2,
                  "decision_awareness": 1,
                  "boundary_awareness": 1,
                  "stability": 1
                }
              }
            }
            """,
        },
    )

    assert response["assessment"]["verdict"] == "weak"
    assert response["assessment"]["dimension_scores"] == {
        "correctness": 1,
        "reasoning": 2,
        "decision_awareness": 1,
        "boundary_awareness": 1,
        "stability": 1,
    }
    assert response["confidence"] == 0.24


def test_evaluator_response_normalizer_uses_top_level_fallback_fields_from_live_provider_shape() -> None:
    normalizer = EvaluatorAgentResponseNormalizer()

    response = normalizer.normalize(
        request={"request_id": "req-live-3"},
        raw_result={
            "request_id": "req-live-3",
            "raw_content": """
            {
              "assessment": {
                "verdict": "partially_sufficient",
                "dimension_scores": {
                  "correctness": 0.68,
                  "reasoning": 0.72,
                  "decision_awareness": 0.70,
                  "boundary_awareness": 0.64,
                  "stability": 0.66
                }
              },
              "core_gaps": [
                "Does not clearly call out Graph and Maintenance as out of scope."
              ],
              "misconceptions": [
                "Leans toward implementation status reporting over boundary explanation."
              ],
              "evidence": [
                "Boundary focus mentions provider contract vs service boundary."
              ],
              "action_recommendation": [
                "Revise the answer to state the current-stage boundary explicitly."
              ]
            }
            """,
        },
    )

    assert response["assessment"]["verdict"] == "partial"
    assert response["assessment"]["core_gaps"] == [
        "Does not clearly call out Graph and Maintenance as out of scope."
    ]
    assert response["assessment"]["misconceptions"] == [
        "Leans toward implementation status reporting over boundary explanation."
    ]
    assert response["assessment"]["evidence"] == [
        "Boundary focus mentions provider contract vs service boundary."
    ]
    assert response["recommended_action"] == (
        "Revise the answer to state the current-stage boundary explicitly."
    )
    assert response["confidence"] == 0.68
