import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useApiClient, type HomeViewDTO } from "../lib/api";

type HomeLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: HomeViewDTO; error: null };

export function HomePage() {
  const client = useApiClient();
  const [state, setState] = useState<HomeLoadState>({ status: "loading", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

    client
      .getHomeView()
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
            error: error instanceof Error ? error.message : "Unable to load home view.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [client]);

  return (
    <section style={{ display: "grid", gap: "1rem" }}>
      <div>
        <h1 style={{ margin: 0, fontSize: "2rem" }}>Projects</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          Start from a real project summary, then drill into its active stage and current question set.
        </p>
      </div>

      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading home view...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load home view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <>
          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Workspace summary</h2>
            <dl style={definitionListStyle}>
              <div>
                <dt style={termStyle}>Projects</dt>
                <dd style={definitionStyle}>{state.data.total_count}</dd>
              </div>
              <div>
                <dt style={termStyle}>Pending proposals</dt>
                <dd style={definitionStyle}>{state.data.pending_proposal_count}</dd>
              </div>
              <div>
                <dt style={termStyle}>Active project</dt>
                <dd style={definitionStyle}>{state.data.active_project_id ?? "none"}</dd>
              </div>
            </dl>
          </article>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "1rem",
            }}
          >
            {state.data.projects.map((project) => (
              <article key={project.project_id} style={cardStyle}>
                <h2 style={cardHeadingStyle}>{project.project_label}</h2>
                <p style={cardTextStyle}>{project.project_summary}</p>
                <dl style={definitionListStyle}>
                  <div>
                    <dt style={termStyle}>Active stage</dt>
                    <dd style={definitionStyle}>{project.active_stage_label}</dd>
                  </div>
                  <div>
                    <dt style={termStyle}>Knowledge entries</dt>
                    <dd style={definitionStyle}>{project.knowledge_entry_count}</dd>
                  </div>
                  <div>
                    <dt style={termStyle}>Mistakes</dt>
                    <dd style={definitionStyle}>{project.mistake_count}</dd>
                  </div>
                  <div>
                    <dt style={termStyle}>Pending proposals</dt>
                    <dd style={definitionStyle}>{project.pending_proposal_count}</dd>
                  </div>
                </dl>
                <p style={{ margin: "0.75rem 0 0" }}>
                  <Link to={`/projects/${project.project_id}`}>Open project</Link>
                </p>
              </article>
            ))}
          </div>
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
  boxShadow: "0 12px 32px rgba(15, 23, 42, 0.06)",
} as const;

const cardStyle = panelStyle;
const cardHeadingStyle = { margin: "0 0 0.5rem" } as const;
const cardTextStyle = { margin: "0 0 0.75rem", color: "#475569" } as const;
const sectionHeadingStyle = { margin: "0 0 0.75rem" } as const;
const definitionListStyle = { display: "grid", gap: "0.75rem", margin: 0 } as const;
const termStyle = { fontSize: "0.875rem", color: "#64748b", fontWeight: 700 } as const;
const definitionStyle = { margin: "0.25rem 0 0" } as const;