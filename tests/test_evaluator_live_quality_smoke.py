from review_gate.evaluator_live_quality_smoke import (
    EvaluatorLiveQualitySample,
    EvaluatorLiveQualitySmokeResult,
    classify_quality_issues,
    default_evaluator_live_quality_samples,
    format_live_quality_report,
    run_evaluator_live_quality_smoke,
)


def test_default_evaluator_live_quality_samples_cover_strong_weak_and_grounded_cases() -> None:
    samples = default_evaluator_live_quality_samples()

    assert [sample.sample_id for sample in samples] == [
        "strong_concrete",
        "abstract_handwavy",
        "low_level_partial",
    ]
    assert samples[0].expected_verdicts == {"strong", "partial"}
    assert samples[1].expected_verdicts == {"weak"}
    assert samples[2].expected_verdicts == {"partial", "weak"}


def test_classify_quality_issues_flags_verdict_score_conflicts_and_empty_findings() -> None:
    result = EvaluatorLiveQualitySmokeResult(
        sample=EvaluatorLiveQualitySample(
            sample_id="abstract_handwavy",
            question_context="Explain the current-stage boundary.",
            answer_text="Generic architecture answer.",
            expected_verdicts={"weak"},
            score_band=(0.0, 0.45),
            required_gap_keywords=("boundary", "normalization"),
        ),
        normalized={
            "assessment": {
                "verdict": "weak",
                "score_total": 0.88,
                "core_gaps": [],
                "misconceptions": [],
                "evidence": [],
            },
            "confidence": 0.88,
        },
    )

    issues = classify_quality_issues(result)

    assert "score_out_of_expected_band" in issues
    assert "missing_required_gap_keywords" in issues
    assert "empty_evidence" in issues


def test_classify_quality_issues_accepts_reasonable_strong_result() -> None:
    result = EvaluatorLiveQualitySmokeResult(
        sample=EvaluatorLiveQualitySample(
            sample_id="strong_concrete",
            question_context="Explain the current-stage boundary.",
            answer_text="Concrete, boundary-aware answer.",
            expected_verdicts={"strong", "partial"},
            score_band=(0.7, 1.0),
            required_gap_keywords=("workflow", "checkpoint"),
        ),
        normalized={
            "assessment": {
                "verdict": "strong",
                "score_total": 0.92,
                "core_gaps": [
                    "Could tie risks more explicitly to workflow migration.",
                    "Could mention checkpoint ordering failure modes.",
                ],
                "misconceptions": [],
                "evidence": ["Explicitly scoped evaluator-agent integration."],
            },
            "confidence": 0.9,
        },
    )

    issues = classify_quality_issues(result)

    assert issues == []


def test_classify_quality_issues_does_not_require_gap_keywords_when_sample_does_not_ask_for_them() -> None:
    result = EvaluatorLiveQualitySmokeResult(
        sample=EvaluatorLiveQualitySample(
            sample_id="strong_concrete",
            question_context="Explain the current-stage boundary.",
            answer_text="Concrete, boundary-aware answer.",
            expected_verdicts={"strong"},
            score_band=(0.7, 1.0),
            required_gap_keywords=(),
        ),
        normalized={
            "assessment": {
                "verdict": "strong",
                "score_total": 0.92,
                "core_gaps": ["Could be slightly more explicit."],
                "misconceptions": [],
                "evidence": ["Explicitly scoped evaluator-agent integration."],
            },
            "confidence": 0.9,
        },
    )

    assert classify_quality_issues(result) == []


def test_run_evaluator_live_quality_smoke_executes_pipeline_for_each_sample() -> None:
    class FakePromptPackage:
        def __init__(self, sample_id: str) -> None:
            self.system_prompt = f"system:{sample_id}"
            self.user_prompt = f"user:{sample_id}"
            self.output_contract = {"sample_id": sample_id}

    class FakeBuilder:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def build(self, request: dict) -> FakePromptPackage:
            self.calls.append(request)
            return FakePromptPackage(request["request_id"])

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def assess(self, request: dict) -> dict:
            self.calls.append(request)
            return {
                "request_id": request["request_id"],
                "raw_content": '{"assessment":{"verdict":"strong","score_total":0.9,"core_gaps":["workflow checkpoint gap"],"misconceptions":[],"evidence":["evidence"]}}',
            }

    class FakeNormalizer:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def normalize(self, *, request: dict, raw_result: dict) -> dict:
            self.calls.append({"request": request, "raw_result": raw_result})
            return {
                "assessment": {
                    "verdict": "strong",
                    "score_total": 0.9,
                    "core_gaps": ["workflow checkpoint gap"],
                    "misconceptions": [],
                    "evidence": ["evidence"],
                },
                "confidence": 0.9,
            }

    samples = [
        EvaluatorLiveQualitySample(
            sample_id="sample-a",
            question_context="Explain the boundary.",
            answer_text="Concrete answer.",
            expected_verdicts={"strong"},
            score_band=(0.7, 1.0),
            required_gap_keywords=("workflow", "checkpoint"),
        ),
        EvaluatorLiveQualitySample(
            sample_id="sample-b",
            question_context="Explain the boundary.",
            answer_text="Concrete answer.",
            expected_verdicts={"strong"},
            score_band=(0.7, 1.0),
            required_gap_keywords=("workflow", "checkpoint"),
        ),
    ]

    builder = FakeBuilder()
    client = FakeClient()
    normalizer = FakeNormalizer()

    results = run_evaluator_live_quality_smoke(
        samples=samples,
        builder=builder,
        client=client,
        normalizer=normalizer,
        project_context="proj",
        stage_context="stage",
        current_decisions=["decision-1"],
        boundary_focus=["focus-1"],
    )

    assert [result.sample.sample_id for result in results] == ["sample-a", "sample-b"]
    assert [result.issues for result in results] == [[], []]
    assert len(builder.calls) == 2
    assert len(client.calls) == 2
    assert len(normalizer.calls) == 2


def test_format_live_quality_report_surfaces_scores_and_issues() -> None:
    report = format_live_quality_report(
        [
            EvaluatorLiveQualitySmokeResult(
                sample=EvaluatorLiveQualitySample(
                    sample_id="strong_concrete",
                    question_context="q",
                    answer_text="a",
                    expected_verdicts={"strong"},
                    score_band=(0.7, 1.0),
                    required_gap_keywords=("workflow",),
                ),
                normalized={
                    "assessment": {"verdict": "strong", "score_total": 0.92},
                    "confidence": 0.9,
                },
                issues=[],
            ),
            EvaluatorLiveQualitySmokeResult(
                sample=EvaluatorLiveQualitySample(
                    sample_id="abstract_handwavy",
                    question_context="q",
                    answer_text="a",
                    expected_verdicts={"weak"},
                    score_band=(0.0, 0.45),
                    required_gap_keywords=("boundary",),
                ),
                normalized={
                    "assessment": {"verdict": "weak", "score_total": 0.88},
                    "confidence": 0.88,
                },
                issues=["score_out_of_expected_band", "missing_required_gap_keywords"],
            ),
        ]
    )

    assert "strong_concrete: verdict=strong score=0.92 confidence=0.90 issues=none" in report
    assert "abstract_handwavy: verdict=weak score=0.88 confidence=0.88 issues=score_out_of_expected_band,missing_required_gap_keywords" in report
