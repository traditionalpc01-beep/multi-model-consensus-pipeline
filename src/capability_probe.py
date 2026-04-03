"""
capability_probe.py
能力探测模块，用于检测基础模型的能力级别并选择合适的执行路径。

能力分级：
- L2 (High): 高能力，正常流程（完整共识）
- L1 (Medium): 中能力，服务端归一化
- L0 (Low): 低能力，跳过共识，直接执行
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CapabilityLevel(Enum):
    """能力级别枚举。"""
    L0 = "L0"  # 低能力
    L1 = "L1"  # 中能力
    L2 = "L2"  # 高能力


@dataclass
class ProbeResult:
    """探测结果。"""
    level: CapabilityLevel
    score: float
    passed_tests: List[str]
    failed_tests: List[str]
    latency_ms: float
    error_message: Optional[str] = None


@dataclass
class CapabilityTest:
    """能力测试定义。"""
    name: str
    description: str
    prompt: str
    validator: Callable[[str], bool]
    weight: float = 1.0


# 能力测试提示词
CAPABILITY_TEST_PROMPTS: Dict[str, str] = {
    "json_parsing": """
请分析以下任务，并返回 JSON 格式的分析结果。
任务：实现用户登录功能
要求 JSON 格式：
{
    "opinion": "string",
    "key_points": ["string"],
    "concerns": ["string"],
    "suggestions": ["string"],
    "feasibility": "high|medium|low"
}
只返回 JSON，不要其他文字。
""",
    "closed_choice": """
请从以下选项中选择最适合的路由：
选项：
A. direct_execution
B. consensus_1_round
C. consensus_3_rounds

任务描述：修复一个简单的按钮样式问题
请只返回选项字母（A/B/C）。
""",
    "schema_compliance": """
请生成符合以下 JSON Schema 的数据：
{
    "type": "object",
    "required": ["route_id", "task_class", "next_action"],
    "properties": {
        "route_id": {"type": "string", "enum": ["direct_execution", "consensus_1_round", "consensus_3_rounds"]},
        "task_class": {"type": "string", "enum": ["simple", "moderate", "complex"]},
        "next_action": {"type": "string", "enum": ["analyze", "execute", "fallback"]}
    }
}
任务：实现中等复杂度的功能模块
只返回 JSON。
""",
    "reasoning": """
请分析以下任务并给出关键要点：
任务：将项目从 SQLite 迁移到 PostgreSQL
请用 3-5 个要点说明关键考虑因素，每行一个要点。
"""
}


def _validate_json_parsing(response: str) -> bool:
    """验证 JSON 解析能力。"""
    try:
        content = response.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        data = json.loads(content)
        required_fields = ["opinion", "key_points", "concerns", "suggestions", "feasibility"]
        return all(field in data for field in required_fields)
    except Exception:
        return False


def _validate_closed_choice(response: str) -> bool:
    """验证封闭选项选择能力。"""
    content = response.strip().upper()
    return content in ["A", "B", "C", "DIRECT_EXECUTION", "CONSENSUS_1_ROUND", "CONSENSUS_3_ROUNDS"]


def _validate_schema_compliance(response: str) -> bool:
    """验证 Schema 合规能力。"""
    try:
        content = response.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        data = json.loads(content)
        required_fields = ["route_id", "task_class", "next_action"]
        if not all(field in data for field in required_fields):
            return False
        valid_routes = ["direct_execution", "consensus_1_round", "consensus_3_rounds"]
        valid_classes = ["simple", "moderate", "complex"]
        valid_actions = ["analyze", "execute", "fallback"]
        return (
            data["route_id"] in valid_routes
            and data["task_class"] in valid_classes
            and data["next_action"] in valid_actions
        )
    except Exception:
        return False


def _validate_reasoning(response: str) -> bool:
    """验证推理能力。"""
    lines = [line.strip() for line in response.splitlines() if line.strip()]
    return 3 <= len(lines) <= 10


# 能力测试定义
CAPABILITY_TESTS: List[CapabilityTest] = [
    CapabilityTest(
        name="json_parsing",
        description="JSON 解析和结构化输出能力",
        prompt=CAPABILITY_TEST_PROMPTS["json_parsing"],
        validator=_validate_json_parsing,
        weight=0.35,
    ),
    CapabilityTest(
        name="closed_choice",
        description="封闭选项选择能力",
        prompt=CAPABILITY_TEST_PROMPTS["closed_choice"],
        validator=_validate_closed_choice,
        weight=0.25,
    ),
    CapabilityTest(
        name="schema_compliance",
        description="JSON Schema 合规能力",
        prompt=CAPABILITY_TEST_PROMPTS["schema_compliance"],
        validator=_validate_schema_compliance,
        weight=0.25,
    ),
    CapabilityTest(
        name="reasoning",
        description="基础推理和要点提取能力",
        prompt=CAPABILITY_TEST_PROMPTS["reasoning"],
        validator=_validate_reasoning,
        weight=0.15,
    ),
]


class CapabilityProbe:
    """
    能力探测器。
    
    通过一系列测试评估模型的能力级别，并选择合适的执行路径。
    """
    
    # 能力级别阈值
    L2_THRESHOLD = 0.80
    L1_THRESHOLD = 0.50
    
    def __init__(
        self,
        tests: Optional[List[CapabilityTest]] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        """
        初始化能力探测器。
        
        Args:
            tests: 自定义测试列表，默认使用内置测试
            timeout_seconds: 单测试超时时间
        """
        self._tests = tests or CAPABILITY_TESTS
        self._timeout = timeout_seconds
        logger.debug("CapabilityProbe 初始化完成，加载 %d 个测试", len(self._tests))
    
    def probe(
        self,
        model_call: Callable[[str], str],
        model_name: str = "unknown",
    ) -> ProbeResult:
        """
        执行能力探测。
        
        Args:
            model_call: 调用模型的函数，接收 prompt 返回 response
            model_name: 模型名称，用于日志
            
        Returns:
            ProbeResult 包含探测结果
        """
        start_time = time.time()
        passed: List[str] = []
        failed: List[str] = []
        total_score = 0.0
        total_weight = 0.0
        error_message: Optional[str] = None
        
        logger.info("开始能力探测 | model=%s | tests=%d", model_name, len(self._tests))
        
        for test in self._tests:
            test_start = time.time()
            try:
                response = model_call(test.prompt)
                is_passed = test.validator(response)
                
                if is_passed:
                    passed.append(test.name)
                    total_score += test.weight
                    logger.debug(
                        "测试通过 | test=%s | weight=%.2f",
                        test.name, test.weight
                    )
                else:
                    failed.append(test.name)
                    logger.debug(
                        "测试失败 | test=%s",
                        test.name
                    )
                
                total_weight += test.weight
                
            except Exception as exc:
                failed.append(test.name)
                total_weight += test.weight
                error_message = f"测试 {test.name} 异常: {str(exc)}"
                logger.exception("能力探测测试异常 | test=%s", test.name)
        
        # 计算最终得分
        score = total_score / total_weight if total_weight > 0 else 0.0
        
        # 判定能力级别
        if score >= self.L2_THRESHOLD:
            level = CapabilityLevel.L2
        elif score >= self.L1_THRESHOLD:
            level = CapabilityLevel.L1
        else:
            level = CapabilityLevel.L0
        
        latency_ms = (time.time() - start_time) * 1000
        
        result = ProbeResult(
            level=level,
            score=score,
            passed_tests=passed,
            failed_tests=failed,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        
        logger.info(
            "能力探测完成 | model=%s | level=%s | score=%.2f | passed=%d | failed=%d | latency=%.0fms",
            model_name, level.value, score, len(passed), len(failed), latency_ms
        )
        
        return result
    
    def get_execution_path(self, level: CapabilityLevel) -> str:
        """
        根据能力级别获取执行路径。
        
        Args:
            level: 能力级别
            
        Returns:
            执行路径标识符
        """
        path_map = {
            CapabilityLevel.L0: "skip_consensus",
            CapabilityLevel.L1: "server_normalization",
            CapabilityLevel.L2: "normal_flow",
        }
        return path_map.get(level, "normal_flow")
    
    def get_test_names(self) -> List[str]:
        """获取所有测试名称。"""
        return [test.name for test in self._tests]


def probe_capability(
    model_call: Callable[[str], str],
    model_name: str = "unknown",
) -> ProbeResult:
    """
    便捷函数：执行能力探测。
    
    Args:
        model_call: 调用模型的函数
        model_name: 模型名称
        
    Returns:
        ProbeResult 探测结果
    """
    probe = CapabilityProbe()
    return probe.probe(model_call, model_name)


def get_capability_action(score: float) -> Tuple[CapabilityLevel, str]:
    """
    根据能力分数获取对应的能力级别和动作。
    
    Args:
        score: 能力分数 [0, 1]
        
    Returns:
        (能力级别, 动作名称)
    """
    probe = CapabilityProbe()
    if score >= probe.L2_THRESHOLD:
        level = CapabilityLevel.L2
    elif score >= probe.L1_THRESHOLD:
        level = CapabilityLevel.L1
    else:
        level = CapabilityLevel.L0
    return level, probe.get_execution_path(level)


__all__ = [
    "CapabilityLevel",
    "ProbeResult",
    "CapabilityTest",
    "CapabilityProbe",
    "CAPABILITY_TEST_PROMPTS",
    "CAPABILITY_TESTS",
    "probe_capability",
    "get_capability_action",
]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("=" * 60)
    print("CapabilityProbe 测试")
    print("=" * 60)
    
    # 测试探测器初始化
    print("\n--- 测试初始化 ---")
    probe = CapabilityProbe()
    print(f"测试数量: {len(probe.get_test_names())}")
    print(f"测试名称: {probe.get_test_names()}")
    
    # 模拟模型调用（总是通过）
    print("\n--- 模拟高能力模型 ---")
    def mock_high_capability(prompt: str) -> str:
        if "json_parsing" in CAPABILITY_TEST_PROMPTS["json_parsing"]:
            return json.dumps({
                "opinion": "可行",
                "key_points": ["点1", "点2"],
                "concerns": [],
                "suggestions": [],
                "feasibility": "high"
            })
        elif "closed_choice" in prompt:
            return "A"
        elif "schema_compliance" in prompt:
            return json.dumps({
                "route_id": "direct_execution",
                "task_class": "simple",
                "next_action": "execute"
            })
        else:
            return "要点1\n要点2\n要点3"
    
    result_high = probe.probe(mock_high_capability, "high_model")
    print(f"级别: {result_high.level.value}")
    print(f"分数: {result_high.score:.2f}")
    print(f"通过: {result_high.passed_tests}")
    print(f"失败: {result_high.failed_tests}")
    print(f"执行路径: {probe.get_execution_path(result_high.level)}")
    
    # 模拟低能力模型
    print("\n--- 模拟低能力模型 ---")
    def mock_low_capability(prompt: str) -> str:
        return "我不确定，让我想想..."
    
    result_low = probe.probe(mock_low_capability, "low_model")
    print(f"级别: {result_low.level.value}")
    print(f"分数: {result_low.score:.2f}")
    print(f"通过: {result_low.passed_tests}")
    print(f"失败: {result_low.failed_tests}")
    print(f"执行路径: {probe.get_execution_path(result_low.level)}")
    
    # 测试便捷函数
    print("\n--- 测试便捷函数 ---")
    for score in [0.2, 0.5, 0.9]:
        level, action = get_capability_action(score)
        print(f"score={score:.1f} -> level={level.value}, action={action}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
