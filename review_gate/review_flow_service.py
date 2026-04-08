from __future__ import annotations

from dataclasses import dataclass

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.agent_clients import AssessmentAgentClient, QuestionGenerationAgentClient
from review_gate.domain import AnswerFact, AssessmentFact, DecisionFact, ProjectReview, StageReview
from review_gate.storage_sqlite import SQLiteStore
from review_gate.view_dtos import (
    AssessmentSummaryDTO,
    ProjectStageItemDTO,
    ProjectViewDTO,
    QuestionSetViewDTO,
    QuestionSummaryDTO,
    QuestionViewDTO,
    StageViewDTO,
    SubmitAnswerResponseDTO,
)


@dataclass(slots=True)
class CurrentQuestionContext:
    project_id: str
    stage_id: str
    question_set_id: str
    question_id: str
    question_level: str
    question_prompt: str
    question_intent: str
    expected_signals: list[str]
    source_context: list[str]


class ReviewFlowService:
    _PROJECTS = {
        "proj-1": {
            "project_id": "proj-1",
            "project_label": "impl-phase-coach",
            "project_summary": "A local review workbench that keeps project progress, review rounds, and durable learning traces aligned.",
            "active_stage_id": "stage-1",
            "stages": [
                {
                    "stage_id": "stage-1",
                    "stage_label": "module-interface-boundary",
                    "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
                    "status": "in_progress",
                    "active_question_set_id": "set-1",
                },
                {
                    "stage_id": "stage-2",
                    "stage_label": "proposal-action-loop",
                    "stage_goal": "stabilize the minimal proposal action loop without widening the maintenance surface",
                    "status": "not_started",
                    "active_question_set_id": "set-2",
                },
            ],
        }
    }

    def __init__(
        self,
        *,
        question_generation_client: QuestionGenerationAgentClient | None = None,
        assessment_client: AssessmentAgentClient | None = None,
        store: SQLiteStore | None = None,
    ) -> None:
        self._question_generation_client = question_generation_client or QuestionGenerationAgentClient.for_testing()
        self._assessment_client = assessment_client or AssessmentAgentClient.for_testing()
        self._store = store
        self._stage_mastery_status: dict[tuple[str, str], str] = {}
        self._latest_assessments: dict[tuple[str, str], dict] = {}
        if self._store is not None:
            self._ensure_project_reviews_seeded()

    @classmethod
    def for_testing(cls) -> "ReviewFlowService":
        return cls()

    @classmethod
    def with_store(cls, store: SQLiteStore) -> "ReviewFlowService":
        return cls(store=store)

    def list_projects(self) -> list[dict]:
        return [
            {
                "project_id": project["project_id"],
                "project_label": project["project_label"],
                "project_summary": project["project_summary"],
                "active_stage_id": project["active_stage_id"],
                "active_stage_label": self._get_stage_definition(project["project_id"], project["active_stage_id"])["stage_label"],
            }
            for project in self._PROJECTS.values()
        ]

    def get_project_view(self, project_id: str) -> ProjectViewDTO:
        project = self._get_project_definition(project_id)
        stored_review = self._get_project_review(project_id)
        stage_reviews = {item.stage_id: item for item in stored_review.stage_reviews} if stored_review is not None else {}
        stage_items = [
            ProjectStageItemDTO(
                stage_id=stage["stage_id"],
                stage_label=(stage_reviews.get(stage["stage_id"]).stage_label if stage["stage_id"] in stage_reviews else stage["stage_label"]),
                status=(stage_reviews.get(stage["stage_id"]).status if stage["stage_id"] in stage_reviews else stage["status"]),
                mastery_status=self._get_stage_mastery_status(project_id, stage["stage_id"]),
                active_question_set_id=(
                    stage_reviews.get(stage["stage_id"]).active_question_set_id
                    if stage["stage_id"] in stage_reviews
                    else stage["active_question_set_id"]
                ),
            )
            for stage in project["stages"]
        ]
        return ProjectViewDTO(
            project_id=project["project_id"],
            project_label=project["project_label"],
            project_summary=project["project_summary"],
            active_stage_id=project["active_stage_id"],
            active_stage_label=self._get_stage_definition(project_id, project["active_stage_id"])["stage_label"],
            pending_proposal_count=0,
            mistake_count=0,
            knowledge_entry_count=0,
            stages=stage_items,
        )

    def get_stage_view(self, project_id: str, stage_id: str) -> StageViewDTO:
        stage = self._get_stage_definition(project_id, stage_id)
        stored_stage = self._get_stage_review(project_id, stage_id)
        return StageViewDTO(
            project_id=project_id,
            stage_id=stage_id,
            stage_label=stored_stage.stage_label if stored_stage is not None else stage["stage_label"],
            stage_goal=stored_stage.stage_goal if stored_stage is not None else stage["stage_goal"],
            status=stored_stage.status if stored_stage is not None else stage["status"],
            mastery_status=self._get_stage_mastery_status(project_id, stage_id),
            active_question_set_id=(stored_stage.active_question_set_id if stored_stage is not None else stage["active_question_set_id"]),
        )

    def get_question_set_view(self, project_id: str, stage_id: str, question_set_id: str) -> QuestionSetViewDTO:
        questions = [
            QuestionSummaryDTO(
                question_id=f"{question_set_id}-q-1",
                question_level="core",
                prompt=f"Explain the stage boundary for {question_set_id}.",
            ),
            QuestionSummaryDTO(
                question_id=f"{question_set_id}-q-2",
                question_level="why",
                prompt=f"Why does {question_set_id} use this boundary?",
            ),
        ]
        return QuestionSetViewDTO(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
            question_set_title=f"Question set {question_set_id}",
            status="active",
            question_count=len(questions),
            current_question_id=questions[0].question_id,
            questions=questions,
        )

    def get_question_view(
        self,
        project_id: str,
        stage_id: str,
        question_set_id: str,
        question_id: str,
    ) -> QuestionViewDTO:
        question_level = self._resolve_question_level(question_id)
        prompt_map = {
            "core": f"Explain the boundary for question {question_id}.",
            "why": f"Why do we use this boundary for question {question_id}?",
            "abstract": f"How does the boundary for question {question_id} generalize?",
        }
        intent_map = {
            "core": "Check current-stage understanding.",
            "why": "Check the reasoning behind the decision.",
            "abstract": "Check boundary transfer and abstraction.",
        }
        return QuestionViewDTO(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
            question_id=question_id,
            question_level=question_level,
            prompt=prompt_map[question_level],
            intent=intent_map[question_level],
            answer_placeholder="Write the answer for the current stage question.",
            allowed_actions=["submit_answer", "continue_answering", "deepen", "pause_review", "skip_and_continue_project"],
        )

    def generate_question_set(self, request: dict) -> dict:
        return self._question_generation_client.generate(request)

    def _get_project_definition(self, project_id: str) -> dict:
        return dict(self._PROJECTS.get(project_id, self._PROJECTS["proj-1"]))

    def _get_stage_definition(self, project_id: str, stage_id: str) -> dict:
        project = self._get_project_definition(project_id)
        for stage in project["stages"]:
            if stage["stage_id"] == stage_id:
                return dict(stage)
        return dict(project["stages"][0])

    def _build_current_question_context(self, request: SubmitAnswerRequest) -> CurrentQuestionContext:
        question_view = self.get_question_view(
            request.project_id,
            request.stage_id,
            request.question_set_id,
            request.question_id,
        )
        question_ref = f"{request.stage_id}:{request.question_set_id}:{request.question_id}"
        return CurrentQuestionContext(
            project_id=request.project_id,
            stage_id=request.stage_id,
            question_set_id=request.question_set_id,
            question_id=request.question_id,
            question_level=question_view.question_level,
            question_prompt=question_view.prompt,
            question_intent=question_view.intent,
            expected_signals=[request.stage_id, request.question_set_id, request.question_id, question_view.question_level],
            source_context=[question_ref],
        )

    def _resolve_question_level(self, question_id: str) -> str:
        lowered = question_id.lower()
        if "abstract" in lowered or lowered.endswith("-3"):
            return "abstract"
        if "why" in lowered or lowered.endswith("-2"):
            return "why"
        return "core"

    def _build_project_review(self, project_id: str) -> ProjectReview:
        project = self._get_project_definition(project_id)
        stage_reviews = [
            StageReview(
                stage_review_id=f"{project_id}:{stage['stage_id']}",
                project_id=project_id,
                stage_id=stage["stage_id"],
                stage_label=stage["stage_label"],
                stage_goal=stage["stage_goal"],
                status=stage["status"],
                question_set_ids=[stage["active_question_set_id"]] if stage.get("active_question_set_id") else [],
                active_question_set_id=stage.get("active_question_set_id"),
                history_count=1 if stage.get("active_question_set_id") else 0,
                retention_status="active",
                mastery_status=self._stage_mastery_status.get((project_id, stage["stage_id"]), "unverified"),
            )
            for stage in project["stages"]
        ]
        return ProjectReview(
            project_id=project_id,
            project_label=project["project_label"],
            project_summary=project["project_summary"],
            stage_reviews=stage_reviews,
            knowledge_index_id=f"knowledge-index:{project_id}",
            knowledge_graph_id=f"knowledge-graph:{project_id}",
            profile_space_id=f"profile-space:{project_id}",
            proposal_center_id=f"proposal-center:{project_id}",
        )

    def _ensure_project_reviews_seeded(self) -> None:
        if self._store is None:
            return
        for project_id in self._PROJECTS:
            if self._store.get_project_review(project_id) is None:
                self._store.upsert_project_review(self._build_project_review(project_id))

    def _get_project_review(self, project_id: str) -> ProjectReview | None:
        if self._store is None:
            return None
        review = self._store.get_project_review(project_id)
        if review is None:
            review = self._build_project_review(project_id)
            self._store.upsert_project_review(review)
        return review

    def _get_stage_review(self, project_id: str, stage_id: str) -> StageReview | None:
        review = self._get_project_review(project_id)
        if review is None:
            return None
        for stage_review in review.stage_reviews:
            if stage_review.stage_id == stage_id:
                return stage_review
        return None

    def _get_stage_mastery_status(self, project_id: str, stage_id: str) -> str:
        if self._store is None:
            return self._stage_mastery_status.get((project_id, stage_id), "unverified")

        decisions = [
            item
            for item in self._store.list_decision_facts(project_id=project_id, stage_id=stage_id)
            if item.decision_type == "stage_mastery"
        ]
        if decisions:
            return decisions[-1].decision_value

        stage_review = self._get_stage_review(project_id, stage_id)
        if stage_review is None:
            return "unverified"
        return stage_review.mastery_status
    def _set_stage_mastery_status(self, project_id: str, stage_id: str, mastery_status: str) -> None:
        if self._store is None:
            self._stage_mastery_status[(project_id, stage_id)] = mastery_status
            return

        review = self._get_project_review(project_id)
        if review is None:
            return
        for stage_review in review.stage_reviews:
            if stage_review.stage_id == stage_id:
                stage_review.mastery_status = mastery_status
                self._store.upsert_project_review(review)
                return

    def get_latest_assessment_snapshot(self, project_id: str, stage_id: str) -> dict | None:
        snapshot = self._latest_assessments.get((project_id, stage_id))
        if snapshot is not None:
            return dict(snapshot)

        if self._store is None:
            return None

        assessments = self._store.list_assessment_facts(project_id=project_id, stage_id=stage_id)
        if not assessments:
            return None
        return assessments[-1].to_dict()

    def submit_answer(self, request: SubmitAnswerRequest) -> SubmitAnswerResponseDTO:
        if not request.answer_text.strip():
            return SubmitAnswerResponseDTO(
                request_id=request.request_id,
                success=False,
                action_type="submit_answer",
                result_type="invalid_input",
                message="Answer text cannot be blank.",
                refresh_targets=[],
                assessment_summary=None,
            )

        current_question = self._build_current_question_context(request)
        answer_id = f"answer-{request.request_id}"
        assessment_response = self._assessment_client.assess(
            {
                "request_id": request.request_id,
                "project_id": current_question.project_id,
                "stage_id": current_question.stage_id,
                "question_set_id": current_question.question_set_id,
                "question_id": current_question.question_id,
                "question_level": current_question.question_level,
                "question_prompt": current_question.question_prompt,
                "question_intent": current_question.question_intent,
                "expected_signals": current_question.expected_signals,
                "user_answer": request.answer_text,
                "source_context": current_question.source_context,
                "current_stage_decisions": [],
                "current_stage_logic_points": [],
                "current_boundary_focus": [],
                "assessment_policy": {"mode": "simple"},
                "history_signals": [],
            }
        )
        assessment = dict(assessment_response["assessment"])
        verdict = assessment.get("verdict", "partial")
        answer_excerpt = request.answer_text.strip()[:120]
        assessment_id = f"assessment-{request.request_id}"
        assessment.update(
            {
                "assessment_id": assessment_id,
                "request_id": request.request_id,
                "answer_id": answer_id,
                "project_id": request.project_id,
                "stage_id": request.stage_id,
                "question_set_id": request.question_set_id,
                "question_id": request.question_id,
                "confidence": float(assessment_response.get("confidence", 0.0)),
            }
        )
        self._latest_assessments[(request.project_id, request.stage_id)] = assessment

        if self._store is not None:
            self._store.upsert_answer_fact(
                AnswerFact(
                    answer_id=answer_id,
                    request_id=request.request_id,
                    project_id=request.project_id,
                    stage_id=request.stage_id,
                    question_set_id=request.question_set_id,
                    question_id=request.question_id,
                    actor_id=request.actor_id,
                    source_page=request.source_page,
                    created_at=request.created_at,
                    answer_text=request.answer_text,
                    draft_id=request.draft_id,
                )
            )
            self._store.upsert_assessment_fact(AssessmentFact.from_dict(assessment))

        if verdict in {"partial", "strong"}:
            self._set_stage_mastery_status(request.project_id, request.stage_id, "partially_verified")
            if self._store is not None:
                self._store.upsert_decision_fact(
                    DecisionFact(
                        decision_id=f"decision-{request.request_id}",
                        request_id=request.request_id,
                        assessment_id=assessment_id,
                        project_id=request.project_id,
                        stage_id=request.stage_id,
                        decision_type="stage_mastery",
                        decision_value="partially_verified",
                        reason_summary=f"stage mastery promoted from {verdict} verdict",
                        created_at=request.created_at,
                    )
                )

        assessment_summary = AssessmentSummaryDTO(
            assessment_id=assessment_id,
            project_id=request.project_id,
            stage_id=request.stage_id,
            question_set_id=request.question_set_id,
            question_id=request.question_id,
            answer_excerpt=answer_excerpt,
        )
        return SubmitAnswerResponseDTO(
            request_id=request.request_id,
            success=True,
            action_type="submit_answer",
            result_type="assessment_created",
            message=f"Assessment created with verdict {verdict}.",
            refresh_targets=["question_detail", "stage_summary"],
            assessment_summary=assessment_summary,

        )

