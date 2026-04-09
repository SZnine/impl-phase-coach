# impl-phase-coach 当前状态接手文档

用途：给后续对话或后续阶段快速接手当前工作，不依赖完整历史对话。

## 1. 当前基线

- 仓库路径：`D:\Desktop\impl-phase-coach`
- 当前分支：`main`
- 最近已提交基线：`e392c7b docs: freeze support signal derivation rules`
- 当前工作区：在 `e392c7b` 之上继续推进了 `阶段 40 / support_signals 结构化派生最小实现`，尚未提交
- 当前主线：
  1. 稳定性优先主线已经收出可用基线
  2. 当前更活跃的是 `知识地图 V1 主线`

## 2. 当前知识地图主线结论

当前已经不是“有没有知识图页面”的问题，而是“知识地图是否已成为真实资产入口”的问题。

已经冻结的核心判断：

1. 这是一个以知识地图为核心索引层的个人工作台，不是一个附属图页
2. 节点是混合节点，且 `foundation` 必须是一等节点
3. 节点本体和用户状态必须分开：
   - `KnowledgeNode`
   - `UserNodeState`
4. 证据锚点默认不进入主图，而作为附属证据层按需展开
5. 知识地图入口是：
   - `/knowledge` 摘要页
   - `/knowledge/graph` 主图页
6. 默认主图围绕 `FocusCluster` 展开，而不是围绕单个节点或全量图展开
7. 当前 explanation 链已经明确：
   - 先有 cache 宿主
   - 再有可替换 generator
   - 当前不接实时 LLM

## 3. 已完成的知识地图 V1 范围

### Task 1

已完成核心对象与 SQLite 宿主：

1. `KnowledgeNode`
2. `EvidenceRef`
3. `UserNodeState`
4. `KnowledgeRelation`
5. `FocusCluster`

关键文件：

- `review_gate/domain.py`
- `review_gate/storage_sqlite.py`
- `tests/test_workbench_storage.py`

### Task 2

已完成 `assessment -> durable knowledge objects` 的最小投影：

1. `KnowledgeNode`
2. `EvidenceRef`
3. `UserNodeState`

关键文件：

- `review_gate/profile_space_service.py`
- `tests/test_profile_space_service.py`

### Task 3

已完成知识地图后端最小读面：

1. `GET /api/knowledge`
2. `GET /api/knowledge/graph-main`

关键文件：

- `review_gate/view_dtos.py`
- `review_gate/workspace_api.py`
- `review_gate/http_api.py`
- `tests/test_workspace_api.py`
- `tests/test_http_api.py`

### Task 4

已完成知识地图前端最小入口：

1. `/knowledge` 作为摘要页入口
2. `/knowledge/graph` 作为主图页入口
3. `KnowledgeNodeCard` 作为节点最小详情宿主

关键文件：

- `frontend/src/pages/KnowledgeMapPage.tsx`
- `frontend/src/pages/KnowledgeGraphPage.tsx`
- `frontend/src/components/KnowledgeNodeCard.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/routes.tsx`
- `frontend/src/components/WorkbenchLayout.tsx`

### Task 5

已完成知识地图 V1 的 scope lock 与 regression 收口：

1. 锁定 `/api/knowledge` 不退化成证据堆
2. 锁定 `/api/knowledge/graph-main` 不把 evidence 当主图节点
3. handoff 首次同步到知识地图 V1

### Task 6

已完成最小关系生成与 `FocusCluster` 稳定化：

1. 只生成：
   - `abstracts`
   - `causes_mistake`
2. `FocusCluster` 从 assessment 粒度收成热点粒度
3. cluster id 基于 `project + stage + hotspot slug` 稳定生成
4. 重复 assessment 会复用已有 cluster，而不是每次新建

### Task 7

已完成 `FocusExplanation` cache：

1. 新对象：`FocusExplanation`
2. explanation cache 有独立 SQLite 宿主
3. `workspace_api` 已采用：
   - `cache first`
   - `fallback second`

### 阶段 27

已完成主图最小关系可视化闭环：

1. 主图能看到中心节点
2. 主图能看到邻居节点
3. 主图能看到连接关系和关系标签

当前仍是片区表达，不是真正拓扑布局。

### 阶段 28

已完成 `FocusCluster` 排序与摘要入口可读性收口：

1. 焦点簇顺序不再按写入顺序漂
2. 摘要页已有 `Why it matters`
3. reason codes 已进入可读 badge

### 阶段 32

已完成 explanation generator 策略层拆分：

1. 新文件：`review_gate/explanation_generators.py`
2. 新协议：`FocusExplanationGenerator`
3. 默认实现：`DeterministicFocusExplanationGenerator`
4. `ProfileSpaceService` 已支持通过 generator 注入 explanation 生成策略

这意味着 explanation 现在已经明确分成三层：

1. `FocusExplanation`：缓存宿主
2. `ExplanationGenerator`：生成策略
3. `workspace_api`：只读 cache，不参与生成

### 阶段 36

已完成 `supports` 的最小高置信扩展：

1. 只在显式 `support_signals` 存在时生成 `supports`
2. 当前只允许三类高置信关系：
   - `foundation -> concept`
   - `foundation -> method`
   - `concept -> decision`
3. 单纯共现不会生成 `supports`
4. 重复 assessment 会复用稳定 `supports` relation id，不会重复刷边

当前这一步仍然是 deterministic default strategy，不接 LLM/agent 做关系推断。

### 阶段 40

已完成 `support_signals` 的结构化派生最小实现：

1. `AssessmentFact` 新增：
   - `dimension_hits`
   - `support_basis_tags`
   - `support_signals`
2. `ReviewFlowService.submit_answer(...)` 已在 assessment 产出时派生：
   - `dimension_hits`
   - `support_signals`
3. `ProfileSpaceService` 继续只消费结构化 `support_signals`
4. `WorkspaceAPI submit_answer` 主链已经可以把派生后的 `supports` 投影进知识地图

当前最关键的边界是：

1. assessment 负责产出结构化 signal
2. profile space 负责消费 signal 并投影关系
3. 当前仍然禁止从自由文本直接推 `supports`

## 4. 当前仍然属于过渡态的部分

这些现在是诚实可用，但还不是长期目标实现：

1. `KnowledgeGraphPage` 仍然是片区式关系表达，不是真正拓扑布局
2. `KnowledgeRelation` 目前只生成最小关系：
   - `abstracts`
   - `causes_mistake`
3. `FocusCluster` 仍是用户侧最小对象，不是全局候选簇系统
4. explanation 仍由 deterministic generator 生成，不是异步预生成 LLM explanation
5. proposal 还没有正式升级成“知识网络治理中心”

## 5. 当前最重要的边界

后续接手时最容易混淆的是下面几组边界：

1. `KnowledgeNode` vs `UserNodeState`
   - 前者是知识本体
   - 后者是当前用户与该节点的关系状态

2. `FocusCluster` vs `FocusExplanation`
   - 前者回答“当前哪个片区值得看”
   - 后者回答“为什么它现在重要”

3. `Explanation cache` vs `Explanation generator`
   - 前者是结果宿主
   - 后者是策略实现

4. `deterministic default strategy` vs `future LLM/agent strategy`
   - 当前用前者
   - 但不把策略点写死

## 6. 当前 agent / LLM 接入原则

当前已经冻结的原则：

1. 当前先用 deterministic default strategy 落地
2. 高语义推断点要集中成可替换策略接缝
3. 不因为当前阶段就把未来需要灵活替换的策略硬写死
4. 但也不因为未来可能接模型，就提前把当前实现过度复杂化

一句话原则：

`硬定事实，不硬定策略。`

也就是：

1. 硬定：
   - 对象
   - store
   - DTO
   - 审计边界
   - 证据锚点
2. 留活：
   - explanation generator
   - relation inference
   - focus scoring
   - 去重/重构建议

如果后续出现下面这些情况，就值得显式考虑接入真实 agent / LLM：

1. relation inference 的规则复杂度明显失控
2. FocusCluster 聚合评分开始依赖高语义判断
3. explanation 文案 deterministic 方案开始明显脆弱
4. 节点合并 / 重命名 / 升降层建议开始进入高价值阶段

## 7. 当前验证状态

最近一轮和阶段 40 直接相关的验证结果：

1. `python -m pytest tests/test_review_flow_service.py::test_submit_answer_derives_support_signals_from_support_basis_tags tests/test_review_flow_service.py::test_submit_answer_derives_support_signals_from_dimension_hits_and_core_gaps tests/test_workspace_api.py::test_submit_answer_action_projects_derived_support_signals_into_supports_relations tests/test_workbench_storage.py::test_sqlite_store_round_trips_durable_facts -q` -> `4 passed`
2. `python -m pytest tests/test_review_flow_service.py tests/test_workspace_api.py tests/test_workbench_storage.py -q` -> `38 passed`

当前已知非阻塞项：

1. `datetime.utcnow()` deprecation warning
2. React Router v7 future flag warning
3. `App.test.tsx` 里的 `act(...)` warning

## 8. 当前下一步建议

当前最合理的下一步不是扩更多页面，而是继续在知识地图主线上做“assessment client 契约收口”或“主图表达轻增强”。

推荐优先级：

1. 先做文档/基线同步后的 checkpoint
2. 再决定是否进入：
   - `support_signals` 是否正式进入 assessment client 契约
   - 或主图轻增强

如果继续实现，我建议优先围绕：

1. `support_signals` 是否正式进入 assessment client 契约
2. assessment 结构化字段是否需要更稳定 schema

而不是现在就扩复杂图交互。

## 9. 新对话启动 prompt

如果要在新对话里继续，可以直接给出下面这段：

```text
请先阅读：
1. docs/superpowers/handoffs/2026-04-08-current-state-handoff.md
2. docs/superpowers/plans/2026-04-08-knowledge-map-core-model.md
3. docs/superpowers/plans/2026-04-08-knowledge-map-v1-implementation.md

当前基线：
- 最近已提交基线：e392c7b docs: freeze support signal derivation rules
- 当前工作区已经继续推进到“阶段 40 / support_signals 结构化派生最小实现”，但还未提交

请按 impl-phase-coach 方式继续：
1. 先判断当前阶段
2. 先给出当前阶段目标/产物/退出条件
3. 不跨阶段
4. 默认提供：
   A. 我自己补充
   B. 你直接补充

当前最重要的边界：
- KnowledgeNode vs UserNodeState
- FocusCluster vs FocusExplanation
- explanation cache vs explanation generator
- deterministic default strategy vs future LLM/agent strategy

当前重点不是扩新页面，而是继续知识地图主线的策略层与价值表达收口。
```
