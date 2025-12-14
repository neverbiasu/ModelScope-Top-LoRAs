# Errors / 故障排查（ModelScope API）

本项目的远端推理链路：
- UI：`ui/callbacks.py`（组装 base model + `loras`）
- 推理：`top_loras/inference.py`（`POST /v1/images/generations` 异步提交 + `GET /v1/tasks/{task_id}` 轮询）

下面是目前遇到过的错误类型、它们“客观上意味着什么”、以及你能立刻采取的动作。

---

## 1) `errors.message = "task not found"`（轮询阶段 FAILED）

**典型报错（示例）**
- `Image generation failed: {..., "errors": {"code": 500, "message": "task not found"}, "task_status": "FAILED"}`
- 你这次的关键信息：
  - `submitted_model`: `MusePublic/489_ckpt_FLUX_1`
  - `submitted_loras`: `yiwanji/FLUX_xiao_hong_shu_ji_zhi_zhen_shi_V2`
  - `task_id`: `4213726`
  - `request_id`: `055f7eed-c688-47d9-9b3b-4752c3f7458a`

**从返回能确定的事实**
- 提交接口已经返回了 `task_id`（说明 submit 这一步没有被拒绝）。
- 随后对 `GET /v1/tasks/{task_id}` 的查询，服务端返回“找不到该任务”。
- 客户端侧没有额外字段能解释“为什么找不到”（因此必须依赖 `request_id/task_id` 给平台排查）。

**常见触发形态（仅基于现象归类，不替平台下结论）**
- 提交后短时间内查询不到任务（一致性窗口/网关路由差异/任务系统异常等都会表现成这个现象）。
- 某些 task-type header 不匹配时，返回 stub/空壳响应或查询异常（本项目已做多 task-type 容错）。

**本项目当前的缓解措施**
- `MODELSCOPE_TASK_NOT_FOUND_GRACE`（默认 15s）内遇到 `task not found` 会自动重试，尽量避免“刚提交就查不到”。
- 对“stub PENDING（空 task_id/request_id）”会自动改用不带 `X-ModelScope-Task-Type` 或尝试 `aigc` 再查。
- 错误会原样透传并附加：`task_id/task_url/submitted_model/submitted_loras/poll_response_headers`，便于工单定位。

**你可以立刻做的动作（减少额外扣费/失败次数）**
- 先把 grace window 拉长到 60s：
  - `export MODELSCOPE_TASK_NOT_FOUND_GRACE=60`
- 轮询间隔拉大一点（减少请求次数）：
  - `export MODELSCOPE_IMAGE_POLL_INTERVAL=4`
- 打开调试输出并复现 1 次，保留完整日志：
  - `export MODELSCOPE_DEBUG=1`

**给平台/工单的最小信息**
- `request_id`
- `task_id`
- `submitted_model` + `submitted_loras`
- 复现时间（含时区）

---

## 2) `40212`（提交阶段被拒/额度或权限类错误）

**典型表现**
- `Submit error 400: ...` 里包含 `40212`（或同类 detail）。
- 常发生在使用 `AI-ModelScope/FLUX.1-dev` 这类 base 时（你已确认之前 base repo 选错）。

**从返回能确定的事实**
- 请求在 submit 阶段就被拒绝，任务不会进入轮询阶段。

**本项目当前处理**
- 对 `400` 先做一次 minimal payload 重试（减少参数导致的 schema/校验失败）。
- 若仍含 `40212`，会尝试 fallback：`model=Qwen/Qwen-Image` + `loras=<lora>`（仅用于排障/对照，不能保证 LoRA 兼容）。

**建议**
- 对 FLUX LoRA：优先用正确的 base（例如你给出的 `MusePublic/489_ckpt_FLUX_1`），不要用 `AI-ModelScope/FLUX.1-dev`。

---

## 3) `Submit error 400`（参数/Schema 不兼容）

**典型表现**
- `Submit error 400: {detail...}`

**从返回能确定的事实**
- 服务端拒绝了提交体（字段不支持/格式不对/模型不接受该参数）。

**本项目当前处理**
- 自动把部分参数做映射：
  - `size` → `width/height`
  - `steps` → `num_inference_steps`
  - `guidance` → `guidance_scale`
- 400 时会用 minimal body 再重试一次。

---

## 4) `stub PENDING`（轮询拿到“空壳任务”）

**典型表现**
- `task_status` 是 `PENDING/RUNNING`，但 `task_id/request_id` 为空，`outputs` 为空。

**从返回能确定的事实**
- 你拿到的不是“真实任务详情”（常见于 task-type header 不匹配的网关响应）。

**本项目当前处理**
- 自动重试：先不带 `X-ModelScope-Task-Type`，再尝试 `aigc`。

---

## 5) `FAILED` 但 `errors.message` 为空

**典型表现**
- `task_status=FAILED` 且 `errors` 里 `message` 为空/缺失。

**本项目当前处理**
- 会短暂等待并重新拉取 1~2 次任务详情，尽量抓到延迟落地的错误信息。

---

## 6) 本地代码错误：`NameError: poll_headers is not defined`

**表现**
- 这是客户端代码 bug，与 ModelScope 无关。

**状态**
- 已修复（并已回归通过）。

---

## 快速收集诊断信息（推荐）

在复现前设置：
- `export MODELSCOPE_DEBUG=1`
- `export MODELSCOPE_TASK_NOT_FOUND_GRACE=60`

复现后，把 UI 输出里的这几项复制出来即可：
- `task_id`
- `request_id`
- `submitted_model`
- `submitted_loras`
- `errors`（原样 JSON）
