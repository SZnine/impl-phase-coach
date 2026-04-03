import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useApiClient, type QuestionSetViewDTO } from "../lib/api";

type QuestionSetLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: QuestionSetViewDTO; error: null };

export function QuestionSetPage() {
  const {
    projectId = "unknown-project",
    stageId = "unknown-stage",
    questionSetId = "unknown-set",
  } = useParams();
  const client = useApiClient();
  const [state, setState] = useState<QuestionSetLoadState>({ status: "loading", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

    client
      .getQuestionSetView(projectId, stageId, questionSetId)
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
            error: error instanceof Error ? error.message : "Unable to load question set view.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [client, projectId, stageId, questionSetId]);

  return (
    <section style={{ display: "grid", gap: "1rem" }}>
      <div>
        <h1 style={{ margin: 0 }}>Question set</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          {projectId} / {stageId} / {questionSetId}
        </p>
      </div>

      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading question set...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load question set view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Question set: {state.data.question_set_title}</h2>
            <dl style={definitionListStyle}>
              <div>
                <dt style={termStyle}>Status</dt>
                <dd style={definitionStyle}>{state.data.status}</dd>
              </div>
              <div>
                <dt style={termStyle}>Questions</dt>
                <dd style={definitionStyle}>{state.data.question_count}</dd>
              </div>
              <div>
                <dt style={termStyle}>Current question</dt>
                <dd style={definitionStyle}>{state.data.current_question_id ?? "none"}</dd>
              </div>
            </dl>
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Questions</h2>
            <ul style={listStyle}>
              {state.data.questions.map((question) => (
                <li key={question.question_id} style={{ marginBottom: "0.75rem" }}>
                  <Link
                    to={`/projects/${projectId}/stages/${stageId}/questions/${questionSetId}/${question.question_id}`}
                  >
                    Question {question.question_id}
                  </Link>
                  <p style={{ margin: "0.25rem 0 0", color: "#475569" }}>
                    <strong>{question.question_level}</strong>
                  </p>
                  <p style={{ margin: "0.25rem 0 0", color: "#475569" }}>{question.prompt}</p>
                </li>
              ))}
            </ul>
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
const listStyle = { margin: 0, paddingLeft: "1.25rem" } as const;
