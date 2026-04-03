# Codex-Qwen Pipeline V2 - 多模型共识架构

## 📊 架构升级历史

| 版本 | 架构 | 模型数量 | 状态 |
|------|------|----------|------|
| V1 | 双模型共识 | 2 (Codex + Qwen) | 已废弃 |
| V2 | 多模型共识 | N (可扩展) | ✅ 当前 |

---

## 一、核心设计理念

### 1.1 从"双模型"到"多模型"

**原架构（双模型）：**
```
基础模型 → Codex CLI + Qwen API → 共识判定 → 执行
```

**新架构（多模型）：**
```
基础模型 → ModelRegistry → 多模型并行分析 → 共识判定 → 执行
                    ↓
            ┌───────┼───────┬───────┐
            │       │       │       │
          Qwen   LongCat  Codex   新模型...
         (OpenAI API 格式兼容)
```

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **统一接口** | 所有模型通过 `ModelProvider` 抽象接口接入 |
| **配置驱动** | 通过配置文件或代码动态注册新模型 |
| **能力匹配** | 根据任务类型自动选择具备相应能力的模型 |
| **优先级排序** | 多模型按优先级排序，优先使用高质量模型 |
| **健康检查** | 自动检测模型可用性，动态调整参与列表 |
| **OpenAI兼容** | 任何 OpenAI API 格式的模型均可接入 |

---

## 二、模型注册中心（ModelRegistry）

### 2.1 核心组件

```
src/model_registry.py
├── ModelCapability (Enum)      # 模型能力类型
├── ModelStatus (Enum)          # 模型状态
├── ModelConfig (Dataclass)     # 模型配置
├── ModelHealth (Dataclass)     # 健康状态
├── ModelProvider (ABC)         # 抽象提供者接口
├── OpenAICompatibleProvider    # OpenAI API 兼容实现
├── CodexCLIProvider            # Codex CLI 专用实现
└── ModelRegistry               # 注册中心（单例）
```

### 2.2 模型能力定义

```python
class ModelCapability(Enum):
    CODE_GENERATION = "code_generation"  # 代码生成
    CODE_REVIEW = "code_review"          # 代码审查
    ANALYSIS = "analysis"                 # 任务分析
    REASONING = "reasoning"               # 深度推理
    CONSENSUS = "consensus"               # 共识参与
    EXECUTION = "execution"               # 代码执行（Codex CLI）
    ALL = "all"                           # 全能力
```

### 2.3 已注册模型

| 模型名称 | 提供者 | 能力 | 优先级 | 每日免费额度 |
|---------|--------|------|--------|-------------|
| **codex_cli** | Codex CLI | EXECUTION, ALL | 10 (最高) | 无限制 |
| **longcat_thinking** | LongCat | CODE_GEN, REASONING, CONSENSUS | 30 | 500K |
| **longcat_lite** | LongCat | CODE_GEN, ANALYSIS, CONSENSUS | 40 | **50M** |
| **qwen** | OpenRouter | CODE_GEN, ANALYSIS, CONSENSUS | 50 | 500K |

---

## 三、共识流程

### 3.1 多模型共识调度

```python
def dispatch_consensus(task: str, context: dict) -> dict[str, dict]:
    """
    向所有具备共识能力的模型分发任务。
    
    Returns:
        {
            "qwen": {"success": True, "parsed": {...}},
            "longcat_thinking": {"success": True, "parsed": {...}},
            "longcat_lite": {"success": True, "parsed": {...}},
            ...
        }
    """
```

### 3.2 共识判定流程

```
任务输入
    ↓
┌─────────────────────────────────────────────────────────────┐
│  ModelRegistry.dispatch_consensus(task)                     │
│                                                             │
│  ┌─────────┐  ┌─────────────┐  ┌───────────┐  ┌─────────┐  │
│  │  Qwen   │  │LongCat Think│  │LongCat Lite│  │ 新模型  │  │
│  │ analyze │  │   analyze   │  │  analyze  │  │ analyze │  │
│  └───┬─────┘  └─────┬───────┘  └─────┬─────┘  └───┬─────┘  │
│      │              │                │            │        │
│      └──────────────┴────────────────┴────────────┘        │
│                         ↓                                   │
│              收集所有模型的分析结果                          │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  consensus_check(results)                                   │
│                                                             │
│  证据比对：                                                  │
│  - goal_aligned: 目标一致性                                  │
│  - constraints_aligned: 约束一致性                           │
│  - implementation_path_aligned: 实现路径一致性               │
│                                                             │
│  判定结果：                                                  │
│  - consensus_reached: 是否达成共识                           │
│  - consensus_points: 共识点                                  │
│  - divergence_points: 分歧点                                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────┬─────────────┐
│ 达成共识    │ 存在分歧    │
└──────┬──────┴──────┬──────┘
       ↓             ↓
  FINAL_PLAN    CONSENSUS_ROUND_2
                    ↓
               继续讨论或人工裁决
```

### 3.3 与原架构对比

| 项目 | 原架构（双模型） | 新架构（多模型） |
|------|-----------------|-----------------|
| 参与模型 | Codex + Qwen | N 个模型（可扩展）|
| 分发方式 | 手动调用两个 API | `dispatch_consensus()` 自动分发 |
| 模型选择 | 硬编码 | 能力匹配 + 优先级排序 |
| 健康检查 | 无 | 自动健康检查 |
| 扩展性 | 新增需改代码 | 配置驱动注册 |

---

## 四、接入新模型

### 4.1 OpenAI API 格式模型接入

只需创建 `ModelConfig` 并注册：

```python
from src.model_registry import ModelRegistry, ModelConfig, ModelCapability

registry = ModelRegistry()

# 接入 DeepSeek
registry.register(ModelConfig(
    name="deepseek",
    display_name="DeepSeek Coder",
    provider="deepseek",
    base_url="https://api.deepseek.com/v1",
    api_key_env="DEEPSEEK_API_KEY",
    model_id="deepseek-coder",
    capabilities=[ModelCapability.CODE_GENERATION, ModelCapability.CONSENSUS],
    max_tokens=16000,
    priority=35,  # 中等优先级
    daily_quota=1000000,
))
```

### 4.2 配置文件批量注册

```json
// models_config.json
{
  "models": [
    {
      "name": "claude",
      "display_name": "Claude 3.5",
      "provider": "anthropic",
      "base_url": "https://api.anthropic.com/v1",
      "api_key_env": "ANTHROPIC_API_KEY",
      "model_id": "claude-3-5-sonnet",
      "capabilities": ["code_generation", "analysis", "consensus"],
      "priority": 20,
      "daily_quota": 500000
    },
    {
      "name": "gemini",
      "display_name": "Gemini Pro",
      "provider": "google",
      "base_url": "https://api.google.com/v1",
      "api_key_env": "GOOGLE_API_KEY",
      "model_id": "gemini-pro",
      "capabilities": ["all"],
      "priority": 45
    }
  ]
}
```

```python
registry.register_from_config_file("models_config.json")
```

---

## 五、状态机设计（不变）

### 状态枚举

```python
WORKFLOW_STATES = {
    "INIT": "初始化",
    "PROBING": "能力探测",
    "ROUTING": "任务路由",
    "CONSENSUS_ROUND_1": "共识第一轮",
    "CONSENSUS_ROUND_2": "共识第二轮",
    "CONSENSUS_ROUND_3": "共识第三轮",
    "CONSENSUS_TIMEOUT": "共识超时",
    "FINAL_PLAN": "最终方案生成",
    "EXECUTING": "执行编码",
    "REVIEWING": "联合复查",
    "REVIEW_FIX_1": "修复第1轮",
    "REVIEW_FIX_2": "修复第2轮",
    "REVIEW_TIMEOUT": "修复超时",
    "COMPLETED": "完成",
    "FUSED": "熔断终止",
    "HUMAN_ESCALATION": "人工介入"
}
```

---

## 六、路由规则表

```python
ROUTING_RULES = {
    "task_classes": {
        "simple": {
            "description": "简单任务",
            "flow": "direct_execution",
            "keywords": ["修改", "调整", "添加", "修复", "更新"]
        },
        "moderate": {
            "description": "中等任务",
            "flow": "consensus_1_round",
            "keywords": ["重构", "实现", "开发", "集成"]
        },
        "complex": {
            "description": "复杂任务",
            "flow": "consensus_3_rounds",
            "keywords": ["架构", "迁移", "替换", "重写", "核心"]
        }
    },
    "fallback": "moderate"
}
```

---

## 七、熔断规则表

```python
FUSE_RULES = {
    "capability_levels": {
        "L0_threshold": 0.3,  # 低能力：跳过共识
        "L1_threshold": 0.6,  # 中能力：服务端归一化
        "L2_threshold": 0.8   # 高能力：正常流程
    },
    "runtime": {
        "schema_fail_max": 3,
        "delay_max_seconds": 30,
        "error_route_max": 2,
        "token_budget_ratio": 0.8
    },
    "actions": {
        "L0": "skip_consensus",
        "L1": "server_normalization",
        "L2": "normal_flow",
        "schema_fail": "safe_mode",
        "delay": "timeout_fallback",
        "token_budget": "early_stop"
    }
}
```

---

## 八、MCP 工具清单

| 工具 | 位置 | 功能 | 备注 |
|------|------|------|------|
| mcp_capability_probe | Server | 探测基础模型能力级别 | Phase 3 |
| mcp_task_router | Server | 任务分级路由 | ✅ Phase 2 |
| mcp_prepare_context | Server | 准备统一上下文 | ✅ Phase 1 |
| **mcp_multi_model_analyze** | ModelRegistry | 多模型并行分析 | 🆕 新增 |
| mcp_consensus_check | Server | 证据比对判定共识 | ✅ Phase 1 |
| mcp_merge_proposals | Server | 归一化合成方案 | ✅ Phase 1 |
| mcp_codex_execute | Codex CLI | 执行编码任务 | ✅ Phase 1 |
| mcp_joint_review | Server | 联合复查 | ✅ Phase 1 |
| mcp_dynamic_fuse | Server | 动态熔断机制 | ✅ Phase 2 |
| mcp_audit_log | Server | 记录决策依据 | ✅ Phase 1 |

---

## 九、Phase 进度

| Phase | 状态 | 测试 | 关键交付 |
|-------|------|------|----------|
| Phase 1 | ✅ 完成 | 29 | 状态机、Schema校验、共识判定 |
| Phase 2 | ✅ 完成 | 69 | TaskRouter、FuseMonitor |
| **Phase 2.5** | ✅ 完成 | 23 | ModelRegistry、多模型框架 |
| Phase 3 | ⏳ 待开始 | - | 能力探针、降级机制 |
| Phase 4 | ⏳ 待开始 | - | 分歧报告、人工介入 |
| Phase 5 | ⏳ 待开始 | - | 验证优化、文档完善 |

---

## 十、后续规划

### 10.1 Phase 3：能力探针和降级（预估 2h）

| 任务 | 描述 |
|------|------|
| P3-T1 | 创建 `capability_probe.py` |
| P3-T2 | 实现 `CAPABILITY_TEST_PROMPTS` |
| P3-T3 | 实现 `mcp_capability_probe` MCP 工具 |
| P3-T4 | 实现降级机制（L0/L1/L2 路径选择） |
| P3-T5 | 集成 `ModelRegistry` 健康检查 |
| P3-T6 | 创建测试文件 |

### 10.2 Phase 4：分歧报告和人工介入（预估 2h）

| 任务 | 描述 |
|------|------|
| P4-T1 | 创建 `divergence_reporter.py` |
| P4-T2 | 多模型分歧汇总模板 |
| P4-T3 | 实现 `mcp_generate_divergence_report` |
| P4-T4 | 实现人工介入触发逻辑 |
| P4-T5 | 集成 ModelRegistry 多模型结果 |
| P4-T6 | 创建测试文件 |

### 10.3 Phase 5：验证和优化（预估 2.5h）

| 任务 | 描述 |
|------|------|
| P5-T1 | 创建 `verification_runner.py` |
| P5-T2 | 实现 `mcp_run_verification` |
| P5-T3 | 整体流程端到端测试 |
| P5-T4 | 性能优化（延迟、Token消耗） |
| P5-T5 | 文档完善（使用指南、API文档） |
| P5-T6 | 最终验收测试 |

---

## 十一、环境变量配置

```bash
# LongCat API
LONGCAT_API_KEY=ak_xxx

# OpenRouter (Qwen)
OPENROUTER_API_KEY=sk-or-v1-xxx

# DeepSeek (示例)
DEEPSEEK_API_KEY=sk-xxx

# Claude (示例)
ANTHROPIC_API_KEY=sk-xxx

# Codex CLI
CODEX_CLI_PATH=codex
```

---

## 十二、测试覆盖

```
Total: 143 tests
├── Phase 1: 29 tests (workflow_state, schema_validator, consensus_checker, mcp_tools)
├── Phase 2: 69 tests (routing_rules: 22, fuse_monitor: 40, mcp_tools: 7)
├── Phase 2.5: 23 tests (model_registry)
└── LongCat: 22 tests (longcat_client)
```

---

## 📅 更新日志

| 日期 | 事件 |
|------|------|
| 2026-04-03 | 三轮共识讨论完成 |
| 2026-04-03 | Phase 1 完成（29 tests） |
| 2026-04-03 | Phase 2 完成（98 tests） |
| 2026-04-03 | LongCat API 接入成功 |
| 2026-04-03 | **架构升级：多模型共识框架** |
| 2026-04-03 | ModelRegistry 完成（143 tests） |