# Codex-Qwen Pipeline V2

多模型协作编码管道，基于三轮共识设计。

## 核心设计原则

1. **控制下沉** - 编排逻辑硬编码到 MCP Server，不让基础模型做开放式推理
2. **封闭选择** - 基础模型只做封闭选项选择（route_id、task_class、next_action）
3. **契约约束** - 所有输入输出绑定 JSON Schema，不合格则熔断
4. **分级降级** - L2(完整编排)/L1(只选路)/L0(禁用模型编排)
5. **弱依赖化** - 基础模型成为"可热插拔的弱依赖节点"

## 角色分工

| 角色 | 职责 | 权限 |
|------|------|------|
| Orchestrator (MCP Server) | 确定性路由、状态管理、异常熔断、归一化输出 | 只读 + 编排决策 |
| 基础模型 | 在封闭选项中选择 route_id/next_action | 弱依赖节点 |
| Qwen | 需求边界分析、逻辑正确性、安全合规 | 只读 |
| Codex | 技术可行性评估、代码编写、问题修复 | 写权限 |
| 人工 | 无法收敛分歧时做最终决策 | 全权限 |

## 工作流程

### 阶段一：共识达成（最多3轮）

```
用户需求 → 任务路由 → 并行分析(Qwen+Codex) → 证据比对 → 共识判定
→ 未达成则迭代 → 3轮后仍未统一则人工裁决或Codex结合意见
```

### 阶段二：执行与复查

```
共识方案 → Codex执行编码 → 联合复查 → 通过则完成 → 不通过则修复(最多2次)
```

## 文件结构

```
F:\codex-qwen-pipeline-v2\
├── codex-qwen-mcp-server-v2.py  # 主程序（待开发）
├── codex-qwen-mcp-server-v1.py.bak  # 原版本备份
├── docs/
│   ├── implementation-spec.md  # 实现规格
│   └── consensus-round3.md  # 第三轮共识
├── tests/  # 测试文件（待开发）
├── schemas/  # JSON Schema 定义（待开发）
└── README.md
```

## 开发优先级 (MVP)

### Phase 1（核心共识流程）
- 状态机框架
- JSON Schema 校验中间件
- mcp_prepare_context
- mcp_qwen_analyze
- mcp_codex_analyze
- mcp_consensus_check
- mcp_joint_review
- 状态持久化

### Phase 2（路由和熔断）
- 路由规则表
- mcp_task_router
- 熔断规则表
- mcp_dynamic_fuse

### Phase 3（能力探针）
- mcp_capability_probe
- 降级机制

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| OPENROUTER_API_KEY | ✅ | - | Qwen 审查必需 |
| CODEX_NODE_PATH | ❌ | codex | Codex CLI 路径 |
| QWEN_MODEL | ❌ | qwen/qwen3.6-plus:free | 审查模型 |
| MAX_ITERATIONS | ❌ | 3 | 最大共识轮数 |
| REVIEW_FIX_LIMIT | ❌ | 2 | 自动修复上限 |