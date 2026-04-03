# Codex-Qwen Pipeline V2 - 任务跟踪

## 📊 当前进度

| Phase | 状态 | 完成度 | Codex Session | 备注 |
|-------|------|--------|---------------|------|
| Phase 1 | ✅ 完成 | 100% | 5 sessions | 29 tests passed |
| Phase 2 | ✅ 完成 | 100% | 4 sessions | 98 tests passed |
| **Phase 2.5** | ✅ 完成 | 100% | - | 多模型框架 (23 tests) |
| **Phase 2.6** | ✅ 完成 | 100% | - | 多模型共识讨论 + 实现 (21 tests) |
| **Phase 2 Total** | ✅ 完成 | 100% | - | **164 tests passed** |
| Phase 3 | ⏳ 待开始 | 0% | - | 能力探针和降级 |
| Phase 4 | ⏳ 待开始 | 0% | - | 分歧报告和人工介入 |
| Phase 5 | ⏳ 待开始 | 0% | - | 验证和优化 |

## 🏗️ 架构升级

**V2 → V2.5 架构升级：从"双模型"到"多模型"**

| 项目 | 原架构 | 新架构 |
|------|--------|--------|
| 模型数量 | 2 (Codex + Qwen) | N (可扩展) |
| 分发方式 | 手动调用 | `dispatch_consensus()` |
| 模型选择 | 硬编码 | 能力匹配 + 优先级 |
| 扩展性 | 改代码 | 配置驱动 |

### 已接入模型

| 模型 | 提供者 | 优先级 | 每日免费额度 |
|------|--------|--------|-------------|
| Codex CLI | Codex CLI | 10 (最高) | 无限制 |
| LongCat Thinking | LongCat | 30 | 500K |
| LongCat Lite | LongCat | 40 | **50M** |
| Qwen | OpenRouter | 50 | 500K |

---

## Phase 2 详情（进行中）

### 协作模式

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Qwen 编码 + Codex Code Review                             │
└─────────────────────────────────────────────────────────────────────────────┘

Qwen (OpenRouter API)          Codex CLI Review
       │                              │
       ▼                              │
┌──────────────┐                      │
│  生成代码    │                      │
│  模块实现    │                      │
└──────┬───────┘                      │
       │                              │
       ▼                              │
┌──────────────┐                      │
│  写入文件    │                      │
└──────┬───────┘                      │
       │                              │
       ▼                              ▼
┌──────────────┐              ┌──────────────┐
│ git add      │─────────────▶│ codex review │
└──────────────┘              │ --uncommitted │
                              └──────┬───────┘
                                     │
                                ┌────┴────┐
                                │ 通过？   │
                                └────┬────┘
                              是 /    \ 否
                                /      \
                               ▼        ▼
                          git commit   反馈给 Qwen
                                       重新生成
```

### 任务清单

| 任务ID | 任务描述 | 状态 | Qwen生成 | Codex Review |
|--------|----------|------|----------|--------------|
| P2-T1 | 创建 routing_rules.py | ✅ 完成 | ✅ qwen3.6-plus | ✅ 通过 (22 tests) |
| P2-T2 | 创建 fuse_monitor.py | ✅ 完成 | ✅ tech_translator | ✅ 通过 (40 tests) |
| P2-T3 | 实现 mcp_task_router | ✅ 完成 | ✅ tech_translator | ✅ 通过 (3 tests) |
| P2-T4 | 实现 mcp_dynamic_fuse | ✅ 完成 | ✅ tech_translator | ✅ 通过 (4 tests) |
| P2-T5 | 改造主 MCP Server | ✅ 完成 | ✅ tech_translator | ✅ 集成完成 |
| P2-T6 | 创建测试文件 | ✅ 完成 | ✅ tech_translator | ✅ 98 tests passed |

---

## Phase 1 详情（已完成）

### Git 提交记录

```
89ea201 docs: add task tracker for Phase 1-5 progress monitoring
1fed2fb feat: refactor MCP server with consensus workflow
2f1cd3c test: add test files for state_store and consensus_checker
8f79eb9 feat: add consensus checker module
f3732c4 feat: add state store module
9920b74 feat: add JSON schema validator module
9c0bb80 feat: add workflow state machine module
7699b84 docs: add Phase 1 development task list
b51aff3 Initial commit: project structure and design specs
```

### 已创建文件

| 文件 | 行数 | 功能 | 测试覆盖 |
|------|------|------|----------|
| workflow_state.py | 132 | 状态机 + 持久化 | ✅ |
| schema_validator.py | ~100 | JSON Schema 校验 | ✅ |
| state_store.py | 50 | 状态持久化 | ✅ |
| consensus_checker.py | 118 | 共识判定 | ✅ |
| codex-qwen-mcp-server-v2.py | 672 | 主 MCP Server | ✅ |

### 测试结果

```
Phase 1:   29 tests (状态机、Schema、共识)
Phase 2:   69 tests (路由、熔断、MCP工具)
Phase 2.5: 23 tests (多模型框架)
LongCat:   22 tests (LongCat客户端)
Total:     143 tests passed
```

---

## Phase 2.5 详情（已完成）

### 多模型共识框架

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ModelRegistry 多模型注册中心                              │
└─────────────────────────────────────────────────────────────────────────────┘

任务输入 → ModelRegistry.dispatch_consensus()
                    ↓
         ┌─────────┼─────────┬─────────┐
         │         │         │         │
       Qwen    LongCat    Codex    新模型...
         │         │         │         │
         └─────────┴─────────┴─────────┘
                       ↓
              收集所有分析结果
                       ↓
              consensus_check()
                       ↓
              共识判定 / 继续讨论
```

### 已创建文件

| 文件 | 行数 | 功能 | 测试覆盖 |
|------|------|------|----------|
| src/model_registry.py | ~700 | 多模型注册中心 | ✅ 23 tests |
| src/longcat_client.py | ~300 | LongCat API 客户端 | ✅ 22 tests |

### 核心功能

- `ModelRegistry.register()` - 注册新模型
- `ModelRegistry.dispatch_consensus()` - 多模型并行分析
- `ModelRegistry.select_by_capability()` - 按能力选择模型
- `ModelRegistry.check_all_health()` - 健康检查

---

## Phase 2.6 详情（已完成）

### 多模型共识讨论

**参与模型**: LongCat Thinking, LongCat Lite, Qwen

**讨论轮次**: 2轮

**共识状态**: ✅ 完全共识

### 第一轮讨论结果

| 模型 | 可行性 | 主要关切点 |
|------|--------|-----------|
| LongCat Thinking | high | 共识判定逻辑、熔断机制、配额限制 |
| LongCat Lite | high | 高并发稳定性、降级策略、优先级定义 |
| Qwen | medium | 优先级语义、共识判定、成本控制 |

### 第二轮共识结论

| 维度 | 结果 |
|------|------|
| goal_aligned | ✅ True |
| constraints_aligned | ✅ True |
| priority_aligned | ✅ True |
| **共识达成** | ✅ 完全共识 |

### 关键决策

1. **共识算法**: 加权评分 (weighted_score)
   - 质量(40%) + 成本(30%) + 延迟(20%) + 置信度(10%)

2. **优先级定义**: 枚举 (CRITICAL/HIGH/MEDIUM/LOW)
   - 映射到数值: CRITICAL=10, HIGH=30, MEDIUM=50, LOW=70

3. **熔断降级**: 三件套
   - 滑动窗口熔断器 + 健康检查探针 + 多级降级策略

### 熔断降级策略（四级）

| Level | 触发条件 | 动作 |
|-------|----------|------|
| L1 | 超时控制 | 切换备用模型 |
| L2 | 并行失败 | 降级串行调用 |
| L3 | 多模型不可用 | 缓存兜底 |
| L4 | 系统级故障 | 静态响应 |

### 相关文档

- `docs/consensus-v2.5-review.md` - 第一轮讨论记录
- `docs/consensus-round2.md` - 第二轮共识结论

---

## Phase 3-5 计划（待开始）

### Phase 3: 能力探针和降级（预估 2h）

| 任务ID | 任务描述 |
|--------|----------|
| P3-T1 | 创建 capability_probe.py |
| P3-T2 | 实现 CAPABILITY_TEST_PROMPTS |
| P3-T3 | 实现 mcp_capability_probe |
| P3-T4 | 实现降级机制（L0/L1/L2） |
| P3-T5 | 改造主 MCP Server |
| P3-T6 | 创建测试文件 |

### Phase 4: 分歧报告和人工介入（预估 2h）

| 任务ID | 任务描述 |
|--------|----------|
| P4-T1 | 创建 divergence_reporter.py |
| P4-T2 | 实现 mcp_generate_divergence_report |
| P4-T3 | 实现人工介入触发逻辑 |
| P4-T4 | 创建结构化分歧报告模板 |
| P4-T5 | 改造主 MCP Server |
| P4-T6 | 创建测试文件 |

### Phase 5: 验证和优化（预估 2.5h）

| 任务ID | 任务描述 |
|--------|----------|
| P5-T1 | 创建 verification_runner.py |
| P5-T2 | 实现 mcp_run_verification |
| P5-T3 | 整体流程测试 |
| P5-T4 | 性能优化 |
| P5-T5 | 文档完善 |
| P5-T6 | 最终验收测试 |

---

## 🔄 Codex 执行监控

### Phase 1 Session 日志

| Session ID | 任务 | 结果 |
|------------|------|------|
| 019d523f-abcc... | 任务1: workflow_state.py | ✅ 完成 |
| 019d5249-750a... | 任务2: schema_validator.py | ✅ 完成 |
| 019d5253-1f7d... | 任务3-4 规划 | 📝 设计确认 |
| 019d5255-bf2c... | 任务3-4 执行 | ✅ 完成 |
| 019d525f-f1f9... | 任务5: 主MCP Server | ✅ 完成 |

### Phase 2 Review 日志

| 任务ID | Qwen生成 | Codex Review | 结果 |
|--------|----------|--------------|------|
| P2-T1 | ✅ qwen3.6-plus | ✅ 通过 | 22 tests, 修复2个问题 |
| P2-T2 | ✅ tech_translator | ✅ 通过 | 40 tests |
| P2-T3 | ✅ tech_translator | ✅ 通过 | 3 tests |
| P2-T4 | ✅ tech_translator | ✅ 通过 | 4 tests |
| P2-T5 | ✅ tech_translator | ✅ 通过 | MCP Server集成 |
| P2-T6 | ✅ tech_translator | ✅ 通过 | 98 tests total |

### Phase 2 Git 提交记录

```
68a221c feat(phase2): complete MCP Server integration with new tools
8998562 feat(phase2): add mcp_task_router and mcp_dynamic_fuse tools
d0d6b32 feat(phase2): add FuseMonitor module for runtime fuse monitoring
5650c96 docs: update task tracker for P2-T1 completion
23d7136 feat(phase2): add TaskRouter module with Qwen-generated code
```

---

## 📅 时间线

| 日期 | 事件 |
|------|------|
| 2026-04-03 | Phase 1 开发完成（29 tests passed） |
| 2026-04-03 | Phase 2 开始（Qwen编码 + Codex Review） |
| 2026-04-03 | P2-T1 完成：routing_rules.py (22 tests) |
| 2026-04-03 | Phase 2 完成：全部6个任务 (98 tests) |
| 2026-04-03 | LongCat API 接入成功 |
| 2026-04-03 | **架构升级：多模型共识框架** |
| 2026-04-03 | Phase 2.5 完成：ModelRegistry (143 tests) |
| 2026-04-03 | **Phase 2.6 完成：两轮多模型共识讨论** |
| 2026-04-03 | - 第一轮：识别关切点（共识判定、熔断、优先级） |
| 2026-04-03 | - 第二轮：达成完全共识（加权评分+枚举优先级） |
| TBD | Phase 3 开发：能力探针和降级机制 |