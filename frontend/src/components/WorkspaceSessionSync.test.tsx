import "@testing-library/jest-dom/vitest";

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { vi } from "vitest";

import { ApiClientProvider, type ApiClient, type WorkspaceSessionDTO } from "../lib/api";
import {
  WorkspaceSessionSync,
  buildPathFromWorkspaceSession,
  buildWorkspaceSessionForPath,
} from "./WorkspaceSessionSync";

function blankSession(): WorkspaceSessionDTO {
  return {
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
  };
}

function createClient(overrides: Partial<ApiClient> = {}): ApiClient {
  return {
    baseUrl: "/api",
    getWorkspaceSession: vi.fn().mockResolvedValue(blankSession()),
    saveWorkspaceSession: vi.fn().mockResolvedValue(blankSession()),
    getHomeView: vi.fn().mockResolvedValue({ total_count: 0, pending_proposal_count: 0, active_project_id: null, projects: [] }),
    getProjectView: vi.fn().mockResolvedValue({
      project_id: "proj-1",
      project_label: "impl-phase-coach",
      project_summary: "summary",
      active_stage_id: "stage-1",
      active_stage_label: "stage-1",
      pending_proposal_count: 0,
      mistake_count: 0,
      knowledge_entry_count: 0,
      stages: [],
    }),
    getStageView: vi.fn().mockResolvedValue({
      project_id: "proj-1",
      stage_id: "stage-1",
      stage_label: "stage-1",
      stage_goal: "goal",
      status: "in_progress",
      mastery_status: "unverified",
      active_question_set_id: "set-1",
      knowledge_summary: null,
    }),
    getMistakesView: vi.fn().mockResolvedValue({ project_filter: null, stage_filter: null, items: [], total_count: 0 }),
    getKnowledgeIndexView: vi.fn().mockResolvedValue({ project_filter: null, stage_filter: null, items: [], total_count: 0 }),
    getKnowledgeGraphView: vi.fn().mockResolvedValue({ project_filter: null, stage_filter: null, nodes: [], total_count: 0 }),
    getProposalsView: vi.fn().mockResolvedValue({ items: [], total_count: 0, pending_count: 0 }),
    submitProposalAction: vi.fn().mockResolvedValue({
      request_id: "proposal-action",
      success: true,
      action_type: "accept",
      result_type: "execution_completed",
      message: "ok",
      refresh_targets: ["proposals"],
      proposal_id: "proposal-1",
      proposal_status: "accepted",
      execution_status: "succeeded",
      execution_summary: "ok",
    }),
    getQuestionSetView: vi.fn().mockResolvedValue({
      project_id: "proj-1",
      stage_id: "stage-1",
      question_set_id: "set-1",
      question_set_title: "set-1",
      status: "active",
      question_count: 1,
      current_question_id: "set-1-q-1",
      questions: [],
    }),
    getQuestionView: vi.fn().mockResolvedValue({
      project_id: "proj-1",
      stage_id: "stage-1",
      question_set_id: "set-1",
      question_id: "set-1-q-1",
      question_level: "core",
      prompt: "prompt",
      intent: "intent",
      answer_placeholder: "placeholder",
      allowed_actions: [],
      status: "ready",
    }),
    submitAnswer: vi.fn().mockResolvedValue({
      request_id: "req-1",
      success: true,
      action_type: "submit_answer",
      result_type: "assessment_created",
      message: "ok",
      refresh_targets: ["question_detail"],
      assessment_summary: null,
    }),
    ...overrides,
  };
}

function LocationEcho() {
  const location = useLocation();
  return <div data-testid="pathname">{location.pathname}</div>;
}

test("builds a saved question route from workspace session", () => {
  expect(
    buildPathFromWorkspaceSession({
      ...blankSession(),
      active_project_id: "proj-1",
      active_stage_id: "stage-1",
      active_question_set_id: "set-1",
      active_question_id: "set-1-q-2",
    }),
  ).toBe("/projects/proj-1/stages/stage-1/questions/set-1/set-1-q-2");
});

test("derives workspace session ids from a question route", () => {
  expect(buildWorkspaceSessionForPath("/projects/proj-1/stages/stage-1/questions/set-1/set-1-q-2")).toMatchObject({
    active_project_id: "proj-1",
    active_stage_id: "stage-1",
    active_question_set_id: "set-1",
    active_question_id: "set-1-q-2",
    active_panel: "questions",
  });
});

test("restores the saved question route when opening the workbench root", async () => {
  const client = createClient({
    getWorkspaceSession: vi.fn().mockResolvedValue({
      ...blankSession(),
      active_project_id: "proj-1",
      active_stage_id: "stage-1",
      active_question_set_id: "set-1",
      active_question_id: "set-1-q-2",
    }),
    saveWorkspaceSession: vi.fn().mockResolvedValue(blankSession()),
  });

  render(
    <ApiClientProvider client={client}>
      <MemoryRouter initialEntries={["/"]}>
        <WorkspaceSessionSync />
        <Routes>
          <Route path="*" element={<LocationEcho />} />
        </Routes>
      </MemoryRouter>
    </ApiClientProvider>,
  );

  await waitFor(() =>
    expect(screen.getByTestId("pathname")).toHaveTextContent(
      "/projects/proj-1/stages/stage-1/questions/set-1/set-1-q-2",
    ),
  );
});

test("saves the current route as workspace session once restore is ready", async () => {
  const saveWorkspaceSession = vi.fn().mockResolvedValue(blankSession());
  const client = createClient({ saveWorkspaceSession });

  render(
    <ApiClientProvider client={client}>
      <MemoryRouter initialEntries={["/projects/proj-1/stages/stage-1/questions/set-1"]}>
        <WorkspaceSessionSync />
        <Routes>
          <Route path="*" element={<LocationEcho />} />
        </Routes>
      </MemoryRouter>
    </ApiClientProvider>,
  );

  await waitFor(() =>
    expect(saveWorkspaceSession).toHaveBeenCalledWith(
      expect.objectContaining({
        active_project_id: "proj-1",
        active_stage_id: "stage-1",
        active_question_set_id: "set-1",
        active_question_id: null,
        active_panel: "questions",
      }),
    ),
  );
});
