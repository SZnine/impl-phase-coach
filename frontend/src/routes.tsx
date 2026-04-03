import { createBrowserRouter, Navigate } from "react-router-dom";

import { WorkbenchLayout } from "./components/WorkbenchLayout";
import { HomePage } from "./pages/HomePage";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraphPage";
import { KnowledgeIndexPage } from "./pages/KnowledgeIndexPage";
import { MistakesPage } from "./pages/MistakesPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProposalsPage } from "./pages/ProposalsPage";
import { QuestionPage } from "./pages/QuestionPage";
import { QuestionSetPage } from "./pages/QuestionSetPage";
import { StagePage } from "./pages/StagePage";

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <WorkbenchLayout />,
      children: [
        { index: true, element: <HomePage /> },
        { path: "projects/:projectId", element: <ProjectPage /> },
        { path: "projects/:projectId/stages/:stageId", element: <StagePage /> },
        {
          path: "projects/:projectId/stages/:stageId/questions/:questionSetId",
          element: <QuestionSetPage />,
        },
        {
          path: "projects/:projectId/stages/:stageId/questions/:questionSetId/:questionId",
          element: <QuestionPage />,
        },
        { path: "mistakes", element: <MistakesPage /> },
        { path: "knowledge/index", element: <KnowledgeIndexPage /> },
        { path: "knowledge/graph", element: <KnowledgeGraphPage /> },
        { path: "proposals", element: <ProposalsPage /> },
        { path: "*", element: <Navigate to="/" replace /> },
      ],
    },
  ],
  {
    future: {
      v7_startTransition: true,
    },
  },
);