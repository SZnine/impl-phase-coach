# impl-phase-coach

个人 skill 开发项目：`impl-phase-coach`

当前项目由两部分组成：
1. 主 skill：负责实现期阶段化推进、阶段判断、A/B 推进协议、阶段复盘口径
2. `review_gate` 子模块：负责阶段内复盘验证、HTML 结果页、snapshot 落盘、知识沉淀与轻量维护

## 当前状态

- 主 skill 已形成可用第一版
- `review_gate` 已形成中文友好的第一版
- 两者的关系已经冻结为：
  - 主 skill 负责建议是否进入复盘
  - `review_gate` 负责真正执行复盘
  - 复盘属于当前主阶段内的验证子流程，不是新的主阶段

## 项目结构

```text
impl-phase-coach/
|- SKILL.md
|- AGENTS.md
|- agents/
|- references/
|- review_gate/
|- docs/
|  `- review-gate/
|- tests/
|- scripts/
`- artifacts/   # 运行时试跑产物，可随时重新生成
```

## 关键入口

### 主 skill 入口

- [SKILL.md](/d:/Desktop/impl-phase-coach/SKILL.md)

这里定义：
- 当前阶段判断
- 当前阶段目标 / 产物 / 退出条件
- A/B 推进协议
- 阶段结束复盘
- `review_gate` 的软接入规则

### 复盘子模块入口

- [workflow.py](/d:/Desktop/impl-phase-coach/review_gate/workflow.py)
- [usage.md](/d:/Desktop/impl-phase-coach/docs/review-gate/usage.md)
- [integration.md](/d:/Desktop/impl-phase-coach/docs/review-gate/integration.md)

这里定义：
- 如何运行一轮复盘
- 如何拿到 HTML 和 snapshot
- 如何把复盘结果接回主 skill 流程

### Workbench UI 入口

默认本地演示使用 deterministic/stub agent，适合不联网回归：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-demo.ps1
```

如需让工作台按钮真实调用本地配置的 Project Agent 和 Evaluator Agent：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-demo.ps1 -LiveAgents -Model gpt-5.4-mini
```

启动后打开：

```text
http://127.0.0.1:5173
```

在 Stage 页面点击 `Generate Project Agent question set`，会通过后端 `/api/actions/generate-question-set` 调用 Project Agent，生成的 checkpoint 会被 Question Set / Question Detail 读面直接读取；随后提交答案会进入 Evaluator Agent、Facts、Graph 链路。

`-LiveAgents` 不会打印 API key。它只会把 backend 进程环境变量指向仓库根目录，默认读取 `.env/api_key.md` 或 `key/api_key.md` 中的 OpenAI-compatible `Base URL` 与 `API Key`。

可分别覆盖模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-demo.ps1 -LiveAgents -ProjectModel gpt-5.4-mini -EvaluatorModel gpt-5.4-mini
```

### 当前答题闭环口径

Workbench 当前最小真实闭环已经收敛为：

1. Project Agent 生成题集后，题集页读取 durable question checkpoint。
2. 用户在 Question Detail 提交答案后，后端写入 answer / assessment / facts / graph，并把对应 question item 标记为 `answered`。
3. `submit_answer` 响应的 `refresh_targets` 必须包含 `question_set`，前端只在收到该目标时刷新题集读面。
4. Question Set 页面根据 question status 展示 `已完成 / 当前题 / 待完成`，并把入口推进到第一道未完成题。

这条链路是当前产品主线：高质量出题、答题、评析解析、知识沉淀。知识星图用于总览和后续推荐，不应抢在答题闭环之前继续局部优化。

## 推荐阅读顺序

1. [SKILL.md](/d:/Desktop/impl-phase-coach/SKILL.md)
2. [integration.md](/d:/Desktop/impl-phase-coach/docs/review-gate/integration.md)
3. [usage.md](/d:/Desktop/impl-phase-coach/docs/review-gate/usage.md)
4. `tests/` 与 `scripts/`

## 说明

- `references/` 主要是给 skill 运行时使用的材料
- `docs/` 主要是给人类阅读和维护使用的材料
- `artifacts/` 存放临时试跑产物，不属于主协议正文；清空后可重新生成
- `tests/` 覆盖 `review_gate` 的当前最小闭环

## 适合谁用

这个仓库目前更适合两类使用方式：

1. 作为个人 skill 源码仓库持续迭代
2. 作为本地已安装 skill 的真实来源目录进行调试与回归验证

## 维护建议

如果你是这个仓库的维护者，推荐按下面顺序使用：

1. 先改 [SKILL.md](/d:/Desktop/impl-phase-coach/SKILL.md) 或 [review_gate](/d:/Desktop/impl-phase-coach/review_gate)
2. 再跑 `tests/` 做最小回归
3. 如需生成真实验证材料，再运行 `scripts/` 里的试跑脚本

当前不建议把 `artifacts/` 当成长期资料库；它更像一次次可重生成的验证输出。
