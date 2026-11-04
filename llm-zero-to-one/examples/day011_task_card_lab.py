"""Validate task-card structure, not business truth; no model or executor."""
FIELDS = ("user", "decision", "inputs", "outputs", "constraints", "acceptance")


def validate_task(card):
    if not isinstance(card, dict): raise ValueError("Task card must be an object")
    errors = []
    for field in FIELDS:
        value = card.get(field)
        valid = (isinstance(value, str) and bool(value.strip())) if field in {"user", "decision"} else (
            isinstance(value, list) and bool(value) and all(isinstance(x, str) and bool(x.strip()) for x in value))
        if not valid: errors.append(field)
    if set(card) - set(FIELDS): errors.append("unexpected_fields")
    return errors


COMPLETE = {
    "user": "合成工业材料收货人员",
    "decision": "哪些温度证据需要人工复核，缺哪些记录？",
    "inputs": ["SHIP-DEMO-01", "带单位和时间的读数", "合成流程阈值", "固定窗口"],
    "outputs": ["异常采样点", "保持值估算", "未知时长", "来源和待审建议"],
    "constraints": ["只读", "不放行货物", "阈值不代表真实产品标准"],
    "acceptance": ["50F转为10C", "样例未知600秒", "无单位拒绝", "不产生业务动作"]}

if __name__ == "__main__":
    print("vague:", validate_task({"user": "收货人员", "decision": "帮我优化冷链"}))
    print("complete:", validate_task(COMPLETE))
    print("bad_list:", validate_task({**COMPLETE, "inputs": "任意资料"}))
