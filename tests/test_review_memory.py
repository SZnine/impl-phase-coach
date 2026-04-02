from review_gate.maintenance import compact_entries
from review_gate.memory import extract_entries
from review_gate.models import (
    KnowledgeEntryType,
    ReviewAssessment,
    ReviewPassState,
)


def test_extract_entries_creates_error_pattern_and_capability_profile() -> None:
    assessment = ReviewAssessment(
        pass_state=ReviewPassState.REDIRECT_TO_LEARNING,
        confidence=0.25,
        core_gaps=["cannot explain denied vs failed clearly"],
        failure_reason="state semantics still collapse under pressure",
        allow_next_stage=False,
        recommend_learning=True,
        learning_recommendations=[
            "Rebuild state semantics before coding return branches.",
            "Compare DENIED and FAILED with two concrete examples.",
        ],
    )

    entries = extract_entries(
        stage_id="stage-2",
        assessment=assessment,
        last_answer="I know they are different, but I cannot explain the boundary.",
    )

    assert len(entries) == 2
    assert {entry.entry_type for entry in entries} == {
        KnowledgeEntryType.ERROR_PATTERN,
        KnowledgeEntryType.CAPABILITY_PROFILE,
    }
    assert entries[0].learning_recommendations
    assert "state semantics" in entries[0].learning_recommendations[0].lower()



def test_compact_entries_merges_duplicate_error_patterns() -> None:
    assessment = ReviewAssessment(
        pass_state=ReviewPassState.CONTINUE_PROBING,
        confidence=0.45,
        core_gaps=["stage boundary explanation is unstable"],
        failure_reason="answer stays at slogan level",
        allow_next_stage=False,
        recommend_learning=True,
        learning_recommendations=[
            "Restate the phase boundary once.",
            "Restate the phase boundary once.",
        ],
    )

    entries = extract_entries(
        stage_id="stage-5",
        assessment=assessment,
        last_answer="I get it, but I cannot defend why this stays in stage 5.",
    )
    duplicates = entries + entries

    result = compact_entries(duplicates)

    assert len(result.entries) == 2
    assert result.merged_entries
    assert result.compression_reason == "merged duplicate stage knowledge entries"
    assert result.entries[0].learning_recommendations == ["Restate the phase boundary once."]
