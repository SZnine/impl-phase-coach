import { NavLink, Outlet } from "react-router-dom";

import { WorkspaceSessionSync } from "./WorkspaceSessionSync";

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  color: isActive ? "#0f172a" : "#475569",
  textDecoration: "none",
  fontWeight: isActive ? 700 : 500,
});

export function WorkbenchLayout() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)",
        color: "#0f172a",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <WorkspaceSessionSync />

      <header
        style={{
          borderBottom: "1px solid rgba(148, 163, 184, 0.3)",
          background: "rgba(255, 255, 255, 0.88)",
          backdropFilter: "blur(12px)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
            maxWidth: "1200px",
            margin: "0 auto",
            padding: "1rem 1.5rem",
          }}
        >
          <div>
            <div style={{ fontSize: "0.75rem", letterSpacing: "0.18em", textTransform: "uppercase", color: "#64748b" }}>
              Coach 工作台
            </div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>出题、答题、评析、知识沉淀</div>
          </div>
          <nav style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }} aria-label="Primary">
            <NavLink to="/" style={navLinkStyle} end>
              今日任务
            </NavLink>
            <NavLink to="/mistakes" style={navLinkStyle}>
              错题本
            </NavLink>
            <NavLink to="/knowledge" style={navLinkStyle}>
              知识沉淀
            </NavLink>
            <NavLink to="/knowledge/graph" style={navLinkStyle}>
              知识星图
            </NavLink>
            <NavLink to="/proposals" style={navLinkStyle}>
              改进建议
            </NavLink>
          </nav>
        </div>
      </header>

      <main
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          padding: "1.5rem",
        }}
      >
        <Outlet />
      </main>
    </div>
  );
}
