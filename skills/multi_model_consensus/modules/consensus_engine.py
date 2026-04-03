
from __future__ import annotations

import re


DIMENSION_FIELDS = {
    "goal": ("key_points",),
    "constraints": ("concerns", "feasibility"),
    "implementation_path": ("suggestions",),
}


class ConsensusEngine:
    def __init__(self):
        self.dimension_fields = DIMENSION_FIELDS
    
    def check(self, qwen_result, codex_result):
        comparisons = {
            "goal": self._compare_dimension("goal", qwen_result, codex_result),
            "constraints": self._compare_dimension("constraints", qwen_result, codex_result),
            "implementation_path": self._compare_dimension(
                "implementation_path",
                qwen_result,
                codex_result,
            ),
        }
        
        return {
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
        }
    
    def _compare_dimension(
        self,
        dimension,
        qwen_analysis,
        codex_analysis,
    ):
        qwen_evidence = self._collect_evidence(qwen_analysis, self.dimension_fields[dimension])
        codex_evidence = self._collect_evidence(codex_analysis, self.dimension_fields[dimension])
        
        qwen_normalized = {normalized: original for normalized, original in qwen_evidence}
        codex_normalized = {normalized: original for normalized, original in codex_evidence}
        
        qwen_keys = set(qwen_normalized)
        codex_keys = set(codex_normalized)
        shared_keys = qwen_keys &amp; codex_keys
        
        return {
            "aligned": qwen_keys == codex_keys,
            "shared_evidence": [
                original for normalized, original in qwen_evidence if normalized in shared_keys
            ],
            "qwen_evidence": [original for _, original in qwen_evidence],
            "codex_evidence": [original for _, original in codex_evidence],
        }
    
    def _collect_evidence(
        self,
        analysis,
        fields,
    ):
        evidence = []
        seen = set()
        
        for field in fields:
            if field == "feasibility":
                original = f"feasibility:{analysis[field]}"
                normalized = self._normalize_text(original)
                if normalized not in seen:
                    evidence.append((normalized, original))
                    seen.add(normalized)
                continue
            
            for value in analysis.get(field, []):
                original = str(value).strip()
                normalized = self._normalize_text(original)
                if normalized and normalized not in seen:
                    evidence.append((normalized, original))
                    seen.add(normalized)
        
        return evidence
    
    def _normalize_text(self, text):
        lowered = text.casefold()
        normalized = re.sub(r"[^\\w\\u4e00-\\u9fff]+", " ", lowered)
        return " ".join(normalized.split())

