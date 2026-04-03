"""
test_routing_rules.py
测试任务路由规则模块。
"""

import pytest
from src.routing_rules import TaskRouter, route_task, TASK_CLASSES


class TestTaskRouter:
    """TaskRouter 测试用例。"""

    def setup_method(self) -> None:
        """每个测试方法前初始化路由器。"""
        self.router = TaskRouter()

    # === 正常路由测试 ===

    def test_route_simple_task_fix(self) -> None:
        """测试简单任务：修复类关键词。"""
        result = self.router.route("修复首页按钮样式问题")
        assert result["task_class"] == "simple"
        assert result["route_id"] == "direct_execution"
        assert "修复" in result["matched_keywords"]
        assert result["confidence"] > 0

    def test_route_simple_task_update(self) -> None:
        """测试简单任务：更新类关键词。"""
        result = self.router.route("更新配置文件中的数据库连接")
        assert result["task_class"] == "simple"
        assert "更新" in result["matched_keywords"]

    def test_route_moderate_task_implement(self) -> None:
        """测试中等任务：实现类关键词。"""
        result = self.router.route("实现用户认证模块")
        assert result["task_class"] == "moderate"
        assert result["route_id"] == "consensus_1_round"
        assert "实现" in result["matched_keywords"]

    def test_route_moderate_task_integrate(self) -> None:
        """测试中等任务：集成类关键词。"""
        result = self.router.route("集成第三方支付系统")
        assert result["task_class"] == "moderate"
        assert "集成" in result["matched_keywords"]

    def test_route_complex_task_architecture(self) -> None:
        """测试复杂任务：架构类关键词。"""
        result = self.router.route("重构核心架构并迁移数据库")
        # "重构" 是 moderate，"架构" 和 "迁移" 是 complex
        # 应该匹配 complex（多个关键词）
        assert result["task_class"] == "complex"
        assert result["route_id"] == "consensus_3_rounds"
        assert "架构" in result["matched_keywords"]
        assert "迁移" in result["matched_keywords"]

    def test_route_complex_task_migrate(self) -> None:
        """测试复杂任务：迁移类关键词。"""
        result = self.router.route("将系统从 MySQL 迁移到 PostgreSQL")
        assert result["task_class"] == "complex"
        assert "迁移" in result["matched_keywords"]

    # === 默认路由测试 ===

    def test_route_no_match_defaults_to_moderate(self) -> None:
        """测试无匹配关键词时默认路由到 moderate。"""
        result = self.router.route("这是一个普通的描述文本")
        assert result["task_class"] == "moderate"
        assert result["route_id"] == "consensus_1_round"
        assert result["matched_keywords"] == []
        assert result["confidence"] == 0.0
        assert "未匹配" in result["reasoning"]

    # === 多关键词测试 ===

    def test_route_multiple_keywords_same_class(self) -> None:
        """测试同一类别的多个关键词。"""
        result = self.router.route("修复并更新用户界面")
        assert result["task_class"] == "simple"
        assert len(result["matched_keywords"]) >= 2
        assert result["confidence"] > 0.1

    def test_route_keywords_from_different_classes(self) -> None:
        """测试不同类别关键词冲突时，选择匹配最多的类别。"""
        # "实现" (moderate) + "架构" (complex) = 2 keywords
        # 但如果描述中 moderate 关键词更多，应该选 moderate
        result = self.router.route("实现新功能并开发相关模块")
        assert result["task_class"] == "moderate"
        assert len(result["matched_keywords"]) >= 2

    # === 异常处理测试 ===

    def test_route_invalid_type_raises_type_error(self) -> None:
        """测试非字符串输入抛出 TypeError。"""
        with pytest.raises(TypeError, match="必须为字符串"):
            self.router.route(123)  # type: ignore

        with pytest.raises(TypeError, match="必须为字符串"):
            self.router.route(None)  # type: ignore

        with pytest.raises(TypeError, match="必须为字符串"):
            self.router.route(["修复", "bug"])  # type: ignore

    def test_route_empty_string_defaults_to_moderate(self) -> None:
        """测试空字符串默认路由到 moderate。"""
        result = self.router.route("")
        assert result["task_class"] == "moderate"
        assert result["matched_keywords"] == []

    # === 工具方法测试 ===

    def test_get_route_id_valid(self) -> None:
        """测试获取有效类别的路由 ID。"""
        assert self.router.get_route_id("simple") == "direct_execution"
        assert self.router.get_route_id("moderate") == "consensus_1_round"
        assert self.router.get_route_id("complex") == "consensus_3_rounds"

    def test_get_route_id_invalid_raises_key_error(self) -> None:
        """测试无效类别抛出 KeyError。"""
        with pytest.raises(KeyError, match="无效的任务类别"):
            self.router.get_route_id("invalid_class")

    def test_get_max_context_files_valid(self) -> None:
        """测试获取有效类别的最大上下文文件数。"""
        assert self.router.get_max_context_files("simple") == 3
        assert self.router.get_max_context_files("moderate") == 10
        assert self.router.get_max_context_files("complex") == 30

    def test_get_max_context_files_invalid_raises_key_error(self) -> None:
        """测试无效类别抛出 KeyError。"""
        with pytest.raises(KeyError, match="无效的任务类别"):
            self.router.get_max_context_files("unknown")

    # === 置信度测试 ===

    def test_confidence_calculation(self) -> None:
        """测试置信度计算。"""
        # simple 有 11 个关键词，匹配 1 个
        result = self.router.route("修复bug")
        assert result["confidence"] == pytest.approx(1 / 11, rel=0.01)

    def test_confidence_capped_at_one(self) -> None:
        """测试置信度上限为 1.0。"""
        # 即使匹配所有关键词，置信度也不应超过 1.0
        result = self.router.route("fix update change adjust modify add 修复 更新 修改 调整 添加")
        assert result["confidence"] <= 1.0

    # === 便捷函数测试 ===

    def test_route_task_convenience_function(self) -> None:
        """测试便捷函数 route_task。"""
        result = route_task("实现新功能")
        assert "route_id" in result
        assert "task_class" in result
        assert "confidence" in result
        assert result["task_class"] == "moderate"

    # === TASK_CLASSES 常量测试 ===

    def test_task_classes_structure(self) -> None:
        """测试 TASK_CLASSES 常量结构。"""
        assert "simple" in TASK_CLASSES
        assert "moderate" in TASK_CLASSES
        assert "complex" in TASK_CLASSES

        for cls_name, cls_info in TASK_CLASSES.items():
            assert "description" in cls_info
            assert "route_id" in cls_info
            assert "keywords" in cls_info
            assert "max_context_files" in cls_info
            assert isinstance(cls_info["keywords"], list)
            assert len(cls_info["keywords"]) > 0

    # === 边界情况测试 ===

    def test_route_case_insensitive(self) -> None:
        """测试关键词匹配不区分大小写。"""
        result1 = self.router.route("FIX the bug")
        result2 = self.router.route("fix the bug")
        assert result1["task_class"] == result2["task_class"] == "simple"

    def test_route_chinese_keywords(self) -> None:
        """测试中文关键词匹配。"""
        result = self.router.route("修复登录页面的样式问题")
        assert result["task_class"] == "simple"
        assert "修复" in result["matched_keywords"]

    def test_route_english_keywords(self) -> None:
        """测试英文关键词匹配。"""
        result = self.router.route("Fix the login page styling issue")
        assert result["task_class"] == "simple"
        assert "fix" in result["matched_keywords"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])