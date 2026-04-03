from __future__ import annotations

from review_gate.domain import ProposalCenter
from review_gate.storage_sqlite import SQLiteStore


class ProposalCenterService:
    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store
        self._proposal_counter = 0
        self._action_counter = 0
        self._execution_counter = 0
        self._proposals: dict[str, dict] = {}
        self._actions: dict[str, dict] = {}

    @classmethod
    def for_testing(cls) -> "ProposalCenterService":
        return cls()

    @classmethod
    def with_store(cls, store: SQLiteStore) -> "ProposalCenterService":
        return cls(store=store)

    def create_compression_proposals(
        self,
        target_type: str,
        target_ids: list[str],
        project_id: str | None = None,
        stage_id: str | None = None,
    ) -> list[dict]:
        proposal_id = self._next_proposal_id()
        proposal = {
            "proposal_id": proposal_id,
            "proposal_type": f"compress_{target_type}",
            "target_type": target_type,
            "target_ids": list(target_ids),
            "project_id": project_id,
            "stage_id": stage_id,
            "status": "pending_review",
            "reason": f"Compress {len(target_ids)} {target_type}",
            "preview_summary": f"Would compress {len(target_ids)} targets from {target_type}.",
            "latest_execution_status": None,
            "latest_execution_summary": None,
            "risk_notes": [],
        }
        if self._store is None:
            self._proposals[proposal_id] = proposal
        else:
            proposal_center = self._load_or_create_center(project_id)
            self._store.upsert_proposal_record(proposal_center.proposal_center_id, proposal)
            self._sync_center_proposal_ids(proposal_center, proposal_id)
        return [dict(proposal)]

    def list_proposals(self, project_id: str | None = None, stage_id: str | None = None) -> list[dict]:
        if self._store is not None:
            return self._store.list_proposal_records(project_id=project_id, stage_id=stage_id)

        proposals = list(self._proposals.values())
        if project_id is not None:
            proposals = [proposal for proposal in proposals if proposal.get("project_id") == project_id]
        if stage_id is not None:
            proposals = [proposal for proposal in proposals if proposal.get("stage_id") == stage_id]
        return [dict(proposal) for proposal in proposals]

    def get_proposal(self, proposal_id: str) -> dict:
        if self._store is not None:
            proposal = self._store.get_proposal_record(proposal_id)
            if proposal is None:
                raise KeyError(proposal_id)
            return proposal
        return dict(self._proposals[proposal_id])

    def record_user_action(self, proposal_id: str, action_type: str, selected_target_ids: list[str]) -> dict:
        proposal = self.get_proposal(proposal_id)
        action_id = self._next_action_id()
        action = {
            "action_id": action_id,
            "proposal_id": proposal_id,
            "action_type": action_type,
            "selected_target_ids": list(selected_target_ids),
        }
        if self._store is None:
            self._actions[action_id] = action
        else:
            proposal_center = self._load_or_create_center(proposal.get("project_id"))
            self._store.upsert_proposal_action_record(proposal_center.proposal_center_id, action)
        return dict(action)

    def execute_proposal(self, proposal_id: str, action_id: str) -> dict:
        proposal = self.get_proposal(proposal_id)
        action = self._get_action(action_id)
        if action["proposal_id"] != proposal_id:
            return {
                "execution_id": None,
                "proposal_id": proposal_id,
                "action_id": action_id,
                "proposal_type": proposal["proposal_type"],
                "proposal_status": proposal["status"],
                "status": "failed",
                "applied_target_ids": [],
                "unchanged_target_ids": list(proposal["target_ids"]),
                "generated_target_ids": [],
                "summary": "Action does not belong to the proposal.",
                "risk_notes": [],
                "error_message": "Action does not belong to the proposal.",
            }

        action_type = action["action_type"]
        selected_target_ids = list(action["selected_target_ids"])
        if not selected_target_ids:
            selected_target_ids = list(proposal["target_ids"])

        if action_type == "accept":
            proposal_status = "accepted"
            execution_status = "succeeded"
            applied_target_ids = selected_target_ids
            unchanged_target_ids = []
        elif action_type == "reject":
            proposal_status = "rejected"
            execution_status = "cancelled"
            applied_target_ids = []
            unchanged_target_ids = list(proposal["target_ids"])
        elif action_type == "defer":
            proposal_status = "deferred"
            execution_status = "cancelled"
            applied_target_ids = []
            unchanged_target_ids = list(proposal["target_ids"])
        else:
            proposal_status = proposal["status"]
            execution_status = "failed"
            applied_target_ids = []
            unchanged_target_ids = list(proposal["target_ids"])

        execution_id = self._next_execution_id()
        summary = f"{action_type} on {proposal_id} => {execution_status}"
        proposal["status"] = proposal_status
        proposal["latest_execution_status"] = execution_status
        proposal["latest_execution_summary"] = summary

        if self._store is None:
            self._proposals[proposal_id] = dict(proposal)
        else:
            proposal_center = self._load_or_create_center(proposal.get("project_id"))
            self._store.upsert_proposal_record(proposal_center.proposal_center_id, proposal)
            self._sync_center_proposal_ids(proposal_center, proposal_id)

        execution = {
            "execution_id": execution_id,
            "proposal_id": proposal_id,
            "action_id": action_id,
            "proposal_type": proposal["proposal_type"],
            "proposal_status": proposal_status,
            "status": execution_status,
            "applied_target_ids": applied_target_ids,
            "unchanged_target_ids": unchanged_target_ids,
            "generated_target_ids": [],
            "summary": summary,
            "risk_notes": [],
            "error_message": None if execution_status != "failed" else "Unsupported action type.",
        }
        if self._store is not None:
            self._store.upsert_execution_record(proposal_center.proposal_center_id, execution)
        return execution

    def _get_action(self, action_id: str) -> dict:
        if self._store is not None:
            action = self._store.get_proposal_action_record(action_id)
            if action is None:
                raise KeyError(action_id)
            return action
        return dict(self._actions[action_id])

    def _load_or_create_center(self, project_id: str | None) -> ProposalCenter:
        if self._store is None:
            raise RuntimeError("Proposal center persistence is unavailable without a store.")
        proposal_center_id = self._proposal_center_id(project_id)
        existing = self._store.get_proposal_center(proposal_center_id)
        if existing is not None:
            return existing
        center = ProposalCenter(
            proposal_center_id=proposal_center_id,
            project_id=project_id or "global",
            proposal_ids=[],
            active_proposal_id=None,
            status="active",
        )
        self._store.upsert_proposal_center(center)
        return center

    def _sync_center_proposal_ids(self, center: ProposalCenter, proposal_id: str) -> None:
        if self._store is None:
            return
        proposal_ids = list(center.proposal_ids)
        if proposal_id not in proposal_ids:
            proposal_ids.append(proposal_id)
        updated_center = ProposalCenter(
            proposal_center_id=center.proposal_center_id,
            project_id=center.project_id,
            proposal_ids=proposal_ids,
            active_proposal_id=proposal_id,
            status=center.status,
        )
        self._store.upsert_proposal_center(updated_center)

    def _proposal_center_id(self, project_id: str | None) -> str:
        return f"proposal-center:{project_id or 'global'}"

    def _next_proposal_id(self) -> str:
        if self._store is None:
            self._proposal_counter += 1
            return f"proposal-{self._proposal_counter}"
        return f"proposal-{len(self._store.list_proposal_records()) + 1}"

    def _next_action_id(self) -> str:
        if self._store is None:
            self._action_counter += 1
            return f"action-{self._action_counter}"
        return f"action-{len(self._store.list_proposal_action_records()) + 1}"

    def _next_execution_id(self) -> str:
        if self._store is None:
            self._execution_counter += 1
            return f"execution-{self._execution_counter}"
        return f"execution-{len(self._store.list_execution_records()) + 1}"
