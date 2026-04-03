import { useEffect, useState } from "react";

import { useApiClient, type ProposalsViewDTO } from "../lib/api";

type ProposalsLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: ProposalsViewDTO; error: null };

export function ProposalsPage() {
  const client = useApiClient();
  const [state, setState] = useState<ProposalsLoadState>({ status: "loading", data: null, error: null });
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actingProposalId, setActingProposalId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

    client
      .getProposalsView()
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
            error: error instanceof Error ? error.message : "Unable to load proposals view.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [client]);

  async function handleAction(proposalId: string, actionType: "accept" | "reject" | "defer") {
    setActingProposalId(proposalId);
    setActionError(null);
    setActionMessage(null);
    try {
      const response = await client.submitProposalAction({
        request_id: `proposal-${proposalId}-${actionType}`,
        source_page: "proposals",
        actor_id: "local-user",
        created_at: new Date().toISOString(),
        proposal_id: proposalId,
        action_type: actionType,
        selected_target_ids: [],
      });
      const refreshed = await client.getProposalsView();
      setState({ status: "ready", data: refreshed, error: null });
      setActionMessage(response.execution_summary ?? response.message);
    } catch (error: unknown) {
      setActionError(error instanceof Error ? error.message : "Unable to apply proposal action.");
    } finally {
      setActingProposalId(null);
    }
  }

  return (
    <section style={{ display: "grid", gap: "1rem" }}>
      <div>
        <h1 style={{ margin: 0 }}>Proposals</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          Long-term proposal entries for future compression and maintenance work.
        </p>
      </div>

      {actionMessage ? (
        <div style={successPanelStyle} role="status">
          {actionMessage}
        </div>
      ) : null}
      {actionError ? (
        <div style={errorPanelStyle} role="alert">
          {actionError}
        </div>
      ) : null}

      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading proposals view...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load proposals view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Proposal summary</h2>
            <p style={{ margin: 0 }}>Total proposals: {state.data.total_count}</p>
            <p style={{ margin: "0.5rem 0 0" }}>Pending review: {state.data.pending_count}</p>
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Entries</h2>
            {state.data.items.length === 0 ? (
              <p style={{ margin: 0, color: "#64748b" }}>No proposals recorded yet.</p>
            ) : (
              <ul style={listStyle}>
                {state.data.items.map((item) => {
                  const disabled = actingProposalId === item.proposal_id;
                  const actionable = item.status === "pending_review";
                  return (
                    <li key={item.proposal_id} style={itemStyle}>
                      <h3 style={{ margin: 0 }}>{item.proposal_type}</h3>
                      <p style={metaStyle}>
                        {item.target_type} / {item.status} / {item.target_count} targets
                      </p>
                      <p style={{ margin: "0.5rem 0 0" }}>Reason: {item.reason}</p>
                      <p style={{ margin: "0.5rem 0 0" }}>Preview: {item.preview_summary}</p>
                      {item.latest_execution_summary ? (
                        <p style={{ margin: "0.5rem 0 0" }}>
                          Execution: {item.latest_execution_summary}
                        </p>
                      ) : null}
                      <div style={buttonRowStyle}>
                        <button type="button" disabled={!actionable || disabled} onClick={() => handleAction(item.proposal_id, "accept")}>
                          Accept
                        </button>
                        <button type="button" disabled={!actionable || disabled} onClick={() => handleAction(item.proposal_id, "reject")}>
                          Reject
                        </button>
                        <button type="button" disabled={!actionable || disabled} onClick={() => handleAction(item.proposal_id, "defer")}>
                          Defer
                        </button>
                      </div>
                    </li>
                  );
                })}
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

const successPanelStyle = {
  ...panelStyle,
  borderColor: "rgba(22, 163, 74, 0.45)",
  background: "rgba(240, 253, 244, 0.92)",
} as const;

const errorPanelStyle = {
  ...panelStyle,
  borderColor: "rgba(220, 38, 38, 0.45)",
  background: "rgba(254, 242, 242, 0.92)",
  color: "#b91c1c",
} as const;

const sectionHeadingStyle = { margin: "0 0 0.75rem" } as const;
const listStyle = { display: "grid", gap: "0.75rem", margin: 0, paddingLeft: "1.25rem" } as const;
const itemStyle = { display: "grid", gap: "0.25rem" } as const;
const metaStyle = { margin: 0, color: "#64748b", fontSize: "0.875rem" } as const;
const buttonRowStyle = { display: "flex", gap: "0.5rem", marginTop: "0.75rem", flexWrap: "wrap" } as const;