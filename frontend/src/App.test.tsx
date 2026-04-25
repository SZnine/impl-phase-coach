import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

import { App } from "./App";
import { router } from "./routes";

let restoreFetch: typeof globalThis.fetch | undefined;

beforeEach(() => {
  restoreFetch = globalThis.fetch;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(
      () => new Promise(() => {
        // keep the default HomePage fetch pending so App shell tests stay synchronous
      }),
    ),
  );
});

afterEach(() => {
  if (restoreFetch) {
    vi.stubGlobal("fetch", restoreFetch);
  }
  vi.clearAllMocks();
});

test("renders workbench navigation", () => {
  render(<App />);

  expect(screen.getByText("Coach 工作台")).toBeInTheDocument();
  expect(screen.getByText("出题、答题、评析、知识沉淀")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "今日任务" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "错题本" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "知识沉淀" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "知识星图" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "改进建议" })).toBeInTheDocument();
});

test("registers the project -> stage -> question route hierarchy", () => {
  const rootRoute = router.routes[0];
  const childPaths = (rootRoute.children ?? []).map((route) => route.path ?? "[index]");

  expect(rootRoute.path).toBe("/");
  expect(childPaths).toContain("projects/:projectId");
  expect(childPaths).toContain("projects/:projectId/stages/:stageId");
  expect(childPaths).toContain("projects/:projectId/stages/:stageId/questions/:questionSetId");
  expect(childPaths).toContain("projects/:projectId/stages/:stageId/questions/:questionSetId/:questionId");
  expect(childPaths).toContain("knowledge");
  expect(childPaths).toContain("knowledge/graph");
});
