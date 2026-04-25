import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useApiClient, type QuestionSetViewDTO } from "../lib/api";

type QuestionSetLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: QuestionSetViewDTO; error: null };

type QuestionSummary = QuestionSetViewDTO["questions"][number];

export function QuestionSetPage() {
  const {
    projectId = "unknown-project",
    stageId = "unknown-stage",
    questionSetId = "unknown-set",
  } = useParams();
  const client = useApiClient();
  const [state, setState] = useState<QuestionSetLoadState>({ status: "loading", data: null, error: null });
  const entryQuestion =
    state.status === "ready"
      ? state.data.questions.find((question) => question.question_id === state.data.current_question_id) ??
        state.data.questions[0] ??
        null
      : null;
  const completedQuestionCount =
    state.status === "ready" ? state.data.questions.filter((question) => isCompletedQuestion(question)).length : 0;
  const totalQuestionCount = state.status === "ready" ? state.data.questions.length : 0;

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
        <h1 style={{ margin: 0 }}>题目训练</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          今天先完成一组高质量题目，答完后会给出评析并沉淀到知识库。
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
            <h2 style={sectionHeadingStyle}>当前推荐题</h2>
            <p style={{ margin: "0 0 0.75rem", color: "#475569" }}>
              {state.data.question_set_title} · {projectId} / {stageId} / {questionSetId}
            </p>
            <dl style={definitionListStyle}>
              <div>
                <dt style={termStyle}>题集状态</dt>
                <dd style={definitionStyle}>{state.data.status}</dd>
              </div>
              <div>
                <dt style={termStyle}>题目进度</dt>
                <dd style={definitionStyle}>
                  {state.data.question_count}
                  <span style={progressLabelStyle}>已完成 {completedQuestionCount} / {totalQuestionCount}</span>
                </dd>
              </div>
              <div>
                <dt style={termStyle}>当前题目</dt>
                <dd style={definitionStyle}>{state.data.current_question_id ?? "none"}</dd>
              </div>
            </dl>
            {entryQuestion ? (
              <div style={{ marginTop: "1rem" }}>
                <Link
                  to={`/projects/${projectId}/stages/${stageId}/questions/${questionSetId}/${entryQuestion.question_id}`}
                  style={buttonLinkStyle}
                >
                  立即答题
                </Link>
                <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
                  当前推荐：{entryQuestion.prompt}
                </p>
              </div>
            ) : null}
          </article>

          <article style={panelStyle}>
            <h2 style={sectionHeadingStyle}>题目列表</h2>
            <ul style={listStyle}>
              {state.data.questions.map((question) => {
                const displayStatus = getQuestionDisplayStatus(question, state.data.current_question_id);

                return (
                  <li key={question.question_id} style={{ marginBottom: "0.75rem" }}>
                    <div style={questionTitleRowStyle}>
                      <Link
                        to={`/projects/${projectId}/stages/${stageId}/questions/${questionSetId}/${question.question_id}`}
                      >
                        题目 {question.question_id}
                      </Link>
                      <span style={displayStatus.style}>{displayStatus.label}</span>
                    </div>
                    <p style={{ margin: "0.25rem 0 0", color: "#475569" }}>
                      <strong>{question.question_level}</strong>
                    </p>
                    <p style={{ margin: "0.25rem 0 0", color: "#475569" }}>{question.prompt}</p>
                  </li>
                );
              })}
            </ul>
          </article>
        </div>
      )}
    </section>
  );
}

function getQuestionDisplayStatus(question: QuestionSummary, currentQuestionId: string | null) {
  if (question.question_id === currentQuestionId) {
    return { label: "当前题", style: currentQuestionStatusStyle };
  }

  if (isCompletedQuestion(question)) {
    return { label: "已完成", style: completedQuestionStatusStyle };
  }

  return { label: "待完成", style: pendingQuestionStatusStyle };
}

function isCompletedQuestion(question: QuestionSummary) {
  return ["answered", "assessed", "completed", "submitted"].includes(question.status.toLowerCase());
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
const progressLabelStyle = {
  display: "inline-flex",
  marginLeft: "0.75rem",
  color: "#15803d",
  fontWeight: 800,
} as const;
const questionTitleRowStyle = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "0.75rem",
} as const;
const questionStatusBaseStyle = {
  borderRadius: "999px",
  padding: "0.2rem 0.6rem",
  fontSize: "0.8rem",
  fontWeight: 800,
  whiteSpace: "nowrap",
} as const;
const currentQuestionStatusStyle = {
  ...questionStatusBaseStyle,
  background: "#ecfdf5",
  color: "#15803d",
} as const;
const completedQuestionStatusStyle = {
  ...questionStatusBaseStyle,
  background: "#dcfce7",
  color: "#166534",
} as const;
const pendingQuestionStatusStyle = {
  ...questionStatusBaseStyle,
  background: "#f8fafc",
  color: "#64748b",
} as const;
const buttonLinkStyle = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  borderRadius: "999px",
  padding: "0.7rem 1rem",
  background: "#15803d",
  color: "#fff",
  fontWeight: 800,
  textDecoration: "none",
} as const;
