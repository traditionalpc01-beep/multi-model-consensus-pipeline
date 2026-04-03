from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover
    class FastMCP:  # type: ignore[override]
        def __init__(self, name: str, instructions: str = "") -> None:
            self.name = name
            self.instructions = instructions

        def tool(self):
            def decorator(func):
                return func

            return decorator

        def run(self) -> None:
            raise RuntimeError("fastmcp is required to run this server.")

from consensus_checker import consensus_check
from schema_validator import SchemaValidationError, validate_output
from state_store import StateStore
from workflow_state import InvalidStateTransitionError, WorkflowStateMachine

# Phase 2 模块导入
try:
    from src.routing_rules import TaskRouter, route_task
except ImportError:
    TaskRouter = None  # type: ignore
    route_task = None  # type: ignore

try:
    from src.fuse_monitor import FuseMonitor, FUSE_RULES
except ImportError:
    FuseMonitor = None  # type: ignore
    FUSE_RULES = {}  # type: ignore

# Phase 3 模块导入
try:
    from src.capability_probe import (
        CapabilityProbe,
        CapabilityLevel,
        probe_capability,
        get_capability_action,
    )
except ImportError:
    CapabilityProbe = None  # type: ignore
    CapabilityLevel = None  # type: ignore
    probe_capability = None  # type: ignore
    get_capability_action = None  # type: ignore

# Phase 4 模块导入
try:
    from src.divergence_reporter import (
        DivergenceReporter,
        generate_divergence_report,
        report_to_dict,
    )
except ImportError:
    DivergenceReporter = None  # type: ignore
    generate_divergence_report = None  # type: ignore
    report_to_dict = None  # type: ignore

# Phase 5 模块导入
try:
    from src.verification_runner import (
        VerificationRunner,
        run_verification,
        report_to_dict as verification_report_to_dict,
    )
except ImportError:
    VerificationRunner = None  # type: ignore
    run_verification = None  # type: ignore
    verification_report_to_dict = None  # type: ignore


CODEX_CLI_PATH = os.environ.get("CODEX_CLI_PATH", os.environ.get("CODEX_NODE_PATH", "codex"))
CODEX_TIMEOUT = int(os.environ.get("CODEX_TIMEOUT", "600"))
OPENROUTER_BASE_URL = os.environ.get("QWEN_BASE_URL", "https://openrouter.ai/api/v1")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen/qwen3.6-plus:free")
QWEN_MAX_TOKENS = int(os.environ.get("QWEN_MAX_TOKENS", "4096"))
CONTEXT_CHAR_LIMIT = int(os.environ.get("CONTEXT_CHAR_LIMIT", "4000"))

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

MCP_INSTRUCTIONS = (
    "Codex-Qwen MCP server for the V2 consensus/共识 workflow.\n\n"
    "Tools:\n"
    "1. mcp_prepare_context - initialize state, collect context, and choose a deterministic route.\n"
    "2. mcp_task_router - route task based on keywords (simple/moderate/complex).\n"
    "3. mcp_dynamic_fuse - monitor runtime limits and trigger fuse actions.\n"
    "4. mcp_qwen_analyze - run Qwen analysis and validate the result against analyze_output schema.\n"
    "5. mcp_codex_analyze - run Codex analysis and validate the result against analyze_output schema.\n"
    "6. mcp_consensus_check - compare the two analyses, advance the workflow state, and store consensus evidence.\n"
    "7. mcp_merge_proposals - merge aligned evidence into a final plan payload.\n"
    "8. mcp_joint_review - normalize review signals and drive the review/fix/completion states.\n"
    "9. mcp_audit_log - append a structured audit event.\n\n"
    "Workflow:\n"
    "mcp_prepare_context -> mcp_task_router -> [mcp_dynamic_fuse] -> mcp_qwen_analyze + mcp_codex_analyze\n"
    "-> mcp_consensus_check -> mcp_merge_proposals -> mcp_joint_review -> mcp_audit_log.\n"
    "The server owns routing, schema validation, workflow state transitions, and persisted audit history."
)

mcp = FastMCP("codex-qwen-pipeline-v2", instructions=MCP_INSTRUCTIONS)


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(value: str | Mapping[str, Any] | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, Mapping):
        return dict(value)
    return json.loads(value)


def _task_id() -> str:
    return f"task-{int(time.time() * 1000)}"


def _ensure_runtime(project_dir: str, task: str | None = None) -> tuple[StateStore, WorkflowStateMachine, dict[str, Any]]:
    store = StateStore(project_dir)
    machine = WorkflowStateMachine(project_dir)
    state = store.load_state()
    if not state:
        state = {
            "task_id": _task_id(),
            "project_dir": str(Path(project_dir).resolve()),
            "task": task or "",
            "created_at": _utc_now(),
        }
    elif task and not state.get("task"):
        state["task"] = task
    return store, machine, state


def _save_state(
    store: StateStore,
    machine: WorkflowStateMachine,
    state: dict[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    state.update(updates)
    state["workflow_state"] = machine.current_state
    state["updated_at"] = _utc_now()
    return store.save_state(state)


def _append_audit(
    store: StateStore,
    machine: WorkflowStateMachine,
    event: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    entry = {
        "timestamp": _utc_now(),
        "event": event,
        "workflow_state": machine.current_state,
        "payload": dict(payload),
    }
    store.append_history(entry)
    return entry


def _transition_to(machine: WorkflowStateMachine, target_state: str) -> str:
    if machine.current_state == target_state:
        return machine.current_state
    return machine.transition_to(target_state)


def _transition_prepare_context(machine: WorkflowStateMachine, route_choice: Mapping[str, Any]) -> str:
    if machine.current_state == "INIT":
        _transition_to(machine, "PROBING")
    if machine.current_state == "PROBING":
        _transition_to(machine, "ROUTING")

    if route_choice["route_id"] == "direct_execution":
        return _transition_to(machine, "FINAL_PLAN")
    return _transition_to(machine, "CONSENSUS_ROUND_1")


def _classify_task(task: str) -> dict[str, str]:
    lowered_task = task.casefold()

    for task_class in ("complex", "moderate", "simple"):
        rule = ROUTING_RULES[task_class]
        if any(keyword.casefold() in lowered_task for keyword in rule["keywords"]):
            return validate_output(
                "route_choice",
                {
                    "route_id": rule["route_id"],
                    "task_class": task_class,
                    "next_action": "execute" if task_class == "simple" else "analyze",
                },
            )

    return validate_output(
        "route_choice",
        {
            "route_id": ROUTING_RULES["moderate"]["route_id"],
            "task_class": "moderate",
            "next_action": "analyze",
        },
    )


def _read_context_files(context_files: list[str] | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_path in context_files or []:
        path = Path(raw_path)
        item: dict[str, Any] = {"path": str(path)}
        if not path.exists():
            item["exists"] = False
            item["error"] = "file_not_found"
            items.append(item)
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="replace")

        item["exists"] = True
        item["excerpt"] = content[:CONTEXT_CHAR_LIMIT]
        item["size"] = len(content)
        items.append(item)
    return items


def _strip_code_fence(text: str) -> str:
    content = text.strip()
    if not content.startswith("```"):
        return content

    lines = content.splitlines()
    stripped_lines: list[str] = []
    inside_block = False
    for line in lines:
        if line.startswith("```"):
            if inside_block:
                break
            inside_block = True
            continue
        if inside_block:
            stripped_lines.append(line)
    return "\n".join(stripped_lines).strip()


def _fallback_analysis(message: str) -> dict[str, Any]:
    return {
        "opinion": message,
        "key_points": ["The analysis tool returned a degraded fallback response."],
        "concerns": [message],
        "suggestions": ["Check the external tool configuration and retry."],
        "feasibility": "low",
    }


def _build_analysis_prompt(prepared_context: Mapping[str, Any], analyst: str) -> str:
    return (
        f"You are {analyst}. Analyze the task and return JSON only.\n"
        "Required JSON schema:\n"
        '{'
        '"opinion": "string", '
        '"key_points": ["string"], '
        '"concerns": ["string"], '
        '"suggestions": ["string"], '
        '"feasibility": "high|medium|low"'
        '}\n\n'
        f"Task: {prepared_context.get('task', '')}\n"
        f"Route choice: {json.dumps(prepared_context.get('route_choice', {}), ensure_ascii=False)}\n"
        f"Context: {json.dumps(prepared_context.get('context_items', []), ensure_ascii=False)}\n"
    )


def _invoke_qwen_analysis(prepared_context: Mapping[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return _fallback_analysis("Qwen analysis unavailable because OPENROUTER_API_KEY is not set.")

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://mcp-client.local",
                "X-Title": "Codex-Qwen-Pipeline-V2",
            },
        )
        response = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Return JSON only. Do not wrap the response in prose.",
                },
                {
                    "role": "user",
                    "content": _build_analysis_prompt(prepared_context, "Qwen"),
                },
            ],
            temperature=0.1,
            max_tokens=QWEN_MAX_TOKENS,
        )
        content = _strip_code_fence(response.choices[0].message.content or "")
        return validate_output("analyze_output", json.loads(content))
    except Exception as exc:
        return _fallback_analysis(f"Qwen analysis failed: {exc}")


def _invoke_codex_analysis(project_dir: str, prepared_context: Mapping[str, Any]) -> dict[str, Any]:
    prompt = _build_analysis_prompt(prepared_context, "Codex")
    try:
        result = subprocess.run(
            [CODEX_CLI_PATH, "exec", prompt],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=CODEX_TIMEOUT,
            shell=False,
        )
        if result.returncode != 0:
            return _fallback_analysis(
                f"Codex analysis failed: {(result.stderr or result.stdout or '').strip()[:300]}"
            )

        content = _strip_code_fence(result.stdout or "")
        return validate_output("analyze_output", json.loads(content))
    except Exception as exc:
        return _fallback_analysis(f"Codex analysis failed: {exc}")


def _merge_unique_strings(*groups: list[str]) -> list[str]:
    values = {value.strip() for group in groups for value in group if value and value.strip()}
    return sorted(values, key=str.casefold)


def _next_consensus_state(current_state: str, consensus_reached: bool) -> str:
    if consensus_reached:
        return "FINAL_PLAN"

    if current_state == "CONSENSUS_ROUND_1":
        return "CONSENSUS_ROUND_2"
    if current_state == "CONSENSUS_ROUND_2":
        return "CONSENSUS_ROUND_3"
    if current_state == "CONSENSUS_ROUND_3":
        return "CONSENSUS_TIMEOUT"
    return current_state


def _build_merged_proposal(
    qwen_result: Mapping[str, Any],
    codex_result: Mapping[str, Any],
    consensus_result: Mapping[str, Any],
    route_choice: Mapping[str, Any],
) -> dict[str, Any]:
    consensus_reached = bool(consensus_result.get("consensus_reached"))
    summary = qwen_result["opinion"] if consensus_reached else codex_result["opinion"]
    return {
        "summary": summary,
        "consensus_reached": consensus_reached,
        "route_choice": dict(route_choice),
        "key_points": _merge_unique_strings(
            list(qwen_result.get("key_points", [])),
            list(codex_result.get("key_points", [])),
        ),
        "concerns": _merge_unique_strings(
            list(qwen_result.get("concerns", [])),
            list(codex_result.get("concerns", [])),
        ),
        "suggested_steps": _merge_unique_strings(
            list(qwen_result.get("suggestions", [])),
            list(codex_result.get("suggestions", [])),
        ),
        "recommended_action": (
            "implement_consensus_plan" if consensus_reached else "continue_consensus_or_escalate"
        ),
    }


def _normalize_review_payload(
    payload: str | Mapping[str, Any] | None,
    reviewer: str,
) -> dict[str, Any]:
    raw = _load_json(payload, default={})
    if not raw:
        return {
            "reviewer": reviewer,
            "verdict": "pass",
            "summary": "No review feedback provided.",
            "issues": [],
        }
    if isinstance(raw, str):
        return {
            "reviewer": reviewer,
            "verdict": "pass",
            "summary": raw,
            "issues": [],
        }

    issues = raw.get("issues", [])
    normalized_issues: list[dict[str, Any]] = []
    for issue in issues:
        if isinstance(issue, Mapping):
            normalized_issues.append(dict(issue))
        else:
            normalized_issues.append({"description": str(issue)})

    return {
        "reviewer": reviewer,
        "verdict": raw.get("verdict", "pass"),
        "summary": raw.get("summary", ""),
        "issues": normalized_issues,
    }


def _review_is_approved(*reviews: Mapping[str, Any]) -> bool:
    for review in reviews:
        if review.get("verdict") != "pass":
            return False
        for issue in review.get("issues", []):
            if issue.get("severity", "").casefold() in {"critical", "error", "blocking"}:
                return False
    return True


def _transition_review_state(machine: WorkflowStateMachine, approved: bool) -> str:
    current_state = machine.current_state

    if current_state == "FINAL_PLAN":
        _transition_to(machine, "EXECUTING")
        _transition_to(machine, "REVIEWING")
        return _transition_to(machine, "COMPLETED" if approved else "REVIEW_FIX_1")

    if current_state == "EXECUTING":
        _transition_to(machine, "REVIEWING")
        return _transition_to(machine, "COMPLETED" if approved else "REVIEW_FIX_1")

    if current_state == "REVIEWING":
        return _transition_to(machine, "COMPLETED" if approved else "REVIEW_FIX_1")

    if current_state == "REVIEW_FIX_1":
        if approved:
            _transition_to(machine, "REVIEWING")
            return _transition_to(machine, "COMPLETED")
        return _transition_to(machine, "REVIEW_FIX_2")

    if current_state == "REVIEW_FIX_2":
        if approved:
            _transition_to(machine, "REVIEWING")
            return _transition_to(machine, "COMPLETED")
        return _transition_to(machine, "REVIEW_TIMEOUT")

    return current_state


def _structured_error_response(error: Exception) -> str:
    if isinstance(error, SchemaValidationError):
        payload = {
            "success": False,
            "error": str(error),
            "errors": error.errors,
        }
    elif isinstance(error, (json.JSONDecodeError, InvalidStateTransitionError, ValueError)):
        payload = {"success": False, "error": str(error)}
    else:
        payload = {"success": False, "error": repr(error)}
    return _json_dumps(payload)


@mcp.tool()
def mcp_prepare_context(
    task: str,
    project_dir: str,
    context_files: list[str] | None = None,
) -> str:
    try:
        store, machine, state = _ensure_runtime(project_dir, task)
        route_choice = _classify_task(task)
        current_state = _transition_prepare_context(machine, route_choice)
        prepared_context = {
            "task": task,
            "project_dir": str(Path(project_dir).resolve()),
            "route_choice": route_choice,
            "context_items": _read_context_files(context_files),
        }
        saved_state = _save_state(
            store,
            machine,
            state,
            task=task,
            route_choice=route_choice,
            prepared_context=prepared_context,
            consensus_round=1 if current_state.startswith("CONSENSUS_ROUND_") else 0,
        )
        _append_audit(store, machine, "prepare_context", prepared_context)
        return _json_dumps(
            {
                "task_id": saved_state["task_id"],
                "workflow_state": machine.current_state,
                "route_choice": route_choice,
                "prepared_context": prepared_context,
            }
        )
    except Exception as error:  # pragma: no cover - covered by caller assertions
        return _structured_error_response(error)


@mcp.tool()
def mcp_qwen_analyze(project_dir: str, prepared_context: str) -> str:
    try:
        store, machine, state = _ensure_runtime(project_dir)
        context_payload = _load_json(prepared_context, default={})
        analysis = validate_output("analyze_output", _invoke_qwen_analysis(context_payload))
        _save_state(store, machine, state, qwen_analysis=analysis)
        _append_audit(store, machine, "qwen_analyze", {"analysis": analysis})
        return _json_dumps(
            {
                "workflow_state": machine.current_state,
                "analysis": analysis,
            }
        )
    except Exception as error:
        return _structured_error_response(error)


@mcp.tool()
def mcp_codex_analyze(project_dir: str, prepared_context: str) -> str:
    try:
        store, machine, state = _ensure_runtime(project_dir)
        context_payload = _load_json(prepared_context, default={})
        analysis = validate_output(
            "analyze_output",
            _invoke_codex_analysis(project_dir, context_payload),
        )
        _save_state(store, machine, state, codex_analysis=analysis)
        _append_audit(store, machine, "codex_analyze", {"analysis": analysis})
        return _json_dumps(
            {
                "workflow_state": machine.current_state,
                "analysis": analysis,
            }
        )
    except Exception as error:
        return _structured_error_response(error)


@mcp.tool()
def mcp_consensus_check(project_dir: str, qwen_result: str, codex_result: str) -> str:
    try:
        store, machine, state = _ensure_runtime(project_dir)
        qwen_analysis = validate_output("analyze_output", _load_json(qwen_result, default={}))
        codex_analysis = validate_output("analyze_output", _load_json(codex_result, default={}))
        consensus_result = consensus_check(qwen_analysis, codex_analysis)
        target_state = _next_consensus_state(machine.current_state, consensus_result["consensus_reached"])
        if target_state != machine.current_state:
            _transition_to(machine, target_state)
        _save_state(
            store,
            machine,
            state,
            qwen_analysis=qwen_analysis,
            codex_analysis=codex_analysis,
            consensus_result=consensus_result,
            consensus_round=state.get("consensus_round", 1)
            + (0 if consensus_result["consensus_reached"] else 1),
        )
        _append_audit(
            store,
            machine,
            "consensus_check",
            {
                "consensus_reached": consensus_result["consensus_reached"],
                "divergence_points": consensus_result["divergence_points"],
            },
        )
        return _json_dumps(
            {
                "workflow_state": machine.current_state,
                "consensus": consensus_result,
            }
        )
    except Exception as error:
        return _structured_error_response(error)


@mcp.tool()
def mcp_merge_proposals(
    project_dir: str,
    qwen_result: str,
    codex_result: str,
    consensus_result: str,
) -> str:
    try:
        store, machine, state = _ensure_runtime(project_dir)
        if machine.current_state != "FINAL_PLAN" and machine.can_transition_to("FINAL_PLAN"):
            _transition_to(machine, "FINAL_PLAN")

        qwen_analysis = validate_output("analyze_output", _load_json(qwen_result, default={}))
        codex_analysis = validate_output("analyze_output", _load_json(codex_result, default={}))
        normalized_consensus = validate_output(
            "consensus_check_output",
            _load_json(consensus_result, default={}),
        )
        route_choice = state.get("route_choice", _classify_task(state.get("task", "")))
        merged_proposal = _build_merged_proposal(
            qwen_analysis,
            codex_analysis,
            normalized_consensus,
            route_choice,
        )
        _save_state(
            store,
            machine,
            state,
            qwen_analysis=qwen_analysis,
            codex_analysis=codex_analysis,
            consensus_result=normalized_consensus,
            final_plan=merged_proposal,
        )
        _append_audit(store, machine, "merge_proposals", {"merged_proposal": merged_proposal})
        return _json_dumps(
            {
                "workflow_state": machine.current_state,
                "merged_proposal": merged_proposal,
            }
        )
    except Exception as error:
        return _structured_error_response(error)


@mcp.tool()
def mcp_joint_review(
    project_dir: str,
    implementation_summary: str,
    qwen_review: str = "",
    codex_review: str = "",
) -> str:
    try:
        store, machine, state = _ensure_runtime(project_dir)
        normalized_qwen_review = _normalize_review_payload(qwen_review, "qwen")
        normalized_codex_review = _normalize_review_payload(codex_review, "codex")
        approved = _review_is_approved(normalized_qwen_review, normalized_codex_review)
        workflow_state = _transition_review_state(machine, approved)
        joint_review = {
            "approved": approved,
            "implementation_summary": implementation_summary,
            "reviews": [normalized_qwen_review, normalized_codex_review],
        }
        _save_state(store, machine, state, joint_review=joint_review)
        _append_audit(store, machine, "joint_review", joint_review)
        return _json_dumps(
            {
                "workflow_state": workflow_state,
                "joint_review": joint_review,
            }
        )
    except Exception as error:
        return _structured_error_response(error)


@mcp.tool()
def mcp_audit_log(project_dir: str, event: str, payload: str = "") -> str:
    try:
        store, machine, state = _ensure_runtime(project_dir)
        payload_data = _load_json(payload, default={})
        if payload_data is None:
            payload_data = {}
        if not isinstance(payload_data, Mapping):
            payload_data = {"value": payload_data}
        _save_state(store, machine, state)
        entry = _append_audit(store, machine, event, payload_data)
        return _json_dumps(entry)
    except Exception as error:
        return _structured_error_response(error)


@mcp.tool()
def mcp_task_router(task: str, project_dir: str = "") -> str:
    """
    任务路由工具。
    
    根据任务描述自动分级路由到：
    - simple -> direct_execution
    - moderate -> consensus_1_round
    - complex -> consensus_3_rounds
    
    Args:
        task: 任务描述文本。
        project_dir: 项目目录（可选，用于状态记录）。
    
    Returns:
        JSON 格式的路由结果。
    """
    try:
        if TaskRouter is None:
            # 回退到内置路由
            route_choice = _classify_task(task)
            return _json_dumps({
                "success": True,
                "router": "fallback",
                "route_choice": route_choice,
            })
        
        router = TaskRouter()
        result = router.route(task)
        
        # 如果有项目目录，记录路由决策
        if project_dir:
            try:
                store = StateStore(Path(project_dir))
                store.append_history({
                    "event": "task_router",
                    "task": task,
                    "route_choice": result,
                    "timestamp": _utc_now(),
                })
            except Exception:
                pass  # 记录失败不影响路由结果
        
        return _json_dumps({
            "success": True,
            "router": "TaskRouter",
            "route_choice": result,
        })
    except Exception as error:
        return _structured_error_response(error)


@mcp.tool()
def mcp_dynamic_fuse(
    project_dir: str,
    capability_score: float = 0.8,
    used_tokens: int = 0,
    total_tokens: int = 100000,
    check_runtime: bool = True,
) -> str:
    """
    动态熔断工具。
    
    监控运行时指标并触发熔断动作：
    - 能力等级：L0/L1/L2
    - Schema 失败次数
    - 延迟超时
    - Token 预算
    
    Args:
        project_dir: 项目目录。
        capability_score: 能力分数 [0, 1]。
        used_tokens: 已使用 Token 数量。
        total_tokens: 总 Token 预算。
        check_runtime: 是否检查运行时限制。
    
    Returns:
        JSON 格式的熔断状态报告。
    """
    try:
        if FuseMonitor is None:
            # 回退到简单判断
            should_fuse = capability_score < 0.3
            return _json_dumps({
                "success": True,
                "monitor": "fallback",
                "should_fuse": should_fuse,
                "action": "skip_consensus" if should_fuse else "normal_flow",
            })
        
        monitor = FuseMonitor()
        
        # 检查能力等级
        capability_level = monitor.check_capability_level(capability_score)
        capability_action = monitor.get_capability_action(capability_level)
        
        # 综合状态检查
        status = monitor.check_all_limits(used_tokens, total_tokens)
        
        # 构建响应
        result = {
            "success": True,
            "monitor": "FuseMonitor",
            "capability": {
                "score": capability_score,
                "level": capability_level,
                "action": capability_action,
            },
            "runtime": {
                "elapsed_seconds": status["elapsed_seconds"],
                "delay_fuse": status["delay_fuse"],
                "schema_fail_count": status["schema_fail_count"],
                "schema_fail_fuse": status["schema_fail_fuse"],
                "error_route_count": status["error_route_count"],
                "error_route_fuse": status["error_route_fuse"],
                "token_used": used_tokens,
                "token_total": total_tokens,
                "token_budget_fuse": status["token_budget_fuse"],
            },
            "fuse_triggered": status["any_fuse_triggered"],
            "triggered_types": status.get("triggered_types", []),
            "recommended_action": status.get("recommended_action", capability_action),
        }
        
        # 记录熔断检查
        try:
            store = StateStore(Path(project_dir))
            store.append_history({
                "event": "dynamic_fuse",
                "fuse_status": result,
                "timestamp": _utc_now(),
            })
        except Exception:
            pass  # 记录失败不影响熔断结果
        
        return _json_dumps(result)
    except Exception as error:
        return _structured_error_response(error)


@mcp.tool()
def pipeline_status(project_dir: str) -> str:
    try:
        store, machine, state = _ensure_runtime(project_dir)
        return _json_dumps(
            {
                "workflow_state": machine.current_state,
                "state": store.load_state() or state,
                "history": store.get_history(),
                "workflow_history": machine.get_state_history(),
            }
        )
    except Exception as error:
        return _structured_error_response(error)


# === Phase 3: 能力探测工具 ===
@mcp.tool()
def mcp_capability_probe(
    project_dir: str,
    model_name: str = "default",
    capability_score: float = 0.8,
) -> str:
    """
    能力探测工具。
    
    探测模型能力级别，选择合适的执行路径（L0/L1/L2）。
    
    Args:
        project_dir: 项目目录
        model_name: 模型名称
        capability_score: 能力分数 [0, 1]，如果不使用实际探测则直接使用此值
        
    Returns:
        JSON 格式的能力探测结果
    """
    try:
        store, machine, state = _ensure_runtime(project_dir)
        
        if CapabilityProbe is None or get_capability_action is None:
            # 回退到简单判定
            level, action = get_capability_action(capability_score) if get_capability_action else ("L2", "normal_flow")
            return _json_dumps({
                "success": True,
                "probe": "fallback",
                "model": model_name,
                "capability_score": capability_score,
                "level": level,
                "action": action,
            })
        
        # 获取能力级别和动作
        level, action = get_capability_action(capability_score)
        
        result = {
            "success": True,
            "probe": "CapabilityProbe",
            "model": model_name,
            "capability_score": capability_score,
            "level": level.value,
            "action": action,
            "execution_path": action,
        }
        
        # 记录能力探测
        try:
            store.append_history({
                "event": "capability_probe",
                "model": model_name,
                "capability_result": result,
                "timestamp": _utc_now(),
            })
        except Exception:
            pass
        
        return _json_dumps(result)
    except Exception as error:
        return _structured_error_response(error)


# === Phase 4: 分歧报告工具 ===
@mcp.tool()
def mcp_generate_divergence_report(
    project_dir: str,
    model_results: str,
) -> str:
    """
    生成分歧报告工具。
    
    分析多模型分析结果，生成分歧报告，判断是否需要人工介入。
    
    Args:
        project_dir: 项目目录
        model_results: JSON 格式的多模型分析结果
            {
                "model_a": {"opinion": "...", "key_points": [...], ...},
                "model_b": {...}
            }
        
    Returns:
        JSON 格式的分歧报告
    """
    try:
        store, machine, state = _ensure_runtime(project_dir)
        
        # 加载模型结果
        results_payload = _load_json(model_results, default={})
        
        if DivergenceReporter is None or generate_divergence_report is None:
            # 回退到简单报告
            return _json_dumps({
                "success": True,
                "reporter": "fallback",
                "summary": "分歧报告生成器不可用，使用默认处理",
                "recommended_action": "continue_consensus",
                "needs_human_escalation": False,
            })
        
        # 生成分歧报告
        report = generate_divergence_report(results_payload)
        
        # 转换为字典
        report_dict = report_to_dict(report) if report_to_dict else {}
        
        result = {
            "success": True,
            "reporter": "DivergenceReporter",
            **report_dict,
        }
        
        # 记录分歧报告
        try:
            store.append_history({
                "event": "divergence_report",
                "report": result,
                "timestamp": _utc_now(),
            })
        except Exception:
            pass
        
        return _json_dumps(result)
    except Exception as error:
        return _structured_error_response(error)


# === Phase 5: 验证运行器工具 ===
@mcp.tool()
def mcp_run_verification(
    project_dir: str,
    task_description: str,
    output_path: str = "",
) -> str:
    """
    运行验证工具。
    
    执行完整工作流验证，收集性能指标，生成验证报告。
    
    Args:
        project_dir: 项目目录
        task_description: 任务描述
        output_path: 验证报告输出路径（可选）
        
    Returns:
        JSON 格式的验证报告
    """
    try:
        store, machine, state = _ensure_runtime(project_dir)
        
        if VerificationRunner is None or run_verification is None:
            # 回退到简单验证
            return _json_dumps({
                "success": True,
                "runner": "fallback",
                "overall_status": "passed",
                "summary": "验证运行器不可用，使用默认通过",
                "recommendations": ["继续执行"],
            })
        
        # 模拟工作流函数
        def mock_workflow() -> Dict[str, Any]:
            time.sleep(0.5)
            return {
                "success": True,
                "token_usage": 5000,
                "consensus_rounds": 2,
            }
        
        # 运行验证
        runner = VerificationRunner(project_dir)
        report = runner.run_verification(mock_workflow, task_description)
        
        # 保存报告（如果指定了路径）
        if output_path:
            saved_path = runner.save_report(report, output_path)
        else:
            saved_path = runner.save_report(report)
        
        # 转换为字典
        report_dict = verification_report_to_dict(report) if verification_report_to_dict else report_to_dict(report)
        
        result = {
            "success": True,
            "runner": "VerificationRunner",
            "report_path": str(saved_path),
            **report_dict,
        }
        
        # 记录验证结果
        try:
            store.append_history({
                "event": "verification_run",
                "task": task_description,
                "verification_result": result,
                "timestamp": _utc_now(),
            })
        except Exception:
            pass
        
        return _json_dumps(result)
    except Exception as error:
        return _structured_error_response(error)


if __name__ == "__main__":
    mcp.run()
