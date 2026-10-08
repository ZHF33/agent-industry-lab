# Bakery Operation V1 Workflow

## 节点名称
Start -> Knowledge Retrieval -> Content Planner -> Xiaohongshu Copywriter -> Douyin Scriptwriter -> Image Prompt Generator -> Compliance Reviewer -> Answer

## 输入变量
- `product_query`: 产品或主题
- `campaign_goal`: 当日运营目标
- `brand_context`: 品牌补充信息
- `date`: 生成日期

## 输出变量
- `content_plan`
- `xiaohongshu_copy`
- `douyin_script`
- `image_prompt`
- `compliance_result`

## Prompt
依次使用 `dify/prompts/content_planner.md`, `xiaohongshu_copywriter.md`, `douyin_scriptwriter.md`, `image_prompt_generator.md`, `compliance_reviewer.md`。Knowledge Retrieval 节点检索 `knowledge/processed` 导入 Dify 后的知识库。视频生成在当前 V2 image-first 阶段跳过。

## JSON 输出格式
```json
{
  "content_plan": {},
  "xiaohongshu_copy": {},
  "douyin_script": {},
  "image_prompt": {},
  "compliance_result": {}
}
```

## 失败处理建议
- Knowledge Retrieval 为空: 返回 `needs_knowledge=true`，提示先上传产品文档。
- 任一生成节点 JSON 无法解析: 重试一次，并要求模型只输出 JSON。
- Compliance Reviewer 为 high risk: 停止后续自动化，只发送人工审核。
