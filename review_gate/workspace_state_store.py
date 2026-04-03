from __future__ import annotations

from pathlib import Path

from review_gate.domain import WorkspaceSession


class JsonWorkspaceStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, session: WorkspaceSession) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(session.to_json(), encoding="utf-8")
        tmp_path.replace(self._path)

    def load(self) -> WorkspaceSession | None:
        if not self._path.exists():
            return None
        return WorkspaceSession.from_json(self._path.read_text(encoding="utf-8"))
