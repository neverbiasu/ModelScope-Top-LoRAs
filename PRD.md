# Top‑LoRAs — 产品需求说明（PRD）

版本：0.1
最后更新：2025-11-10

## 概述
Top‑LoRAs 提供一条可在本地或 CI 运行的轻量数据流水线和只读 Gradio UI，用于从 ModelScope 前端响应构建可缓存的 LoRA 榜单（Top LoRAs）。重点：缓存 JSON 精简、图片保存到本地 `cache/images/{task}` 以供前端使用，且不在缓存中保存原始二进制或 `aigc_attributes`。

## 核心决策（已确认）
- 图片优先通过 `cover_url`（HTTP/HTTPS）直接下载并保存到 `cache/images/{task}`，通常不需要 ModelScope API token；TOKEN 主要用于生成/受保护资源的场景，而不是常规图片下载。
- 缓存 JSON 明确禁止包含 `raw blob` 或 `aigc_attributes` 字段。

## 功能要点（摘要）
- 数据采集：从 ModelScope 前端 JSON（或公开 API）解析并提取模型元数据（id、title、author、cover_url、downloads、modelscope_url、updated_at、tags 等），解析结果须去掉 `aigc_attributes`。
- 图片下载：默认通过 `cover_url` 直接下载到 `cache/images/{task}` 并在 JSON 中记录 `cover_local`；仅在直接下载失败且环境提供 token 时，才尝试带鉴权的回退请求。
- 缓存：以 `cache/top_loras_{safe_task}.json` 为单位存储，顶层包含 `_cached_at` 与 `results`。
- CLI：提供 `--limit`、`--task`、`--force-refresh`、`--cache-file`、`--images-dir`、`--per-task-cache` 等参数；默认会下载图片并填充 `cover_local`。
- UI：Gradio 提供 Selection（Gallery）→ Generate 的两步流程；Gallery 从缓存读取并展示封面，Generate 页用于显示所选模型详情与生成参数（token 为生成用途）。

## 数据契约（最简）
- 顶层：{ `_cached_at`: ISO timestamp, `results`: [ ... ] }
- 每条 result 至少包含：
  - `id` (str)
  - `title_en` / `title_cn` (str)
  - `cover_url` (str)
  - `cover_local` (str|null)
  - `downloads` (list)
  - `modelscope_url` (str)
  - `updated_at` (ISO str)
- 明确禁止：`raw blobs`、`aigc_attributes`。

## 验收标准（Acceptance Criteria）
- 单元测试通过（parser、download、cache 等关键路径）。
- 运行 `python fetch_top_models.py --task <task> --force-refresh` 后：
  - 生成/更新 `cache/top_loras_{safe_task}.json`（不含 `aigc_attributes`）。
  - 在 `cache/images/{safe_task}` 中保存封面图片，且 `cover_local` 指向正确路径。
- Gradio UI 能从缓存加载 Gallery 且可选中模型进入 Generate 页；Generate 页可接收 token 用于生成流程（token 不用于一般图片下载）。

## CI 与部署建议
- 若大多数图片为公开链接，CI 无需安装 `modelscope` 或注入 token；仅需在 workflow 中运行 CLI 刷新并将 `cache/*.json` 或图片作为 artifacts 发布（如需要）。
- 若存在受限资源或测试生成流程，请在 GitHub Secrets 中添加 `MODELSCOPE_API_TOKEN` 并在 workflow 中注入给运行环境（仅在必要时使用）。

## 后续扩展（可选）
- 增强认证下载：支持更多 header 格式或短期签名回退方案。
- 将缓存作为 artifact 上传或推送到远端以便共享。

## 下一步建议
1. 添加一个示例 GitHub Actions workflow：展示如何在 CI 中运行 `fetch_top_models.py --force-refresh` 并把 `cache/` 目录上传为构件。
2. 将 README 中的“Cache schema (short)” 链接到 `DATA_INTERFACE.md`（或在仓库根写一份更详尽的数据字典）。
3. 若你同意，我可以把这份 PRD 合并到 README 的文档区并且创建 `TODO.md`（非必需）。

---

**PRD 完整状态：** 已更新（2025-11-10）。


当前实现的只读 Gradio UI 已能显示卡片网格与基础信息，但存在若干用户体验问题，需要优先改进：

- 布局问题：在部分桌面浏览器窗口下出现单列（应确保在典型桌面宽度下显示多列卡片）。
- 卡片一致性：封面需要强制统一纵横比（例如 16:9 或可配置的比例）并且裁剪策略需稳定（object-fit: cover 对多数图片效果良好，但仍需校准）。
- 头像与封面需在同一卡片内自然排列（避免使用 gallery 弹出或外部组件拆分视图）。
- 图片服务：当前将本地文件转换为 base64 嵌入页面以避免 file:// 加载问题，但对于大量图片会使 HTML 体积非常大，影响加载性能；应切换为 Gradio 静态路由或使用 `gr.Image` 组件提供图片资源。
- 交互性：缺少加载指示器、刷新状态与后台任务提示（用户希望界面更加响应并在刷新时看到进度）。
- 过滤与分页：当缓存包含大量模型时，需要客户端分页、搜索与过滤，以保持界面响应性。

短期目标（优先级高）

1. 修复网格布局以确保桌面多列显示（改用 `auto-fit` + `minmax(240px,1fr)`，并为容器增加唯一 id 以避免样式覆盖）。
2. 将图片服务改为 Gradio 静态或 `gr.Image`（避免大量 base64 内嵌）。
3. 在卡片上强制封面纵横比并统一裁剪策略，保证卡片高度一致。
4. 添加加载指示与后台刷新提示（含小型进度反馈）。

验收标准（针对 UI 改进）

- 桌面宽度 >= 1000px 时，界面至少显示 2 列（优选 3 列）；卡片一致且封面纵横比保持统一。
- 页面不再把所有本地图片以 base64 嵌入 HTML（首页 HTML 大小明显下降），图片通过 Gradio 静态路由或 `gr.Image` 正常加载。
- 刷新操作显示加载动画/进度，并在完成后自动更新缓存视图。

### 9.4 选择 → 生成 工作流（Selection → Generation）

目标：把当前“只读展示”扩展为两阶段流程，便于用户在浏览与对比模型后，进入生成（推理）工作区执行样例生成。设计应兼顾发现（选择）与执行（生成）的 UX。

阶段划分：
1. 选择阶段（Selection） — 卡片网格、筛选、快速比较、标记/收藏、打开详情。
   - 用户动作：浏览、搜索、按基础模型或标签筛选、短列表对比（勾选多模型进行对比）。
   - 输出：选中一个或多个模型，点击“Generate”或在详情面板中打开生成工作区。

2. 生成阶段（Generation / Run） — 参数面板、预设、执行/排队、实时日志与输出回显。
   - 参数：strength/scale、steps、guidance, sampler, seed, resolution 等，支持预设与保存。
   - 执行：提交到本地或远程 worker，展示进度条、日志、并在完成后显示输出图像与参数快照。

交互要点：
- 在 Selection 期间支持“快速预览”与“对比模式”（side-by-side 小图展示）。
- 详情面板包含“Generate”按钮，能把当前参数与模型打包并跳转到 Generation 面板（或在模态内直接展开）。
- Generation 面板应允许“重复运行（with same params）”、“导出参数为 JSON”、以及“保存输出到 cache/outputs”。

安全与资源控制：
- 后端运行推理需要限制并发/显存使用，支持队列与超时。默认启用安全策略（例如阻止不受信任模型自动运行可执行代码）。
- 鉴权：若使用远程推理服务，需要在配置中安全存储 API Key 与访问令牌，前端仅提交参数与模型 id。

验收标准（Selection → Generation）：
- 用户可以从卡片直接进入生成面板并提交一次生成任务（本地或远端）。
- 生成任务能返回结果并在 UI 中展示输出图片与参数 metadata；输出写入 `cache/outputs/{task}/` 并可在后续会话中查看。

### 9.5 推理 API 技术合约（草案）

为生成阶段定义一个最小的后端 API 合约（本地或远端 worker）：

- POST /api/v1/generate
  - 请求体(JSON)：
    {
      "model_id": "string",
      "task": "text-to-image-synthesis",
      "params": { "strength": 0.75, "steps": 20, "seed": 12345, ... },
      "output_dir": "cache/outputs/text-to-image-synthesis/"
    }
  - 返回：{ "job_id": "uuid", "status": "queued" }

- GET /api/v1/generate/{job_id}
  - 返回：{ "job_id": "uuid", "status": "running|complete|failed", "progress": 0.45, "result": { "image_url": "/static/outputs/..." }, "log": [ ... ] }

实现注意事项：
- 对于本地 demo，可把 worker 实现为线程或子进程，直接写入 `cache/outputs` 并在 /static 路径下提供文件。远端实现需认证与队列管理。
- 后端应对输入做白名单字段检查，避免注入危险参数或对文件系统进行任意写入。

### 9.6 与 ModelScope API（API‑Inference）对接

目标：支持把 Generate 阶段的推理请求发往 ModelScope 的 API‑Inference（当可用时），并在本地提供退化方案（本地 worker/mock 或 pipeline）。参考：ModelScope 文档 https://modelscope.cn/docs/model-service/API-Inference/intro

鉴权与安全：
- 使用 `MODELSCOPE_API_TOKEN` 环境变量或从 UI 的 Token 输入框读取 token（仅在用户明确提供时才在会话中保留），并在请求头中按 ModelScope 要求传递（通常为 Authorization 或自定义 header）。
- 前端不直接持久化 token；只在会话内传递并建议用户在 CI/Secrets 中保存生产 token。

ModelScope 请求示例（草案）：
POST https://modelscope.cn/api/v1/inference
Headers: { Authorization: "Bearer <TOKEN>", "Content-Type": "application/json" }
Body (JSON):
{
  "model": "<model_id>",
  "task": "text-to-image-synthesis",
  "input": { "prompt": "<text>", "seed": 42, "steps": 20, "guidance": 7.5 }
}

响应（草案）:
{
  "status": "success|failed|running",
  "result": { "images": ["data:image/png;base64,..."], "metadata": { ... } },
  "job_id": "..."
}

本地退化方案（无 token 或不希望使用远端服务）:
- 使用本地 pipeline（例如 ModelScope 的 pipeline 接口或其他已安装模型）在工作进程中执行推理并把结果写入 `cache/outputs/{task}/`。
- 本地方案应与远端返回的 result schema 对齐，以便 UI 层透明处理。

错误、重试与超时：
- 对远端调用实现超时（建议 60s）与指数退避重试（最多 3 次）策略。
- 当鉴权失败或配额限制（429/403）时，展示清晰的前端提示并回退到本地方案（如已配置）。

合规与成本控制：
- 因为远端推理可能计费或受配额限制，UI 应在提交前提示可能产生的消耗（简短文本），并允许用户确认。

验收标准（针对与 ModelScope 对接）:
- 在提供有效 `MODELSCOPE_API_TOKEN` 的情况下，Generate 页面能成功调用 ModelScope 的 API‑Inference，返回图像并在 UI 中展示。
- 在没有 token 或鉴权失败时，可回退到本地 worker 或提示用户并不执行远端调用。
- 记录并展示远端返回的 `job_id`/状态，支持轮询查询并在完成后展示结果。



## 10. 缓存与性能策略

- Top20 列表请求在应用层缓存 **10 分钟**，支持手动刷新
- 图片使用 **lazy loading** 与占位图
- 图片链接优先使用 CDN 或代理加速 URL
- 对关键 API 调用实现 **指数退避重试**（最多 3 次，初始间隔 1s）

## 11. 错误处理与边界情况

| 场景 | 处理方式 |
|------|---------|
| 无网络连接 | 显示友好错误提示 + 重试按钮 |
| 鉴权失败 (401) | 提示"请配置 API Key"，跳转到设置面板 |
| 返回结果不足 20 | 显示实际数量，提示"没有更多内容" |
| 封面 URL 失效 | 使用预设占位图 |
| 参数超出范围 | UI 端校验，显示允许范围与建议值 |
| 模型兼容性冲突 | 禁用"生成"按钮，展示原因 |
| 请求超时（>10s） | 显示"请求超时"，允许重试 |

## 12. 测试计划

### 12.1 单元测试
- ModelScope API wrapper：
  - Happy path（正常返回 20 条）
  - 鉴权失败 (401)
  - 网络超时与异常
  - 异常数据格式（缺字段、类型错误）

### 12.2 集成测试
- 用真实或受控环境验证 Top20 流程
- 优先在本地用实际 API Key 验证

### 12.3 UI 关键路径测试
- 检索 → 打开详情 → 修改参数 → 导出 JSON
- 筛选与搜索功能
- 错误提示显示

### 12.4 性能测试
- 加载 20 张封面的首屏时间（目标 < 2s）
- 内存占用（Gradio 应用）

## 13. 里程碑与预计工期（单人开发为基准）

| 阶段 | 任务 | 预计工期 |
|------|------|---------|
| 准备 | 确认 API、获取 Key、环境配置 | 0.5 天 |
| 后端 | API wrapper、缓存、错误处理 | 0.5 天 |
| 前端 | Gradio UI（展示、详情、导出） | 1 天 |
| 测试与文档 | 单元测试、README、PR 提交 | 0.5 天 |
| **合计** | | **~2.5-3 天** |

> 工期受 ModelScope API 可用性、鉴权需求、网络环境影响。

## 14. 验收标准（Acceptance Criteria）

- [ ] 能从 ModelScope 获取并展示最多 20 个 LoRA（封面、名称、作者、兼容模型）
- [ ] 详情视图能展示建议参数并允许用户编辑与导出配置为 JSON
- [ ] 针对鉴权失败、网络错误、无结果等情况有清晰友好的错误提示
- [ ] repo 包含运行说明（README）、依赖清单与基本单元测试
- [ ] 首页渲染时间 ≤ 2 秒（不含模型下载与运行）

## 15. 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| ModelScope API 限制或字段频繁变动 | 实现 wrapper 层屏蔽字段变更；加单元测试 |
| 部署环境无足够算力进行实时推理 | 把生成预览作为可选功能；在 README 明确说明 |
| 网络访问延迟或间歇性故障 | 实现缓存、重试、超时机制 |

## 16. 参考文档

- [ModelScope 官方文档](https://modelscope.cn/docs)
- [ModelScope GitHub 仓库](https://github.com/modelscope/modelscope)
- [Gradio 官方文档](https://gradio.app/docs/)
- [Gradio 快速开始](https://gradio.app/get_started)

## 17. 后续行动

1. **开发前确认**：在本地验证 ModelScope API 是否可达，确认是否需要代理与鉴权信息
2. **实现**：按照本 PRD 的功能需求、API 合约、UI 草图进行开发
3. **验收**：对照验收标准逐一检查并提交 PR

---

**PRD 审核状态：** 待开发团队评审与确认
