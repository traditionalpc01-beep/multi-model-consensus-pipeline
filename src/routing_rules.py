"""
routing_rules.py
任务路由规则模块，用于根据任务描述自动分级路由。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

TASK_CLASSES: Dict[str, Dict[str, Any]] = {
    "simple": {
        "description": "简单任务（单文件修改、小范围调整）",
        "route_id": "direct_execution",
        "keywords": ["fix", "update", "change", "adjust", "modify", "add", "修复", "更新", "修改", "调整", "添加"],
        "max_context_files": 3
    },
    "moderate": {
        "description": "中等任务（多文件修改、新功能添加）",
        "route_id": "consensus_1_round",
        "keywords": ["implement", "build", "develop", "integrate", "refactor", "实现", "开发", "集成", "重构"],
        "max_context_files": 10
    },
    "complex": {
        "description": "复杂任务（架构变更、核心模块重构）",
        "route_id": "consensus_3_rounds",
        "keywords": ["architecture", "rewrite", "replace", "migrate", "core", "架构", "替换", "迁移", "核心", "重写"],
        "max_context_files": 30
    }
}

__all__ = ["TaskRouter", "route_task", "TASK_CLASSES"]


class TaskRouter:
    """任务路由器。根据任务描述文本进行关键词匹配并自动分级路由。"""

    def __init__(self) -> None:
        """初始化路由规则。"""
        self._rules = TASK_CLASSES
        logger.debug("TaskRouter 初始化完成，加载 %d 个路由规则", len(self._rules))

    def route(self, task_description: str) -> Dict[str, Any]:
        """
        根据任务描述进行路由判断。

        Args:
            task_description: 任务描述文本。

        Returns:
            路由结果字典，包含 route_id, task_class, confidence, reasoning,
            matched_keywords, max_context_fields 字段。

        Raises:
            TypeError: 当 task_description 不是字符串类型时抛出。
            RuntimeError: 当路由规则处理失败时抛出。
        """
        if not isinstance(task_description, str):
            err_msg = f"task_description 必须为字符串，类型为 {type(task_description).__name__}"
            logger.error(err_msg)
            raise TypeError(err_msg)

        try:
            desc_lower = task_description.lower()
            match_records: List[Tuple[str, List[str]]] = []
            any_match = False

            for cls_name, cls_info in self._rules.items():
                keywords: List[str] = cls_info["keywords"]
                matched: List[str] = [kw for kw in keywords if kw.lower() in desc_lower]
                if len(matched) > 0:
                    any_match = True
                match_records.append((cls_name, matched))

            # 按匹配次数降序排序，次数相同时按规则定义顺序保持
            match_records.sort(key=lambda x: len(x[1]), reverse=True)
            best_class, matched_keywords = match_records[0]

            # 无匹配时默认返回 moderate
            if not any_match or len(matched_keywords) == 0:
                best_class = "moderate"
                matched_keywords = []

            # 计算置信度
            total_keywords = len(self._rules[best_class]["keywords"])
            confidence = len(matched_keywords) / total_keywords if total_keywords > 0 else 0.0
            confidence = min(1.0, max(0.0, confidence))  # 确保范围在 [0, 1]

            # 生成推理说明
            if not any_match:
                reasoning = "未匹配到任何预定义关键词，根据规则默认路由至中等任务。"
            else:
                kw_display = ", ".join(f"'{kw}'" for kw in matched_keywords)
                reasoning = (
                    f"匹配到 {best_class} 类关键词 ({len(matched_keywords)}/{total_keywords}): "
                    f"{kw_display}。"
                )

            result: Dict[str, Any] = {
                "route_id": self.get_route_id(best_class),
                "task_class": best_class,
                "confidence": round(confidence, 4),
                "reasoning": reasoning,
                "matched_keywords": matched_keywords,
                "max_context_files": self.get_max_context_files(best_class)
            }
            logger.info(
                "路由决策完成 | 任务类: %s | 路由ID: %s | 置信度: %.2f",
                result["task_class"],
                result["route_id"],
                result["confidence"]
            )
            return result

        except Exception as e:
            logger.exception("路由处理过程中发生未知错误: %s", e)
            raise RuntimeError(f"路由处理失败: {e}") from e

    def get_route_id(self, task_class: str) -> str:
        """
        获取任务类对应的路由ID。

        Args:
            task_class: 任务类别名称 ("simple", "moderate", "complex")。

        Returns:
            路由ID字符串。

        Raises:
            KeyError: 当任务类别不存在时抛出。
        """
        if task_class not in self._rules:
            err_msg = f"无效的任务类别: '{task_class}'。有效类别: {list(self._rules.keys())}"
            logger.warning(err_msg)
            raise KeyError(err_msg)
        return self._rules[task_class]["route_id"]

    def get_max_context_files(self, task_class: str) -> int:
        """
        获取任务类对应的最大上下文文件数。

        Args:
            task_class: 任务类别名称 ("simple", "moderate", "complex")。

        Returns:
            最大上下文文件数量。

        Raises:
            KeyError: 当任务类别不存在时抛出。
        """
        if task_class not in self._rules:
            err_msg = f"无效的任务类别: '{task_class}'。有效类别: {list(self._rules.keys())}"
            logger.warning(err_msg)
            raise KeyError(err_msg)
        return self._rules[task_class]["max_context_files"]


def route_task(task_description: str) -> Dict[str, Any]:
    """
    便捷函数：路由任务。

    Args:
        task_description: 任务描述文本。

    Returns:
        路由结果字典。

    Raises:
        TypeError, RuntimeError: 继承自 TaskRouter.route 的异常。
    """
    router = TaskRouter()
    return router.route(task_description)


if __name__ == "__main__":
    # 配置基础日志以便独立运行测试
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    test_cases = [
        "修复首页按钮样式错乱的问题",
        "实现用户认证模块并集成第三方登录",
        "将核心数据架构从 SQLite 迁移到 PostgreSQL",
        "这是一个没有明显技术词汇的普通描述",
    ]

    for idx, desc in enumerate(test_cases):
        print(f"\n{'='*40}\n测试用例 {idx+1}: {desc}\n{'-'*40}")
        try:
            result = route_task(desc)
            for key, val in result.items():
                print(f"  {key:.<20} {val}")
        except Exception as e:
            logger.error("执行失败: %s", e)
            print(f"  捕获异常: {e}")