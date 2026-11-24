---
name: pressure-hysteresis-review
description: Review synthetic compressed-air pressure hysteresis, missing-sample gaps and stale state.
---

先核对系统、kPa单位、明确的窗口初始状态及时间。严格按采集顺序复盘，低于触发阈值进入低压，达到恢复阈值才恢复，中间带保留记忆。超过最大采样间隔重置未知，禁止以旧正常状态填补缺测。设备工程师审核证据与处置需求，本工具不写设备、不压制实时告警、不签发安全结论。
