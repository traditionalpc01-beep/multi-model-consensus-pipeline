# Phase 1 开发任务清单

请按照以下顺序实现 Phase 1 核心共识流程。每完成一个步骤请提交 git commit。

## 任务 1: 创建状态机模块 (workflow_state.py)

**文件**: `F:\codex-qwen-pipeline-v2\workflow_state.py`

**要求**:
- 实现 WORKFLOW_STATES 枚举（参考 docs/architecture.md）
- 实现 STATE_TRANSITIONS 迁移规则
- 实现 WorkflowStateMachine 类：
  - `__init__(project_dir)` - 初始化状态机
  - `current_state` - 当前状态属性
  - `can_transition_to(target_state)` - 检查是否可以迁移
  - `transition_to(target_state)` - 执行状态迁移
  - `get_state_history()` - 获取状态历史
- 实现状态持久化到 `.pipeline-state/workflow.json`

**提交**: `git commit -m "feat: add workflow state machine module"`

---

## 任务 2: 创建 JSON Schema 校验模块 (schema_validator.py)

**文件**: `F:\codex-qwen-pipeline-v2\schema_validator.py`

**要求**:
- 实现 JSON_SCHEMAS 字典（包含 analyze_output, consensus_check_output, route_choice, divergence_report）
- 实现 SchemaValidator 类：
  - `validate(schema_name, data)` - 校验数据是否符合 schema
  - `get_validation_errors(schema_name, data)` - 获取详细错误信息
  - `is_valid(schema_name, data)` - 快速校验返回 bool
- 校验失败时返回结构化错误信息

**提交**: `git commit -m "feat: add JSON schema validator module"`

---

## 任务 3: 创建状态存储模块 (state_store.py)

**文件**: `F:\codex-qwen-pipeline-v2\state_store.py`

**要求**:
- 实现 StateStore 类：
  - `__init__(project_dir)` - 初始化存储
  - `save_state(state_dict)` - 保存状态到 JSON
  - `load_state()` - 加载当前状态
  - `append_history(entry)` - 追加历史记录
  - `get_history()` - 获取完整历史
- 状态文件路径: `.pipeline-state/state.json`
- 历史文件路径: `.pipeline-state/history.jsonl`

**提交**: `git commit -m "feat: add state store module"`

---

## 任务 4: 创建共识判定模块 (consensus_checker.py)

**文件**: `F:\codex-qwen-pipeline-v2\consensus_checker.py`

**要求**:
- 实现 consensus_check(qwen_result, codex_result) 函数
- 基于证据比对判定共识（不使用语义相似度）
- 检查三个维度：
  - goal_aligned: 需求理解是否一致
  - constraints_aligned: 约束是否一致
  - implementation_path_aligned: 实现路径是否一致
- 返回 consensus_check_output 格式（符合 Schema）
- 提取分歧点

**提交**: `git commit -m "feat: add consensus checker module"`

---

## 任务 5: 改造主 MCP Server 文件

**文件**: `F:\codex-qwen-pipeline-v2\codex-qwen-mcp-server-v2.py`

**要求**:
- 基于 v1 版本（codex-qwen-mcp-server-v1.py.bak）进行改造
- 导入新增的模块（workflow_state, schema_validator, state_store, consensus_checker）
- 新增 MCP 工具：
  - `mcp_prepare_context` - 准备上下文
  - `mcp_qwen_analyze` - Qwen 分析（改造原 qwen_review）
  - `mcp_codex_analyze` - Codex 分析（新增，使用 codex exec）
  - `mcp_consensus_check` - 共识判定
  - `mcp_merge_proposals` - 方案归一化
  - `mcp_joint_review` - 联合复查
  - `mcp_audit_log` - 审计日志
- 修改 mcp instructions 描述新的工作流程
- 集成状态机控制流程

**提交**: `git commit -m "feat: refactor MCP server with consensus workflow"`

---

## 任务 6: 创建测试文件

**文件**: `F:\codex-qwen-pipeline-v2\tests\test_workflow_state.py`, `test_consensus_checker.py`

**要求**:
- 测试状态机初始化
- 测试状态迁移规则
- 测试共识判定函数
- 测试 Schema 校验

**提交**: `git commit -m "feat: add unit tests for core modules"`

---

## 开发原则

1. **TDD**: 先写测试再写实现
2. **小步提交**: 每个任务完成后立即 git commit
3. **Schema 严格**: 所有输出必须符合 JSON Schema
4. **硬编码优先**: 控制逻辑硬编码，不让模型做开放式推理
5. **熔断机制**: Schema 校验失败触发熔断

---

请开始执行任务 1，创建 workflow_state.py 模块。