
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


ROUTING_RULES = {
    "simple": {
        "route_id": "direct_execution",
        "keywords": ["fix", "update", "change", "adjust", "modify", "add", "修复", "更新", "修改", "调整", "添加"],
    },
    "moderate": {
        "route_id": "consensus_1_round",
        "keywords": ["implement", "build", "develop", "integrate", "实现", "开发", "集成"],
    },
    "complex": {
        "route_id": "consensus_3_rounds",
        "keywords": ["architecture", "rewrite", "replace", "refactor", "migrate", "架构", "重构", "替换", "迁移", "核心"],
    },
}


class RouteChoice:
    def __init__(self, route_id, task_class, next_action):
        self.route_id = route_id
        self.task_class = task_class
        self.next_action = next_action
    
    def to_dict(self):
        return {
            "route_id": self.route_id,
            "task_class": self.task_class,
            "next_action": self.next_action
        }


class TaskRouter:
    def __init__(self):
        self.rules = ROUTING_RULES
    
    def route(self, task):
        lowered_task = task.casefold()
        
        for task_class in ("complex", "moderate", "simple"):
            rule = self.rules[task_class]
            if any(keyword.casefold() in lowered_task for keyword in rule["keywords"]):
                return RouteChoice(
                    route_id=rule["route_id"],
                    task_class=task_class,
                    next_action="execute" if task_class == "simple" else "analyze"
                )
        
        return RouteChoice(
            route_id=self.rules["moderate"]["route_id"],
            task_class="moderate",
            next_action="analyze"
        )


class CapabilityLevel(Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"


class CapabilityProbe:
    L2_THRESHOLD = 0.80
    L1_THRESHOLD = 0.50
    
    def __init__(self):
        pass
    
    def get_capability_action(self, score):
        if score >= self.L2_THRESHOLD:
            level = CapabilityLevel.L2
            action = "normal_flow"
        elif score >= self.L1_THRESHOLD:
            level = CapabilityLevel.L1
            action = "server_normalization"
        else:
            level = CapabilityLevel.L0
            action = "skip_consensus"
        return level, action
    
    def get_execution_path(self, level):
        path_map = {
            CapabilityLevel.L0: "skip_consensus",
            CapabilityLevel.L1: "server_normalization",
            CapabilityLevel.L2: "normal_flow",
        }
        return path_map.get(level, "normal_flow")


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
    
    def _compare_dimension(self, dimension, qwen_analysis, codex_analysis):
        qwen_evidence = self._collect_evidence(qwen_analysis, self.dimension_fields[dimension])
        codex_evidence = self._collect_evidence(codex_analysis, self.dimension_fields[dimension])
        
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
    
    def _collect_evidence(self, analysis, fields):
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
        normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", lowered)
        return " ".join(normalized.split())


class WorkflowState:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.state_dir = project_dir / ".skill-state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "state.json"
        self.history_file = self.state_dir / "history.jsonl"
        
        self._state = {}
        self._history = []
        self._load()
    
    def _load(self):
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self._state = json.load(f)
        else:
            self._state = {
                "current_state": "INIT",
                "context": {},
                "capability_level": None,
                "consensus_results": [],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self._save()
        
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._history.append(json.loads(line))
    
    def _save(self):
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)
    
    def _append_history(self, entry):
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._history.append(entry)
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    def get_state(self):
        return self._state.copy()
    
    def set_context(self, context):
        self._state["context"] = context
        self._append_history({"event": "set_context", "context": context})
        self._save()
    
    def set_capability_level(self, level):
        self._state["capability_level"] = level.value if hasattr(level, 'value') else level
        self._append_history({"event": "set_capability_level", "level": self._state["capability_level"]})
        self._save()
    
    def add_consensus_result(self, result):
        self._state["consensus_results"].append(result)
        self._append_history({"event": "add_consensus_result", "result": result})
        self._save()
    
    def reset(self):
        self._state = {
            "current_state": "INIT",
            "context": {},
            "capability_level": None,
            "consensus_results": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._history = []
        if self.history_file.exists():
            self.history_file.unlink()
        self._save()


FUSE_RULES = {
    "capability_levels": {
        "L0_threshold": 0.3,
        "L1_threshold": 0.6,
        "L2_threshold": 0.8
    },
    "runtime": {
        "schema_fail_max": 3,
        "delay_max_seconds": 30,
        "error_route_max": 2,
        "token_budget_ratio": 0.8
    }
}


class FuseStatus:
    def __init__(self, any_fuse_triggered, capability_level, capability_action, 
                 delay_fuse, schema_fail_fuse, token_budget_fuse, 
                 error_route_fuse, recommended_action):
        self.any_fuse_triggered = any_fuse_triggered
        self.capability_level = capability_level
        self.capability_action = capability_action
        self.delay_fuse = delay_fuse
        self.schema_fail_fuse = schema_fail_fuse
        self.token_budget_fuse = token_budget_fuse
        self.error_route_fuse = error_route_fuse
        self.recommended_action = recommended_action


class FuseMonitor:
    def __init__(self):
        self.rules = FUSE_RULES
        self.schema_fail_count = 0
        self.error_route_count = 0
        self.elapsed_seconds = 0.0
    
    def check_capability_level(self, score):
        thresholds = self.rules["capability_levels"]
        if score >= thresholds["L2_threshold"]:
            return "L2"
        elif score >= thresholds["L1_threshold"]:
            return "L1"
        else:
            return "L0"
    
    def get_capability_action(self, level):
        actions = {
            "L0": "skip_consensus",
            "L1": "server_normalization",
            "L2": "normal_flow"
        }
        return actions.get(level, "normal_flow")
    
    def check_all_limits(self, used_tokens=0, total_tokens=100000):
        capability_level = self.check_capability_level(0.8)
        capability_action = self.get_capability_action(capability_level)
        
        delay_fuse = self.elapsed_seconds > self.rules["runtime"]["delay_max_seconds"]
        schema_fail_fuse = self.schema_fail_count >= self.rules["runtime"]["schema_fail_max"]
        token_ratio = used_tokens / total_tokens if total_tokens > 0 else 0
        token_budget_fuse = token_ratio >= self.rules["runtime"]["token_budget_ratio"]
        error_route_fuse = self.error_route_count >= self.rules["runtime"]["error_route_max"]
        
        any_fuse_triggered = delay_fuse or schema_fail_fuse or token_budget_fuse or error_route_fuse
        
        recommended_action = capability_action
        if any_fuse_triggered:
            recommended_action = "fallback"
        
        return FuseStatus(
            any_fuse_triggered=any_fuse_triggered,
            capability_level=capability_level,
            capability_action=capability_action,
            delay_fuse=delay_fuse,
            schema_fail_fuse=schema_fail_fuse,
            token_budget_fuse=token_budget_fuse,
            error_route_fuse=error_route_fuse,
            recommended_action=recommended_action
        )
    
    def record_schema_fail(self):
        self.schema_fail_count += 1
    
    def record_error_route(self):
        self.error_route_count += 1
    
    def record_delay(self, seconds):
        self.elapsed_seconds += seconds
    
    def reset(self):
        self.schema_fail_count = 0
        self.error_route_count = 0
        self.elapsed_seconds = 0.0


class FallbackLevel(Enum):
    L1 = "MODEL_FALLBACK"
    L2 = "PARALLEL_FALLBACK"
    L3 = "CACHE_FALLBACK"
    L4 = "STATIC_FALLBACK"


class FallbackResult:
    def __init__(self, level, success, data=None, error_message=None):
        self.level = level
        self.success = success
        self.data = data
        self.error_message = error_message


class FallbackManager:
    def __init__(self):
        self.fallback_chain = [
            FallbackLevel.L1,
            FallbackLevel.L2,
            FallbackLevel.L3,
            FallbackLevel.L4
        ]
        self.current_level_index = 0
    
    def get_fallback_result(self, level, **kwargs):
        handlers = {
            FallbackLevel.L1: self._handle_model_fallback,
            FallbackLevel.L2: self._handle_parallel_fallback,
            FallbackLevel.L3: self._handle_cache_fallback,
            FallbackLevel.L4: self._handle_static_fallback,
        }
        
        handler = handlers.get(level, self._handle_static_fallback)
        return handler(**kwargs)
    
    def _handle_model_fallback(self, **kwargs):
        return FallbackResult(
            level=FallbackLevel.L1,
            success=True,
            data={"action": "switch_to_backup_model"}
        )
    
    def _handle_parallel_fallback(self, **kwargs):
        return FallbackResult(
            level=FallbackLevel.L2,
            success=True,
            data={"action": "execute_serially"}
        )
    
    def _handle_cache_fallback(self, **kwargs):
        return FallbackResult(
            level=FallbackLevel.L3,
            success=True,
            data={"action": "use_cached_response"}
        )
    
    def _handle_static_fallback(self, **kwargs):
        return FallbackResult(
            level=FallbackLevel.L4,
            success=True,
            data={"action": "use_static_default"}
        )
    
    def execute_with_fallback(self, primary_func, *args, **kwargs):
        try:
            result = primary_func(*args, **kwargs)
            return FallbackResult(
                level=FallbackLevel.L1,
                success=True,
                data=result
            )
        except Exception as e:
            for level in self.fallback_chain:
                fallback_result = self.get_fallback_result(level, error=e)
                if fallback_result.success:
                    return fallback_result
            
            return FallbackResult(
                level=FallbackLevel.L4,
                success=False,
                error_message="All fallbacks failed"
            )
    
    def reset(self):
        self.current_level_index = 0


class MultiModelConsensusSkill:
    def __init__(self, project_dir=None):
        self.project_dir = Path(project_dir or os.getcwd())
        self.state = WorkflowState(self.project_dir)
        self.task_router = TaskRouter()
        self.capability_probe = CapabilityProbe()
        self.consensus_engine = ConsensusEngine()
        self.fuse_monitor = FuseMonitor()
        self.fallback_manager = FallbackManager()
    
    def prepare_context(self, task, context_files=None):
        route_choice = self.task_router.route(task)
        context = {
            "task": task,
            "route_choice": route_choice.to_dict(),
            "context_files": context_files or []
        }
        self.state.set_context(context)
        return {
            "success": True,
            "route_choice": route_choice.to_dict(),
            "context": context
        }
    
    def probe_capability(self, capability_score=0.8):
        level, action = self.capability_probe.get_capability_action(capability_score)
        self.state.set_capability_level(level)
        return {
            "success": True,
            "level": level.value if hasattr(level, 'value') else level,
            "action": action
        }
    
    def run_consensus_round(self, qwen_analysis, codex_analysis):
        consensus_result = self.consensus_engine.check(qwen_analysis, codex_analysis)
        self.state.add_consensus_result(consensus_result)
        return {
            "success": True,
            "consensus_result": consensus_result
        }
    
    def check_fuse(self, used_tokens=0, total_tokens=100000):
        fuse_status = self.fuse_monitor.check_all_limits(used_tokens, total_tokens)
        return {
            "success": True,
            "fuse_status": {
                "any_fuse_triggered": fuse_status.any_fuse_triggered,
                "capability_level": fuse_status.capability_level,
                "capability_action": fuse_status.capability_action,
                "delay_fuse": fuse_status.delay_fuse,
                "schema_fail_fuse": fuse_status.schema_fail_fuse,
                "token_budget_fuse": fuse_status.token_budget_fuse,
                "error_route_fuse": fuse_status.error_route_fuse,
                "recommended_action": fuse_status.recommended_action
            }
        }
    
    def get_fallback(self, level=None):
        fallback_level = level or FallbackLevel.L1
        fallback_result = self.fallback_manager.get_fallback_result(fallback_level)
        return {
            "success": fallback_result.success,
            "fallback_level": fallback_level.value if hasattr(fallback_level, 'value') else fallback_level,
            "data": fallback_result.data,
            "error_message": fallback_result.error_message
        }
    
    def record_schema_fail(self):
        self.fuse_monitor.record_schema_fail()
        return {"success": True}
    
    def record_error_route(self):
        self.fuse_monitor.record_error_route()
        return {"success": True}
    
    def record_delay(self, seconds):
        self.fuse_monitor.record_delay(seconds)
        return {"success": True}
    
    def get_workflow_state(self):
        return {
            "success": True,
            "state": self.state.get_state()
        }
    
    def reset(self):
        self.state.reset()
        self.fuse_monitor.reset()
        self.fallback_manager.reset()
        return {"success": True}


__all__ = [
    "MultiModelConsensusSkill",
    "TaskRouter",
    "CapabilityProbe",
    "CapabilityLevel",
    "ConsensusEngine",
    "WorkflowState",
    "FuseMonitor",
    "FallbackManager"
]

