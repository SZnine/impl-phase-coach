import "@testing-library/jest-dom/vitest";

import type { ReactElement } from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import {
  ApiClientProvider,
  type ApiClient,
  type FocusClusterCardDTO,
  type HomeViewDTO,
  type KnowledgeGraphMainViewDTO,
  type KnowledgeGraphViewDTO,
  type KnowledgeIndexViewDTO,
  type KnowledgeMapSummaryViewDTO,
  type KnowledgeNodeCardDTO,
  type MistakesViewDTO,
  type ProjectViewDTO,
  type ProposalActionResponseDTO,
  type ProposalsViewDTO,
  type QuestionSetViewDTO,
  type QuestionViewDTO,
  type StageViewDTO,
  type SubmitAnswerResponseDTO,
  type AssessmentReviewViewDTO,
} from "./lib/api";
import { HomePage } from "./pages/HomePage";
import { KnowledgeMapPage } from "./pages/KnowledgeMapPage";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraphPage";
import { KnowledgeIndexPage } from "./pages/KnowledgeIndexPage";
import { MistakesPage } from "./pages/MistakesPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProposalsPage } from "./pages/ProposalsPage";
import { QuestionPage } from "./pages/QuestionPage";
import { QuestionSetPage } from "./pages/QuestionSetPage";
import { StagePage } from "./pages/StagePage";

function renderWithClient(ui: ReactElement, client: ApiClient, path: string) {
  return render(
    <ApiClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/" element={ui} />
          <Route path="/projects/:projectId" element={ui} />
          <Route path="/projects/:projectId/stages/:stageId" element={ui} />
          <Route path="/projects/:projectId/stages/:stageId/questions/:questionSetId" element={ui} />
          <Route path="/projects/:projectId/stages/:stageId/questions/:questionSetId/:questionId" element={ui} />
          <Route path="/mistakes" element={ui} />
          <Route path="/knowledge" element={ui} />
          <Route path="/knowledge/index" element={ui} />
          <Route path="/knowledge/graph" element={ui} />
          <Route path="/proposals" element={ui} />
        </Routes>
      </MemoryRouter>
    </ApiClientProvider>,
  );
}

const homeView: HomeViewDTO = {
  total_count: 1,
  pending_proposal_count: 1,
  active_project_id: "proj-1",
  projects: [
    {
      project_id: "proj-1",
      project_label: "impl-phase-coach",
      project_summary: "A local review workbench that keeps project progress, review rounds, and durable learning traces aligned.",
      active_stage_id: "stage-1",
      active_stage_label: "module-interface-boundary",
      pending_proposal_count: 1,
      mistake_count: 1,
      knowledge_entry_count: 1,
    },
  ],
};

const projectView: ProjectViewDTO = {
  project_id: "proj-1",
  project_label: "impl-phase-coach",
  project_summary: "A local review workbench that keeps project progress, review rounds, and durable learning traces aligned.",
  active_stage_id: "stage-1",
  active_stage_label: "module-interface-boundary",
  pending_proposal_count: 1,
  mistake_count: 1,
  knowledge_entry_count: 1,
  stages: [
    {
      stage_id: "stage-1",
      stage_label: "module-interface-boundary",
      status: "in_progress",
      mastery_status: "partially_verified",
      active_question_set_id: "set-1",
    },
    {
      stage_id: "stage-2",
      stage_label: "proposal-action-loop",
      status: "not_started",
      mastery_status: "unverified",
      active_question_set_id: "set-2",
    },
  ],
};

const stageView: StageViewDTO = {
  project_id: "proj-1",
  stage_id: "stage-1",
  stage_label: "Validation stage",
  stage_goal: "Confirm boundary handling",
  status: "in_progress",
  mastery_status: "unverified",
  active_question_set_id: "set-1",
  knowledge_summary: {
    knowledge_entry_count: 1,
    mistake_count: 1,
    latest_summary: "synced partial assessment with 1 knowledge entries and 1 mistakes",
  },
};

const mistakesView: MistakesViewDTO = {
  project_filter: null,
  stage_filter: null,
  total_count: 1,
  items: [
    {
      mistake_id: "proj-1:stage-1:a-1:mistake-1",
      label: "Decision awareness",
      mistake_type: "reasoning_gap",
      project_id: "proj-1",
      stage_id: "stage-1",
      root_cause_summary: "Decision awareness",
      avoidance_summary: "Review the stage boundary and revisit: Decision awareness",
      status: "active",
    },
  ],
};

const knowledgeGraphView: KnowledgeGraphViewDTO = {
  project_filter: null,
  stage_filter: null,
  total_count: 1,
  nodes: [
    {
      node_id: "proj-1:stage-1:a-1:node-1",
      label: "Decision awareness",
      node_type: "decision",
      project_id: "proj-1",
      stage_id: "stage-1",
      strength: 2,
      linked_mistake_ids: ["proj-1:stage-1:a-1:mistake-1"],
      summary: "Derived from partial assessment in stage-1.",
      status: "active",
    },
  ],
};

const focusClusterCard: FocusClusterCardDTO = {
  cluster_id: "cluster-1",
  title: "State boundary hotspot",
  center_node_id: "node-1",
  neighbor_node_ids: ["node-2"],
  focus_reason_codes: ["current_project_hit", "weak_signal_active"],
  focus_reason_summary: "Current stage exposed a repeated boundary weakness.",
};

const knowledgeMapSummaryView: KnowledgeMapSummaryViewDTO = {
  focus_clusters: [focusClusterCard],
  current_weak_spots: ["State and return value separation"],
  foundation_hotspots: [],
};

const knowledgeGraphMainNode: KnowledgeNodeCardDTO = {
  node_id: "node-1",
  label: "State and return value separation",
  node_type: "concept",
  abstract_level: "L1",
  scope: "project-bound",
  canonical_summary: "Derived from partial assessment in stage-1.",
  mastery_status: "partial",
  review_needed: true,
  relation_preview: [],
  evidence_summary: { evidence_count: 1 },
};

const knowledgeGraphMainNeighborNode: KnowledgeNodeCardDTO = {
  node_id: "node-2",
  label: "Boundary confusion",
  node_type: "mistake",
  abstract_level: "L1",
  scope: "personal",
  canonical_summary: "Repeated misconception around the current boundary.",
  mastery_status: "partial",
  review_needed: true,
  relation_preview: [],
  evidence_summary: { evidence_count: 1 },
};

const knowledgeGraphMainView: KnowledgeGraphMainViewDTO = {
  selected_cluster: focusClusterCard,
  nodes: [knowledgeGraphMainNode, knowledgeGraphMainNeighborNode],
  relations: [
    {
      relation_id: "relation-1",
      source_node_id: "node-1",
      target_node_id: "node-2",
      relation_type: "causes_mistake",
    },
  ],
};

const knowledgeGraphMainViewWithSupports: KnowledgeGraphMainViewDTO = {
  selected_cluster: {
    ...focusClusterCard,
    neighbor_node_ids: ["node-2", "node-3"],
  },
  nodes: [
    knowledgeGraphMainNode,
    knowledgeGraphMainNeighborNode,
    {
      node_id: "node-3",
      label: "State machine",
      node_type: "foundation",
      abstract_level: "L1",
      scope: "universal",
      canonical_summary: "A control-model primitive for staged flow handling.",
      mastery_status: "partial",
      review_needed: true,
      relation_preview: [],
      evidence_summary: { evidence_count: 1 },
    },
  ],
  relations: [
    {
      relation_id: "relation-1",
      source_node_id: "node-1",
      target_node_id: "node-2",
      relation_type: "causes_mistake",
    },
    {
      relation_id: "relation-2",
      source_node_id: "node-3",
      target_node_id: "node-1",
      relation_type: "supports",
    },
  ],
};

const knowledgeIndexView: KnowledgeIndexViewDTO = {
  project_filter: null,
  stage_filter: null,
  total_count: 1,
  items: [
    {
      entry_id: "proj-1:stage-1:a-1:index-1",
      title: "Decision awareness",
      entry_type: "mistake_avoidance",
      summary: "Revisit why this stage needs: Decision awareness",
      project_id: "proj-1",
      stage_id: "stage-1",
      linked_mistake_ids: ["proj-1:stage-1:a-1:mistake-1"],
    },
  ],
};

const proposalsView: ProposalsViewDTO = {
  total_count: 1,
  pending_count: 1,
  items: [
    {
      proposal_id: "proposal-1",
      proposal_type: "compress_mistake_entries",
      target_type: "mistake_entries",
      target_count: 2,
      status: "pending_review",
      reason: "Compress 2 mistake_entries",
      preview_summary: "Would compress 2 targets from mistake_entries.",
      latest_execution_status: null,
      latest_execution_summary: null,
    },
  ],
};

const proposalsViewAfterAccept: ProposalsViewDTO = {
  total_count: 1,
  pending_count: 0,
  items: [
    {
      proposal_id: "proposal-1",
      proposal_type: "compress_mistake_entries",
      target_type: "mistake_entries",
      target_count: 2,
      status: "accepted",
      reason: "Compress 2 mistake_entries",
      preview_summary: "Would compress 2 targets from mistake_entries.",
      latest_execution_status: "succeeded",
      latest_execution_summary: "accept on proposal-1 => succeeded",
    },
  ],
};

const questionSetView: QuestionSetViewDTO = {
  project_id: "proj-1",
  stage_id: "stage-1",
  question_set_id: "set-1",
  question_set_title: "Stage-1 review set",
  status: "active",
  question_count: 3,
  current_question_id: "q-2",
  questions: [
    {
      question_id: "q-1",
      question_level: "core",
      prompt: "What is the core boundary here?",
      status: "answered",
    },
    {
      question_id: "q-2",
      question_level: "why",
      prompt: "Why is this boundary necessary?",
      status: "ready",
    },
    {
      question_id: "q-3",
      question_level: "scenario",
      prompt: "What failure scenario should be checked next?",
      status: "ready",
    },
  ],
};

const questionView: QuestionViewDTO = {
  project_id: "proj-1",
  stage_id: "stage-1",
  question_set_id: "set-1",
  question_id: "q-2",
  question_level: "why",
  prompt: "Why is this boundary necessary?",
  intent: "Check whether the user can explain the separation between read and write flows.",
  answer_placeholder: "Answer in your own words",
  allowed_actions: ["continue_answering", "deepen", "pause_review", "skip_and_continue_project"],
  status: "ready",
};

const assessmentReviewView: AssessmentReviewViewDTO = {
  project_id: "proj-1",
  stage_id: "stage-1",
  has_assessment: true,
  assessment_id: "assessment-req-1",
  question_set_id: "set-1",
  question_id: "q-2",
  verdict: "partial",
  verdict_label: "部分掌握",
  score_percent: 68,
  confidence_percent: 74,
  answer_excerpt: "Need review",
  review_title: "方向正确，但还需要补齐关键缺口",
  review_summary: "这次回答有可取之处，但还需要讲清：normalizer failure scenario。",
  correct_points: ["结论方向基本正确"],
  gap_points: ["normalizer failure scenario"],
  misconception_points: ["treats storage as provider compatibility layer"],
  evidence: ["The answer names normalizer but does not explain malformed provider output."],
  recommended_follow_up_questions: ["If provider output contains both questions and items, which field wins?"],
  learning_recommendations: ["Review provider output normalization and storage boundaries."],
  knowledge_updates: [
    {
      update_type: "knowledge_entry",
      title: "normalizer failure scenario",
      summary: "Revisit why this stage needs: normalizer failure scenario",
      status: "active",
    },
  ],
  next_action_label: "继续追问一个失败场景",
};

function createClient(overrides: Partial<ApiClient> = {}): ApiClient {
  return {
    baseUrl: "/api",
    getWorkspaceSession: vi.fn().mockResolvedValue({
      workspace_session_id: "local-workspace-session",
      active_project_id: null,
      active_stage_id: null,
      active_panel: "questions",
      active_question_set_id: null,
      active_question_id: null,
      active_profile_space_id: null,
      active_proposal_center_id: null,
      last_opened_at: "",
      filters: {},
    }),
    saveWorkspaceSession: vi.fn().mockResolvedValue({
      workspace_session_id: "local-workspace-session",
      active_project_id: null,
      active_stage_id: null,
      active_panel: "questions",
      active_question_set_id: null,
      active_question_id: null,
      active_profile_space_id: null,
      active_proposal_center_id: null,
      last_opened_at: "",
      filters: {},
    }),
    getHomeView: vi.fn().mockResolvedValue(homeView),
    getProjectView: vi.fn().mockResolvedValue(projectView),
    getStageView: vi.fn().mockResolvedValue(stageView),
    getMistakesView: vi.fn().mockResolvedValue(mistakesView),
    getKnowledgeMapSummaryView: vi.fn().mockResolvedValue(knowledgeMapSummaryView),
    getKnowledgeGraphView: vi.fn().mockResolvedValue(knowledgeGraphView),
    getKnowledgeGraphMainView: vi.fn().mockResolvedValue(knowledgeGraphMainView),
    getKnowledgeIndexView: vi.fn().mockResolvedValue(knowledgeIndexView),
    getProposalsView: vi.fn().mockResolvedValue(proposalsView),
    submitProposalAction: vi.fn().mockResolvedValue({
      request_id: "proposal-1-accept",
      success: true,
      action_type: "accept",
      result_type: "execution_completed",
      message: "accept on proposal-1 => succeeded",
      refresh_targets: ["proposals"],
      proposal_id: "proposal-1",
      proposal_status: "accepted",
      execution_status: "succeeded",
      execution_summary: "accept on proposal-1 => succeeded",
    } satisfies ProposalActionResponseDTO),
    getQuestionSetView: vi.fn().mockResolvedValue(questionSetView),
    getQuestionView: vi.fn().mockResolvedValue(questionView),
    getLatestAssessmentReview: vi.fn().mockResolvedValue(assessmentReviewView),
    generateQuestionSet: vi.fn().mockResolvedValue({
      request_id: "req-qgen-ui",
      questions: [
        {
          question_id: "q-1",
          question_level: "why",
          prompt: "Why expose question generation to the workbench?",
          intent: "Check generated workflow entry.",
          expected_signals: ["HTTP action"],
          source_context: ["stage page"],
        },
      ],
      generation_summary: "Generated 1 question.",
      coverage_notes: [],
      warnings: [],
      confidence: 0.8,
    }),
    submitAnswer: vi.fn().mockResolvedValue({
      request_id: "req-1",
      success: true,
      action_type: "submit_answer",
      result_type: "assessment_created",
      message: "Assessment created with verdict partial.",
      refresh_targets: ["question_detail", "stage_summary", "question_set"],
      assessment_summary: {
        assessment_id: "assessment-req-1",
        project_id: "proj-1",
        stage_id: "stage-1",
        question_set_id: "set-1",
        question_id: "q-2",
        answer_excerpt: "Need review",
        status: "created",
      },
    } satisfies SubmitAnswerResponseDTO),
    ...overrides,
  };
}

test("HomePage renders a task-first workbench entry instead of a generic project list", async () => {
  renderWithClient(<HomePage />, createClient(), "/");

  expect(screen.getByText("Loading home view...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "今日任务" })).toBeInTheDocument();
  expect(screen.getByText("先完成一组题目，再看评析，把薄弱点沉淀进知识库。")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "题目训练" })).toBeInTheDocument();
  expect(screen.getByText("当前阶段：module-interface-boundary")).toBeInTheDocument();
  expect(screen.getByText("impl-phase-coach")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "进入今日训练" })).toHaveAttribute("href", "/projects/proj-1/stages/stage-1");
  expect(screen.getByRole("link", { name: "查看知识沉淀" })).toHaveAttribute("href", "/knowledge");
  expect(screen.getByRole("link", { name: "查看错题本" })).toHaveAttribute("href", "/mistakes");
  expect(screen.queryByText("Open the frozen project shell and inspect its stage list.")).not.toBeInTheDocument();
});

test("ProjectPage renders loaded project summary and stage list", async () => {
  renderWithClient(<ProjectPage />, createClient(), "/projects/proj-1");

  expect(screen.getByText("Loading project view...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Project: impl-phase-coach" })).toBeInTheDocument();
  expect(screen.getByText("A local review workbench that keeps project progress, review rounds, and durable learning traces aligned.")).toBeInTheDocument();
  expect(screen.getAllByText("module-interface-boundary").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("proposal-action-loop")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Open stage" })[0]).toHaveAttribute("href", "/projects/proj-1/stages/stage-1");
  expect(screen.queryByText("This page stays on the project boundary and exposes the next stage boundary.")).not.toBeInTheDocument();
});

test("StagePage renders loaded stage data and not the static placeholder", async () => {
  renderWithClient(<StagePage />, createClient(), "/projects/proj-1/stages/stage-1");

  expect(screen.getByText("Loading stage view...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "今日训练准备" })).toBeInTheDocument();
  expect(screen.getByText("先确认当前阶段，再生成题目进入训练。")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "训练阶段：Validation stage" })).toBeInTheDocument();
  expect(screen.getByText("Confirm boundary handling")).toBeInTheDocument();
  expect(screen.getByText("in_progress")).toBeInTheDocument();
  expect(screen.getByText("unverified")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "已有知识沉淀" })).toBeInTheDocument();
  expect(screen.getByText("知识点").parentElement).toHaveTextContent("1");
  expect(screen.getByText("误区").parentElement).toHaveTextContent("1");
  expect(screen.getByText("synced partial assessment with 1 knowledge entries and 1 mistakes")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "进入题目训练" })).toHaveAttribute(
    "href",
    "/projects/proj-1/stages/stage-1/questions/set-1",
  );
  expect(screen.getByRole("button", { name: "让 Project Agent 生成题目" })).toBeInTheDocument();
  expect(screen.queryByText(/Nested under project/)).not.toBeInTheDocument();
});

test("StagePage triggers Project Agent question generation from the workbench", async () => {
  const client = createClient();

  renderWithClient(<StagePage />, client, "/projects/proj-1/stages/stage-1");

  await screen.findByRole("heading", { name: "训练阶段：Validation stage" });
  fireEvent.click(screen.getByRole("button", { name: "让 Project Agent 生成题目" }));

  await waitFor(() =>
    expect(client.generateQuestionSet).toHaveBeenCalledWith(
      expect.objectContaining({
        project_id: "proj-1",
        stage_id: "stage-1",
        source_page: "stage_detail",
        actor_id: "local-user",
        stage_label: "Validation stage",
        stage_goal: "Confirm boundary handling",
        learning_goal: "练习当前阶段的真实项目题、面试基础题和误区诊断题",
        target_user_level: "intermediate",
        preferred_language: "zh-CN",
        question_mix: ["project implementation", "interview fundamentals", "mistake diagnosis", "failure scenario"],
        preferred_question_style: "concrete study-app question list with direct prompts and reviewable answers",
        question_strategy: "full_depth",
        max_questions: 4,
      }),
    ),
  );
});

test("MistakesPage renders loaded mistake entries and not the shell placeholder", async () => {
  renderWithClient(<MistakesPage />, createClient(), "/mistakes");

  expect(screen.getByText("Loading mistakes view...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Mistakes" })).toBeInTheDocument();
  expect(screen.getByText("Total mistakes: 1")).toBeInTheDocument();
  expect(screen.getByText("Decision awareness")).toBeInTheDocument();
  expect(screen.getByText("Root cause: Decision awareness")).toBeInTheDocument();
  expect(screen.getByText("Avoidance: Review the stage boundary and revisit: Decision awareness")).toBeInTheDocument();
  expect(screen.queryByText("Empty shell for mistake tracking.")).not.toBeInTheDocument();
});

test("KnowledgeMapPage renders focus clusters and summary entry points", async () => {
  renderWithClient(<KnowledgeMapPage />, createClient(), "/knowledge");

  expect(screen.getByText("Loading knowledge map summary...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Knowledge Map" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "State boundary hotspot" })).toBeInTheDocument();
  expect(screen.getByText("State and return value separation")).toBeInTheDocument();
  expect(screen.getByText("Why it matters")).toBeInTheDocument();
  expect(screen.getByText("Current stage exposed a repeated boundary weakness.")).toBeInTheDocument();
  expect(screen.getByText("Current Project Hit")).toBeInTheDocument();
  expect(screen.getByText("Weak Signal Active")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open map cluster" })).toHaveAttribute(
    "href",
    "/knowledge/graph?cluster=cluster-1",
  );
});

test("KnowledgeGraphPage renders graph main view instead of the legacy graph shell", async () => {
  renderWithClient(<KnowledgeGraphPage />, createClient(), "/knowledge/graph");

  expect(screen.getByText("Loading knowledge graph view...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "知识星图" })).toBeInTheDocument();
  expect(screen.getByText("当前聚焦")).toBeInTheDocument();
  expect(screen.getByText("星图预览")).toBeInTheDocument();
  expect(screen.getByText("State boundary hotspot")).toBeInTheDocument();
  expect(screen.getByText("可见知识点")).toBeInTheDocument();
  expect(screen.getByText("可见关系")).toBeInTheDocument();
  expect(screen.getByText("关系筛选")).toBeInTheDocument();
  expect(screen.getAllByText("State and return value separation").length).toBeGreaterThanOrEqual(2);
  expect(screen.getAllByText("Boundary confusion").length).toBeGreaterThanOrEqual(2);
  expect(screen.getAllByText("Mastery: partial")).toHaveLength(2);
});

test("KnowledgeGraphPage presents the graph as a Chinese learning surface", async () => {
  renderWithClient(<KnowledgeGraphPage />, createClient(), "/knowledge/graph");

  expect(await screen.findByRole("heading", { name: "知识星图" })).toBeInTheDocument();
  expect(screen.getByText("从本阶段答题评析沉淀出的知识点、薄弱点和它们之间的关系。")).toBeInTheDocument();
  expect(screen.getByText("当前聚焦")).toBeInTheDocument();
  expect(screen.getByText("星图预览")).toBeInTheDocument();
  expect(screen.getByText("可见知识点")).toBeInTheDocument();
  expect(screen.getByText("可见关系")).toBeInTheDocument();
  expect(screen.getByText("关系类型")).toBeInTheDocument();
  expect(screen.getByText("中心知识点")).toBeInTheDocument();
  expect(screen.getByText("相关知识点")).toBeInTheDocument();
  expect(screen.getByText("关系筛选")).toBeInTheDocument();
});

test("KnowledgeGraphPage scopes graph request from project and stage query params", async () => {
  const client = createClient();

  renderWithClient(<KnowledgeGraphPage />, client, "/knowledge/graph?project=proj-1&stage=stage-1");

  await screen.findByRole("heading", { name: "知识星图" });

  expect(client.getKnowledgeGraphMainView).toHaveBeenCalledWith("proj-1", "stage-1", undefined);
});

test("KnowledgeGraphPage renders loaded graph nodes and not a shell placeholder", async () => {
  renderWithClient(<KnowledgeGraphPage />, createClient(), "/knowledge/graph");

  expect(screen.getByText("Loading knowledge graph view...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "知识星图" })).toBeInTheDocument();
  expect(screen.getByText("当前聚焦")).toBeInTheDocument();
  expect(screen.getByText("State boundary hotspot")).toBeInTheDocument();
  expect(screen.getAllByText("State and return value separation").length).toBeGreaterThanOrEqual(2);
  expect(screen.getAllByText("Boundary confusion").length).toBeGreaterThanOrEqual(2);
  expect(screen.getAllByText("Derived from partial assessment in stage-1.").length).toBeGreaterThanOrEqual(2);
  expect(screen.getAllByText("Evidence: 1")).toHaveLength(2);
  expect(screen.getByText("关系明细")).toBeInTheDocument();
  expect(screen.getAllByText("Causes Mistake (1)").length).toBeGreaterThanOrEqual(2);
  expect(screen.getAllByRole("link", { name: "State and return value separation" })[0]).toHaveAttribute("href", "#node-node-1");
  expect(screen.getAllByRole("link", { name: "Boundary confusion" })[0]).toHaveAttribute("href", "#node-node-2");
});

test("KnowledgeGraphPage filters visible relations by type", async () => {
  const client = createClient({
    getKnowledgeGraphMainView: vi.fn().mockResolvedValue(knowledgeGraphMainViewWithSupports),
  });

  renderWithClient(<KnowledgeGraphPage />, client, "/knowledge/graph");

  await screen.findByRole("heading", { name: "知识星图" });
  fireEvent.click(screen.getByRole("button", { name: "Supports" }));

  expect(screen.getByRole("button", { name: "Supports" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getAllByText("Supports (1)").length).toBeGreaterThanOrEqual(2);
  expect(screen.queryByText("Causes Mistake (1)")).not.toBeInTheDocument();
});

test("KnowledgeGraphPage highlights related nodes when a relation is focused", async () => {
  renderWithClient(<KnowledgeGraphPage />, createClient(), "/knowledge/graph");

  await screen.findByRole("heading", { name: "知识星图" });
  fireEvent.click(screen.getByRole("button", { name: "relation-1" }));

  expect(screen.getByRole("button", { name: "relation-1" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "node-node-1" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "node-node-2" })).toHaveAttribute("aria-pressed", "true");
});

test("KnowledgeGraphPage highlights related relations when a node is focused", async () => {
  renderWithClient(<KnowledgeGraphPage />, createClient(), "/knowledge/graph");

  await screen.findByRole("heading", { name: "知识星图" });
  fireEvent.click(screen.getByRole("button", { name: "node-node-1" }));

  expect(screen.getByRole("button", { name: "node-node-1" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "relation-1" })).toHaveAttribute("data-highlighted", "true");
});

test("KnowledgeIndexPage renders loaded index entries and not a shell placeholder", async () => {
  renderWithClient(<KnowledgeIndexPage />, createClient(), "/knowledge/index");

  expect(screen.getByText("Loading knowledge index view...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Knowledge Index" })).toBeInTheDocument();
  expect(screen.getByText("Total entries: 1")).toBeInTheDocument();
  expect(screen.getByText("Decision awareness")).toBeInTheDocument();
  expect(screen.getByText("Revisit why this stage needs: Decision awareness")).toBeInTheDocument();
  expect(screen.getByText("Linked mistakes: proj-1:stage-1:a-1:mistake-1")).toBeInTheDocument();
});

test("ProposalsPage renders loaded proposal entries and not the shell placeholder", async () => {
  renderWithClient(<ProposalsPage />, createClient(), "/proposals");

  expect(screen.getByText("Loading proposals view...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Proposals" })).toBeInTheDocument();
  expect(screen.getByText("Total proposals: 1")).toBeInTheDocument();
  expect(screen.getByText("Pending review: 1")).toBeInTheDocument();
  expect(screen.getByText("compress_mistake_entries")).toBeInTheDocument();
  expect(screen.getByText("Reason: Compress 2 mistake_entries")).toBeInTheDocument();
  expect(screen.getByText("Preview: Would compress 2 targets from mistake_entries.")).toBeInTheDocument();
  expect(screen.queryByText("Empty shell for proposal review.")).not.toBeInTheDocument();
});

test("ProposalsPage applies accept and refreshes proposal execution summary", async () => {
  const client = createClient({
    getProposalsView: vi.fn().mockResolvedValueOnce(proposalsView).mockResolvedValueOnce(proposalsViewAfterAccept),
  });

  renderWithClient(<ProposalsPage />, client, "/proposals");

  await screen.findByRole("heading", { name: "Proposals" });
  fireEvent.click(screen.getByRole("button", { name: "Accept" }));

  expect(await screen.findByText("accept on proposal-1 => succeeded")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("mistake_entries / accepted / 2 targets")).toBeInTheDocument());
  expect(client.submitProposalAction).toHaveBeenCalledTimes(1);
});

test("QuestionSetPage renders loaded question set data and not the static placeholder", async () => {
  renderWithClient(
    <QuestionSetPage />,
    createClient(),
    "/projects/proj-1/stages/stage-1/questions/set-1",
  );

  expect(screen.getByText("Loading question set...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "题目训练" })).toBeInTheDocument();
  expect(screen.getByText("今天先完成一组高质量题目，答完后会给出评析并沉淀到知识库。")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "当前推荐题" })).toBeInTheDocument();
  expect(screen.getByText("已完成 1 / 3")).toBeInTheDocument();
  expect(screen.getByText("题目 q-1")).toBeInTheDocument();
  expect(screen.getByText("What is the core boundary here?")).toBeInTheDocument();
  expect(screen.getByText("已完成")).toBeInTheDocument();
  expect(screen.getByText("题目 q-2")).toBeInTheDocument();
  expect(screen.getByText("Why is this boundary necessary?")).toBeInTheDocument();
  expect(screen.getByText("当前题")).toBeInTheDocument();
  expect(screen.getByText("题目 q-3")).toBeInTheDocument();
  expect(screen.getByText("What failure scenario should be checked next?")).toBeInTheDocument();
  expect(screen.getByText("待完成")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "立即答题" })).toHaveAttribute(
    "href",
    "/projects/proj-1/stages/stage-1/questions/set-1/q-2",
  );
  expect(screen.queryByText(/Question set: unknown-set/)).not.toBeInTheDocument();
});

test("QuestionSetPage regenerates questions from the training entry", async () => {
  const refreshedQuestionSetView: QuestionSetViewDTO = {
    ...questionSetView,
    question_count: 1,
    current_question_id: "q-new",
    questions: [
      {
        question_id: "q-new",
        question_level: "scenario",
        prompt: "How would you test malformed Project Agent output?",
        status: "ready",
      },
    ],
  };
  const client = createClient({
    getQuestionSetView: vi.fn().mockResolvedValueOnce(questionSetView).mockResolvedValueOnce(refreshedQuestionSetView),
  });

  renderWithClient(
    <QuestionSetPage />,
    client,
    "/projects/proj-1/stages/stage-1/questions/set-1",
  );

  await screen.findByRole("heading", { name: "题目训练" });
  fireEvent.click(screen.getByRole("button", { name: "让 Project Agent 出一组新题" }));

  await waitFor(() =>
    expect(client.generateQuestionSet).toHaveBeenCalledWith(
      expect.objectContaining({
        project_id: "proj-1",
        stage_id: "stage-1",
        source_page: "question_set",
        stage_label: "Validation stage",
        stage_goal: "Confirm boundary handling",
        learning_goal: "练习当前阶段的真实项目题、面试基础题和误区诊断题",
        target_user_level: "intermediate",
        preferred_language: "zh-CN",
        question_mix: ["project implementation", "interview fundamentals", "mistake diagnosis", "failure scenario"],
        preferred_question_style: "concrete study-app question list with direct prompts and reviewable answers",
        question_strategy: "full_depth",
        max_questions: 4,
      }),
    ),
  );
  expect(await screen.findByText("已生成 1 道题，并刷新题目列表。")).toBeInTheDocument();
  expect(screen.getByText("How would you test malformed Project Agent output?")).toBeInTheDocument();
});

test("QuestionPage renders loaded question data and not the static placeholder", async () => {
  renderWithClient(
    <QuestionPage />,
    createClient(),
    "/projects/proj-1/stages/stage-1/questions/set-1/q-2",
  );

  expect(screen.getByText("Loading question...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "闯关答题" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Why is this boundary necessary?" })).toBeInTheDocument();
  expect(screen.getByText("Check whether the user can explain the separation between read and write flows.")).toBeInTheDocument();
  expect(screen.getByText("Answer in your own words")).toBeInTheDocument();
  expect(screen.getByText("项目上下文")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "提交答案" })).toBeInTheDocument();
  expect(screen.getByText("continue_answering")).toBeInTheDocument();
  expect(screen.queryByText(/Placeholder for question prompt/)).not.toBeInTheDocument();
});

test("QuestionPage renders a readable error state when the client rejects", async () => {
  const client = createClient({
    getQuestionView: vi.fn().mockRejectedValue(new Error("question view unavailable")),
  });

  renderWithClient(
    <QuestionPage />,
    client,
    "/projects/proj-1/stages/stage-1/questions/set-1/q-2",
  );

  expect(await screen.findByText("Failed to load question view.")).toBeInTheDocument();
  expect(screen.getByText("question view unavailable")).toBeInTheDocument();
});

test("QuestionPage submits an answer and refreshes the stage summary", async () => {
  const refreshedStageView: StageViewDTO = {
    ...stageView,
    mastery_status: "partially_verified",
  };
  const client = createClient({
    getStageView: vi.fn().mockResolvedValueOnce(stageView).mockResolvedValueOnce(refreshedStageView),
  });

  renderWithClient(
    <QuestionPage />,
    client,
    "/projects/proj-1/stages/stage-1/questions/set-1/q-2",
  );

  await screen.findByRole("heading", { name: "Why is this boundary necessary?" });
  fireEvent.change(screen.getByLabelText("Answer"), { target: { value: "Need review" } });
  fireEvent.click(screen.getByRole("button", { name: "提交答案" }));

  expect(await screen.findByText("Assessment created with verdict partial.")).toBeInTheDocument();
  expect(screen.getByText("你的回答摘要：Need review")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "评析解析" })).toBeInTheDocument();
  expect(screen.getByText("方向正确，但还需要补齐关键缺口")).toBeInTheDocument();
  expect(screen.getByText("部分掌握 · 68%")).toBeInTheDocument();
  expect(screen.getByText("normalizer failure scenario")).toBeInTheDocument();
  expect(screen.getByText("知识沉淀")).toBeInTheDocument();
  expect(screen.getByText("继续追问一个失败场景")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "返回题集" })).toHaveAttribute(
    "href",
    "/projects/proj-1/stages/stage-1/questions/set-1",
  );
  expect(screen.getByRole("link", { name: "查看知识星图" })).toHaveAttribute(
    "href",
    "/knowledge/graph?project=proj-1&stage=stage-1",
  );
  expect(screen.getByRole("link", { name: "进入下一题" })).toHaveAttribute(
    "href",
    "/projects/proj-1/stages/stage-1/questions/set-1/q-3",
  );
  await waitFor(() => expect(screen.getByText("partially_verified")).toBeInTheDocument());
  expect(client.submitAnswer).toHaveBeenCalledTimes(1);
  expect(client.getLatestAssessmentReview).toHaveBeenCalledWith("proj-1", "stage-1");
  expect(client.getQuestionSetView).toHaveBeenCalledWith("proj-1", "stage-1", "set-1");
});

test("QuestionPage does not refresh question set when submit response omits that target", async () => {
  const client = createClient({
    submitAnswer: vi.fn().mockResolvedValue({
      request_id: "req-no-question-set-refresh",
      success: true,
      action_type: "submit_answer",
      result_type: "assessment_created",
      message: "Assessment created with verdict partial.",
      refresh_targets: ["question_detail", "stage_summary"],
      assessment_summary: {
        assessment_id: "assessment-req-no-question-set-refresh",
        project_id: "proj-1",
        stage_id: "stage-1",
        question_set_id: "set-1",
        question_id: "q-2",
        answer_excerpt: "Need review",
        status: "created",
      },
    } satisfies SubmitAnswerResponseDTO),
    getQuestionSetView: vi.fn().mockResolvedValue(questionSetView),
  });

  renderWithClient(
    <QuestionPage />,
    client,
    "/projects/proj-1/stages/stage-1/questions/set-1/q-2",
  );

  await screen.findByRole("heading", { name: "Why is this boundary necessary?" });
  fireEvent.change(screen.getByLabelText("Answer"), { target: { value: "Need review" } });
  fireEvent.click(screen.getByRole("button", { name: "提交答案" }));

  expect(await screen.findByText("Assessment created with verdict partial.")).toBeInTheDocument();
  await waitFor(() => expect(client.getLatestAssessmentReview).toHaveBeenCalledWith("proj-1", "stage-1"));
  expect(client.getQuestionSetView).not.toHaveBeenCalled();
  expect(screen.queryByRole("link", { name: "进入下一题" })).not.toBeInTheDocument();
});

test("QuestionPage resets answer draft and submit state when route params change", async () => {
  const client = createClient({
    getQuestionView: vi
      .fn()
      .mockResolvedValueOnce(questionView)
      .mockResolvedValueOnce({
        ...questionView,
        question_id: "q-3",
        question_level: "abstract",
        prompt: "How does this boundary generalize?",
        intent: "Check whether the user can transfer the boundary.",
      }),
  });

  render(
    <ApiClientProvider client={client}>
      <MemoryRouter initialEntries={["/projects/proj-1/stages/stage-1/questions/set-1/q-2"]}>
        <nav>
          <Link to="/projects/proj-1/stages/stage-1/questions/set-1/q-3">Go to q-3</Link>
        </nav>
        <Routes>
          <Route
            path="/projects/:projectId/stages/:stageId/questions/:questionSetId/:questionId"
            element={<QuestionPage />}
          />
        </Routes>
      </MemoryRouter>
    </ApiClientProvider>,
  );

  await screen.findByRole("heading", { name: "Why is this boundary necessary?" });
  fireEvent.change(screen.getByLabelText("Answer"), { target: { value: "Need review" } });
  fireEvent.click(screen.getByRole("button", { name: "提交答案" }));
  await screen.findByText("Assessment created with verdict partial.");

  fireEvent.click(screen.getByRole("link", { name: "Go to q-3" }));

  expect(await screen.findByRole("heading", { name: "How does this boundary generalize?" })).toBeInTheDocument();
  await waitFor(() => expect(screen.getByLabelText("Answer")).toHaveValue(""));
  expect(screen.queryByText("Assessment created with verdict partial.")).not.toBeInTheDocument();
  expect(screen.queryByText("你的回答摘要：Need review")).not.toBeInTheDocument();
});
