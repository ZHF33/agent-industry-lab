---
name: task-dependency-review
description: Review a synthetic production plan's prerequisites, cycle evidence and pending-task blockers.
---

提交sample.json四字段。工具仅接受当前plan_id。取得计划、任务和确定性审查结果后引用精确source。解释结构先后顺序、待处理任务、未完成前置、循环及状态矛盾。旧版本或旧快照需人工核对。

最多四轮，每轮三工具。遇到循环时本例保守地返回空候选列表，展示一条循环证据。人工意见仅确认报告，派工、改状态与设备操作属于外部业务流程。
