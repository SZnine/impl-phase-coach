# impl-phase-coach 当前状态接手文档

用途：给后续对话或下一阶段实现快速接手当前工作，不依赖完整历史对话。

## 1. 当前基线

- 仓库路径：`D:\Desktop\impl-phase-coach`
- 当前分支：`main`
- 最近已提交基线：`157e738 feat: add lightweight graph focus interactions`
- 当前工作区：在 `157e738` 之上继续推进了 `阶段 59 / 一键式本地演示入口最小实现`，尚未提交
- 当前更活跃的主线：`知识地图 V1`

## 2. 当前主线结论

当前已经不是“有没有知识地图页”的问题，而是“知识地图是否已经成为真实可走通、可演示、可验证的工作台入口”的问题。

当前已冻结的核心判断：
1. 这是一个以知识地图为核心索引层的个人工作台，不是附属图页。
2. 节点本体与用户状态分离：
   - `KnowledgeNode`
   - `UserNodeState`
3. 证据锚点默认不进主图，而作为附属证据层按需展开。
4. 知识地图入口是：
   - `/knowledge` 摘要页
   - `/knowledge/graph` 主图页
5. explanation 链已拆成：
   - `FocusExplanation` cache 宿主
   - 可替换 `generator`
   - 页面只读 cache，不读实时 LLM
6. `support_signals` 当前属于 `ReviewFlowService` 内部稳定 assessment schema，不是外部正式 client 契约。

## 3. 已完成能力

### 核心对象与宿主

已完成：
1. `KnowledgeNode`
2. `EvidenceRef`
3. `UserNodeState`
4. `KnowledgeRelation`
5. `FocusCluster`
6. `FocusExplanation`

关键文件：
- `review_gate/domain.py`
- `review_gate/storage_sqlite.py`

### assessment -> durable projection

已完成：
1. `assessment -> KnowledgeNode / EvidenceRef / UserNodeState`
2. 最小关系：
   - `abstracts`
   - `causes_mistake`
   - 高置信 `supports`
3. `FocusCluster` 最小稳定化
4. `FocusExplanation` cache-first 读取链

关键文件：
- `review_gate/review_flow_service.py`
- `review_gate/profile_space_service.py`
- `review_gate/workspace_api.py`
- `review_gate/http_api.py`

### 前后端读面

已完成：
1. `GET /api/knowledge`
2. `GET /api/knowledge/graph-main`
3. `/knowledge` 摘要页
4. `/knowledge/graph` 主图页
5. 主图轻增强：
   - 中心节点强化
   - 关系分组
   - 图例与计数
6. 主图轻交互增强：
   - 关系类型筛选
   - 节点/关系互相高亮

关键文件：
- `frontend/src/pages/KnowledgeMapPage.tsx`
- `frontend/src/pages/KnowledgeGraphPage.tsx`
- `frontend/src/components/KnowledgeNodeCard.tsx`

### 阶段 59：一键式本地演示入口

已完成：
1. `http_api` 支持 demo 路径环境变量覆写：
   - `REVIEW_WORKBENCH_DB_PATH`
   - `REVIEW_WORKBENCH_SESSION_PATH`
2. `scripts/seed_demo_data.py`
   - 创建独立 demo sqlite
   - 创建独立 demo session
   - 走真实 `submit_answer_action` 主链种数据
   - 额外补一个 `supports` showcase cluster，方便真实外显当前进度
3. `scripts/start-demo.ps1`
   - 先 seed demo 数据
   - 再启动后端
   - 再启动前端
4. 顺手修复了现有读面缺口：
   - `WorkspaceAPI.get_knowledge_graph_main_view(...)` 在显式传 `cluster_id` 时 `selected_cluster` 未初始化

关键文件：
- `review_gate/http_api.py`
- `review_gate/workspace_api.py`
- `scripts/seed_demo_data.py`
- `scripts/start-demo.ps1`
- `tests/test_http_api.py`
- `tests/test_demo_seed.py`

## 4. 当前仍属过渡态的部分

这些现在可用，但还不是长期目标实现：
1. `KnowledgeGraphPage` 仍然是片区式关系表达，不是真正拓扑布局。
2. explanation 仍由 deterministic generator 生成，不是异步预生成 LLM explanation。
3. `supports` 当前仍以高置信 deterministic 规则为主，不做自由文本推断。
4. `support_signals` 虽然已经进入真实主链，但当前仍只冻结为服务内 schema，不对外承诺。
5. demo 能力目前是“一键脚本 + demo seed + 独立 DB”，不是完整 demo mode。

## 5. 当前最重要的边界

后续最容易混的是下面几组：
1. `KnowledgeNode` vs `UserNodeState`
   - 前者是知识本体
   - 后者是当前用户与该节点的关系状态
2. `FocusCluster` vs `FocusExplanation`
   - 前者回答“当前哪个片区值得看”
   - 后者回答“为什么它现在重要”
3. explanation cache vs explanation generator
   - 前者是结果宿主
   - 后者是策略实现
4. 内部 assessment schema vs 外部 assessment client 契约
   - 当前 `dimension_hits / support_basis_tags / support_signals` 只属于前者
5. demo 入口层 vs 业务主链
   - demo 脚本和 demo seed 只是运行辅助层
   - 不应该反向污染知识地图业务真相

## 6. agent / LLM 接入原则

当前冻结原则：
1. 当前先用 deterministic default strategy 落地。
2. 高语义推断点要集中成可替换策略接缝。
3. 不因为当前阶段，就把未来需要灵活替换的策略硬写死。
4. 也不因为未来可能接模型，就把当前实现过度复杂化。

一句话原则：

`硬定事实，不硬定策略。`

## 7. assessment support schema 当前约束

当前已内部稳定的字段：
1. `dimension_hits`
2. `support_basis_tags`
3. `support_signals`

当前工程约束：
1. 服务内：稳定
2. 对外 client：未冻结

当前再判断后的结论仍然是：
1. 现在不建议把这三类字段升级成正式 assessment client 契约。
2. 只有至少满足下面 `2/3`，才值得重新评估外放：
   - 连续两轮以上没有再改字段形状
   - `basis_type / basis_key` 不再摇摆
   - 至少一个真实外部调用方需要直接消费

## 8. 最近验证结果

和阶段 59 直接相关的最近验证：

1. `python -m pytest tests/test_http_api.py::test_create_default_workspace_api_uses_environment_demo_paths tests/test_demo_seed.py -q` -> `2 passed`
2. `python -m pytest tests/test_http_api.py tests/test_demo_seed.py tests/test_workspace_api.py -q` -> `42 passed`

当前已知非阻塞项：
1. `datetime.utcnow()` deprecation warning
2. React Router v7 future flag warning
3. `App.test.tsx` 里的 `act(...)` warning
4. pytest 结束时偶发 Windows 临时目录清理 `PermissionError`，但测试本身通过

## 9. 当前下一步建议

当前最合理的下一步不是继续扩新功能，而是先把 demo 入口这一轮收口：
1. 同步实施计划与 handoff
2. 做一次 git checkpoint

如果继续功能推进，再优先判断：
1. 主图是否还值得再做一小步轻交互增强
2. 或 assessment support 字段是否已经满足外放门槛

## 10. 新对话启动 prompt

当前基线：
- 最近已提交基线：`157e738 feat: add lightweight graph focus interactions`
- 当前工作区：包含 `阶段 59 / 一键式本地演示入口最小实现` 的未提交改动

请按 impl-phase-coach 方式继续：
1. 先判断当前阶段
2. 先给出当前阶段目标 / 产物 / 退出条件
3. 不跨阶段
4. 默认提供：
   - A. 我自己补充
   - B. 你直接补充

当前最相关的边界：
- `KnowledgeNode` vs `UserNodeState`
- `FocusCluster` vs `FocusExplanation`
- explanation cache vs explanation generator
- 内部 assessment schema vs 外部 assessment client 契约
- demo 运行层 vs 知识地图业务主链
