import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { KnowledgeNodeCard } from "../components/KnowledgeNodeCard";
import { useApiClient, type KnowledgeGraphMainViewDTO } from "../lib/api";

type KnowledgeGraphLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: KnowledgeGraphMainViewDTO; error: null };

export function KnowledgeGraphPage() {
  const client = useApiClient();
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<KnowledgeGraphLoadState>({ status: "loading", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });
    const clusterId = searchParams.get("cluster") ?? undefined;

    client
      .getKnowledgeGraphMainView(undefined, undefined, clusterId)
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
            error: error instanceof Error ? error.message : "Unable to load knowledge graph view.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [client, searchParams]);

  return (
    <section style={{ display: "grid", gap: "1rem" }}>
      <div>
        <h1 style={{ margin: 0 }}>Knowledge Graph</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          Durable knowledge nodes extracted from completed review assessments.
        </p>
      </div>

      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading knowledge graph view...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load knowledge graph view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Selected cluster</h2>
            {state.data.selected_cluster ? (
              <>
                <p style={{ margin: 0, fontWeight: 700 }}>{state.data.selected_cluster.title}</p>
                <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
                  {state.data.selected_cluster.focus_reason_summary}
                </p>
              </>
            ) : (
              <p style={{ margin: 0, color: "#64748b" }}>No cluster selected.</p>
            )}
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Map preview</h2>
            {state.data.nodes.length === 0 ? (
              <p style={{ margin: 0, color: "#64748b" }}>No visible nodes for the current cluster.</p>
            ) : (
              <div style={{ display: "grid", gap: "1rem" }}>
                <div style={previewColumnsStyle}>
                  <div>
                    <p style={subtleLabelStyle}>Center node</p>
                    <div style={nodePillStyle}>
                      {state.data.selected_cluster
                        ? getNodeLabel(state.data, state.data.selected_cluster.center_node_id)
                        : state.data.nodes[0]?.label ?? "Unknown node"}
                    </div>
                  </div>
                  <div>
                    <p style={subtleLabelStyle}>Related nodes</p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                      {getNeighborNodes(state.data).length === 0 ? (
                        <span style={emptyHintStyle}>No neighboring nodes in this cluster.</span>
                      ) : (
                        getNeighborNodes(state.data).map((node) => (
                          <div key={node.node_id} style={neighborPillStyle}>
                            {node.label}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                <div>
                  <p style={subtleLabelStyle}>Connections</p>
                  {state.data.relations.length === 0 ? (
                    <span style={emptyHintStyle}>No visible relations in this cluster.</span>
                  ) : (
                    <div style={{ display: "grid", gap: "0.5rem" }}>
                      {state.data.relations.map((relation) => (
                        <div key={relation.relation_id} style={relationRowStyle}>
                          <span style={relationNodeStyle}>{getNodeLabel(state.data, relation.source_node_id)}</span>
                          <span style={relationBadgeStyle}>{formatRelationType(relation.relation_type)}</span>
                          <span style={relationNodeStyle}>{getNodeLabel(state.data, relation.target_node_id)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Nodes</h2>
            {state.data.nodes.length === 0 ? (
              <p style={{ margin: 0, color: "#64748b" }}>No durable knowledge nodes recorded yet.</p>
            ) : (
              <div style={gridStyle}>
                {state.data.nodes.map((node) => (
                  <KnowledgeNodeCard key={node.node_id} node={node} />
                ))}
              </div>
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
const gridStyle = { display: "grid", gap: "0.75rem" } as const;
const previewColumnsStyle = {
  display: "grid",
  gap: "1rem",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
} as const;
const subtleLabelStyle = {
  margin: "0 0 0.5rem",
  color: "#64748b",
  fontSize: "0.85rem",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.03em",
} as const;
const nodePillStyle = {
  display: "inline-flex",
  alignItems: "center",
  padding: "0.55rem 0.8rem",
  borderRadius: "999px",
  background: "#dbeafe",
  color: "#1d4ed8",
  fontWeight: 700,
} as const;
const neighborPillStyle = {
  display: "inline-flex",
  alignItems: "center",
  padding: "0.45rem 0.7rem",
  borderRadius: "999px",
  background: "#f8fafc",
  border: "1px solid rgba(148, 163, 184, 0.35)",
  color: "#334155",
} as const;
const emptyHintStyle = { color: "#64748b", fontSize: "0.9rem" } as const;
const relationRowStyle = {
  display: "grid",
  gap: "0.75rem",
  alignItems: "center",
  gridTemplateColumns: "minmax(0, 1fr) auto minmax(0, 1fr)",
} as const;
const relationBadgeStyle = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "0.25rem 0.55rem",
  borderRadius: "999px",
  background: "#fef3c7",
  color: "#92400e",
  fontSize: "0.82rem",
  fontWeight: 700,
  textTransform: "lowercase",
} as const;
const relationNodeStyle = {
  color: "#0f172a",
  fontWeight: 600,
} as const;

function getNeighborNodes(data: KnowledgeGraphMainViewDTO) {
  if (!data.selected_cluster) {
    return data.nodes.slice(1);
  }
  const neighborIds = new Set(data.selected_cluster.neighbor_node_ids);
  return data.nodes.filter((node) => neighborIds.has(node.node_id));
}

function getNodeLabel(data: KnowledgeGraphMainViewDTO, nodeId: string) {
  return data.nodes.find((node) => node.node_id === nodeId)?.label ?? nodeId;
}

function formatRelationType(relationType: string) {
  return relationType.replace(/_/g, " ");
}
