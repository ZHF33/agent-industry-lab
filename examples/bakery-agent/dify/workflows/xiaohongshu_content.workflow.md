# Xiaohongshu Content Workflow

## 节点名称
Start -> Knowledge Retrieval -> Content Planner -> Xiaohongshu Copywriter -> Compliance Reviewer -> Answer

## 输入变量
- `product_query`
- `campaign_goal`
- `brand_context`

## 输出变量
- `titles`
- `cover_text`
- `body`
- `hashtags`
- `compliance_result`

## Prompt
使用 `content_planner.md` 生成选题，再使用 `xiaohongshu_copywriter.md` 生成笔记，最后使用 `compliance_reviewer.md` 检查风险。

## JSON 输出格式
```json
{
  "titles": [],
  "cover_text": "",
  "body": "",
  "hashtags": [],
  "compliance_result": {}
}
```

## 失败处理建议
- 标题为空: 重试 copywriter 节点。
- 合规风险中高: 输出 required_edits，不进入发布。
