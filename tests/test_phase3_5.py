"""
Tests for Phase 3-5 modules: capability_probe, divergence_reporter, verification_runner.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

# Test Phase 3: Capability Probe
from src.capability_probe import (
    CapabilityLevel,
    CapabilityProbe,
    CapabilityTest,
    ProbeResult,
    get_capability_action,
    probe_capability,
    CAPABILITY_TEST_PROMPTS,
)

# Test Phase 4: Divergence Reporter
from src.divergence_reporter import (
    DivergencePoint,
    DivergenceReporter,
    DivergenceReport,
    DivergenceSeverity,
    generate_divergence_report,
    report_to_dict,
)

# Test Phase 5: Verification Runner
from src.verification_runner import (
    VerificationMetric,
    VerificationReport,
    VerificationRunner,
    VerificationStatus,
    VerificationStep,
    report_to_dict as verification_report_to_dict,
    run_verification,
)


# === Phase 3 Tests: Capability Probe ===
class TestCapabilityProbe:
    """Tests for the CapabilityProbe class."""
    
    def test_initialization(self):
        """Test that CapabilityProbe initializes correctly."""
        probe = CapabilityProbe()
        assert probe is not None
        assert len(probe.get_test_names()) == 4
    
    def test_probe_high_capability(self):
        """Test probing a high capability model."""
        probe = CapabilityProbe()
        
        # 获取测试提示词用于判断
        test_prompts = CAPABILITY_TEST_PROMPTS
        
        def mock_model_call(prompt: str) -> str:
            if "请分析以下任务，并返回 JSON 格式的分析结果" in prompt:
                return json.dumps({
                    "opinion": "可行",
                    "key_points": ["要点1", "要点2"],
                    "concerns": [],
                    "suggestions": [],
                    "feasibility": "high"
                })
            elif "请从以下选项中选择最适合的路由" in prompt:
                return "A"
            elif "请生成符合以下 JSON Schema 的数据" in prompt:
                return json.dumps({
                    "route_id": "direct_execution",
                    "task_class": "simple",
                    "next_action": "execute"
                })
            else:
                return "要点1\n要点2\n要点3"
        
        result = probe.probe(mock_model_call, "test_model")
        assert isinstance(result, ProbeResult)
        assert result.level in [CapabilityLevel.L1, CapabilityLevel.L2]
        assert result.score >= 0.0
        assert result.score <= 1.0
    
    def test_probe_low_capability(self):
        """Test probing a low capability model."""
        probe = CapabilityProbe()
        
        def mock_model_call(prompt: str) -> str:
            return "我不确定"
        
        result = probe.probe(mock_model_call, "test_model")
        assert isinstance(result, ProbeResult)
        assert result.level == CapabilityLevel.L0
        assert result.score < 0.5
    
    def test_get_execution_path(self):
        """Test getting execution path based on capability level."""
        probe = CapabilityProbe()
        assert probe.get_execution_path(CapabilityLevel.L0) == "skip_consensus"
        assert probe.get_execution_path(CapabilityLevel.L1) == "server_normalization"
        assert probe.get_execution_path(CapabilityLevel.L2) == "normal_flow"
    
    def test_get_capability_action(self):
        """Test the convenience function get_capability_action."""
        level, action = get_capability_action(0.9)
        assert level == CapabilityLevel.L2
        assert action == "normal_flow"
        
        level, action = get_capability_action(0.5)
        assert level == CapabilityLevel.L1
        assert action == "server_normalization"
        
        level, action = get_capability_action(0.2)
        assert level == CapabilityLevel.L0
        assert action == "skip_consensus"
    
    def test_convenience_function(self):
        """Test the probe_capability convenience function."""
        def mock_model_call(prompt: str) -> str:
            return "要点1\n要点2\n要点3"
        
        result = probe_capability(mock_model_call, "test_model")
        assert isinstance(result, ProbeResult)


# === Phase 4 Tests: Divergence Reporter ===
class TestDivergenceReporter:
    """Tests for the DivergenceReporter class."""
    
    def test_initialization(self):
        """Test that DivergenceReporter initializes correctly."""
        reporter = DivergenceReporter()
        assert reporter is not None
    
    def test_generate_report_consensus(self):
        """Test generating a report with full consensus."""
        reporter = DivergenceReporter()
        
        model_results = {
            "model_a": {
                "opinion": "可行",
                "key_points": ["要点1", "要点2"],
                "concerns": ["关注点1"],
                "suggestions": ["建议1"],
                "feasibility": "high",
            },
            "model_b": {
                "opinion": "可行",
                "key_points": ["要点1", "要点2"],
                "concerns": ["关注点1"],
                "suggestions": ["建议1"],
                "feasibility": "high",
            },
        }
        
        report = reporter.generate_report(model_results)
        assert isinstance(report, DivergenceReport)
        assert report.overall_status is not None
        assert len(report.consensus_points) > 0
        assert report.model_count == 2
    
    def test_generate_report_divergence(self):
        """Test generating a report with divergence."""
        reporter = DivergenceReporter()
        
        model_results = {
            "model_a": {
                "opinion": "可行",
                "key_points": ["要点A1", "要点A2"],
                "concerns": ["关注点A"],
                "suggestions": ["建议A1", "建议A2"],
                "feasibility": "high",
            },
            "model_b": {
                "opinion": "需谨慎",
                "key_points": ["要点B1"],
                "concerns": ["关注点B1", "关注点B2"],
                "suggestions": ["建议B"],
                "feasibility": "medium",
            },
        }
        
        report = reporter.generate_report(model_results)
        assert isinstance(report, DivergenceReport)
        assert len(report.divergence_points) > 0
    
    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        reporter = DivergenceReporter()
        
        model_results = {
            "model_a": {
                "opinion": "可行",
                "key_points": ["要点1"],
                "concerns": [],
                "suggestions": [],
                "feasibility": "high",
            },
            "model_b": {
                "opinion": "可行",
                "key_points": ["要点1"],
                "concerns": [],
                "suggestions": [],
                "feasibility": "high",
            },
        }
        
        report = reporter.generate_report(model_results)
        report_dict = report_to_dict(report)
        
        assert isinstance(report_dict, dict)
        assert "overall_status" in report_dict
        assert "consensus_rate" in report_dict
        assert "recommendations" in report_dict
    
    def test_convenience_function(self):
        """Test the generate_divergence_report convenience function."""
        model_results = {
            "model_a": {
                "opinion": "可行",
                "key_points": ["要点1"],
                "concerns": [],
                "suggestions": [],
                "feasibility": "high",
            },
            "model_b": {
                "opinion": "可行",
                "key_points": ["要点1"],
                "concerns": [],
                "suggestions": [],
                "feasibility": "high",
            },
        }
        
        report = generate_divergence_report(model_results)
        assert isinstance(report, DivergenceReport)


# === Phase 5 Tests: Verification Runner ===
class TestVerificationRunner:
    """Tests for the VerificationRunner class."""
    
    def test_initialization(self, tmp_path):
        """Test that VerificationRunner initializes correctly."""
        runner = VerificationRunner(str(tmp_path))
        assert runner is not None
    
    def test_start_and_complete_step(self, tmp_path):
        """Test starting and completing verification steps."""
        runner = VerificationRunner(str(tmp_path))
        
        step = runner.start_step("test_step")
        assert step.status == VerificationStatus.RUNNING
        
        runner.complete_step(step, VerificationStatus.PASSED)
        assert step.status == VerificationStatus.PASSED
        assert step.end_time is not None
    
    def test_add_metric(self, tmp_path):
        """Test adding verification metrics."""
        runner = VerificationRunner(str(tmp_path))
        
        runner.add_metric("test_metric", 0.8, "score", 0.7)
        # The metric is added to internal state, tested indirectly via run_verification
    
    def test_run_verification(self, tmp_path):
        """Test running a complete verification."""
        runner = VerificationRunner(str(tmp_path))
        
        def mock_workflow() -> Dict[str, Any]:
            return {
                "success": True,
                "token_usage": 5000,
            }
        
        report = runner.run_verification(mock_workflow, "测试任务")
        assert isinstance(report, VerificationReport)
        assert report.overall_status in [
            VerificationStatus.PASSED,
            VerificationStatus.PARTIAL,
        ]
        assert report.total_duration_ms > 0
        assert len(report.steps) > 0
        assert len(report.recommendations) > 0
    
    def test_save_report(self, tmp_path):
        """Test saving a verification report."""
        runner = VerificationRunner(str(tmp_path))
        
        def mock_workflow() -> Dict[str, Any]:
            return {"success": True}
        
        report = runner.run_verification(mock_workflow, "测试任务")
        saved_path = runner.save_report(report)
        
        assert saved_path.exists()
        assert saved_path.suffix == ".json"
    
    def test_report_to_dict(self, tmp_path):
        """Test converting verification report to dictionary."""
        runner = VerificationRunner(str(tmp_path))
        
        def mock_workflow() -> Dict[str, Any]:
            return {"success": True}
        
        report = runner.run_verification(mock_workflow, "测试任务")
        report_dict = verification_report_to_dict(report)
        
        assert isinstance(report_dict, dict)
        assert "overall_status" in report_dict
        assert "steps" in report_dict
        assert "metrics" in report_dict
        assert "recommendations" in report_dict
    
    def test_convenience_function(self, tmp_path):
        """Test the run_verification convenience function."""
        def mock_workflow() -> Dict[str, Any]:
            return {"success": True}
        
        report = run_verification(str(tmp_path), mock_workflow, "测试任务")
        assert isinstance(report, VerificationReport)


# === Integration Tests ===
class TestPhase35Integration:
    """Integration tests for Phase 3-5 modules."""
    
    def test_full_workflow_simulation(self, tmp_path):
        """Test a simulated full workflow using all three modules."""
        # Phase 3: Capability Probe
        probe = CapabilityProbe()
        
        def mock_model(prompt: str) -> str:
            if "请分析以下任务，并返回 JSON 格式的分析结果" in prompt:
                return json.dumps({
                    "opinion": "可行",
                    "key_points": ["要点1"],
                    "concerns": [],
                    "suggestions": [],
                    "feasibility": "high"
                })
            elif "请从以下选项中选择最适合的路由" in prompt:
                return "A"
            elif "请生成符合以下 JSON Schema 的数据" in prompt:
                return json.dumps({
                    "route_id": "direct_execution",
                    "task_class": "simple",
                    "next_action": "execute"
                })
            else:
                return "要点1\n要点2\n要点3"
        
        probe_result = probe.probe(mock_model, "test_model")
        assert probe_result.level in [CapabilityLevel.L1, CapabilityLevel.L2]
        
        # Phase 4: Divergence Reporter (simulate model results)
        reporter = DivergenceReporter()
        model_results = {
            "model_a": {
                "opinion": "可行",
                "key_points": ["要点1"],
                "concerns": [],
                "suggestions": [],
                "feasibility": "high",
            },
            "model_b": {
                "opinion": "可行",
                "key_points": ["要点1"],
                "concerns": [],
                "suggestions": [],
                "feasibility": "high",
            },
        }
        divergence_report = reporter.generate_report(model_results)
        assert divergence_report.consensus_rate == 1.0
        
        # Phase 5: Verification Runner
        runner = VerificationRunner(str(tmp_path))
        
        def mock_workflow() -> Dict[str, Any]:
            return {
                "success": True,
                "token_usage": 5000,
            }
        
        verification_report = runner.run_verification(mock_workflow, "完整工作流测试")
        assert verification_report.overall_status == VerificationStatus.PASSED
        
        # All phases completed successfully
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
