from __future__ import annotations

from typing import Protocol

from review_gate.domain import FocusExplanation, current_utc_timestamp


class FocusExplanationGenerator(Protocol):
    def build_focus_cluster_explanation(self, *, profile_space_id: str, cluster: dict) -> FocusExplanation: ...


class DeterministicFocusExplanationGenerator:
    def build_focus_cluster_explanation(self, *, profile_space_id: str, cluster: dict) -> FocusExplanation:
        return FocusExplanation(
            explanation_id=f"focus_cluster:{cluster['cluster_id']}",
            profile_space_id=profile_space_id,
            subject_type="focus_cluster",
            subject_id=cluster["cluster_id"],
            reason_codes=list(cluster.get("focus_reason_codes", [])),
            summary=self._build_focus_explanation_summary(cluster),
            generated_by="deterministic",
            generated_at=current_utc_timestamp(),
            version="v1",
        )

    def _build_focus_explanation_summary(self, cluster: dict) -> str:
        title = str(cluster.get("title", "This cluster")).replace(" hotspot", "")
        codes = list(cluster.get("focus_reason_codes", []))
        if "weak_signal_active" in codes and "current_project_hit" in codes:
            return f"{title} matters now because the current stage exposed it as an active weak area."
        if "weak_signal_active" in codes:
            return f"{title} matters now because it still shows an active weak signal."
        if "current_project_hit" in codes:
            return f"{title} matters now because the current project is actively hitting it."
        if "foundation_hot" in codes:
            return f"{title} matters now because it is acting as a frequently triggered foundation hotspot."
        if "recently_changed" in codes:
            return f"{title} matters now because its supporting knowledge changed recently."
        if "high_structural_importance" in codes:
            return f"{title} matters now because it is a structural anchor in the current map."
        if "cross_project_reuse" in codes:
            return f"{title} matters now because it keeps showing up across multiple projects."
        return f"{title} matters now because it is part of the current working map."
