# 最终实现方案请求

## 三轮共识已达成（100%）

请 Codex 结合以下所有共识，给出具体的实现方案（代码改造建议）。

### 共识总结

#### 1. 角色分工
| 角色 | 职责 | 权限 |
|------|------|------|
| Orchestrator（MCP Server 独立） | 确定性路由、状态管理、异常熔断、归一化输出 | 只读 + 编排决策 |
| 基础模型（可热插拔） | 在封闭选项中选择 route_id/next_action，回传状态字段 | 弱依赖节点 |
| Qwen | 需求边界分析、逻辑正确性、安全合规、方案补充 | 只读 |
| Codex | 技术可行性评估、实现方案细化、代码编写、问题修复 | 写权限 |
| 人工 | 无法收敛分歧时做最终决策 | 全权限 |

#### 2. 工具清单（硬编码 vs 模型调用）
| 工具 | 硬编码程度 |
|------|-----------|
| capability_probe | 100% Server |
| task_router | 80% Server（基础模型只选） |
| prepare_context | 100% Server |
| qwen_analyze | 模型调用 |
| codex_analyze | 模型调用 |
| merge_proposals | 90% Server（模板引擎） |
| consensus_check | 100% Server（字段比对） |
| generate_divergence_report | 100% Server |
| codex_execute | 模型调用 |
| joint_review | 模型调用 + Server 归一化 |
| dynamic_fuse | 100% Server |
| audit_log | 100% Server |

#### 3. 共识判定机制
- 主判定：证据比对（需求理解、约束是否一致、分歧是否影响实现路径）
- 辅助信号：语义相似度只作预筛
- 输出结构化：JSON Schema 抽取核心字段

#### 4. 最终裁决者
- 无法收敛分歧 → 人工裁决
- 模型只输出结构化分歧报告

#### 5. Review 自动修复上限
- MVP 默认 2 次
- 后续引入动态熔断（差异度降幅<10% 或 Token 预算达 80%）

#### 6. 基础模型可替换性
- 最低能力：JSON Schema + 确定性选择 + 状态回传
- 能力分级：L2/L1/L0
- 熔断规则：连续失败 > 3 次、延迟 > 30s、错误路由 > 2 次

### 请给出实现方案

请针对现有 `codex-qwen-mcp-server.py` 文件，给出具体改造建议：

1. 新增哪些工具？每个工具的输入输出 Schema？
2. 状态机设计？状态迁移规则？
3. 路由规则表设计？task_class 如何分级？
4. 熔断机制实现细节？
5. JSON Schema 校验中间件如何实现？
6. 归一化模板引擎如何实现？
7. 能力探针如何设计？

请输出：
- 改造后的代码结构建议
- 关键代码片段示例
- 实现优先级排序（MVP 先实现哪些）