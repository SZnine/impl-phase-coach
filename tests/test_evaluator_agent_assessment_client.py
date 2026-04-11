from pathlib import Path

from review_gate.evaluator_agent_assessment_client import (
    EvaluatorAgentAssessmentClient,
    EvaluatorAgentRuntimeConfig,
)


def _build_test_client(*, transport) -> EvaluatorAgentAssessmentClient:
    return EvaluatorAgentAssessmentClient(
        runtime_config=EvaluatorAgentRuntimeConfig(
            provider="openai_compatible",
            base_url="https://example.test",
            api_key="test-key",
            model="gpt-5.4",
        ),
        transport=transport,
    )


def test_evaluator_agent_client_reads_runtime_config_from_env_api_key_file(
    tmp_path: Path,
) -> None:
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    (env_dir / "api_key.md").write_text(
        "Base URL:https://example.test\nAPI Key:test-key\n",
        encoding="utf-8",
    )

    client = EvaluatorAgentAssessmentClient.from_local_config(root_dir=tmp_path, model="gpt-5.4")

    assert client._runtime_config.provider == "openai_compatible"
    assert client._runtime_config.base_url == "https://example.test"
    assert client._runtime_config.api_key == "test-key"
    assert client._runtime_config.model == "gpt-5.4"


def test_evaluator_agent_client_reads_runtime_config_from_key_api_key_file(
    tmp_path: Path,
) -> None:
    key_dir = tmp_path / "key"
    key_dir.mkdir()
    (key_dir / "api_key.md").write_text(
        "Base URL:https://example.test\nAPI Key:test-key\n",
        encoding="utf-8",
    )

    client = EvaluatorAgentAssessmentClient.from_local_config(root_dir=tmp_path, model="gpt-5.4")

    assert client._runtime_config.provider == "openai_compatible"
    assert client._runtime_config.base_url == "https://example.test"
    assert client._runtime_config.api_key == "test-key"
    assert client._runtime_config.model == "gpt-5.4"


def test_evaluator_agent_client_builds_openai_compatible_request_and_returns_raw_content() -> None:
    seen: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
        seen["url"] = url
        seen["headers"] = headers
        seen["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"assessment":{"verdict":"partial","score_total":0.72}}'
                    }
                }
            ]
        }

    client = _build_test_client(transport=fake_transport)

    response = client.assess(
        {
            "request_id": "req-1",
            "messages": [
                {"role": "system", "content": "You are the Evaluator Agent."},
                {"role": "user", "content": "Assess the answer."},
            ],
            "response_format": {"type": "json_object"},
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
    assert payload["stream"] is True
    assert response["request_id"] == "req-1"
    assert response["provider"] == "openai_compatible"
    assert response["model"] == "gpt-5.4"
    assert response["raw_content"] == '{"assessment":{"verdict":"partial","score_total":0.72}}'
    assert response["raw_response"]["choices"][0]["message"]["content"] == response["raw_content"]
