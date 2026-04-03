# Codex-Qwen Pipeline V2 - 实现规格

## 一、状态机设计

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

### 状态迁移规则

```python
STATE_TRANSITIONS = {
    "INIT": ["PROBING"],
    "PROBING": ["ROUTING", "FUSED"],
    "ROUTING": ["CONSENSUS_ROUND_1", "FINAL_PLAN", "FUSED"],
    "CONSENSUS_ROUND_1": ["CONSENSUS_ROUND_2", "FINAL_PLAN", "CONSENSUS_TIMEOUT"],
    "CONSENSUS_ROUND_2": ["CONSENSUS_ROUND_3", "FINAL_PLAN", "CONSENSUS_TIMEOUT"],
    "CONSENSUS_ROUND_3": ["CONSENSUS_TIMEOUT", "FINAL_PLAN"],
    "CONSENSUS_TIMEOUT": ["HUMAN_ESCALATION", "FINAL_PLAN"],
    "FINAL_PLAN": ["EXECUTING"],
    "EXECUTING": ["REVIEWING"],
    "REVIEWING": ["COMPLETED", "REVIEW_FIX_1", "REVIEW_TIMEOUT"],
    "REVIEW_FIX_1": ["REVIEWING", "REVIEW_FIX_2", "REVIEW_TIMEOUT"],
    "REVIEW_FIX_2": ["REVIEWING", "REVIEW_TIMEOUT"],
    "REVIEW_TIMEOUT": ["HUMAN_ESCALATION"],
    "FUSED": ["HUMAN_ESCALATION"],
    "HUMAN_ESCALATION": ["FINAL_PLAN", "COMPLETED", "FUSED"]
}
```

## 二、路由规则表

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

## 三、熔断规则表

```python
FUSE_RULES = {
    "capability_levels": {
        "L0_threshold": 0.3,
        "L1_threshold": 0.6,
        "L2_threshold": 0.8
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
        "schema_fail": "safe_mode",
        "delay": "timeout_fallback",
        "token_budget": "early_stop"
    }
}
```

## 四、JSON Schema 定义

### analyze_output

```json
{
  "type": "object",
  "required": ["opinion", "key_points", "concerns", "suggestions", "feasibility"],
  "properties": {
    "opinion": {"type": "string"},
    "key_points": {"type": "array", "items": {"type": "string"}},
    "concerns": {"type": "array", "items": {"type": "string"}},
    "suggestions": {"type": "array", "items": {"type": "string"}},
    "feasibility": {"type": "string", "enum": ["high", "medium", "low"]}
  },
  "additionalProperties": false
}
```

### consensus_check_output

```json
{
  "type": "object",
  "required": ["consensus_reached", "consensus_points", "divergence_points", "evidence_comparison"],
  "properties": {
    "consensus_reached": {"type": "boolean"},
    "consensus_points": {"type": "array"},
    "divergence_points": {"type": "array"},
    "evidence_comparison": {
      "type": "object",
      "properties": {
        "goal_aligned": {"type": "boolean"},
        "constraints_aligned": {"type": "boolean"},
        "implementation_path_aligned": {"type": "boolean"}
      }
    }
  },
  "additionalProperties": false
}
```

### route_choice

```json
{
  "type": "object",
  "required": ["route_id", "task_class", "next_action"],
  "properties": {
    "route_id": {"type": "string", "enum": ["direct_execution", "consensus_1_round", "consensus_3_rounds"]},
    "task_class": {"type": "string", "enum": ["simple", "moderate", "complex"]},
    "next_action": {"type": "string", "enum": ["analyze", "execute", "fallback", "abstain", "need_human"]}
  },
  "additionalProperties": false
}
```

## 五、MCP 工具清单

| 工具 | 位置 | 功能 |
|------|------|------|
| mcp_capability_probe | Server 100% | 探测基础模型能力级别 |
| mcp_task_router | Server 80% + 模型选路 | 任务分级路由 |
| mcp_prepare_context | Server 100% | 准备统一上下文 |
| mcp_qwen_analyze | Qwen API | Qwen 分析需求和方案 |
| mcp_codex_analyze | Codex CLI | Codex 评估可行性和约束 |
| mcp_merge_proposals | Server 90% | 归一化合成候选方案 |
| mcp_consensus_check | Server 100% | 证据比对判定共识 |
| mcp_generate_divergence_report | Server 100% | 输出结构化分歧报告 |
| mcp_codex_execute | Codex CLI | 执行编码任务 |
| mcp_joint_review | Qwen + Server | 联合复查 |
| mcp_run_verification | Server 100% | 执行测试/lint/build |
| mcp_dynamic_fuse | Server 100% | 动态熔断机制 |
| mcp_audit_log | Server 100% | 记录决策依据 |

## 六、Phase 1 实现步骤

### Step 1: 状态机框架

创建 `workflow_state.py`，实现：
- WorkflowStateMachine 类
- 状态迁移验证
- 状态持久化

### Step 2: JSON Schema 校验中间件

创建 `schema_validator.py`，实现：
- validate_output(schema_name, data) 函数
- Schema 加载和校验
- 错误处理和熔断触发

### Step 3: 核心 MCP 工具

修改主文件，添加：
- mcp_prepare_context
- mcp_qwen_analyze
- mcp_codex_analyze
- mcp_consensus_check
- mcp_joint_review

### Step 4: 状态持久化

创建 `state_store.py`，实现：
- StateStore 类
- JSON 文件读写
- 历史记录追加

## 七、测试计划

每个工具需要对应的测试文件：
- tests/test_workflow_state.py
- tests/test_schema_validator.py
- tests/test_consensus_check.py
- tests/test_mcp_tools.py