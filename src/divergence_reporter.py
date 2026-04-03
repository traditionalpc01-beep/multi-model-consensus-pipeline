"""
divergence_reporter.py
分歧报告模块，用于生成多模型分析结果之间的分歧报告，并提供人工介入触发逻辑。

主要功能：
1. 汇总多模型分析结果的分歧点
2. 生成结构化的分歧报告
3. 判断是否需要人工介入
4. 提供分歧解决建议
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DivergenceSeverity(Enum):
    """分歧严重程度枚举。"""
    CRITICAL = "critical"    # 严重分歧，必须人工介入
    HIGH = "high"            # 高度分歧，建议人工介入
    MEDIUM = "medium"        # 中度分歧，可尝试继续讨论
    LOW = "low"              # 低度分歧，可自动调和


@dataclass
class DivergencePoint:
    """分歧点数据结构。"""
    dimension: str                    # 分歧维度
    model_evidence: Dict[str, List[str]]  # 各模型的证据
    severity: DivergenceSeverity      # 严重程度
    impact: str                      # 影响描述
    resolution_hint: Optional[str] = None  # 解决建议


@dataclass
class DivergenceReport:
    """完整分歧报告。"""
    summary: str                      # 总结
    divergence_points: List[DivergencePoint]  # 分歧点列表
    consensus_points: List[str]       # 共识点列表
    recommended_action: str           # 推荐动作
    needs_human_escalation: bool       # 是否需要人工介入
    model_count: int                   # 参与模型数量
    consensus_rate: float              # 共识率
    overall_status: str = "completed"  # 总体状态
    recommendations: List[str] = None   # 建议列表
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class DivergenceReporter:
    """
    分歧报告生成器。
    
    分析多个模型的分析结果，识别分歧点，生成结构化报告。
    """
    
    # 分歧维度定义
    DIMENSIONS = {
        "goal": "目标理解",
        "constraints": "约束条件",
        "implementation_path": "实现路径",
        "feasibility": "可行性评估",
    }
    
    # 推荐动作
    ACTION_CONTINUE = "continue_consensus"
    ACTION_ESCALATE = "escalate_to_human"
    ACTION_FALLBACK = "fallback_to_codex"
    
    def __init__(
        self,
        critical_threshold: int = 1,
        high_threshold: int = 2,
        escalation_threshold: float = 0.5,
    ) -> None:
        """
        初始化分歧报告生成器。
        
        Args:
            critical_threshold: 严重分歧触发人工介入的数量
            high_threshold: 高度分歧触发人工介入的数量
            escalation_threshold: 共识率低于此值时触发人工介入
        """
        self.critical_threshold = critical_threshold
        self.high_threshold = high_threshold
        self.escalation_threshold = escalation_threshold
        logger.debug("DivergenceReporter 初始化完成")
    
    def generate_report(
        self,
        model_results: Mapping[str, Mapping[str, Any]],
    ) -> DivergenceReport:
        """
        生成分歧报告。
        
        Args:
            model_results: 各模型的分析结果字典
                {
                    "model_name": {
                        "opinion": "...",
                        "key_points": [...],
                        "concerns": [...],
                        "suggestions": [...],
                        "feasibility": "high|medium|low"
                    }
                }
        
        Returns:
            DivergenceReport 包含完整分歧分析
        """
        model_names = list(model_results.keys())
        model_count = len(model_names)
        
        if model_count < 2:
            return DivergenceReport(
                summary="参与模型不足，无法进行分歧分析",
                divergence_points=[],
                consensus_points=[],
                recommended_action=self.ACTION_FALLBACK,
                needs_human_escalation=False,
                model_count=model_count,
                consensus_rate=1.0,
            )
        
        logger.info("开始生成分歧报告 | models=%s", model_names)
        
        divergence_points: List[DivergencePoint] = []
        consensus_points: List[str] = []
        
        # 分析各维度的分歧
        for dimension, dimension_name in self.DIMENSIONS.items():
            dim_divergence = self._analyze_dimension(
                dimension, model_results
            )
            if dim_divergence:
                divergence_points.append(dim_divergence)
            else:
                consensus_points.append(dimension_name)
        
        # 计算统计指标
        total_dimensions = len(self.DIMENSIONS)
        consensus_count = len(consensus_points)
        consensus_rate = consensus_count / total_dimensions if total_dimensions > 0 else 1.0
        
        # 判定是否需要人工介入
        needs_escalation = self._needs_human_escalation(
            divergence_points, consensus_rate
        )
        
        # 确定推荐动作
        recommended_action = self._determine_action(
            divergence_points, needs_escalation, consensus_rate
        )
        
        # 生成总结
        summary = self._generate_summary(
            model_names, divergence_points, consensus_points, consensus_rate
        )
        
        # 生成建议
        recommendations = self._generate_recommendations(divergence_points, needs_escalation)
        
        report = DivergenceReport(
            summary=summary,
            divergence_points=divergence_points,
            consensus_points=consensus_points,
            recommended_action=recommended_action,
            needs_human_escalation=needs_escalation,
            model_count=model_count,
            consensus_rate=consensus_rate,
            overall_status="completed",
            recommendations=recommendations,
        )
        
        logger.info(
            "分歧报告生成完成 | divergence_points=%d | consensus_rate=%.2f | needs_escalation=%s",
            len(divergence_points), consensus_rate, needs_escalation
        )
        
        return report
    
    def _analyze_dimension(
        self,
        dimension: str,
        model_results: Mapping[str, Mapping[str, Any]],
    ) -> Optional[DivergencePoint]:
        """
        分析单个维度的分歧。
        
        Args:
            dimension: 维度名称
            model_results: 各模型分析结果
            
        Returns:
            DivergencePoint 或 None（如果无分歧）
        """
        model_evidence: Dict[str, List[str]] = {}
        
        for model_name, result in model_results.items():
            evidence = self._extract_evidence(dimension, result)
            model_evidence[model_name] = evidence
        
        # 检查是否有分歧
        has_divergence = self._has_divergence(model_evidence)
        
        if not has_divergence:
            return None
        
        # 评估严重程度
        severity = self._assess_severity(dimension, model_evidence)
        
        # 生成影响描述
        impact = self._generate_impact(dimension, model_evidence)
        
        # 生成解决建议
        resolution_hint = self._generate_resolution_hint(dimension, model_evidence)
        
        return DivergencePoint(
            dimension=self.DIMENSIONS.get(dimension, dimension),
            model_evidence=model_evidence,
            severity=severity,
            impact=impact,
            resolution_hint=resolution_hint,
        )
    
    def _extract_evidence(
        self,
        dimension: str,
        result: Mapping[str, Any],
    ) -> List[str]:
        """从模型结果中提取特定维度的证据。"""
        evidence: List[str] = []
        
        if dimension == "goal":
            evidence.extend(result.get("key_points", []))
        elif dimension == "constraints":
            evidence.extend(result.get("concerns", []))
        elif dimension == "implementation_path":
            evidence.extend(result.get("suggestions", []))
        elif dimension == "feasibility":
            feasibility = result.get("feasibility", "unknown")
            evidence.append(f"feasibility:{feasibility}")
        
        return [str(e).strip() for e in evidence if str(e).strip()]
    
    def _has_divergence(
        self,
        model_evidence: Dict[str, List[str]],
    ) -> bool:
        """检查是否存在分歧。"""
        if len(model_evidence) < 2:
            return False
        
        # 归一化并比较证据集合
        normalized_sets: List[Set[str]] = []
        for evidence in model_evidence.values():
            normalized = {self._normalize_text(e) for e in evidence}
            normalized_sets.append(normalized)
        
        # 检查所有集合是否相同
        first_set = normalized_sets[0]
        return not all(s == first_set for s in normalized_sets[1:])
    
    def _normalize_text(self, text: str) -> str:
        """归一化文本用于比较。"""
        import re
        normalized = text.casefold()
        normalized = re.sub(r'[^\w\u4e00-\u9fff]+', ' ', normalized)
        return ' '.join(normalized.split())
    
    def _assess_severity(
        self,
        dimension: str,
        model_evidence: Dict[str, List[str]],
    ) -> DivergenceSeverity:
        """评估分歧严重程度。"""
        # 关键维度的分歧更严重
        critical_dimensions = {"goal", "implementation_path"}
        high_dimensions = {"constraints"}
        
        if dimension in critical_dimensions:
            return DivergenceSeverity.CRITICAL
        elif dimension in high_dimensions:
            return DivergenceSeverity.HIGH
        else:
            # 检查证据差异大小
            evidence_lengths = [len(e) for e in model_evidence.values()]
            max_diff = max(evidence_lengths) - min(evidence_lengths)
            if max_diff >= 3:
                return DivergenceSeverity.HIGH
            elif max_diff >= 1:
                return DivergenceSeverity.MEDIUM
            else:
                return DivergenceSeverity.LOW
    
    def _generate_impact(
        self,
        dimension: str,
        model_evidence: Dict[str, List[str]],
    ) -> str:
        """生成分歧影响描述。"""
        impacts = {
            "goal": "可能导致实现目标不明确，影响最终交付结果",
            "constraints": "可能忽略重要约束条件，带来技术债务或安全隐患",
            "implementation_path": "可能导致实现方案不一致，增加集成和维护成本",
            "feasibility": "可能导致风险评估不准确，影响项目进度",
        }
        return impacts.get(dimension, "分歧可能影响任务执行质量")
    
    def _generate_resolution_hint(
        self,
        dimension: str,
        model_evidence: Dict[str, List[str]],
    ) -> Optional[str]:
        """生成分歧解决建议。"""
        hints = {
            "goal": "建议明确需求目标，重新确认用户期望",
            "constraints": "建议整合各模型提出的约束条件，进行优先级排序",
            "implementation_path": "建议对比各实现方案，选择技术风险最低的方案",
            "feasibility": "建议进行技术可行性验证，或寻求专家评估",
        }
        return hints.get(dimension)
    
    def _needs_human_escalation(
        self,
        divergence_points: List[DivergencePoint],
        consensus_rate: float,
    ) -> bool:
        """判断是否需要人工介入。"""
        # 检查严重分歧数量
        critical_count = sum(
            1 for dp in divergence_points
            if dp.severity == DivergenceSeverity.CRITICAL
        )
        if critical_count >= self.critical_threshold:
            return True
        
        # 检查高度分歧数量
        high_count = sum(
            1 for dp in divergence_points
            if dp.severity == DivergenceSeverity.HIGH
        )
        if high_count >= self.high_threshold:
            return True
        
        # 检查共识率
        if consensus_rate < self.escalation_threshold:
            return True
        
        return False
    
    def _determine_action(
        self,
        divergence_points: List[DivergencePoint],
        needs_escalation: bool,
        consensus_rate: float,
    ) -> str:
        """确定推荐动作。"""
        if needs_escalation:
            return self.ACTION_ESCALATE
        
        if consensus_rate >= 0.8:
            return self.ACTION_FALLBACK
        
        return self.ACTION_CONTINUE
    
    def _generate_summary(
        self,
        model_names: List[str],
        divergence_points: List[DivergencePoint],
        consensus_points: List[str],
        consensus_rate: float,
    ) -> str:
        """生成报告总结。"""
        model_list = ", ".join(model_names)
        
        if not divergence_points:
            return f"参与模型 {model_list} 在所有维度达成完全共识"
        
        critical_count = sum(
            1 for dp in divergence_points
            if dp.severity == DivergenceSeverity.CRITICAL
        )
        high_count = sum(
            1 for dp in divergence_points
            if dp.severity == DivergenceSeverity.HIGH
        )
        
        return (
            f"参与模型 {model_list} 分析完成。"
            f"共识率 {consensus_rate:.0%}，"
            f"发现 {len(divergence_points)} 个分歧点 "
            f"(严重 {critical_count} 个，高度 {high_count} 个)。"
            f"已在 {len(consensus_points)} 个维度达成共识。"
        )
    
    def _generate_recommendations(
        self,
        divergence_points: List[DivergencePoint],
        needs_escalation: bool,
    ) -> List[str]:
        """生成建议列表。"""
        recommendations: List[str] = []
        
        if needs_escalation:
            recommendations.append("建议人工介入解决分歧")
        
        for dp in divergence_points:
            if dp.resolution_hint:
                recommendations.append(dp.resolution_hint)
        
        if not recommendations:
            recommendations.append("分歧已解决或无需特殊处理")
        
        return recommendations


def report_to_dict(report: DivergenceReport) -> Dict[str, Any]:
    """
    将 DivergenceReport 转换为可序列化的字典。
    
    Args:
        report: 分歧报告
        
    Returns:
        可序列化的字典
    """
    return {
        "summary": report.summary,
        "divergence_points": [
            {
                "dimension": dp.dimension,
                "model_evidence": dp.model_evidence,
                "severity": dp.severity.value,
                "impact": dp.impact,
                "resolution_hint": dp.resolution_hint,
            }
            for dp in report.divergence_points
        ],
        "consensus_points": report.consensus_points,
        "recommended_action": report.recommended_action,
        "needs_human_escalation": report.needs_human_escalation,
        "model_count": report.model_count,
        "consensus_rate": report.consensus_rate,
        "overall_status": report.overall_status,
        "recommendations": report.recommendations,
    }


def generate_divergence_report(
    model_results: Mapping[str, Mapping[str, Any]],
) -> DivergenceReport:
    """
    便捷函数：生成分歧报告。
    
    Args:
        model_results: 各模型分析结果
        
    Returns:
        DivergenceReport 分歧报告
    """
    reporter = DivergenceReporter()
    return reporter.generate_report(model_results)


__all__ = [
    "DivergenceSeverity",
    "DivergencePoint",
    "DivergenceReport",
    "DivergenceReporter",
    "report_to_dict",
    "generate_divergence_report",
]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("=" * 60)
    print("DivergenceReporter 测试")
    print("=" * 60)
    
    # 模拟完全一致的模型结果
    print("\n--- 测试完全共识 ---")
    consensus_results = {
        "model_a": {
            "opinion": "可行",
            "key_points": ["要点1", "要点2"],
            "concerns": ["关注点1"],
            "suggestions": ["建议1"],
            "feasibility": "high",
        },
        "model_b": {
            "opinion": "可行",
            "key_points": ["要点1", "要点2"],
            "concerns": ["关注点1"],
            "suggestions": ["建议1"],
            "feasibility": "high",
        },
    }
    reporter = DivergenceReporter()
    report1 = reporter.generate_report(consensus_results)
    print(f"共识率: {report1.consensus_rate:.0%}")
    print(f"需要人工介入: {report1.needs_human_escalation}")
    print(f"推荐动作: {report1.recommended_action}")
    print(f"总结: {report1.summary}")
    
    # 模拟有分歧的模型结果
    print("\n--- 测试有分歧 ---")
    divergence_results = {
        "model_a": {
            "opinion": "可行",
            "key_points": ["要点A1", "要点A2"],
            "concerns": ["关注点A"],
            "suggestions": ["建议A1", "建议A2"],
            "feasibility": "high",
        },
        "model_b": {
            "opinion": "需谨慎",
            "key_points": ["要点B1"],
            "concerns": ["关注点B1", "关注点B2"],
            "suggestions": ["建议B"],
            "feasibility": "medium",
        },
    }
    report2 = reporter.generate_report(divergence_results)
    print(f"共识率: {report2.consensus_rate:.0%}")
    print(f"需要人工介入: {report2.needs_human_escalation}")
    print(f"推荐动作: {report2.recommended_action}")
    print(f"分歧点数量: {len(report2.divergence_points)}")
    print(f"共识点: {report2.consensus_points}")
    print(f"总结: {report2.summary}")
    
    # 测试转换为字典
    print("\n--- 测试字典转换 ---")
    report_dict = report_to_dict(report2)
    print(f"转换成功，包含 {len(report_dict)} 个字段")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
