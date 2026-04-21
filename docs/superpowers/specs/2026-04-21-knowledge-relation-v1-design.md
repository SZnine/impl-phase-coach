# KnowledgeRelation v1 设计

> 本文定义新 Graph Layer 的第一版 revision-scoped relation 能力。目标是让 `GraphRevision` 从“topic list”进入“最小可连边图”，并让 `/api/knowledge/graph-revision` 能稳定读出 `KnowledgeNode[] + KnowledgeRelation[]`。

## 1. 当前定位

当前已经完成：

```text
AssessmentFactItem
  -> KnowledgeSignal
  -> GraphRevision + KnowledgeNode + ActiveGraphRevisionPointer
  -> GraphRevisionViewDTO
  -> GET /api/knowledge/graph-revision
```

这条链路已经让新 Graph Layer 可写、可激活、可读。当前缺口是：

1. `GraphRevision.relation_count` 长期为 `0`。
2. `GraphRevisionViewDTO.relations` 长期为空数组。
3. 新 graph 只能表达“有哪些知识点”，不能表达“知识点之间如何连接”。
4. 旧 `ProfileSpaceService` 已有 relation 语义，但它属于旧 profile-space v1，不应反向污染新 revision-scoped graph。

因此下一阶段应补 `KnowledgeRelationRecord` 的最小闭环。

## 2. 本阶段目标

建立新 Graph Layer 的第一版 relation 主链：

```text
KnowledgeSignal[]
  -> KnowledgeNode[]
  -> KnowledgeRelation[]
  -> GraphRevision.relation_count
  -> GraphRevisionViewDTO.relations
```

它回答三个问题：

1. 同一版 `GraphRevision` 内哪些节点有关联？
2. 关系类型是什么？
3. 关系从哪些 signals / facts 来，置信度和状态是什么？

完成后，后续 focus cluster、user state、Maintenance Agent 都可以依赖 revision-scoped relation，而不是继续依赖旧 profile-space relation。

## 3. 推荐方案

推荐采用 **Schema + deterministic projection + read model 一起做最小闭环**。

也就是：

```text
KnowledgeRelationRecord
graph_knowledge_relations
KnowledgeSignalGraphProjector.project(...) -> relations
WorkspaceAPI.get_graph_revision_view(...) -> relation DTOs
GET /api/knowledge/graph-revision -> relations
```

理由：

1. 只加 schema 没有可观测业务价值，容易形成局部最小但全局推进弱。
2. 直接接 LLM/Maintenance Agent 太早，因为 relation record 和 read model 还没有稳定。
3. deterministic v1 可以先把“可连边、可读出、可测试”跑通，再让后续 LLM rewrite 接管复杂语义。
4. 当前 `GraphRevisionViewDTO.relations` 已经是预留挂载点，先补它能最大化利用刚完成的 read model。

## 4. 非目标

本阶段不做：

1. 不设计 Maintenance Agent。
2. 不调用 LLM 生成或重写 relation。
3. 不引入 `GraphRewriteRecord`。
4. 不做 focus cluster。
5. 不做 user node state。
6. 不改前端 UI。
7. 不迁移或复用旧 `ProfileSpaceService` 的 relation 存储。
8. 不把 relation 写回 Assessment Facts / KnowledgeSignal。
9. 不尝试覆盖所有 relation 语义。

## 5. KnowledgeRelationRecord 边界

`KnowledgeRelationRecord` 是 revision-scoped graph 的关系本体。

它回答“同一版图里的两个节点如何连接”。

最小字段：

```text
knowledge_relation_id: str
graph_revision_id: str
from_node_id: str
to_node_id: str
relation_type: str
directionality: str
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

v1 不加入：

1. `canonical_key`
2. `weight`
3. `rewrite_record_id`

原因是这些字段更适合 Maintenance Agent 或 graph rewrite 阶段决定。当前 deterministic projection 只需要稳定表达“这条边存在、来自哪里、可信度多少”。

## 6. SQLite 表边界

新增表：

```text
graph_knowledge_relations
```

建议列：

```text
knowledge_relation_id TEXT PRIMARY KEY
graph_revision_id TEXT NOT NULL
from_node_id TEXT NOT NULL
to_node_id TEXT NOT NULL
relation_type TEXT NOT NULL
directionality TEXT NOT NULL
confidence REAL NOT NULL
status TEXT NOT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
payload TEXT NOT NULL
```

建议索引：

```text
idx_graph_knowledge_relations_revision(graph_revision_id)
idx_graph_knowledge_relations_from_node(from_node_id)
idx_graph_knowledge_relations_to_node(to_node_id)
idx_graph_knowledge_relations_type(relation_type)
```

外键：

```text
graph_revision_id -> graph_revisions(graph_revision_id)
from_node_id -> graph_knowledge_nodes(knowledge_node_id)
to_node_id -> graph_knowledge_nodes(knowledge_node_id)
```

写入顺序：

```text
insert_graph_revision
insert_graph_nodes
insert_graph_relations
upsert_active_graph_revision_pointer
```

原因是 relation 依赖 nodes，pointer 只能在 revision、nodes、relations 都落库后激活。

## 7. relation 语义 v1

本阶段只做 deterministic relation v1，不追求语义完备，也不凭 node 类型做宽泛启发式连边。

推荐第一版只生成 provenance-backed `supports`：

```text
support_source_topic -> support_target_topic
relation_type = supports
directionality = directed
```

生成条件：

1. 同一 `GraphRevision` 内至少有 2 个 node。
2. 两端 node 都来自同一 `AssessmentFactBatch`。
3. 上游 assessment 中存在明确 `support_signals`。
4. `AssessmentSynthesizer` 已经把该 `support_signal` 物化成 `support_relation` fact。
5. `AssessmentFactSignalProjector` 已经把该 fact 物化成 `support_relation` signal。
6. `KnowledgeSignalGraphProjector` 只根据 `support_relation` signal 的 payload 生成 relation。

如果没有明确 `support_relation` signal，不生成 relation。

这条规则的目标不是证明“语义上一定支持”，而是先建立一条保守、可解释、可回溯的连边机制。relation 的存在必须能追溯到上游 assessment 的结构化支持信号，而不是 projector 根据 topic 类型自行猜测。后续 Maintenance Agent 可以基于 facts + graph 重新压缩和改写 relation。

### 7.1 支持信号物化边界

当前 `ReviewFlowService` 已经会从 `support_basis_tags` 和低分维度命中中派生 `support_signals`。本阶段不重新设计这个逻辑，只把它纳入 checkpoint 主链：

```text
assessment.support_signals
  -> AssessmentFactItem(fact_type="support_relation")
  -> KnowledgeSignal(signal_type="support_relation")
  -> KnowledgeRelationRecord(relation_type="supports")
```

`support_relation` fact 的 payload 至少包含：

```text
source_label
source_node_type
target_label
target_node_type
basis_type
basis_key
relation_type = supports
```

source/target node 的 topic key 使用同一套稳定 slug 规则生成，确保 support relation 可以指向同 revision 内的具体 nodes。

暂不生成：

1. `depends_on`
2. `conflicts_with`
3. `similar_to`
4. `prerequisite_of`
5. `causes_mistake`
6. `abstracts`

这些关系需要更强语义判断，当前 deterministic projector 容易写成不可维护的启发式规则。

## 8. Projector 边界

`KnowledgeSignalGraphProjector.project(...)` 当前返回：

```text
GraphRevisionRecord
KnowledgeNodeRecord[]
ActiveGraphRevisionPointerRecord
```

本阶段调整为：

```text
GraphRevisionRecord
KnowledgeNodeRecord[]
KnowledgeRelationRecord[]
ActiveGraphRevisionPointerRecord
```

`GraphRevisionRecord.relation_count` 由 `len(relations)` 决定。

projector 仍然保持 deterministic，不调用 LLM，不访问数据库，不读取旧 profile-space。

它只根据传入的 `KnowledgeSignalRecord[]` 和刚投影出的 `KnowledgeNodeRecord[]` 生成 relation。

## 9. Read Model 边界

新增 DTO：

```text
GraphRevisionRelationDTO
```

字段：

```text
knowledge_relation_id: str
graph_revision_id: str
from_node_id: str
to_node_id: str
relation_type: str
directionality: str
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

更新：

```text
GraphRevisionViewDTO.relations: list[GraphRevisionRelationDTO]
```

读取顺序：

```text
active pointer
  -> graph revision
  -> list_graph_nodes(revision_id)
  -> list_graph_relations(revision_id)
  -> GraphRevisionViewDTO
```

如果 revision 存在但没有 relations，返回 `relations=[]`。这仍然是合法状态。

## 10. 和 graph-main 的关系

本阶段不要求 `/api/knowledge/graph-main` 消费新 relation。

原因：

1. `graph-main` 是产品兼容读面，当前仍然保留旧 profile fallback。
2. 新 relation 的稳定消费面应先放在 `/api/knowledge/graph-revision`。
3. UI 切换前，不应让兼容 DTO 同时承担新旧 relation 语义。

后续 Graph UI 正式切换时，再决定是否：

1. 让 UI 直接消费 `/api/knowledge/graph-revision`。
2. 或新增产品级 graph read model，把 revision graph 映射成 UI 专用结构。

## 11. 错误边界

本阶段不抛业务错误：

1. 没有 active revision：返回 empty `GraphRevisionViewDTO`。
2. revision 存在但 relations 为空：返回 revision + nodes + empty relations。
3. relation 指向缺失 node：测试应暴露为数据一致性错误，不在 read model 中静默修复。

不捕获 SQLite / 代码级异常。真实异常应暴露给测试。

## 12. 测试边界

本阶段测试重点：

1. `KnowledgeRelationRecord` JSON round-trip。
2. SQLite 能写入和读取 `graph_knowledge_relations`。
3. `KnowledgeSignalGraphProjector` 能在有弱点和支撑节点时生成 `supports` relation。
4. `GraphRevisionRecord.relation_count` 等于生成 relation 数量。
5. `AssessmentSynthesizer` 会把 `support_signals` 物化成 `support_relation` facts。
6. `AssessmentFactSignalProjector` 会把 `support_relation` facts 物化成 `support_relation` signals。
7. submit-side orchestration 会把 relation 写入 checkpoint store。
8. `WorkspaceAPI.get_graph_revision_view` 返回 relation DTO。
9. HTTP `/api/knowledge/graph-revision` 在 submit 后能读到 relation。
10. 最小真实闭环测试使用 HTTP submit + SQLite store + graph-revision read，不只测单个 projector 函数。
11. 现有 `/api/knowledge/graph-main` 兼容测试继续通过。

不测试：

1. 前端 relation 展示。
2. graph-main relation 映射。
3. relation layout。
4. Maintenance Agent rewrite。
5. LLM 生成 relation。

## 13. 离用户真实使用还差什么

完成本阶段后，后端 Graph Layer 会从 topic list 变成最小 graph，但仍未达到真实用户长期使用：

1. 还没有 Graph Layer user state。
2. 还没有 revision-scoped focus cluster。
3. UI 还没有正式切换到 revision graph。
4. relation 语义只有 deterministic `supports`，不够丰富。
5. 还没有 Maintenance Agent 做整理、压缩、重构。

因此本阶段的真实价值是“让 graph 结构闭环成立”，不是“完成图谱产品体验”。

## 14. 后续阶段

推荐顺序：

```text
KnowledgeRelation v1
  -> Graph Layer user state / focus cluster
  -> Graph UI 正式切换
  -> Maintenance Agent
  -> LLM full live/golden eval
```

其中 `KnowledgeRelation v1` 是进入 user state / focus cluster 前的必要结构基础。没有 relation，focus cluster 会退化成 topic grouping，而不是图谱片区。
