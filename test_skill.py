
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

print("=" * 60)
print("Multi-Model Consensus Skill 测试")
print("=" * 60)

print("\n--- 1. 测试 Skill 初始化 ---")
try:
    skill = MultiModelConsensusSkill()
    print("✓ Skill 初始化成功")
except Exception as e:
    print(f"✗ Skill 初始化失败: {e}")
    sys.exit(1)

print("\n--- 2. 测试任务路由 ---")
try:
    result = skill.prepare_context(task="实现用户登录功能")
    print(f"✓ 任务路由成功")
    print(f"  路由ID: {result['route_choice']['route_id']}")
    print(f"  任务类别: {result['route_choice']['task_class']}")
except Exception as e:
    print(f"✗ 任务路由失败: {e}")

print("\n--- 3. 测试能力探测 ---")
try:
    probe_result = skill.probe_capability(capability_score=0.85)
    print(f"✓ 能力探测成功")
    print(f"  级别: {probe_result['level']}")
    print(f"  动作: {probe_result['action']}")
except Exception as e:
    print(f"✗ 能力探测失败: {e}")

print("\n--- 4. 测试共识判定 ---")
try:
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
    print(f"✓ 共识判定成功")
    print(f"  共识达成: {consensus_result['consensus_result']['consensus_reached']}")
except Exception as e:
    print(f"✗ 共识判定失败: {e}")

print("\n--- 5. 测试独立模块 ---")
print("\n--- 5.1 TaskRouter ---")
try:
    router = TaskRouter()
    choice = router.route("修复登录按钮样式")
    print(f"✓ TaskRouter 成功")
    print(f"  路由: {choice.route_id}")
except Exception as e:
    print(f"✗ TaskRouter 失败: {e}")

print("\n--- 5.2 CapabilityProbe ---")
try:
    probe = CapabilityProbe()
    level, action = probe.get_capability_action(0.9)
    print(f"✓ CapabilityProbe 成功")
    print(f"  级别: {level.value}")
    print(f"  动作: {action}")
except Exception as e:
    print(f"✗ CapabilityProbe 失败: {e}")

print("\n--- 5.3 ConsensusEngine ---")
try:
    engine = ConsensusEngine()
    qwen = {"opinion": "ok", "key_points": ["a"], "concerns": [], "suggestions": [], "feasibility": "high"}
    codex = {"opinion": "ok", "key_points": ["a"], "concerns": [], "suggestions": [], "feasibility": "high"}
    result = engine.check(qwen, codex)
    print(f"✓ ConsensusEngine 成功")
    print(f"  共识达成: {result['consensus_reached']}")
except Exception as e:
    print(f"✗ ConsensusEngine 失败: {e}")

print("\n--- 5.4 FuseMonitor ---")
try:
    monitor = FuseMonitor()
    status = monitor.check_all_limits()
    print(f"✓ FuseMonitor 成功")
    print(f"  熔断触发: {status.any_fuse_triggered}")
except Exception as e:
    print(f"✗ FuseMonitor 失败: {e}")

print("\n--- 5.5 FallbackManager ---")
try:
    manager = FallbackManager()
    def fail(): raise Exception("fail")
    result = manager.execute_with_fallback(fail)
    print(f"✓ FallbackManager 成功")
    print(f"  成功: {result.success}")
except Exception as e:
    print(f"✗ FallbackManager 失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

