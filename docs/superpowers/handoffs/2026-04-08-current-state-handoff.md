# impl-phase-coach 当前状态接手文档

用途：给后续对话或后续阶段快速接手当前工作，不依赖完整历史对话。

## 1. 当前基线

- 仓库路径：`D:\Desktop\impl-phase-coach`
- 当前分支：`main`
- 最近已提交基线：`a8f6702 feat: persist durable review facts`
- 当前主线：`稳定性优先`
- 当前工作区：存在未提交改动，这些改动主要是：
  1. 会话恢复合法性与分级回退
  2. ProfileSpace 信号门槛一致性收口
  3. handoff 文档更新

## 2. 当前主线

当前不是继续扩页面，也不是先做知识质量增强。
当前已经冻结的主线是：

1. 先把工作台做成“本地长期真能用”的产品
2. 先补稳定性、恢复和状态一致性
3. 再做知识质量和交互增强

当前主线顺序固定为：

1. 题流事实真实化
2. 会话恢复补全
3. 真实使用测试与稳定性收口
4. 之后才进入知识质量提升

## 3. 已完成能力

### 3.1 工作台骨架

这些页面已经存在并能工作：

1. 首页
2. 项目页
3. 阶段页
4. 题集页
5. 题目页
6. 错题集页
7. 知识索引页
8. 知识图页
9. 建议中心页

### 3.2 主答题链

这条链已经是真实链路：

1. `Home -> Project -> Stage -> QuestionSet -> Question`
2. `submit_answer -> assessment -> stage summary refresh`
3. `submit_answer -> AnswerFact / AssessmentFact / DecisionFact`

关键文件：

- `review_gate/review_flow_service.py`
- `review_gate/workspace_api.py`
- `review_gate/http_api.py`
- `review_gate/storage_sqlite.py`
- `frontend/src/pages/QuestionPage.tsx`
- `frontend/src/lib/api.ts`

### 3.3 长期集合链路

这些长期集合已经是真实页面，不再是占位壳：

1. 错题集页：`assessment -> ProfileSpace -> MistakesPage`
2. 知识索引页：`assessment -> ProfileSpace -> KnowledgeIndexPage`
3. 知识图页：`assessment -> ProfileSpace -> KnowledgeGraphPage`
4. 建议中心页：`ProposalCenter -> ProposalsPage`

### 3.4 建议中心最小动作闭环

当前最小动作闭环已成立：

1. `accept`
2. `reject`
3. `defer`

并且已经守住这条边界：

- `proposal status` 和 `execution status` 分开

### 3.5 默认真实持久化启动路径

默认启动已经不再走纯 testing service。

默认入口：

- `review_gate/http_api.py`

默认真实宿主：

1. `ReviewFlowService.with_store(store)`
2. `ProfileSpaceService.with_store(store)`
3. `ProposalCenterService.with_store(store)`
4. `JsonWorkspaceStateStore(...)`

默认本地运行数据路径：

1. SQLite：`.workbench/review-workbench.sqlite3`
2. Session：`.workbench/workspace-session.json`

## 4. 当前已完成的稳定性能力

当前已经补上的稳定性能力：

1. `stage mastery` 跨重开恢复
2. `WorkspaceSession` 默认路径级恢复
3. 长期集合数据跨重开恢复
4. `Answer / Assessment / Decision` durable facts 已落盘
5. 非法 session 恢复目标会被后端收正并分级回退
6. `ProfileSpace` 的 durable knowledge 信号门槛已统一

## 5. 当前仍是过渡态的部分

这些现在能跑，但还不能误判成最终写法：

1. `review_flow_service.py` 仍整体偏 deterministic shell
2. `QuestionSet` 更完整的事实状态还没有 fully durable
3. `WorkspaceSessionSync.tsx` 当前只恢复路径级定位
4. 草稿、复杂过滤器、pause 中间态还没有恢复
5. `ProfileSpaceService` 的知识提炼规则仍是轻量规则，不是知识质量优化版本
6. `ProposalCenterService` 仍是最小维护链，不是完整维护系统

## 6. 当前最重要的边界

后续接手时最容易混淆的是这 4 条边界：

1. `ReviewFlowService` 负责题流事实
2. `ProfileSpaceService` 负责长期知识资产
3. `ProposalCenterService` 负责 proposal / action / execution
4. `WorkspaceSession` 只负责“我上次停在哪”，不负责业务事实

如果后续实现把这 4 层混掉，系统会重新变胖。

## 7. 最近验证结果

最近已经验证通过：

1. `python -m pytest -q` -> `94 passed`
2. `npm --prefix frontend test` -> `31 passed`
3. `npm --prefix frontend run build` -> `passed`

另外，第二轮和第三轮真实场景试跑已经证明：

1. 正常恢复链成立
2. 非法恢复目标分级回退成立
3. `strong + 无 gaps` 不再产出 graph node 噪音

相关产物：

- `artifacts/workbench-live-trial/20260408-153730/summary.md`
- `artifacts/workbench-live-trial/20260408-154900/summary.md`

## 8. 当前已知非阻塞项

这两项当前不是主线阻塞，不要优先修：

1. React Router v7 future flag warning
2. `App.test.tsx` 里的 `act(...)` warning

## 9. 当前明确不做

下一轮不要先做这些：

1. 知识质量增强
2. 知识图高级交互
3. proposal 批量操作
4. 多用户
5. 云同步
6. 视觉重做

## 10. 下一步建议

如果继续当前主线，最合理的下一步不是扩页面，而是继续稳定性收口。

建议优先级：

1. 继续补 `QuestionSet` 更完整 durable facts
2. 再补 session 的更细恢复边界
3. 再做人测和稳定性整理

## 11. 最应该先读的文件

如果后续对话或后续阶段要快速接手，优先按这个顺序读：

1. `docs/superpowers/handoffs/2026-04-08-current-state-handoff.md`
2. `docs/superpowers/plans/2026-04-08-review-flow-durable-facts.md`
3. `review_gate/http_api.py`
4. `review_gate/workspace_api.py`
5. `review_gate/review_flow_service.py`
6. `review_gate/storage_sqlite.py`
7. `frontend/src/components/WorkspaceSessionSync.tsx`
8. `frontend/src/lib/api.ts`

如果需要看测试锚点，再读：

1. `tests/test_http_api.py`
2. `tests/test_workspace_api.py`
3. `tests/test_profile_space_service.py`
4. `tests/test_proposal_center_service.py`
5. `frontend/src/components/WorkspaceSessionSync.test.tsx`
6. `frontend/src/lib/api.test.ts`

## 12. 新对话启动 prompt

```text
你当前接手的是 D:\Desktop\impl-phase-coach 仓库，继续沿用 impl-phase-coach 的阶段化协作方式。

先不要重做高层战略讨论，也不要扩散需求。
先读：
1. docs/superpowers/handoffs/2026-04-08-current-state-handoff.md
2. docs/superpowers/plans/2026-04-08-review-flow-durable-facts.md
3. review_gate/http_api.py
4. review_gate/workspace_api.py
5. review_gate/review_flow_service.py
6. review_gate/storage_sqlite.py
7. frontend/src/components/WorkspaceSessionSync.tsx
8. frontend/src/lib/api.ts

当前冻结主线是“稳定性优先”，不要跳去做知识质量增强或新页面扩展。

最重要的边界：
1. ReviewFlowService 管题流事实
2. ProfileSpaceService 管长期知识资产
3. ProposalCenterService 管 proposal/action/execution
4. WorkspaceSession 只管工作位置恢复

先给出：
- 当前阶段目标
- 当前阶段产物
- 当前阶段退出条件

然后沿“稳定性优先”主线继续推进，不要跨阶段。
```