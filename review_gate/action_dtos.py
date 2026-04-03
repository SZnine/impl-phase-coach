from __future__ import annotations

import json
import types
from dataclasses import dataclass, field, fields
from typing import Any, get_args, get_origin, get_type_hints


class TransportModel:
    def model_dump(self) -> dict[str, Any]:
        return {field.name: _dump_value(getattr(self, field.name)) for field in fields(self)}

    def model_dump_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.model_dump(), ensure_ascii=False, indent=indent)

    @classmethod
    def model_validate(cls, data: Any) -> "TransportModel":
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__} requires a mapping for validation")

        hints = get_type_hints(cls)
        values: dict[str, Any] = {}
        for field in fields(cls):
            if field.name in data:
                values[field.name] = _coerce_value(hints.get(field.name, Any), data[field.name])
        return cls(**values)

    @classmethod
    def model_validate_json(cls, data: str) -> "TransportModel":
        return cls.model_validate(json.loads(data))


def _dump_value(value: Any) -> Any:
    if isinstance(value, TransportModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_dump_value(item) for item in value]
    if isinstance(value, tuple):
        return [_dump_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump_value(item) for key, item in value.items()}
    return value


def _coerce_value(annotation: Any, value: Any) -> Any:
    if value is None:
        return None

    origin = get_origin(annotation)
    if origin in (types.UnionType, getattr(types, "UnionType", None)):
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            try:
                return _coerce_value(arg, value)
            except (TypeError, ValueError):
                continue
        return value

    if origin is list:
        item_type = get_args(annotation)[0] if get_args(annotation) else Any
        return [_coerce_value(item_type, item) for item in value]

    if isinstance(annotation, type) and issubclass(annotation, TransportModel):
        return annotation.model_validate(value)

    return value


@dataclass(slots=True)
class ActionRequestBase(TransportModel):
    request_id: str
    project_id: str
    stage_id: str
    source_page: str
    actor_id: str
    created_at: str


@dataclass(slots=True)
class SubmitAnswerRequest(ActionRequestBase):
    question_set_id: str
    question_id: str
    answer_text: str
    draft_id: str | None = None


@dataclass(slots=True)
class ProposalActionRequest(TransportModel):
    request_id: str
    source_page: str
    actor_id: str
    created_at: str
    proposal_id: str
    action_type: str
    selected_target_ids: list[str] = field(default_factory=list)