from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib import request as urllib_request

from review_gate.project_agent_prompt_builder import ProjectAgentPromptBuilder


@dataclass(slots=True)
class ProjectAgentRuntimeConfig:
    provider: str
    base_url: str
    api_key: str
    model: str


class ProjectAgentQuestionGenerationClient:
    def __init__(
        self,
        *,
        runtime_config: ProjectAgentRuntimeConfig,
        prompt_builder: ProjectAgentPromptBuilder | None = None,
        transport: Callable[[str, Mapping[str, str], dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self._runtime_config = runtime_config
        self._prompt_builder = prompt_builder or ProjectAgentPromptBuilder()
        self._transport = transport or self._default_transport

    @classmethod
    def from_local_config(
        cls,
        *,
        root_dir: Path | None = None,
        model: str = "gpt-5.4",
        provider: str = "openai_compatible",
    ) -> "ProjectAgentQuestionGenerationClient":
        config_path = cls._resolve_config_path(root_dir=root_dir)
        runtime_config = cls._load_runtime_config(config_path=config_path, model=model, provider=provider)
        return cls(runtime_config=runtime_config)

    def generate(self, request: Mapping[str, Any]) -> dict[str, Any]:
        prompt_package = self._prompt_builder.build(request)
        payload = {
            "model": self._runtime_config.model,
            "messages": [
                {"role": "system", "content": prompt_package.system_prompt},
                {"role": "user", "content": prompt_package.user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._runtime_config.api_key}",
            "Content-Type": "application/json",
        }
        raw_response = self._transport(self._build_chat_completions_url(), headers, payload)
        raw_content = self._extract_message_content(raw_response)
        return {
            "request_id": str(request["request_id"]),
            "provider": self._runtime_config.provider,
            "model": self._runtime_config.model,
            "raw_content": raw_content,
            "raw_response": raw_response,
            "output_contract": prompt_package.output_contract,
        }

    def _build_chat_completions_url(self) -> str:
        base_url = self._runtime_config.base_url.rstrip("/")
        if base_url.endswith("/v1"):
            return f"{base_url}/chat/completions"
        return f"{base_url}/v1/chat/completions"

    @staticmethod
    def _resolve_config_path(*, root_dir: Path | None) -> Path:
        env_path = os.environ.get("REVIEW_WORKBENCH_PROJECT_AGENT_CONFIG_PATH", "").strip()
        if env_path:
            candidate = Path(env_path)
            if candidate.exists():
                return candidate
            raise FileNotFoundError(f"Configured project agent config path does not exist: {candidate}")

        search_root = Path(root_dir) if root_dir is not None else Path(__file__).resolve().parents[1]
        candidates = [
            search_root / ".env" / "api_key.md",
            search_root / "key" / "api_key.md",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError("No api_key.md found in .env/ or key/")

    @staticmethod
    def _load_runtime_config(
        *,
        config_path: Path,
        model: str,
        provider: str,
    ) -> ProjectAgentRuntimeConfig:
        base_url = ""
        api_key = ""
        for raw_line in config_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if line.lower().startswith("base url:"):
                base_url = line.split(":", 1)[1].strip()
            elif line.lower().startswith("api key:"):
                api_key = line.split(":", 1)[1].strip()
        if not base_url or not api_key:
            raise ValueError(f"Missing base_url/api_key in {config_path}")
        return ProjectAgentRuntimeConfig(
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )

    @staticmethod
    def _extract_message_content(response: Mapping[str, Any]) -> str:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("LLM response missing choices")
        message = choices[0].get("message")
        if not isinstance(message, Mapping):
            raise ValueError("LLM response missing message")
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text_chunks: list[str] = []
            for item in content:
                if not isinstance(item, Mapping):
                    continue
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    text_chunks.append(item["text"])
            merged = "".join(text_chunks).strip()
            if merged:
                return merged
        raise ValueError("LLM response missing message content")

    @staticmethod
    def _default_transport(url: str, headers: Mapping[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(url=url, data=encoded, headers=dict(headers), method="POST")
        with urllib_request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)
