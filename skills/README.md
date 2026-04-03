# Multi-Model Consensus Skill

多模型共识编排Skill - 将原项目的核心能力封装为独立的单文件Skill版本。

## 核心功能

### 1. 任务路由 (TaskRouter)
根据任务描述自动进行分级路由，支持simple/moderate/complex三个级别。

### 2. 能力探测 (CapabilityProbe)
根据能力分数判断执行路径（L0/L1/L2）。

### 3. 共识引擎 (ConsensusEngine)
比较多模型分析结果，判定是否达成共识。

### 4. 工作流状态 (WorkflowState)
管理工作流状态和历史记录，支持持久化存储。

### 5. 熔断监控 (FuseMonitor)
监控运行时指标，在达到阈值时触发熔断动作。

### 6. 降级管理 (FallbackManager)
提供四级降级策略，确保系统稳定性。

## 快速开始

```python
from skills.multi_model_consensus_skill import MultiModelConsensusSkill

# 初始化Skill
skill = MultiModelConsensusSkill()

# 准备上下文
result = skill.prepare_context(
    task="实现用户认证模块",
    context_files=["auth.py", "user.py"]
)

# 探测能力
result = skill.probe_capability(0.85)

# 执行共识检查
qwen_analysis = {
    "key_points": ["用户登录", "密码验证"],
    "concerns": ["安全问题"],
    "feasibility": "high",
    "suggestions": ["使用JWT"]
}
codex_analysis = {
    "key_points": ["用户登录", "密码验证"],
    "concerns": ["安全问题"],
    "feasibility": "high",
    "suggestions": ["使用JWT"]
}
result = skill.run_consensus_round(qwen_analysis, codex_analysis)

# 获取工作流状态
result = skill.get_workflow_state()

# 重置状态
skill.reset()
```

## 主要方法

| 方法 | 描述 |
|------|------|
| `prepare_context(task, context_files)` | 准备任务上下文 |
| `probe_capability(capability_score)` | 探测能力等级 |
| `run_consensus_round(qwen_analysis, codex_analysis)` | 执行一轮共识检查 |
| `check_fuse(used_tokens, total_tokens)` | 检查熔断状态 |
| `get_fallback(level)` | 获取降级策略 |
| `record_schema_fail()` | 记录Schema失败 |
| `record_error_route()` | 记录错误路由 |
| `record_delay(seconds)` | 记录延迟 |
| `get_workflow_state()` | 获取工作流状态 |
| `reset()` | 重置所有状态 |

## 运行示例

```bash
# 运行基础测试
python test_skill_integration.py

# 运行详细示例
python -m skills.examples
```

## 文件结构

```
skills/
├── __init__.py              # Skill入口
├── multi_model_consensus_skill.py  # 单文件Skill实现
├── examples.py              # 使用示例
├── README.md                # 本文档
└── multi_model_consensus/   # 模块化版本（备用）
```

## Skill化优势

1. **单文件结构** - 避免复杂的相对导入问题
2. **渐进式设计** - 功能模块化，易于扩展
3. **状态隔离** - 每个Skill实例有独立状态
4. **持久化存储** - 工作流状态自动保存
5. **完整功能** - 包含原项目所有核心能力
