import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useApiClient, type GenerateQuestionSetResponseDTO, type StageViewDTO } from "../lib/api";

type StageLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: StageViewDTO; error: null };

export function StagePage() {
  const { projectId = "unknown-project", stageId = "unknown-stage" } = useParams();
  const client = useApiClient();
  const navigate = useNavigate();
  const [state, setState] = useState<StageLoadState>({ status: "loading", data: null, error: null });
  const [generationState, setGenerationState] = useState<"idle" | "generating">("idle");
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [generationResult, setGenerationResult] = useState<GenerateQuestionSetResponseDTO | null>(null);
  const activeQuestionSetHref =
    state.status === "ready" && state.data.active_question_set_id
      ? `/projects/${projectId}/stages/${stageId}/questions/${state.data.active_question_set_id}`
      : null;

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });
    setGenerationError(null);
    setGenerationResult(null);

    client
      .getStageView(projectId, stageId)
      .then((data) => {
        if (active) {
          setState({ status: "ready", data, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            status: "error",
            data: null,
            error: error instanceof Error ? error.message : "Unable to load stage view.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [client, projectId, stageId]);

  async function handleGenerateQuestionSet() {
    if (state.status !== "ready" || !state.data.active_question_set_id) {
      return;
    }

    setGenerationState("generating");
    setGenerationError(null);
    setGenerationResult(null);

    try {
      const response = await client.generateQuestionSet({
        request_id: makeRequestId(),
        project_id: projectId,
        stage_id: stageId,
        source_page: "stage_detail",
        actor_id: "local-user",
        created_at: new Date().toISOString(),
        stage_label: state.data.stage_label,
        stage_goal: state.data.stage_goal,
        stage_summary: `Generate a live question set for ${state.data.stage_label}.`,
        stage_artifacts: ["question set read surface", "question detail read surface"],
        stage_exit_criteria: ["generated questions can be opened and answered"],
        current_decisions: ["Project Agent question generation is available through an HTTP action."],
        key_logic_points: ["generated checkpoints must be readable by question set and question detail views"],
        known_weak_points: ["provider output may drift from the exact prompt field contract"],
        boundary_focus: ["Project Agent output", "generated question checkpoint", "submit answer context"],
        question_strategy: "full_depth",
        max_questions: 4,
        source_refs: [`stage:${stageId}`],
      });
      setGenerationResult(response);
      navigate(`/projects/${projectId}/stages/${stageId}/questions/${state.data.active_question_set_id}`);
    } catch (error: unknown) {
      setGenerationError(error instanceof Error ? error.message : "Unable to generate question set.");
    } finally {
      setGenerationState("idle");
    }
  }

  return (
    <section style={{ display: "grid", gap: "1rem" }}>
      <div>
        <h1 style={{ margin: 0 }}>Stage</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          {projectId} / {stageId}
        </p>
      </div>

      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading stage view...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load stage view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Stage: {state.data.stage_label}</h2>
            <dl style={definitionListStyle}>
              <div>
                <dt style={termStyle}>Goal</dt>
                <dd style={definitionStyle}>{state.data.stage_goal}</dd>
              </div>
              <div>
                <dt style={termStyle}>Status</dt>
                <dd style={definitionStyle}>{state.data.status}</dd>
              </div>
              <div>
                <dt style={termStyle}>Mastery</dt>
                <dd style={definitionStyle}>{state.data.mastery_status}</dd>
              </div>
              <div>
                <dt style={termStyle}>Active question set</dt>
                <dd style={definitionStyle}>{state.data.active_question_set_id ?? "none"}</dd>
              </div>
            </dl>
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Knowledge summary</h2>
            <dl style={definitionListStyle}>
              <div>
                <dt style={termStyle}>Knowledge entries</dt>
                <dd style={definitionStyle}>{state.data.knowledge_summary?.knowledge_entry_count ?? 0}</dd>
              </div>
              <div>
                <dt style={termStyle}>Mistakes</dt>
                <dd style={definitionStyle}>{state.data.knowledge_summary?.mistake_count ?? 0}</dd>
              </div>
              <div>
                <dt style={termStyle}>Latest extraction</dt>
                <dd style={definitionStyle}>{state.data.knowledge_summary?.latest_summary ?? "No knowledge extracted yet."}</dd>
              </div>
            </dl>
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Project boundary</h2>
            <p style={{ margin: 0, color: "#475569" }}>Project {state.data.project_id} stays within the stage read view.</p>
            <p style={{ margin: "0.75rem 0 0" }}>
              Open a question set for this stage through the read chain, then drill into question detail.
            </p>
            <div style={{ margin: "0.75rem 0 0" }}>
              <button
                type="button"
                disabled={generationState === "generating" || !state.data.active_question_set_id}
                onClick={handleGenerateQuestionSet}
                style={buttonStyle}
              >
                {generationState === "generating" ? "Generating..." : "Generate Project Agent question set"}
              </button>
            </div>
            {generationError ? (
              <p style={{ margin: "0.75rem 0 0", color: "#b91c1c" }} role="alert">
                {generationError}
              </p>
            ) : null}
            {generationResult ? (
              <p style={{ margin: "0.75rem 0 0", color: "#475569" }}>
                Generated {generationResult.questions.length} questions.
              </p>
            ) : null}
            {activeQuestionSetHref ? (
              <p style={{ margin: "0.5rem 0 0" }}>
                <Link to={activeQuestionSetHref}>Open question set {state.data.active_question_set_id}</Link>
              </p>
            ) : (
              <p style={{ margin: "0.5rem 0 0", color: "#64748b" }}>No active question set is available yet.</p>
            )}
          </article>
        </div>
      )}
    </section>
  );
}

const panelStyle = {
  border: "1px solid rgba(148, 163, 184, 0.35)",
  borderRadius: "1rem",
  background: "rgba(255, 255, 255, 0.92)",
  padding: "1rem",
} as const;

const sectionHeadingStyle = { margin: "0 0 0.75rem" } as const;
const definitionListStyle = { display: "grid", gap: "0.75rem", margin: 0 } as const;
const termStyle = { fontSize: "0.875rem", color: "#64748b", fontWeight: 700 } as const;
const definitionStyle = { margin: "0.25rem 0 0" } as const;
const buttonStyle = {
  border: 0,
  borderRadius: "999px",
  padding: "0.75rem 1.1rem",
  background: "#0f172a",
  color: "#fff",
  fontWeight: 700,
  cursor: "pointer",
} as const;

function makeRequestId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}`;
}
