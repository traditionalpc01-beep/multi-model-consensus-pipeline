#!/usr/bin/env python3
from skills.multi_model_consensus_skill import MultiModelConsensusSkill


def test_skill_basic_functionality():
    print("=" * 60)
    print("Multi-Model Consensus Skill 测试")
    print("=" * 60)
    
    skill = MultiModelConsensusSkill()
    
    print("\n1. 测试 prepare_context")
    result = skill.prepare_context("实现用户认证模块", context_files=["auth.py", "user.py"])
    print(f"   成功: {result['success']}")
    print(f"   路由选择: {result['route_choice']}")
    
    print("\n2. 测试 probe_capability")
    result = skill.probe_capability(0.85)
    print(f"   成功: {result['success']}")
    print(f"   能力等级: {result['level']}")
    print(f"   动作: {result['action']}")
    
    print("\n3. 测试 run_consensus_round")
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
    print(f"   成功: {result['success']}")
    print(f"   共识达成: {result['consensus_result']['consensus_reached']}")
    
    print("\n4. 测试 check_fuse")
    result = skill.check_fuse(used_tokens=80000, total_tokens=100000)
    print(f"   成功: {result['success']}")
    print(f"   熔断触发: {result['fuse_status']['any_fuse_triggered']}")
    
    print("\n5. 测试 get_fallback")
    result = skill.get_fallback()
    print(f"   成功: {result['success']}")
    print(f"   降级级别: {result['fallback_level']}")
    print(f"   数据: {result['data']}")
    
    print("\n6. 测试 get_workflow_state")
    result = skill.get_workflow_state()
    print(f"   成功: {result['success']}")
    print(f"   状态: {result['state']}")
    
    print("\n7. 测试 reset")
    result = skill.reset()
    print(f"   成功: {result['success']}")
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_skill_basic_functionality()
