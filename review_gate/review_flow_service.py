from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.agent_clients import AssessmentAgentClient, QuestionGenerationAgentClient
from review_gate.answer_checkpoint_writer import AnswerCheckpointWriter
from review_gate.assessment_synthesizer import AssessmentSynthesizer
from review_gate.checkpoint_models import (
    EvidenceSpanRecord,
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)
from review_gate.domain import AnswerFact, AssessmentFact, DecisionFact, ProjectReview, StageReview, WorkspaceEvent
from review_gate.evaluator_agent_prompt_builder import EvaluatorAgentPromptBuilder
from review_gate.evaluator_agent_response_normalizer import EvaluatorAgentResponseNormalizer
from review_gate.generated_chain_resolver import GeneratedChainResolver, ResolvedQuestionChain
from review_gate.project_agent_question_generation_client import ProjectAgentQuestionGenerationClient
from review_gate.project_agent_response_normalizer import ProjectAgentResponseNormalizer
from review_gate.question_checkpoint_writer import QuestionCheckpointWriter
from review_gate.question_set_generation_publisher import QuestionSetGenerationPublisher
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
    _SUPPORT_DIMENSION_BASIS = {
        "state_modeling": {
            "source_label": "State machine",
            "source_node_type": "foundation",
            "target_node_type": "concept",
        },
        "boundary_awareness": {
            "source_label": "Boundary discipline",
            "source_node_type": "foundation",
            "target_node_type": "method",
        },
        "decision_awareness": {
            "source_label": "Decision framing",
            "source_node_type": "concept",
            "target_node_type": "decision",
        },
    }

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
        question_generation_client: QuestionGenerationAgentClient | ProjectAgentQuestionGenerationClient | None = None,
        project_agent_response_normalizer: ProjectAgentResponseNormalizer | None = None,
        evaluator_agent_prompt_builder: EvaluatorAgentPromptBuilder | None = None,
        evaluator_agent_response_normalizer: EvaluatorAgentResponseNormalizer | None = None,
        assessment_client: AssessmentAgentClient | None = None,
        store: SQLiteStore | None = None,
    ) -> None:
        self._question_generation_client = question_generation_client or QuestionGenerationAgentClient.for_testing()
        self._project_agent_response_normalizer = project_agent_response_normalizer
        self._evaluator_agent_prompt_builder = evaluator_agent_prompt_builder
        self._evaluator_agent_response_normalizer = evaluator_agent_response_normalizer
        self._assessment_client = assessment_client or AssessmentAgentClient.for_testing()
        self._assessment_synthesizer = AssessmentSynthesizer()
        self._store = store
        self._generated_chain_resolver = GeneratedChainResolver(store=store) if store is not None else None
        self._question_checkpoint_writer = QuestionCheckpointWriter(store=store) if store is not None else None
        self._question_set_generation_publisher = (
            QuestionSetGenerationPublisher(store=store) if store is not None else None
        )
        self._answer_checkpoint_writer = (
            AnswerCheckpointWriter(store=store, synthesizer=self._assessment_synthesizer) if store is not None else None
        )
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

    @classmethod
    def with_local_project_agent(
        cls,
        *,
        store: SQLiteStore | None = None,
        root_dir: Path | None = None,
        model: str = "gpt-5.4",
    ) -> "ReviewFlowService":
        return cls(
            question_generation_client=ProjectAgentQuestionGenerationClient.from_local_config(
                root_dir=root_dir,
                model=model,
            ),
            project_agent_response_normalizer=ProjectAgentResponseNormalizer(),
            store=store,
        )

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
        generated_items = self._get_latest_generated_question_items(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
        )
        if generated_items:
            questions = [
                QuestionSummaryDTO(
                    question_id=self._transport_question_id(item),
                    question_level=item.difficulty_level or item.question_type,
                    prompt=item.prompt,
                    status=item.status,
                )
                for item in generated_items
            ]
            return QuestionSetViewDTO(
                project_id=project_id,
                stage_id=stage_id,
                question_set_id=question_set_id,
                question_set_title=f"Generated question set {question_set_id}",
                status="active",
                question_count=len(questions),
                current_question_id=self._resolve_current_question_id(questions),
                questions=questions,
            )

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

    @staticmethod
    def _resolve_current_question_id(questions: list[QuestionSummaryDTO]) -> str | None:
        for question in questions:
            if question.status not in {"answered", "assessed", "completed", "submitted"}:
                return question.question_id
        if not questions:
            return None
        return questions[0].question_id

    def project_exists(self, project_id: str | None) -> bool:
        return project_id is not None and project_id in self._PROJECTS

    def stage_exists(self, project_id: str | None, stage_id: str | None) -> bool:
        if not self.project_exists(project_id) or stage_id is None:
            return False
        project = self._PROJECTS[project_id]
        return any(stage["stage_id"] == stage_id for stage in project["stages"])

    def question_set_exists(self, project_id: str | None, stage_id: str | None, question_set_id: str | None) -> bool:
        if not self.stage_exists(project_id, stage_id) or question_set_id is None:
            return False
        stage = self._get_stage_review(project_id, stage_id)
        if stage is not None and stage.active_question_set_id is not None:
            return question_set_id == stage.active_question_set_id
        stage_definition = self._get_stage_definition(project_id, stage_id)
        return question_set_id == stage_definition.get("active_question_set_id")

    def question_exists(
        self,
        project_id: str | None,
        stage_id: str | None,
        question_set_id: str | None,
        question_id: str | None,
    ) -> bool:
        if not self.question_set_exists(project_id, stage_id, question_set_id) or question_id is None:
            return False
        if (
            project_id is not None
            and stage_id is not None
            and question_set_id is not None
            and self._get_generated_question_item(
                project_id=project_id,
                stage_id=stage_id,
                question_set_id=question_set_id,
                transport_question_id=question_id,
            )
            is not None
        ):
            return True
        expected_ids = {
            f"{question_set_id}-q-1",
            f"{question_set_id}-q-2",
            f"{question_set_id}-q-3",
        }
        return question_id in expected_ids

    def get_question_view(
        self,
        project_id: str,
        stage_id: str,
        question_set_id: str,
        question_id: str,
    ) -> QuestionViewDTO:
        generated_item = self._get_generated_question_item(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
            transport_question_id=question_id,
        )
        if generated_item is not None:
            return QuestionViewDTO(
                project_id=project_id,
                stage_id=stage_id,
                question_set_id=question_set_id,
                question_id=question_id,
                question_level=generated_item.difficulty_level or generated_item.question_type,
                prompt=generated_item.prompt,
                intent=generated_item.intent,
                answer_placeholder="Answer the generated question for the current stage.",
                allowed_actions=["submit_answer", "continue_answering", "deepen", "pause_review", "skip_and_continue_project"],
                status=generated_item.status,
            )

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

    def _get_latest_generated_question_items(
        self,
        *,
        project_id: str,
        stage_id: str,
        question_set_id: str,
    ) -> list[QuestionItemRecord]:
        if self._store is None:
            return []
        for event in reversed(self._store.list_events(project_id=project_id)):
            if event.event_type != "question_set_generated":
                continue
            if str(event.payload.get("stage_id", "")).strip() != stage_id:
                continue
            if str(event.payload.get("question_set_id", "")).strip() != question_set_id:
                continue
            question_batch_id = str(event.payload.get("question_batch_id", "")).strip()
            if not question_batch_id:
                continue
            question_batch = self._store.get_question_batch(question_batch_id)
            if question_batch is None:
                continue
            return self._store.list_question_items(question_batch.question_batch_id)
        return []

    def _get_generated_question_item(
        self,
        *,
        project_id: str,
        stage_id: str,
        question_set_id: str,
        transport_question_id: str,
    ) -> QuestionItemRecord | None:
        for item in self._get_latest_generated_question_items(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
        ):
            if self._transport_question_id(item) == transport_question_id:
                return item
        return None

    @staticmethod
    def _transport_question_id(item: QuestionItemRecord) -> str:
        return str(item.payload.get("transport_question_id", item.question_id))

    def generate_question_set(self, request: dict) -> dict:
        response = self._question_generation_client.generate(request)
        response = self._normalize_question_generation_response(request=request, response=response)
        if self._question_checkpoint_writer is not None and self._question_set_generation_publisher is not None:
            self._persist_question_generation_checkpoint(request, response)
        return response

    def _normalize_question_generation_response(self, *, request: dict, response: dict) -> dict:
        if self._project_agent_response_normalizer is None:
            return response
        if "raw_content" not in response:
            return response
        return self._project_agent_response_normalizer.normalize(request=request, raw_result=response)

    def _normalize_assessment_response(self, *, request: SubmitAnswerRequest, response: dict) -> dict:
        if self._evaluator_agent_response_normalizer is None:
            return response
        if "raw_content" not in response:
            return response
        return self._evaluator_agent_response_normalizer.normalize(
            request={
                "request_id": request.request_id,
                "project_id": request.project_id,
                "stage_id": request.stage_id,
                "question_set_id": request.question_set_id,
                "question_id": request.question_id,
            },
            raw_result=response,
        )

    def _build_assessment_request_payload(
        self,
        *,
        request: SubmitAnswerRequest,
        current_question: CurrentQuestionContext,
    ) -> dict:
        if self._evaluator_agent_prompt_builder is None:
            return {
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

        prompt = self._evaluator_agent_prompt_builder.build(
            {
                "request_id": request.request_id,
                "project_context": self._get_project_definition(request.project_id)["project_summary"],
                "stage_context": self._get_stage_definition(request.project_id, request.stage_id)["stage_goal"],
                "question_context": f"{current_question.question_level}: {current_question.question_prompt}",
                "answer_text": request.answer_text,
                "current_decisions": current_question.expected_signals,
                "boundary_focus": current_question.source_context,
            }
        )
        return {
            "request_id": request.request_id,
            "messages": [
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "output_contract": prompt.output_contract,
        }

    def _get_project_definition(self, project_id: str) -> dict:
        return dict(self._PROJECTS.get(project_id, self._PROJECTS["proj-1"]))

    def _get_stage_definition(self, project_id: str, stage_id: str) -> dict:
        project = self._get_project_definition(project_id)
        for stage in project["stages"]:
            if stage["stage_id"] == stage_id:
                return dict(stage)
        return dict(project["stages"][0])

    def _build_current_question_context(
        self,
        request: SubmitAnswerRequest,
        *,
        resolved_chain: ResolvedQuestionChain | None = None,
    ) -> CurrentQuestionContext:
        generated_context = self._build_generated_question_context(request, resolved_chain=resolved_chain)
        if generated_context is not None:
            return generated_context

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

    def _build_generated_question_context(
        self,
        request: SubmitAnswerRequest,
        *,
        resolved_chain: ResolvedQuestionChain | None,
    ) -> CurrentQuestionContext | None:
        if resolved_chain is None:
            return None

        generated_item = resolved_chain.generated_item
        if generated_item is None:
            return None

        return CurrentQuestionContext(
            project_id=request.project_id,
            stage_id=request.stage_id,
            question_set_id=request.question_set_id,
            question_id=request.question_id,
            question_level=generated_item.difficulty_level or generated_item.question_type,
            question_prompt=generated_item.prompt,
            question_intent=generated_item.intent,
            expected_signals=self._coerce_str_list(generated_item.payload.get("expected_signals")),
            source_context=self._coerce_str_list(generated_item.payload.get("source_context")),
        )

    def _resolve_question_level(self, question_id: str) -> str:
        lowered = question_id.lower()
        if "abstract" in lowered or lowered.endswith("-3"):
            return "abstract"
        if "why" in lowered or lowered.endswith("-2"):
            return "why"
        return "core"

    @staticmethod
    def _coerce_str_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            items = value
        elif isinstance(value, tuple):
            items = list(value)
        elif isinstance(value, dict):
            items = list(value.keys())
        else:
            items = [value]
        return [str(item) for item in items if str(item).strip()]

    def _resolve_question_chain_for_submit(self, request: SubmitAnswerRequest) -> ResolvedQuestionChain | None:
        if self._generated_chain_resolver is None:
            return None
        return self._generated_chain_resolver.resolve(
            project_id=request.project_id,
            stage_id=request.stage_id,
            question_set_id=request.question_set_id,
            transport_question_id=request.question_id,
            request_id=request.request_id,
            created_at=request.created_at,
        )

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

        resolved_chain = self._resolve_question_chain_for_submit(request)
        current_question = self._build_current_question_context(request, resolved_chain=resolved_chain)
        answer_id = f"answer-{request.request_id}"
        assessment_response = self._assessment_client.assess(
            self._build_assessment_request_payload(request=request, current_question=current_question)
        )
        assessment_response = self._normalize_assessment_response(request=request, response=assessment_response)
        assessment = dict(assessment_response["assessment"])
        verdict = assessment.get("verdict", "partial")
        answer_excerpt = request.answer_text.strip()[:120]
        assessment_id = f"assessment-{request.request_id}"
        assessment["dimension_hits"] = self._derive_dimension_hits(assessment)
        assessment["support_signals"] = self._derive_support_signals(assessment)
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
                "answer_excerpt": answer_excerpt,
                "recommended_action": str(assessment_response.get("recommended_action", "")),
                "recommended_follow_up_questions": self._coerce_str_list(
                    assessment_response.get("recommended_follow_up_questions")
                ),
                "learning_recommendations": self._coerce_str_list(
                    assessment_response.get("learning_recommendations")
                ),
            }
        )
        self._latest_assessments[(request.project_id, request.stage_id)] = assessment

        if self._store is not None:
            writer_assessment = {
                "verdict": verdict,
                "score": float(assessment_response.get("confidence", 0.0)),
                "summary": f"Assessment verdict {verdict} for {request.question_id}.",
                "gaps": list(assessment.get("core_gaps", [])),
                "dimensions": list(assessment.get("dimension_hits", [])),
            }
            writer_support_signals = [
                dict(item)
                for item in assessment.get("support_signals", [])
                if isinstance(item, dict)
            ]
            if writer_support_signals:
                writer_assessment["support_signals"] = writer_support_signals
            if resolved_chain is None:
                resolved_chain = self._resolve_question_chain_for_submit(request)
            if resolved_chain is None:
                raise RuntimeError("Generated chain resolver is required when checkpoint store is enabled")
            self._answer_checkpoint_writer.write(
                request=request,
                resolved_chain=resolved_chain,
                assessment=writer_assessment,
            )
            evidence_spans = self._build_submit_evidence_spans(
                request_id=request.request_id,
                created_at=request.created_at,
                evidence=list(assessment_response["assessment"].get("evidence", [])),
            )
            if evidence_spans:
                self._store.insert_evidence_spans(evidence_spans)
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
            self._mark_resolved_question_answered(resolved_chain)

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
            refresh_targets=["question_detail", "stage_summary", "question_set"],
            assessment_summary=assessment_summary,

        )

    def _mark_resolved_question_answered(self, resolved_chain: ResolvedQuestionChain | None) -> None:
        if self._store is None or resolved_chain is None:
            return

        for item in self._store.list_question_items(resolved_chain.question_batch_id):
            if item.question_id != resolved_chain.question_item_id:
                continue
            if item.status == "answered":
                return
            self._store.insert_question_items([replace(item, status="answered")])
            return

    def _persist_question_generation_checkpoint(self, request: dict, response: dict) -> None:
        question_set_id = self._resolve_stage_question_set_id(
            project_id=str(request["project_id"]),
            stage_id=str(request["stage_id"]),
        )
        persisted_generation = self._question_checkpoint_writer.write(
            request=request,
            response=response,
            question_set_id=question_set_id,
        )
        self._question_set_generation_publisher.publish(
            request_id=str(request["request_id"]),
            project_id=str(request["project_id"]),
            stage_id=str(request["stage_id"]),
            question_set_id=question_set_id,
            question_batch_id=persisted_generation.question_batch_id,
            workflow_run_id=persisted_generation.workflow_run_id,
            question_item_ids=persisted_generation.question_item_ids,
            created_at=str(request.get("created_at", "")),
        )

    def _resolve_stage_question_set_id(self, *, project_id: str, stage_id: str) -> str:
        stage = self._get_stage_review(project_id, stage_id)
        if stage is not None and stage.active_question_set_id:
            return stage.active_question_set_id
        return str(self._get_stage_definition(project_id, stage_id).get("active_question_set_id", ""))

    def _build_submit_evidence_spans(
        self,
        *,
        request_id: str,
        created_at: str,
        evidence: list[str],
    ) -> list[EvidenceSpanRecord]:
        evaluation_item_id = f"ei-{request_id}-0"
        answer_item_id = f"ai-{request_id}-0"
        spans: list[EvidenceSpanRecord] = []
        for index, item in enumerate(evidence):
            content = str(item)
            spans.append(
                EvidenceSpanRecord(
                    evidence_span_id=f"es-{request_id}-{index}",
                    evaluation_item_id=evaluation_item_id,
                    answer_item_id=answer_item_id,
                    span_type="quoted_text",
                    supports_dimension="assessment",
                    content=content,
                    start_offset=0 if content else None,
                    end_offset=len(content) if content else None,
                    created_at=created_at,
                    payload={"evidence_index": index},
                )
            )
        return spans

    def _derive_dimension_hits(self, assessment: dict) -> list[str]:
        dimension_scores = assessment.get("dimension_scores", {})
        if not isinstance(dimension_scores, dict):
            return []
        return [
            key
            for key, value in dimension_scores.items()
            if key in self._SUPPORT_DIMENSION_BASIS and int(value) <= 2
        ]

    def _derive_support_signals(self, assessment: dict) -> list[dict[str, str]]:
        derived: list[dict[str, str]] = []
        support_basis_tags = assessment.get("support_basis_tags", [])
        core_gaps = [str(item).strip() for item in assessment.get("core_gaps", []) if str(item).strip()]
        dimension_hits = [str(item).strip() for item in assessment.get("dimension_hits", []) if str(item).strip()]

        for item in support_basis_tags:
            if not isinstance(item, dict):
                continue
            source_label = str(item.get("source_label", "")).strip()
            source_node_type = str(item.get("source_node_type", "")).strip()
            target_label = str(item.get("target_label", "")).strip()
            target_node_type = str(item.get("target_node_type", "")).strip()
            basis_key = str(item.get("basis_key", "")).strip()
            if not (source_label and source_node_type and target_label and target_node_type and basis_key):
                continue
            derived.append(
                {
                    "source_label": source_label,
                    "source_node_type": source_node_type,
                    "target_label": target_label,
                    "target_node_type": target_node_type,
                    "basis_type": "support_basis_tag",
                    "basis_key": basis_key,
                }
            )

        if not core_gaps:
            return self._dedupe_support_signals(derived)

        for basis_key in dimension_hits:
            basis = self._SUPPORT_DIMENSION_BASIS.get(basis_key)
            if basis is None:
                continue
            for gap in core_gaps:
                inferred_target_node_type = self._infer_support_target_node_type(gap)
                if inferred_target_node_type != basis["target_node_type"]:
                    continue
                derived.append(
                    {
                        "source_label": basis["source_label"],
                        "source_node_type": basis["source_node_type"],
                        "target_label": gap,
                        "target_node_type": basis["target_node_type"],
                        "basis_type": "dimension_hit",
                        "basis_key": basis_key,
                    }
                )

        return self._dedupe_support_signals(derived)

    def _infer_support_target_node_type(self, gap_label: str) -> str:
        lowered = gap_label.strip().lower()
        if "decision" in lowered:
            return "decision"
        if any(token in lowered for token in {"discipline", "strategy", "method", "workflow", "practice"}):
            return "method"
        return "concept"

    def _dedupe_support_signals(self, items: list[dict[str, str]]) -> list[dict[str, str]]:
        deduped: list[dict[str, str]] = []
        seen: set[tuple[str, str, str, str, str, str]] = set()
        for item in items:
            key = (
                item.get("source_label", ""),
                item.get("source_node_type", ""),
                item.get("target_label", ""),
                item.get("target_node_type", ""),
                item.get("basis_type", ""),
                item.get("basis_key", ""),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

