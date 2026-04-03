# Multi-Model Consensus Pipeline

> 多模型协作编码管道 - 基于三轮共识设计的 AI 编码工作流

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 164 passed](https://img.shields.io/badge/tests-164%20passed-brightgreen.svg)](tests/)

## 🎯 项目简介

这是一个**确定性编排**的多模型协作框架，通过三轮共识机制确保代码质量：

```
用户需求 → 任务路由 → 并行分析(多模型) → 证据比对 → 共识判定 → Codex执行 → 联合复查
```

### 核心特性

- **控制下沉** - 编排逻辑硬编码到 MCP Server，不让基础模型做开放式推理
- **封闭选择** - 基础模型只做封闭选项选择（route_id、task_class、next_action）
- **契约约束** - 所有输入输出绑定 JSON Schema，不合格则熔断
- **分级降级** - L2(完整编排)/L1(只选路)/L0(禁用模型编排)
- **弱依赖化** - 基础模型成为"可热插拔的弱依赖节点"

## 🤖 已接入模型

| 模型 | 提供者 | 优先级 | 每日免费额度 | 用途 |
|------|--------|--------|-------------|------|
| Codex CLI | OpenAI | 10 (最高) | 无限制 | 代码编写、技术可行性评估 |
| LongCat Thinking | LongCat | 30 | 500K | 深度分析、共识讨论 |
| LongCat Lite | LongCat | 40 | **50M** | 快速分析、备用 |
| Qwen | OpenRouter | 50 | 500K | 需求分析、安全合规审查 |

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/multi-model-consensus-pipeline.git
cd multi-model-consensus-pipeline

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API Keys
```

### 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENROUTER_API_KEY` | ✅ | - | Qwen 审查必需 |
| `LONGCAT_API_KEY` | ✅ | - | LongCat 模型访问 |
| `CODEX_NODE_PATH` | ❌ | `codex` | Codex CLI 路径 |
| `QWEN_MODEL` | ❌ | `qwen/qwen3.6-plus:free` | 审查模型 |
| `MAX_ITERATIONS` | ❌ | `3` | 最大共识轮数 |
| `REVIEW_FIX_LIMIT` | ❌ | `2` | 自动修复上限 |

## 🚀 快速开始

```python
from src.model_registry import ModelRegistry
from src.workflow_state import WorkflowStateMachine

# 初始化模型注册中心
registry = ModelRegistry()

# 注册模型
registry.register("qwen", qwen_adapter, priority=50)
registry.register("longcat", longcat_adapter, priority=30)

# 分发共识任务
result = registry.dispatch_consensus(
    task="实现用户登录功能",
    context={"project": "web-app", "language": "python"}
)

# 检查共识状态
if result.consensus_level == "full":
    print("✅ 完全共识，可以执行")
else:
    print("⚠️ 需要进一步讨论")
```

## 📁 项目结构

```
multi-model-consensus-pipeline/
├── src/
│   ├── __init__.py
│   ├── model_registry.py      # 多模型注册中心
│   ├── longcat_client.py      # LongCat API 客户端
│   ├── routing_rules.py       # 任务路由规则
│   ├── fuse_monitor.py        # 熔断监控器
│   ├── weighted_consensus.py  # 加权共识算法
│   ├── priority_level.py      # 优先级枚举
│   └── fallback_manager.py    # 降级管理器
├── tests/
│   ├── test_model_registry.py
│   ├── test_routing_rules.py
│   ├── test_fuse_monitor.py
│   └── ...                    # 共 164 个测试
├── docs/
│   ├── implementation-spec.md # 实现规格
│   ├── architecture-v2.md     # 架构设计
│   ├── consensus-round3.md     # 第三轮共识
│   └── TASK-TRACKER.md        # 任务追踪
├── workflow_state.py          # 状态机
├── consensus_checker.py       # 共识判定器
├── schema_validator.py        # JSON Schema 校验
├── state_store.py             # 状态持久化
└── codex-qwen-mcp-server-v2.py # 主 MCP Server
```

## 🔄 工作流程

### 阶段一：共识达成（最多3轮）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         共识达成流程                                     │
└─────────────────────────────────────────────────────────────────────────┘

用户需求
    │
    ▼
┌──────────────┐
│  任务路由    │ ─── 根据任务类型分发给合适的模型组合
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│         并行分析 (多模型)                  │
│  ┌────────┐  ┌────────┐  ┌────────┐     │
│  │ Qwen   │  │LongCat │  │ Codex  │     │
│  └────────┘  └────────┘  └────────┘     │
│       │           │           │          │
│       └───────────┴───────────┘          │
│                   │                      │
└───────────────────┼──────────────────────┘
                    ▼
           ┌──────────────┐
           │  证据比对    │
           └──────┬───────┘
                  │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
   ┌─────────┐      ┌──────────┐
   │ 共识？  │─ 否 ─▶│ 继续讨论 │ ── 返回分析（最多3轮）
   └────┬────┘      └──────────┘
        │ 是
        ▼
   ┌─────────┐
   │ 执行    │
   └─────────┘
```

### 阶段二：执行与复查

```
共识方案 → Codex执行编码 → 联合复查 → 通过则完成 → 不通过则修复(最多2次)
```

## 🛡️ 熔断降级策略

| Level | 触发条件 | 动作 |
|-------|----------|------|
| L0 | 正常运行 | 完整多模型编排 |
| L1 | 单模型超时 | 切换备用模型 |
| L2 | 并行失败 | 降级串行调用 |
| L3 | 多模型不可用 | 缓存兜底 |
| L4 | 系统级故障 | 静态响应 |

## 📊 开发进度

| Phase | 状态 | 完成度 | 描述 |
|-------|------|--------|------|
| Phase 1 | ✅ 完成 | 100% | 核心共识流程 |
| Phase 2 | ✅ 完成 | 100% | 路由和熔断 |
| Phase 2.5 | ✅ 完成 | 100% | 多模型框架 |
| Phase 2.6 | ✅ 完成 | 100% | 多模型共识讨论 |
| Phase 3 | ⏳ 待开始 | 0% | 能力探针和降级 |
| Phase 4 | ⏳ 待开始 | 0% | 分歧报告和人工介入 |
| Phase 5 | ⏳ 待开始 | 0% | 验证和优化 |

**测试覆盖**: 164 tests passed ✅

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_model_registry.py -v
pytest tests/test_routing_rules.py -v

# 查看覆盖率
pytest tests/ --cov=src --cov-report=html
```

## 📖 文档

- [实现规格](docs/implementation-spec.md)
- [架构设计 V2](docs/architecture-v2.md)
- [多模型共识讨论](docs/consensus-v2.5-review.md)
- [任务追踪](docs/TASK-TRACKER.md)

## 🤝 角色分工

| 角色 | 职责 | 权限 |
|------|------|------|
| **Orchestrator** (MCP Server) | 确定性路由、状态管理、异常熔断 | 只读 + 编排决策 |
| **基础模型** | 在封闭选项中选择 route_id/next_action | 弱依赖节点 |
| **Qwen** | 需求边界分析、逻辑正确性、安全合规 | 只读 |
| **Codex** | 技术可行性评估、代码编写、问题修复 | 写权限 |
| **人工** | 无法收敛分歧时做最终决策 | 全权限 |

## 📝 License

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

本项目基于以下理念构建：
- **Superpowers** - 强制流程优于建议流程
- **TDD** - 测试驱动开发
- **确定性编排** - 控制下沉，契约约束