# impl-phase-coach 当前状态接手文档

用途：给后续对话或后续阶段快速接手当前工作，不依赖完整历史对话。

## 1. 当前基线

- 仓库路径：`D:\Desktop\impl-phase-coach`
- 当前分支：`main`
- 最近已提交基线：`9e843b7 feat: tighten workspace restore and profile signal gates`
- 当前主线：`稳定性优先`
- 当前工作区：存在未提交的知识地图 V1 改动

## 2. 当前主线

当前不是继续横向扩页面，也不是优先做知识质量增强。当前已经冻结成两条并行但不混写的线：

1. `稳定性主线`
   - durable facts
   - session restore
   - 真实使用回归
2. `知识地图 V1 主线`
   - 核心对象
   - 最小读面
   - 摘要页 -> 主图页
   - 最小关系
   - FocusCluster 稳定入口

当前更活跃的是第 2 条线，但前提仍是不能破坏稳定性基线。

## 3. 已完成的稳定性能力

这些能力已经成立：

1. `stage mastery` 跨重开恢复
2. `WorkspaceSession` 路径级恢复
3. 非法 session 目标会被后端收正并分级回退
4. `AnswerFact / AssessmentFact / DecisionFact` durable facts 已落地
5. 长期集合默认真实持久化：
   - `ProfileSpaceService.with_store(...)`
   - `ProposalCenterService.with_store(...)`
6. `submit_answer -> assessment -> stage summary refresh` 真实链路成立
7. `ProposalsPage` 最小动作闭环成立：
   - `accept`
   - `reject`
   - `defer`

## 4. 已完成的知识地图 V1 范围

### 4.1 核心模型与实现计划

相关文档：

- `docs/superpowers/plans/2026-04-08-knowledge-map-core-model.md`
- `docs/superpowers/plans/2026-04-08-knowledge-map-v1-implementation.md`

知识地图 V1 已冻结的核心对象顺序：

1. `KnowledgeNode`
2. `EvidenceRef`
3. `UserNodeState`
4. `KnowledgeRelation`
5. `FocusCluster`

公开关系最小集合：

1. `supports`
2. `depends_on`
3. `abstracts`
4. `causes_mistake`
5. `evidenced_by`

### 4.2 已完成的实现阶段

#### Task 1

已完成核心 domain 对象与 SQLite 宿主：

- `review_gate/domain.py`
- `review_gate/storage_sqlite.py`
- `tests/test_workbench_storage.py`

#### Task 2

已完成 assessment 到以下对象的最小 durable 投影：

1. `KnowledgeNode`
2. `EvidenceRef`
3. `UserNodeState`

关键文件：

- `review_gate/profile_space_service.py`
- `tests/test_profile_space_service.py`

#### Task 3

已完成知识地图后端最小读面：

1. `GET /api/knowledge`
2. `GET /api/knowledge/graph-main`

关键文件：

- `review_gate/view_dtos.py`
- `review_gate/workspace_api.py`
- `review_gate/http_api.py`
- `tests/test_workspace_api.py`
- `tests/test_http_api.py`

#### Task 4

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

#### Task 5

已完成 scope lock 与 regression 收口：

1. 锁 `/api/knowledge` 不退化成证据堆
2. 锁 `/api/knowledge/graph-main` 不把 evidence 当主图节点
3. handoff 文档刷新

#### Task 6

已完成最小关系生成与 FocusCluster 稳定化：

1. 生成：
   - `abstracts`
   - `causes_mistake`
2. `FocusCluster` 从 assessment 粒度收成热点粒度
3. cluster id 基于 `project + stage + hotspot slug` 稳定生成
4. 重复 assessment 会复用已有 cluster，而不是每次新建

关键文件：

- `review_gate/profile_space_service.py`
- `tests/test_profile_space_service.py`

#### 阶段 27

已完成主图最小关系可视化闭环：

1. 主图页能看见：
   - `Center node`
   - `Related nodes`
   - `Connections`
2. 关系以最小文本化方式显式出现
3. 暂不进入复杂拓扑布局

关键文件：

- `frontend/src/pages/KnowledgeGraphPage.tsx`
- `frontend/src/read-pages.test.tsx`

#### 阶段 28

已完成 `FocusCluster` 与 summary explanation 可读性收口：

1. 焦点簇按稳定 reason priority 排序
2. `Why it matters` 区块已经成立
3. explanation 仍走静态信号，不走实时 LLM

关键文件：

- `review_gate/workspace_api.py`
- `frontend/src/pages/KnowledgeMapPage.tsx`
- `tests/test_workspace_api.py`
- `frontend/src/read-pages.test.tsx`

## 5. 当前知识地图 V1 的真实边界

当前已经成立的是：

1. 知识地图入口先走摘要页，再进主图页
2. 后端有独立 summary/main-view DTO
3. assessment 已能投影成 durable knowledge objects
4. assessment 已开始产出最小关系：
   - `abstracts`
   - `causes_mistake`
5. `FocusCluster` 已经进入最小应用流，并具备基础稳定化
6. 主图页已经能看见关系，而不只是节点卡片
7. 摘要页已经能解释“为什么它现在重要”

当前仍然属于过渡态的部分：

1. `KnowledgeRelation` 目前只生成极小集合，还没有更丰富的结构关系
2. `FocusCluster` 仍然只是用户侧最小对象，不是全局候选簇系统
3. `KnowledgeGraphPage` 仍是片区式表达，不是真正拓扑布局
4. `focus_reason_summary` 目前是静态 signal 驱动，不是预生成解释缓存
5. 旧的 `ProfileSpace` legacy 读面仍保留，未整体切到新对象读面

## 6. 当前明确不做的内容

知识地图 V1 当前明确不做：

1. 全局候选焦点簇系统
2. 复杂图编辑
3. 节点批量治理
4. 大规模自动合并
5. 复杂图布局算法优化
6. 高级筛选器系统
7. 多用户知识图共享
8. proposal center 的完整治理后台化
9. 全量证据节点默认进入主图
10. 实时 LLM 驱动的页面解释主链

## 7. 当前最重要的边界

后续接手时最容易混掉的是：

1. `ReviewFlowService`
   - 负责题流事实
2. `ProfileSpaceService`
   - 负责长期知识资产
3. `ProposalCenterService`
   - 负责 proposal / action / execution
4. `WorkspaceSession`
   - 只负责“我上次停在哪”
5. `KnowledgeNode`
   - 负责稳定知识本体
6. `UserNodeState`
   - 负责当前用户与节点的关系状态
7. `FocusCluster`
   - 负责视图级知识片区组织对象

不要把：

- 用户状态塞进节点本体
- 证据锚点塞进默认主图
- 焦点簇写成临时页面算法结果

## 8. 当前已冻结的 agent / LLM 接入原则

当前已经明确：

1. 现在不因为阶段推进而提前接入真实 agent / LLM
2. 也不因为“未来可能要接”而把当前实现过度框架化
3. 当前执行原则是：
   - `硬定事实，不硬定策略`
   - deterministic default strategy 先落地
   - 高语义推断点保留清晰接缝

后续如果出现这些情况，可以显式建议接入 agent / LLM：

1. 关系推断明显超过规则边界
2. FocusCluster 聚合评分开始依赖高语义判断
3. 去重 / 重命名 / 升降层建议开始出现高价值
4. 解释生成的规则链明显变脆

当前 API 已备好，所以到点时可以直接显式提出，不需要死守 deterministic。

## 9. 最近验证结果

最新确认通过的关键回归：

1. `python -m pytest tests/test_profile_space_service.py -q` -> `11 passed`
2. `python -m pytest tests/test_workspace_api.py tests/test_http_api.py -q` -> `36 passed`
3. `python -m pytest -q` -> `100 passed`
4. `npm --prefix frontend test -- src/read-pages.test.tsx` -> `15 passed`
5. `npm --prefix frontend test` -> `34 passed`
6. `npm --prefix frontend run build` -> `passed`

另有真实试跑产物：

- `artifacts/workbench-live-trial/20260408-153730/summary.md`
- `artifacts/workbench-live-trial/20260408-154900/summary.md`

## 10. 当前已知非阻塞项

1. React Router v7 future flag warning
2. `App.test.tsx` 里仍有一个 `act(...)` warning
3. `review_gate/domain.py` 里的 `datetime.utcnow()` 有 Python 3.14 deprecation warning

这些当前都不是主线阻塞项，不要优先扩修。

## 11. 当前阶段与下一步建议

当前已经完成并冻结：

- `阶段 28 / FocusCluster 与 summary explanation 可读性收口`

当前最合理的下一步不是继续发散，而是先做一次阶段判断：

1. 回到文档与 checkpoint 收口
2. 或继续知识地图主线，进入更高价值的下一步

如果继续知识地图主线，当前更合理的下一步优先级是：

1. 继续增强主图表达，但保持轻量
2. 或设计 explanation 预生成缓存方案
3. 不要直接跳复杂图交互、复杂治理、实时 LLM

## 12. 新对话启动 Prompt

如果需要在新对话中继续，建议先让新对话阅读：

1. `docs/superpowers/handoffs/2026-04-08-current-state-handoff.md`
2. `docs/superpowers/plans/2026-04-08-knowledge-map-core-model.md`
3. `docs/superpowers/plans/2026-04-08-knowledge-map-v1-implementation.md`

然后再给它这个起始提示：

```text
请先阅读：
1. docs/superpowers/handoffs/2026-04-08-current-state-handoff.md
2. docs/superpowers/plans/2026-04-08-knowledge-map-core-model.md
3. docs/superpowers/plans/2026-04-08-knowledge-map-v1-implementation.md

当前项目是 impl-phase-coach。当前主线仍然是“稳定性优先”，但知识地图 V1 已经完成 Task 1-6，以及阶段 27、28 的最小收口。请不要跨阶段扩写，先判断当前处于哪个阶段，再输出：
- 当前阶段目标
- 当前阶段产物
- 当前阶段退出条件
然后只继续当前最小闭环。
```
