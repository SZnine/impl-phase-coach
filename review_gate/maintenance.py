from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    CompactionMode,
    CompactionPlan,
    CompactionResult,
    KnowledgeEntry,
    MaintenanceExecution,
    MaintenanceTask,
    MaintenanceTaskStatus,
    new_task_id,
)


def compact_entries(
    entries: list[KnowledgeEntry], mode: CompactionMode = CompactionMode.LIGHT
) -> CompactionResult:
    unique: dict[tuple[str, str, str, str], KnowledgeEntry] = {}
    merged_entries: list[str] = []

    for entry in entries:
        key = (entry.entry_type.value, entry.stage_id, entry.summary, entry.root_cause)
        if key in unique:
            merged_entries.append(entry.entry_id)
            existing = unique[key]
            for item in entry.evidence:
                if item not in existing.evidence:
                    existing.evidence.append(item)
            for recommendation in entry.learning_recommendations:
                if recommendation not in existing.learning_recommendations:
                    existing.learning_recommendations.append(recommendation)
            continue

        entry.learning_recommendations = _unique_recommendations(entry.learning_recommendations)
        unique[key] = entry

    return CompactionResult(
        entries=list(unique.values()),
        merged_entries=merged_entries,
        dropped_entries=[],
        compression_reason=_compression_reason(mode, bool(merged_entries)),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


def create_maintenance_task(
    *, mode: CompactionMode, entries: list[KnowledgeEntry]
) -> MaintenanceTask:
    return MaintenanceTask(
        task_id=new_task_id(),
        mode=mode,
        status=MaintenanceTaskStatus.PENDING,
        source_entry_count=len(entries),
    )


def plan_compaction(
    entries: list[KnowledgeEntry], *, mode: CompactionMode
) -> CompactionPlan:
    duplicates = _find_duplicate_entry_ids(entries)
    return CompactionPlan(
        mode=mode,
        candidate_entry_ids=duplicates,
        requires_manual_review=mode is CompactionMode.DEEP,
        strategy_summary=_strategy_summary(mode),
    )


def run_maintenance_task(
    entries: list[KnowledgeEntry], *, mode: CompactionMode
) -> MaintenanceExecution:
    task = create_maintenance_task(mode=mode, entries=entries)
    plan = plan_compaction(entries, mode=mode)
    result = compact_entries(entries, mode=mode)
    task.status = MaintenanceTaskStatus.COMPLETED
    return MaintenanceExecution(task=task, plan=plan, result=result)


def _find_duplicate_entry_ids(entries: list[KnowledgeEntry]) -> list[str]:
    seen: dict[tuple[str, str, str, str], str] = {}
    duplicates: list[str] = []

    for entry in entries:
        key = (entry.entry_type.value, entry.stage_id, entry.summary, entry.root_cause)
        if key in seen:
            duplicates.append(entry.entry_id)
            continue
        seen[key] = entry.entry_id

    return duplicates


def _strategy_summary(mode: CompactionMode) -> str:
    if mode is CompactionMode.DEEP:
        return "deep compaction with manual review gate"
    return "light merge duplicate stage knowledge entries"


def _compression_reason(mode: CompactionMode, merged: bool) -> str:
    if not merged:
        return "no compression needed"
    if mode is CompactionMode.DEEP:
        return "deep-compacted duplicate stage knowledge entries"
    return "merged duplicate stage knowledge entries"


def _unique_recommendations(recommendations: list[str]) -> list[str]:
    unique: list[str] = []
    for item in recommendations:
        if item not in unique:
            unique.append(item)
    return unique
