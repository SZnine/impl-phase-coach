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
