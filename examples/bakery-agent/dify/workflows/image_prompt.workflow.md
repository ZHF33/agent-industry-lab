# Image Prompt Workflow

## 节点名称
Start -> Knowledge Retrieval -> Image Prompt Generator -> Compliance Reviewer -> Answer

## 输入变量
- `product_query`
- `visual_direction`
- `channel`

## 输出变量
- `prompt_zh`
- `prompt_en`
- `negative_prompt`
- `aspect_ratio`
- `compliance_result`

## Prompt
使用 `image_prompt_generator.md`。图片提示词要明确主体、构图、光线、质感、背景和道具。

## JSON 输出格式
```json
{
  "prompt_zh": "",
  "prompt_en": "",
  "negative_prompt": "",
  "aspect_ratio": "",
  "compliance_result": {}
}
```

## 失败处理建议
- 缺少产品主体: 重试并追加产品知识摘要。
- 出现品牌侵权或医疗暗示: 删除相关表达。
