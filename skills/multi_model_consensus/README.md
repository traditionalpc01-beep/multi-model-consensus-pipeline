
# Multi-Model Consensus Skill

多模型共识编排Skill - 基于渐进式流程设计的能力封装

## 概述

这个Skill将原项目的核心能力封装成一个易于使用的模块，支持：
- 任务自动路由
- 能力探测与分级
- 多模型共识判定
- 熔断监控
- 降级管理
- 工作流状态管理

## 安装

将 `skills/multi_model_consensus` 目录复制到你的项目中。

## 快速开始

```python
from skills.multi_model_consensus import MultiModelConsensusSkill

# 初始化Skill
skill = MultiModelConsensusSkill(project_dir="/path/to/project")

# 1. 准备上下文
result = skill.prepare_context(
    task="实现用户登录功能",
    context_files=["/path/to/file1.py", "/path/to/file2.py"]
)
print(f"路由结果: {result['route_choice']}")

# 2. 能力探测
probe_result = skill.probe_capability(capability_score=0.85)
print(f"能力级别: {probe_result['level']}")

# 3. 运行共识判定
qwen_analysis = {
    "opinion": "这是一个可行的方案",
    "key_points": ["使用JWT认证", "密码哈希存储"],
    "concerns": [],
    "suggestions": ["添加验证码", "实现会话管理"],
    "feasibility": "high"
}

codex_analysis = {
    "opinion": "技术方案可行",
    "key_points": ["使用JWT认证", "密码哈希存储"],
    "concerns": ["需要考虑安全性"],
    "suggestions": ["添加验证码", "实现会话管理"],
    "feasibility": "high"
}

consensus_result = skill.run_consensus_round(qwen_analysis, codex_analysis)
print(f"共识达成: {consensus_result['consensus_result']['consensus_reached']}")

# 4. 获取工作流状态
state = skill.get_workflow_state()
print(f"当前状态: {state}")
```

## 核心功能

### 1. 任务路由

自动将任务分类为简单、中等、复杂三个级别：

```python
from skills.multi_model_consensus.modules import TaskRouter

router = TaskRouter()
choice = router.route("修复登录按钮样式")
print(choice.route_id)  # direct_execution
```

### 2. 能力探测

根据能力分数确定执行路径：

```python
from skills.multi_model_consensus.modules import CapabilityProbe

probe = CapabilityProbe()
level, action = probe.get_capability_action(0.85)
print(f"Level: {level.value}, Action: {action}")
```

### 3. 共识判定

比较多模型分析结果，判定共识：

```python
from skills.multi_model_consensus.modules import ConsensusEngine

engine = ConsensusEngine()
result = engine.check(qwen_analysis, codex_analysis)
print(f"共识达成: {result['consensus_reached']}")
```

### 4. 熔断监控

监控运行时指标并触发熔断：

```python
from skills.multi_model_consensus.modules import FuseMonitor

monitor = FuseMonitor()
status = monitor.check_all_limits(used_tokens=85000, total_tokens=100000)
print(f"熔断触发: {status.any_fuse_triggered}")
```

### 5. 降级管理

提供多级降级策略：

```python
from skills.multi_model_consensus.modules import FallbackManager

manager = FallbackManager()

def risky_operation():
    raise Exception("Primary failed")

result = manager.execute_with_fallback(risky_operation)
print(f"降级级别: {result.level.value}")
```

## 渐进式设计原则

1. **模块化封装** - 每个功能独立成模块，可单独使用
2. **最小依赖** - 核心模块无外部依赖
3. **状态隔离** - 每个Skill实例有独立的状态
4. **容错设计** - 内置降级和熔断机制

## 目录结构

```
skills/multi_model_consensus/
├── __init__.py              # 模块入口
├── skill.py                 # 主Skill类
├── README.md                # 本文档
└── modules/
    ├── __init__.py
    ├── task_router.py       # 任务路由
    ├── capability_probe.py  # 能力探测
    ├── consensus_engine.py  # 共识引擎
    ├── workflow_state.py    # 工作流状态
    ├── fuse_monitor.py      # 熔断监控
    └── fallback_manager.py  # 降级管理
```

## 许可证

MIT License

