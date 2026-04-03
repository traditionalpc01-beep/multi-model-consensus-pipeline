"""
test_fuse_monitor.py
测试熔断监控模块。
"""

import pytest
import time
from src.fuse_monitor import FuseMonitor, FUSE_RULES


class TestFuseMonitorCapabilityLevel:
    """能力等级判定测试。"""

    def setup_method(self) -> None:
        self.monitor = FuseMonitor()

    def test_check_capability_level_L0(self) -> None:
        """测试低能力等级 L0。"""
        assert self.monitor.check_capability_level(0.1) == "L0"
        assert self.monitor.check_capability_level(0.25) == "L0"
        assert self.monitor.check_capability_level(0.29) == "L0"

    def test_check_capability_level_L1(self) -> None:
        """测试中能力等级 L1。"""
        assert self.monitor.check_capability_level(0.3) == "L1"
        assert self.monitor.check_capability_level(0.5) == "L1"
        assert self.monitor.check_capability_level(0.59) == "L1"

    def test_check_capability_level_L2(self) -> None:
        """测试高能力等级 L2。"""
        assert self.monitor.check_capability_level(0.6) == "L2"
        assert self.monitor.check_capability_level(0.8) == "L2"
        assert self.monitor.check_capability_level(1.0) == "L2"

    def test_check_capability_level_invalid_type(self) -> None:
        """测试非数字类型抛出 ValueError。"""
        with pytest.raises(ValueError, match="必须为数字"):
            self.monitor.check_capability_level("0.5")  # type: ignore

        with pytest.raises(ValueError, match="必须为数字"):
            self.monitor.check_capability_level(None)  # type: ignore

    def test_check_capability_level_out_of_range(self) -> None:
        """测试超出范围值抛出 ValueError。"""
        with pytest.raises(ValueError, match="必须在"):
            self.monitor.check_capability_level(-0.1)

        with pytest.raises(ValueError, match="必须在"):
            self.monitor.check_capability_level(1.5)

    def test_get_capability_action(self) -> None:
        """测试能力等级对应动作。"""
        assert self.monitor.get_capability_action("L0") == "skip_consensus"
        assert self.monitor.get_capability_action("L1") == "server_normalization"
        assert self.monitor.get_capability_action("L2") == "normal_flow"  # 高能力正常流程

    def test_get_capability_action_invalid_level(self) -> None:
        """测试无效等级抛出 KeyError。"""
        with pytest.raises(KeyError, match="无效的能力等级"):
            self.monitor.get_capability_action("L3")  # type: ignore


class TestFuseMonitorSchemaFail:
    """Schema 失败监控测试。"""

    def setup_method(self) -> None:
        self.monitor = FuseMonitor()

    def test_check_schema_fail_below_threshold(self) -> None:
        """测试低于阈值不熔断。"""
        assert self.monitor.check_schema_fail(0) is False
        assert self.monitor.check_schema_fail(1) is False
        assert self.monitor.check_schema_fail(2) is False

    def test_check_schema_fail_at_threshold(self) -> None:
        """测试达到阈值触发熔断。"""
        assert self.monitor.check_schema_fail(3) is True

    def test_check_schema_fail_above_threshold(self) -> None:
        """测试超过阈值触发熔断。"""
        assert self.monitor.check_schema_fail(4) is True
        assert self.monitor.check_schema_fail(10) is True

    def test_check_schema_fail_invalid_type(self) -> None:
        """测试非整数类型抛出 ValueError。"""
        with pytest.raises(ValueError, match="必须为整数"):
            self.monitor.check_schema_fail(3.5)  # type: ignore

    def test_check_schema_fail_negative(self) -> None:
        """测试负数抛出 ValueError。"""
        with pytest.raises(ValueError, match="不能为负数"):
            self.monitor.check_schema_fail(-1)

    def test_increment_schema_fail(self) -> None:
        """测试增加 Schema 失败计数。"""
        assert self.monitor.increment_schema_fail() == 1
        assert self.monitor.increment_schema_fail() == 2
        assert self.monitor.increment_schema_fail() == 3
        assert self.monitor.get_schema_fail_count() == 3


class TestFuseMonitorDelay:
    """延迟监控测试。"""

    def setup_method(self) -> None:
        self.monitor = FuseMonitor()

    def test_check_delay_below_threshold(self) -> None:
        """测试低于阈值不超时。"""
        assert self.monitor.check_delay(0) is False
        assert self.monitor.check_delay(10) is False
        assert self.monitor.check_delay(29) is False

    def test_check_delay_at_threshold(self) -> None:
        """测试达到阈值触发超时。"""
        assert self.monitor.check_delay(30) is True

    def test_check_delay_above_threshold(self) -> None:
        """测试超过阈值触发超时。"""
        assert self.monitor.check_delay(60) is True
        assert self.monitor.check_delay(120) is True

    def test_check_delay_invalid_type(self) -> None:
        """测试非数字类型抛出 ValueError。"""
        with pytest.raises(ValueError, match="必须为数字"):
            self.monitor.check_delay("10")  # type: ignore

    def test_check_delay_negative(self) -> None:
        """测试负数抛出 ValueError。"""
        with pytest.raises(ValueError, match="不能为负数"):
            self.monitor.check_delay(-5)

    def test_get_elapsed_time(self) -> None:
        """测试获取耗时。"""
        time.sleep(0.1)
        elapsed = self.monitor.get_elapsed_time()
        assert elapsed >= 0.1
        assert elapsed < 1.0  # 应该很短


class TestFuseMonitorTokenBudget:
    """Token 预算监控测试。"""

    def setup_method(self) -> None:
        self.monitor = FuseMonitor()

    def test_check_token_budget_below_threshold(self) -> None:
        """测试低于阈值不超预算。"""
        # 阈值 ratio = 0.8
        assert self.monitor.check_token_budget(50000, 100000) is False  # 0.5
        assert self.monitor.check_token_budget(70000, 100000) is False  # 0.7
        assert self.monitor.check_token_budget(79999, 100000) is False  # 0.79999

    def test_check_token_budget_at_threshold(self) -> None:
        """测试达到阈值触发超预算。"""
        assert self.monitor.check_token_budget(80000, 100000) is True  # 0.8

    def test_check_token_budget_above_threshold(self) -> None:
        """测试超过阈值触发超预算。"""
        assert self.monitor.check_token_budget(90000, 100000) is True  # 0.9
        assert self.monitor.check_token_budget(100000, 100000) is True  # 1.0

    def test_check_token_budget_invalid_type(self) -> None:
        """测试非整数类型抛出 ValueError。"""
        with pytest.raises(ValueError, match="必须为整数"):
            self.monitor.check_token_budget(50000.5, 100000)  # type: ignore

    def test_check_token_budget_negative(self) -> None:
        """测试负数抛出 ValueError。"""
        with pytest.raises(ValueError, match="不能为负数"):
            self.monitor.check_token_budget(-1000, 100000)

    def test_check_token_budget_zero_total(self) -> None:
        """测试 total 为零抛出 ValueError。"""
        with pytest.raises(ValueError, match="不能为零"):
            self.monitor.check_token_budget(1000, 0)

    def test_get_token_usage_ratio(self) -> None:
        """测试计算 Token 使用比例。"""
        assert self.monitor.get_token_usage_ratio(50000, 100000) == 0.5
        assert self.monitor.get_token_usage_ratio(80000, 100000) == 0.8
        assert self.monitor.get_token_usage_ratio(0, 100000) == 0.0
        assert self.monitor.get_token_usage_ratio(100000, 0) == 0.0  # 保护性返回


class TestFuseMonitorErrorRoute:
    """错误路由监控测试。"""

    def setup_method(self) -> None:
        self.monitor = FuseMonitor()

    def test_check_error_route_below_threshold(self) -> None:
        """测试低于阈值不熔断。"""
        assert self.monitor.check_error_route(0) is False
        assert self.monitor.check_error_route(1) is False

    def test_check_error_route_at_threshold(self) -> None:
        """测试达到阈值触发熔断。"""
        assert self.monitor.check_error_route(2) is True

    def test_check_error_route_above_threshold(self) -> None:
        """测试超过阈值触发熔断。"""
        assert self.monitor.check_error_route(3) is True

    def test_check_error_route_invalid(self) -> None:
        """测试无效参数抛出 ValueError。"""
        with pytest.raises(ValueError, match="必须为非负整数"):
            self.monitor.check_error_route(-1)

        with pytest.raises(ValueError, match="必须为非负整数"):
            self.monitor.check_error_route(2.5)  # type: ignore

    def test_increment_error_route(self) -> None:
        """测试增加错误路由计数。"""
        assert self.monitor.increment_error_route() == 1
        assert self.monitor.increment_error_route() == 2


class TestFuseMonitorActions:
    """熔断动作测试。"""

    def setup_method(self) -> None:
        self.monitor = FuseMonitor()

    def test_get_fuse_action_valid(self) -> None:
        """测试获取有效触发类型的动作。"""
        assert self.monitor.get_fuse_action("L0") == "skip_consensus"
        assert self.monitor.get_fuse_action("L1") == "server_normalization"
        assert self.monitor.get_fuse_action("schema_fail") == "safe_mode"
        assert self.monitor.get_fuse_action("delay") == "timeout_fallback"
        assert self.monitor.get_fuse_action("token_budget") == "early_stop"

    def test_get_fuse_action_invalid(self) -> None:
        """测试无效触发类型抛出 KeyError。"""
        with pytest.raises(KeyError, match="无效的触发类型"):
            self.monitor.get_fuse_action("invalid_trigger")


class TestFuseMonitorReset:
    """计数器重置测试。"""

    def test_reset_counters(self) -> None:
        """测试重置计数器。"""
        monitor = FuseMonitor()
        monitor.increment_schema_fail()
        monitor.increment_schema_fail()
        monitor.increment_error_route()
        time.sleep(0.1)
        
        monitor.reset_counters()
        
        assert monitor.get_schema_fail_count() == 0
        assert monitor._error_route_count == 0
        assert monitor.get_elapsed_time() < 0.1  # 新计时


class TestFuseMonitorCheckAll:
    """综合状态检查测试。"""

    def test_check_all_limits_no_fuse(self) -> None:
        """测试无熔断触发的综合状态。"""
        monitor = FuseMonitor()
        status = monitor.check_all_limits(used_tokens=50000, total_tokens=100000)
        
        assert status["delay_fuse"] is False
        assert status["schema_fail_fuse"] is False
        assert status["error_route_fuse"] is False
        assert status["token_budget_fuse"] is False
        assert status["any_fuse_triggered"] is False
        assert status["recommended_action"] is None

    def test_check_all_limits_with_fuse(self) -> None:
        """测试有熔断触发的综合状态。"""
        monitor = FuseMonitor()
        monitor._schema_fail_count = 3  # 模拟达到阈值
        
        status = monitor.check_all_limits(used_tokens=85000, total_tokens=100000)
        
        assert status["schema_fail_fuse"] is True
        assert status["token_budget_fuse"] is True
        assert status["any_fuse_triggered"] is True
        assert "schema_fail" in status.get("triggered_types", [])
        assert status["recommended_action"] == "safe_mode"


class TestFuseRulesConfig:
    """熔断规则配置测试。"""

    def test_fuse_rules_structure(self) -> None:
        """测试 FUSE_RULES 结构完整性。"""
        assert "capability_levels" in FUSE_RULES
        assert "runtime" in FUSE_RULES
        assert "actions" in FUSE_RULES

    def test_capability_thresholds(self) -> None:
        """测试能力阈值配置。"""
        levels = FUSE_RULES["capability_levels"]
        assert levels["L0_threshold"] == 0.3
        assert levels["L1_threshold"] == 0.6
        assert levels["L2_threshold"] == 0.8

    def test_runtime_limits(self) -> None:
        """测试运行时限制配置。"""
        runtime = FUSE_RULES["runtime"]
        assert runtime["schema_fail_max"] == 3
        assert runtime["delay_max_seconds"] == 30
        assert runtime["error_route_max"] == 2
        assert runtime["token_budget_ratio"] == 0.8

    def test_actions_mapping(self) -> None:
        """测试动作映射配置。"""
        actions = FUSE_RULES["actions"]
        assert actions["L0"] == "skip_consensus"
        assert actions["L1"] == "server_normalization"
        assert actions["L2"] == "normal_flow"  # 高能力正常流程
        assert actions["schema_fail"] == "safe_mode"
        assert actions["delay"] == "timeout_fallback"
        assert actions["token_budget"] == "early_stop"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])