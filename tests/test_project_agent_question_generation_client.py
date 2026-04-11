from pathlib import Path

import pytest

from review_gate.project_agent_question_generation_client import (
    ProjectAgentQuestionGenerationClient,
    ProjectAgentRuntimeConfig,
)


def _build_test_client(*, transport) -> ProjectAgentQuestionGenerationClient:
    return ProjectAgentQuestionGenerationClient(
        runtime_config=ProjectAgentRuntimeConfig(
            provider="openai_compatible",
            base_url="https://example.test",
            api_key="test-key",
            model="gpt-5.4",
        ),
        transport=transport,
    )


def test_project_agent_client_reads_runtime_config_from_local_file(tmp_path: Path) -> None:
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    (env_dir / "api_key.md").write_text(
        "Base URL:https://example.test\nAPI Key:test-key\n",
        encoding="utf-8",
    )

    client = ProjectAgentQuestionGenerationClient.from_local_config(root_dir=tmp_path, model="gpt-5.4")

    assert client._runtime_config.provider == "openai_compatible"
    assert client._runtime_config.base_url == "https://example.test"
    assert client._runtime_config.api_key == "test-key"
    assert client._runtime_config.model == "gpt-5.4"


def test_project_agent_client_builds_openai_compatible_request_and_returns_raw_content() -> None:
    seen: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
        seen["url"] = url
        seen["headers"] = headers
        seen["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"questions":[{"id":"q-1","prompt":"Why did we split orchestration?","type":"open","intent":"Check migration reasoning.","difficulty":"intermediate"}]}'
                    }
                }
            ]
        }

    client = _build_test_client(transport=fake_transport)

    response = client.generate(
        {
            "request_id": "req-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "llm-generation",
            "stage_goal": "use a real llm-backed project agent",
            "stage_summary": "generation-side orchestration split is complete",
            "current_decisions": ["extract generation owners"],
            "key_logic_points": ["checkpoint continuity"],
            "known_weak_points": ["raw llm output normalization"],
            "boundary_focus": ["project vs interview mix"],
            "max_questions": 4,
        }
    )

    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["headers"] == {
        "Authorization": f"Bearer {client._runtime_config.api_key}",
        "Content-Type": "application/json",
    }
    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "gpt-5.4"
    assert response["request_id"] == "req-1"
    assert response["provider"] == "openai_compatible"
    assert response["model"] == "gpt-5.4"
    assert '"questions"' in response["raw_content"]


def test_project_agent_client_rejects_missing_message_content() -> None:
    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
        return {"choices": [{"message": {"content": ""}}]}

    client = _build_test_client(transport=fake_transport)

    with pytest.raises(ValueError, match="missing message content"):
        client.generate(
            {
                "request_id": "req-2",
                "project_id": "proj-1",
                "stage_id": "stage-1",
            }
        )
