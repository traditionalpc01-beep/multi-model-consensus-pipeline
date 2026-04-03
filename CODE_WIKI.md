# Multi-Model Consensus Pipeline Code Wiki

> 多模型协作编码管道 - 基于三轮共识设计的 AI 编码工作流

## 目录
- [项目概述](#项目概述)
- [系统架构](#系统架构)
- [核心模块详解](#核心模块详解)
- [关键类与函数](#关键类与函数)
- [依赖关系](#依赖关系)
- [配置与环境](#配置与环境)
- [运行方式](#运行方式)
- [测试说明](#测试说明)

---

## 项目概述

### 项目简介
这是一个**确定性编排**的多模型协作框架，通过三轮共识机制确保代码质量。项目将编排逻辑硬编码到 MCP Server，不让基础模型做开放式推理，而是让它们只做封闭选项选择。

### 核心设计理念
1. **控制下沉** - 编排逻辑硬编码到 MCP Server
2. **封闭选择** - 基础模型只做封闭选项选择
3. **契约约束** - 所有输入输出绑定 JSON Schema
4. **分级降级** - L2(完整编排)/L1(只选路)/L0(禁用模型编排)
5. **弱依赖化** - 基础模型成为"可热插拔的弱依赖节点"

### 已接入模型
| 模型 | 提供者 | 优先级 | 每日免费额度 | 用途 |
|------|--------|--------|-------------|------|
| Codex CLI | OpenAI | 10 (最高) | 无限制 | 代码编写、技术可行性评估 |
| LongCat Thinking | LongCat | 30 | 500K | 深度分析、共识讨论 |
| LongCat Lite | LongCat | 40 | 50M | 快速分析、备用 |
| Qwen | OpenRouter | 50 | 500K | 需求分析、安全合规审查 |

---

## 系统架构

### 整体架构图
```
用户需求
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                    MCP Server 编排层                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │TaskRouter│  │FuseMonit │  │SchemaVld │  │Workflow │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
└───────┼──────────────┼──────────────┼──────────────┼──────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                    多模型共识层                          │
│  ┌────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐ │
│  │ Qwen   │  │ LongCat  │  │  Codex  │  │ Consensus│ │
│  │分析    │  │ 分析     │  │  分析    │  │  Checker │ │
│  └────────┘  └──────────┘  └─────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────┘
        │              │              │              │
        └──────────────┴──────────────┴──────────────┘
                              │
                              ▼
                    ┌──────────────┐
                    │  最终方案执行  │
                    │  Codex CLI    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  联合复查     │
                    │  修复/完成    │
                    └──────────────┘
```

### 工作流程
#### 阶段一：共识达成（最多3轮）
```
用户需求 → 任务路由 → 并行分析(多模型) → 证据比对 → 共识判定 → Codex执行 → 联合复查
```

#### 阶段二：执行与复查
```
共识方案 → Codex执行编码 → 联合复查 → 通过则完成 → 不通过则修复(最多2次)
```

---

## 核心模块详解

### 1. MCP Server 入口模块
**文件**: [codex-qwen-mcp-server-v2.py](file:///workspace/codex-qwen-mcp-server-v2.py)

这是整个系统的主入口点，基于 FastMCP 框架构建，提供了完整的 MCP 工具接口。

**主要功能**:
- 初始化和管理工作流状态
- 提供 MCP 工具供外部调用
- 协调各个模块的执行顺序
- 处理状态持久化和审计日志

**核心 MCP 工具**:
- `mcp_prepare_context` - 初始化状态、收集上下文、选择路由
- `mcp_task_router` - 基于关键词的任务路由
- `mcp_dynamic_fuse` - 监控运行时限制并触发熔断动作
- `mcp_qwen_analyze` - 运行 Qwen 分析并验证输出
- `mcp_codex_analyze` - 运行 Codex 分析并验证输出
- `mcp_consensus_check` - 比较分析结果、推进工作流状态
- `mcp_merge_proposals` - 合并对齐的证据到最终方案
- `mcp_joint_review` - 标准化复查信号驱动完成状态
- `mcp_audit_log` - 追加结构化审计事件

---

### 2. 模型注册中心
**文件**: [src/model_registry.py](file:///workspace/src/model_registry.py)

这是多模型管理的核心模块，采用单例模式设计，负责模型的注册、选择、健康检查和共识调度。

**核心组件**:
- `ModelCapability` (枚举) - 定义模型能力类型
- `ModelStatus` (枚举) - 定义模型状态
- `ModelConfig` (数据类) - 模型配置结构
- `ModelHealth` (数据类) - 模型健康状态
- `ModelProvider` (抽象基类) - 模型提供者接口
- `OpenAICompatibleProvider` - OpenAI API 兼容提供者
- `CodexCLIProvider` - Codex CLI 专用提供者
- `ModelRegistry` - 模型注册中心（单例）

**关键功能**:
- 支持动态注册新模型
- 配置文件驱动的模型加载
- 基于能力和优先级的模型选择
- 健康状态监控
- 多模型共识任务分发

---

### 3. 任务路由模块
**文件**: [src/routing_rules.py](file:///workspace/src/routing_rules.py)

负责根据任务描述自动进行分级路由，将任务分配到不同的处理流程。

**任务分类**:
| 类别 | 路由 ID | 关键词 | 最大上下文文件数 |
|------|---------|--------|-----------------|
| simple | direct_execution | fix, update, change, adjust, modify, add | 3 |
| moderate | consensus_1_round | implement, build, develop, integrate, refactor | 10 |
| complex | consensus_3_rounds | architecture, rewrite, replace, migrate, core | 30 |

**核心组件**:
- `TaskRouter` - 任务路由器类
- `route_task` - 便捷路由函数

---

### 4. 熔断监控模块
**文件**: [src/fuse_monitor.py](file:///workspace/src/fuse_monitor.py)

监控运行时指标，在达到阈值时触发相应的熔断动作，确保系统稳定性。

**熔断规则配置**:
```python
FUSE_RULES = {
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
    }
}
```

**核心组件**:
- `FuseMonitor` - 熔断监控器类

**监控指标**:
- 能力等级检测 (L0/L1/L2)
- Schema 失败次数
- 延迟超时
- Token 预算使用
- 错误路由次数

---

### 5. 工作流状态机
**文件**: [workflow_state.py](file:///workspace/workflow_state.py)

管理整个编码工作流的状态转换，确保流程按预定顺序执行。

**工作流状态**:
| 状态 | 描述 |
|------|------|
| INIT | 初始化 |
| PROBING | 能力探测 |
| ROUTING | 任务路由 |
| CONSENSUS_ROUND_1 | 共识第一轮 |
| CONSENSUS_ROUND_2 | 共识第二轮 |
| CONSENSUS_ROUND_3 | 共识第三轮 |
| CONSENSUS_TIMEOUT | 共识超时 |
| FINAL_PLAN | 最终方案生成 |
| EXECUTING | 执行编码 |
| REVIEWING | 联合复查 |
| REVIEW_FIX_1 | 修复第1轮 |
| REVIEW_FIX_2 | 修复第2轮 |
| REVIEW_TIMEOUT | 修复超时 |
| COMPLETED | 完成 |
| FUSED | 熔断终止 |
| HUMAN_ESCALATION | 人工介入 |

**核心组件**:
- `WorkflowStateMachine` - 工作流状态机类
- `InvalidWorkflowStateError` - 无效工作流状态异常
- `InvalidStateTransitionError` - 无效状态转换异常

---

### 6. 共识判定模块
**文件**: [consensus_checker.py](file:///workspace/consensus_checker.py)

负责比较多个模型的分析结果，判定是否达成共识，并识别分歧点。

**比较维度**:
- `goal` - 目标一致性
- `constraints` - 约束条件一致性
- `implementation_path` - 实现路径一致性

**核心函数**:
- `consensus_check` - 执行共识检查
- `_compare_dimension` - 比较单个维度
- `_collect_evidence` - 收集证据
- `_normalize_text` - 文本归一化

---

### 7. Schema 验证模块
**文件**: [schema_validator.py](file:///workspace/schema_validator.py)

使用 JSON Schema 对所有输入输出进行严格验证，确保数据格式符合预期。

**预定义 Schema**:
| Schema 名称 | 用途 |
|------------|------|
| analyze_output | 模型分析输出验证 |
| consensus_check_output | 共识检查输出验证 |
| route_choice | 路由选择验证 |
| divergence_report | 分歧报告验证 |

**核心组件**:
- `SchemaValidator` - Schema 验证器类
- `UnknownSchemaError` - 未知 Schema 异常
- `SchemaValidationError` - Schema 验证异常

---

### 8. 状态持久化模块
**文件**: [state_store.py](file:///workspace/state_store.py)

负责工作流状态和审计历史的持久化存储。

**存储结构**:
```
.pipeline-state/
├── state.json      # 当前工作流状态
└── history.jsonl   # 审计历史（JSON Lines 格式）
```

**核心组件**:
- `StateStore` - 状态存储类

---

### 9. 加权共识模块
**文件**: [src/weighted_consensus.py](file:///workspace/src/weighted_consensus.py)

提供基于多维度评分的加权共识计算。

**权重配置**:
| 指标 | 权重 |
|------|------|
| quality | 0.40 |
| cost | 0.30 |
| latency | 0.20 |
| confidence | 0.10 |

**共识阈值**:
- FULL_THRESHOLD = 0.75 (完全共识)
- PARTIAL_THRESHOLD = 0.50 (部分共识)

**核心组件**:
- `ModelResponse` (数据类) - 模型响应
- `ConsensusResult` (数据类) - 共识结果
- `WeightedScoreConsensus` - 加权共识计算器

---

### 10. LongCat 客户端
**文件**: [src/longcat_client.py](file:///workspace/src/longcat_client.py)

LongCat API 专用客户端，兼容 OpenAI API 格式。

**支持的模型**:
| 模型类型 | 模型名称 | 描述 | 最大 Token | 每日免费额度 |
|---------|---------|------|-----------|-------------|
| thinking | LongCat-Flash-Thinking-2601 | 深度思考模型 | 256000 | 500K |
| chat | LongCat-Flash-Chat | 高性能通用对话 | 256000 | 500K |
| lite | LongCat-Flash-Lite | 高效轻量化MoE | 320000 | 50M |
| omni | LongCat-Flash-Omni-2603 | 多模态模型 | 8000 | 500K |

**核心组件**:
- `LongCatClient` - LongCat 客户端类
- `invoke_longcat` - 便捷调用函数

---

### 11. 降级管理器
**文件**: [src/fallback_manager.py](file:///workspace/src/fallback_manager.py)

提供四级降级策略，在服务失败时逐步降级处理。

**降级级别**:
| 级别 | 名称 | 策略 |
|------|------|------|
| L1 | MODEL_FALLBACK | 超时/错误时切换到备用模型 |
| L2 | PARALLEL_FALLBACK | 并行失败时降级为串行执行 |
| L3 | CACHE_FALLBACK | 多模型不可用时使用缓存响应 |
| L4 | STATIC_FALLBACK | 系统级故障时返回静态默认值 |

**核心组件**:
- `FallbackLevel` (枚举) - 降级级别
- `FallbackResult` (数据类) - 降级结果
- `FallbackManager` - 降级管理器

---

## 关键类与函数

### ModelRegistry 类

**核心方法**:
- `__init__()` - 初始化注册中心，加载默认模型
- `register(config: ModelConfig)` - 注册新模型
- `register_from_config_file(config_path)` - 从配置文件批量注册
- `get_provider(name)` - 获取模型提供者
- `select_by_capability(capability)` - 按能力选择模型
- `select_best_for_task(task_type)` - 选择最佳模型
- `check_all_health()` - 检查所有模型健康状态
- `dispatch_consensus(task, context, models)` - 分发共识任务

**使用示例**:
```python
from src.model_registry import ModelRegistry, ModelCapability

registry = ModelRegistry()

# 列出所有模型
print(registry.list_models())

# 选择共识模型
consensus_models = registry.get_consensus_models()

# 分发共识任务
results = registry.dispatch_consensus(
    task="实现用户登录功能",
    context={"project": "web-app"}
)
```

---

### TaskRouter 类

**核心方法**:
- `route(task_description)` - 执行路由判断
- `get_route_id(task_class)` - 获取路由 ID
- `get_max_context_files(task_class)` - 获取最大上下文文件数

**使用示例**:
```python
from src.routing_rules import TaskRouter

router = TaskRouter()
result = router.route("实现用户认证模块")

print(f"Route ID: {result['route_id']}")
print(f"Task Class: {result['task_class']}")
print(f"Confidence: {result['confidence']}")
```

---

### FuseMonitor 类

**核心方法**:
- `check_capability_level(score)` - 判定能力等级
- `get_capability_action(level)` - 获取熔断动作
- `check_schema_fail(fail_count)` - 检查 Schema 失败
- `check_delay(elapsed_seconds)` - 检查延迟
- `check_token_budget(used, total)` - 检查 Token 预算
- `check_all_limits(used_tokens, total_tokens)` - 综合检查

**使用示例**:
```python
from src.fuse_monitor import FuseMonitor

monitor = FuseMonitor()

# 检查能力等级
level = monitor.check_capability_level(0.85)
action = monitor.get_capability_action(level)

# 综合状态检查
status = monitor.check_all_limits(used_tokens=85000, total_tokens=100000)
print(f"Fuse triggered: {status['any_fuse_triggered']}")
```

---

### WorkflowStateMachine 类

**核心方法**:
- `__init__(project_dir)` - 初始化状态机
- `can_transition_to(target_state)` - 检查是否可转换
- `transition_to(target_state)` - 执行状态转换
- `get_state_history()` - 获取状态历史

**使用示例**:
```python
from workflow_state import WorkflowStateMachine

machine = WorkflowStateMachine("/path/to/project")

# 检查是否可以转换
if machine.can_transition_to("CONSENSUS_ROUND_1"):
    machine.transition_to("CONSENSUS_ROUND_1")

# 获取当前状态
print(f"Current state: {machine.current_state}")
```

---

### SchemaValidator 类

**核心方法**:
- `validate(schema_name, data)` - 验证数据
- `get_validation_errors(schema_name, data)` - 获取验证错误
- `is_valid(schema_name, data)` - 检查是否有效

**使用示例**:
```python
from schema_validator import SchemaValidator, validate_output

validator = SchemaValidator()

# 验证数据
data = {
    "opinion": "这是一个可行的方案",
    "key_points": ["点1", "点2"],
    "concerns": [],
    "suggestions": [],
    "feasibility": "high"
}

validated = validate_output("analyze_output", data)
```

---

## 依赖关系

### 内部模块依赖图
```
codex-qwen-mcp-server-v2.py (主入口)
├── consensus_checker.py
│   └── schema_validator.py
├── schema_validator.py
├── state_store.py
├── workflow_state.py
├── src/routing_rules.py
├── src/fuse_monitor.py
├── src/model_registry.py
│   └── src/priority_level.py
├── src/longcat_client.py
├── src/weighted_consensus.py
└── src/fallback_manager.py
```

### 外部依赖
主要依赖（基于代码推断）:
- `fastmcp` - MCP Server 框架
- `openai` - OpenAI API 客户端
- `jsonschema` - JSON Schema 验证
- `python >= 3.11`

---

## 配置与环境

### 必需环境变量
| 变量 | 说明 |
|------|------|
| `OPENROUTER_API_KEY` | Qwen 审查必需 |
| `LONGCAT_API_KEY` | LongCat 模型访问 |

### 可选环境变量
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CODEX_CLI_PATH` | `codex` | Codex CLI 路径 |
| `QWEN_MODEL` | `qwen/qwen3.6-plus:free` | 审查模型 |
| `MAX_ITERATIONS` | `3` | 最大共识轮数 |
| `REVIEW_FIX_LIMIT` | `2` | 自动修复上限 |
| `CODEX_TIMEOUT` | `600` | Codex 超时（秒） |
| `QWEN_MAX_TOKENS` | `4096` | Qwen 最大 Token |
| `CONTEXT_CHAR_LIMIT` | `4000` | 上下文字符限制 |

---

## 运行方式

### 安装依赖
```bash
# 克隆仓库
cd /workspace

# 安装依赖（假设有 requirements.txt）
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API Keys
```

### 启动 MCP Server
```bash
python codex-qwen-mcp-server-v2.py
```

### 快速开始示例
```python
from src.model_registry import ModelRegistry
from workflow_state import WorkflowStateMachine

# 初始化模型注册中心
registry = ModelRegistry()

# 分发共识任务
results = registry.dispatch_consensus(
    task="实现用户登录功能",
    context={"project": "web-app", "language": "python"}
)

# 检查共识状态
for model_name, result in results.items():
    print(f"{model_name}: {result.get('success', False)}")
```

---

## 测试说明

### 运行测试
项目包含 164 个测试用例，覆盖主要功能模块。

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_model_registry.py -v
pytest tests/test_routing_rules.py -v
pytest tests/test_fuse_monitor.py -v

# 查看覆盖率
pytest tests/ --cov=src --cov-report=html
```

### 测试文件列表
| 测试文件 | 覆盖模块 |
|---------|---------|
| [test_consensus_checker.py](file:///workspace/tests/test_consensus_checker.py) | consensus_checker.py |
| [test_fuse_monitor.py](file:///workspace/tests/test_fuse_monitor.py) | src/fuse_monitor.py |
| [test_longcat_client.py](file:///workspace/tests/test_longcat_client.py) | src/longcat_client.py |
| [test_mcp_tools.py](file:///workspace/tests/test_mcp_tools.py) | codex-qwen-mcp-server-v2.py |
| [test_model_registry.py](file:///workspace/tests/test_model_registry.py) | src/model_registry.py |
| [test_p2_6.py](file:///workspace/tests/test_p2_6.py) | Phase 2.6 功能 |
| [test_routing_rules.py](file:///workspace/tests/test_routing_rules.py) | src/routing_rules.py |
| [test_schema_validator.py](file:///workspace/tests/test_schema_validator.py) | schema_validator.py |
| [test_state_store.py](file:///workspace/tests/test_state_store.py) | state_store.py |
| [test_workflow_state.py](file:///workspace/tests/test_workflow_state.py) | workflow_state.py |

---

## 开发进度

| Phase | 状态 | 完成度 | 描述 |
|-------|------|--------|------|
| Phase 1 | ✅ 完成 | 100% | 核心共识流程 |
| Phase 2 | ✅ 完成 | 100% | 路由和熔断 |
| Phase 2.5 | ✅ 完成 | 100% | 多模型框架 |
| Phase 2.6 | ✅ 完成 | 100% | 多模型共识讨论 |
| Phase 3 | ⏳ 待开始 | 0% | 能力探针和降级 |
| Phase 4 | ⏳ 待开始 | 0% | 分歧报告和人工介入 |
| Phase 5 | ⏳ 待开始 | 0% | 验证和优化 |

---

## 相关文档

- [README.md](file:///workspace/README.md) - 项目主文档
- [docs/implementation-spec.md](file:///workspace/docs/implementation-spec.md) - 实现规格
- [docs/architecture-v2.md](file:///workspace/docs/architecture-v2.md) - 架构设计 V2
- [docs/consensus-v2.5-review.md](file:///workspace/docs/consensus-v2.5-review.md) - 多模型共识讨论
- [docs/TASK-TRACKER.md](file:///workspace/docs/TASK-TRACKER.md) - 任务追踪

---

## License

MIT License - 详见 [LICENSE](file:///workspace/LICENSE) 文件
