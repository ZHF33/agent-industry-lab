---
name: api-quota-review
description: Review synthetic API burst budgets using bounded tool calls and human approval.
---

输入sample.json四字段。严格按工单service_id调用lookup_traffic、lookup_limit、assess_budget，三个均成功再给建议，引用工具source。时效、对象、版本错配时只报告证据不足。理想投影假设无其他消费，不是实时准入或重试保证。demand超过capacity不能仅靠等待解决整个原子批次。

最多四轮、每轮三工具，有限修正错误；interrupt等待具名approve/reject。不得实际请求、退款、调整配额、等待重试、发业务消息。模型建议与确定性报告分开，人工检查拆批假设及业务幂等性。
