# Graph Read Surface 设计

> 本文定义 submit-side 已写入的 `GraphRevision -> KnowledgeNode` 如何进入 workspace/http 读面。目标是让新 Graph Layer 可读，同时不破坏现有 profile-space graph/map v1 页面。

## 1. 当前状态

当前已经完成三段写入链路：

```text
AssessmentFactItemRecord
  -> KnowledgeSignalRecord
  -> GraphRevisionRecord + KnowledgeNodeRecord[] + ActiveGraphRevisionPointerRecord
```

submit-side 主链现在会在一次 answer submit 后自动写入：

```text
knowledge_signals
graph_revisions
graph_knowledge_nodes
active_graph_revision_pointers
```

但现有 workspace/http 读面仍主要读取旧路径：

```text
WorkspaceAPI.get_knowledge_graph_view()
  -> ProfileSpaceService.list_knowledge_nodes()

WorkspaceAPI.get_knowledge_graph_main_view()
  -> ProfileSpaceService.list_map_nodes()
  -> ProfileSpaceService.list_user_node_states()
  -> ProfileSpaceService.list_focus_clusters()
  -> ProfileSpaceService.list_knowledge_relations()
```

因此当前系统处于“新 graph 可写、storage 可查，但主业务读面还没有消费新 graph”的状态。

## 2. 本阶段目标

本阶段目标是把新 active graph revision 接入 `WorkspaceAPI.get_knowledge_graph_main_view()`：

```text
WorkspaceAPI.get_knowledge_graph_main_view(project_id, stage_id)
  -> SQLiteStore.get_active_graph_revision_pointer(project_id, "stage", stage_id)
  -> SQLiteStore.get_graph_revision(active_graph_revision_id)
  -> SQLiteStore.list_graph_nodes(active_graph_revision_id)
  -> KnowledgeGraphMainViewDTO
```

如果新 active revision 不存在，继续走旧 profile-space fallback：

```text
ProfileSpaceService.list_map_nodes()
ProfileSpaceService.list_user_node_states()
ProfileSpaceService.list_focus_clusters()
ProfileSpaceService.list_knowledge_relations()
```

这样可以让新链路进入现有 HTTP endpoint，同时保留 demo seed、旧测试和旧 UI 的兼容性。

## 3. 推荐方案

推荐采用“新 graph 优先，旧 profile fallback”。

理由：

1. 新写入链路已经能生成 active pointer，读面应该以 pointer 作为“当前图版本”的唯一入口。
2. 现有前端已经消费 `/api/knowledge/graph-main`，优先复用该入口可以最快形成写读闭环。
3. 旧 profile-space graph 仍承担 demo seed 和历史 UI 兼容职责，不应在本阶段删除。
4. 独立新增 endpoint 会形成两个并行读面，短期更安全，但会推迟主业务闭环。
5. 同时做 endpoint 和 graph-main 会扩大测试矩阵，不符合当前“先让新主链可读”的目标。

## 4. 非目标

本阶段不做：

1. 新增 `KnowledgeRelationRecord`。
2. 新增 graph relation 表。
3. LLM graph consolidation。
4. Maintenance Agent。
5. UI 视觉重做。
6. 删除或迁移旧 `ProfileSpaceService` graph/map v1。
7. 设计 user node state、focus cluster、focus explanation 的新 Graph Layer 版本。
8. 修改 submit-side projection 写入顺序。

## 5. API 边界

本阶段优先改 `WorkspaceAPI.get_knowledge_graph_main_view()`，不改 `get_knowledge_graph_view()`。

原因：

1. `graph-main` 已经是当前知识图谱主视图 DTO，包含 node cards 和 relations。
2. 新 Graph Layer v1 当前只有 revision-scoped nodes，没有 relations、clusters、user state。
3. `get_knowledge_graph_view()` 当前更接近旧 simple graph/list 入口，先不扩散迁移面。

HTTP 层不新增 endpoint：

```text
GET /api/knowledge/graph-main
```

继续调用：

```text
WorkspaceAPI.get_knowledge_graph_main_view(project_id, stage_id, cluster_id, node_id)
```

其中 `cluster_id` 和 `node_id` 在新 graph path 中暂不参与过滤。它们只在 fallback profile path 中保留旧语义。

## 6. DTO 映射

新 `KnowledgeNodeRecord` 映射到现有 `KnowledgeNodeCardDTO`：

```text
KnowledgeNodeRecord.knowledge_node_id -> KnowledgeNodeCardDTO.node_id
KnowledgeNodeRecord.label -> KnowledgeNodeCardDTO.label
KnowledgeNodeRecord.node_type -> KnowledgeNodeCardDTO.node_type
KnowledgeNodeRecord.topic_key -> evidence_summary["topic_key"]
KnowledgeNodeRecord.description -> KnowledgeNodeCardDTO.canonical_summary
KnowledgeNodeRecord.confidence -> evidence_summary["confidence_percent"]
len(KnowledgeNodeRecord.source_signal_ids) -> evidence_summary["signal_count"]
len(KnowledgeNodeRecord.supporting_fact_ids) -> evidence_summary["fact_count"]
```

长期看，新 graph DTO 应该独立表达 `graph_revision_id`、`source_signal_ids`、`supporting_fact_ids`、`confidence` 等字段。但本阶段先复用 `KnowledgeGraphMainViewDTO`，避免 UI 和 transport schema 同时扩张。

默认字段：

```text
abstract_level = "topic"
scope = "stage"
mastery_status = "unverified"
review_needed = node_type == "weakness_topic"
relation_preview = []
relations = []
selected_cluster = None
```

## 7. Store 依赖

`WorkspaceAPI` 当前构造依赖里已经有 `ReviewFlowService`、`ProposalCenter`、`ProfileSpaceService` 和 session store。

本阶段需要让 `WorkspaceAPI` 可选持有 `SQLiteStore`：

```text
WorkspaceAPI(..., checkpoint_store: SQLiteStore | None = None)
```

读取顺序：

1. 如果 `checkpoint_store` 为空，直接走旧 profile fallback。
2. 如果 `project_id` 或 `stage_id` 为空，直接走旧 profile fallback。
3. 查询 active pointer：`get_active_graph_revision_pointer(project_id, "stage", stage_id)`。
4. 如果 pointer 不存在，走旧 profile fallback。
5. 如果 pointer 存在但 revision 或 nodes 查不到，走旧 profile fallback。
6. 如果 pointer、revision、nodes 都存在，返回新 graph DTO。

`create_default_workspace_api(db_path=...)` 应把同一个 `SQLiteStore` 传给 `WorkspaceAPI`，这样通过 HTTP submit 后再读 `/api/knowledge/graph-main` 能看到新 graph。

## 8. 错误边界

读面采用 fallback，而不是严格失败。

原因：

1. 写入链路已经采用严格失败，用于暴露 projection 错误。
2. 读面要服务 UI 和 demo，不能因为新 graph 暂无 active revision 就让页面失败。
3. fallback 可以支持渐进迁移：新 graph 存在时用新 path，不存在时旧体验不变。

但本阶段不吞掉真实代码异常：

1. `checkpoint_store` 方法抛出的非空缺异常不做广泛 catch。
2. 只对“查不到 pointer / revision / nodes 为空”做 fallback。
3. 不引入跨层修复逻辑，例如读面补写 pointer 或生成 graph。

## 9. 测试边界

本阶段测试重点：

1. `WorkspaceAPI.get_knowledge_graph_main_view()` 在 active graph revision 存在时返回新 graph nodes。
2. 返回 DTO 中 `selected_cluster is None`、`relations == []`。
3. weakness node 映射为 `review_needed=True`、`mastery_status="unverified"`。
4. 当 active pointer 不存在时，旧 profile-space fallback 行为保持不变。
5. HTTP `/api/knowledge/graph-main` 在 submit 后能读到新 graph node。
6. demo seed 旧路径继续通过。

不测试：

1. graph relation 展示。
2. cluster filtering。
3. node selection side panel。
4. UI canvas/rendering。
5. LLM maintenance。

## 10. 验收标准

本阶段完成后应满足：

1. 一次 submit 后，`/api/knowledge/graph-main` 能读到新 `graph_knowledge_nodes`。
2. 没有 active graph revision 时，旧 graph-main profile-space 行为不变。
3. `KnowledgeGraphMainViewDTO` 不新增必填字段，避免前端破坏。
4. 旧 `get_knowledge_graph_view()` 暂不变。
5. 所有 workspace/http/demo seed 相关测试通过。

## 11. 后续阶段

完成 read surface 后，再考虑：

1. 是否新增独立 revision-aware DTO。
2. 是否让 `/api/knowledge/graph` 也切到新 graph。
3. 是否引入 `KnowledgeRelationRecord`。
4. 是否设计新 Graph Layer 的 user state / focus cluster。
5. 是否把旧 `ProfileSpaceService` graph/map v1 逐步退场。
