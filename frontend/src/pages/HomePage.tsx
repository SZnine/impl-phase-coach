import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useApiClient, type HomeViewDTO } from "../lib/api";

type HomeLoadState =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: HomeViewDTO; error: null };

export function HomePage() {
  const client = useApiClient();
  const [state, setState] = useState<HomeLoadState>({ status: "loading", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

    client
      .getHomeView()
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
            error: error instanceof Error ? error.message : "Unable to load home view.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [client]);

  const activeProject =
    state.status === "ready"
      ? state.data.projects.find((project) => project.project_id === state.data.active_project_id) ??
        state.data.projects[0] ??
        null
      : null;

  return (
    <section style={{ display: "grid", gap: "1rem" }}>
      <div>
        <h1 style={{ margin: 0, fontSize: "2rem" }}>今日任务</h1>
        <p style={{ margin: "0.5rem 0 0", color: "#475569" }}>
          先完成一组题目，再看评析，把薄弱点沉淀进知识库。
        </p>
      </div>

      {state.status === "loading" ? (
        <div style={panelStyle} role="status" aria-live="polite">
          Loading home view...
        </div>
      ) : state.status === "error" ? (
        <div style={panelStyle} role="alert">
          <p style={{ margin: 0, fontWeight: 700 }}>Failed to load home view.</p>
          <p style={{ margin: "0.5rem 0 0", color: "#b91c1c" }}>{state.error}</p>
        </div>
      ) : (
        <>
          {activeProject ? (
            <article style={heroStyle}>
              <div>
                <p style={eyebrowStyle}>当前项目</p>
                <h2 style={{ margin: "0.25rem 0 0", fontSize: "1.6rem" }}>{activeProject.project_label}</h2>
                <p style={{ margin: "0.75rem 0 0", color: "#475569", lineHeight: 1.7 }}>
                  {activeProject.project_summary}
                </p>
              </div>
              <div style={heroActionStyle}>
                <h3 style={sectionHeadingStyle}>题目训练</h3>
                <p style={{ margin: "0 0 0.75rem", color: "#475569" }}>
                  当前阶段：{activeProject.active_stage_label}
                </p>
                <Link
                  to={`/projects/${activeProject.project_id}/stages/${activeProject.active_stage_id}`}
                  style={primaryLinkStyle}
                >
                  进入今日训练
                </Link>
              </div>
            </article>
          ) : (
            <article style={panelStyle}>
              <h2 style={sectionHeadingStyle}>暂无当前任务</h2>
              <p style={{ margin: 0, color: "#475569" }}>还没有可训练的项目。</p>
            </article>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "1rem",
            }}
          >
            <article style={cardStyle}>
              <h2 style={cardHeadingStyle}>知识沉淀</h2>
              <p style={cardTextStyle}>答题后的评析会转成知识点、误区和后续复习线索。</p>
              <dl style={definitionListStyle}>
                <div>
                  <dt style={termStyle}>知识点</dt>
                  <dd style={definitionStyle}>{activeProject?.knowledge_entry_count ?? 0}</dd>
                </div>
                <div>
                  <dt style={termStyle}>待处理建议</dt>
                  <dd style={definitionStyle}>{state.data.pending_proposal_count}</dd>
                </div>
              </dl>
              <p style={{ margin: "0.75rem 0 0" }}>
                <Link to="/knowledge">查看知识沉淀</Link>
              </p>
            </article>

            <article style={cardStyle}>
              <h2 style={cardHeadingStyle}>错题本</h2>
              <p style={cardTextStyle}>集中回看回答里的误区和根因，避免下一轮题目重复踩坑。</p>
              <dl style={definitionListStyle}>
                <div>
                  <dt style={termStyle}>错题/误区</dt>
                  <dd style={definitionStyle}>{activeProject?.mistake_count ?? 0}</dd>
                </div>
                <div>
                  <dt style={termStyle}>项目数</dt>
                  <dd style={definitionStyle}>{state.data.total_count}</dd>
                </div>
              </dl>
              <p style={{ margin: "0.75rem 0 0" }}>
                <Link to="/mistakes">查看错题本</Link>
              </p>
            </article>

            {state.data.projects.map((project) => (
              <article key={project.project_id} style={cardStyle}>
                <h2 style={cardHeadingStyle}>项目复盘：{project.project_label}</h2>
                <p style={cardTextStyle}>{project.project_summary}</p>
                <dl style={definitionListStyle}>
                  <div>
                    <dt style={termStyle}>当前阶段</dt>
                    <dd style={definitionStyle}>{project.active_stage_label}</dd>
                  </div>
                  <div>
                    <dt style={termStyle}>知识点</dt>
                    <dd style={definitionStyle}>{project.knowledge_entry_count}</dd>
                  </div>
                  <div>
                    <dt style={termStyle}>误区</dt>
                    <dd style={definitionStyle}>{project.mistake_count}</dd>
                  </div>
                  <div>
                    <dt style={termStyle}>待处理建议</dt>
                    <dd style={definitionStyle}>{project.pending_proposal_count}</dd>
                  </div>
                </dl>
                <p style={{ margin: "0.75rem 0 0" }}>
                  <Link to={`/projects/${project.project_id}`}>打开项目复盘</Link>
                </p>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

const panelStyle = {
  border: "1px solid rgba(148, 163, 184, 0.35)",
  borderRadius: "1rem",
  background: "rgba(255, 255, 255, 0.92)",
  padding: "1rem",
  boxShadow: "0 12px 32px rgba(15, 23, 42, 0.06)",
} as const;

const cardStyle = panelStyle;
const cardHeadingStyle = { margin: "0 0 0.5rem" } as const;
const cardTextStyle = { margin: "0 0 0.75rem", color: "#475569" } as const;
const sectionHeadingStyle = { margin: "0 0 0.75rem" } as const;
const definitionListStyle = { display: "grid", gap: "0.75rem", margin: 0 } as const;
const termStyle = { fontSize: "0.875rem", color: "#64748b", fontWeight: 700 } as const;
const definitionStyle = { margin: "0.25rem 0 0" } as const;
const heroStyle = {
  ...panelStyle,
  display: "grid",
  gridTemplateColumns: "minmax(0, 1.7fr) minmax(260px, 0.8fr)",
  gap: "1rem",
  alignItems: "center",
} as const;
const heroActionStyle = {
  border: "1px solid rgba(21, 128, 61, 0.25)",
  borderRadius: "0.85rem",
  background: "#f0fdf4",
  padding: "1rem",
} as const;
const eyebrowStyle = {
  margin: 0,
  color: "#15803d",
  fontSize: "0.85rem",
  fontWeight: 800,
} as const;
const primaryLinkStyle = {
  display: "inline-flex",
  borderRadius: "999px",
  background: "#15803d",
  color: "#fff",
  padding: "0.7rem 1rem",
  fontWeight: 800,
  textDecoration: "none",
} as const;
