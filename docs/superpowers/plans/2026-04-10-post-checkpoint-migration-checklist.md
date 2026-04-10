# 2026-04-10 Post-Checkpoint Migration Checklist

## 1. 当前阶段定位

当前系统已经完成：

1. `Workflow -> Question -> Answer -> Evaluation -> Facts` 的第一迁移 checkpoint
2. SQLite 第一批 `11` 张表与最小 helper
3. `ReviewFlowService` 对 checkpoint 主链的最小接线
4. fresh-db 与 transport regression 锁定

当前系统还没有完成：

1. `Graph / Maintenance / Focus` 主链
2. 更稳定的应用层编排边界
3. `Assessment Facts` 向终态 canonical shape 的继续收敛

一句话：

`现在已经不是“架构预设阶段”，而是“checkpoint 已落地，准备继续拆过渡 orchestration 的阶段”。`

---

## 2. 当前接近长期稳定的部分

这些部分后面可以优先保留，不要轻易推翻。

### 2.1 Checkpoint record 分层

文件：

- `review_gate/checkpoint_models.py`

当前价值：

1. 已明确切出 `Workflow / Question / Answer / Evaluation / Assessment Facts` 五段记录
2. 已具备 `JsonSerializable` 契约与 round-trip 测试
3. 已经是后续 repository / service 继续分拆的稳定宿主

判断：

`接近长期稳定`

注意：

1. `AssessmentFact*` 仍偏 payload-heavy
2. 结构已可保留，字段表达还会继续收敛

### 2.2 First-checkpoint SQLite schema

文件：

- `review_gate/storage_sqlite.py`

当前价值：

1. 第一批 `11` 张表已经落地
2. 主链 FK 与关键索引已经具备
3. checkpoint records 和 SQLite row 之间的最小往返已成立

判断：

`当前阶段稳定，可作为下一阶段基线`

注意：

1. 当前仍是“单文件 store”
2. 后面该拆的是 repository 边界，不是先推翻表结构

### 2.3 Minimal synthesizer host

文件：

- `review_gate/assessment_synthesizer.py`

当前价值：

1. 已经把 “Evaluation -> Facts” 从 `ReviewFlowService` 中切出独立宿主
2. 已证明该边界是可独立测试的

判断：

`模块位置正确，但能力仍是最小过渡版`

### 2.4 Regression baseline

文件：

- `tests/test_assessment_synthesizer.py`
- `tests/test_checkpoint_storage.py`
- `tests/test_review_flow_service.py`
- `tests/test_http_api.py`

当前价值：

1. 已锁住 checkpoint 主链
2. 已锁住 fresh-db transport regression
3. 已锁住 repeated generation / mixed legacy event 这些高风险边界

判断：

`必须保留并继续扩展`

---

## 3. 当前明确属于过渡写法的部分

这些部分不是“错”，但不应继续做厚。

### 3.1 `ReviewFlowService` 仍是过渡 orchestration owner

文件：

- `review_gate/review_flow_service.py`

当前承担：

1. 生成题集
2. submit answer
3. generated-chain reuse
4. fallback backfill
5. legacy fact 并写
6. 调用 `AssessmentSynthesizer`

问题：

1. 职责已经明显偏重
2. 每次继续迁移，都容易把新的桥接逻辑继续塞回这里
3. 它已经不是一个适合长期增长的边界

判断：

`必须继续迁出职责，不能再做厚`

### 3.2 Event-based generated-chain reuse mapping

文件：

- `review_gate/review_flow_service.py`
- `event_store` 相关读写

当前价值：

1. 在不改 DTO、不改 store schema 的前提下，解决了 generated chain reuse

问题：

1. 本质仍是过渡映射层
2. 它不应该长期挂在 `ReviewFlowService` 里

判断：

`当前可接受，但下一阶段要考虑迁到更独立的应用层/协调层`

### 3.3 Legacy fact dual-write

当前状态：

1. checkpoint chain 已写
2. `AnswerFact / AssessmentFact / DecisionFact` 仍并写

问题：

1. 这是迁移期兼容策略，不是终态
2. 如果继续长期保留，会让事实来源双轨混杂

判断：

`必须在后续阶段显式规划退出，而不是无限并存`

---

## 4. 下一阶段最该迁出的职责

### 4.1 从 `ReviewFlowService` 迁出的第一优先级

1. generated-chain reuse 解析
2. question generation checkpoint persistence 组装
3. submit answer checkpoint persistence 组装

原因：

1. 这些都是“应用层协调职责”
2. 不属于长期的 review flow 业务判断本身

### 4.2 第二优先级

1. legacy fact dual-write 的集中封装
2. `Evaluation -> Facts` 的更稳定 service 调用边界

原因：

1. 现在 dual-write 还散在 `ReviewFlowService`
2. 长期看应该把“旧链兼容”与“新链主路径”分开

### 4.3 暂时不该先动的

1. Graph projection
2. Maintenance
3. Focus / explanation / star map
4. transport DTO 外形

原因：

1. 当前最大风险不在图层
2. 现在继续向图层推进，会再次把主链边界冲掉

---

## 5. 下一阶段的推荐入口

我建议下一阶段先做：

`应用层协调边界拆分`

更具体一点，就是在不改 transport、不改 graph 的前提下，开始显式拉出：

1. `QuestionCheckpointWriter` 或等价应用服务
2. `AnswerCheckpointWriter` 或等价应用服务
3. `GeneratedChainResolver` 或等价协调组件

当前目标不是命名，而是职责拆分。

### 为什么这是最优入口

1. 当前主链已经跑通，最大风险不再是“没有链路”，而是“过渡 owner 过厚”
2. 继续补 Graph 不会让系统更稳
3. 先拆应用层协调，才有资格进入下一主阶段

---

## 6. 下一阶段明确不该做的事

1. 不继续往 `ReviewFlowService` 里加更多迁移桥
2. 不把 event-based reuse mapping 直接当终态
3. 不开始 Graph / Maintenance 实现
4. 不因为 checkpoint 已通过，就跳过过渡层整形

---

## 7. 冻结结论

当前第一迁移 checkpoint 之后的工程判断：

1. 已接近长期稳定：
   - checkpoint record 分层
   - first-checkpoint SQLite schema
   - minimal synthesizer host
   - regression baseline
2. 明确属于过渡写法：
   - `ReviewFlowService` 过厚 orchestration
   - event-based generated-chain reuse mapping
   - legacy fact dual-write
3. 下一阶段最优目标：
   - `先拆应用层协调边界，再继续主链迁移`

一句话：

`下一阶段不是继续补功能，而是把第一迁移 checkpoint 周围的过渡 orchestration 拆薄。`
