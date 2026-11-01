---
name: cold-chain-excursion-review
description: Review synthetic industrial shipment temperature anomalies with unit normalization and explicit unknown intervals.
---

使用sample.json四字段提交，保留整秒带时区as_of。只用当前shipment_id调用lookup_shipment、lookup_readings、assess_excursion，读取三项成功结果再写带精确source的中文报告。

先统一C/F单位，再按合成阈值核采样点；短间隔是左端读数保持估算，长间隔全部未知，不能解释为真实连续暴露。区分异常点、估算时长和未知时长，列出设备/原始记录/产品流程政策需要人工核对的内容。

最多四轮，每轮三工具；参数错误根据返回信息有限修正。禁止访问外部资料、发消息、放行货物、改运单、控制设备或声称产品安全。人工approve仅接受分析，不执行业务动作。无异常也不能生成放行授权。
