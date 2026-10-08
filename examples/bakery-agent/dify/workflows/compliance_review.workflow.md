# Compliance Review Workflow

## 节点名称
Start -> Compliance Reviewer -> Answer

## 输入变量
- `xiaohongshu_copy`
- `douyin_script`
- `image_prompt`
- `video_prompt`
- `product_knowledge`
- `platform_rules`

## 输出变量
- `approved`
- `risk_level`
- `issues`
- `required_edits`
- `safe_publish_summary`

## Prompt
使用 `compliance_reviewer.md`。Stage 1 仅允许通过到人工审核，不允许自动发布。

## JSON 输出格式
```json
{
  "approved": false,
  "risk_level": "low",
  "issues": [],
  "required_edits": [],
  "safe_publish_summary": ""
}
```

## 失败处理建议
- 审核输出缺少 risk_level: 默认 medium 并要求人工复核。
- 内容为空: 返回 high risk 和 needs_content=true。
