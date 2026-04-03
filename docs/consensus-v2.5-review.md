# 多模型共识讨论记录

## 会话信息

- **日期**: 2026-04-03
- **议题**: 架构 V2.5 评审
- **参与模型**: LongCat Thinking, LongCat Lite, Qwen

---

## 一、各模型意见

### LongCat Thinking

| 项目 | 内容 |
|------|------|
| **Opinion** | 整体架构方向正确，但细节需完善 |
| **Feasibility** | high |
| **Key Points** | 1. 统一模型注册中心是良好架构模式 2. OpenAI API 格式兼容降低接入成本 3. 多模型并行分析可提升结果质量 |
| **Concerns** | 1. 共识判定逻辑未明确 2. 缺乏模型健康检查和熔断机制 3. 免费额度限制可能导致服务中断 |
| **Suggestions** | 1. 明确定义共识算法 2. 实现健康检查和熔断机制 3. 添加成本控制和配额监控 |

### LongCat Lite

| 项目 | 内容 |
|------|------|
| **Opinion** | 整体合理，具备扩展性和灵活性 |
| **Feasibility** | high |
| **Key Points** | 1. 动态调度策略实现差异化利用 2. 成本优化策略有效 |
| **Concerns** | 1. 高并发稳定性未验证 2. 缺乏降级策略 3. 优先级数值缺乏清晰依据 |
| **Suggestions** | 1. 验证高并发稳定性 2. 实现降级策略 3. 明确优先级语义 |

### Qwen

| 项目 | 内容 |
|------|------|
| **Opinion** | 整体设计合理，但优先级语义、共识判定规则、资源管控策略未明确 |
| **Feasibility** | medium |
| **Key Points** | 1. 统一注册中心与 OpenAI API 兼容降低门槛 2. 并行共识机制提升可靠性 |
| **Concerns** | 1. 优先级数值定义不直观 2. 共识判定逻辑缺失 3. 并行调用可能触发限流和成本飙升 |
| **Suggestions** | 1. 明确优先级语义 2. 实现共识判定 3. 添加配额监控和成本预警 |

---

## 二、共识判定

### 证据比对

| 维度 | 结果 | 说明 |
|------|------|------|
| goal_aligned | ✅ True | 所有模型都认为架构可行 |
| constraints_aligned | ❌ False | 存在分歧点 |
| implementation_path_aligned | ✅ True | 都支持继续推进 |

### 共识状态

**共识达成: ❌ False**

分歧点需要解决:
- 成本/配额控制: 仅 1 个模型关切（次要）

### 共同关切点（≥2 模型）

| 关切点 | 模型数 | 优先级 |
|--------|--------|--------|
| 共识判定逻辑 | 2 | 🔴 高 |
| 降级/熔断机制 | 2 | 🔴 高 |
| 优先级定义 | 2 | 🟡 中 |
| 成本/配额控制 | 1 | 🟢 低 |

---

## 三、改进方案（LongCat Thinking 提议）

### 3.1 共识算法设计

```python
# 置信度加权语义投票算法
def reach_consensus(responses, threshold=0.75):
    # Step 1: 过滤低置信度响应
    filtered = [r for r in responses if r.confidence > 0.6]
    if len(filtered) < 2:
        return {'status': 'none'}

    # Step 2: 计算语义相似度矩阵
    similarity_matrix = SBERT.similarity([r.text for r in filtered])

    # Step 3: 计算加权支持度
    weighted_scores = []
    for i, resp in enumerate(filtered):
        support = np.mean(similarity_matrix[i])
        latency_penalty = 1 - (resp.latency / max(r.latency for r in filtered))
        weighted = support * resp.confidence * latency_penalty
        weighted_scores.append(weighted)

    # Step 4: 判定共识
    best_idx = np.argmax(weighted_scores)
    if weighted_scores[best_idx] > threshold:
        return {'status': 'full', 'result': filtered[best_idx].text}
    elif weighted_scores[best_idx] > threshold * 0.7:
        return {'status': 'partial', 'result': filtered[best_idx].text}
    else:
        return {'status': 'none'}
```

### 3.2 降级熔断机制

```python
# 滑动窗口熔断器
class CircuitBreaker:
    def __init__(self, name, failure_threshold=5, recovery_timeout=30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = 'CLOSED'
        self.failure_count = 0
        self.last_failure_time = None

    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise CircuitOpenException(f'{self.name} is OPEN')

        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
            raise e
```

**三级降级策略:**

| Level | 名称 | 条件 | 动作 |
|-------|------|------|------|
| 1 | 模型降级 | 主模型熔断 | 切换备用模型 |
| 2 | 功能降级 | 多模型不可用 | 返回缓存/简化响应 |
| 3 | 服务降级 | 系统级故障 | 兜底文案+默认数据 |

### 3.3 优先级定义

| Level | 名称 | SLA | 共识要求 | 模型访问 |
|-------|------|-----|----------|----------|
| P0 | 紧急 | 99.99% 可用, 200ms 延迟 | full | 所有模型 |
| P1 | 高 | 99.9% 可用, 500ms 延迟 | partial | 主流模型 |
| P2 | 中 | 99.5% 可用, 2s 延迟 | none | 经济型模型 |
| P3 | 低 | 99% 可用 | none | 最低成本模型 |

### 3.4 成本控制策略

1. **智能路由**: 根据复杂度选择性价比模型
2. **动态批处理**: 合并小请求
3. **缓存策略**: Redis 缓存, TTL=1h
4. **Token 压缩**: 自动截断、摘要提取
5. **预算管理**: 多级预警 (50%, 80%, 90%, 95%)

---

## 四、待改进事项

| 优先级 | 事项 | 状态 |
|--------|------|------|
| 🔴 高 | 实现共识判定算法 | ⏳ 待开发 |
| 🔴 高 | 实现降级熔断机制 | ⏳ 待开发 |
| 🟡 中 | 明确优先级语义 | ⏳ 待开发 |
| 🟢 低 | 成本控制策略 | ⏳ 可选 |

---

## 五、结论

**共识状态**: 部分共识

**下一步**:
1. 将改进方案纳入 Phase 3 开发
2. 实现共识判定算法
3. 实现降级熔断机制
4. 更新架构文档