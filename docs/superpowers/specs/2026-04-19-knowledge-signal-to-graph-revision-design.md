# KnowledgeSignal -> GraphRevision v1 设计

> 本文定义 `KnowledgeSignal` 进入 Knowledge Graph Layer 的第一版投影方案。目标是产出一个可激活、可读取、可追溯的最小图谱版本，而不是完整知识维护系统。

## 1. 当前定位

上一阶段已经完成：

```text
AssessmentFactItemRecord
  -> KnowledgeSignalRecord
```

当前阶段进入：

```text
KnowledgeSignalRecord
  -> GraphRevisionRecord
  -> KnowledgeNodeRecord
  -> ActiveGraphRevisionPointerRecord
```

这一步开始真正进入 Graph Layer，但仍然只做 deterministic projection，不引入 Knowledge Maintenance Agent，不调用 LLM，不做复杂关系推理。

## 2. 推荐切法

本阶段推荐做“无关系的最小可激活图谱版本”：

1. 一个 projection run 生成一个 `GraphRevisionRecord`。
2. 同一个 `topic_key` 下的 signals 聚合成一个 `KnowledgeNodeRecord`。
3. node 保留 `source_signal_ids` 和 `supporting_fact_ids`。
4. relation 暂不生成，`relation_count = 0`。
5. projection 成功后写入 `ActiveGraphRevisionPointerRecord`，让读面可以找到当前 active revision。

核心数据流：

```text
knowledge_signals
  -> graph_revisions
  -> graph_knowledge_nodes
  -> active_graph_revision_pointers
```

## 3. 为什么不只做 GraphRevision 空壳

只做 `GraphRevisionRecord` 会形成局部最小，但对终态帮助很弱：

1. 没有 node，读面无法展示任何长期知识对象。
2. 没有 active pointer，系统无法稳定回答“当前是哪一版图”。
3. 后续实现仍然要重新打开同一批 schema 和 projection 边界。

因此本阶段至少需要同时包含 revision、node 和 active pointer。

## 4. 为什么暂不做 KnowledgeRelation

`KnowledgeRelation` 的复杂度不在建表，而在语义：

1. relation type 需要更稳定的领域规则。
2. directionality 会引入因果、前置、包含、相似等区分。
3. 多个 signal 之间的冲突和合并需要维护策略。
4. relation 权重和置信度更适合由 Maintenance Agent 或后续 graph consolidation 处理。

如果当前阶段强行生成 relation，容易把 deterministic v1 写成不可维护的启发式规则。因此 v1 明确不生成 relation，只保留 revision 的 `relation_count = 0`。

## 5. GraphRevisionRecord 边界

`GraphRevisionRecord` 回答“当前是哪一版图”。

建议字段：

1. `graph_revision_id`
2. `project_id`
3. `scope_type`
4. `scope_ref`
5. `revision_type`
6. `based_on_revision_id`
7. `source_fact_batch_ids`
8. `source_signal_ids`
9. `status`
10. `revision_summary`
11. `node_count`
12. `relation_count`
13. `created_by`
14. `created_at`
15. `activated_at`
16. `payload`

v1 约束：

1. `revision_type = "deterministic_signal_projection"`。
2. `status` 先使用 `active` 或 `superseded`。
3. `based_on_revision_id` 可为空，后续重构时再使用。
4. `source_signal_ids` 记录本 revision 消费的 signal 集合。

## 6. KnowledgeNodeRecord 边界

`KnowledgeNodeRecord` 回答“这一版图里有什么长期知识对象”。

建议字段：

1. `knowledge_node_id`
2. `graph_revision_id`
3. `topic_key`
4. `label`
5. `node_type`
6. `description`
7. `source_signal_ids`
8. `supporting_fact_ids`
9. `confidence`
10. `status`
11. `created_by`
12. `created_at`
13. `updated_at`
14. `payload`

v1 聚合规则：

1. 按 `topic_key` 分组。
2. 每组生成一个 node。
3. `knowledge_node_id = kn-{graph_revision_id}-{topic_key}`，实现时需要对 topic key 做安全化处理。
4. `label` 优先使用该组最高 confidence signal 的 summary。
5. `node_type` 优先按 signal 类型聚合：有 weakness 则为 `weakness_topic`，只有 strength 则为 `strength_topic`，否则为 `evidence_topic`。
6. `confidence` 取该组 signals 的最大 confidence。
7. `source_signal_ids` 收集该组全部 signal id。
8. `supporting_fact_ids` 收集该组全部 assessment fact item id。

## 7. ActiveGraphRevisionPointerRecord 边界

`ActiveGraphRevisionPointerRecord` 回答“某个 project/scope 当前使用哪一版图”。

建议字段：

1. `project_id`
2. `scope_type`
3. `scope_ref`
4. `active_graph_revision_id`
5. `updated_at`
6. `updated_by`
7. `payload`

v1 约束：

1. pointer 只指向已成功写入的 revision。
2. 同一 `project_id + scope_type + scope_ref` 只有一个 active pointer。
3. pointer 更新不修改旧 revision 和旧 nodes。
4. 如果后续需要审计 pointer 切换，再追加 pointer history；v1 不做。

## 8. Projector 边界

推荐新增：

```text
KnowledgeSignalGraphProjector
```

职责：

1. 输入一组 `KnowledgeSignalRecord`。
2. 输入 projection scope：`project_id`、`scope_type`、`scope_ref`。
3. 输出 `GraphRevisionRecord`、`KnowledgeNodeRecord[]`、`ActiveGraphRevisionPointerRecord`。
4. 不读取旧 `ProfileSpaceService`。
5. 不写旧 `knowledge_map_node_store` / `knowledge_relation_store`。
6. 不生成 relation。
7. 不调用 LLM。

projector 可以是纯对象转换；持久化由 `SQLiteStore` 方法负责。

## 9. 持久化边界

新增三张表：

1. `graph_revisions`
2. `graph_knowledge_nodes`
3. `active_graph_revision_pointers`

本阶段不新增：

1. `graph_knowledge_relations`
2. `graph_rewrite_records`
3. `user_node_states`
4. `focus_clusters`
5. `focus_explanations`

命名上建议避免复用旧表 `knowledge_node_store`，因为旧表服务 profile/map v1，语义不是 revision-scoped graph node。

## 10. 读面边界

本阶段只需要提供 storage read methods，不强制接入 HTTP/UI：

1. `get_graph_revision(graph_revision_id)`
2. `list_graph_nodes(graph_revision_id)`
3. `get_active_graph_revision_pointer(project_id, scope_type, scope_ref)`

是否把 active graph 接到 workspace API，放到下一阶段决定。原因是当前阶段先确保 graph projection 数据层成立，避免把 API/UI 读面和 schema 设计混在一起。

## 11. 验收标准

本阶段完成时应满足：

1. 可以从一组 knowledge signals 生成一个 graph revision。
2. 同 topic signals 被聚合为同一个 revision-scoped node。
3. revision 记录 node_count、relation_count、source_signal_ids。
4. active pointer 指向最新生成的 revision。
5. 新 graph nodes 不写入旧 `knowledge_map_node_store`。
6. projection 不调用 LLM。
7. 测试覆盖：单 topic、多 topic、active pointer 替换、旧 graph store 隔离。

## 12. 下一阶段

完成 v1 后，下一阶段再考虑：

1. `KnowledgeRelationRecord`
2. graph read API / UI 接入
3. Knowledge Maintenance Agent
4. relation consolidation
5. graph rewrite history
6. user node state 和 focus cluster

当前阶段的核心判断是：先建立“可激活的 revision-scoped node graph”，不要把 relation 和 maintenance 复杂度提前带入。
