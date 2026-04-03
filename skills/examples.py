#!/usr/bin/env python3
from skills.multi_model_consensus_skill import MultiModelConsensusSkill, CapabilityLevel, FallbackLevel


def example_basic_workflow():
    """示例1：基础工作流程"""
    print("=" * 60)
    print("示例1：基础工作流程")
    print("=" * 60)
    
    skill = MultiModelConsensusSkill()
    
    print("\n步骤1：准备上下文")
    result = skill.prepare_context(
        task="修复用户登录页面的样式问题",
        context_files=["login.html", "styles.css"]
    )
    print(f"任务: {result['context']['task']}")
    print(f"路由选择: {result['route_choice']}")
    
    print("\n步骤2：探测能力")
    result = skill.probe_capability(0.75)
    print(f"能力等级: {result['level']}")
    print(f"执行动作: {result['action']}")
    
    print("\n步骤3：执行共识检查")
    qwen_analysis = {
        "key_points": ["修复按钮样式", "调整输入框宽度"],
        "concerns": [],
        "feasibility": "high",
        "suggestions": ["使用flex布局"]
    }
    codex_analysis = {
        "key_points": ["修复按钮样式", "调整输入框宽度"],
        "concerns": [],
        "feasibility": "high",
        "suggestions": ["使用flex布局"]
    }
    result = skill.run_consensus_round(qwen_analysis, codex_analysis)
    print(f"共识达成: {result['consensus_result']['consensus_reached']}")
    
    print("\n步骤4：获取工作流状态")
    result = skill.get_workflow_state()
    print(f"当前状态: {result['state']['current_state']}")
    print(f"共识结果数: {len(result['state']['consensus_results'])}")
    
    print("\n步骤5：重置状态")
    skill.reset()
    print("状态已重置")


def example_complex_task():
    """示例2：复杂任务处理"""
    print("\n" + "=" * 60)
    print("示例2：复杂任务处理")
    print("=" * 60)
    
    skill = MultiModelConsensusSkill()
    
    print("\n1. 准备复杂任务")
    result = skill.prepare_context(
        task="重构系统架构，将单体应用迁移到微服务",
        context_files=["main.py", "database.py", "api.py"]
    )
    print(f"任务类别: {result['route_choice']['task_class']}")
    print(f"路由ID: {result['route_choice']['route_id']}")
    
    print("\n2. 模拟运行时指标监控")
    skill.record_schema_fail()
    skill.record_schema_fail()
    skill.record_delay(25)
    
    print("\n3. 检查熔断状态")
    result = skill.check_fuse(used_tokens=75000, total_tokens=100000)
    fuse_status = result['fuse_status']
    print(f"熔断触发: {fuse_status['any_fuse_triggered']}")
    print(f"能力等级: {fuse_status['capability_level']}")
    print(f"推荐动作: {fuse_status['recommended_action']}")
    
    print("\n4. 获取降级策略")
    for level in [FallbackLevel.L1, FallbackLevel.L2, FallbackLevel.L3, FallbackLevel.L4]:
        result = skill.get_fallback(level)
        print(f"{result['fallback_level']}: {result['data']}")


def example_consensus_divergence():
    """示例3：处理共识分歧"""
    print("\n" + "=" * 60)
    print("示例3：处理共识分歧")
    print("=" * 60)
    
    skill = MultiModelConsensusSkill()
    
    skill.prepare_context("实现用户认证功能")
    
    print("\n模拟有分歧的分析结果")
    qwen_analysis = {
        "key_points": ["JWT认证", "OAuth2"],
        "concerns": ["安全性"],
        "feasibility": "high",
        "suggestions": ["使用JWT"]
    }
    codex_analysis = {
        "key_points": ["Session认证", "Cookie"],
        "concerns": ["兼容性"],
        "feasibility": "medium",
        "suggestions": ["使用Session"]
    }
    
    result = skill.run_consensus_round(qwen_analysis, codex_analysis)
    consensus_result = result['consensus_result']
    
    print(f"共识达成: {consensus_result['consensus_reached']}")
    print(f"\n共识点数量: {len(consensus_result['consensus_points'])}")
    print(f"分歧点数量: {len(consensus_result['divergence_points'])}")
    
    if consensus_result['divergence_points']:
        print("\n分歧详情:")
        for divergence in consensus_result['divergence_points']:
            print(f"\n维度: {divergence['dimension']}")
            print(f"Qwen证据: {divergence['qwen_evidence']}")
            print(f"Codex证据: {divergence['codex_evidence']}")


def main():
    """运行所有示例"""
    example_basic_workflow()
    example_complex_task()
    example_consensus_divergence()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

