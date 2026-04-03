"""
longcat_client.py
LongCat API 客户端模块，用于调用 LongCat 模型进行编码工作。

接入端点：https://api.longcat.chat/openai
兼容 OpenAI API 格式。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# LongCat API 配置
LONGCAT_BASE_URL = os.environ.get("LONGCAT_BASE_URL", "https://api.longcat.chat/openai")
LONGCAT_API_KEY = os.environ.get("LONGCAT_API_KEY", "")
LONGCAT_MODEL = os.environ.get("LONGCAT_MODEL", "LongCat-Flash-Thinking-2601")

# 模型列表
LONGCAT_MODELS = {
    "thinking": {
        "name": "LongCat-Flash-Thinking-2601",
        "description": "深度思考模型，适合复杂编码任务",
        "max_tokens": 256000,
        "daily_free_quota": 500000,
    },
    "chat": {
        "name": "LongCat-Flash-Chat",
        "description": "高性能通用对话模型",
        "max_tokens": 256000,
        "daily_free_quota": 500000,
    },
    "lite": {
        "name": "LongCat-Flash-Lite",
        "description": "高效轻量化MoE模型，超大免费额度",
        "max_tokens": 320000,
        "daily_free_quota": 50000000,
    },
    "omni": {
        "name": "LongCat-Flash-Omni-2603",
        "description": "多模态模型",
        "max_tokens": 8000,
        "daily_free_quota": 500000,
    },
}

__all__ = ["LongCatClient", "LONGCAT_MODELS", "invoke_longcat"]


class LongCatClient:
    """
    LongCat API 客户端。
    
    兼容 OpenAI API 格式，支持多种 LongCat 模型。
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """
        初始化 LongCat 客户端。
        
        Args:
            api_key: API 密钥，默认从环境变量 LONGCAT_API_KEY 读取。
            base_url: API 基础 URL，默认 https://api.longcat.chat/openai。
            model: 模型名称，默认 LongCat-Flash-Thinking-2601。
        """
        self._api_key = api_key or LONGCAT_API_KEY
        self._base_url = base_url or LONGCAT_BASE_URL
        self._model = model or LONGCAT_MODEL
        
        if not self._api_key:
            logger.warning("LongCat API Key 未设置，请设置 LONGCAT_API_KEY 环境变量")
        
        logger.debug(
            "LongCatClient 初始化完成 | base_url=%s | model=%s",
            self._base_url, self._model
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        发送对话请求。
        
        Args:
            messages: 消息列表，格式 [{"role": "user/assistant/system", "content": "..."}]。
            temperature: 温度参数，默认 0.1（编码任务建议低温度）。
            max_tokens: 最大输出 Token 数，默认 4096。
            stream: 是否流式输出，默认 False。
        
        Returns:
            API 响应字典。
        
        Raises:
            ValueError: 当 API Key 未设置时抛出。
            RuntimeError: 当 API 调用失败时抛出。
        """
        if not self._api_key:
            err_msg = "LongCat API Key 未设置，请设置 LONGCAT_API_KEY 环境变量或传入 api_key 参数"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        try:
            from openai import OpenAI
            
            client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
            )
            
            logger.info(
                "LongCat API 调用 | model=%s | messages=%d | max_tokens=%d",
                self._model, len(messages), max_tokens
            )
            
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )
            
            if stream:
                # 流式响应处理
                result: Dict[str, Any] = {
                    "success": True,
                    "model": self._model,
                    "stream": True,
                    "content": "",
                }
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        result["content"] += chunk.choices[0].delta.content
                return result
            else:
                # 非流式响应
                content = response.choices[0].message.content or ""
                return {
                    "success": True,
                    "model": self._model,
                    "content": content,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                }
        
        except Exception as exc:
            logger.exception("LongCat API 调用失败: %s", exc)
            raise RuntimeError(f"LongCat API 调用失败: {exc}") from exc
    
    def generate_code(
        self,
        task: str,
        context: Optional[str] = None,
        language: str = "Python",
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """
        生成代码。
        
        Args:
            task: 编码任务描述。
            context: 上下文信息（如现有代码、约束条件）。
            language: 目标语言，默认 Python。
            max_tokens: 最大输出 Token 数。
        
        Returns:
            包含生成代码的响应字典。
        """
        system_prompt = (
            f"你是专业的 {language} 开发工程师。"
            "生成高质量、可维护的代码。"
            "遵循最佳实践：完整类型注解、文档字符串、错误处理。"
            "输出代码时使用 ```{language} 代码块包裹。"
        )
        
        user_content = f"任务：{task}"
        if context:
            user_content += f"\n\n上下文：{context}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        
        return self.chat(messages, temperature=0.1, max_tokens=max_tokens)
    
    def review_code(
        self,
        code: str,
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        代码审查。
        
        Args:
            code: 待审查的代码。
            focus_areas: 关注领域（如 ["安全", "性能", "可维护性"]）。
        
        Returns:
            包含审查意见的响应字典。
        """
        system_prompt = (
            "你是资深代码审查专家。"
            "审查代码质量、安全性、性能、可维护性。"
            "输出结构化审查报告："
            "- P0: 严重问题（安全漏洞、数据丢失风险）"
            "- P1: 重要问题（逻辑错误、SOLID 违规）"
            "- P2: 中等问题（代码异味、维护性问题）"
            "- P3: 低优先级问题（风格、命名）"
        )
        
        focus_str = ""
        if focus_areas:
            focus_str = f"\n重点关注：{', '.join(focus_areas)}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请审查以下代码：{focus_str}\n\n```\n{code}\n```"},
        ]
        
        return self.chat(messages, temperature=0.3, max_tokens=4096)
    
    def set_model(self, model_type: str) -> None:
        """
        设置模型类型。
        
        Args:
            model_type: 模型类型键名（thinking/chat/lite/omni）。
        
        Raises:
            KeyError: 当模型类型无效时抛出。
        """
        if model_type not in LONGCAT_MODELS:
            err_msg = f"无效的模型类型: '{model_type}'。有效类型: {list(LONGCAT_MODELS.keys())}"
            logger.error(err_msg)
            raise KeyError(err_msg)
        
        self._model = LONGCAT_MODELS[model_type]["name"]
        logger.info("模型切换: %s", self._model)
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息。"""
        for key, info in LONGCAT_MODELS.items():
            if info["name"] == self._model:
                return {"type": key, **info}
        return {"type": "unknown", "name": self._model}


def invoke_longcat(
    task: str,
    context: Optional[str] = None,
    model_type: str = "thinking",
    max_tokens: int = 8192,
) -> Dict[str, Any]:
    """
    便捷函数：调用 LongCat 进行编码任务。
    
    Args:
        task: 编码任务描述。
        context: 上下文信息。
        model_type: 模型类型，默认 thinking（深度思考）。
        max_tokens: 最大输出 Token 数。
    
    Returns:
        包含生成结果的响应字典。
    """
    client = LongCatClient()
    client.set_model(model_type)
    return client.generate_code(task, context=context, max_tokens=max_tokens)


if __name__ == "__main__":
    # 配置日志以便独立测试
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("=" * 60)
    print("LongCat Client 测试")
    print("=" * 60)
    
    # 显示模型信息
    print("\n--- 支持的模型 ---")
    for key, info in LONGCAT_MODELS.items():
        print(f"{key}: {info['name']} - {info['description']} ({info['daily_free_quota']} tokens/day)")
    
    # 测试客户端初始化
    print("\n--- 客户端初始化 ---")
    client = LongCatClient()
    print(f"Base URL: {client._base_url}")
    print(f"Model: {client._model}")
    print(f"API Key set: {bool(client._api_key)}")
    
    # 测试模型切换
    print("\n--- 模型切换测试 ---")
    client.set_model("lite")
    info = client.get_model_info()
    print(f"当前模型: {info}")
    
    # 如果有 API Key，测试实际调用
    if LONGCAT_API_KEY:
        print("\n--- API 调用测试 ---")
        try:
            result = client.chat(
                messages=[{"role": "user", "content": "你好，请简短介绍一下你自己。"}],
                max_tokens=100,
            )
            print(f"Success: {result['success']}")
            print(f"Content: {result['content'][:200]}...")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("\n--- API Key 未设置 ---")
        print("请设置环境变量 LONGCAT_API_KEY 后测试实际调用")
        print("获取 API Key: https://longcat.chat/platform/api_keys")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)