import importlib.util
import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from schema_validator import is_valid_output
from state_store import StateStore
from workflow_state import WorkflowStateMachine


def load_server_module():
    module_path = Path(__file__).resolve().parents[1] / "codex-qwen-mcp-server-v2.py"
    spec = importlib.util.spec_from_file_location("codex_qwen_mcp_server_v2", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_analysis(
    *,
    opinion: str = "Proceed with the consensus workflow.",
    key_points: list[str] | None = None,
    concerns: list[str] | None = None,
    suggestions: list[str] | None = None,
    feasibility: str = "high",
) -> dict[str, object]:
    return {
        "opinion": opinion,
        "key_points": key_points or ["The server should own orchestration."],
        "concerns": concerns or ["Need strict schema validation."],
        "suggestions": suggestions or ["Persist workflow state."],
        "feasibility": feasibility,
    }


def make_review(
    *,
    verdict: str = "pass",
    summary: str = "Review passed.",
    issues: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "verdict": verdict,
        "summary": summary,
        "issues": issues or [],
    }


class McpServerV2ToolTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path.cwd() / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        self.project_dir = temp_root / f"mcp-server-v2-{uuid4().hex}"
        self.project_dir.mkdir()
        self.module = load_server_module()
        self.store = StateStore(self.project_dir)

    def tearDown(self) -> None:
        if self.project_dir.exists():
            shutil.rmtree(self.project_dir)

    def test_prepare_context_initializes_state_and_routes_complex_task(self) -> None:
        context_file = self.project_dir / "notes.md"
        context_file.write_text("Need deterministic orchestration and audit history.", encoding="utf-8")

        response = json.loads(
            self.module.mcp_prepare_context(
                task="重构核心架构并替换主 MCP Server",
                project_dir=str(self.project_dir),
                context_files=[str(context_file)],
            )
        )

        self.assertEqual(response["workflow_state"], "CONSENSUS_ROUND_1")
        self.assertEqual(response["route_choice"]["route_id"], "consensus_3_rounds")
        self.assertTrue(is_valid_output("route_choice", response["route_choice"]))
        self.assertEqual(
            WorkflowStateMachine(self.project_dir).current_state,
            "CONSENSUS_ROUND_1",
        )
        saved_state = self.store.load_state()
        self.assertEqual(saved_state["task_id"], response["task_id"])
        self.assertEqual(saved_state["route_choice"], response["route_choice"])
        self.assertEqual(saved_state["prepared_context"]["context_items"][0]["path"], str(context_file))

    def test_qwen_analyze_validates_and_persists_analysis_output(self) -> None:
        prepared_context = self.module.mcp_prepare_context(
            task="实现 MCP 共识流程",
            project_dir=str(self.project_dir),
        )
        analysis = make_analysis(suggestions=["Persist workflow state.", "Merge proposal templates."])

        with patch.object(self.module, "_invoke_qwen_analysis", return_value=analysis):
            response = json.loads(
                self.module.mcp_qwen_analyze(
                    project_dir=str(self.project_dir),
                    prepared_context=prepared_context,
                )
            )

        self.assertTrue(is_valid_output("analyze_output", response["analysis"]))
        self.assertEqual(response["analysis"], analysis)
        self.assertEqual(self.store.load_state()["qwen_analysis"], analysis)

    def test_codex_analyze_validates_and_persists_analysis_output(self) -> None:
        prepared_context = self.module.mcp_prepare_context(
            task="实现 MCP 共识流程",
            project_dir=str(self.project_dir),
        )
        analysis = make_analysis(
            opinion="Codex agrees with the workflow.",
            suggestions=["Persist workflow state.", "Keep review logic structured."],
        )

        with patch.object(self.module, "_invoke_codex_analysis", return_value=analysis):
            response = json.loads(
                self.module.mcp_codex_analyze(
                    project_dir=str(self.project_dir),
                    prepared_context=prepared_context,
                )
            )

        self.assertTrue(is_valid_output("analyze_output", response["analysis"]))
        self.assertEqual(response["analysis"], analysis)
        self.assertEqual(self.store.load_state()["codex_analysis"], analysis)

    def test_consensus_check_advances_to_next_round_when_models_diverge(self) -> None:
        self.module.mcp_prepare_context(
            task="实现 MCP 共识流程",
            project_dir=str(self.project_dir),
        )
        qwen_result = make_analysis(
            concerns=["Need strict schema validation."],
            suggestions=["Persist workflow state."],
            feasibility="high",
        )
        codex_result = make_analysis(
            concerns=["Need offline execution support."],
            suggestions=["Refactor the router first."],
            feasibility="medium",
        )

        response = json.loads(
            self.module.mcp_consensus_check(
                project_dir=str(self.project_dir),
                qwen_result=json.dumps(qwen_result, ensure_ascii=False),
                codex_result=json.dumps(codex_result, ensure_ascii=False),
            )
        )

        self.assertFalse(response["consensus"]["consensus_reached"])
        self.assertEqual(response["workflow_state"], "CONSENSUS_ROUND_2")
        self.assertEqual(WorkflowStateMachine(self.project_dir).current_state, "CONSENSUS_ROUND_2")

    def test_consensus_check_advances_to_final_plan_when_models_align(self) -> None:
        self.module.mcp_prepare_context(
            task="实现 MCP 共识流程",
            project_dir=str(self.project_dir),
        )
        qwen_result = make_analysis(
            suggestions=["Persist workflow state.", "Keep audit history."],
        )
        codex_result = make_analysis(
            opinion="proceed with the consensus workflow.",
            suggestions=["Keep audit history!", "Persist workflow state."],
        )

        response = json.loads(
            self.module.mcp_consensus_check(
                project_dir=str(self.project_dir),
                qwen_result=json.dumps(qwen_result, ensure_ascii=False),
                codex_result=json.dumps(codex_result, ensure_ascii=False),
            )
        )

        self.assertTrue(response["consensus"]["consensus_reached"])
        self.assertEqual(response["workflow_state"], "FINAL_PLAN")
        self.assertEqual(WorkflowStateMachine(self.project_dir).current_state, "FINAL_PLAN")

    def test_merge_proposals_creates_final_plan_payload(self) -> None:
        self.module.mcp_prepare_context(
            task="实现 MCP 共识流程",
            project_dir=str(self.project_dir),
        )
        qwen_result = make_analysis(
            suggestions=["Persist workflow state.", "Keep audit history."],
        )
        codex_result = make_analysis(
            suggestions=["Keep audit history.", "Persist workflow state."],
        )
        consensus_result = json.loads(
            self.module.mcp_consensus_check(
                project_dir=str(self.project_dir),
                qwen_result=json.dumps(qwen_result, ensure_ascii=False),
                codex_result=json.dumps(codex_result, ensure_ascii=False),
            )
        )["consensus"]

        response = json.loads(
            self.module.mcp_merge_proposals(
                project_dir=str(self.project_dir),
                qwen_result=json.dumps(qwen_result, ensure_ascii=False),
                codex_result=json.dumps(codex_result, ensure_ascii=False),
                consensus_result=json.dumps(consensus_result, ensure_ascii=False),
            )
        )

        self.assertEqual(response["workflow_state"], "FINAL_PLAN")
        self.assertTrue(response["merged_proposal"]["consensus_reached"])
        self.assertEqual(
            response["merged_proposal"]["suggested_steps"],
            ["Keep audit history.", "Persist workflow state."],
        )
        self.assertEqual(self.store.load_state()["final_plan"], response["merged_proposal"])

    def test_joint_review_completes_workflow_when_reviews_pass(self) -> None:
        self.module.mcp_prepare_context(
            task="实现 MCP 共识流程",
            project_dir=str(self.project_dir),
        )
        aligned = make_analysis(
            suggestions=["Persist workflow state.", "Keep audit history."],
        )
        self.module.mcp_consensus_check(
            project_dir=str(self.project_dir),
            qwen_result=json.dumps(aligned, ensure_ascii=False),
            codex_result=json.dumps(aligned, ensure_ascii=False),
        )
        self.module.mcp_merge_proposals(
            project_dir=str(self.project_dir),
            qwen_result=json.dumps(aligned, ensure_ascii=False),
            codex_result=json.dumps(aligned, ensure_ascii=False),
            consensus_result=json.dumps(
                {
                    "consensus_reached": True,
                    "consensus_points": [],
                    "divergence_points": [],
                    "evidence_comparison": {
                        "goal_aligned": True,
                        "constraints_aligned": True,
                        "implementation_path_aligned": True,
                    },
                },
                ensure_ascii=False,
            ),
        )

        response = json.loads(
            self.module.mcp_joint_review(
                project_dir=str(self.project_dir),
                implementation_summary="Implemented the new MCP workflow server.",
                qwen_review=json.dumps(make_review(), ensure_ascii=False),
                codex_review=json.dumps(make_review(summary="Implementation is ready."), ensure_ascii=False),
            )
        )

        self.assertTrue(response["joint_review"]["approved"])
        self.assertEqual(response["workflow_state"], "COMPLETED")
        self.assertEqual(WorkflowStateMachine(self.project_dir).current_state, "COMPLETED")

    def test_audit_log_appends_history_entry(self) -> None:
        response = json.loads(
            self.module.mcp_audit_log(
                project_dir=str(self.project_dir),
                event="manual_check",
                payload=json.dumps({"note": "validated"}, ensure_ascii=False),
            )
        )

        history = self.store.get_history()
        self.assertEqual(response["event"], "manual_check")
        self.assertEqual(history[-1]["event"], "manual_check")
        self.assertEqual(history[-1]["payload"], {"note": "validated"})

    def test_instructions_describe_new_consensus_workflow(self) -> None:
        instructions = self.module.MCP_INSTRUCTIONS

        for tool_name in (
            "mcp_prepare_context",
            "mcp_task_router",
            "mcp_dynamic_fuse",
            "mcp_qwen_analyze",
            "mcp_codex_analyze",
            "mcp_consensus_check",
            "mcp_merge_proposals",
            "mcp_joint_review",
            "mcp_audit_log",
        ):
            self.assertIn(tool_name, instructions)
        self.assertIn("共识", instructions)

    def test_task_router_routes_simple_task(self) -> None:
        """测试 mcp_task_router 对简单任务的路由。"""
        response = json.loads(
            self.module.mcp_task_router(
                task="修复登录页面的按钮样式",
                project_dir=str(self.project_dir),
            )
        )

        self.assertTrue(response["success"])
        self.assertIn("route_choice", response)
        route_choice = response["route_choice"]
        self.assertEqual(route_choice["task_class"], "simple")
        self.assertEqual(route_choice["route_id"], "direct_execution")

    def test_task_router_routes_complex_task(self) -> None:
        """测试 mcp_task_router 对复杂任务的路由。"""
        response = json.loads(
            self.module.mcp_task_router(
                task="重构核心架构并迁移数据库",
                project_dir=str(self.project_dir),
            )
        )

        self.assertTrue(response["success"])
        route_choice = response["route_choice"]
        self.assertEqual(route_choice["task_class"], "complex")
        self.assertEqual(route_choice["route_id"], "consensus_3_rounds")

    def test_task_router_without_project_dir(self) -> None:
        """测试 mcp_task_router 无项目目录时仍能工作。"""
        response = json.loads(
            self.module.mcp_task_router(
                task="实现新功能模块",
            )
        )

        self.assertTrue(response["success"])
        self.assertIn("route_choice", response)

    def test_dynamic_fuse_normal_capability(self) -> None:
        """测试 mcp_dynamic_fuse 正常能力等级。"""
        response = json.loads(
            self.module.mcp_dynamic_fuse(
                project_dir=str(self.project_dir),
                capability_score=0.8,
                used_tokens=50000,
                total_tokens=100000,
            )
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["capability"]["level"], "L2")
        self.assertFalse(response["fuse_triggered"])

    def test_dynamic_fuse_low_capability_triggers_action(self) -> None:
        """测试 mcp_dynamic_fuse 低能力触发熔断。"""
        response = json.loads(
            self.module.mcp_dynamic_fuse(
                project_dir=str(self.project_dir),
                capability_score=0.2,
            )
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["capability"]["level"], "L0")
        self.assertEqual(response["capability"]["action"], "skip_consensus")

    def test_dynamic_fuse_token_budget_triggers_fuse(self) -> None:
        """测试 mcp_dynamic_fuse Token 预算触发熔断。"""
        response = json.loads(
            self.module.mcp_dynamic_fuse(
                project_dir=str(self.project_dir),
                capability_score=0.8,
                used_tokens=85000,
                total_tokens=100000,
            )
        )

        self.assertTrue(response["success"])
        self.assertTrue(response["runtime"]["token_budget_fuse"])
        self.assertTrue(response["fuse_triggered"])
        self.assertIn("token_budget", response["triggered_types"])

    def test_dynamic_fuse_without_project_dir(self) -> None:
        """测试 mcp_dynamic_fuse 无项目目录时仍能工作。"""
        # 不提供 project_dir 或使用空字符串
        response = json.loads(
            self.module.mcp_dynamic_fuse(
                project_dir="",
                capability_score=0.5,
            )
        )

        # 可能因为路径无效而失败，但不应崩溃
        # 检查响应是否是有效的 JSON
        self.assertIn("success", response)


if __name__ == "__main__":
    unittest.main()
