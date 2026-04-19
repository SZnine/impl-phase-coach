# Facts -> Graph 迁移入口设计

> 本文只定义从当前已落地的 Assessment Facts 进入未来 Knowledge Graph 的第一道稳定入口。它不是完整图谱实现计划，也不替换终态业务架构文档。

## 1. 当前定位

项目当前已经完成了从题集、作答、评估到 `AssessmentFactBatchRecord` / `AssessmentFactItemRecord` 的事实沉淀。下一步如果直接把这些 fact 投影成 graph node/relation，会把事实层、图谱层和旧的 profile projection 再次耦合在一起。

因此本阶段的迁移入口应定义为：

```text
AssessmentFactItemRecord -> KnowledgeSignalRecord
```

而不是：

```text
AssessmentFactItemRecord -> KnowledgeNode / KnowledgeRelation
```

`KnowledgeSignal` 是事实层和图谱层之间的桥接对象。它仍然保留事实来源，但已经转成图谱维护可以消费的稳定信号。

## 2. 设计目标

1. 固定 Facts -> Graph 的第一道对象契约，避免后续 GraphRevision 设计反复牵动事实层。
2. 保持 Assessment Facts 为历史真相层，Graph 只作为派生层。
3. 让后续 Knowledge Maintenance Agent 或 deterministic graph projector 都能消费同一种 signal 输入。
4. 保留完整可追溯性：任意 signal 都能追回产生它的 fact batch 和 fact item。

## 3. 非目标

本阶段不做以下内容：

1. 不创建新版 `KnowledgeNode` / `KnowledgeRelation`。
2. 不创建 `GraphRevision`。
3. 不维护 `active_graph_revision_pointers`。
4. 不替换旧的 `ProfileSpaceService.sync_from_assessment`。
5. 不做图谱合并、去重、衰减、聚类、冲突消解。
6. 不把旧的 `knowledge_node_store` 扩写成终态 graph 表。

这些能力属于下一阶段的 Graph projection / Graph revision 工作。

## 4. 推荐数据流

长期数据流：

```text
Evaluation Item
  -> AssessmentFactBatch / AssessmentFactItem
  -> KnowledgeSignal
  -> GraphRevision
  -> KnowledgeNode / KnowledgeRelation
  -> ActiveGraphRevisionPointer
```

当前阶段只落地：

```text
AssessmentFactBatch / AssessmentFactItem
  -> KnowledgeSignal
```

这条路径应是 append-only。后续如果 signal 生成规则升级，可以生成新的 signal batch 或通过 `schema_version` / `projector_version` 区分，不反向修改历史 fact。

## 5. KnowledgeSignal 对象边界

`KnowledgeSignalRecord` 应表达“这条事实对未来知识图谱意味着什么”，而不是表达最终图谱结构。

建议字段：

1. `signal_id`：signal 唯一标识。
2. `fact_batch_id`：来源 fact batch。
3. `fact_item_id`：来源 fact item。
4. `session_id`：可选，便于按一次 review flow 回溯。
5. `signal_type`：信号类型，例如 `strength`, `weakness`, `misconception`, `evidence`, `followup`.
6. `topic_key`：稳定 topic 标识，优先来自 fact item 的 topic/category 归一化结果。
7. `confidence`：信号置信度，来自评估结果或 projector 规则。
8. `polarity`：正向、负向或中性，例如 `positive`, `negative`, `neutral`。
9. `summary`：短文本摘要，用于后续 agent 或 graph projector 消费。
10. `payload`：JSON 扩展字段，保留证据、原始维度、评分、标签等非稳定结构。
11. `projector_version`：生成规则版本。
12. `created_at`：创建时间。

关键约束：

1. signal 不应包含最终 node id 或 relation id。
2. signal 可以包含 topic hints，但不应声明最终图结构。
3. signal 必须可重复生成或至少可追溯生成规则。
4. signal 表应允许同一个 fact item 产生多条 signal。

## 6. 投影器边界

新增一个独立 projector，而不是把逻辑塞进 `AssessmentSynthesizer` 或 `ProfileSpaceService`。

推荐命名：

```text
AssessmentFactSignalProjector
```

职责：

1. 读取 `AssessmentFactBatchRecord` 和对应 `AssessmentFactItemRecord`。
2. 按 deterministic 规则生成 `KnowledgeSignalRecord`。
3. 不访问 graph store。
4. 不调用 LLM。
5. 不修改 assessment facts。

这样切分的原因是：当前阶段需要固定对象边界，不需要引入 graph lifecycle。LLM 可以在更上游生成 evaluation / assessment，也可以在未来 maintenance 阶段参与 graph consolidation，但不应让迁移入口依赖 LLM 才能稳定运行。

## 7. 持久化边界

新增 `knowledge_signals` 表即可。

推荐约束：

1. `signal_id` 为主键。
2. `fact_item_id` 建索引。
3. `fact_batch_id` 建索引。
4. `topic_key` 建索引。
5. `signal_type` 建索引。
6. 可选唯一约束：`fact_item_id + signal_type + topic_key + projector_version`，用于避免同一规则重复写入。

是否强制唯一应在实现时结合现有 storage 风格决定。更稳妥的第一版是先提供幂等 upsert 逻辑，而不是依赖复杂唯一键表达所有业务语义。

## 8. 与旧 ProfileSpaceService 的关系

旧 `ProfileSpaceService.sync_from_assessment` 可以暂时保留为 legacy projection path，但不要继续加厚。

迁移期边界：

1. 新路径从 `AssessmentFactItemRecord` 生成 `KnowledgeSignalRecord`。
2. 旧路径继续服务已有 demo 或历史测试。
3. 不让新 signal 写入旧 `knowledge_node_store`。
4. 后续 `GraphRevision` 落地后，再决定旧路径是适配、废弃还是迁移。

这样可以避免在还没有新版 graph revision 模型前，把新事实层强行接到旧 graph/profile 表。

## 9. 验收标准

本设计对应的实现阶段完成时，应满足：

1. 可以从一批 assessment facts 生成一批 knowledge signals。
2. signal 可追溯到原始 fact batch 和 fact item。
3. signal 生成不依赖 LLM。
4. signal 生成不写入旧 knowledge node/relation 表。
5. 测试覆盖一对一和一对多 signal 生成。
6. 测试覆盖幂等或重复投影处理。
7. 旧 review flow 行为不被破坏。

## 10. 后续阶段

完成 `KnowledgeSignal` 入口后，下一阶段才进入真正 Graph projection：

```text
KnowledgeSignal
  -> GraphRevision
  -> revision-scoped KnowledgeNode / KnowledgeRelation
  -> ActiveGraphRevisionPointer
```

届时再处理：

1. graph revision schema。
2. node/relation identity 策略。
3. signal 到 node/relation 的聚合规则。
4. active revision 切换。
5. Knowledge Maintenance Agent 的介入点。

当前设计的核心价值是：先把事实层和图谱层之间的门固定住，避免在图谱还没设计完时让 facts 直接流入旧 graph 结构。
