# Graph Revision Read Model 设计

> 本文定义新 Graph Layer 的 revision-aware 读模型。目标是让 `GraphRevision / KnowledgeNode` 有自己的稳定读取契约，而不是长期挤在旧 `KnowledgeGraphMainViewDTO` 和旧 profile-space graph 语义里。

## 1. 当前定位

当前已经完成：

```text
AssessmentFactItem
  -> KnowledgeSignal
  -> GraphRevision + KnowledgeNode + ActiveGraphRevisionPointer
  -> /api/knowledge/graph-main 兼容读面
```

这意味着系统已经具备“用户提交答案后，Facts 驱动的新 graph 可以被读到”的最小闭环。

但当前读面仍然是过渡状态：

1. `KnowledgeGraphMainViewDTO` 是旧 profile-space graph/main view 的 DTO。
2. 新 graph path 只把 revision-scoped nodes 映射成旧 node cards。
3. `graph_revision_id`、`source_signal_ids`、`supporting_fact_ids`、`confidence` 等 provenance 信息没有一等字段。
4. `cluster_id` / `node_id` 选择参数仍然保留给旧 profile-space fallback。
5. 后续 relation、user state、focus cluster 如果继续塞进旧 DTO，会扩大过渡债。

因此下一阶段不应直接做复杂 relation 或 Maintenance Agent，而应先补一层稳定的 Graph Revision Read Model。

## 2. 本阶段目标

建立一个新 Graph Layer 专用的读模型：

```text
ActiveGraphRevisionPointer
  -> GraphRevision
  -> KnowledgeNode[]
  -> GraphRevisionViewDTO
```

它回答三个问题：

1. 当前 active graph revision 是哪一版？
2. 这一版里有哪些 revision-scoped knowledge nodes？
3. 每个 node 从哪些 signals / facts 来，置信度和状态是什么？

完成后，后续 relation、focus cluster、user state 都应挂到这个 revision-aware read model 上，而不是继续污染旧 profile-space DTO。

## 3. 推荐方案

推荐新增独立 DTO 和独立 workspace/http read method，但先不改 UI：

```text
WorkspaceAPI.get_graph_revision_view(project_id, stage_id)
GET /api/knowledge/graph-revision
```

理由：

1. 现有 `/api/knowledge/graph-main` 已经承担兼容读面，继续加字段会破坏它的职责。
2. 新 endpoint 可以稳定表达 `graph_revision_id`、`source_signal_ids`、`supporting_fact_ids` 等新 graph 语义。
3. UI 暂时不切换，避免把读模型设计和前端呈现绑在同一阶段。
4. 这个 read model 是后续 `KnowledgeRelationRecord`、Graph Layer user state、focus cluster 的挂载点。
5. 它能为真实用户使用前的调试和 LLM 全链路测试提供可观测出口。

## 4. 非目标

本阶段不做：

1. 不新增 `KnowledgeRelationRecord`。
2. 不生成 relation。
3. 不设计 Maintenance Agent。
4. 不改前端页面。
5. 不移除 `/api/knowledge/graph-main`。
6. 不移除旧 `ProfileSpaceService` graph/map v1。
7. 不改变 submit-side graph projection 写入顺序。
8. 不把 LLM 维护 agent 接进 graph rewrite。

## 5. DTO 边界

推荐新增三个 DTO。

### 5.1 GraphRevisionSummaryDTO

表达当前 revision 元信息：

```text
graph_revision_id: str
project_id: str
scope_type: str
scope_ref: str
revision_type: str
status: str
node_count: int
relation_count: int
source_fact_batch_ids: list[str]
source_signal_ids: list[str]
created_by: str
created_at: str
activated_at: str
revision_summary: str
```

### 5.2 GraphRevisionNodeDTO

表达 revision-scoped node：

```text
knowledge_node_id: str
graph_revision_id: str
topic_key: str
label: str
node_type: str
description: str
source_signal_ids: list[str]
supporting_fact_ids: list[str]
confidence: float
status: str
created_by: str
created_at: str
updated_at: str
payload: dict[str, object]
```

### 5.3 GraphRevisionViewDTO

表达完整读面：

```text
project_id: str
stage_id: str
has_active_revision: bool
revision: GraphRevisionSummaryDTO | None
nodes: list[GraphRevisionNodeDTO]
relations: list[dict[str, object]]
```

v1 约束：

1. `relations` 暂时返回空数组。
2. 没有 active revision 时，`has_active_revision=False`，`revision=None`，`nodes=[]`。
3. 不 fallback 到旧 profile-space graph；这个 endpoint 只表达新 Graph Layer。

## 6. API 边界

新增 workspace method：

```text
WorkspaceAPI.get_graph_revision_view(project_id: str, stage_id: str) -> GraphRevisionViewDTO
```

新增 HTTP endpoint：

```text
GET /api/knowledge/graph-revision?project_id=...&stage_id=...
```

读取顺序：

```text
checkpoint_store missing
  -> return empty GraphRevisionViewDTO

active pointer missing
  -> return empty GraphRevisionViewDTO

revision missing
  -> return empty GraphRevisionViewDTO

revision exists
  -> return revision summary + list_graph_nodes(revision_id)
```

注意：这里不采用旧 profile fallback。原因是这个 endpoint 的目的就是调试和消费新 Graph Layer；如果 fallback 到旧 graph，会掩盖新 graph 是否真的生成。

## 7. 和现有 graph-main 的关系

两条读面并存：

```text
/api/knowledge/graph-main
  -> 产品兼容读面
  -> 新 graph 优先 + 旧 profile fallback

/api/knowledge/graph-revision
  -> 新 Graph Layer 调试/稳定契约读面
  -> 只读 active graph revision
```

这不是重复，而是两种职责：

1. `graph-main` 负责让现有产品页面不中断。
2. `graph-revision` 负责让新 graph 的真实结构可观测、可测试、可被后续能力依赖。

## 8. 错误边界

本阶段读面不抛业务错误：

1. 没有 store：返回 empty view。
2. 没有 active pointer：返回 empty view。
3. pointer 指向的 revision 不存在：返回 empty view。
4. revision 存在但 nodes 为空：返回 revision + empty nodes。

但不捕获 SQLite / 代码级异常。真实异常应暴露给测试，而不是被包装成 empty view。

## 9. 测试边界

本阶段测试重点：

1. active graph revision 存在时，WorkspaceAPI 返回 revision summary。
2. active graph revision 存在时，WorkspaceAPI 返回 nodes，并保留 provenance 字段。
3. 没有 active revision 时，返回 empty view，而不是旧 profile fallback。
4. HTTP `/api/knowledge/graph-revision` 在 submit 后能读到 active revision。
5. 现有 `/api/knowledge/graph-main` 兼容测试继续通过。

不测试：

1. 前端展示。
2. relation 映射。
3. cluster 选择。
4. Maintenance Agent。
5. LLM graph rewrite。

## 10. 离用户真实使用还差什么

当前距离“真实用户可用”还差这些阶段：

1. Revision-aware read model：让新 graph 有稳定、可解释、可调试的读取契约。
2. Product UI 接入：前端要能展示新 graph revision，而不是只靠旧兼容 DTO。
3. User state / focus cluster 新模型：用户需要看到当前弱点、复习状态、重点区域，这些不能长期依赖旧 profile-space。
4. KnowledgeRelation：图谱需要表达“支持、依赖、冲突、相似、前置”等关系，否则只是 topic list。
5. Maintenance workflow：用户需要能触发整理、压缩、重构，而不是每次 submit 都做 deterministic projection。
6. 端到端项目数据隔离和恢复：真实使用需要稳定本地 DB、session、demo/live 数据边界。
7. UI 产品化：中文交互、可解释文案、空状态、错误状态、加载状态、操作入口。

因此当前更准确的状态是“核心后端迁移闭环可运行”，还不是“真实用户长期使用闭环完成”。

## 11. 离 LLM 全部接入测试还差什么

当前已经接入过 Project Agent 和 Evaluator Agent 的 OpenAI-compatible client 边界，但全 LLM 接入测试还差：

1. Project Agent live question generation：固定真实项目上下文，跑真实 LLM 出题，并检查问题质量、层级、面试覆盖。
2. Evaluator Agent live assessment：真实 LLM 评估答案，输出稳定 assessment envelope。
3. Assessment Synthesizer stability：把 LLM 输出稳定压成 facts，避免字段漂移影响下游 graph。
4. Facts -> Signals -> Graph live smoke：用真实 LLM 产生的 assessment 走完整 graph projection。
5. Graph Revision read verification：用 live 数据验证 `/api/knowledge/graph-revision` 能解释 provenance。
6. Maintenance Agent live path：后续才引入，让 LLM 读取 facts + current graph，产出 `GraphRewriteRecord + GraphRevision`。
7. Golden dataset：准备一组固定学习清单/项目材料/答案样本，用于比较不同模型输出质量。
8. Failure taxonomy：记录 LLM 输出 JSON 失败、语义漂移、低质量问题、过度抽象、事实缺失等失败类型。

所以 LLM 全接入测试不是“把 key 接上就完成”，而是需要一条可重复的 live smoke + golden eval 管线。

## 12. 后续阶段

推荐顺序：

```text
GraphRevision Read Model
  -> KnowledgeRelation v1
  -> Graph Layer user state / focus cluster
  -> Graph UI 正式切换
  -> Maintenance Agent
  -> LLM full live/golden eval
```

其中 `GraphRevision Read Model` 是当前最值得先做的阶段，因为它会成为后面所有 graph 能力的共同读出口。
