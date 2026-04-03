import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  useApiClient,
  type StageViewDTO,
  type QuestionViewDTO,
  type SubmitAnswerResponseDTO,
} from "../lib/api";

type QuestionPageState =
  | { status: "loading"; stage: null; question: null; error: null }
  | { status: "error"; stage: null; question: null; error: string }
  | { status: "ready"; stage: StageViewDTO; question: QuestionViewDTO; error: null };

function makeRequestId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}`;
}

export function QuestionPage() {
  const {
    projectId = "unknown-project",
    stageId = "unknown-stage",
    questionSetId = "unknown-set",
    questionId = "unknown-question",
  } = useParams();
  const client = useApiClient();
  const [pageState, setPageState] = useState<QuestionPageState>({
    status: "loading",
    stage: null,
    question: null,
    error: null,
  });
  const [answerText, setAnswerText] = useState("");
  const [submitState, setSubmitState] = useState<"idle" | "submitting">("idle");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitResult, setSubmitResult] = useState<SubmitAnswerResponseDTO | null>(null);

  useEffect(() => {
    let active = true;
    setPageState({ status: "loading", stage: null, question: null, error: null });
    setAnswerText("");
    setSubmitState("idle");
    setSubmitError(null);
    setSubmitResult(null);

    Promise.all([
      client.getStageView(projectId, stageId),
      client.getQuestionView(projectId, stageId, questionSetId, questionId),
    ])
      .then(([stage, question]) => {
        if (active) {
          setPageState({ status: "ready", stage, question, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setPageState({
            status: "error",
            stage: null,
            question: null,
            error: error instanceof Error ? error.message : "Unable to load question view.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [client, projectId, stageId, questionSetId, questionId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitState("submitting");
    setSubmitError(null);
    setSubmitResult(null);

    try {
      const response = await client.submitAnswer({
        request_id: makeRequestId(),
        project_id: projectId,
        stage_id: stageId,
        source_page: "question_detail",
        actor_id: "local-user",
        created_at: new Date().toISOString(),
        question_set_id: questionSetId,
        question_id: questionId,
        answer_text: answerText,
        draft_id: null,
      });
      setSubmitResult(response);

      const refreshedStage = await client.getStageView(projectId, stageId);
      setPageState((current) =>
        current.status === "ready"
          ? {
              status: "ready",
              stage: refreshedStage,
              question: current.question,
              error: null,
            }
          : current,
      );
    } catch (error: unknown) {
      setSubmitError(error instanceof Error ? error.message : "Unable to submit answer.");
    } finally {
      setSubmitState("idle");
    }
  }

  return (
    <section style={{ display: "grid", gap: "1rem" }}>
      <div>
        <h1 style={{ margin: 0 }}>Question</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          {projectId} / {stageId} / {questionSetId} / {questionId}
        </p>
      </div>

      {pageState.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading question...
        </div>
      ) : pageState.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load question view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{pageState.error}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          <article style={panelStyle}>
            <h2 style={{ margin: "0 0 0.75rem" }}>Question: {pageState.question.prompt}</h2>
            <p style={{ margin: 0, color: "#475569" }}>Question {pageState.question.question_id}</p>
            <dl style={definitionListStyle}>
              <div>
                <dt style={termStyle}>Level</dt>
                <dd style={definitionStyle}>{pageState.question.question_level}</dd>
              </div>
              <div>
                <dt style={termStyle}>Intent</dt>
                <dd style={definitionStyle}>{pageState.question.intent}</dd>
              </div>
              <div>
                <dt style={termStyle}>Answer placeholder</dt>
                <dd style={definitionStyle}>{pageState.question.answer_placeholder}</dd>
              </div>
              <div>
                <dt style={termStyle}>Status</dt>
                <dd style={definitionStyle}>{pageState.question.status}</dd>
              </div>
            </dl>
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Stage summary</h2>
            <dl style={definitionListStyle}>
              <div>
                <dt style={termStyle}>Stage status</dt>
                <dd style={definitionStyle}>{pageState.stage.status}</dd>
              </div>
              <div>
                <dt style={termStyle}>Mastery</dt>
                <dd style={definitionStyle}>{pageState.stage.mastery_status}</dd>
              </div>
              <div>
                <dt style={termStyle}>Active question set</dt>
                <dd style={definitionStyle}>{pageState.stage.active_question_set_id ?? "none"}</dd>
              </div>
            </dl>
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Submit answer</h2>
            <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.75rem" }}>
              <label style={{ display: "grid", gap: "0.5rem" }}>
                <span style={termStyle}>Answer</span>
                <textarea
                  aria-label="Answer"
                  value={answerText}
                  onChange={(event) => setAnswerText(event.target.value)}
                  placeholder={pageState.question.answer_placeholder}
                  rows={6}
                  style={textareaStyle}
                />
              </label>
              <div>
                <button type="submit" disabled={submitState === "submitting"} style={buttonStyle}>
                  {submitState === "submitting" ? "Submitting..." : "Submit answer"}
                </button>
              </div>
            </form>
            {submitError ? (
              <p style={{ margin: "0.75rem 0 0", color: "#b91c1c" }} role="alert">
                {submitError}
              </p>
            ) : null}
            {submitResult ? (
              <div style={{ marginTop: "0.75rem" }}>
                <p style={{ margin: 0, fontWeight: 700 }}>{submitResult.message}</p>
                {submitResult.assessment_summary ? (
                  <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
                    Answer excerpt: {submitResult.assessment_summary.answer_excerpt}
                  </p>
                ) : null}
              </div>
            ) : null}
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>Allowed actions</h2>
            <ul style={listStyle}>
              {pageState.question.allowed_actions.map((action) => (
                <li key={action}>{action}</li>
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
const textareaStyle = {
  width: "100%",
  minHeight: "8rem",
  padding: "0.75rem",
  borderRadius: "0.75rem",
  border: "1px solid rgba(148, 163, 184, 0.6)",
  font: "inherit",
} as const;
const buttonStyle = {
  border: 0,
  borderRadius: "999px",
  padding: "0.75rem 1.1rem",
  background: "#0f172a",
  color: "#fff",
  fontWeight: 700,
  cursor: "pointer",
} as const;
