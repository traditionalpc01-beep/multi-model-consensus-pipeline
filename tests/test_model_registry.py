"""
test_model_registry.py
测试通用模型注册中心。
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from src.model_registry import (
    ModelCapability,
    ModelStatus,
    ModelConfig,
    ModelHealth,
    ModelRegistry,
    OpenAICompatibleProvider,
    CodexCLIProvider,
    registry,
)


class TestModelConfig:
    """模型配置测试。"""

    def test_model_config_creation(self) -> None:
        """测试模型配置创建。"""
        config = ModelConfig(
            name="test_model",
            display_name="Test Model",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="TEST_API_KEY",
            model_id="test-v1",
            capabilities=[ModelCapability.CODE_GENERATION],
            max_tokens=4096,
            priority=100,
        )
        assert config.name == "test_model"
        assert config.provider == "test"
        assert config.enabled is True
        assert len(config.capabilities) == 1

    def test_model_config_with_multiple_capabilities(self) -> None:
        """测试多能力配置。"""
        config = ModelConfig(
            name="multi_model",
            display_name="Multi",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="TEST_API_KEY",
            model_id="multi-v1",
            capabilities=[
                ModelCapability.CODE_GENERATION,
                ModelCapability.ANALYSIS,
                ModelCapability.CONSENSUS,
            ],
        )
        assert len(config.capabilities) == 3


class TestModelHealth:
    """模型健康状态测试。"""

    def test_model_health_available(self) -> None:
        """测试可用状态。"""
        health = ModelHealth(
            name="test",
            status=ModelStatus.AVAILABLE,
            last_check=0,
            latency_ms=100,
        )
        assert health.status == ModelStatus.AVAILABLE
        assert health.error_message == ""

    def test_model_health_error(self) -> None:
        """测试错误状态。"""
        health = ModelHealth(
            name="test",
            status=ModelStatus.ERROR,
            last_check=0,
            error_message="API Key 未设置",
        )
        assert health.status == ModelStatus.ERROR
        assert "API Key" in health.error_message


class TestOpenAICompatibleProvider:
    """OpenAI 兼容提供者测试。"""

    def test_provider_initialization(self) -> None:
        """测试提供者初始化。"""
        config = ModelConfig(
            name="test",
            display_name="Test",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="TEST_API_KEY",
            model_id="test-v1",
            capabilities=[ModelCapability.ALL],
        )
        provider = OpenAICompatibleProvider(config)
        assert provider.get_config().name == "test"

    def test_provider_no_api_key(self) -> None:
        """测试无 API Key 时的错误响应。"""
        config = ModelConfig(
            name="test",
            display_name="Test",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="NONEXISTENT_KEY",
            model_id="test-v1",
            capabilities=[ModelCapability.ALL],
        )
        provider = OpenAICompatibleProvider(config)
        result = provider.chat([{"role": "user", "content": "test"}])
        assert result["success"] is False
        assert "API Key" in result["error"]

    def test_provider_health_check_no_key(self) -> None:
        """测试无 API Key 的健康检查。"""
        config = ModelConfig(
            name="test",
            display_name="Test",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="NONEXISTENT_KEY",
            model_id="test-v1",
            capabilities=[ModelCapability.ALL],
        )
        provider = OpenAICompatibleProvider(config)
        health = provider.health_check()
        assert health.status == ModelStatus.ERROR

    @patch("src.model_registry.OpenAICompatibleProvider._get_client")
    def test_provider_chat_success(self, mock_client: MagicMock) -> None:
        """测试成功调用（模拟）。"""
        config = ModelConfig(
            name="test",
            display_name="Test",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="TEST_KEY",
            model_id="test-v1",
            capabilities=[ModelCapability.ALL],
        )
        
        # 设置环境变量
        os.environ["TEST_KEY"] = "fake_key"
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        
        mock_client.return_value.chat.completions.create.return_value = mock_response
        
        provider = OpenAICompatibleProvider(config)
        provider._client = mock_client.return_value
        
        result = provider.chat([{"role": "user", "content": "Hi"}])
        
        assert result["success"] is True
        assert result["content"] == "Hello"
        
        # 清理
        del os.environ["TEST_KEY"]


class TestCodexCLIProvider:
    """Codex CLI 提供者测试。"""

    def test_codex_provider_initialization(self) -> None:
        """测试 Codex CLI 提供者初始化。"""
        config = ModelConfig(
            name="codex",
            display_name="Codex CLI",
            provider="codex_cli",
            base_url="",
            api_key_env="",
            model_id="codex",
            capabilities=[ModelCapability.EXECUTION],
        )
        provider = CodexCLIProvider(config)
        assert provider.get_config().name == "codex"


class TestModelRegistry:
    """模型注册中心测试。"""

    def setup_method(self) -> None:
        """每个测试前清空注册中心。"""
        registry.clear()
    
    def teardown_method(self) -> None:
        """每个测试后恢复默认模型。"""
        registry.clear()
        registry._load_default_models()

    def test_registry_singleton(self) -> None:
        """测试单例模式。"""
        reg1 = ModelRegistry()
        reg2 = ModelRegistry()
        assert reg1 is reg2

    def test_register_model(self) -> None:
        """测试注册模型。"""
        config = ModelConfig(
            name="custom_model",
            display_name="Custom",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="TEST_KEY",
            model_id="custom-v1",
            capabilities=[ModelCapability.ANALYSIS],
        )
        registry.register(config)
        
        assert "custom_model" in registry.list_models()
        assert registry.get_config("custom_model") is not None

    def test_list_models(self) -> None:
        """测试列出模型。"""
        registry._load_default_models()
        models = registry.list_models()
        assert "qwen" in models
        assert "longcat_thinking" in models
        assert "codex_cli" in models

    def test_select_by_capability(self) -> None:
        """测试按能力选择模型。"""
        registry._load_default_models()
        
        # 代码生成
        code_models = registry.select_by_capability(ModelCapability.CODE_GENERATION)
        assert len(code_models) > 0
        
        # 执行（Codex CLI 最高优先级）
        exec_models = registry.select_by_capability(ModelCapability.EXECUTION)
        assert "codex_cli" in exec_models

    def test_select_best_for_task(self) -> None:
        """测试选择最佳模型。"""
        registry._load_default_models()
        
        # 执行任务 -> Codex CLI
        best = registry.select_best_for_task("execution")
        assert best == "codex_cli"

    def test_get_consensus_models(self) -> None:
        """测试获取共识模型列表。"""
        registry._load_default_models()
        
        consensus_models = registry.get_consensus_models()
        assert len(consensus_models) > 0
        # 应包含 qwen, longcat_thinking, longcat_lite
        assert "qwen" in consensus_models
        assert "longcat_thinking" in consensus_models

    def test_get_provider(self) -> None:
        """测试获取提供者。"""
        registry._load_default_models()
        
        provider = registry.get_provider("qwen")
        assert provider is not None
        assert isinstance(provider, OpenAICompatibleProvider)
        
        codex_provider = registry.get_provider("codex_cli")
        assert codex_provider is not None
        assert isinstance(codex_provider, CodexCLIProvider)

    def test_clear(self) -> None:
        """测试清空注册。"""
        registry._load_default_models()
        assert len(registry.list_models()) > 0
        
        registry.clear()
        assert len(registry.list_models()) == 0


class TestModelRegistryPriority:
    """优先级排序测试。"""

    def setup_method(self) -> None:
        registry.clear()

    def teardown_method(self) -> None:
        registry.clear()
        registry._load_default_models()

    def test_priority_sorting(self) -> None:
        """测试优先级排序。"""
        # 注册三个模型，不同优先级
        registry.register(ModelConfig(
            name="low_priority",
            display_name="Low",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="TEST_KEY",
            model_id="low",
            capabilities=[ModelCapability.CODE_GENERATION],
            priority=200,  # 低优先级
        ))
        
        registry.register(ModelConfig(
            name="high_priority",
            display_name="High",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="TEST_KEY",
            model_id="high",
            capabilities=[ModelCapability.CODE_GENERATION],
            priority=10,  # 高优先级
        ))
        
        registry.register(ModelConfig(
            name="medium_priority",
            display_name="Medium",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="TEST_KEY",
            model_id="medium",
            capabilities=[ModelCapability.CODE_GENERATION],
            priority=100,
        ))
        
        models = registry.select_by_capability(ModelCapability.CODE_GENERATION)
        
        # 应按优先级排序：high(10) -> medium(100) -> low(200)
        assert models[0] == "high_priority"
        assert models[1] == "medium_priority"
        assert models[2] == "low_priority"


class TestModelCapabilityEnum:
    """能力枚举测试。"""

    def test_capability_values(self) -> None:
        """测试能力值。"""
        assert ModelCapability.CODE_GENERATION.value == "code_generation"
        assert ModelCapability.CONSENSUS.value == "consensus"
        assert ModelCapability.ALL.value == "all"

    def test_all_capability_includes_everything(self) -> None:
        """测试 ALL 能力匹配所有。"""
        registry.clear()
        registry.register(ModelConfig(
            name="universal",
            display_name="Universal",
            provider="test",
            base_url="https://api.test.com",
            api_key_env="TEST_KEY",
            model_id="universal",
            capabilities=[ModelCapability.ALL],
        ))
        
        # ALL 能力应该匹配任何任务类型
        for cap in [ModelCapability.CODE_GENERATION, ModelCapability.ANALYSIS, ModelCapability.EXECUTION]:
            models = registry.select_by_capability(cap)
            assert "universal" in models


class TestDefaultModelsLoaded:
    """默认模型加载测试。"""

    def test_default_models_loaded(self) -> None:
        """测试默认模型自动加载。"""
        registry.clear()
        reg = ModelRegistry()  # 初始化时自动加载
        
        models = reg.list_models()
        assert "qwen" in models
        assert "longcat_thinking" in models
        assert "longcat_lite" in models
        assert "codex_cli" in models

    def test_longcat_lite_quota(self) -> None:
        """测试 LongCat Lite 的超大额度。"""
        registry.clear()
        reg = ModelRegistry()
        
        config = reg.get_config("longcat_lite")
        assert config is not None
        assert config.daily_quota == 50000000  # 50M

    def test_codex_cli_priority(self) -> None:
        """测试 Codex CLI 最高优先级。"""
        registry.clear()
        reg = ModelRegistry()
        
        config = reg.get_config("codex_cli")
        assert config is not None
        assert config.priority == 10  # 最高


if __name__ == "__main__":
    pytest.main([__file__, "-v"])