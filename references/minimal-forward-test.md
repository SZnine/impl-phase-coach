# Minimal Forward Test

这个文件给 `impl-phase-coach` 提供第一版最小人工试跑方案。目标不是自动化验证，而是让另一个 Codex 或人工评审能低成本判断：这个 skill 是否已经具备可试跑的稳定性。

## Test Goal

确认这个 skill 在第一次真实使用时，至少能够做到：

1. 先识别当前实现阶段。
2. 先输出阶段目标、产物和退出条件。
3. 默认保持当前阶段最小闭环，不直接跨阶段展开。
4. 在进入代码阶段时给出 A/B 两种推进选项。
5. 不退化成普通助理口吻或高层泛化分析。

## Recommended First Prompt

推荐第一条试跑请求：

“用 $impl-phase-coach 带我按阶段实现一个小功能。先判断我当前处于哪个实现阶段，给出当前阶段目标、产物和退出条件，只给关键位置示例代码，不要一次性写完整实现。”

如果需要英文试跑：

“Use $impl-phase-coach to help me implement a small feature in phases. First identify my current implementation stage, define the stage goal, deliverables, and exit criteria, and only give key example code instead of a full implementation. Explain boundaries only when they are actually relevant.”

## Precondition Failure

如果首轮结果是：

- 系统明确说 `$impl-phase-coach` 当前环境里不存在
- 系统没有真正进入这个 skill，而是自动 fallback 到别的 skill 或普通回答

那么这次试跑应判为：`前置条件失败 / discovery failure`

这不属于 `impl-phase-coach` 的核心行为失败，原因是：

1. skill 根本没有被成功加载。
2. 后续回答不是这个 skill 的真实输出样本。
3. 因此前置条件失败不能拿来评估阶段识别、输出协议或 A/B 协议。

遇到这种情况时，先修 discovery 问题，再重新做同一条试跑请求。

## Pass Signals

下面这些信号说明试跑基本通过：

1. 回答一开始就明确说出当前阶段。
2. 回答明确包含阶段目标、阶段产物、退出条件。
3. 如果边界容易混淆，回答会明确说明当前最相关的边界点。
4. 回答没有提前展开后续阶段，也没有直接给整包实现。
5. 如果进入代码阶段，回答提供了 `A. 我自己补充` 和 `B. 你直接补充`。
6. 回答语气仍然是工程化、结构化、教练式，而不是泛泛建议。

## Fail Signals

下面这些信号说明试跑失败或明显跑偏：

1. 没有识别当前阶段就直接写代码。
2. 省略阶段目标、产物或退出条件。
3. 遇到明显边界混淆时，没有解释当前为什么先处理这一边。
4. 直接给完整实现，违背最小闭环。
5. 直接切回路线图、战略分析或泛化方法论讨论。
6. 在纠偏场景里先改代码风格，而不是先检查边界和状态语义。

注意：只有在 skill 已经被真正加载后，才使用这组失败信号。否则先判为 `前置条件失败`。

## Degraded But Recoverable

下面这些情况说明不是完全失败，但需要修正：

1. 当前阶段判断基本对，但解释依据太弱。
2. 输出结构大体对，但漏了知识权重或 A/B 选项。
3. 代码示例控制住了范围，但没有解释为什么放在这个文件里。
4. 首轮回答没有按最小骨架展开，导致结构不稳定。

遇到这些情况，优先补结构，不要推倒重来。

## Suggested Review Order

评审一次试跑结果时，按下面顺序看：

1. skill 是否真正被发现并加载。
2. 有没有先识别当前阶段。
3. 有没有把回答压缩在当前阶段最小闭环里。
4. 有没有按默认输出协议回答。
5. 有没有给出正确的 A/B 推进方式。
6. 风格有没有退化成普通助理或高层分析。

## Next Action Rule

如果第一次试跑通过：

- 可以继续做更具体的 forward-test，例如纠偏场景试跑、状态语义场景试跑。

如果第一次试跑失败：

- 先判断失败属于“前置条件失败”“阶段误判”“协议缺失”“风格退化”哪一类。
- 只修改导致失败的最小部分，不要顺手重写整个 skill。

如果你准备做真正独立的新会话试跑，读取 `references/independent-forward-test-playbook.md`。
