"""
model_registry.py
通用模型注册中心，支持任意 OpenAI API 格式的模型接入。

架构升级：从 "双模型共识" 升级为 "多模型共识"
- Codex CLI（专用工具）
- Qwen（OpenRouter API）
- LongCat（LongCat API）
- 任意其他 OpenAI API 格式的模型

设计原则：
1. 统一抽象接口
2. 配置驱动注册
3. 动态扩容能力
4. 健康检查机制
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """模型能力类型。"""
    CODE_GENERATION = "code_generation"      # 代码生成
    CODE_REVIEW = "code_review"              # 代码审查
    ANALYSIS = "analysis"                     # 任务分析
    REASONING = "reasoning"                   # 深度推理
    CONSENSUS = "consensus"                   # 共识参与
    EXECUTION = "execution"                   # 代码执行（Codex CLI）
    ALL = "all"                               # 全能力


class ModelStatus(Enum):
    """模型状态。"""
    AVAILABLE = "available"      # 可用
    RATE_LIMITED = "rate_limited" # 速率限制
    ERROR = "error"               # 错误状态
    DISABLED = "disabled"         # 已禁用
    UNKNOWN = "unknown"           # 未检测


@dataclass
class ModelConfig:
    """模型配置。"""
    name: str                              # 模型唯一标识
    display_name: str                      # 显示名称
    provider: str                          # 提供商（openai, openrouter, longcat, codex_cli）
    base_url: str                          # API 基础 URL
    api_key_env: str                       # API Key 环境变量名
    model_id: str                          # 实际模型 ID
    capabilities: List[ModelCapability]    # 能力列表
    max_tokens: int = 4096                 # 最大输出 Token
    temperature: float = 0.1               # 默认温度
    daily_quota: int = 0                   # 每日免费额度（0=无限制或付费）
    priority: int = 100                    # 优先级（数字越小优先级越高）
    enabled: bool = True                   # 是否启用
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据


@dataclass
class ModelHealth:
    """模型健康状态。"""
    name: str
    status: ModelStatus
    last_check: float                      # 上次检查时间戳
    latency_ms: float = 0                  # 响应延迟
    error_message: str = ""                # 错误信息
    quota_used: int = 0                    # 今日已用额度
    quota_remaining: int = 0               # 今日剩余额度


class ModelProvider(ABC):
    """
    抽象模型提供者接口。
    
    所有接入的模型都需要实现此接口。
    """
    
    @abstractmethod
    def __init__(self, config: ModelConfig) -> None:
        """初始化模型提供者。"""
        pass
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """发送对话请求。"""
        pass
    
    @abstractmethod
    def generate_code(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """生成代码。"""
        pass
    
    @abstractmethod
    def analyze(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """分析任务。"""
        pass
    
    @abstractmethod
    def review(
        self,
        code: str,
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """审查代码。"""
        pass
    
    @abstractmethod
    def health_check(self) -> ModelHealth:
        """健康检查。"""
        pass
    
    @abstractmethod
    def get_config(self) -> ModelConfig:
        """获取配置。"""
        pass


class OpenAICompatibleProvider(ModelProvider):
    """
    OpenAI API 格式的通用模型提供者。
    
    适用于：Qwen (OpenRouter)、LongCat、DeepSeek、等所有 OpenAI 兼容 API。
    """
    
    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._api_key = os.environ.get(config.api_key_env, "")
        self._client = None
        
        if not self._api_key:
            logger.warning(
                "模型 %s API Key 未设置，请设置环境变量 %s",
                config.name, config.api_key_env
            )
        
        logger.debug(
            "OpenAICompatibleProvider 初始化 | name=%s | base_url=%s | model_id=%s",
            config.name, config.base_url, config.model_id
        )
    
    def _get_client(self) -> Any:
        """延迟初始化 OpenAI 客户端。"""
        if self._client is None and self._api_key:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=self._config.base_url,
                api_key=self._api_key,
            )
        return self._client
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """发送对话请求。"""
        if not self._api_key:
            return self._error_response("API Key 未设置")
        
        client = self._get_client()
        if client is None:
            return self._error_response("客户端初始化失败")
        
        try:
            response = client.chat.completions.create(
                model=self._config.model_id,
                messages=messages,
                temperature=temperature or self._config.temperature,
                max_tokens=max_tokens or self._config.max_tokens,
            )
            
            content = response.choices[0].message.content or ""
            return {
                "success": True,
                "model": self._config.name,
                "provider": self._config.provider,
                "content": content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
        except Exception as exc:
            logger.exception("%s API 调用失败: %s", self._config.name, exc)
            return self._error_response(str(exc))
    
    def generate_code(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """生成代码。"""
        system_prompt = (
            f"你是专业开发工程师。生成高质量代码。"
            "遵循最佳实践：类型注解、文档字符串、错误处理。"
            "输出代码使用代码块包裹。"
        )
        
        user_content = f"任务：{task}"
        if context:
            user_content += f"\n\n上下文：{context}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        
        return self.chat(messages, temperature=0.1, max_tokens=max_tokens or 8192)
    
    def analyze(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """分析任务。返回结构化分析结果。"""
        system_prompt = (
            "你是需求分析师。分析任务并返回结构化 JSON。\n"
            "JSON schema:\n"
            '{"opinion": "string", "key_points": ["string"], "concerns": ["string"], '
            '"suggestions": ["string"], "feasibility": "high|medium|low"}'
        )
        
        user_content = f"任务：{task}"
        if context:
            user_content += f"\n\n上下文：{json.dumps(context, ensure_ascii=False)}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        
        result = self.chat(messages, temperature=0.3, max_tokens=2048)
        
        # 尝试解析 JSON
        if result["success"]:
            content = result["content"]
            # 去除代码块包裹
            if content.startswith("```"):
                lines = content.splitlines()
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            try:
                result["parsed"] = json.loads(content)
            except json.JSONDecodeError:
                result["parsed"] = None
                result["parse_error"] = "JSON 解析失败"
        
        return result
    
    def review(
        self,
        code: str,
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """审查代码。"""
        system_prompt = (
            "你是代码审查专家。审查代码质量、安全性、性能。\n"
            "输出结构化审查报告：\n"
            "- P0: 严重问题\n- P1: 重要问题\n- P2: 中等问题\n- P3: 低优先级"
        )
        
        focus_str = ""
        if focus_areas:
            focus_str = f"\n重点关注：{', '.join(focus_areas)}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"审查代码：{focus_str}\n\n```\n{code}\n```"},
        ]
        
        return self.chat(messages, temperature=0.3, max_tokens=4096)
    
    def health_check(self) -> ModelHealth:
        """健康检查。"""
        if not self._api_key:
            return ModelHealth(
                name=self._config.name,
                status=ModelStatus.ERROR,
                last_check=time.time(),
                error_message="API Key 未设置",
            )
        
        try:
            start_time = time.time()
            result = self.chat(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=10,
            )
            latency = (time.time() - start_time) * 1000
            
            if result["success"]:
                return ModelHealth(
                    name=self._config.name,
                    status=ModelStatus.AVAILABLE,
                    last_check=time.time(),
                    latency_ms=latency,
                )
            else:
                return ModelHealth(
                    name=self._config.name,
                    status=ModelStatus.ERROR,
                    last_check=time.time(),
                    latency_ms=latency,
                    error_message=result.get("error", "未知错误"),
                )
        except Exception as exc:
            return ModelHealth(
                name=self._config.name,
                status=ModelStatus.ERROR,
                last_check=time.time(),
                error_message=str(exc),
            )
    
    def get_config(self) -> ModelConfig:
        """获取配置。"""
        return self._config
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """生成错误响应。"""
        return {
            "success": False,
            "model": self._config.name,
            "provider": self._config.provider,
            "error": message,
            "content": "",
        }


class CodexCLIProvider(ModelProvider):
    """
    Codex CLI 专用提供者。
    
    Codex CLI 是独立工具，不通过 OpenAI API 调用。
    """
    
    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._codex_path = os.environ.get("CODEX_CLI_PATH", "codex")
        logger.debug("CodexCLIProvider 初始化 | path=%s", self._codex_path)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Codex CLI 不支持标准 chat，使用 execute。"""
        # 将 messages 合并为 prompt
        prompt = "\n".join([m["content"] for m in messages])
        return self._execute_codex(prompt)
    
    def generate_code(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """生成代码。"""
        prompt = f"任务：{task}"
        if context:
            prompt += f"\n\n上下文：{context}"
        return self._execute_codex(prompt)
    
    def analyze(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """分析任务。"""
        prompt = f"分析任务：{task}"
        if context:
            prompt += f"\n上下文：{json.dumps(context, ensure_ascii=False)}"
        prompt += "\n返回结构化 JSON 分析结果。"
        return self._execute_codex(prompt)
    
    def review(
        self,
        code: str,
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """审查代码。"""
        prompt = f"审查代码：\n```\n{code}\n```"
        if focus_areas:
            prompt += f"\n重点关注：{', '.join(focus_areas)}"
        return self._execute_codex(prompt)
    
    def health_check(self) -> ModelHealth:
        """健康检查。"""
        try:
            import subprocess
            result = subprocess.run(
                [self._codex_path, "--version"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                return ModelHealth(
                    name=self._config.name,
                    status=ModelStatus.AVAILABLE,
                    last_check=time.time(),
                )
            else:
                return ModelHealth(
                    name=self._config.name,
                    status=ModelStatus.ERROR,
                    last_check=time.time(),
                    error_message=result.stderr.decode(),
                )
        except Exception as exc:
            return ModelHealth(
                name=self._config.name,
                status=ModelStatus.ERROR,
                last_check=time.time(),
                error_message=str(exc),
            )
    
    def get_config(self) -> ModelConfig:
        """获取配置。"""
        return self._config
    
    def _execute_codex(self, prompt: str) -> Dict[str, Any]:
        """执行 Codex CLI 命令。"""
        try:
            import subprocess
            result = subprocess.run(
                [self._codex_path, "--prompt", prompt],
                capture_output=True,
                timeout=300,
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "model": self._config.name,
                    "provider": "codex_cli",
                    "content": result.stdout.decode(),
                }
            else:
                return {
                    "success": False,
                    "model": self._config.name,
                    "provider": "codex_cli",
                    "error": result.stderr.decode(),
                    "content": "",
                }
        except Exception as exc:
            return {
                "success": False,
                "model": self._config.name,
                "provider": "codex_cli",
                "error": str(exc),
                "content": "",
            }


class ModelRegistry:
    """
    模型注册中心。
    
    管理所有接入的模型，支持：
    - 动态注册新模型
    - 配置文件驱动
    - 能力匹配选择
    - 健康状态监控
    - 多模型共识调度
    """
    
    _instance: Optional["ModelRegistry"] = None
    _providers: Dict[str, ModelProvider] = {}
    _configs: Dict[str, ModelConfig] = {}
    _health: Dict[str, ModelHealth] = {}
    
    def __new__(cls) -> "ModelRegistry":
        """单例模式。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """初始化注册中心。"""
        if not self._providers:
            self._load_default_models()
    
    def _load_default_models(self) -> None:
        """加载默认模型配置。"""
        # Qwen (OpenRouter)
        self.register(ModelConfig(
            name="qwen",
            display_name="Qwen (OpenRouter)",
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="OPENROUTER_API_KEY",
            model_id="qwen/qwen3.6-plus:free",
            capabilities=[ModelCapability.CODE_GENERATION, ModelCapability.ANALYSIS, ModelCapability.CONSENSUS],
            max_tokens=4096,
            priority=50,
            daily_quota=500000,
        ))
        
        # LongCat Thinking
        self.register(ModelConfig(
            name="longcat_thinking",
            display_name="LongCat Thinking",
            provider="longcat",
            base_url="https://api.longcat.chat/openai",
            api_key_env="LONGCAT_API_KEY",
            model_id="LongCat-Flash-Thinking-2601",
            capabilities=[ModelCapability.CODE_GENERATION, ModelCapability.REASONING, ModelCapability.CONSENSUS],
            max_tokens=256000,
            priority=30,  # 高优先级
            daily_quota=500000,
        ))
        
        # LongCat Lite（超大免费额度）
        self.register(ModelConfig(
            name="longcat_lite",
            display_name="LongCat Lite (50M/day)",
            provider="longcat",
            base_url="https://api.longcat.chat/openai",
            api_key_env="LONGCAT_API_KEY",
            model_id="LongCat-Flash-Lite",
            capabilities=[ModelCapability.CODE_GENERATION, ModelCapability.ANALYSIS, ModelCapability.CONSENSUS],
            max_tokens=320000,
            priority=40,
            daily_quota=50000000,  # 50M
        ))
        
        # Codex CLI
        self.register(ModelConfig(
            name="codex_cli",
            display_name="Codex CLI",
            provider="codex_cli",
            base_url="",  # 不使用 HTTP API
            api_key_env="",  # 无需 API Key
            model_id="codex",
            capabilities=[ModelCapability.EXECUTION, ModelCapability.CODE_REVIEW, ModelCapability.ALL],
            max_tokens=0,  # CLI 无限制
            priority=10,  # 最高优先级（执行任务）
            daily_quota=0,
        ))
        
        logger.info("默认模型加载完成，已注册 %d 个模型", len(self._configs))
    
    def register(self, config: ModelConfig) -> None:
        """
        注册新模型。
        
        Args:
            config: 模型配置。
        """
        # 根据提供商类型选择 Provider 类
        if config.provider == "codex_cli":
            provider = CodexCLIProvider(config)
        else:
            provider = OpenAICompatibleProvider(config)
        
        self._configs[config.name] = config
        self._providers[config.name] = provider
        
        logger.info(
            "模型注册 | name=%s | provider=%s | capabilities=%s | priority=%d",
            config.name, config.provider, [c.value for c in config.capabilities], config.priority
        )
    
    def register_from_config_file(self, config_path: Union[str, Path]) -> None:
        """
        从配置文件批量注册模型。
        
        Args:
            config_path: 配置文件路径（JSON 格式）。
        """
        path = Path(config_path)
        if not path.exists():
            logger.error("配置文件不存在: %s", path)
            return
        
        with open(path, "r", encoding="utf-8") as f:
            configs = json.load(f)
        
        for item in configs.get("models", []):
            capabilities = [ModelCapability(c) for c in item.get("capabilities", ["all"])]
            config = ModelConfig(
                name=item["name"],
                display_name=item.get("display_name", item["name"]),
                provider=item["provider"],
                base_url=item["base_url"],
                api_key_env=item["api_key_env"],
                model_id=item["model_id"],
                capabilities=capabilities,
                max_tokens=item.get("max_tokens", 4096),
                temperature=item.get("temperature", 0.1),
                daily_quota=item.get("daily_quota", 0),
                priority=item.get("priority", 100),
                enabled=item.get("enabled", True),
                metadata=item.get("metadata", {}),
            )
            self.register(config)
    
    def get_provider(self, name: str) -> Optional[ModelProvider]:
        """获取模型提供者。"""
        return self._providers.get(name)
    
    def get_config(self, name: str) -> Optional[ModelConfig]:
        """获取模型配置。"""
        return self._configs.get(name)
    
    def get_health(self, name: str) -> Optional[ModelHealth]:
        """获取模型健康状态。"""
        return self._health.get(name)
    
    def list_models(self) -> List[str]:
        """列出所有已注册模型。"""
        return list(self._configs.keys())
    
    def list_available_models(self) -> List[str]:
        """列出所有可用模型。"""
        return [
            name for name, config in self._configs.items()
            if config.enabled and self._health.get(name, ModelHealth(name=name, status=ModelStatus.UNKNOWN)).status == ModelStatus.AVAILABLE
        ]
    
    def select_by_capability(self, capability: ModelCapability) -> List[str]:
        """
        根据能力选择模型。
        
        Args:
            capability: 需要的能力。
        
        Returns:
            具备该能力的模型列表（按优先级排序）。
        """
        candidates = []
        for name, config in self._configs.items():
            if capability in config.capabilities or ModelCapability.ALL in config.capabilities:
                if config.enabled:
                    candidates.append((name, config.priority))
        
        # 按优先级排序
        candidates.sort(key=lambda x: x[1])
        return [name for name, _ in candidates]
    
    def select_best_for_task(self, task_type: str) -> Optional[str]:
        """
        根据任务类型选择最佳模型。
        
        Args:
            task_type: 任务类型（code_generation, analysis, review, execution）。
        
        Returns:
            最佳模型名称。
        """
        capability_map = {
            "code_generation": ModelCapability.CODE_GENERATION,
            "analysis": ModelCapability.ANALYSIS,
            "review": ModelCapability.CODE_REVIEW,
            "execution": ModelCapability.EXECUTION,
            "consensus": ModelCapability.CONSENSUS,
            "reasoning": ModelCapability.REASONING,
        }
        
        capability = capability_map.get(task_type, ModelCapability.ALL)
        candidates = self.select_by_capability(capability)
        
        # 检查健康状态
        for name in candidates:
            health = self._health.get(name)
            if health and health.status == ModelStatus.AVAILABLE:
                return name
        
        # 没有可用健康检查结果，返回第一个候选
        return candidates[0] if candidates else None
    
    def check_all_health(self) -> Dict[str, ModelHealth]:
        """检查所有模型健康状态。"""
        for name, provider in self._providers.items():
            self._health[name] = provider.health_check()
        
        logger.info("健康检查完成 | 可用: %s", self.list_available_models())
        return self._health
    
    def get_consensus_models(self) -> List[str]:
        """
        获取参与共识的模型列表。
        
        Returns:
            具备共识能力的模型列表（按优先级排序）。
        """
        return self.select_by_capability(ModelCapability.CONSENSUS)
    
    def dispatch_consensus(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        models: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        向多个模型分发共识任务。
        
        Args:
            task: 任务描述。
            context: 上下文信息。
            models: 指定模型列表（默认使用所有共识模型）。
        
        Returns:
            各模型的分析结果字典。
        """
        target_models = models or self.get_consensus_models()
        results: Dict[str, Dict[str, Any]] = {}
        
        logger.info("共识任务分发 | models=%s | task=%s", target_models, task[:50])
        
        for name in target_models:
            provider = self._providers.get(name)
            if provider is None:
                results[name] = {"success": False, "error": "模型未注册"}
                continue
            
            # 检查是否启用
            config = self._configs.get(name)
            if config and not config.enabled:
                results[name] = {"success": False, "error": "模型已禁用"}
                continue
            
            # 执行分析
            result = provider.analyze(task, context)
            results[name] = result
            
            logger.debug(
                "模型 %s 分析完成 | success=%s | tokens=%s",
                name, result["success"], result.get("usage", {}).get("total_tokens", 0)
            )
        
        return results
    
    def clear(self) -> None:
        """清空所有注册（用于测试）。"""
        self._providers.clear()
        self._configs.clear()
        self._health.clear()


# 全局注册中心实例
registry = ModelRegistry()


__all__ = [
    "ModelCapability",
    "ModelStatus",
    "ModelConfig",
    "ModelHealth",
    "ModelProvider",
    "OpenAICompatibleProvider",
    "CodexCLIProvider",
    "ModelRegistry",
    "registry",
]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("=" * 60)
    print("ModelRegistry 测试")
    print("=" * 60)
    
    # 初始化注册中心
    reg = ModelRegistry()
    
    # 列出所有模型
    print("\n--- 已注册模型 ---")
    for name in reg.list_models():
        config = reg.get_config(name)
        if config:
            print(f"  {name}: {config.display_name} | provider={config.provider} | priority={config.priority}")
    
    # 列出共识模型
    print("\n--- 共识参与模型 ---")
    for name in reg.get_consensus_models():
        print(f"  {name}")
    
    # 选择最佳模型
    print("\n--- 最佳模型选择 ---")
    for task_type in ["code_generation", "analysis", "execution"]:
        best = reg.select_best_for_task(task_type)
        print(f"  {task_type}: {best}")
    
    # 健康检查
    print("\n--- 健康检查 ---")
    health = reg.check_all_health()
    for name, h in health.items():
        print(f"  {name}: {h.status.value} | latency={h.latency_ms:.0f}ms | error={h.error_message or 'None'}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)