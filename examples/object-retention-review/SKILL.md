---
name: object-retention-review
description: Review synthetic object version and fixed retention evidence with human approval.
---

输入sample.json所列四字段。只使用该工单object_id调用lookup_object_versions、lookup_retention、assess_retention；三个均成功后引用source给出建议。

核对版本身份、观察时间、完整性、删除标记、保留截至日和legal_hold。信息缺失转人工，不能把“未记录限制”说成“可以删除”。以API提交并在review节点暂停，具名人工approve/reject只接受或拒绝建议。禁用存储连接、对象内容读取、删除、恢复、策略修改和通知。失败在四轮预算内修正，耗尽后报告失败。
