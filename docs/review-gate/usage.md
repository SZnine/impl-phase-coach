# Review Gate Usage

## 作用

`review_gate` 提供一个面向项目的一次性复盘入口：
`run_review_workflow()`。

适用场景：
- 启动一轮阶段内复盘
- 评估用户当前回答
- 生成教练式复盘报告
- 抽取知识沉淀条目
- 渲染 HTML 结果页
- 可选写出本地 snapshot JSON

## 最小调用示例

```python
from pathlib import Path

from review_gate import ReviewMode, ReviewRequest, run_review_workflow

request = ReviewRequest(
    stage_id="stage-10",
    stage_summary="接入项目级统一复盘入口",
    candidate_answer="需要复盘",
    mode=ReviewMode.DEEP,
    trigger_reason="project_entrypoint",
)

result = run_review_workflow(
    request=request,
    answer="当前回答内容",
    snapshot_target=Path("artifacts/review-output.json"),
)
```

## 返回产物

`run_review_workflow()` 返回 `ReviewWorkflowResult`，包含：
- `session`：当前复盘 session
- `report`：结构化复盘报告
- `knowledge_entries`：知识沉淀条目
- `html`：人类可读 HTML 结果字符串
- `snapshot`：本地 JSON-ready 结构
- `snapshot_target`：如果传入了落盘路径，则返回该路径

## 如何查看 HTML

当前版本直接返回 `result.html`。

推荐临时使用方式：
1. 把 `result.html` 写到本地文件
2. 在浏览器里打开
3. 通过“展开完整复盘 / 收起完整复盘”查看完整报告

## 如何查看 Snapshot

如果传入 `snapshot_target`，JSON 会自动写出。

当前 snapshot 包含：
- `human_summary`
- `session`
- `report`
- `knowledge_entries`

推荐阅读顺序：
1. `human_summary`
2. `session.pass_state` 与 `session.learning_recommendations`
3. `knowledge_entries`
4. `report.expanded_report`

## 当前范围

这个入口目前刻意保持最小：
- 只覆盖单轮复盘
- 不提供多轮连续拷打状态机
- 不提供长期存储后端
- 不自动写 HTML 文件
- 不调度知识库维护任务

这些都属于后续阶段工作。
