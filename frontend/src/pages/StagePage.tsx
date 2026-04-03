import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useApiClient, type StageViewDTO } from "../lib/api";

type StageLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: StageViewDTO; error: null };

export function StagePage() {
  const { projectId = "unknown-project", stageId = "unknown-stage" } = useParams();
  const client = useApiClient();
  const [state, setState] = useState<StageLoadState>({ status: "loading", data: null, error: null });
  const activeQuestionSetHref =
    state.status === "ready" && state.data.active_question_set_id
      ? `/projects/${projectId}/stages/${stageId}/questions/${state.data.active_question_set_id}`
      : null;

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

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
