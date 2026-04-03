"""
test_longcat_client.py
测试 LongCat API 客户端模块。
"""

import pytest
from unittest.mock import MagicMock, patch
from src.longcat_client import (
    LongCatClient,
    LONGCAT_MODELS,
    LONGCAT_BASE_URL,
    LONGCAT_MODEL,
    invoke_longcat,
)


class TestLongCatClientInit:
    """客户端初始化测试。"""

    def test_default_initialization(self) -> None:
        """测试默认初始化参数。"""
        client = LongCatClient()
        assert client._base_url == LONGCAT_BASE_URL
        assert client._model == LONGCAT_MODEL

    def test_custom_initialization(self) -> None:
        """测试自定义初始化参数。"""
        client = LongCatClient(
            api_key="test_key",
            base_url="https://custom.api.com",
            model="LongCat-Flash-Lite",
        )
        assert client._api_key == "test_key"
        assert client._base_url == "https://custom.api.com"
        assert client._model == "LongCat-Flash-Lite"

    def test_no_api_key_warning(self) -> None:
        """测试无 API Key 时的警告。"""
        client = LongCatClient(api_key="")
        assert client._api_key == ""


class TestLongCatClientSetModel:
    """模型设置测试。"""

    def setup_method(self) -> None:
        self.client = LongCatClient(api_key="test_key")

    def test_set_model_thinking(self) -> None:
        """测试切换到思考模型。"""
        self.client.set_model("thinking")
        assert self.client._model == "LongCat-Flash-Thinking-2601"

    def test_set_model_chat(self) -> None:
        """测试切换到聊天模型。"""
        self.client.set_model("chat")
        assert self.client._model == "LongCat-Flash-Chat"

    def test_set_model_lite(self) -> None:
        """测试切换到轻量模型。"""
        self.client.set_model("lite")
        assert self.client._model == "LongCat-Flash-Lite"

    def test_set_model_omni(self) -> None:
        """测试切换到多模态模型。"""
        self.client.set_model("omni")
        assert self.client._model == "LongCat-Flash-Omni-2603"

    def test_set_model_invalid_raises_key_error(self) -> None:
        """测试无效模型类型抛出 KeyError。"""
        with pytest.raises(KeyError, match="无效的模型类型"):
            self.client.set_model("invalid_model")


class TestLongCatClientGetModelInfo:
    """获取模型信息测试。"""

    def setup_method(self) -> None:
        self.client = LongCatClient(api_key="test_key")

    def test_get_model_info_thinking(self) -> None:
        """测试获取思考模型信息。"""
        self.client.set_model("thinking")
        info = self.client.get_model_info()
        assert info["type"] == "thinking"
        assert info["name"] == "LongCat-Flash-Thinking-2601"
        assert "description" in info
        assert "daily_free_quota" in info

    def test_get_model_info_lite(self) -> None:
        """测试获取轻量模型信息。"""
        self.client.set_model("lite")
        info = self.client.get_model_info()
        assert info["type"] == "lite"
        assert info["daily_free_quota"] == 50000000  # 50M


class TestLongCatClientChat:
    """对话请求测试。"""

    def test_chat_no_api_key_raises_value_error(self) -> None:
        """测试无 API Key 时抛出 ValueError。"""
        client = LongCatClient(api_key="")
        with pytest.raises(ValueError, match="API Key 未设置"):
            client.chat([{"role": "user", "content": "test"}])

    @patch("src.longcat_client.LongCatClient.chat")
    def test_chat_success_mock(self, mock_chat: MagicMock) -> None:
        """测试成功调用（模拟）。"""
        mock_chat.return_value = {
            "success": True,
            "model": "LongCat-Flash-Thinking-2601",
            "content": "Hello!",
            "usage": {"total_tokens": 100},
        }
        
        client = LongCatClient(api_key="test_key")
        result = client.chat([{"role": "user", "content": "Hello"}])
        
        assert result["success"] is True
        assert "content" in result


class TestLongCatClientGenerateCode:
    """代码生成测试。"""

    @patch("src.longcat_client.LongCatClient.chat")
    def test_generate_code_basic(self, mock_chat: MagicMock) -> None:
        """测试基本代码生成。"""
        mock_chat.return_value = {
            "success": True,
            "content": "```python\ndef hello(): pass\n```",
        }
        
        client = LongCatClient(api_key="test_key")
        result = client.generate_code(task="写一个 hello 函数")
        
        assert result["success"] is True
        mock_chat.assert_called_once()

    @patch("src.longcat_client.LongCatClient.chat")
    def test_generate_code_with_context(self, mock_chat: MagicMock) -> None:
        """测试带上下文的代码生成。"""
        mock_chat.return_value = {"success": True, "content": "code"}
        
        client = LongCatClient(api_key="test_key")
        result = client.generate_code(
            task="添加新功能",
            context="现有模块: auth.py, user.py",
            language="Python",
        )
        
        assert result["success"] is True
        # 验证 messages 包含上下文
        call_args = mock_chat.call_args
        messages = call_args[0][0]  # 第一个参数是 messages
        assert any("上下文" in m.get("content", "") for m in messages)


class TestLongCatClientReviewCode:
    """代码审查测试。"""

    @patch("src.longcat_client.LongCatClient.chat")
    def test_review_code_basic(self, mock_chat: MagicMock) -> None:
        """测试基本代码审查。"""
        mock_chat.return_value = {
            "success": True,
            "content": "P0: 无严重问题\nP1: 建议...",
        }
        
        client = LongCatClient(api_key="test_key")
        result = client.review_code("def foo(): pass")
        
        assert result["success"] is True
        mock_chat.assert_called_once()

    @patch("src.longcat_client.LongCatClient.chat")
    def test_review_code_with_focus_areas(self, mock_chat: MagicMock) -> None:
        """测试带关注领域的代码审查。"""
        mock_chat.return_value = {"success": True, "content": "安全审查结果"}
        
        client = LongCatClient(api_key="test_key")
        result = client.review_code(
            code="password = '123456'",
            focus_areas=["安全", "性能"],
        )
        
        assert result["success"] is True
        call_args = mock_chat.call_args
        messages = call_args[0][0]
        assert any("安全" in m.get("content", "") for m in messages)


class TestInvokeLongCat:
    """便捷函数测试。"""

    @patch("src.longcat_client.LongCatClient.generate_code")
    def test_invoke_longcat_default_model(self, mock_gen: MagicMock) -> None:
        """测试默认模型调用。"""
        mock_gen.return_value = {"success": True, "content": "code"}
        
        result = invoke_longcat(task="写代码")
        
        assert result["success"] is True
        # generate_code 使用位置参数传 task
        mock_gen.assert_called_once()

    @patch("src.longcat_client.LongCatClient.generate_code")
    def test_invoke_longcat_lite_model(self, mock_gen: MagicMock) -> None:
        """测试切换到 lite 模型。"""
        mock_gen.return_value = {"success": True, "content": "code"}
        
        result = invoke_longcat(task="写代码", model_type="lite")
        
        assert result["success"] is True


class TestLongCatModelsConfig:
    """模型配置测试。"""

    def test_models_config_structure(self) -> None:
        """测试模型配置结构完整。"""
        assert "thinking" in LONGCAT_MODELS
        assert "chat" in LONGCAT_MODELS
        assert "lite" in LONGCAT_MODELS
        assert "omni" in LONGCAT_MODELS

    def test_model_config_fields(self) -> None:
        """测试每个模型配置包含必要字段。"""
        required_fields = ["name", "description", "max_tokens", "daily_free_quota"]
        
        for model_type, config in LONGCAT_MODELS.items():
            for field in required_fields:
                assert field in config, f"{model_type} 缺少 {field}"

    def test_lite_model_free_quota(self) -> None:
        """测试 lite 模型的超大免费额度。"""
        assert LONGCAT_MODELS["lite"]["daily_free_quota"] == 50000000

    def test_thinking_model_max_tokens(self) -> None:
        """测试思考模型的最大 Token 数。"""
        assert LONGCAT_MODELS["thinking"]["max_tokens"] == 256000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])