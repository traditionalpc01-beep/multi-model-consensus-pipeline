import unittest

from schema_validator import (
    JSON_SCHEMAS,
    SchemaValidationError,
    SchemaValidator,
    UnknownSchemaError,
)


class SchemaValidatorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = SchemaValidator()

    def test_validate_accepts_valid_analyze_output(self) -> None:
        payload = {
            "opinion": "Proceed with a single consensus round.",
            "key_points": ["The task is bounded."],
            "concerns": ["Need schema enforcement."],
            "suggestions": ["Validate every model output."],
            "feasibility": "high",
        }

        validated = self.validator.validate("analyze_output", payload)

        self.assertEqual(validated, payload)

    def test_validate_raises_structured_error_details_for_invalid_payload(self) -> None:
        payload = {
            "opinion": "Proceed",
            "key_points": [],
            "concerns": [],
            "suggestions": [],
            "feasibility": "unknown",
        }

        with self.assertRaises(SchemaValidationError) as ctx:
            self.validator.validate("analyze_output", payload)

        error = ctx.exception
        self.assertEqual(error.schema_name, "analyze_output")
        self.assertEqual(error.errors[0]["data_path"], "feasibility")
        self.assertIn("is not one of", error.errors[0]["message"])

    def test_get_validation_errors_returns_all_detected_issues(self) -> None:
        payload = {
            "route_id": "invalid_route",
            "task_class": "simple",
        }

        errors = self.validator.get_validation_errors("route_choice", payload)

        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]["data_path"], "")
        self.assertIn("'next_action' is a required property", errors[0]["message"])
        self.assertEqual(errors[1]["data_path"], "route_id")

    def test_is_valid_reports_boolean_status(self) -> None:
        valid_payload = {
            "summary": "Models disagree on constraints handling.",
            "divergence_points": [
                {
                    "dimension": "constraints",
                    "qwen_evidence": ["Avoid network access."],
                    "codex_evidence": ["Need to install packages."],
                    "impact": "Conflicting delivery assumptions.",
                }
            ],
            "recommended_action": "escalate_to_human",
        }

        invalid_payload = {
            "summary": "Missing action.",
            "divergence_points": [],
        }

        self.assertTrue(self.validator.is_valid("divergence_report", valid_payload))
        self.assertFalse(self.validator.is_valid("divergence_report", invalid_payload))

    def test_unknown_schema_name_raises_specific_error(self) -> None:
        with self.assertRaises(UnknownSchemaError):
            self.validator.validate("missing_schema", {})


class JsonSchemasDefinitionTestCase(unittest.TestCase):
    def test_required_phase_one_schemas_are_registered(self) -> None:
        expected_names = {
            "analyze_output",
            "consensus_check_output",
            "route_choice",
            "divergence_report",
        }

        self.assertTrue(expected_names.issubset(JSON_SCHEMAS))


if __name__ == "__main__":
    unittest.main()
