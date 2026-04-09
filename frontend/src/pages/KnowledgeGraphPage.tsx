import { useEffect, useMemo, useState } from "react";
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
  const [relationTypeFilter, setRelationTypeFilter] = useState<string>("all");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedRelationId, setSelectedRelationId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });
    setRelationTypeFilter("all");
    setSelectedNodeId(null);
    setSelectedRelationId(null);
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

  const readyState = state.status === "ready" ? state.data : null;
  const visibleRelations = useMemo(
    () => (readyState ? getVisibleRelations(readyState, relationTypeFilter) : []),
    [readyState, relationTypeFilter],
  );
  const relationGroups = useMemo(() => getRelationGroupsFromList(visibleRelations), [visibleRelations]);
  const highlightedNodeIds = useMemo(
    () => (readyState ? getHighlightedNodeIds(readyState, selectedNodeId, selectedRelationId) : new Set<string>()),
    [readyState, selectedNodeId, selectedRelationId],
  );
  const highlightedRelationIds = useMemo(
    () =>
      readyState ? getHighlightedRelationIds(readyState, selectedNodeId, selectedRelationId) : new Set<string>(),
    [readyState, selectedNodeId, selectedRelationId],
  );

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
                <div style={overviewGridStyle}>
                  <div style={overviewCardStyle}>
                    <p style={subtleLabelStyle}>Visible nodes</p>
                    <p style={overviewValueStyle}>{state.data.nodes.length}</p>
                  </div>
                  <div style={overviewCardStyle}>
                    <p style={subtleLabelStyle}>Visible relations</p>
                    <p style={overviewValueStyle}>{visibleRelations.length}</p>
                  </div>
                  <div style={overviewCardStyle}>
                    <p style={subtleLabelStyle}>Relation types</p>
                    <p style={overviewValueStyle}>{relationGroups.length}</p>
                  </div>
                </div>

                <div style={previewColumnsStyle}>
                  <div style={centerNodePanelStyle}>
                    <p style={subtleLabelStyle}>Center node</p>
                    {getCenterNode(state.data) ? (
                      <>
                        <div style={nodePillStyle}>{getCenterNode(state.data)?.label}</div>
                        <p style={{ margin: "0.75rem 0 0", color: "#1e293b", fontWeight: 600 }}>
                          {getCenterNode(state.data)?.node_type} / {getCenterNode(state.data)?.abstract_level}
                        </p>
                        <p style={{ margin: "0.35rem 0 0", color: "#475569" }}>
                          {getCenterNode(state.data)?.canonical_summary}
                        </p>
                      </>
                    ) : (
                      <div style={nodePillStyle}>Unknown node</div>
                    )}
                  </div>
                  <div>
                    <p style={subtleLabelStyle}>Related nodes</p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                      {getNeighborNodes(state.data).length === 0 ? (
                        <span style={emptyHintStyle}>No neighboring nodes in this cluster.</span>
                      ) : (
                        getNeighborNodes(state.data).map((node) => (
                          <div
                            key={node.node_id}
                            style={{
                              ...neighborPillStyle,
                              ...(highlightedNodeIds.has(node.node_id) ? highlightedNeighborPillStyle : null),
                            }}
                          >
                            {node.label}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                <div style={legendPanelStyle}>
                  <p style={subtleLabelStyle}>Relation guide</p>
                  <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      onClick={() => setRelationTypeFilter("all")}
                      aria-pressed={relationTypeFilter === "all"}
                      style={{
                        ...filterButtonStyle,
                        ...(relationTypeFilter === "all" ? filterButtonActiveStyle : null),
                      }}
                    >
                      All
                    </button>
                    {relationGroups.length === 0 ? (
                      <span style={emptyHintStyle}>No relation types visible in this cluster.</span>
                    ) : (
                      relationGroups.map(([relationType, relations]) => (
                        <button
                          key={relationType}
                          type="button"
                          aria-label={formatRelationType(relationType)}
                          onClick={() => setRelationTypeFilter(relationType)}
                          aria-pressed={relationTypeFilter === relationType}
                          style={{
                            ...filterButtonStyle,
                            ...(relationTypeFilter === relationType ? filterButtonActiveStyle : null),
                          }}
                        >
                          {formatRelationType(relationType)} ({relations.length})
                        </button>
                      ))
                    )}
                  </div>
                </div>

                <div>
                  <p style={subtleLabelStyle}>Connections by type</p>
                  {visibleRelations.length === 0 ? (
                    <span style={emptyHintStyle}>No visible relations in this cluster.</span>
                  ) : (
                    <div style={{ display: "grid", gap: "0.5rem" }}>
                      {relationGroups.map(([relationType, relations]) => (
                        <section key={relationType} style={relationGroupStyle}>
                          <h3 style={relationGroupHeadingStyle}>
                            {formatRelationType(relationType)} ({relations.length})
                          </h3>
                          <div style={{ display: "grid", gap: "0.5rem" }}>
                            {relations.map((relation) => (
                              <button
                                key={relation.relation_id}
                                type="button"
                                aria-label={relation.relation_id}
                                aria-pressed={selectedRelationId === relation.relation_id}
                                data-highlighted={highlightedRelationIds.has(relation.relation_id)}
                                onClick={() => {
                                  setSelectedRelationId((current) =>
                                    current === relation.relation_id ? null : relation.relation_id,
                                  );
                                  setSelectedNodeId(null);
                                }}
                                style={{
                                  ...relationRowStyle,
                                  ...(selectedRelationId === relation.relation_id ? relationRowSelectedStyle : null),
                                  ...(highlightedRelationIds.has(relation.relation_id)
                                    ? relationRowHighlightedStyle
                                    : null),
                                }}
                              >
                                <a href={`#node-${relation.source_node_id}`} style={relationLinkStyle}>
                                  {getNodeLabel(state.data, relation.source_node_id)}
                                </a>
                                <span style={relationBadgeStyle}>{formatRelationType(relation.relation_type)}</span>
                                <a href={`#node-${relation.target_node_id}`} style={relationLinkStyle}>
                                  {getNodeLabel(state.data, relation.target_node_id)}
                                </a>
                              </button>
                            ))}
                          </div>
                        </section>
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
                  <button
                    type="button"
                    aria-label={`node-${node.node_id}`}
                    aria-pressed={highlightedNodeIds.has(node.node_id)}
                    onClick={() => {
                      setSelectedNodeId((current) => (current === node.node_id ? null : node.node_id));
                      setSelectedRelationId(null);
                    }}
                    key={node.node_id}
                    id={`node-${node.node_id}`}
                    style={{
                      ...nodeCardButtonStyle,
                      ...(node.node_id === state.data.selected_cluster?.center_node_id ? centerCardShellStyle : null),
                      ...(highlightedNodeIds.has(node.node_id) ? highlightedCardShellStyle : null),
                    }}
                  >
                    <KnowledgeNodeCard node={node} />
                  </button>
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
const overviewGridStyle = {
  display: "grid",
  gap: "0.75rem",
  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
} as const;
const overviewCardStyle = {
  border: "1px solid rgba(148, 163, 184, 0.3)",
  borderRadius: "0.9rem",
  background: "#f8fafc",
  padding: "0.85rem",
} as const;
const overviewValueStyle = {
  margin: 0,
  color: "#0f172a",
  fontSize: "1.4rem",
  fontWeight: 800,
} as const;
const previewColumnsStyle = {
  display: "grid",
  gap: "1rem",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
} as const;
const centerNodePanelStyle = {
  borderRadius: "1rem",
  background: "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)",
  border: "1px solid rgba(96, 165, 250, 0.35)",
  padding: "1rem",
} as const;
const legendPanelStyle = {
  borderRadius: "0.9rem",
  background: "#fffbeb",
  border: "1px solid rgba(245, 158, 11, 0.2)",
  padding: "0.9rem",
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
const highlightedNeighborPillStyle = {
  background: "#dbeafe",
  border: "1px solid rgba(96, 165, 250, 0.45)",
  color: "#1d4ed8",
} as const;
const emptyHintStyle = { color: "#64748b", fontSize: "0.9rem" } as const;
const relationGroupStyle = {
  border: "1px solid rgba(148, 163, 184, 0.25)",
  borderRadius: "0.9rem",
  background: "#fff",
  padding: "0.8rem",
} as const;
const relationGroupHeadingStyle = {
  margin: "0 0 0.75rem",
  color: "#0f172a",
  fontSize: "0.95rem",
} as const;
const relationRowStyle = {
  appearance: "none",
  width: "100%",
  display: "grid",
  gap: "0.75rem",
  alignItems: "center",
  gridTemplateColumns: "minmax(0, 1fr) auto minmax(0, 1fr)",
  padding: "0.7rem 0.8rem",
  borderRadius: "0.8rem",
  background: "#ffffff",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  cursor: "pointer",
  textAlign: "left",
} as const;
const relationRowSelectedStyle = {
  border: "1px solid rgba(59, 130, 246, 0.55)",
  boxShadow: "0 0 0 2px rgba(59, 130, 246, 0.16)",
} as const;
const relationRowHighlightedStyle = {
  background: "#eff6ff",
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
const relationLinkStyle = {
  color: "#0f172a",
  fontWeight: 600,
  textDecoration: "none",
} as const;
const centerCardShellStyle = {
  borderRadius: "1rem",
  boxShadow: "0 0 0 2px rgba(37, 99, 235, 0.12)",
} as const;
const highlightedCardShellStyle = {
  borderRadius: "1rem",
  boxShadow: "0 0 0 2px rgba(59, 130, 246, 0.28)",
} as const;
const nodeCardButtonStyle = {
  appearance: "none",
  width: "100%",
  border: "none",
  background: "transparent",
  padding: 0,
  cursor: "pointer",
  textAlign: "left",
} as const;
const filterButtonStyle = {
  appearance: "none",
  border: "1px solid rgba(148, 163, 184, 0.28)",
  borderRadius: "999px",
  background: "#ffffff",
  color: "#0f172a",
  padding: "0.3rem 0.65rem",
  fontWeight: 700,
  cursor: "pointer",
} as const;
const filterButtonActiveStyle = {
  background: "#dbeafe",
  border: "1px solid rgba(96, 165, 250, 0.45)",
  color: "#1d4ed8",
} as const;

function getCenterNode(data: KnowledgeGraphMainViewDTO) {
  const centerNodeId = data.selected_cluster?.center_node_id;
  if (!centerNodeId) {
    return data.nodes[0] ?? null;
  }
  return data.nodes.find((node) => node.node_id === centerNodeId) ?? null;
}

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

function getRelationGroups(data: KnowledgeGraphMainViewDTO) {
  return getRelationGroupsFromList(data.relations);
}

function getRelationGroupsFromList(relations: KnowledgeGraphMainViewDTO["relations"]) {
  const groups = new Map<string, KnowledgeGraphMainViewDTO["relations"]>();
  for (const relation of relations) {
    const existing = groups.get(relation.relation_type);
    if (existing) {
      existing.push(relation);
    } else {
      groups.set(relation.relation_type, [relation]);
    }
  }
  return [...groups.entries()];
}

function getVisibleRelations(data: KnowledgeGraphMainViewDTO, relationTypeFilter: string) {
  if (relationTypeFilter === "all") {
    return data.relations;
  }
  return data.relations.filter((relation) => relation.relation_type === relationTypeFilter);
}

function getHighlightedNodeIds(
  data: KnowledgeGraphMainViewDTO,
  selectedNodeId: string | null,
  selectedRelationId: string | null,
) {
  if (selectedRelationId) {
    const relation = data.relations.find((item) => item.relation_id === selectedRelationId);
    return new Set(relation ? [relation.source_node_id, relation.target_node_id] : []);
  }
  if (selectedNodeId) {
    return new Set([selectedNodeId]);
  }
  return new Set<string>();
}

function getHighlightedRelationIds(
  data: KnowledgeGraphMainViewDTO,
  selectedNodeId: string | null,
  selectedRelationId: string | null,
) {
  if (selectedRelationId) {
    return new Set([selectedRelationId]);
  }
  if (selectedNodeId) {
    return new Set(
      data.relations
        .filter((relation) => relation.source_node_id === selectedNodeId || relation.target_node_id === selectedNodeId)
        .map((relation) => relation.relation_id),
    );
  }
  return new Set<string>();
}

function formatRelationType(relationType: string) {
  return relationType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
