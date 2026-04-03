# Codex-Qwen Pipeline V2 - 任务跟踪

## 📊 当前进度

| Phase | 状态 | 完成度 | Codex Session | 备注 |
|-------|------|--------|---------------|------|
| Phase 1 | ✅ 完成 | 100% | 019d523f, 019d5249, 019d5253, 019d5255, 019d525f | 29 tests passed |
| Phase 2 | ⏳ 待开始 | 0% | - | 路由和熔断机制 |
| Phase 3 | ⏳ 待开始 | 0% | - | 能力探针和降级 |
| Phase 4 | ⏳ 待开始 | 0% | - | 分歧报告和人工介入 |
| Phase 5 | ⏳ 待开始 | 0% | - | 验证和优化 |

---

## Phase 1 详情（已完成）

### Git 提交记录

```
1fed2fb feat: refactor MCP server with consensus workflow
2f1cd3c test: add test files for state_store and consensus_checker
8f79eb9 feat: add consensus checker module
f3732c4 feat: add state store module
9920b74 feat: add JSON schema validator module
9c0bb80 feat: add workflow state machine module
7699b84 docs: add Phase 1 development task list
b51aff3 Initial commit: project structure and design specs
```

### Codex Session 日志

| Session ID | 任务 | 执行时间 | 结果 |
|------------|------|----------|------|
| 019d523f-abcc-7cb2-88d0-e461076fda12 | 任务1: workflow_state.py | 超时但完成 | ✅ 创建模块 + 测试 |
| 019d5249-750a-7703-a9f3-78688a5b751b | 任务2: schema_validator.py | 超时但完成 | ✅ 创建模块 + 测试 |
| 019d5253-1f7d-72f1-9e61-7bfba577c331 | 任务3-4规划 | 提出设计方案 | 📝 确认设计后执行 |
| 019d5255-bf2c-7c70-b340-f32afd4822be | 任务3-4执行 | 超时但完成 | ✅ state_store + consensus_checker |
| 019d525f-f1f9-7e73-9fda-470449f27ec4 | 任务5: 主MCP Server | 超时但完成 | ✅ codex-qwen-mcp-server-v2.py |

### 已创建文件

| 文件 | 行数 | 功能 | 测试覆盖 |
|------|------|------|----------|
| workflow_state.py | 132 | 状态机 + 持久化 | ✅ test_workflow_state.py |
| schema_validator.py | ~100 | JSON Schema 校验 | ✅ test_schema_validator.py |
| state_store.py | 50 | 状态持久化 | ✅ test_state_store.py |
| consensus_checker.py | 118 | 共识判定 | ✅ test_consensus_checker.py |
| codex-qwen-mcp-server-v2.py | 672 | 主 MCP Server | ✅ test_mcp_tools.py |

### 测试结果

```
============================= 29 passed in 2.03s ==============================
```

---

## Phase 2 计划（路由和熔断机制）

### 任务清单

| 任务ID | 任务描述 | 预估时间 | 依赖 |
|--------|----------|----------|------|
| P2-T1 | 创建 `routing_rules.py` - 路由规则表 | 15min | Phase 1 |
| P2-T2 | 创建 `fuse_monitor.py` - 熔断监控模块 | 20min | Phase 1 |
| P2-T3 | 实现 `mcp_task_router` - 任务路由工具 | 15min | P2-T1 |
| P2-T4 | 实现 `mcp_dynamic_fuse` - 动态熔断工具 | 20min | P2-T2 |
| P2-T5 | 改造主 MCP Server 集成路由和熔断 | 30min | P2-T3, P2-T4 |
| P2-T6 | 创建测试文件 | 20min | P2-T1-T5 |

### 熔断规则设计

```python
FUSE_RULES = {
    "capability_levels": {
        "L0_threshold": 0.3,  # 能力评分<0.3 则 L0
        "L1_threshold": 0.6,  # 能力评分<0.6 则 L1
        "L2_threshold": 0.8   # 能力评分>=0.8 则 L2
    },
    "runtime": {
        "schema_fail_max": 3,     # JSON Schema 连续失败>3次
        "delay_max_seconds": 30,  # 响应延迟>30秒
        "error_route_max": 2,     # 错误路由>2次
        "token_budget_ratio": 0.8 # Token预算达80%
    },
    "actions": {
        "L0": "skip_consensus_direct_execute",
        "L1": "server_normalization_only",
        "schema_fail": "safe_mode",
        "delay": "timeout_fallback",
        "token_budget": "early_stop"
    }
}
```

---

## Phase 3 计划（能力探针和降级）

### 任务清单

| 任务ID | 任务描述 | 预估时间 | 依赖 |
|--------|----------|----------|------|
| P3-T1 | 创建 `capability_probe.py` - 能力探针模块 | 25min | Phase 2 |
| P3-T2 | 实现 CAPABILITY_TEST_PROMPTS 测试项 | 15min | P3-T1 |
| P3-T3 | 实现 `mcp_capability_probe` MCP 工具 | 20min | P3-T1, P3-T2 |
| P3-T4 | 实现降级机制（L0/L1/L2 三级） | 25min | P3-T3 |
| P3-T5 | 改造主 MCP Server 集成能力探针 | 20min | P3-T3, P3-T4 |
| P3-T6 | 创建测试文件 | 20min | P3-T1-T5 |

### 能力探针测试项

```python
CAPABILITY_TEST_PROMPTS = [
    {
        "name": "json_schema_compliance",
        "prompt": "请根据 JSON Schema 输出结构化数据...",
        "weight": 0.4
    },
    {
        "name": "closed_set_selection",
        "prompt": "从选项 A/B/C 中选择最适合的路径...",
        "weight": 0.3
    },
    {
        "name": "state_passthrough",
        "prompt": "回传状态字段 request_id/step/retry_count...",
        "weight": 0.2
    },
    {
        "name": "abstain_capability",
        "prompt": "不确定时输出 abstain...",
        "weight": 0.1
    }
]
```

---

## Phase 4 计划（分歧报告和人工介入）

### 任务清单

| 任务ID | 任务描述 | 预估时间 | 依赖 |
|--------|----------|----------|------|
| P4-T1 | 创建 `divergence_reporter.py` - 分歧报告模块 | 20min | Phase 3 |
| P4-T2 | 实现 `mcp_generate_divergence_report` 工具 | 15min | P4-T1 |
| P4-T3 | 实现人工介入触发逻辑（HUMAN_ESCALATION） | 20min | Phase 1 状态机 |
| P4-T4 | 创建结构化分歧报告模板 | 15min | P4-T1 |
| P4-T5 | 改造主 MCP Server 集成分歧报告 | 20min | P4-T2, P4-T3 |
| P4-T6 | 创建测试文件 | 20min | P4-T1-T5 |

### 分歧报告 Schema

```json
{
  "divergence_id": 1,
  "dimension": "goal/constraints/implementation_path",
  "qwen_position": "Qwen 的立场",
  "codex_position": "Codex 的立场",
  "evidence_qwen": "Qwen 的证据",
  "evidence_codex": "Codex 的证据",
  "impact_level": "low/medium/high/critical",
  "suggested_resolution": "qwen_win/codex_win/merge/human_decide"
}
```

---

## Phase 5 计划（验证和优化）

### 任务清单

| 任务ID | 任务描述 | 预估时间 | 依赖 |
|--------|----------|----------|------|
| P5-T1 | 创建 `verification_runner.py` - 验证运行器 | 25min | Phase 4 |
| P5-T2 | 实现 `mcp_run_verification` 工具 | 20min | P5-T1 |
| P5-T3 | 整体流程测试（端到端） | 30min | Phase 1-4 |
| P5-T4 | 性能优化（延迟、Token 消耗） | 30min | P5-T3 |
| P5-T5 | 文档完善（使用指南、API 文档） | 30min | Phase 1-4 |
| P5-T6 | 最终验收测试 | 20min | P5-T1-T5 |

### 验证指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| 首次 review 通过率 | > 70% | 统计 joint_review pass 比例 |
| 平均端到端延迟 | < 120s | 从 INIT 到 COMPLETED 的时间 |
| Token 成本 | 控制在预算内 | 统计各阶段 token 消耗 |
| 分歧解决率 | > 90% | 3轮内达成共识的比例 |
| 测试覆盖率 | > 80% | pytest --cov |

---

## 🔄 Codex 执行监控

### 执行模式

当前 Codex 使用 `codex exec --full-auto` 模式执行，特点：
- ✅ 无需人工确认，全自动执行
- ⚠️ 执行时间较长（复杂任务可能超时）
- ⚠️ 超时后需检查是否有部分完成

### 监控指标

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 平均执行时间 | ~180s | < 300s |
| 超时率 | ~60% | < 20% |
| 任务完成率 | 100%（超时后检查） | 100% |
| Git 提交率 | 每任务1次 | 每任务1次 |

### 问题记录

| 问题 | 描述 | 解决方案 |
|------|------|----------|
| PowerShell 编码问题 | 执行 PowerShell 命令时编码报错 | Codex 已自动处理 |
| 超时中断 | 复杂任务执行超时 exit code -1 | 检查 git log 确认部分完成 |
| .tmp-tests 权限警告 | 测试临时目录权限问题 | 不影响测试结果 |

---

## 📅 时间线

| 日期 | 事件 |
|------|------|
| 2026-04-03 | 三轮共识讨论完成（100%共识） |
| 2026-04-03 | Phase 1 开发完成（29 tests passed） |
| 2026-04-03 | Phase 2-5 计划制定完成 |
| TBD | Phase 2 开发开始 |
| TBD | Phase 3-5 开发 |
| TBD | 最终验收 |

---

## 📝 待办事项

- [ ] Phase 2: 路由和熔断机制开发
- [ ] Phase 3: 能力探针和降级机制
- [ ] Phase 4: 分歧报告和人工介入
- [ ] Phase 5: 验证和优化
- [ ] 整体端到端测试
- [ ] 更新 Copaw 配置使用 v2 版本
- [ ] 编写用户使用指南