import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useApiClient, type KnowledgeMapSummaryViewDTO } from "../lib/api";

type KnowledgeMapLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: KnowledgeMapSummaryViewDTO; error: null };

export function KnowledgeMapPage() {
  const client = useApiClient();
  const [state, setState] = useState<KnowledgeMapLoadState>({ status: "loading", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

    client
      .getKnowledgeMapSummaryView()
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
            error: error instanceof Error ? error.message : "Unable to load knowledge map summary.",
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
        <h1 style={{ margin: 0 }}>Knowledge Map</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          Start from a focused knowledge summary, then open the graph main view for the active cluster.
        </p>
      </div>

      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading knowledge map summary...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load knowledge map summary.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Current weak spots</h2>
            {state.data.current_weak_spots.length > 0 ? (
              <ul style={inlineListStyle}>
                {state.data.current_weak_spots.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p style={{ margin: 0, color: "#64748b" }}>No current weak spots highlighted.</p>
            )}
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Current focus clusters</h2>
            {state.data.focus_clusters.length === 0 ? (
              <p style={{ margin: 0, color: "#64748b" }}>No focus clusters generated yet.</p>
            ) : (
              <div style={{ display: "grid", gap: "1rem" }}>
                {state.data.focus_clusters.map((cluster) => (
                  <article key={cluster.cluster_id} style={cardStyle}>
                    <h3 style={{ margin: 0 }}>{cluster.title}</h3>
                    <p style={{ margin: "0.35rem 0 0", color: "#64748b" }}>Center node: {cluster.center_node_id}</p>
                    {cluster.neighbor_node_ids.length > 0 ? (
                      <p style={{ margin: "0.5rem 0 0" }}>
                        Related nodes: {cluster.neighbor_node_ids.slice(0, 3).join(", ")}
                      </p>
                    ) : null}
                    {cluster.focus_reason_codes.length > 0 ? (
                      <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                        {cluster.focus_reason_codes.map((code) => (
                          <span key={code} style={reasonBadgeStyle}>
                            {formatFocusReasonCode(code)}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <div style={{ marginTop: "0.75rem", display: "grid", gap: "0.35rem" }}>
                      <p style={whyLabelStyle}>Why it matters</p>
                      <p style={{ margin: 0 }}>{cluster.focus_reason_summary}</p>
                    </div>
                    <p style={{ margin: "0.75rem 0 0" }}>
                      <Link to={`/knowledge/graph?cluster=${cluster.cluster_id}`}>Open map cluster</Link>
                    </p>
                  </article>
                ))}
              </div>
            )}
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Foundation hotspots</h2>
            {state.data.foundation_hotspots.length > 0 ? (
              <ul style={inlineListStyle}>
                {state.data.foundation_hotspots.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p style={{ margin: 0, color: "#64748b" }}>No foundation hotspots highlighted yet.</p>
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

const cardStyle = {
  border: "1px solid rgba(148, 163, 184, 0.25)",
  borderRadius: "0.875rem",
  padding: "1rem",
  background: "#f8fafc",
} as const;

const sectionHeadingStyle = { margin: "0 0 0.75rem" } as const;
const inlineListStyle = { display: "grid", gap: "0.5rem", margin: 0, paddingLeft: "1.25rem" } as const;
const reasonBadgeStyle = {
  display: "inline-flex",
  alignItems: "center",
  padding: "0.3rem 0.55rem",
  borderRadius: "999px",
  background: "#eef2ff",
  color: "#4338ca",
  fontSize: "0.82rem",
  fontWeight: 700,
} as const;
const whyLabelStyle = {
  margin: 0,
  color: "#64748b",
  fontSize: "0.85rem",
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.03em",
} as const;

function formatFocusReasonCode(code: string) {
  return code
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
