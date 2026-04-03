import { describe, expect, test, vi } from "vitest";

import { createApiClient } from "./api";

describe("createApiClient", () => {
  test("reads home view from the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ total_count: 1, projects: [] }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.getHomeView();

    expect(fetchImpl).toHaveBeenCalledWith("/api/home", expect.any(Object));
  });

  test("reads project view from the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ project_id: "proj-1", stages: [] }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.getProjectView("proj-1");

    expect(fetchImpl).toHaveBeenCalledWith("/api/projects/proj-1", expect.any(Object));
  });

  test("reads stage view from the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ project_id: "proj-1", stage_id: "stage-1" }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.getStageView("proj-1", "stage-1");

    expect(fetchImpl).toHaveBeenCalledWith("/api/projects/proj-1/stages/stage-1", expect.any(Object));
  });

  test("reads mistakes view from the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ total_count: 0, items: [] }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.getMistakesView("proj-1", "stage-1");

    expect(fetchImpl).toHaveBeenCalledWith("/api/mistakes?project_id=proj-1&stage_id=stage-1", expect.any(Object));
  });

  test("reads knowledge index view from the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ total_count: 0, items: [] }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.getKnowledgeIndexView("proj-1", "stage-1");

    expect(fetchImpl).toHaveBeenCalledWith("/api/knowledge/index?project_id=proj-1&stage_id=stage-1", expect.any(Object));
  });

  test("reads knowledge graph view from the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ total_count: 0, nodes: [] }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.getKnowledgeGraphView("proj-1", "stage-1");

    expect(fetchImpl).toHaveBeenCalledWith("/api/knowledge/graph?project_id=proj-1&stage_id=stage-1", expect.any(Object));
  });

  test("reads proposals view from the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ total_count: 0, pending_count: 0, items: [] }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.getProposalsView();

    expect(fetchImpl).toHaveBeenCalledWith("/api/proposals", expect.any(Object));
  });

  test("submits proposal actions to the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.submitProposalAction({
      request_id: "proposal-1-accept",
      source_page: "proposals",
      actor_id: "local-user",
      created_at: "2026-04-03T00:00:00Z",
      proposal_id: "proposal-1",
      action_type: "accept",
      selected_target_ids: [],
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/actions/proposal-action",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Accept: "application/json",
          "Content-Type": "application/json",
        }),
      }),
    );
  });

  test("reads question set and question views from the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "active" }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.getQuestionSetView("proj-1", "stage-1", "set-1");
    await client.getQuestionView("proj-1", "stage-1", "set-1", "q-1");

    expect(fetchImpl).toHaveBeenNthCalledWith(
      1,
      "/api/projects/proj-1/stages/stage-1/questions/set-1",
      expect.any(Object),
    );
    expect(fetchImpl).toHaveBeenNthCalledWith(
      2,
      "/api/projects/proj-1/stages/stage-1/questions/set-1/q-1",
      expect.any(Object),
    );
  });

  test("submits answers to the backend HTTP path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });
    const client = createApiClient("/api", fetchImpl as typeof fetch);

    await client.submitAnswer({
      request_id: "req-1",
      project_id: "proj-1",
      stage_id: "stage-1",
      source_page: "question_detail",
      actor_id: "local-user",
      created_at: "2026-04-03T00:00:00Z",
      question_set_id: "set-1",
      question_id: "q-1",
      answer_text: "Need review",
      draft_id: null,
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/actions/submit-answer",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Accept: "application/json",
          "Content-Type": "application/json",
        }),
      }),
    );
  });
});
test("reads workspace session from the backend HTTP path", async () => {
  const fetchImpl = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ workspace_session_id: "local-workspace-session" }),
  });
  const client = createApiClient("/api", fetchImpl as typeof fetch);

  await client.getWorkspaceSession();

  expect(fetchImpl).toHaveBeenCalledWith("/api/workspace-session", expect.any(Object));
});

test("saves workspace session to the backend HTTP path", async () => {
  const fetchImpl = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ workspace_session_id: "local-workspace-session" }),
  });
  const client = createApiClient("/api", fetchImpl as typeof fetch);

  await client.saveWorkspaceSession({
    workspace_session_id: "local-workspace-session",
    active_project_id: "proj-1",
    active_stage_id: "stage-1",
    active_panel: "questions",
    active_question_set_id: "set-1",
    active_question_id: "set-1-q-2",
    active_profile_space_id: null,
    active_proposal_center_id: null,
    last_opened_at: "2026-04-03T00:00:00Z",
    filters: {},
  });

  expect(fetchImpl).toHaveBeenCalledWith(
    "/api/workspace-session",
    expect.objectContaining({
      method: "PUT",
      headers: expect.objectContaining({
        Accept: "application/json",
        "Content-Type": "application/json",
      }),
    }),
  );
});
