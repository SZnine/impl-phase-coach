import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useApiClient, type WorkspaceSessionDTO } from "../lib/api";

const DEFAULT_SESSION_ID = "local-workspace-session";

function emptySession(): WorkspaceSessionDTO {
  return {
    workspace_session_id: DEFAULT_SESSION_ID,
    active_project_id: null,
    active_stage_id: null,
    active_panel: "questions",
    active_question_set_id: null,
    active_question_id: null,
    active_profile_space_id: null,
    active_proposal_center_id: null,
    last_opened_at: "",
    filters: {},
  };
}

export function buildPathFromWorkspaceSession(session: WorkspaceSessionDTO): string | null {
  if (session.active_panel === "mistakes") {
    return "/mistakes";
  }
  if (session.active_panel === "knowledge_index") {
    return "/knowledge/index";
  }
  if (session.active_panel === "knowledge_graph") {
    return "/knowledge/graph";
  }
  if (session.active_panel === "proposals") {
    return "/proposals";
  }
  if (
    session.active_project_id &&
    session.active_stage_id &&
    session.active_question_set_id &&
    session.active_question_id
  ) {
    return `/projects/${session.active_project_id}/stages/${session.active_stage_id}/questions/${session.active_question_set_id}/${session.active_question_id}`;
  }
  if (session.active_project_id && session.active_stage_id && session.active_question_set_id) {
    return `/projects/${session.active_project_id}/stages/${session.active_stage_id}/questions/${session.active_question_set_id}`;
  }
  if (session.active_project_id && session.active_stage_id) {
    return `/projects/${session.active_project_id}/stages/${session.active_stage_id}`;
  }
  if (session.active_project_id) {
    return `/projects/${session.active_project_id}`;
  }
  return null;
}

export function buildWorkspaceSessionForPath(pathname: string): WorkspaceSessionDTO {
  const base = emptySession();
  const normalizedPath = pathname === "" ? "/" : pathname.replace(/\/+$/, "") || "/";

  if (normalizedPath === "/") {
    return {
      ...base,
      active_panel: "projects",
    };
  }
  if (normalizedPath === "/mistakes") {
    return {
      ...base,
      active_panel: "mistakes",
    };
  }
  if (normalizedPath === "/knowledge/index") {
    return {
      ...base,
      active_panel: "knowledge_index",
    };
  }
  if (normalizedPath === "/knowledge/graph") {
    return {
      ...base,
      active_panel: "knowledge_graph",
    };
  }
  if (normalizedPath === "/proposals") {
    return {
      ...base,
      active_panel: "proposals",
    };
  }

  const questionMatch = normalizedPath.match(/^\/projects\/([^/]+)\/stages\/([^/]+)\/questions\/([^/]+)\/([^/]+)$/);
  if (questionMatch) {
    return {
      ...base,
      active_project_id: questionMatch[1],
      active_stage_id: questionMatch[2],
      active_question_set_id: questionMatch[3],
      active_question_id: questionMatch[4],
      active_panel: "questions",
    };
  }

  const questionSetMatch = normalizedPath.match(/^\/projects\/([^/]+)\/stages\/([^/]+)\/questions\/([^/]+)$/);
  if (questionSetMatch) {
    return {
      ...base,
      active_project_id: questionSetMatch[1],
      active_stage_id: questionSetMatch[2],
      active_question_set_id: questionSetMatch[3],
      active_panel: "questions",
    };
  }

  const stageMatch = normalizedPath.match(/^\/projects\/([^/]+)\/stages\/([^/]+)$/);
  if (stageMatch) {
    return {
      ...base,
      active_project_id: stageMatch[1],
      active_stage_id: stageMatch[2],
      active_panel: "questions",
    };
  }

  const projectMatch = normalizedPath.match(/^\/projects\/([^/]+)$/);
  if (projectMatch) {
    return {
      ...base,
      active_project_id: projectMatch[1],
      active_panel: "projects",
    };
  }

  return base;
}

export function WorkspaceSessionSync() {
  const client = useApiClient();
  const location = useLocation();
  const navigate = useNavigate();
  const [restoreReady, setRestoreReady] = useState(false);
  const [pendingRestorePath, setPendingRestorePath] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    client
      .getWorkspaceSession()
      .then((session) => {
        if (!active) {
          return;
        }
        const restorePath = buildPathFromWorkspaceSession(session);
        if (location.pathname === "/" && restorePath && restorePath !== "/") {
          setPendingRestorePath(restorePath);
          navigate(restorePath, { replace: true });
          return;
        }
        setRestoreReady(true);
      })
      .catch(() => {
        if (active) {
          setRestoreReady(true);
        }
      });

    return () => {
      active = false;
    };
  }, [client, navigate]);

  useEffect(() => {
    if (pendingRestorePath && location.pathname === pendingRestorePath) {
      setPendingRestorePath(null);
      setRestoreReady(true);
    }
  }, [location.pathname, pendingRestorePath]);

  useEffect(() => {
    if (!restoreReady) {
      return;
    }
    const nextSession = {
      ...buildWorkspaceSessionForPath(location.pathname),
      last_opened_at: new Date().toISOString(),
    };
    void client.saveWorkspaceSession(nextSession).catch(() => undefined);
  }, [client, location.pathname, restoreReady]);

  return null;
}
