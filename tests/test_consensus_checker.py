import unittest

from schema_validator import SchemaValidationError, is_valid_output

from consensus_checker import consensus_check


def make_analysis(
    *,
    opinion: str = "Proceed with the orchestrated flow.",
    key_points: list[str] | None = None,
    concerns: list[str] | None = None,
    suggestions: list[str] | None = None,
    feasibility: str = "high",
) -> dict[str, object]:
    return {
        "opinion": opinion,
        "key_points": key_points or ["Server owns routing decisions."],
        "concerns": concerns or ["Need strict schema validation."],
        "suggestions": suggestions or ["Add a state store module."],
        "feasibility": feasibility,
    }


class ConsensusCheckerTestCase(unittest.TestCase):
    def test_consensus_check_reports_full_alignment_for_matching_evidence(self) -> None:
        qwen_result = make_analysis(
            key_points=["Server owns routing decisions.", "Consensus stays deterministic."],
            concerns=["Need strict schema validation."],
            suggestions=["Add a state store module.", "Keep audit history."],
        )
        codex_result = make_analysis(
            opinion="proceed with the orchestrated flow.",
            key_points=["Consensus stays deterministic!", "Server owns routing decisions."],
            concerns=["Need strict schema validation"],
            suggestions=["Keep audit history", "Add a state store module"],
        )

        result = consensus_check(qwen_result, codex_result)

        self.assertTrue(result["consensus_reached"])
        self.assertEqual(
            result["evidence_comparison"],
            {
                "goal_aligned": True,
                "constraints_aligned": True,
                "implementation_path_aligned": True,
            },
        )
        self.assertEqual(
            {point["dimension"] for point in result["consensus_points"]},
            {"goal", "constraints", "implementation_path"},
        )
        self.assertEqual(result["divergence_points"], [])
        self.assertTrue(is_valid_output("consensus_check_output", result))

    def test_consensus_check_surfaces_dimension_level_divergence(self) -> None:
        qwen_result = make_analysis(
            concerns=["Need strict schema validation."],
            suggestions=["Add a state store module."],
            feasibility="high",
        )
        codex_result = make_analysis(
            concerns=["Need offline execution support."],
            suggestions=["Refactor the router first."],
            feasibility="medium",
        )

        result = consensus_check(qwen_result, codex_result)
        divergence_by_dimension = {
            point["dimension"]: point for point in result["divergence_points"]
        }

        self.assertFalse(result["consensus_reached"])
        self.assertEqual(
            result["evidence_comparison"],
            {
                "goal_aligned": True,
                "constraints_aligned": False,
                "implementation_path_aligned": False,
            },
        )
        self.assertEqual(set(divergence_by_dimension), {"constraints", "implementation_path"})
        self.assertEqual(
            divergence_by_dimension["constraints"]["qwen_evidence"],
            ["Need strict schema validation.", "feasibility:high"],
        )
        self.assertEqual(
            divergence_by_dimension["constraints"]["codex_evidence"],
            ["Need offline execution support.", "feasibility:medium"],
        )

    def test_consensus_check_normalizes_case_whitespace_and_punctuation(self) -> None:
        qwen_result = make_analysis(
            key_points=["Server owns routing decisions."],
            concerns=["Need strict schema validation."],
            suggestions=["Add a state store module."],
        )
        codex_result = make_analysis(
            key_points=["  server owns routing decisions  "],
            concerns=["Need strict schema validation"],
            suggestions=["Add a state store module!"],
        )

        result = consensus_check(qwen_result, codex_result)

        self.assertTrue(result["consensus_reached"])
        self.assertEqual(result["divergence_points"], [])

    def test_consensus_check_rejects_invalid_analyze_payloads(self) -> None:
        invalid_result = {
            "opinion": "Proceed",
            "key_points": [],
            "concerns": [],
            "suggestions": [],
            "feasibility": "unknown",
        }

        with self.assertRaises(SchemaValidationError):
            consensus_check(invalid_result, make_analysis())


if __name__ == "__main__":
    unittest.main()
