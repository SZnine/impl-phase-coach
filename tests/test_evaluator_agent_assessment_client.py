from pathlib import Path

import requests

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
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["stream"] is True
    assert response["request_id"] == "req-1"
    assert response["provider"] == "openai_compatible"
    assert response["model"] == "gpt-5.4"
    assert response["raw_content"] == '{"assessment":{"verdict":"partial","score_total":0.72}}'
    assert response["raw_response"]["choices"][0]["message"]["content"] == response["raw_content"]


def test_evaluator_agent_client_defaults_response_format_to_json_object_when_absent() -> None:
    seen: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
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

    client.assess(
        {
            "request_id": "req-2",
            "messages": [
                {"role": "system", "content": "You are the Evaluator Agent."},
                {"role": "user", "content": "Assess the answer."},
            ],
        }
    )

    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["response_format"] == {"type": "json_object"}


def test_evaluator_agent_client_defaults_response_format_to_json_object_when_none() -> None:
    seen: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
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

    client.assess(
        {
            "request_id": "req-3",
            "messages": [
                {"role": "system", "content": "You are the Evaluator Agent."},
                {"role": "user", "content": "Assess the answer."},
            ],
            "response_format": None,
        }
    )

    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["response_format"] == {"type": "json_object"}


def test_evaluator_agent_client_preserves_explicit_response_format_override() -> None:
    seen: dict[str, object] = {}
    override = {"type": "json_schema", "json_schema": {"name": "assessment"}}

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
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

    client.assess(
        {
            "request_id": "req-4",
            "messages": [
                {"role": "system", "content": "You are the Evaluator Agent."},
                {"role": "user", "content": "Assess the answer."},
            ],
            "response_format": override,
        }
    )

    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["response_format"] == override


def test_evaluator_agent_client_extracts_list_text_content_fragments() -> None:
    raw_content = EvaluatorAgentAssessmentClient._extract_message_content(
        {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": '{"assessment":'},
                            {"type": "tool_call", "text": "ignored"},
                            {"type": "text", "text": '{"verdict":"partial"}}'},
                        ]
                    }
                }
            ]
        }
    )

    assert raw_content == '{"assessment":{"verdict":"partial"}}'


def test_evaluator_agent_client_default_transport_assembles_streamed_content(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def iter_lines(self):
            return iter(
                [
                    b'data: {"choices":[{"delta":{"content":"{\\"assessment\\":"}}]}',
                    b'data: {"choices":[{"delta":{"content":"{\\"verdict\\":\\"partial\\"}"}}]}',
                    b'data: {"choices":[{"delta":{"content":"}"}}]}',
                    b"data: [DONE]",
                ]
            )

        def json(self) -> dict[str, object]:
            raise AssertionError("json() should not be called for streamed responses")

    captured: dict[str, object] = {}

    def fake_post(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)

    response = EvaluatorAgentAssessmentClient._default_transport(
        "https://example.test/v1/chat/completions",
        {"Authorization": "Bearer test-key", "Content-Type": "application/json"},
        {
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "Assess the answer."}],
            "response_format": {"type": "json_object"},
            "stream": True,
        },
    )

    assert captured["args"] == ("https://example.test/v1/chat/completions",)
    assert captured["kwargs"]["stream"] is True
    assert response == {
        "choices": [
            {
                "message": {
                    "content": '{"assessment":{"verdict":"partial"}}'
                }
            }
        ]
    }
