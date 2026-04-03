from __future__ import annotations

from typing import Any, Mapping

from jsonschema import Draft202012Validator


JSON_SCHEMAS: dict[str, dict[str, Any]] = {
    "analyze_output": {
        "type": "object",
        "required": ["opinion", "key_points", "concerns", "suggestions", "feasibility"],
        "properties": {
            "opinion": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
            "concerns": {"type": "array", "items": {"type": "string"}},
            "suggestions": {"type": "array", "items": {"type": "string"}},
            "feasibility": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "additionalProperties": False,
    },
    "consensus_check_output": {
        "type": "object",
        "required": [
            "consensus_reached",
            "consensus_points",
            "divergence_points",
            "evidence_comparison",
        ],
        "properties": {
            "consensus_reached": {"type": "boolean"},
            "consensus_points": {
                "type": "array",
                "items": {"type": ["string", "object"]},
            },
            "divergence_points": {
                "type": "array",
                "items": {"type": ["string", "object"]},
            },
            "evidence_comparison": {
                "type": "object",
                "required": [
                    "goal_aligned",
                    "constraints_aligned",
                    "implementation_path_aligned",
                ],
                "properties": {
                    "goal_aligned": {"type": "boolean"},
                    "constraints_aligned": {"type": "boolean"},
                    "implementation_path_aligned": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    },
    "route_choice": {
        "type": "object",
        "required": ["route_id", "task_class", "next_action"],
        "properties": {
            "route_id": {
                "type": "string",
                "enum": ["direct_execution", "consensus_1_round", "consensus_3_rounds"],
            },
            "task_class": {"type": "string", "enum": ["simple", "moderate", "complex"]},
            "next_action": {
                "type": "string",
                "enum": ["analyze", "execute", "fallback", "abstain", "need_human"],
            },
        },
        "additionalProperties": False,
    },
    "divergence_report": {
        "type": "object",
        "required": ["summary", "divergence_points", "recommended_action"],
        "properties": {
            "summary": {"type": "string"},
            "divergence_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "dimension",
                        "qwen_evidence",
                        "codex_evidence",
                        "impact",
                    ],
                    "properties": {
                        "dimension": {
                            "type": "string",
                            "enum": ["goal", "constraints", "implementation_path", "other"],
                        },
                        "qwen_evidence": {"type": "array", "items": {"type": "string"}},
                        "codex_evidence": {"type": "array", "items": {"type": "string"}},
                        "impact": {"type": "string"},
                        "resolution_hint": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
            "recommended_action": {
                "type": "string",
                "enum": ["continue_consensus", "escalate_to_human", "fallback_to_codex"],
            },
        },
        "additionalProperties": False,
    },
}


class UnknownSchemaError(KeyError):
    """Raised when a schema name is not registered."""


class SchemaValidationError(ValueError):
    """Raised when payload validation fails."""

    def __init__(self, schema_name: str, errors: list[dict[str, Any]]) -> None:
        self.schema_name = schema_name
        self.errors = errors
        super().__init__(
            f"Schema '{schema_name}' validation failed with {len(errors)} error(s)."
        )


class SchemaValidator:
    def __init__(self, schemas: Mapping[str, dict[str, Any]] | None = None) -> None:
        self.schemas = dict(JSON_SCHEMAS if schemas is None else schemas)
        self._validators = {
            schema_name: Draft202012Validator(schema)
            for schema_name, schema in self.schemas.items()
        }

    def validate(self, schema_name: str, data: Any) -> Any:
        errors = self.get_validation_errors(schema_name, data)
        if errors:
            raise SchemaValidationError(schema_name, errors)
        return data

    def get_validation_errors(self, schema_name: str, data: Any) -> list[dict[str, Any]]:
        validator = self._get_validator(schema_name)
        return [
            self._format_error(error)
            for error in sorted(validator.iter_errors(data), key=self._error_sort_key)
        ]

    def is_valid(self, schema_name: str, data: Any) -> bool:
        return not self.get_validation_errors(schema_name, data)

    def _get_validator(self, schema_name: str) -> Draft202012Validator:
        if schema_name not in self._validators:
            available = ", ".join(sorted(self._validators))
            raise UnknownSchemaError(
                f"Unknown schema '{schema_name}'. Available schemas: {available}"
            )
        return self._validators[schema_name]

    @staticmethod
    def _error_sort_key(error: Any) -> tuple[str, str, str]:
        return (
            SchemaValidator._format_path(error.absolute_path),
            error.validator or "",
            error.message,
        )

    @staticmethod
    def _format_error(error: Any) -> dict[str, Any]:
        return {
            "message": error.message,
            "validator": error.validator,
            "validator_value": error.validator_value,
            "data_path": SchemaValidator._format_path(error.absolute_path),
            "schema_path": SchemaValidator._format_path(error.absolute_schema_path),
        }

    @staticmethod
    def _format_path(path: Any) -> str:
        parts: list[str] = []
        for item in path:
            if isinstance(item, int):
                if parts:
                    parts[-1] = f"{parts[-1]}[{item}]"
                else:
                    parts.append(f"[{item}]")
            else:
                parts.append(str(item))
        return ".".join(parts)


DEFAULT_VALIDATOR = SchemaValidator()


def validate_output(schema_name: str, data: Any) -> Any:
    return DEFAULT_VALIDATOR.validate(schema_name, data)


def get_validation_errors(schema_name: str, data: Any) -> list[dict[str, Any]]:
    return DEFAULT_VALIDATOR.get_validation_errors(schema_name, data)


def is_valid_output(schema_name: str, data: Any) -> bool:
    return DEFAULT_VALIDATOR.is_valid(schema_name, data)
