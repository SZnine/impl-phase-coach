import { useEffect, useState } from "react";

import { useApiClient, type KnowledgeIndexViewDTO } from "../lib/api";

type KnowledgeIndexLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: KnowledgeIndexViewDTO; error: null };

export function KnowledgeIndexPage() {
  const client = useApiClient();
  const [state, setState] = useState<KnowledgeIndexLoadState>({ status: "loading", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

    client
      .getKnowledgeIndexView()
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
            error: error instanceof Error ? error.message : "Unable to load knowledge index view.",
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
        <h1 style={{ margin: 0 }}>Knowledge Index</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          Durable, readable index entries extracted from completed review assessments.
        </p>
      </div>

      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading knowledge index view...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load knowledge index view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Index summary</h2>
            <p style={{ margin: 0 }}>Total entries: {state.data.total_count}</p>
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Entries</h2>
            {state.data.items.length === 0 ? (
              <p style={{ margin: 0, color: "#64748b" }}>No durable knowledge entries recorded yet.</p>
            ) : (
              <ul style={listStyle}>
                {state.data.items.map((item) => (
                  <li key={item.entry_id} style={itemStyle}>
                    <h3 style={{ margin: 0 }}>{item.title}</h3>
                    <p style={metaStyle}>
                      {item.project_id} / {item.stage_id} / {item.entry_type}
                    </p>
                    <p style={{ margin: "0.5rem 0 0" }}>{item.summary}</p>
                    {item.linked_mistake_ids.length > 0 ? (
                      <p style={{ margin: "0.5rem 0 0" }}>
                        Linked mistakes: {item.linked_mistake_ids.join(", ")}
                      </p>
                    ) : null}
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