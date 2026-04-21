# Live Graph Smoke 设计

> 本文定义一条 opt-in 的真实 LLM graph smoke。目标不是把 live provider 纳入默认测试，而是用用户本地配置的 evaluator provider 跑通一次真实 submit，并验证新 Graph Layer 能从真实评估输出进入 `graph-revision` 和 `graph-main`。

## 1. 当前定位

当前后端主链已经在 fake assessment 下闭环：

```text
submit-answer
  -> Evaluator assessment
  -> EvaluationBatch / EvaluationItem
  -> AssessmentFactBatch / AssessmentFactItem
  -> KnowledgeSignal
  -> GraphRevision / KnowledgeNode / KnowledgeRelation
  -> /api/knowledge/graph-revision
  -> /api/knowledge/graph-main
```

但还没有证明真实 LLM 输出能稳定穿过这条链路。下一步应补一条人工触发的 live smoke，而不是继续局部增强 graph DTO。

## 2. 目标

新增一条命令行入口，使用 `.env/api_key.md` 或 `key/api_key.md` 中的 evaluator provider 配置，执行：

1. 创建临时 SQLite workspace。
2. 使用 live `EvaluatorAgentAssessmentClient`。
3. 通过 HTTP API 提交一条固定答案。
4. 读取 `/api/knowledge/graph-revision`。
5. 读取 `/api/knowledge/graph-main`。
6. 输出可审查 artifact。

## 3. 非目标

本阶段不做：

1. 不把 live smoke 放进默认 `pytest`。
2. 不读取或打印 API key。
3. 不默认使用 Project Agent live 出题。
4. 不新增 graph schema。
5. 不要求每次 live smoke 都产生 relation。
6. 不把 live smoke 结果作为确定性质量门禁。

## 4. 命令入口

新增脚本：

```text
scripts/run_live_graph_smoke.py
```

建议参数：

```text
--root-dir
--model
--output-dir
--strict
```

默认：

1. `root-dir` 为仓库根目录。
2. `model` 为 `gpt-5.4-mini`。
3. `output-dir` 为 `artifacts/live-graph-smoke`。
4. `strict` 关闭；仅在结构缺失时返回非零。

## 5. 输入样例

提交的答案应刻意包含一个真实弱点，并给 evaluator 足够上下文让它可能产生 `support_basis_tags`：

```text
I can describe that the API boundary exists, but I did not define the request/response contract, persistence boundary, or malformed provider-output regression clearly.
```

该答案目标是触发：

1. `partial` 或 `weak` verdict。
2. 至少一个 `core_gaps`。
3. 至少一个 assessment fact。
4. 至少一个 graph node。
5. 如果 evaluator 输出 support basis，则产生 relation。

## 6. 输出 artifact

每次运行输出一个 JSON 文件和一个 Markdown 摘要：

```text
artifacts/live-graph-smoke/YYYYMMDD-HHMMSS.json
artifacts/live-graph-smoke/YYYYMMDD-HHMMSS.md
```

JSON 包含：

1. submit response。
2. graph revision response。
3. graph main response。
4. derived checks。
5. artifact db path。

Markdown 包含：

1. verdict / confidence。
2. graph node count。
3. relation count。
4. selected cluster summary。
5. issues list。

不得包含 API key、完整 provider request header、Authorization 或原始配置文件内容。

## 7. 检查规则

必过检查：

1. submit response `success == true`。
2. `graph_revision.has_active_revision == true`。
3. `graph_revision.revision.node_count >= 1`。
4. `graph_main.nodes` 非空。
5. `graph_main.selected_cluster != null`。

观察性检查，不作为默认失败：

1. `relation_count >= 1`。
2. graph-main relation preview 非空。
3. evaluator 输出 support basis。

如果 `--strict` 开启，则 relation 缺失也视为失败。

## 8. 测试边界

默认单元测试只验证脚本内部的纯函数：

1. issue classification。
2. report formatting。
3. artifact payload 不包含敏感字段。

不在默认测试中访问真实网络。

## 9. 成功标准

本阶段完成后，应满足：

1. 开发者可以显式运行 live graph smoke。
2. 默认 test suite 不依赖网络。
3. live smoke 能产出可审查 artifact。
4. live smoke 能证明真实 evaluator 输出至少可进入 graph node 和 selected cluster。
5. relation 是否产生被记录为质量信号，而不是硬编码假设。

