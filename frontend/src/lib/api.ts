import { createContext, createElement, useContext, type ReactNode } from "react";

export type StageKnowledgeSummaryDTO = {
  knowledge_entry_count: number;
  mistake_count: number;
  latest_summary: string;
};

export type WorkspaceSessionDTO = {
  workspace_session_id: string;
  active_project_id: string | null;
  active_stage_id: string | null;
  active_panel: string;
  active_question_set_id: string | null;
  active_question_id: string | null;
  active_profile_space_id: string | null;
  active_proposal_center_id: string | null;
  last_opened_at: string;
  filters: Record<string, string>;
};

export type HomeProjectItemDTO = {
  project_id: string;
  project_label: string;
  project_summary: string;
  active_stage_id: string;
  active_stage_label: string;
  pending_proposal_count: number;
  mistake_count: number;
  knowledge_entry_count: number;
};

export type HomeViewDTO = {
  projects: HomeProjectItemDTO[];
  total_count: number;
  pending_proposal_count: number;
  active_project_id: string | null;
};

export type ProjectStageItemDTO = {
  stage_id: string;
  stage_label: string;
  status: string;
  mastery_status: string;
  active_question_set_id: string | null;
};

export type ProjectViewDTO = {
  project_id: string;
  project_label: string;
  project_summary: string;
  active_stage_id: string;
  active_stage_label: string;
  pending_proposal_count: number;
  mistake_count: number;
  knowledge_entry_count: number;
  stages: ProjectStageItemDTO[];
};

export type StageViewDTO = {
  project_id: string;
  stage_id: string;
  stage_label: string;
  stage_goal: string;
  status: string;
  mastery_status: string;
  active_question_set_id: string | null;
  knowledge_summary: StageKnowledgeSummaryDTO | null;
};

export type MistakeItemDTO = {
  mistake_id: string;
  label: string;
  mistake_type: string;
  project_id: string;
  stage_id: string;
  root_cause_summary: string;
  avoidance_summary: string;
  status: string;
};

export type MistakesViewDTO = {
  project_filter: string | null;
  stage_filter: string | null;
  items: MistakeItemDTO[];
  total_count: number;
};

export type KnowledgeIndexItemDTO = {
  entry_id: string;
  title: string;
  entry_type: string;
  summary: string;
  project_id: string;
  stage_id: string;
  linked_mistake_ids: string[];
  status?: string;
};

export type KnowledgeIndexViewDTO = {
  project_filter: string | null;
  stage_filter: string | null;
  items: KnowledgeIndexItemDTO[];
  total_count: number;
};

export type KnowledgeGraphNodeDTO = {
  node_id: string;
  label: string;
  node_type: string;
  project_id: string;
  stage_id: string;
  strength: number;
  linked_mistake_ids: string[];
  summary: string;
  status?: string;
};

export type KnowledgeGraphViewDTO = {
  project_filter: string | null;
  stage_filter: string | null;
  nodes: KnowledgeGraphNodeDTO[];
  total_count: number;
};

export type FocusClusterCardDTO = {
  cluster_id: string;
  title: string;
  center_node_id: string;
  neighbor_node_ids: string[];
  focus_reason_codes: string[];
  focus_reason_summary: string;
};

export type KnowledgeMapSummaryViewDTO = {
  focus_clusters: FocusClusterCardDTO[];
  current_weak_spots: string[];
  foundation_hotspots: string[];
};

export type KnowledgeNodeCardDTO = {
  node_id: string;
  label: string;
  node_type: string;
  abstract_level: string;
  scope: string;
  canonical_summary: string;
  mastery_status: string;
  review_needed: boolean;
  relation_preview: Array<Record<string, string>>;
  evidence_summary: Record<string, number>;
};

export type KnowledgeGraphMainViewDTO = {
  selected_cluster: FocusClusterCardDTO | null;
  nodes: KnowledgeNodeCardDTO[];
  relations: Array<Record<string, string>>;
};

export type ProposalItemDTO = {
  proposal_id: string;
  proposal_type: string;
  target_type: string;
  target_count: number;
  status: string;
  reason: string;
  preview_summary: string;
  latest_execution_status: string | null;
  latest_execution_summary: string | null;
};

export type ProposalsViewDTO = {
  items: ProposalItemDTO[];
  total_count: number;
  pending_count: number;
};

export type ProposalActionRequestDTO = {
  request_id: string;
  source_page: string;
  actor_id: string;
  created_at: string;
  proposal_id: string;
  action_type: string;
  selected_target_ids: string[];
};

export type ProposalActionResponseDTO = {
  request_id: string;
  success: boolean;
  action_type: string;
  result_type: string;
  message: string;
  refresh_targets: string[];
  proposal_id: string;
  proposal_status: string;
  execution_status: string | null;
  execution_summary: string | null;
};

export type QuestionSummaryDTO = {
  question_id: string;
  question_level: string;
  prompt: string;
  status: string;
};

export type QuestionSetViewDTO = {
  project_id: string;
  stage_id: string;
  question_set_id: string;
  question_set_title: string;
  status: string;
  question_count: number;
  current_question_id: string | null;
  questions: QuestionSummaryDTO[];
};

export type QuestionViewDTO = {
  project_id: string;
  stage_id: string;
  question_set_id: string;
  question_id: string;
  question_level: string;
  prompt: string;
  intent: string;
  answer_placeholder: string;
  allowed_actions: string[];
  status: string;
};

export type GenerateQuestionDTO = {
  question_id: string;
  question_level: string;
  prompt: string;
  intent: string;
  expected_signals: string[];
  source_context: string[];
};

export type GenerateQuestionSetRequestDTO = {
  request_id: string;
  project_id: string;
  stage_id: string;
  source_page: string;
  actor_id: string;
  created_at: string;
  stage_label: string;
  stage_goal: string;
  stage_summary: string;
  learning_goal: string;
  target_user_level: string;
  preferred_language: string;
  question_mix: string[];
  preferred_question_style: string;
  stage_artifacts: string[];
  stage_exit_criteria: string[];
  current_decisions: string[];
  key_logic_points: string[];
  known_weak_points: string[];
  boundary_focus: string[];
  question_strategy: string;
  max_questions: number;
  source_refs: string[];
};

export type GenerateQuestionSetResponseDTO = {
  request_id: string;
  questions: GenerateQuestionDTO[];
  generation_summary: string;
  coverage_notes: string[];
  warnings: string[];
  confidence: number;
};

export type SubmitAnswerRequestDTO = {
  request_id: string;
  project_id: string;
  stage_id: string;
  source_page: string;
  actor_id: string;
  created_at: string;
  question_set_id: string;
  question_id: string;
  answer_text: string;
  draft_id: string | null;
};

export type AssessmentSummaryDTO = {
  assessment_id: string;
  project_id: string;
  stage_id: string;
  question_set_id: string;
  question_id: string;
  answer_excerpt: string;
  status: string;
};

export type SubmitAnswerResponseDTO = {
  request_id: string;
  success: boolean;
  action_type: string;
  result_type: string;
  message: string;
  refresh_targets: string[];
  assessment_summary: AssessmentSummaryDTO | null;
};

export type AssessmentReviewViewDTO = {
  project_id: string;
  stage_id: string;
  has_assessment: boolean;
  assessment_id: string | null;
  question_set_id: string | null;
  question_id: string | null;
  verdict: string;
  verdict_label: string;
  score_percent: number;
  confidence_percent: number;
  answer_excerpt: string;
  review_title: string;
  review_summary: string;
  correct_points: string[];
  gap_points: string[];
  misconception_points: string[];
  evidence: string[];
  recommended_follow_up_questions: string[];
  learning_recommendations: string[];
  knowledge_updates: Array<Record<string, string>>;
  next_action_label: string;
};

export type ApiClient = {
  baseUrl: string;
  getWorkspaceSession(): Promise<WorkspaceSessionDTO>;
  saveWorkspaceSession(session: WorkspaceSessionDTO): Promise<WorkspaceSessionDTO>;
  getHomeView(): Promise<HomeViewDTO>;
  getProjectView(projectId: string): Promise<ProjectViewDTO>;
  getStageView(projectId: string, stageId: string): Promise<StageViewDTO>;
  getMistakesView(projectId?: string, stageId?: string): Promise<MistakesViewDTO>;
  getKnowledgeMapSummaryView(projectId?: string, stageId?: string): Promise<KnowledgeMapSummaryViewDTO>;
  getKnowledgeIndexView(projectId?: string, stageId?: string): Promise<KnowledgeIndexViewDTO>;
  getKnowledgeGraphView(projectId?: string, stageId?: string): Promise<KnowledgeGraphViewDTO>;
  getKnowledgeGraphMainView(
    projectId?: string,
    stageId?: string,
    clusterId?: string,
    nodeId?: string,
  ): Promise<KnowledgeGraphMainViewDTO>;
  getProposalsView(): Promise<ProposalsViewDTO>;
  submitProposalAction(request: ProposalActionRequestDTO): Promise<ProposalActionResponseDTO>;
  getQuestionSetView(
    projectId: string,
    stageId: string,
    questionSetId: string,
  ): Promise<QuestionSetViewDTO>;
  getQuestionView(
    projectId: string,
    stageId: string,
    questionSetId: string,
    questionId: string,
  ): Promise<QuestionViewDTO>;
  generateQuestionSet(request: GenerateQuestionSetRequestDTO): Promise<GenerateQuestionSetResponseDTO>;
  submitAnswer(request: SubmitAnswerRequestDTO): Promise<SubmitAnswerResponseDTO>;
  getLatestAssessmentReview(projectId: string, stageId: string): Promise<AssessmentReviewViewDTO>;
};

type FetchLike = typeof fetch;

function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
}

async function readJson<T>(fetchImpl: FetchLike, url: string, entityLabel: string): Promise<T> {
  const response = await fetchImpl(url, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Unable to load ${entityLabel}.`);
  }

  return (await response.json()) as T;
}

async function sendJson<TResponse>(
  fetchImpl: FetchLike,
  url: string,
  body: object,
  entityLabel: string,
  method = "POST",
): Promise<TResponse> {
  const response = await fetchImpl(url, {
    method,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Unable to submit ${entityLabel}.`);
  }

  return (await response.json()) as TResponse;
}

export function createApiClient(baseUrl = "/api", fetchImpl: FetchLike = fetch): ApiClient {
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);

  return {
    baseUrl: normalizedBaseUrl,
    getWorkspaceSession() {
      return readJson<WorkspaceSessionDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/workspace-session`,
        "workspace session",
      );
    },
    saveWorkspaceSession(session) {
      return sendJson<WorkspaceSessionDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/workspace-session`,
        session,
        "workspace session",
        "PUT",
      );
    },
    getHomeView() {
      return readJson<HomeViewDTO>(fetchImpl, `${normalizedBaseUrl}/home`, "home view");
    },
    getProjectView(projectId) {
      return readJson<ProjectViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/projects/${projectId}`,
        "project view",
      );
    },
    getStageView(projectId, stageId) {
      return readJson<StageViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/projects/${projectId}/stages/${stageId}`,
        "stage view",
      );
    },
    getMistakesView(projectId, stageId) {
      const query = new URLSearchParams();
      if (projectId) {
        query.set("project_id", projectId);
      }
      if (stageId) {
        query.set("stage_id", stageId);
      }
      const suffix = query.size > 0 ? `?${query.toString()}` : "";
      return readJson<MistakesViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/mistakes${suffix}`,
        "mistakes view",
      );
    },
    getKnowledgeMapSummaryView(projectId, stageId) {
      const query = new URLSearchParams();
      if (projectId) {
        query.set("project_id", projectId);
      }
      if (stageId) {
        query.set("stage_id", stageId);
      }
      const suffix = query.size > 0 ? `?${query.toString()}` : "";
      return readJson<KnowledgeMapSummaryViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/knowledge${suffix}`,
        "knowledge map summary view",
      );
    },
    getKnowledgeIndexView(projectId, stageId) {
      const query = new URLSearchParams();
      if (projectId) {
        query.set("project_id", projectId);
      }
      if (stageId) {
        query.set("stage_id", stageId);
      }
      const suffix = query.size > 0 ? `?${query.toString()}` : "";
      return readJson<KnowledgeIndexViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/knowledge/index${suffix}`,
        "knowledge index view",
      );
    },
    getKnowledgeGraphView(projectId, stageId) {
      const query = new URLSearchParams();
      if (projectId) {
        query.set("project_id", projectId);
      }
      if (stageId) {
        query.set("stage_id", stageId);
      }
      const suffix = query.size > 0 ? `?${query.toString()}` : "";
      return readJson<KnowledgeGraphViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/knowledge/graph${suffix}`,
        "knowledge graph view",
      );
    },
    getKnowledgeGraphMainView(projectId, stageId, clusterId, nodeId) {
      const query = new URLSearchParams();
      if (projectId) {
        query.set("project_id", projectId);
      }
      if (stageId) {
        query.set("stage_id", stageId);
      }
      if (clusterId) {
        query.set("cluster_id", clusterId);
      }
      if (nodeId) {
        query.set("node_id", nodeId);
      }
      const suffix = query.size > 0 ? `?${query.toString()}` : "";
      return readJson<KnowledgeGraphMainViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/knowledge/graph-main${suffix}`,
        "knowledge graph main view",
      );
    },
    getProposalsView() {
      return readJson<ProposalsViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/proposals`,
        "proposals view",
      );
    },
    submitProposalAction(request) {
      return sendJson<ProposalActionResponseDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/actions/proposal-action`,
        request,
        "proposal action",
      );
    },
    getQuestionSetView(projectId, stageId, questionSetId) {
      return readJson<QuestionSetViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/projects/${projectId}/stages/${stageId}/questions/${questionSetId}`,
        "question set view",
      );
    },
    getQuestionView(projectId, stageId, questionSetId, questionId) {
      return readJson<QuestionViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/projects/${projectId}/stages/${stageId}/questions/${questionSetId}/${questionId}`,
        "question view",
      );
    },
    generateQuestionSet(request) {
      return sendJson<GenerateQuestionSetResponseDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/actions/generate-question-set`,
        request,
        "question generation",
      );
    },
    submitAnswer(request) {
      return sendJson<SubmitAnswerResponseDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/actions/submit-answer`,
        request,
        "answer",
      );
    },
    getLatestAssessmentReview(projectId, stageId) {
      const query = new URLSearchParams();
      query.set("project_id", projectId);
      query.set("stage_id", stageId);
      return readJson<AssessmentReviewViewDTO>(
        fetchImpl,
        `${normalizedBaseUrl}/assessments/latest-review?${query.toString()}`,
        "latest assessment review",
      );
    },
  };
}

const defaultClient = createApiClient();
const ApiClientContext = createContext<ApiClient>(defaultClient);

export function ApiClientProvider({ client, children }: { client: ApiClient; children: ReactNode }) {
  return createElement(ApiClientContext.Provider, { value: client }, children);
}

export function useApiClient() {
  return useContext(ApiClientContext);
}
