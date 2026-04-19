# Submit-Side Graph Projection Orchestration 设计

> 本文定义 submit-side checkpoint 主链如何接入已经完成的 `AssessmentFact -> KnowledgeSignal -> GraphRevision` 能力。目标是让一次用户提交答案后，系统自动沉淀 signals 和 active graph revision。

## 1. 当前状态

当前已经具备三段能力：

```text
AssessmentFactItemRecord -> KnowledgeSignalRecord
KnowledgeSignalRecord[] -> GraphRevisionRecord + KnowledgeNodeRecord[] + ActiveGraphRevisionPointerRecord
SQLiteStore persists signals / graph revisions / graph nodes / active pointers
```

但 submit-side 主链当前只做到：

```text
AnswerCheckpointWriter.write()
  -> AssessmentSynthesizer
  -> insert AssessmentFactBatchRecord
  -> insert AssessmentFactItemRecord[]
```

因此当前 graph projection 是“可测试、可手动调用”的能力，还不是业务主链的一部分。

## 2. 本阶段目标

把 submit-side checkpoint 主链扩展为：

```text
AnswerCheckpointWriter.write()
  -> write workflow / answer / evaluation checkpoints
  -> synthesize assessment facts
  -> insert assessment facts
  -> project assessment facts to knowledge signals
  -> insert knowledge signals
  -> project knowledge signals to graph revision
  -> insert graph revision
  -> insert graph nodes
  -> upsert active graph revision pointer
```

完成后，一次 submit flow 应能通过 storage 查询到：

1. assessment fact batch/items
2. knowledge signals
3. active graph revision pointer
4. graph revision
5. graph nodes

## 3. 放置位置

接入点放在 `AnswerCheckpointWriter.write()` 内。

理由：

1. 它已经是 submit-side checkpoint 主链的写入边界。
2. 它已经拥有 `SubmitAnswerRequest`，可以拿到 `project_id`、`stage_id`、`created_at`。
3. 它已经拿到 `fact_batch` 和 `fact_items`。
4. graph projection 是 facts 的派生写入，不应放进 `AssessmentSynthesizer`。
5. graph projection 不应放进 `ReviewFlowService`，否则会让 service 重新承担 checkpoint 细节。
6. 不触碰 `ProfileSpaceService`，避免新 graph layer 和旧 profile/map v1 串味。

## 4. 新增依赖

`AnswerCheckpointWriter` 当前依赖：

```text
SQLiteStore
AssessmentSynthesizer
```

本阶段新增两个依赖：

```text
AssessmentFactSignalProjector
KnowledgeSignalGraphProjector
```

推荐构造方式：

```text
AnswerCheckpointWriter(
  store,
  synthesizer,
  signal_projector=None,
  graph_projector=None,
)
```

如果调用方不传，则 writer 内部使用默认 projector。这样不会强迫现有测试和 `ReviewFlowService` 一次性改完所有调用点，同时仍然允许测试注入替身。

## 5. 写入顺序

推荐顺序：

```text
1. insert workflow in-progress
2. insert answer/evaluation checkpoints
3. synthesize facts
4. insert fact batch/items
5. project fact batch/items -> knowledge signals
6. insert knowledge signals
7. if signals are not empty:
     project signals -> graph revision/nodes/pointer
     insert graph revision
     insert graph nodes
     upsert active pointer
8. mark workflow completed
9. return CheckpointWriteResult
```

关键点：

1. `KnowledgeSignal` 必须在 graph projection 前落库。
2. `GraphRevision` 必须在 `KnowledgeNode` 和 pointer 前落库。
3. pointer 必须最后写入，避免指向一个尚未完整写入的 revision。

## 6. 空 signals 处理

如果 `fact_items` 为空，或 projector 生成的 `knowledge_signals` 为空：

1. 不创建 graph revision。
2. 不创建 graph nodes。
3. 不更新 active pointer。
4. `CheckpointWriteResult.graph_revision_id = None`。
5. `CheckpointWriteResult.knowledge_signal_count = 0`。
6. submit flow 仍然完成。

理由：Graph 是派生层，不应该因为本次评估没有可沉淀 signal 而制造空 graph revision。

## 7. CheckpointWriteResult 扩展

当前字段：

```text
workflow_run_id
question_batch_id
answer_batch_id
evaluation_batch_id
assessment_fact_batch_id
```

建议新增：

```text
assessment_fact_item_count: int
knowledge_signal_count: int
graph_revision_id: str | None
graph_node_count: int
```

这些字段只用于运行观测和测试断言，不作为下游业务真相。真实数据仍以 storage 表为准。

## 8. 错误边界

v1 推荐采用“严格失败”：

1. 如果 facts 写入成功但 signal/graph projection 抛异常，`AnswerCheckpointWriter.write()` 直接抛出。
2. 不在本阶段吞掉 graph projection 错误。
3. 不在本阶段实现跨表事务回滚。

理由：

1. 当前是重构迁移期，静默失败会掩盖主链未接通的问题。
2. 现有 SQLiteStore 方法本身已经是分步写入风格，本阶段不引入新的 transaction manager。
3. Graph projection 是 deterministic 代码，不是外部 LLM 或网络调用，失败应视为代码问题。

后续如果要让派生层失败不影响 submit，需要单独设计 `derived_projection_status` 或 workflow event，而不是在本阶段隐式吞错。

## 9. 测试边界

本阶段测试重点：

1. `AnswerCheckpointWriter.write()` 返回新增观测字段。
2. submit 后 `list_knowledge_signals_for_fact_batch(...)` 能查到 signals。
3. submit 后 `get_active_graph_revision_pointer(project_id, "stage", stage_id)` 能查到 pointer。
4. pointer 指向的 revision 能查到 graph nodes。
5. 当 assessment 没有 gaps 时，不创建 graph revision，不更新 pointer。
6. 旧 `list_knowledge_nodes()` / `list_knowledge_relations()` 仍为空。

不测试：

1. HTTP/UI 读面。
2. KnowledgeRelation。
3. Maintenance Agent。
4. LLM graph consolidation。

## 10. 非目标

本阶段不做：

1. `KnowledgeRelationRecord`
2. graph read API / UI 接入
3. `ProfileSpaceService` 迁移
4. Maintenance Agent
5. relation consolidation
6. graph rewrite history
7. user node state / focus cluster
8. 跨表事务管理器

## 11. 验收标准

本阶段完成后应满足：

1. 一次普通 submit 能自动生成 knowledge signals。
2. 一次普通 submit 能自动生成 active graph revision。
3. graph nodes 是 revision-scoped，不写入旧 graph/profile 表。
4. `CheckpointWriteResult` 能暴露 signal/node/revision 观测字段。
5. 无 signal 的 submit 不创建空 graph revision。
6. 所有现有 submit-side checkpoint 测试继续通过。

## 12. 下一阶段

完成该 orchestration 后，下一步再考虑 graph read surface：

```text
active_graph_revision_pointer
  -> graph_revision
  -> graph_nodes
  -> workspace/http read DTO
```

只有当 read surface 稳定后，再进入 `KnowledgeRelation` 或 Maintenance Agent。否则会在 graph 还不可读时提前引入关系复杂度。
