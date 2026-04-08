import type { KnowledgeNodeCardDTO } from "../lib/api";

type KnowledgeNodeCardProps = {
  node: KnowledgeNodeCardDTO;
};

export function KnowledgeNodeCard({ node }: KnowledgeNodeCardProps) {
  return (
    <article
      style={{
        border: "1px solid rgba(148, 163, 184, 0.35)",
        borderRadius: "1rem",
        background: "rgba(255, 255, 255, 0.94)",
        padding: "1rem",
        display: "grid",
        gap: "0.5rem",
      }}
    >
      <div>
        <h3 style={{ margin: 0 }}>{node.label}</h3>
        <p style={{ margin: "0.35rem 0 0", color: "#64748b", fontSize: "0.875rem" }}>
          {node.node_type} / {node.abstract_level} / {node.scope}
        </p>
      </div>
      <p style={{ margin: 0 }}>{node.canonical_summary}</p>
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", fontSize: "0.9rem" }}>
        <span>Mastery: {node.mastery_status}</span>
        <span>Review needed: {node.review_needed ? "yes" : "no"}</span>
        <span>Evidence: {node.evidence_summary.evidence_count ?? 0}</span>
      </div>
    </article>
  );
}
