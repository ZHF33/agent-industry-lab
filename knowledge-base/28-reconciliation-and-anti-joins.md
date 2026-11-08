# 第二十八讲草稿　记录比计划多，为什么点检还会缺项？

面向刚开始做业务对账的读者。本课用一份合成点检表解释组合键、反连接和一对多计数。学完可以手算计划覆盖，保留冲突证据，并说清哪些异常需要人工复核。配套[设备点检记录对账 Agent](../examples/inspection-reconciliation-review/README.md)。

## 从签到表看缺项

培训有三名学员，收回四张签到单，其中一人签了两次，一张来自其他班。单看总数会觉得已经收齐。要确认覆盖，得逐个核名单。点检同样如此，一台泵可有多个点检项。类比的边界是生产记录还会有复测、状态修订和不同班次，需先确定核对口径。

**组合键**是用多个字段一起确定匹配对象。本例用设备 ID 与点检项 ID。只用 TEMP 会把不同泵的温度检查混在一起。记录 ID 则区分某一条观察。两条记录可能有相同组合键并保留不同记录 ID。

小问题：PUMP-B 的 TEMP 已收到，能填上 PUMP-A 的 TEMP 吗？不能，设备不同，组合键不同。

## 两张表分别回答什么

| 合成计划键 | 已收观察 |
| --- | --- |
| PUMP-A / SEAL | R1 pass，R2 fail |
| PUMP-A / TEMP | 空 |
| PUMP-B / TEMP | R3 pass |
| PUMP-C / TEMP 未列计划 | R4 pass |

把计划键集合记作 P，把至少有一条观察的键集合记作 O。集合只关心成员是否存在。P 与 O 的交集有两项。P 减 O 得到缺项 A/TEMP，O 减 P 得到计划外 C/TEMP。四条观察压成三种观察键，计划覆盖是 2/3。这里分母是计划键数。若计划为空，应报告数量，由业务口径决定是否定义比例。

**反连接**保留左边那些在右边找不到对应键的行。用计划作左边得到缺项，反过来得到计划外。该操作只证明所选数据中缺少匹配。复核人员仍要检查采集延迟、任务版本和现场记录。

## 匹配基数为什么要单独核

**基数**在这里表示一个键能匹配几条记录。A/SEAL 匹配两条，所以“匹配键数”仍只加一，“匹配记录数”则加二。若直接把计划连接观察后数行，A/SEAL 会被展开为两行。只统计行数会把复测当成额外的计划覆盖。

程序还区分多条与冲突。同一键两条 pass 表示多条，只有结果集合同时含 pass 和 fail 才报告冲突。保留 R1、R2 让人工回查。按记录 ID 排序只让输出稳定，不能用它推断哪个结果最新。

小问题：把 R2 改为 pass 会怎样？多条仍存在，冲突消失，计划覆盖仍是 2/3。这个单变量对照说明三种指标彼此独立。

## 读实现的关键步骤

以下片段依赖完整项目中的变量，不能独立运行。

```python
groups[key(row)].append({"record_id": record_id, "result": row["result"]})
```

输入是一条观察，key 生成设备与点检项二元组。groups 是按组合键保存记录列表的映射，append 保留每一条。后续发现冲突时可以原样列出相关编号。重复使用同一记录 ID 会被拒绝，防止同一身份指向歧义数据。

```python
actual = set(groups)
missing_pairs = expected - actual
```

actual 是观察键集合，expected 是计划键集合。差集保留左边独有的键。程序从小到大排序后生成报告，并用同一分组计算冲突和失败证据。

## SQL 对照

数据库常用 NOT EXISTS 表达同一思路。下列教学片段需要已有表、同一快照范围和非空键，本项目使用内存实现。

```sql
SELECT p.device_id, p.check_id
FROM checklist_items AS p
WHERE NOT EXISTS (
    SELECT 1 FROM observations AS o
    WHERE o.device_id = p.device_id AND o.check_id = p.check_id
);
```

子查询逐项找同设备同点检项。存在任何匹配就排除该计划项。实际接入须再限定计划 ID、版本和适用班次。若用 NOT IN 且右侧有 NULL，判断可能变成未知，因此应先明确空值约束和查询语义。选读 PostgreSQL 的 EXISTS 与 NOT IN 说明。 [官方文档](https://www.postgresql.org/docs/current/functions-subquery.html)

## 最小实验

准备 Python 3.11+ 和完整仓库，在 PowerShell 进入仓库根目录。使用[课堂例子](examples/inspection_reconciliation_lab.py)。

```powershell
python knowledge-base/examples/inspection_reconciliation_lab.py
```

静态推导的预期输出如下。

```text
planned: 3
records: 4
matched: 2
missing: [('PUMP-A', 'TEMP')]
unexpected: [('PUMP-C', 'TEMP')]
multiple: [('PUMP-A', 'SEAL')]
conflicts: [('PUMP-A', 'SEAL')]
```

找不到 agent 时先检查完整目录。Unique record ID required 指观察身份重用，应核上游，而非把所有重复结果静默删除。旧版本、过期证据会在 Agent 报告中单列。课堂函数只演示对账计算，审核流程还会检查版本、时间及模型取证范围。

## 取舍和练习

小快照用集合和分组就能核查，代码限制每表 100 条。大量记录可按计划与组合键建索引，并让对账查询在一致读取范围内完成。这个例子没有复测优先级、原始测量阈值或设备放行授权。真实接入要定义复测如何生效，并验证来源完整性。

1. 收到的记录总数等于计划数，可以判断收齐吗？还要检查各计划键有没有对应记录。
2. A/SEAL 同时 pass 与 fail，应该保留哪条？本例保留两条，交人工依据来源和复测规则判定。
3. 删除 R4，缺项会减少吗？只会消除计划外记录，A/TEMP 仍缺项。
4. 把键简化为 TEMP 会怎样？不同设备被错误合并，可能掩盖缺项。

当日交付为两份合成清单、两种方向的差集及一条多条但不冲突的反例。2026-11-07 核查 PostgreSQL 子查询和 Python 分组容器文档。例子和推演原创 MIT，静态检查已做，课堂运行待使用者验收。 [Python collections](https://docs.python.org/3/library/collections.html)
