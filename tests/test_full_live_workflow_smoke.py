from review_gate.full_live_workflow_smoke import (
    build_full_live_workflow_smoke_artifact,
    classify_full_live_workflow_smoke_issues,
    format_full_live_workflow_smoke_report,
    resolve_first_generated_transport_question_id,
)


def test_resolve_first_generated_transport_question_id_uses_question_set_prefix() -> None:
    question_id = resolve_first_generated_transport_question_id(
        generation_response={
            "questions": [
                {
                    "question_id": "q-1",
                    "prompt": "Explain the generated question.",
                }
            ]
        },
        question_set_id="set-1",
    )

    assert question_id == "set-1-q-1"


def test_classify_full_live_workflow_smoke_issues_accepts_minimal_success() -> None:
    issues = classify_full_live_workflow_smoke_issues(
        generation_response={"questions": [{"question_id": "q-1"}]},
        submit_response={"success": True},
        assessment_review={"has_assessment": True, "review_title": "方向正确，但还需要补齐关键缺口"},
        question_set_view={
            "question_count": 1,
            "current_question_id": "set-1-q-1",
            "questions": [{"question_id": "set-1-q-1", "status": "answered"}],
        },
        graph_revision={
            "has_active_revision": True,
            "revision": {"node_count": 1, "relation_count": 0},
            "nodes": [{"knowledge_node_id": "kn-1"}],
        },
        graph_main={
            "nodes": [{"node_id": "kn-1"}],
            "selected_cluster": {"center_node_id": "kn-1"},
            "relations": [],
        },
        strict=False,
    )

    assert issues == []


def test_classify_full_live_workflow_smoke_issues_treats_relation_as_strict_only() -> None:
    kwargs = {
        "generation_response": {"questions": [{"question_id": "q-1"}]},
        "submit_response": {"success": True},
        "assessment_review": {"has_assessment": True, "review_title": "方向正确，但还需要补齐关键缺口"},
        "question_set_view": {
            "question_count": 1,
            "current_question_id": "set-1-q-1",
            "questions": [{"question_id": "set-1-q-1", "status": "answered"}],
        },
        "graph_revision": {
            "has_active_revision": True,
            "revision": {"node_count": 1, "relation_count": 0},
            "nodes": [{"knowledge_node_id": "kn-1"}],
        },
        "graph_main": {
            "nodes": [{"node_id": "kn-1"}],
            "selected_cluster": {"center_node_id": "kn-1"},
            "relations": [],
        },
    }

    assert classify_full_live_workflow_smoke_issues(**kwargs, strict=False) == []
    assert classify_full_live_workflow_smoke_issues(**kwargs, strict=True) == [
        "missing_relation_in_strict_mode"
    ]


def test_build_full_live_workflow_smoke_artifact_omits_sensitive_provider_config() -> None:
    artifact = build_full_live_workflow_smoke_artifact(
        generation_response={"questions": [{"question_id": "q-1"}]},
        selected_question_id="set-1-q-1",
        submit_response={"success": True},
        assessment_review={"has_assessment": True, "review_title": "方向正确，但还需要补齐关键缺口"},
        question_set_view={
            "question_count": 1,
            "current_question_id": "set-1-q-1",
            "questions": [{"question_id": "set-1-q-1", "status": "answered"}],
        },
        graph_revision={"has_active_revision": True},
        graph_main={"nodes": []},
        issues=[],
        db_path="C:/tmp/full-smoke.sqlite3",
        project_model="gpt-5.4-mini",
        evaluator_model="gpt-5.4-mini",
    )

    assert artifact["project_model"] == "gpt-5.4-mini"
    assert artifact["evaluator_model"] == "gpt-5.4-mini"
    assert artifact["selected_question_id"] == "set-1-q-1"
    assert artifact["assessment_review"]["has_assessment"] is True
    assert artifact["question_set_view"]["questions"][0]["status"] == "answered"
    assert "api_key" not in str(artifact).lower()
    assert "authorization" not in str(artifact).lower()


def test_format_full_live_workflow_smoke_report_surfaces_generation_and_graph_counts() -> None:
    report = format_full_live_workflow_smoke_report(
        {
            "project_model": "gpt-5.4-mini",
            "evaluator_model": "gpt-5.4-mini",
            "selected_question_id": "set-1-q-1",
            "issues": [],
            "generation_response": {"questions": [{"question_id": "q-1"}, {"question_id": "q-2"}]},
            "assessment_review": {
                "has_assessment": True,
                "review_title": "方向正确，但还需要补齐关键缺口",
                "knowledge_updates": [{"title": "normalizer failure scenario"}],
            },
            "question_set_view": {
                "question_count": 2,
                "current_question_id": "set-1-q-2",
                "questions": [
                    {"question_id": "set-1-q-1", "status": "answered"},
                    {"question_id": "set-1-q-2", "status": "ready"},
                ],
            },
            "graph_revision": {"revision": {"node_count": 2, "relation_count": 1}},
            "graph_main": {
                "selected_cluster": {
                    "center_node_id": "kn-target",
                    "neighbor_node_ids": ["kn-source"],
                    "focus_reason_codes": ["weak_signal_active", "relation_connected"],
                }
            },
        }
    )

    assert "project_model: gpt-5.4-mini" in report
    assert "evaluator_model: gpt-5.4-mini" in report
    assert "generated_question_count: 2" in report
    assert "selected_question_id: set-1-q-1" in report
    assert "answered_question_count: 1" in report
    assert "current_question_id: set-1-q-2" in report
    assert "review_title: 方向正确，但还需要补齐关键缺口" in report
    assert "knowledge_update_count: 1" in report
    assert "node_count: 2" in report
    assert "relation_count: 1" in report
    assert "issues: none" in report


def test_classify_full_live_workflow_smoke_issues_requires_assessment_review() -> None:
    issues = classify_full_live_workflow_smoke_issues(
        generation_response={"questions": [{"question_id": "q-1"}]},
        submit_response={"success": True},
        assessment_review={"has_assessment": False},
        question_set_view={
            "question_count": 1,
            "current_question_id": "set-1-q-1",
            "questions": [{"question_id": "set-1-q-1", "status": "answered"}],
        },
        graph_revision={
            "has_active_revision": True,
            "revision": {"node_count": 1, "relation_count": 0},
            "nodes": [{"knowledge_node_id": "kn-1"}],
        },
        graph_main={
            "nodes": [{"node_id": "kn-1"}],
            "selected_cluster": {"center_node_id": "kn-1"},
            "relations": [],
        },
        strict=False,
    )

    assert issues == ["missing_assessment_review"]


def test_classify_full_live_workflow_smoke_issues_requires_answered_question_progress() -> None:
    issues = classify_full_live_workflow_smoke_issues(
        generation_response={"questions": [{"question_id": "q-1"}]},
        submit_response={"success": True, "refresh_targets": ["question_detail", "stage_summary"]},
        assessment_review={"has_assessment": True, "review_title": "方向正确，但还需要补齐关键缺口"},
        question_set_view={
            "question_count": 1,
            "current_question_id": "set-1-q-1",
            "questions": [{"question_id": "set-1-q-1", "status": "ready"}],
        },
        graph_revision={
            "has_active_revision": True,
            "revision": {"node_count": 1, "relation_count": 0},
            "nodes": [{"knowledge_node_id": "kn-1"}],
        },
        graph_main={
            "nodes": [{"node_id": "kn-1"}],
            "selected_cluster": {"center_node_id": "kn-1"},
            "relations": [],
        },
        strict=False,
    )

    assert issues == ["missing_question_set_refresh_target", "missing_answered_question_progress"]
