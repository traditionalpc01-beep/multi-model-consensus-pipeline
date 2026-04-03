from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from schema_validator import validate_output


DIMENSION_FIELDS: dict[str, tuple[str, ...]] = {
    "goal": ("key_points",),
    "constraints": ("concerns", "feasibility"),
    "implementation_path": ("suggestions",),
}


def consensus_check(
    qwen_result: Mapping[str, Any],
    codex_result: Mapping[str, Any],
) -> dict[str, Any]:
    qwen_analysis = validate_output("analyze_output", dict(qwen_result))
    codex_analysis = validate_output("analyze_output", dict(codex_result))

    comparisons = {
        "goal": _compare_dimension("goal", qwen_analysis, codex_analysis),
        "constraints": _compare_dimension("constraints", qwen_analysis, codex_analysis),
        "implementation_path": _compare_dimension(
            "implementation_path",
            qwen_analysis,
            codex_analysis,
        ),
    }

    result = {
        "consensus_reached": all(item["aligned"] for item in comparisons.values()),
        "consensus_points": [
            {
                "dimension": dimension,
                "shared_evidence": item["shared_evidence"],
            }
            for dimension, item in comparisons.items()
            if item["aligned"]
        ],
        "divergence_points": [
            {
                "dimension": dimension,
                "qwen_evidence": item["qwen_evidence"],
                "codex_evidence": item["codex_evidence"],
                "shared_evidence": item["shared_evidence"],
            }
            for dimension, item in comparisons.items()
            if not item["aligned"]
        ],
        "evidence_comparison": {
            "goal_aligned": comparisons["goal"]["aligned"],
            "constraints_aligned": comparisons["constraints"]["aligned"],
            "implementation_path_aligned": comparisons["implementation_path"]["aligned"],
        },
    }
    return validate_output("consensus_check_output", result)


def _compare_dimension(
    dimension: str,
    qwen_analysis: Mapping[str, Any],
    codex_analysis: Mapping[str, Any],
) -> dict[str, Any]:
    qwen_evidence = _collect_evidence(qwen_analysis, DIMENSION_FIELDS[dimension])
    codex_evidence = _collect_evidence(codex_analysis, DIMENSION_FIELDS[dimension])

    qwen_normalized = {normalized: original for normalized, original in qwen_evidence}
    codex_normalized = {normalized: original for normalized, original in codex_evidence}

    qwen_keys = set(qwen_normalized)
    codex_keys = set(codex_normalized)
    shared_keys = qwen_keys & codex_keys

    return {
        "aligned": qwen_keys == codex_keys,
        "shared_evidence": [
            original for normalized, original in qwen_evidence if normalized in shared_keys
        ],
        "qwen_evidence": [original for _, original in qwen_evidence],
        "codex_evidence": [original for _, original in codex_evidence],
    }


def _collect_evidence(
    analysis: Mapping[str, Any],
    fields: Iterable[str],
) -> list[tuple[str, str]]:
    evidence: list[tuple[str, str]] = []
    seen: set[str] = set()

    for field in fields:
        if field == "feasibility":
            original = f"feasibility:{analysis[field]}"
            normalized = _normalize_text(original)
            if normalized not in seen:
                evidence.append((normalized, original))
                seen.add(normalized)
            continue

        for value in analysis.get(field, []):
            original = str(value).strip()
            normalized = _normalize_text(original)
            if normalized and normalized not in seen:
                evidence.append((normalized, original))
                seen.add(normalized)

    return evidence


def _normalize_text(text: str) -> str:
    lowered = text.casefold()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", lowered)
    return " ".join(normalized.split())
