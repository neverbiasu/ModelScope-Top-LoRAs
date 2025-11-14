*<!-- DRAFT: Outputs schema - do not merge to main without review -->

# Top LoRAs — 数据接口与 Outputs 缓存（草稿）

本文档描述两部分内容：

1. `fetch_top_models.py` 与模型缓存（保留兼容性说明）；
2. 生成任务输出（`cache/outputs/{task}`）的数据契约草稿。

目的：为前端、后端与离线消费者定义一个最小且兼容的 JSON 格式，以便统一展示、重现与归档生成任务结果。

> 注意：该 Outputs 契约目前为草稿。请勿在未评审的情况下合并到主分支。

---

## 1) 模型缓存（简要回顾）

- 现有模型缓存文件仍使用 `cache/top_loras_{safe_task}.json`：顶级 `_cached_at` 与 `results` 数组。
- 模型对象字段示例：`id`, `title_cn`, `title_en`, `cover_url`, `cover_local`, `downloads`, `likes`, `tags_*` 等。
- 消费端应忽略未知字段以保持前向兼容。

---

## 2) Outputs 缓存（草稿） — 目标格式

路径示例： `cache/outputs/<safe_task>/<job_id>.json`

主要目标：可重现、可归档、可逐步更新（status），并优先通过 URL 引用结果文件。

### 基本字段

- `job_id` (string, required): 唯一 job 标识（建议 `uuid4` 或 `<model_id>-<timestamp>`）。
- `task` (string, required): 任务类型（`text-to-image`, `image-to-image` 等）。
- `model_id` (string, required): 生成所用模型标识。
- `params` (object, required): 原始请求参数（avoid sensitive fields）。
- `status` (string, required): `queued` / `running` / `succeeded` / `failed` / `cancelled`。
- `created_at` (string, required, ISO8601): job 创建时间（UTC）。
- `started_at` (string|null, ISO8601): 实际开始时间或 null。
- `completed_at` (string|null, ISO8601): 结束时间或 null。
- `meta` (object, optional): 运行时元信息（`node`, `attempts`, `duration_seconds` 等）。
- `result` (array, required but may be empty): 结果项数组，每项为 object（见下）。
- `error` (object|null): 失败时填充，包含 `code`, `message`, `details`。

### Result item (`result[]`)

- `index` (integer): 结果序号。
- `type` (string): `image` / `text` / `json` 等。
- `data` (object): 与 `type` 对应的载体：
  - 对于 `image`:
    - `url` (string|null): 相对或绝对 URL（优先）；
    - `base64` (string|null): base64 编码图像（回退）；
    - `mime` (string|null): MIME 类型（例如 `image/png`）。
- `meta` (object|null): 该项的元信息，例如 `width`, `height`, `seed`。

### 设计与兼容性

- 优先使用 `result[].url`，在无法提供 URL 时回退到 `result[].base64`；避免一次性加载大量 base64 数据。
- 所有时间字段使用 ISO8601（UTC）。
- `params` 中不得包含明文凭证或敏感数据。

### 简化 JSON Schema（用于校验）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["job_id","task","model_id","params","status","created_at","result"],
  "properties": {
    "job_id": {"type":"string"},
    "task": {"type":"string"},
    "model_id": {"type":"string"},
    "params": {"type":"object"},
    "status": {"type":"string"},
    "created_at": {"type":"string","format":"date-time"},
    "started_at": {"type":["string","null"]},
    "completed_at": {"type":["string","null"]},
    "meta": {"type":["object","null"]},
    "result": {"type":"array"},
    "error": {"type":["object","null"]}
  }
}
```

### 示例（成功）

```json
{
  "job_id": "b2a9f3d4-8c7a-4e2b-9a2c-0f1e2d3c4b5a",
  "task": "text-to-image",
  "model_id": "owner/my-lora-v1",
  "params": { "prompt": "A fantasy landscape", "steps": 20, "seed": 12345 },
  "status": "succeeded",
  "created_at": "2025-11-11T10:12:34Z",
  "started_at": "2025-11-11T10:12:40Z",
  "completed_at": "2025-11-11T10:13:05Z",
  "meta": { "node": "local-macbook", "duration_seconds": 25 },
  "result": [
    {
      "index": 0,
      "type": "image",
      "data": {
        "url": "cache/outputs/text-to-image/b2a9f3d4/0.png",
        "base64": null,
        "mime": "image/png"
      },
      "meta": { "width": 1024, "height": 1024, "seed": 12345 }
    }
  ],
  "error": null
}
```

### 示例（失败）

```json
{
  "job_id": "e4c1b2a3-1111-2222-3333-444455556666",
  "task": "text-to-image",
  "model_id": "owner/my-lora-v1",
  "params": { "prompt": "..." },
  "status": "failed",
  "created_at": "2025-11-11T11:00:00Z",
  "started_at": "2025-11-11T11:00:10Z",
  "completed_at": "2025-11-11T11:00:12Z",
  "meta": { "node": "remote-api", "attempts": 1 },
  "result": [],
  "error": { "code": "api.timeout", "message": "ModelScope inference timed out", "details": { "timeout_seconds": 30 } }
}
```

---

## 下一步建议

1. 在 `top_loras/inference.py` 中实现写入/更新逻辑以遵守该契约；
2. 为 `submit_job` 编写 2 个单元测试（远端成功 mock 与远端失败/超时 mock）；
3. 在 `Agent.md` 标注本文件为草稿并在 CI/pre-commit 中阻止未评审草稿合并到主分支。
*