import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useApiClient, type ProjectViewDTO } from "../lib/api";

type ProjectLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: ProjectViewDTO; error: null };

export function ProjectPage() {
  const { projectId = "unknown-project" } = useParams();
  const client = useApiClient();
  const [state, setState] = useState<ProjectLoadState>({ status: "loading", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

    client
      .getProjectView(projectId)
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
            error: error instanceof Error ? error.message : "Unable to load project view.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [client, projectId]);

  return (
    <section style={{ display: "grid", gap: "1rem" }}>
      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading project view...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load project view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <>
          <div>
            <h1 style={{ margin: 0 }}>Project: {state.data.project_label}</h1>
            <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>{state.data.project_summary}</p>
          </div>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Project summary</h2>
            <dl style={definitionListStyle}>
              <div>
                <dt style={termStyle}>Active stage</dt>
                <dd style={definitionStyle}>{state.data.active_stage_label}</dd>
              </div>
              <div>
                <dt style={termStyle}>Knowledge entries</dt>
                <dd style={definitionStyle}>{state.data.knowledge_entry_count}</dd>
              </div>
              <div>
                <dt style={termStyle}>Mistakes</dt>
                <dd style={definitionStyle}>{state.data.mistake_count}</dd>
              </div>
              <div>
                <dt style={termStyle}>Pending proposals</dt>
                <dd style={definitionStyle}>{state.data.pending_proposal_count}</dd>
              </div>
            </dl>
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Stages</h2>
            <ul style={listStyle}>
              {state.data.stages.map((stage) => (
                <li key={stage.stage_id} style={{ marginBottom: "0.75rem" }}>
                  <div style={{ fontWeight: 700 }}>{stage.stage_label}</div>
                  <div style={{ color: "#475569", fontSize: "0.95rem" }}>
                    {stage.status} / {stage.mastery_status}
                  </div>
                  <p style={{ margin: "0.4rem 0 0" }}>
                    <Link to={`/projects/${state.data.project_id}/stages/${stage.stage_id}`}>Open stage</Link>
                  </p>
                </li>
              ))}
            </ul>
          </article>
        </>
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
const listStyle = { margin: 0, paddingLeft: "1.25rem" } as const;