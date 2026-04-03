
import sys
import os

sys.path.insert(0, os.path.abspath('/workspace'))

from skills.multi_model_consensus import MultiModelConsensusSkill
from skills.multi_model_consensus.modules import (
    TaskRouter,
    CapabilityProbe,
    ConsensusEngine,
    FuseMonitor,
    FallbackManager
)

def example_skill_usage():
    print("=" * 60)
    print("Multi-Model Consensus Skill 使用示例")
    print("=" * 60)
    
    skill = MultiModelConsensusSkill()
    
    print("\n--- 1. 准备上下文 ---")
    result = skill.prepare_context(task="实现用户登录功能")
    print(f"成功: {result['success']}")
    print(f"路由: {result['route_choice']['route_id']}")
    
    print("\n--- 2. 能力探测 ---")
    probe_result = skill.probe_capability(capability_score=0.85)
    print(f"成功: {probe_result['success']}")
    print(f"级别: {probe_result['level']}")
    print(f"动作: {probe_result['action']}")
    
    print("\n--- 3. 共识判定 ---")
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
    print(f"成功: {consensus_result['success']}")
    print(f"共识达成: {consensus_result['consensus_result']['consensus_reached']}")
    
    print("\n--- 4. 工作流状态 ---")
    state = skill.get_workflow_state()
    print(f"成功: {state['success']}")
    print(f"状态: {state['state']}")
    
    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)

def example_task_router():
    print("\n--- 任务路由示例 ---")
    router = TaskRouter()
    
    tasks = [
        "修复登录按钮样式",
        "实现用户认证模块",
        "重构整个架构"
    ]
    
    for task in tasks:
        choice = router.route(task)
        print(f"\n任务: {task}")
        print(f"  路由: {choice.route_id}")
        print(f"  类别: {choice.task_class}")
        print(f"  动作: {choice.next_action}")

def example_capability_probe():
    print("\n--- 能力探测示例 ---")
    probe = CapabilityProbe()
    
    scores = [0.2, 0.5, 0.9]
    for score in scores:
        level, action = probe.get_capability_action(score)
        print(f"\n分数: {score}")
        print(f"  级别: {level.value}")
        print(f"  动作: {action}")

def example_consensus_engine():
    print("\n--- 共识引擎示例 ---")
    engine = ConsensusEngine()
    
    qwen = {
        "opinion": "可行",
        "key_points": ["点1", "点2"],
        "concerns": [],
        "suggestions": ["建议1"],
        "feasibility": "high"
    }
    
    codex = {
        "opinion": "方案可行",
        "key_points": ["点1", "点2"],
        "concerns": ["需要注意"],
        "suggestions": ["建议1"],
        "feasibility": "high"
    }
    
    result = engine.check(qwen, codex)
    print(f"共识达成: {result['consensus_reached']}")
    print(f"共识点数量: {len(result['consensus_points'])}")
    print(f"分歧点数量: {len(result['divergence_points'])}")

def example_fuse_monitor():
    print("\n--- 熔断监控示例 ---")
    monitor = FuseMonitor()
    
    status = monitor.check_all_limits(used_tokens=85000, total_tokens=100000)
    print(f"熔断触发: {status.any_fuse_triggered}")
    print(f"能力级别: {status.capability_level}")
    print(f"推荐动作: {status.recommended_action}")

def example_fallback_manager():
    print("\n--- 降级管理示例 ---")
    manager = FallbackManager()
    
    def primary():
        raise Exception("Primary failed")
    
    result = manager.execute_with_fallback(primary)
    print(f"成功: {result.success}")
    print(f"降级级别: {result.level.value}")

if __name__ == "__main__":
    example_skill_usage()
    example_task_router()
    example_capability_probe()
    example_consensus_engine()
    example_fuse_monitor()
    example_fallback_manager()

