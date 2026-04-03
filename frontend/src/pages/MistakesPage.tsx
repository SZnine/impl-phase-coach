import { useEffect, useState } from "react";

import { useApiClient, type MistakesViewDTO } from "../lib/api";

type MistakesLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: MistakesViewDTO; error: null };

export function MistakesPage() {
  const client = useApiClient();
  const [state, setState] = useState<MistakesLoadState>({ status: "loading", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

    client
      .getMistakesView()
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
            error: error instanceof Error ? error.message : "Unable to load mistakes view.",
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
        <h1 style={{ margin: 0 }}>Mistakes</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          Long-term mistake entries extracted from completed review assessments.
        </p>
      </div>

      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading mistakes view...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load mistakes view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Mistake summary</h2>
            <p style={{ margin: 0 }}>Total mistakes: {state.data.total_count}</p>
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Entries</h2>
            {state.data.items.length === 0 ? (
              <p style={{ margin: 0, color: "#64748b" }}>No durable mistakes recorded yet.</p>
            ) : (
              <ul style={listStyle}>
                {state.data.items.map((item) => (
                  <li key={item.mistake_id} style={itemStyle}>
                    <h3 style={{ margin: 0 }}>{item.label}</h3>
                    <p style={metaStyle}>
                      {item.project_id} / {item.stage_id} / {item.mistake_type}
                    </p>
                    <p style={{ margin: "0.5rem 0 0" }}>Root cause: {item.root_cause_summary}</p>
                    <p style={{ margin: "0.5rem 0 0" }}>Avoidance: {item.avoidance_summary}</p>
                  </li>
                ))}
              </ul>
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
const listStyle = { display: "grid", gap: "0.75rem", margin: 0, paddingLeft: "1.25rem" } as const;
const itemStyle = { display: "grid", gap: "0.25rem" } as const;
const metaStyle = { margin: 0, color: "#64748b", fontSize: "0.875rem" } as const;