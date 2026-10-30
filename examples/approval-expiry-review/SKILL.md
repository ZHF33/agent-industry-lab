---
name: approval-expiry-review
description: Triage synthetic stale access approvals without granting access or renewing approval.
---

按sample.json四字段提交。仅用request_id调用lookup_request、lookup_approval、assess_approval，三个工具均成功再引用source解释。核申请/修订/动作/资源、审核者、有效期、撤销与消费标记；as_of等于expires_at即过期。可同时列多个阻断理由。

无阻断只表示快照条件满足，不认证身份、不授权执行。最多四轮，每轮三工具；本次人工approve只接受分诊建议，不能把旧批准续期或恢复外部任务。禁授予访问、发消息、修改申请、消费令牌或调用业务系统。
