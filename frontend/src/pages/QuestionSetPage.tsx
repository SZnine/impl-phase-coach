import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useApiClient, type GenerateQuestionSetResponseDTO, type QuestionSetViewDTO, type StageViewDTO } from "../lib/api";

type QuestionSetLoadState =
  | { status: "loading"; data: null; stage: null; error: null }
  | { status: "error"; data: null; stage: null; error: string }
  | { status: "ready"; data: QuestionSetViewDTO; stage: StageViewDTO; error: null };

type QuestionSummary = QuestionSetViewDTO["questions"][number];

export function QuestionSetPage() {
  const {
    projectId = "unknown-project",
    stageId = "unknown-stage",
    questionSetId = "unknown-set",
  } = useParams();
  const client = useApiClient();
  const [state, setState] = useState<QuestionSetLoadState>({ status: "loading", data: null, stage: null, error: null });
  const [generationState, setGenerationState] = useState<"idle" | "generating">("idle");
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [generationResult, setGenerationResult] = useState<GenerateQuestionSetResponseDTO | null>(null);
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
    setState({ status: "loading", data: null, stage: null, error: null });
    setGenerationState("idle");
    setGenerationError(null);
    setGenerationResult(null);

    Promise.all([client.getQuestionSetView(projectId, stageId, questionSetId), client.getStageView(projectId, stageId)])
      .then(([data, stage]) => {
        if (active) {
          setState({ status: "ready", data, stage, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            status: "error",
            data: null,
            stage: null,
            error: error instanceof Error ? error.message : "Unable to load question set view.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [client, projectId, stageId, questionSetId]);

  async function handleGenerateQuestionSet() {
    if (state.status !== "ready") {
      return;
    }

    setGenerationState("generating");
    setGenerationError(null);
    setGenerationResult(null);

    try {
      const response = await client.generateQuestionSet({
        request_id: makeRequestId(),
        project_id: projectId,
        stage_id: stageId,
        source_page: "question_set",
        actor_id: "local-user",
        created_at: new Date().toISOString(),
        stage_label: state.stage.stage_label,
        stage_goal: state.stage.stage_goal,
        stage_summary: `Generate a practice question set for ${state.stage.stage_label}.`,
        stage_artifacts: ["question set read surface", "question detail read surface"],
        stage_exit_criteria: ["questions can be opened, answered, assessed, and accumulated into knowledge"],
        current_decisions: ["Question training is the primary user entry for the workbench."],
        key_logic_points: ["generated checkpoints must refresh the question set read surface"],
        known_weak_points: ["question quality may drift if project context is too generic"],
        boundary_focus: ["Project Agent output", "generated question checkpoint", "answer assessment"],
        question_strategy: "full_depth",
        max_questions: 4,
        source_refs: [`stage:${stageId}`, `question_set:${questionSetId}`],
      });
      const refreshedQuestionSet = await client.getQuestionSetView(projectId, stageId, questionSetId);
      setGenerationResult(response);
      setState({ status: "ready", data: refreshedQuestionSet, stage: state.stage, error: null });
    } catch (error: unknown) {
      setGenerationError(error instanceof Error ? error.message : "Unable to generate question set.");
    } finally {
      setGenerationState("idle");
    }
  }

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
            <div style={{ marginTop: "1rem", display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "center" }}>
              <button
                type="button"
                disabled={generationState === "generating"}
                onClick={handleGenerateQuestionSet}
                style={secondaryButtonStyle}
              >
                {generationState === "generating" ? "正在出题..." : "让 Project Agent 出一组新题"}
              </button>
              {generationResult ? (
                <span style={generationSuccessStyle}>已生成 {generationResult.questions.length} 道题，并刷新题目列表。</span>
              ) : null}
            </div>
            {generationError ? (
              <p style={{ margin: "0.75rem 0 0", color: "#b91c1c" }} role="alert">
                {generationError}
              </p>
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

function makeRequestId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}`;
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
const secondaryButtonStyle = {
  border: "1px solid rgba(21, 128, 61, 0.35)",
  borderRadius: "999px",
  padding: "0.65rem 0.9rem",
  background: "#fff",
  color: "#166534",
  fontWeight: 800,
  cursor: "pointer",
} as const;
const generationSuccessStyle = {
  color: "#15803d",
  fontWeight: 800,
} as const;
