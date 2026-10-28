---
name: revision-conflict-review
description: Review stale work-order change proposals against synthetic revision evidence.
---

输入sample.json四字段。仅按change_id使用lookup_change、lookup_record、assess_revision，三个工具均成功再总结并引用source。检查对象、观察时间、base_revision与revision，以及工单状态和允许的priority字段。

冲突须重读并重新审查，不静默合并、不替换提案基准。版本相同也仅快照匹配，不授权未来写入。最多四轮、每轮三工具，错误在预算内修正；具名approve/reject只接受建议。禁止修改工单/版本、派单、发消息或创建数据库。
