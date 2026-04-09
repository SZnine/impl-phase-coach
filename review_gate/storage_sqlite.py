from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from review_gate.domain import (
    AnswerFact,
    AssessmentFact,
    DecisionFact,
    EvidenceRef,
    FocusCluster,
    FocusExplanation,
    KnowledgeNode,
    KnowledgeRelation,
    ProfileSpace,
    ProjectReview,
    ProposalCenter,
    QuestionSet,
    UserNodeState,
    WorkspaceEvent,
)
from review_gate.checkpoint_models import (
    AnswerBatchRecord,
    AnswerItemRecord,
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    EvidenceSpanRecord,
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
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

                CREATE TABLE IF NOT EXISTS knowledge_map_node_store (
                    node_id TEXT PRIMARY KEY,
                    profile_space_id TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    abstract_level TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_knowledge_map_node_store_profile_space
                    ON knowledge_map_node_store(profile_space_id);

                CREATE TABLE IF NOT EXISTS evidence_ref_store (
                    evidence_id TEXT PRIMARY KEY,
                    profile_space_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_evidence_ref_store_profile_node
                    ON evidence_ref_store(profile_space_id, node_id);

                CREATE INDEX IF NOT EXISTS idx_evidence_ref_store_project_stage
                    ON evidence_ref_store(project_id, stage_id);

                CREATE TABLE IF NOT EXISTS user_node_state_store (
                    profile_space_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    activation_status TEXT NOT NULL,
                    mastery_status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (profile_space_id, node_id)
                );

                CREATE INDEX IF NOT EXISTS idx_user_node_state_store_mastery
                    ON user_node_state_store(mastery_status);

                CREATE TABLE IF NOT EXISTS knowledge_relation_store (
                    relation_id TEXT PRIMARY KEY,
                    profile_space_id TEXT NOT NULL,
                    source_node_id TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_knowledge_relation_store_profile_source
                    ON knowledge_relation_store(profile_space_id, source_node_id);

                CREATE INDEX IF NOT EXISTS idx_knowledge_relation_store_profile_target
                    ON knowledge_relation_store(profile_space_id, target_node_id);

                CREATE TABLE IF NOT EXISTS focus_cluster_store (
                    cluster_id TEXT PRIMARY KEY,
                    profile_space_id TEXT NOT NULL,
                    center_node_id TEXT NOT NULL,
                    generated_from TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_focus_cluster_store_profile_space
                    ON focus_cluster_store(profile_space_id);

                CREATE TABLE IF NOT EXISTS focus_explanation_store (
                    explanation_id TEXT PRIMARY KEY,
                    profile_space_id TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    generated_by TEXT NOT NULL,
                    version TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_focus_explanation_store_profile_subject
                    ON focus_explanation_store(profile_space_id, subject_type, subject_id);

                CREATE TABLE IF NOT EXISTS workflow_requests (
                    request_id TEXT PRIMARY KEY,
                    request_type TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    run_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    supersedes_run_id TEXT,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (request_id) REFERENCES workflow_requests(request_id)
                );

                CREATE INDEX IF NOT EXISTS idx_workflow_runs_request_id
                    ON workflow_runs(request_id);

                CREATE TABLE IF NOT EXISTS question_batches (
                    question_batch_id TEXT PRIMARY KEY,
                    workflow_run_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    generated_by TEXT NOT NULL,
                    source TEXT NOT NULL,
                    batch_goal TEXT NOT NULL,
                    entry_question_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_question_batches_workflow_run_id
                    ON question_batches(workflow_run_id);

                CREATE INDEX IF NOT EXISTS idx_question_batches_project_stage
                    ON question_batches(project_id, stage_id);

                CREATE TABLE IF NOT EXISTS question_items (
                    question_id TEXT PRIMARY KEY,
                    question_batch_id TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    difficulty_level TEXT NOT NULL,
                    order_index INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (question_batch_id) REFERENCES question_batches(question_batch_id)
                );

                CREATE INDEX IF NOT EXISTS idx_question_items_batch_order
                    ON question_items(question_batch_id, order_index);

                CREATE TABLE IF NOT EXISTS answer_batches (
                    answer_batch_id TEXT PRIMARY KEY,
                    question_batch_id TEXT NOT NULL,
                    workflow_run_id TEXT NOT NULL,
                    submitted_by TEXT NOT NULL,
                    submission_mode TEXT NOT NULL,
                    completion_status TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (question_batch_id) REFERENCES question_batches(question_batch_id),
                    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_answer_batches_question_batch_id
                    ON answer_batches(question_batch_id);

                CREATE INDEX IF NOT EXISTS idx_answer_batches_workflow_run_id
                    ON answer_batches(workflow_run_id);

                CREATE TABLE IF NOT EXISTS answer_items (
                    answer_item_id TEXT PRIMARY KEY,
                    answer_batch_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    answered_by TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    answer_format TEXT NOT NULL,
                    order_index INTEGER NOT NULL,
                    answered_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    revision_of_answer_item_id TEXT,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (answer_batch_id) REFERENCES answer_batches(answer_batch_id),
                    FOREIGN KEY (question_id) REFERENCES question_items(question_id)
                );

                CREATE INDEX IF NOT EXISTS idx_answer_items_batch_order
                    ON answer_items(answer_batch_id, order_index);

                CREATE INDEX IF NOT EXISTS idx_answer_items_question_id
                    ON answer_items(question_id);

                CREATE TABLE IF NOT EXISTS evaluation_batches (
                    evaluation_batch_id TEXT PRIMARY KEY,
                    answer_batch_id TEXT NOT NULL,
                    workflow_run_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    evaluated_by TEXT NOT NULL,
                    evaluator_version TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    supersedes_evaluation_batch_id TEXT,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (answer_batch_id) REFERENCES answer_batches(answer_batch_id),
                    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_evaluation_batches_answer_batch_id
                    ON evaluation_batches(answer_batch_id);

                CREATE INDEX IF NOT EXISTS idx_evaluation_batches_workflow_run_id
                    ON evaluation_batches(workflow_run_id);

                CREATE TABLE IF NOT EXISTS evaluation_items (
                    evaluation_item_id TEXT PRIMARY KEY,
                    evaluation_batch_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    answer_item_id TEXT NOT NULL,
                    local_verdict TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (evaluation_batch_id) REFERENCES evaluation_batches(evaluation_batch_id),
                    FOREIGN KEY (answer_item_id) REFERENCES answer_items(answer_item_id)
                );

                CREATE INDEX IF NOT EXISTS idx_evaluation_items_batch_id
                    ON evaluation_items(evaluation_batch_id);

                CREATE INDEX IF NOT EXISTS idx_evaluation_items_answer_item_id
                    ON evaluation_items(answer_item_id);

                CREATE TABLE IF NOT EXISTS evidence_spans (
                    evidence_span_id TEXT PRIMARY KEY,
                    evaluation_item_id TEXT NOT NULL,
                    answer_item_id TEXT NOT NULL,
                    span_type TEXT NOT NULL,
                    supports_dimension TEXT NOT NULL,
                    content TEXT NOT NULL,
                    start_offset INTEGER,
                    end_offset INTEGER,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (evaluation_item_id) REFERENCES evaluation_items(evaluation_item_id),
                    FOREIGN KEY (answer_item_id) REFERENCES answer_items(answer_item_id)
                );

                CREATE INDEX IF NOT EXISTS idx_evidence_spans_evaluation_item_id
                    ON evidence_spans(evaluation_item_id);

                CREATE INDEX IF NOT EXISTS idx_evidence_spans_answer_item_id
                    ON evidence_spans(answer_item_id);

                CREATE TABLE IF NOT EXISTS assessment_fact_batches (
                    assessment_fact_batch_id TEXT PRIMARY KEY,
                    evaluation_batch_id TEXT NOT NULL,
                    workflow_run_id TEXT NOT NULL,
                    synthesized_by TEXT NOT NULL,
                    synthesizer_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    synthesized_at TEXT NOT NULL,
                    supersedes_assessment_fact_batch_id TEXT,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (evaluation_batch_id) REFERENCES evaluation_batches(evaluation_batch_id),
                    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_assessment_fact_batches_evaluation_batch_id
                    ON assessment_fact_batches(evaluation_batch_id);

                CREATE INDEX IF NOT EXISTS idx_assessment_fact_batches_workflow_run_id
                    ON assessment_fact_batches(workflow_run_id);

                CREATE TABLE IF NOT EXISTS assessment_fact_items (
                    assessment_fact_item_id TEXT PRIMARY KEY,
                    assessment_fact_batch_id TEXT NOT NULL,
                    source_evaluation_item_id TEXT,
                    fact_type TEXT NOT NULL,
                    topic_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    supersedes_assessment_fact_item_id TEXT,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (assessment_fact_batch_id) REFERENCES assessment_fact_batches(assessment_fact_batch_id)
                );

                CREATE INDEX IF NOT EXISTS idx_assessment_fact_items_batch_id
                    ON assessment_fact_items(assessment_fact_batch_id);

                CREATE INDEX IF NOT EXISTS idx_assessment_fact_items_fact_type_topic_key
                    ON assessment_fact_items(fact_type, topic_key);

                CREATE TABLE IF NOT EXISTS question_set_store (
                    question_set_id TEXT PRIMARY KEY,
                    stage_review_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_question_set_store_stage_review_id
                    ON question_set_store(stage_review_id);

                CREATE TABLE IF NOT EXISTS answer_fact_store (
                    answer_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    question_set_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    source_page TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_answer_fact_store_project_stage
                    ON answer_fact_store(project_id, stage_id);

                CREATE TABLE IF NOT EXISTS assessment_fact_store (
                    assessment_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    answer_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    question_set_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_assessment_fact_store_project_stage
                    ON assessment_fact_store(project_id, stage_id);

                CREATE TABLE IF NOT EXISTS decision_fact_store (
                    decision_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    assessment_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    decision_value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_decision_fact_store_project_stage
                    ON decision_fact_store(project_id, stage_id);

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

    def upsert_knowledge_node(self, node: KnowledgeNode) -> None:
        payload = node.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_map_node_store (
                    node_id,
                    profile_space_id,
                    node_type,
                    abstract_level,
                    scope,
                    status,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.node_id,
                    node.profile_space_id,
                    node.node_type,
                    node.abstract_level,
                    node.scope,
                    node.status,
                    payload,
                ),
            )

    def get_knowledge_node(self, node_id: str) -> KnowledgeNode | None:
        row = self._fetch_one(
            "SELECT payload FROM knowledge_map_node_store WHERE node_id = ?",
            (node_id,),
        )
        if row is None:
            return None
        return KnowledgeNode.from_json(row["payload"])

    def list_knowledge_nodes(self, profile_space_id: str | None = None) -> list[KnowledgeNode]:
        if profile_space_id is None:
            rows = self._fetch_all(
                "SELECT payload FROM knowledge_map_node_store ORDER BY node_id",
                (),
            )
        else:
            rows = self._fetch_all(
                "SELECT payload FROM knowledge_map_node_store WHERE profile_space_id = ? ORDER BY node_id",
                (profile_space_id,),
            )
        return [KnowledgeNode.from_json(row["payload"]) for row in rows]

    def upsert_evidence_ref(self, evidence_ref: EvidenceRef) -> None:
        payload = evidence_ref.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO evidence_ref_store (
                    evidence_id,
                    profile_space_id,
                    node_id,
                    evidence_type,
                    project_id,
                    stage_id,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_ref.evidence_id,
                    evidence_ref.profile_space_id,
                    evidence_ref.node_id,
                    evidence_ref.evidence_type,
                    evidence_ref.project_id,
                    evidence_ref.stage_id,
                    payload,
                ),
            )

    def list_evidence_refs(
        self,
        profile_space_id: str | None = None,
        node_id: str | None = None,
        project_id: str | None = None,
        stage_id: str | None = None,
    ) -> list[EvidenceRef]:
        clauses: list[str] = []
        params: list[Any] = []
        if profile_space_id is not None:
            clauses.append("profile_space_id = ?")
            params.append(profile_space_id)
        if node_id is not None:
            clauses.append("node_id = ?")
            params.append(node_id)
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if stage_id is not None:
            clauses.append("stage_id = ?")
            params.append(stage_id)
        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetch_all(
            f"SELECT payload FROM evidence_ref_store{where_clause} ORDER BY evidence_id",
            tuple(params),
        )
        return [EvidenceRef.from_json(row["payload"]) for row in rows]

    def upsert_user_node_state(self, state: UserNodeState) -> None:
        payload = state.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_node_state_store (
                    profile_space_id,
                    node_id,
                    activation_status,
                    mastery_status,
                    payload
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    state.profile_space_id,
                    state.node_id,
                    state.activation_status,
                    state.mastery_status,
                    payload,
                ),
            )

    def get_user_node_state(self, profile_space_id: str, node_id: str) -> UserNodeState | None:
        row = self._fetch_one(
            """
            SELECT payload FROM user_node_state_store
            WHERE profile_space_id = ? AND node_id = ?
            """,
            (profile_space_id, node_id),
        )
        if row is None:
            return None
        return UserNodeState.from_json(row["payload"])

    def list_user_node_states(self, profile_space_id: str | None = None) -> list[UserNodeState]:
        if profile_space_id is None:
            rows = self._fetch_all(
                "SELECT payload FROM user_node_state_store ORDER BY node_id",
                (),
            )
        else:
            rows = self._fetch_all(
                """
                SELECT payload FROM user_node_state_store
                WHERE profile_space_id = ?
                ORDER BY node_id
                """,
                (profile_space_id,),
            )
        return [UserNodeState.from_json(row["payload"]) for row in rows]

    def upsert_knowledge_relation(self, relation: KnowledgeRelation) -> None:
        payload = relation.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_relation_store (
                    relation_id,
                    profile_space_id,
                    source_node_id,
                    target_node_id,
                    relation_type,
                    status,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relation.relation_id,
                    relation.profile_space_id,
                    relation.source_node_id,
                    relation.target_node_id,
                    relation.relation_type,
                    relation.status,
                    payload,
                ),
            )

    def list_knowledge_relations(
        self,
        profile_space_id: str | None = None,
        source_node_id: str | None = None,
        target_node_id: str | None = None,
        relation_type: str | None = None,
    ) -> list[KnowledgeRelation]:
        clauses: list[str] = []
        params: list[Any] = []
        if profile_space_id is not None:
            clauses.append("profile_space_id = ?")
            params.append(profile_space_id)
        if source_node_id is not None:
            clauses.append("source_node_id = ?")
            params.append(source_node_id)
        if target_node_id is not None:
            clauses.append("target_node_id = ?")
            params.append(target_node_id)
        if relation_type is not None:
            clauses.append("relation_type = ?")
            params.append(relation_type)
        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetch_all(
            f"SELECT payload FROM knowledge_relation_store{where_clause} ORDER BY relation_id",
            tuple(params),
        )
        return [KnowledgeRelation.from_json(row["payload"]) for row in rows]

    def upsert_focus_cluster(self, cluster: FocusCluster) -> None:
        payload = cluster.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO focus_cluster_store (
                    cluster_id,
                    profile_space_id,
                    center_node_id,
                    generated_from,
                    status,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cluster.cluster_id,
                    cluster.profile_space_id,
                    cluster.center_node_id,
                    cluster.generated_from,
                    cluster.status,
                    payload,
                ),
            )

    def list_focus_clusters(
        self,
        profile_space_id: str | None = None,
        status: str | None = None,
    ) -> list[FocusCluster]:
        clauses: list[str] = []
        params: list[Any] = []
        if profile_space_id is not None:
            clauses.append("profile_space_id = ?")
            params.append(profile_space_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetch_all(
            f"SELECT payload FROM focus_cluster_store{where_clause} ORDER BY cluster_id",
            tuple(params),
        )
        return [FocusCluster.from_json(row["payload"]) for row in rows]

    def upsert_focus_explanation(self, explanation: FocusExplanation) -> None:
        payload = explanation.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO focus_explanation_store (
                    explanation_id,
                    profile_space_id,
                    subject_type,
                    subject_id,
                    generated_by,
                    version,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    explanation.explanation_id,
                    explanation.profile_space_id,
                    explanation.subject_type,
                    explanation.subject_id,
                    explanation.generated_by,
                    explanation.version,
                    payload,
                ),
            )

    def get_focus_explanation(
        self,
        *,
        subject_type: str,
        subject_id: str,
        profile_space_id: str | None = None,
    ) -> FocusExplanation | None:
        clauses = ["subject_type = ?", "subject_id = ?"]
        params: list[Any] = [subject_type, subject_id]
        if profile_space_id is not None:
            clauses.append("profile_space_id = ?")
            params.append(profile_space_id)
        row = self._fetch_one(
            f"SELECT payload FROM focus_explanation_store WHERE {' AND '.join(clauses)} ORDER BY explanation_id LIMIT 1",
            tuple(params),
        )
        if row is None:
            return None
        return FocusExplanation.from_json(row["payload"])

    def insert_workflow_request(self, record: WorkflowRequestRecord) -> None:
        self._insert_json_record(
            table_name="workflow_requests",
            pk_column="request_id",
            pk_value=record.request_id,
            record=record,
            columns={
                "request_type": record.request_type,
                "project_id": record.project_id,
                "stage_id": record.stage_id,
                "requested_by": record.requested_by,
                "source": record.source,
                "status": record.status,
                "created_at": record.created_at,
            },
        )

    def get_workflow_request(self, request_id: str) -> WorkflowRequestRecord | None:
        row = self._fetch_one("SELECT payload FROM workflow_requests WHERE request_id = ?", (request_id,))
        if row is None:
            return None
        return WorkflowRequestRecord.from_json(row["payload"])

    def insert_workflow_run(self, record: WorkflowRunRecord) -> None:
        self._insert_json_record(
            table_name="workflow_runs",
            pk_column="run_id",
            pk_value=record.run_id,
            record=record,
            columns={
                "request_id": record.request_id,
                "run_type": record.run_type,
                "status": record.status,
                "started_at": record.started_at,
                "finished_at": record.finished_at,
                "supersedes_run_id": record.supersedes_run_id,
            },
        )

    def get_workflow_run(self, run_id: str) -> WorkflowRunRecord | None:
        row = self._fetch_one("SELECT payload FROM workflow_runs WHERE run_id = ?", (run_id,))
        if row is None:
            return None
        return WorkflowRunRecord.from_json(row["payload"])

    def insert_question_batch(self, record: QuestionBatchRecord) -> None:
        self._insert_json_record(
            table_name="question_batches",
            pk_column="question_batch_id",
            pk_value=record.question_batch_id,
            record=record,
            columns={
                "workflow_run_id": record.workflow_run_id,
                "project_id": record.project_id,
                "stage_id": record.stage_id,
                "generated_by": record.generated_by,
                "source": record.source,
                "batch_goal": record.batch_goal,
                "entry_question_id": record.entry_question_id,
                "status": record.status,
                "created_at": record.created_at,
            },
        )

    def get_question_batch(self, question_batch_id: str) -> QuestionBatchRecord | None:
        row = self._fetch_one("SELECT payload FROM question_batches WHERE question_batch_id = ?", (question_batch_id,))
        if row is None:
            return None
        return QuestionBatchRecord.from_json(row["payload"])

    def insert_question_items(self, records: list[QuestionItemRecord]) -> None:
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO question_items (
                        question_id,
                        question_batch_id,
                        question_type,
                        prompt,
                        intent,
                        difficulty_level,
                        order_index,
                        status,
                        created_at,
                        payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.question_id,
                        record.question_batch_id,
                        record.question_type,
                        record.prompt,
                        record.intent,
                        record.difficulty_level,
                        record.order_index,
                        record.status,
                        record.created_at,
                        record.to_json(),
                    ),
                )

    def list_question_items(self, question_batch_id: str) -> list[QuestionItemRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM question_items
            WHERE question_batch_id = ?
            ORDER BY order_index
            """,
            (question_batch_id,),
        )
        return [QuestionItemRecord.from_json(row["payload"]) for row in rows]

    def insert_answer_batch(self, record: AnswerBatchRecord) -> None:
        self._insert_json_record(
            table_name="answer_batches",
            pk_column="answer_batch_id",
            pk_value=record.answer_batch_id,
            record=record,
            columns={
                "question_batch_id": record.question_batch_id,
                "workflow_run_id": record.workflow_run_id,
                "submitted_by": record.submitted_by,
                "submission_mode": record.submission_mode,
                "completion_status": record.completion_status,
                "submitted_at": record.submitted_at,
                "status": record.status,
            },
        )

    def get_answer_batch(self, answer_batch_id: str) -> AnswerBatchRecord | None:
        row = self._fetch_one("SELECT payload FROM answer_batches WHERE answer_batch_id = ?", (answer_batch_id,))
        if row is None:
            return None
        return AnswerBatchRecord.from_json(row["payload"])

    def list_answer_batches(self, question_batch_id: str) -> list[AnswerBatchRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM answer_batches
            WHERE question_batch_id = ?
            ORDER BY submitted_at, answer_batch_id
            """,
            (question_batch_id,),
        )
        return [AnswerBatchRecord.from_json(row["payload"]) for row in rows]

    def insert_answer_items(self, records: list[AnswerItemRecord]) -> None:
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO answer_items (
                        answer_item_id,
                        answer_batch_id,
                        question_id,
                        answered_by,
                        answer_text,
                        answer_format,
                        order_index,
                        answered_at,
                        status,
                        revision_of_answer_item_id,
                        payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.answer_item_id,
                        record.answer_batch_id,
                        record.question_id,
                        record.answered_by,
                        record.answer_text,
                        record.answer_format,
                        record.order_index,
                        record.answered_at,
                        record.status,
                        record.revision_of_answer_item_id,
                        record.to_json(),
                    ),
                )

    def list_answer_items(self, answer_batch_id: str) -> list[AnswerItemRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM answer_items
            WHERE answer_batch_id = ?
            ORDER BY order_index
            """,
            (answer_batch_id,),
        )
        return [AnswerItemRecord.from_json(row["payload"]) for row in rows]

    def insert_evaluation_batch(self, record: EvaluationBatchRecord) -> None:
        self._insert_json_record(
            table_name="evaluation_batches",
            pk_column="evaluation_batch_id",
            pk_value=record.evaluation_batch_id,
            record=record,
            columns={
                "answer_batch_id": record.answer_batch_id,
                "workflow_run_id": record.workflow_run_id,
                "project_id": record.project_id,
                "stage_id": record.stage_id,
                "evaluated_by": record.evaluated_by,
                "evaluator_version": record.evaluator_version,
                "confidence": record.confidence,
                "status": record.status,
                "evaluated_at": record.evaluated_at,
                "supersedes_evaluation_batch_id": record.supersedes_evaluation_batch_id,
            },
        )

    def get_evaluation_batch(self, evaluation_batch_id: str) -> EvaluationBatchRecord | None:
        row = self._fetch_one(
            "SELECT payload FROM evaluation_batches WHERE evaluation_batch_id = ?",
            (evaluation_batch_id,),
        )
        if row is None:
            return None
        return EvaluationBatchRecord.from_json(row["payload"])

    def list_evaluation_batches(self, answer_batch_id: str) -> list[EvaluationBatchRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM evaluation_batches
            WHERE answer_batch_id = ?
            ORDER BY evaluated_at, evaluation_batch_id
            """,
            (answer_batch_id,),
        )
        return [EvaluationBatchRecord.from_json(row["payload"]) for row in rows]

    def insert_evaluation_items(self, records: list[EvaluationItemRecord]) -> None:
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO evaluation_items (
                        evaluation_item_id,
                        evaluation_batch_id,
                        question_id,
                        answer_item_id,
                        local_verdict,
                        confidence,
                        status,
                        evaluated_at,
                        payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.evaluation_item_id,
                        record.evaluation_batch_id,
                        record.question_id,
                        record.answer_item_id,
                        record.local_verdict,
                        record.confidence,
                        record.status,
                        record.evaluated_at,
                        record.to_json(),
                    ),
                )

    def list_evaluation_items(self, evaluation_batch_id: str) -> list[EvaluationItemRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM evaluation_items
            WHERE evaluation_batch_id = ?
            ORDER BY evaluation_item_id
            """,
            (evaluation_batch_id,),
        )
        return [EvaluationItemRecord.from_json(row["payload"]) for row in rows]

    def insert_evidence_spans(self, records: list[EvidenceSpanRecord]) -> None:
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO evidence_spans (
                        evidence_span_id,
                        evaluation_item_id,
                        answer_item_id,
                        span_type,
                        supports_dimension,
                        content,
                        start_offset,
                        end_offset,
                        created_at,
                        payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.evidence_span_id,
                        record.evaluation_item_id,
                        record.answer_item_id,
                        record.span_type,
                        record.supports_dimension,
                        record.content,
                        record.start_offset,
                        record.end_offset,
                        record.created_at,
                        record.to_json(),
                    ),
                )

    def list_evidence_spans(self, evaluation_item_id: str) -> list[EvidenceSpanRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM evidence_spans
            WHERE evaluation_item_id = ?
            ORDER BY created_at, evidence_span_id
            """,
            (evaluation_item_id,),
        )
        return [EvidenceSpanRecord.from_json(row["payload"]) for row in rows]

    def insert_assessment_fact_batch(self, record: AssessmentFactBatchRecord) -> None:
        self._insert_json_record(
            table_name="assessment_fact_batches",
            pk_column="assessment_fact_batch_id",
            pk_value=record.assessment_fact_batch_id,
            record=record,
            columns={
                "evaluation_batch_id": record.evaluation_batch_id,
                "workflow_run_id": record.workflow_run_id,
                "synthesized_by": record.synthesized_by,
                "synthesizer_version": record.synthesizer_version,
                "status": record.status,
                "synthesized_at": record.synthesized_at,
                "supersedes_assessment_fact_batch_id": record.supersedes_assessment_fact_batch_id,
            },
        )

    def get_latest_assessment_fact_batch(self, project_id: str, stage_id: str) -> AssessmentFactBatchRecord | None:
        row = self._fetch_one(
            """
            SELECT assessment_fact_batches.payload
            FROM assessment_fact_batches
            JOIN evaluation_batches
                ON evaluation_batches.evaluation_batch_id = assessment_fact_batches.evaluation_batch_id
            WHERE evaluation_batches.project_id = ? AND evaluation_batches.stage_id = ?
            ORDER BY assessment_fact_batches.synthesized_at DESC, assessment_fact_batches.assessment_fact_batch_id DESC
            LIMIT 1
            """,
            (project_id, stage_id),
        )
        if row is None:
            return None
        return AssessmentFactBatchRecord.from_json(row["payload"])

    def insert_assessment_fact_items(self, records: list[AssessmentFactItemRecord]) -> None:
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO assessment_fact_items (
                        assessment_fact_item_id,
                        assessment_fact_batch_id,
                        source_evaluation_item_id,
                        fact_type,
                        topic_key,
                        title,
                        confidence,
                        status,
                        created_at,
                        supersedes_assessment_fact_item_id,
                        payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.assessment_fact_item_id,
                        record.assessment_fact_batch_id,
                        record.source_evaluation_item_id,
                        record.fact_type,
                        record.topic_key,
                        record.title,
                        record.confidence,
                        record.status,
                        record.created_at,
                        record.supersedes_assessment_fact_item_id,
                        record.to_json(),
                    ),
                )

    def list_assessment_fact_items(self, assessment_fact_batch_id: str) -> list[AssessmentFactItemRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM assessment_fact_items
            WHERE assessment_fact_batch_id = ?
            ORDER BY created_at, assessment_fact_item_id
            """,
            (assessment_fact_batch_id,),
        )
        return [AssessmentFactItemRecord.from_json(row["payload"]) for row in rows]

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

    def upsert_answer_fact(self, fact: AnswerFact) -> None:
        payload = fact.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO answer_fact_store (
                    answer_id,
                    request_id,
                    project_id,
                    stage_id,
                    question_set_id,
                    question_id,
                    actor_id,
                    source_page,
                    created_at,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.answer_id,
                    fact.request_id,
                    fact.project_id,
                    fact.stage_id,
                    fact.question_set_id,
                    fact.question_id,
                    fact.actor_id,
                    fact.source_page,
                    fact.created_at,
                    payload,
                ),
            )

    def get_answer_fact(self, answer_id: str) -> AnswerFact | None:
        row = self._fetch_one(
            "SELECT payload FROM answer_fact_store WHERE answer_id = ?",
            (answer_id,),
        )
        if row is None:
            return None
        return AnswerFact.from_json(row["payload"])

    def list_answer_facts(self, project_id: str | None = None, stage_id: str | None = None) -> list[AnswerFact]:
        if project_id is None and stage_id is None:
            rows = self._fetch_all(
                "SELECT payload FROM answer_fact_store ORDER BY created_at, answer_id",
                (),
            )
        elif stage_id is None:
            rows = self._fetch_all(
                "SELECT payload FROM answer_fact_store WHERE project_id = ? ORDER BY created_at, answer_id",
                (project_id,),
            )
        else:
            rows = self._fetch_all(
                "SELECT payload FROM answer_fact_store WHERE project_id = ? AND stage_id = ? ORDER BY created_at, answer_id",
                (project_id, stage_id),
            )
        return [AnswerFact.from_json(row["payload"]) for row in rows]

    def upsert_assessment_fact(self, fact: AssessmentFact) -> None:
        payload = fact.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assessment_fact_store (
                    assessment_id,
                    request_id,
                    answer_id,
                    project_id,
                    stage_id,
                    question_set_id,
                    question_id,
                    verdict,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.assessment_id,
                    fact.request_id,
                    fact.answer_id,
                    fact.project_id,
                    fact.stage_id,
                    fact.question_set_id,
                    fact.question_id,
                    fact.verdict,
                    payload,
                ),
            )

    def get_assessment_fact(self, assessment_id: str) -> AssessmentFact | None:
        row = self._fetch_one(
            "SELECT payload FROM assessment_fact_store WHERE assessment_id = ?",
            (assessment_id,),
        )
        if row is None:
            return None
        return AssessmentFact.from_json(row["payload"])

    def list_assessment_facts(self, project_id: str | None = None, stage_id: str | None = None) -> list[AssessmentFact]:
        if project_id is None and stage_id is None:
            rows = self._fetch_all(
                "SELECT payload FROM assessment_fact_store ORDER BY assessment_id",
                (),
            )
        elif stage_id is None:
            rows = self._fetch_all(
                "SELECT payload FROM assessment_fact_store WHERE project_id = ? ORDER BY assessment_id",
                (project_id,),
            )
        else:
            rows = self._fetch_all(
                "SELECT payload FROM assessment_fact_store WHERE project_id = ? AND stage_id = ? ORDER BY assessment_id",
                (project_id, stage_id),
            )
        return [AssessmentFact.from_json(row["payload"]) for row in rows]
    def upsert_decision_fact(self, fact: DecisionFact) -> None:
        payload = fact.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO decision_fact_store (
                    decision_id,
                    request_id,
                    assessment_id,
                    project_id,
                    stage_id,
                    decision_type,
                    decision_value,
                    created_at,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.decision_id,
                    fact.request_id,
                    fact.assessment_id,
                    fact.project_id,
                    fact.stage_id,
                    fact.decision_type,
                    fact.decision_value,
                    fact.created_at,
                    payload,
                ),
            )

    def get_decision_fact(self, decision_id: str) -> DecisionFact | None:
        row = self._fetch_one(
            "SELECT payload FROM decision_fact_store WHERE decision_id = ?",
            (decision_id,),
        )
        if row is None:
            return None
        return DecisionFact.from_json(row["payload"])

    def list_decision_facts(self, project_id: str | None = None, stage_id: str | None = None) -> list[DecisionFact]:
        if project_id is None and stage_id is None:
            rows = self._fetch_all(
                "SELECT payload FROM decision_fact_store ORDER BY created_at, decision_id",
                (),
            )
        elif stage_id is None:
            rows = self._fetch_all(
                "SELECT payload FROM decision_fact_store WHERE project_id = ? ORDER BY created_at, decision_id",
                (project_id,),
            )
        else:
            rows = self._fetch_all(
                "SELECT payload FROM decision_fact_store WHERE project_id = ? AND stage_id = ? ORDER BY created_at, decision_id",
                (project_id, stage_id),
            )
        return [DecisionFact.from_json(row["payload"]) for row in rows]
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
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _fetch_one(self, query: str, params: tuple[Any, ...]) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(query, params).fetchone()

    def _fetch_all(self, query: str, params: tuple[Any, ...]) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def _insert_json_record(
        self,
        *,
        table_name: str,
        pk_column: str,
        pk_value: Any,
        record: Any,
        columns: dict[str, Any],
    ) -> None:
        column_names = [pk_column, *columns.keys(), "payload"]
        placeholders = ", ".join("?" for _ in column_names)
        values = [pk_value, *columns.values(), record.to_json()]
        with self._connect() as conn:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {table_name} ({", ".join(column_names)})
                VALUES ({placeholders})
                """,
                values,
            )

    def _dumps_payload(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _loads_payload(self, payload: str) -> dict[str, Any]:
        value = json.loads(payload)
        if isinstance(value, dict):
            return {str(key): item for key, item in value.items()}
        return {}







