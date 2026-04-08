# impl-phase-coach Current State Handoff

> 用途：给新对话一个显式、可读、可操作的接手入口。  
> 当前仓库状态以本文件为主，不要求新对话先理解完整历史对话。

## 1. 当前仓库与基线

- 仓库路径：`D:\Desktop\impl-phase-coach`
- 当前分支：`main`
- 当前工作区状态：`clean`
- 最近提交：`01f50ae feat: build persistent review workbench mvp`
- 上一个基线提交：`e13cbe0 chore: establish initial impl-phase-coach baseline`

## 2. 当前所处主阶段

当前处于：`阶段 17 / 稳定性优先路线冻结后，等待下一轮实现`

这意味着：

1. 工作台 MVP 骨架已经完成，不再是 demo。
2. 长期集合已经有真实持久化默认启动路径。
3. 下一轮不该扩新页面，也不该先做知识质量增强。
4. 下一轮主线应该是：`稳定性优先`

## 3. 当前已经真实打通的链路

### 3.1 主答题链

已经真实成立：

1. 首页 -> 项目页 -> 阶段页 -> 题集页 -> 题目页
2. `submit_answer -> assessment -> stage summary refresh`

关键文件：

- [review_flow_service.py](/d:/Desktop/impl-phase-coach/review_gate/review_flow_service.py)
- [workspace_api.py](/d:/Desktop/impl-phase-coach/review_gate/workspace_api.py)
- [http_api.py](/d:/Desktop/impl-phase-coach/review_gate/http_api.py)
- [QuestionPage.tsx](/d:/Desktop/impl-phase-coach/frontend/src/pages/QuestionPage.tsx)
- [api.ts](/d:/Desktop/impl-phase-coach/frontend/src/lib/api.ts)

### 3.2 长期知识集合只读链

已经真实成立：

1. `assessment -> ProfileSpace -> MistakesPage`
2. `assessment -> ProfileSpace -> KnowledgeIndexPage`
3. `assessment -> ProfileSpace -> KnowledgeGraphPage`

关键文件：

- [profile_space_service.py](/d:/Desktop/impl-phase-coach/review_gate/profile_space_service.py)
- [MistakesPage.tsx](/d:/Desktop/impl-phase-coach/frontend/src/pages/MistakesPage.tsx)
- [KnowledgeIndexPage.tsx](/d:/Desktop/impl-phase-coach/frontend/src/pages/KnowledgeIndexPage.tsx)
- [KnowledgeGraphPage.tsx](/d:/Desktop/impl-phase-coach/frontend/src/pages/KnowledgeGraphPage.tsx)

### 3.3 ProposalCenter 最小动作链

已经真实成立：

1. `ProposalsPage` 读真实 proposal
2. `accept / reject / defer` 三个最小动作闭环
3. proposal 状态和 execution 结果分离

关键文件：

- [proposal_center_service.py](/d:/Desktop/impl-phase-coach/review_gate/proposal_center_service.py)
- [ProposalsPage.tsx](/d:/Desktop/impl-phase-coach/frontend/src/pages/ProposalsPage.tsx)
- [action_dtos.py](/d:/Desktop/impl-phase-coach/review_gate/action_dtos.py)
- [view_dtos.py](/d:/Desktop/impl-phase-coach/review_gate/view_dtos.py)

### 3.4 默认真实持久化启动路径

当前默认启动已经不再走纯 testing service。

默认入口：

- [http_api.py](/d:/Desktop/impl-phase-coach/review_gate/http_api.py)

默认真实宿主：

1. `ProfileSpaceService.with_store(store)`
2. `ProposalCenterService.with_store(store)`
3. `ReviewFlowService.with_store(store)`
4. `JsonWorkspaceStateStore(...)`

默认本地数据路径：

1. SQLite：`.workbench/review-workbench.sqlite3`
2. Session：`.workbench/workspace-session.json`

## 4. 当前已经补上的稳定性能力

### 4.1 已补上

1. `stage mastery` 跨重开恢复
2. `WorkspaceSession` 的默认路由位置恢复
3. 关闭再打开后，长期集合数据能回来

关键文件：

- [review_flow_service.py](/d:/Desktop/impl-phase-coach/review_gate/review_flow_service.py)
- [workspace_state_store.py](/d:/Desktop/impl-phase-coach/review_gate/workspace_state_store.py)
- [WorkspaceSessionSync.tsx](/d:/Desktop/impl-phase-coach/frontend/src/components/WorkspaceSessionSync.tsx)

### 4.2 当前还没有补全的部分

这些是“下一轮稳定性主线”要继续补的，不要误判成已经完成：

1. `Answer / Assessment / Decision` 题流事实的完整真实宿主
2. `QuestionSet` 的真实题流状态恢复
3. 更细粒度的 session 恢复：
   - 过滤器
   - 草稿
   - pause 状态
4. 更完整的真实使用失败回放

## 5. 当前哪些写法还是过渡态

### 5.1 仍然是过渡写法

1. [review_flow_service.py](/d:/Desktop/impl-phase-coach/review_gate/review_flow_service.py)
   - 仍然整体偏 deterministic shell
   - 当前真实化的重点是 `mastery_status`
   - 还没有把完整 `Answer / Assessment / Decision` 都做成 durable facts

2. [profile_space_service.py](/d:/Desktop/impl-phase-coach/review_gate/profile_space_service.py)
   - 已经支持 `with_store(...)`
   - 但知识提炼规则仍是轻量规则，不是最终质量版

3. [proposal_center_service.py](/d:/Desktop/impl-phase-coach/review_gate/proposal_center_service.py)
   - 已经支持 `with_store(...)`
   - 但 proposal 生成策略、批量动作和复杂执行流都没做

4. [WorkspaceSessionSync.tsx](/d:/Desktop/impl-phase-coach/frontend/src/components/WorkspaceSessionSync.tsx)
   - 当前只恢复“路径级定位”
   - 没有恢复草稿、复杂过滤器、临时 UI 状态

### 5.2 已经接近长期稳定写法

1. `workspace_api -> http_api -> api.ts -> pages` 这条门面链
2. DTO 边界：
   - `action_dtos.py`
   - `view_dtos.py`
3. 长期集合本体页和阶段摘要切片分离：
   - 阶段页只看摘要
   - 错题 / 索引 / 图 / proposal 页看本体

## 6. 当前已经验证过的测试结果

最后一次已知稳定验证结果：

1. `python -m pytest -q` -> `89 passed`
2. `npm --prefix frontend test` -> `31 passed`
3. `npm --prefix frontend run build` -> `passed`

说明：

1. 这些结果来自稳定性主线收口后的验证。
2. 如果新对话开始接手前担心代码漂移，可以先重跑这 3 条命令。

## 7. 当前已知的非阻塞项

这两个问题当前不是阻塞项，不要在新对话一开始就优先修它们：

1. React Router v7 future flag warning
2. [App.test.tsx](/d:/Desktop/impl-phase-coach/frontend/src/App.test.tsx) 相关的 `act(...)` warning

原因：

1. 它们不影响当前真实链路验收。
2. 当前主线优先级是稳定性，不是测试控制台洁癖。

## 8. 已冻结的下一轮路线

新对话不要重新做高层战略讨论，直接沿这条路线推进：

### 主线：稳定性优先

顺序固定为：

1. `迭代 1：题流事实真实化`
2. `迭代 2：会话恢复补全`
3. `迭代 3：真实使用测试与稳定性收口`

明确先不做：

1. 知识质量提升
2. 知识图高级交互
3. proposal 批量操作
4. 多用户
5. 云同步
6. 视觉重做

## 9. 新对话最应该先读的文件

如果新对话需要快速接手，不要全仓乱读，优先按这个顺序开：

1. [docs/superpowers/handoffs/2026-04-08-current-state-handoff.md](/d:/Desktop/impl-phase-coach/docs/superpowers/handoffs/2026-04-08-current-state-handoff.md)
2. [review_gate/http_api.py](/d:/Desktop/impl-phase-coach/review_gate/http_api.py)
3. [review_gate/workspace_api.py](/d:/Desktop/impl-phase-coach/review_gate/workspace_api.py)
4. [review_gate/review_flow_service.py](/d:/Desktop/impl-phase-coach/review_gate/review_flow_service.py)
5. [review_gate/profile_space_service.py](/d:/Desktop/impl-phase-coach/review_gate/profile_space_service.py)
6. [review_gate/proposal_center_service.py](/d:/Desktop/impl-phase-coach/review_gate/proposal_center_service.py)
7. [frontend/src/components/WorkspaceSessionSync.tsx](/d:/Desktop/impl-phase-coach/frontend/src/components/WorkspaceSessionSync.tsx)
8. [frontend/src/lib/api.ts](/d:/Desktop/impl-phase-coach/frontend/src/lib/api.ts)

如果要看测试锚点，再读：

1. [tests/test_http_api.py](/d:/Desktop/impl-phase-coach/tests/test_http_api.py)
2. [tests/test_workspace_api.py](/d:/Desktop/impl-phase-coach/tests/test_workspace_api.py)
3. [tests/test_profile_space_service.py](/d:/Desktop/impl-phase-coach/tests/test_profile_space_service.py)
4. [tests/test_proposal_center_service.py](/d:/Desktop/impl-phase-coach/tests/test_proposal_center_service.py)
5. [frontend/src/components/WorkspaceSessionSync.test.tsx](/d:/Desktop/impl-phase-coach/frontend/src/components/WorkspaceSessionSync.test.tsx)
6. [frontend/src/lib/api.test.ts](/d:/Desktop/impl-phase-coach/frontend/src/lib/api.test.ts)

## 10. 新对话的启动 prompt

下面这段可以直接贴到新对话里：

```text
你当前接手的是 D:\Desktop\impl-phase-coach 仓库，继续沿用 impl-phase-coach 的阶段化协作方式。

先不要重做高层讨论，也不要重新发散需求。

先读取：
1. docs/superpowers/handoffs/2026-04-08-current-state-handoff.md
2. review_gate/http_api.py
3. review_gate/workspace_api.py
4. review_gate/review_flow_service.py
5. frontend/src/components/WorkspaceSessionSync.tsx
6. frontend/src/lib/api.ts

当前已冻结主线是“稳定性优先”，不要跳去做知识质量增强或新页面扩展。

当前最重要的边界：
1. ReviewFlowService 管题流事实
2. ProfileSpaceService 管长期知识资产
3. ProposalCenterService 管 proposal/action/execution
4. WorkspaceSession 只管工作位置恢复

先给出：
- 当前阶段目标
- 当前阶段产物
- 当前阶段退出条件

然后沿“稳定性优先”主线推进，不要跨阶段。
```

## 11. 如果新对话要继续实现，建议从哪里开始

推荐起点：

1. 先用当前 handoff 文档确认主线没有漂
2. 再写新的稳定性计划文档
3. 然后进入：
   - `迭代 1 / 题流事实真实化`

不建议起点：

1. 直接重构知识图
2. 直接优化知识提炼质量
3. 直接扩 proposal 批量动作
4. 直接重做首页视觉

