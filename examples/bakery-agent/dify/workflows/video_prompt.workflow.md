# Video Prompt Workflow

## 节点名称
Start -> Knowledge Retrieval -> Douyin Scriptwriter -> Video Prompt Generator -> Compliance Reviewer -> Answer

## 输入变量
- `product_query`
- `visual_direction`
- `duration_seconds`

## 输出变量
- `video_prompt_zh`
- `video_prompt_en`
- `duration_seconds`
- `camera_motion`
- `keyframes`
- `negative_prompt`
- `compliance_result`

## Prompt
使用 `douyin_scriptwriter.md` 和 `video_prompt_generator.md`，为 Seedance 或 Kling 的异步任务预留字段。

## JSON 输出格式
```json
{
  "video_prompt_zh": "",
  "video_prompt_en": "",
  "duration_seconds": 5,
  "camera_motion": "",
  "keyframes": [],
  "negative_prompt": "",
  "compliance_result": {}
}
```

## 失败处理建议
- 视频任务创建失败: n8n 记录 provider、请求体和错误码，不重试超过 2 次。
- 轮询超时: 保存 pending 状态并通知人工处理。
