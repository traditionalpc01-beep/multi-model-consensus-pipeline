"""
fuse_monitor.py
熔断监控模块，监控运行时指标并触发熔断动作。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Literal

logger = logging.getLogger(__name__)

# 熔断规则配置
FUSE_RULES: Dict[str, Dict[str, Any]] = {
    "capability_levels": {
        "L0_threshold": 0.3,  # 低能力，跳过共识
        "L1_threshold": 0.6,  # 中能力，服务端归一化
        "L2_threshold": 0.8   # 高能力，正常流程
    },
    "runtime": {
        "schema_fail_max": 3,       # JSON Schema 连续失败上限
        "delay_max_seconds": 30,    # 单步延迟上限
        "error_route_max": 2,       # 错误路由上限
        "token_budget_ratio": 0.8   # Token预算预警比例
    },
    "actions": {
        "L0": "skip_consensus",      # 直接执行，跳过共识
        "L1": "server_normalization", # 服务端强制归一化
        "L2": "normal_flow",         # 正常共识流程（高能力）
        "schema_fail": "safe_mode",   # 安全模式输出
        "delay": "timeout_fallback",  # 超时降级
        "token_budget": "early_stop"  # 提前终止
    }
}

__all__ = ["FuseMonitor", "FUSE_RULES"]


class FuseMonitor:
    """
    熔断监控器。
    
    监控运行时指标，包括能力等级、Schema失败次数、延迟、Token预算，
    并在触发阈值时返回对应的熔断动作。
    """
    
    def __init__(self) -> None:
        """初始化熔断监控器。"""
        self._rules = FUSE_RULES
        self._schema_fail_count: int = 0
        self._error_route_count: int = 0
        self._start_time: float = time.time()
        logger.debug("FuseMonitor 初始化完成")
    
    # === 能力等级检测 ===
    
    def check_capability_level(self, score: float) -> Literal["L0", "L1", "L2"]:
        """
        根据能力分数判定等级。
        
        Args:
            score: 能力分数，范围 [0, 1]。
        
        Returns:
            能力等级：L0（低）、L1（中）、L2（高）。
        
        Raises:
            ValueError: 当 score 超出范围时抛出。
        """
        if not isinstance(score, (int, float)):
            err_msg = f"score 必须为数字，类型为 {type(score).__name__}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        if score < 0 or score > 1:
            err_msg = f"score 必须在 [0, 1] 范围内，当前值: {score}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        thresholds = self._rules["capability_levels"]
        L0_threshold = thresholds["L0_threshold"]
        L1_threshold = thresholds["L1_threshold"]
        L2_threshold = thresholds["L2_threshold"]
        
        if score < L0_threshold:
            level = "L0"
        elif score < L1_threshold:
            level = "L1"
        else:
            level = "L2"
        
        logger.info("能力等级判定 | 分数: %.2f | 等级: %s", score, level)
        return level
    
    def get_capability_action(self, level: Literal["L0", "L1", "L2"]) -> str:
        """
        获取能力等级对应的熔断动作。
        
        Args:
            level: 能力等级。
        
        Returns:
            熔断动作名称。
        
        Raises:
            KeyError: 当等级无效时抛出。
        """
        actions = self._rules["actions"]
        if level not in actions:
            err_msg = f"无效的能力等级: '{level}'。有效等级: L0, L1, L2"
            logger.error(err_msg)
            raise KeyError(err_msg)
        return actions[level]
    
    # === Schema 失败监控 ===
    
    def check_schema_fail(self, fail_count: int) -> bool:
        """
        检查 Schema 失败次数是否达到熔断阈值。
        
        Args:
            fail_count: Schema 失败次数。
        
        Returns:
            True 表示需要熔断，False 表示正常。
        
        Raises:
            ValueError: 当 fail_count 为负数时抛出。
        """
        if not isinstance(fail_count, int):
            err_msg = f"fail_count 必须为整数，类型为 {type(fail_count).__name__}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        if fail_count < 0:
            err_msg = f"fail_count 不能为负数: {fail_count}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        max_fails = self._rules["runtime"]["schema_fail_max"]
        should_fuse = fail_count >= max_fails
        
        if should_fuse:
            logger.warning(
                "Schema 失败熔断触发 | 失败次数: %d | 阈值: %d",
                fail_count, max_fails
            )
        
        return should_fuse
    
    def increment_schema_fail(self) -> int:
        """
        增加 Schema 失败计数。
        
        Returns:
            当前失败计数。
        """
        self._schema_fail_count += 1
        logger.debug("Schema 失败计数增加: %d", self._schema_fail_count)
        return self._schema_fail_count
    
    def get_schema_fail_count(self) -> int:
        """获取当前 Schema 失败计数。"""
        return self._schema_fail_count
    
    # === 延迟监控 ===
    
    def check_delay(self, elapsed_seconds: float) -> bool:
        """
        检查延迟是否超过阈值。
        
        Args:
            elapsed_seconds: 已耗时（秒）。
        
        Returns:
            True 表示超时需熔断，False 表示正常。
        
        Raises:
            ValueError: 当 elapsed_seconds 为负数时抛出。
        """
        if not isinstance(elapsed_seconds, (int, float)):
            err_msg = f"elapsed_seconds 必须为数字，类型为 {type(elapsed_seconds).__name__}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        if elapsed_seconds < 0:
            err_msg = f"elapsed_seconds 不能为负数: {elapsed_seconds}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        max_delay = self._rules["runtime"]["delay_max_seconds"]
        is_timeout = elapsed_seconds >= max_delay
        
        if is_timeout:
            logger.warning(
                "延迟熔断触发 | 耗时: %.1fs | 阈值: %ds",
                elapsed_seconds, max_delay
            )
        
        return is_timeout
    
    def get_elapsed_time(self) -> float:
        """获取从初始化到现在的耗时（秒）。"""
        return time.time() - self._start_time
    
    # === Token 预算监控 ===
    
    def check_token_budget(self, used: int, total: int) -> bool:
        """
        检查 Token 使用是否超过预算比例。
        
        Args:
            used: 已使用的 Token 数量。
            total: 总 Token 预算。
        
        Returns:
            True 表示超预算需熔断，False 表示正常。
        
        Raises:
            ValueError: 当参数无效时抛出。
        """
        if not isinstance(used, int) or not isinstance(total, int):
            err_msg = "used 和 total 必须为整数"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        if used < 0 or total < 0:
            err_msg = f"used 和 total 不能为负数: used={used}, total={total}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        if total == 0:
            err_msg = "total 不能为零"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        ratio = self._rules["runtime"]["token_budget_ratio"]
        current_ratio = used / total
        is_over_budget = current_ratio >= ratio
        
        if is_over_budget:
            logger.warning(
                "Token 预算熔断触发 | 已用: %d | 总量: %d | 比例: %.2f | 阈值: %.2f",
                used, total, current_ratio, ratio
            )
        
        return is_over_budget
    
    def get_token_usage_ratio(self, used: int, total: int) -> float:
        """计算 Token 使用比例。"""
        if total == 0:
            return 0.0
        return used / total
    
    # === 错误路由监控 ===
    
    def check_error_route(self, error_count: int) -> bool:
        """
        检查错误路由次数是否达到熔断阈值。
        
        Args:
            error_count: 错误路由次数。
        
        Returns:
            True 表示需要熔断，False 表示正常。
        """
        if not isinstance(error_count, int) or error_count < 0:
            err_msg = f"error_count 必须为非负整数: {error_count}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        max_errors = self._rules["runtime"]["error_route_max"]
        should_fuse = error_count >= max_errors
        
        if should_fuse:
            logger.warning(
                "错误路由熔断触发 | 错误次数: %d | 阈值: %d",
                error_count, max_errors
            )
        
        return should_fuse
    
    def increment_error_route(self) -> int:
        """增加错误路由计数。"""
        self._error_route_count += 1
        logger.debug("错误路由计数增加: %d", self._error_route_count)
        return self._error_route_count
    
    # === 熔断动作 ===
    
    def get_fuse_action(self, trigger_type: str) -> str:
        """
        获取熔断触发类型对应的动作。
        
        Args:
            trigger_type: 触发类型，如 'schema_fail', 'delay', 'token_budget'。
        
        Returns:
            熔断动作名称。
        
        Raises:
            KeyError: 当触发类型无效时抛出。
        """
        actions = self._rules["actions"]
        if trigger_type not in actions:
            err_msg = f"无效的触发类型: '{trigger_type}'。有效类型: {list(actions.keys())}"
            logger.error(err_msg)
            raise KeyError(err_msg)
        return actions[trigger_type]
    
    # === 计数器管理 ===
    
    def reset_counters(self) -> None:
        """重置所有计数器和计时器。"""
        self._schema_fail_count = 0
        self._error_route_count = 0
        self._start_time = time.time()
        logger.info("熔断监控器计数器已重置")
    
    # === 综合状态检查 ===
    
    def check_all_limits(self, used_tokens: int = 0, total_tokens: int = 100000) -> Dict[str, Any]:
        """
        综合检查所有限制条件。
        
        Args:
            used_tokens: 已使用的 Token 数量。
            total_tokens: 总 Token 预算。
        
        Returns:
            综合状态报告字典，包含各指标的检查结果。
        """
        elapsed = self.get_elapsed_time()
        status: Dict[str, Any] = {
            "elapsed_seconds": elapsed,
            "delay_fuse": self.check_delay(elapsed),
            "schema_fail_count": self._schema_fail_count,
            "schema_fail_fuse": self.check_schema_fail(self._schema_fail_count),
            "error_route_count": self._error_route_count,
            "error_route_fuse": self.check_error_route(self._error_route_count),
            "token_used": used_tokens,
            "token_total": total_tokens,
            "token_budget_fuse": self.check_token_budget(used_tokens, total_tokens),
            "any_fuse_triggered": False,
            "recommended_action": None
        }
        
        # 检查是否有任何熔断触发
        triggers = []
        if status["delay_fuse"]:
            triggers.append("delay")
        if status["schema_fail_fuse"]:
            triggers.append("schema_fail")
        if status["error_route_fuse"]:
            triggers.append("error_route")
        if status["token_budget_fuse"]:
            triggers.append("token_budget")
        
        status["any_fuse_triggered"] = len(triggers) > 0
        if triggers:
            status["triggered_types"] = triggers
            # 优先返回第一个触发的动作
            status["recommended_action"] = self.get_fuse_action(triggers[0])
        
        logger.info("综合状态检查完成 | 熔断触发: %s | 触发类型: %s", 
                   status["any_fuse_triggered"], triggers if triggers else "无")
        
        return status


if __name__ == "__main__":
    # 配置日志以便独立运行测试
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    monitor = FuseMonitor()
    
    print("=" * 60)
    print("FuseMonitor 测试")
    print("=" * 60)
    
    # 测试能力等级
    print("\n--- 能力等级测试 ---")
    for score in [0.2, 0.5, 0.9]:
        level = monitor.check_capability_level(score)
        action = monitor.get_capability_action(level)
        print(f"score={score:.1f} -> level={level} -> action={action}")
    
    # 测试 Schema 失败
    print("\n--- Schema 失败测试 ---")
    for count in [1, 2, 3, 4]:
        should_fuse = monitor.check_schema_fail(count)
        print(f"fail_count={count} -> should_fuse={should_fuse}")
    
    # 测试延迟
    print("\n--- 延迟测试 ---")
    monitor.reset_counters()
    import time as test_time
    test_time.sleep(0.5)  # 短暂等待
    elapsed = monitor.get_elapsed_time()
    print(f"elapsed={elapsed:.2f}s -> is_timeout={monitor.check_delay(elapsed)}")
    
    # 测试 Token 预算
    print("\n--- Token 预算测试 ---")
    for used, total in [(50000, 100000), (80000, 100000), (90000, 100000)]:
        ratio = monitor.get_token_usage_ratio(used, total)
        is_over = monitor.check_token_budget(used, total)
        print(f"used={used}, total={total} -> ratio={ratio:.2f} -> is_over={is_over}")
    
    # 测试综合状态
    print("\n--- 综合状态检查 ---")
    monitor.reset_counters()
    monitor._schema_fail_count = 3  # 模拟达到阈值
    status = monitor.check_all_limits(used_tokens=85000, total_tokens=100000)
    print(f"any_fuse_triggered: {status['any_fuse_triggered']}")
    print(f"triggered_types: {status.get('triggered_types', [])}")
    print(f"recommended_action: {status['recommended_action']}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)