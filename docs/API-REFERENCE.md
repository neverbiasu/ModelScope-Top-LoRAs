<!-- DRAFT -->
# ModelScope API-Inference Reference (Image Generation Extract)

> 摘录自用户提供的文档内容并聚焦“文生图”调用；仍属草稿，后续需根据官方最新说明校对。

## 前提条件
- 需要已注册并绑定阿里云与实名认证的 ModelScope 账号。
- 获取 Access Token: https://modelscope.cn/my/myaccesstoken
- 设置环境变量或在 UI 中输入：`MODELSCOPE_API_TOKEN`。

## 基础信息
- Base URL: `https://api-inference.modelscope.cn/`
- Image Generation Endpoint: `POST v1/images/generations`
- Async Polling Endpoint: `GET v1/tasks/{task_id}` with header `X-ModelScope-Task-Type: image_generation`
- 必须 Header: `Authorization: Bearer <TOKEN>` & `Content-Type: application/json` & 提交时 `X-ModelScope-Async-Mode: true`

## 请求参数（文生图）
| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| model | 是 | string | 模型 ID，例如 `black-forest-labs/FLUX.1-Krea-dev` |
| prompt | 是 | string | 正向提示词，建议英文提高质量 |
| negative_prompt | 否 | string | 负向提示词 |
| size | 否 | string | 分辨率，如 `1024x1024`（受模型限制范围） |
| seed | 否 | int | 随机种子，0/缺省为随机 |
| steps | 否 | int | 采样步数（例如 30） |
| guidance | 否 | float | 提示词引导系数（例如 3.5） |
| image_url | 否 | string | 编辑/图生图场景的输入图 URL |

## 返回示例（提交）
```jsonc
{
  "task_id": "abc123..."
}
```

## 轮询返回示例（成功）
```jsonc
{
  "task_id": "abc123...",
  "task_status": "SUCCEED",
  "output_images": ["https://.../image1.png", "https://.../image2.png"]
}
```

失败时：
```jsonc
{
  "task_id": "abc123...",
  "task_status": "FAILED",
  "error": "<message>"
}
```

## 时序
1. POST `/v1/images/generations` -> 得到 `task_id`
2. 定期 GET `/v1/tasks/{task_id}` 带 `X-ModelScope-Task-Type: image_generation`
3. SUCCEED -> 使用 `output_images` 中的 URL 下载或展示；FAILED -> 记录错误。

## 本项目中适配
- 文件：`top_loras/inference.py` 中 `_remote_infer_image` 实现上述流程。
- 支持配置：
  - `MODELSCOPE_INFER_BASE` (默认 `https://api-inference.modelscope.cn/`)
  - `MODELSCOPE_IMAGE_POLL_INTERVAL` (默认 3 秒)
  - `MODELSCOPE_IMAGE_POLL_MAX_SECONDS` (默认 60 秒)
- 成功后会下载首张图片本地存为 `cache/outputs/images/gen_<id>.jpg` 并在 UI 展示。

## 后续计划
- 支持多张图展示 `images_local` 列表。
- 支持 size 参数 UI 输入与负向提示词。
- 错误码细化与重试策略（网络瞬时失败）。
- 扩展至其他任务类型（文本生成、图文理解）。

## 注意事项
- 若出现 400 Bad Request，请确认：
  - 模型是否支持 image generation（LoRA ID 与 API 能力可能不同）。
  - 参数范围是否符合官方限制（steps, guidance, size）。
  - Token 权限与账户实名认证状态。
- 若持续返回 mock，说明远程抛异常已回退；查看 job JSON 中 `error` 字段。

---
(草稿结束)
