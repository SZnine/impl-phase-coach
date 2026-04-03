from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from review_gate.domain import (
    ProfileSpace,
    ProjectReview,
    ProposalCenter,
    QuestionSet,
    WorkspaceEvent,
)


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS project_store (
                    project_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS profile_store (
                    profile_space_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS profile_stage_summary_store (
                    profile_space_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (profile_space_id, project_id, stage_id)
                );

                CREATE INDEX IF NOT EXISTS idx_profile_stage_summary_store_project_stage
                    ON profile_stage_summary_store(project_id, stage_id);

                CREATE TABLE IF NOT EXISTS mistake_entry_store (
                    mistake_id TEXT PRIMARY KEY,
                    profile_space_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_mistake_entry_store_project_stage
                    ON mistake_entry_store(project_id, stage_id);

                CREATE TABLE IF NOT EXISTS index_entry_store (
                    entry_id TEXT PRIMARY KEY,
                    profile_space_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_index_entry_store_project_stage
                    ON index_entry_store(project_id, stage_id);

                CREATE TABLE IF NOT EXISTS knowledge_node_store (
                    node_id TEXT PRIMARY KEY,
                    profile_space_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_knowledge_node_store_project_stage
                    ON knowledge_node_store(project_id, stage_id);

                CREATE TABLE IF NOT EXISTS question_set_store (
                    question_set_id TEXT PRIMARY KEY,
                    stage_review_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_question_set_store_stage_review_id
                    ON question_set_store(stage_review_id);

                CREATE TABLE IF NOT EXISTS proposal_center_store (
                    proposal_center_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_proposal_center_store_project_id
                    ON proposal_center_store(project_id);

                CREATE TABLE IF NOT EXISTS proposal_store (
                    proposal_id TEXT PRIMARY KEY,
                    proposal_center_id TEXT NOT NULL,
                    project_id TEXT,
                    stage_id TEXT,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_proposal_store_center_id
                    ON proposal_store(proposal_center_id);

                CREATE INDEX IF NOT EXISTS idx_proposal_store_project_stage
                    ON proposal_store(project_id, stage_id);

                CREATE TABLE IF NOT EXISTS proposal_action_store (
                    action_id TEXT PRIMARY KEY,
                    proposal_center_id TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_proposal_action_store_center_id
                    ON proposal_action_store(proposal_center_id);

                CREATE INDEX IF NOT EXISTS idx_proposal_action_store_proposal_id
                    ON proposal_action_store(proposal_id);

                CREATE TABLE IF NOT EXISTS execution_record_store (
                    execution_id TEXT PRIMARY KEY,
                    proposal_center_id TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_execution_record_store_center_id
                    ON execution_record_store(proposal_center_id);

                CREATE INDEX IF NOT EXISTS idx_execution_record_store_proposal_id
                    ON execution_record_store(proposal_id);

                CREATE TABLE IF NOT EXISTS event_store (
                    event_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_event_store_project_id
                    ON event_store(project_id);

                CREATE INDEX IF NOT EXISTS idx_event_store_created_at
                    ON event_store(created_at);
                """
            )

    def upsert_project_review(self, review: ProjectReview) -> None:
        payload = review.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO project_store (project_id, payload)
                VALUES (?, ?)
                """,
                (review.project_id, payload),
            )

    def get_project_review(self, project_id: str) -> ProjectReview | None:
        row = self._fetch_one(
            "SELECT payload FROM project_store WHERE project_id = ?",
            (project_id,),
        )
        if row is None:
            return None
        return ProjectReview.from_json(row["payload"])

    def upsert_profile_space(self, profile_space: ProfileSpace) -> None:
        payload = profile_space.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO profile_store (profile_space_id, project_id, payload)
                VALUES (?, ?, ?)
                """,
                (profile_space.profile_space_id, profile_space.project_id, payload),
            )

    def get_profile_space(self, profile_space_id: str) -> ProfileSpace | None:
        row = self._fetch_one(
            "SELECT payload FROM profile_store WHERE profile_space_id = ?",
            (profile_space_id,),
        )
        if row is None:
            return None
        return ProfileSpace.from_json(row["payload"])

    def upsert_profile_stage_summary(
        self,
        profile_space_id: str,
        project_id: str,
        stage_id: str,
        summary: dict[str, Any],
    ) -> None:
        payload = self._dumps_payload(summary)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO profile_stage_summary_store (
                    profile_space_id,
                    project_id,
                    stage_id,
                    payload
                ) VALUES (?, ?, ?, ?)
                """,
                (profile_space_id, project_id, stage_id, payload),
            )

    def get_profile_stage_summary(
        self,
        profile_space_id: str,
        project_id: str,
        stage_id: str,
    ) -> dict[str, Any] | None:
        row = self._fetch_one(
            """
            SELECT payload FROM profile_stage_summary_store
            WHERE profile_space_id = ? AND project_id = ? AND stage_id = ?
            """,
            (profile_space_id, project_id, stage_id),
        )
        if row is None:
            return None
        return self._loads_payload(row["payload"])

    def list_profile_stage_summaries(
        self,
        profile_space_id: str | None = None,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._list_payloads(
            table_name="profile_stage_summary_store",
            id_column=None,
            profile_space_id=profile_space_id,
            project_id=project_id,
            stage_id=None,
        )

    def upsert_profile_mistake(self, profile_space_id: str, item: dict[str, Any]) -> None:
        payload = self._dumps_payload(item)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mistake_entry_store (
                    mistake_id,
                    profile_space_id,
                    project_id,
                    stage_id,
                    payload
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (item["mistake_id"], profile_space_id, item["project_id"], item["stage_id"], payload),
            )

    def list_profile_mistakes(
        self,
        profile_space_id: str | None = None,
        project_id: str | None = None,
        stage_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._list_payloads(
            table_name="mistake_entry_store",
            id_column="mistake_id",
            profile_space_id=profile_space_id,
            project_id=project_id,
            stage_id=stage_id,
        )

    def upsert_profile_index_entry(self, profile_space_id: str, item: dict[str, Any]) -> None:
        payload = self._dumps_payload(item)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO index_entry_store (
                    entry_id,
                    profile_space_id,
                    project_id,
                    stage_id,
                    payload
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (item["entry_id"], profile_space_id, item["project_id"], item["stage_id"], payload),
            )

    def list_profile_index_entries(
        self,
        profile_space_id: str | None = None,
        project_id: str | None = None,
        stage_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._list_payloads(
            table_name="index_entry_store",
            id_column="entry_id",
            profile_space_id=profile_space_id,
            project_id=project_id,
            stage_id=stage_id,
        )

    def upsert_profile_knowledge_node(self, profile_space_id: str, item: dict[str, Any]) -> None:
        payload = self._dumps_payload(item)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_node_store (
                    node_id,
                    profile_space_id,
                    project_id,
                    stage_id,
                    payload
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (item["node_id"], profile_space_id, item["project_id"], item["stage_id"], payload),
            )

    def list_profile_knowledge_nodes(
        self,
        profile_space_id: str | None = None,
        project_id: str | None = None,
        stage_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._list_payloads(
            table_name="knowledge_node_store",
            id_column="node_id",
            profile_space_id=profile_space_id,
            project_id=project_id,
            stage_id=stage_id,
        )

    def upsert_question_set(self, question_set: QuestionSet) -> None:
        payload = question_set.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO question_set_store (
                    question_set_id,
                    stage_review_id,
                    payload
                ) VALUES (?, ?, ?)
                """,
                (question_set.question_set_id, question_set.stage_review_id, payload),
            )

    def get_question_set(self, question_set_id: str) -> QuestionSet | None:
        row = self._fetch_one(
            "SELECT payload FROM question_set_store WHERE question_set_id = ?",
            (question_set_id,),
        )
        if row is None:
            return None
        return QuestionSet.from_json(row["payload"])

    def upsert_proposal_center(self, proposal_center: ProposalCenter) -> None:
        payload = proposal_center.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO proposal_center_store (
                    proposal_center_id,
                    project_id,
                    payload
                ) VALUES (?, ?, ?)
                """,
                (
                    proposal_center.proposal_center_id,
                    proposal_center.project_id,
                    payload,
                ),
            )

    def get_proposal_center(self, proposal_center_id: str) -> ProposalCenter | None:
        row = self._fetch_one(
            "SELECT payload FROM proposal_center_store WHERE proposal_center_id = ?",
            (proposal_center_id,),
        )
        if row is None:
            return None
        return ProposalCenter.from_json(row["payload"])

    def upsert_proposal_record(self, proposal_center_id: str, item: dict[str, Any]) -> None:
        payload = self._dumps_payload(item)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO proposal_store (
                    proposal_id,
                    proposal_center_id,
                    project_id,
                    stage_id,
                    payload
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (item["proposal_id"], proposal_center_id, item.get("project_id"), item.get("stage_id"), payload),
            )

    def get_proposal_record(self, proposal_id: str) -> dict[str, Any] | None:
        row = self._fetch_one(
            "SELECT payload FROM proposal_store WHERE proposal_id = ?",
            (proposal_id,),
        )
        if row is None:
            return None
        return self._loads_payload(row["payload"])

    def list_proposal_records(
        self,
        proposal_center_id: str | None = None,
        project_id: str | None = None,
        stage_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._list_payloads(
            table_name="proposal_store",
            id_column="proposal_id",
            profile_space_id=None,
            project_id=project_id,
            stage_id=stage_id,
            proposal_center_id=proposal_center_id,
            proposal_id=None,
            action_id=None,
        )

    def upsert_proposal_action_record(self, proposal_center_id: str, item: dict[str, Any]) -> None:
        payload = self._dumps_payload(item)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO proposal_action_store (
                    action_id,
                    proposal_center_id,
                    proposal_id,
                    payload
                ) VALUES (?, ?, ?, ?)
                """,
                (item["action_id"], proposal_center_id, item["proposal_id"], payload),
            )

    def get_proposal_action_record(self, action_id: str) -> dict[str, Any] | None:
        row = self._fetch_one(
            "SELECT payload FROM proposal_action_store WHERE action_id = ?",
            (action_id,),
        )
        if row is None:
            return None
        return self._loads_payload(row["payload"])

    def list_proposal_action_records(
        self,
        proposal_center_id: str | None = None,
        proposal_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._list_payloads(
            table_name="proposal_action_store",
            id_column="action_id",
            profile_space_id=None,
            project_id=None,
            stage_id=None,
            proposal_center_id=proposal_center_id,
            proposal_id=proposal_id,
            action_id=None,
        )

    def upsert_execution_record(self, proposal_center_id: str, item: dict[str, Any]) -> None:
        payload = self._dumps_payload(item)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO execution_record_store (
                    execution_id,
                    proposal_center_id,
                    proposal_id,
                    action_id,
                    payload
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (item["execution_id"], proposal_center_id, item["proposal_id"], item["action_id"], payload),
            )

    def list_execution_records(
        self,
        proposal_center_id: str | None = None,
        proposal_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._list_payloads(
            table_name="execution_record_store",
            id_column="execution_id",
            profile_space_id=None,
            project_id=None,
            stage_id=None,
            proposal_center_id=proposal_center_id,
            proposal_id=proposal_id,
            action_id=None,
        )

    def append_event(self, event: WorkspaceEvent) -> None:
        payload = event.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO event_store (
                    event_id,
                    project_id,
                    event_type,
                    created_at,
                    payload
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (event.event_id, event.project_id, event.event_type, event.created_at, payload),
            )

    def get_event(self, event_id: str) -> WorkspaceEvent | None:
        row = self._fetch_one(
            "SELECT payload FROM event_store WHERE event_id = ?",
            (event_id,),
        )
        if row is None:
            return None
        return WorkspaceEvent.from_json(row["payload"])

    def list_events(self, project_id: str | None = None) -> list[WorkspaceEvent]:
        if project_id is None:
            rows = self._fetch_all(
                "SELECT payload FROM event_store ORDER BY created_at, event_id",
                (),
            )
        else:
            rows = self._fetch_all(
                "SELECT payload FROM event_store WHERE project_id = ? ORDER BY created_at, event_id",
                (project_id,),
            )
        return [WorkspaceEvent.from_json(row["payload"]) for row in rows]

    def _list_payloads(
        self,
        *,
        table_name: str,
        id_column: str | None,
        profile_space_id: str | None,
        project_id: str | None,
        stage_id: str | None,
        proposal_center_id: str | None = None,
        proposal_id: str | None = None,
        action_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if profile_space_id is not None:
            clauses.append("profile_space_id = ?")
            params.append(profile_space_id)
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if stage_id is not None:
            clauses.append("stage_id = ?")
            params.append(stage_id)
        if proposal_center_id is not None:
            clauses.append("proposal_center_id = ?")
            params.append(proposal_center_id)
        if proposal_id is not None:
            clauses.append("proposal_id = ?")
            params.append(proposal_id)
        if action_id is not None:
            clauses.append("action_id = ?")
            params.append(action_id)
        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        order_column = id_column or "stage_id"
        rows = self._fetch_all(
            f"SELECT payload FROM {table_name}{where_clause} ORDER BY {order_column}",
            tuple(params),
        )
        return [self._loads_payload(row["payload"]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _fetch_one(self, query: str, params: tuple[Any, ...]) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(query, params).fetchone()

    def _fetch_all(self, query: str, params: tuple[Any, ...]) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def _dumps_payload(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _loads_payload(self, payload: str) -> dict[str, Any]:
        value = json.loads(payload)
        if isinstance(value, dict):
            return {str(key): item for key, item in value.items()}
        return {}
