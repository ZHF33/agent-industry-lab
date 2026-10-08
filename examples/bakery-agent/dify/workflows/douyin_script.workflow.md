# Douyin Script Workflow

## 节点名称
Start -> Knowledge Retrieval -> Content Planner -> Douyin Scriptwriter -> Compliance Reviewer -> Answer

## 输入变量
- `product_query`
- `campaign_goal`
- `duration_seconds`

## 输出变量
- `hook`
- `shots`
- `cta`
- `compliance_result`

## Prompt
使用 `content_planner.md` 和 `douyin_scriptwriter.md`。脚本必须可拍摄，镜头数量建议 4 到 6 个。

## JSON 输出格式
```json
{
  "hook": "",
  "shots": [],
  "cta": "",
  "compliance_result": {}
}
```

## 失败处理建议
- 无 hook: 重试并强调前 3 秒。
- 镜头不可拍: 要求改写为实际门店可拍摄画面。
