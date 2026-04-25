import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  useApiClient,
  type AssessmentReviewViewDTO,
  type QuestionSetViewDTO,
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
  const [assessmentReview, setAssessmentReview] = useState<AssessmentReviewViewDTO | null>(null);
  const [nextQuestionId, setNextQuestionId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setPageState({ status: "loading", stage: null, question: null, error: null });
    setAnswerText("");
    setSubmitState("idle");
    setSubmitError(null);
    setSubmitResult(null);
    setAssessmentReview(null);
    setNextQuestionId(null);

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
    setAssessmentReview(null);
    setNextQuestionId(null);

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

      const shouldRefreshQuestionSet = response.refresh_targets.includes("question_set");
      const [refreshedStage, latestReview, questionSet] = await Promise.all([
        client.getStageView(projectId, stageId),
        client.getLatestAssessmentReview(projectId, stageId),
        shouldRefreshQuestionSet ? client.getQuestionSetView(projectId, stageId, questionSetId) : Promise.resolve(null),
      ]);
      setAssessmentReview(latestReview);
      setNextQuestionId(questionSet ? findNextQuestionId(questionSet, questionId) : null);
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

          {assessmentReview?.has_assessment ? (
            <AssessmentReviewPanel
              review={assessmentReview}
              projectId={projectId}
              stageId={stageId}
              questionSetId={questionSetId}
              nextQuestionId={nextQuestionId}
            />
          ) : null}

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

function findNextQuestionId(questionSet: QuestionSetViewDTO, currentQuestionId: string) {
  const currentIndex = questionSet.questions.findIndex((question) => question.question_id === currentQuestionId);
  if (currentIndex < 0) {
    return null;
  }
  return questionSet.questions[currentIndex + 1]?.question_id ?? null;
}

function AssessmentReviewPanel({
  review,
  projectId,
  stageId,
  questionSetId,
  nextQuestionId,
}: {
  review: AssessmentReviewViewDTO;
  projectId: string;
  stageId: string;
  questionSetId: string;
  nextQuestionId: string | null;
}) {
  const questionSetHref = `/projects/${projectId}/stages/${stageId}/questions/${questionSetId}`;
  const nextQuestionHref = nextQuestionId ? `${questionSetHref}/${nextQuestionId}` : null;

  return (
    <article style={panelStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "start" }}>
        <div>
          <h2 style={sectionHeadingStyle}>评析解析</h2>
          <p style={{ margin: 0, fontWeight: 800 }}>{review.review_title}</p>
        </div>
        <span style={scorePillStyle}>
          {review.verdict_label} · {review.score_percent}%
        </span>
      </div>
      {review.review_summary ? (
        <p style={{ margin: "0.75rem 0 0", color: "#334155", lineHeight: 1.7 }}>{review.review_summary}</p>
      ) : null}
      <ReviewList title="答得不错的地方" items={review.correct_points} />
      <ReviewList title="需要补齐的缺口" items={review.gap_points} />
      <ReviewList title="可能的误区" items={review.misconception_points} />
      <ReviewList title="下一组追问题" items={review.recommended_follow_up_questions} />

      {review.knowledge_updates.length > 0 ? (
        <section style={{ marginTop: "1rem" }}>
          <h3 style={smallHeadingStyle}>知识沉淀</h3>
          <ul style={listStyle}>
            {review.knowledge_updates.map((update, index) => (
              <li key={`${update.title ?? "knowledge"}-${index}`}>
                <strong>{update.title ? `知识点：${update.title}` : "知识点"}</strong>
                {update.summary ? <span>: {update.summary}</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {review.next_action_label ? (
        <p style={{ margin: "1rem 0 0", fontWeight: 800, color: "#15803d" }}>{review.next_action_label}</p>
      ) : null}

      <nav aria-label="Assessment follow-up actions" style={reviewNavStyle}>
        <Link to={questionSetHref} style={secondaryLinkStyle}>
          返回题集
        </Link>
        {nextQuestionHref ? (
          <Link to={nextQuestionHref} style={primaryLinkStyle}>
            进入下一题
          </Link>
        ) : null}
      </nav>
    </article>
  );
}

function ReviewList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section style={{ marginTop: "1rem" }}>
      <h3 style={smallHeadingStyle}>{title}</h3>
      <ul style={listStyle}>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
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
const smallHeadingStyle = { margin: "0 0 0.5rem", fontSize: "1rem" } as const;
const scorePillStyle = {
  borderRadius: "999px",
  background: "#dcfce7",
  color: "#166534",
  padding: "0.35rem 0.65rem",
  fontSize: "0.875rem",
  fontWeight: 800,
  whiteSpace: "nowrap",
} as const;
const reviewNavStyle = {
  display: "flex",
  flexWrap: "wrap",
  gap: "0.75rem",
  marginTop: "1rem",
} as const;
const primaryLinkStyle = {
  borderRadius: "999px",
  background: "#15803d",
  color: "#fff",
  padding: "0.65rem 0.9rem",
  fontWeight: 800,
  textDecoration: "none",
} as const;
const secondaryLinkStyle = {
  borderRadius: "999px",
  border: "1px solid rgba(21, 128, 61, 0.35)",
  color: "#166534",
  padding: "0.65rem 0.9rem",
  fontWeight: 800,
  textDecoration: "none",
} as const;
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
