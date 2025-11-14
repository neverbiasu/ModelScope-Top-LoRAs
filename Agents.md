# Agents — 工作与草稿管理（复用自 Agent.md）

<!-- DRAFT: 本文件为团队内部 agents 指南与草稿管理，应在评审后将最终版本合并 -->

更新日期：2025-11-11

目的：替代旧的 `Agent.md`，提供一份更接近 `agents.md` 规范风格的内部指南，包含：



## 草稿文件（当前）

暂不提交、仅在工作区或专用分支维护的文档：

<!-- DRAFT: agents-style guide — derived from Agent.md -->

# Agents — 工作与草稿管理（表格与有序列表版）

更新日期：2025-11-11

目的：以更简洁、结构化的方式记录草稿管理、提交流程、代码规范与常见问题，便于团队快速查阅与在 CI 中自动化检查。

## Recent Changes

- 2025-11-13: `top_loras/parser.py` — 将 `import re as _re` 移到模块顶部以符合代码风格与静态检查要求；更新 TODO，已在本地完成并记录（不自动推送）。
 - 2025-11-13: `top_loras/inference.py` — 为远程请求添加 `MAX_RETRIES` 的指数退避重试辅助函数，并用于提交、轮询与图像下载调用；记录为本地变更且已同步到 TODO。该逻辑在网络错误或 429/5xx 时会重试，最多重试 `MAX_RETRIES` 次。
 - 2025-11-13: `top_loras/inference.py` 测试 — 对 `_requests_with_retries` 进行了本地验证，使用 `https://httpbin.org/status/429` 触发 429/503 响应并观察到重试日志输出。测试结果：最终返回 HTTP 503（重试已触发 2 次后结束）；详情见下方日志。

Test log (local):

```
[2025-11-13T21:26:40Z] Request GET https://httpbin.org/status/429 returned 503; retry 1/3
[2025-11-13T21:26:41Z] Request GET https://httpbin.org/status/429 returned 503; retry 2/3
FINAL_STATUS 503
```
1. 草稿文件（当前）
	| 文件 | 状态 | 说明 |
	|---|---:|---|
	| `PRD.md` | draft | 产品需求说明，含未定设计点 |
	| `TODO.md` | draft | 开发优先级与任务（频繁变动） |
	| `DATA_INTERFACE.md` | draft | Outputs schema（生成任务结果） |

	说明：新增草稿时请把文件放到 `docs/drafts/` 或在文件顶部写入 `<!-- DRAFT -->`。

2. 提交流程（简洁、按步骤）
	1. 在 feature 分支完成草稿并在文件顶部加 `<!-- DRAFT -->`。
	2. 提交 PR，描述变更、验收标准与风险；@ 至少一名评审人。
	3. 评审通过后移除 `<!-- DRAFT -->` 或由合并者在合并时移除。

	额外要求：如果草稿包含代码改动（如 `top_loras/inference.py`），需同时提交最小的单元测试并在 CI 通过。

3. 合并前快速检查（表格化）
	| 检查项 | 说明 | 操作 |
	|---|---|---|
	| 敏感信息 | 是否包含 API token/凭证/个人数据 | 用 `<YOUR_TOKEN>` 占位或从文件中移除 |
	| 调试遗留 | 是否包含 `print` 或大量 base64 | 把 `print` 替换为 `logging` 或移除；base64 改为 URL |
	| 未决决策 | 文档是否含未决问题 | 列为 `TODO` 并保留草稿标记 |
	| 可重复性 | 是否包含复现步骤与验收标准 | 补充步骤与期望输出 |

4. 代码规范（关键点，表格）
	| 主题 | 要点 |
	|---|---|
	| 风格 | 遵循 PEP8；CI 中使用 `black`、`ruff` |
	| 类型 | 公共 API 使用 typing，关键函数写 docstring |
	| 日志 | 使用 `logging`；避免 `print` 在主分支出现 |
	| Secrets | Token 通过 env/CI secret 注入，不能入库 |
	| 测试 | parser、api wrapper、cache、download 必须有单元测试 |
	| 回调安全 | Gradio 回调需容错并返回与 outputs 数量一致的值 |

5. 已遇问题与对策（有序清单，含复现与解决建议）
	1. 语法损坏（未闭合字符串）
		- 避免直接粘贴回调片段；在提交前运行 `python -m py_compile`。
	2. Gradio 回调输出不匹配（arity mismatch）
		- 确保所有分支返回与绑定输出数量一致；编写小脚本覆盖边界路径。
	3. Gallery 中 None 导致的 image 错误
		- sanitize 模型数据；缺封面使用透明 data-URI 或本地占位图。
	4. 回调接收意外参数（EventData 形态差异）
		- 回调签名采用 `(*args, **kwargs)` 或 `(evt, state=None, **kwargs)` 并解析常见字段。
	5. base64 导致性能问题
		- 优先使用 `result.url` 或 Gradio 静态资源；仅在回退时使用 base64。

6. 快速验证清单（按步骤）
	1. 语法检查：`python -m py_compile app.py`。
	2. 单元测试：`pytest tests/ -q`（或针对模块运行）。
	3. 本地 UI 验证：启动 UI → 选择模型 → 检查 Generate 页是否更新。
	4. 出错时：拷贝终端中的 `[DBG] gallery.select` 或 traceback 以便排查。

7. 建议的下一步（短列表）
	- 在 CI 中添加 pre-merge 钩子：运行 `python -m py_compile` 与 pytest；阻止含 `<!-- DRAFT -->` 的文件合并。
	- 将本文件摘录为 `CONTRIBUTING.md` 的一节并增加 PR 模板以简化评审流程。

8. 运行小工具（可选）
	| 操作 | 推荐命令 |
	|---|---|
	| 本地语法检查 | `python -m py_compile app.py` |
	| 运行全部测试 | `pytest -q` |

---

注：如果需要，我可以把 `Agent.md` 迁移为 `docs/drafts/Agent.md.snapshot` 以保留历史记录，或进一步把 `Agents.md` 转为 `CONTRIBUTING.md` 并创建 `.github/PULL_REQUEST_TEMPLATE.md`。
