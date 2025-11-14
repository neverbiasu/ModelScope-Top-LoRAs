# Top‑LoRAs — 可执行任务清单

本 TODO 面向短周期迭代：每项任务应具体、可验证并包含验收标准。已完成项放到 Done 区。草稿文档请保留在 `Agent.md` 或 `docs/drafts` 分支。

优先级说明：
- Next：立即做，影响面大且能快速提升稳定性或用户体验；
- Backlog：中期重构/测试任务；
- Docs/Housekeeping：文档与流程改进。

## Next（高优先级）

 - [ ] 代码清理：将 `re` 模块移到模块顶层导入
  - 步骤：在 `top_loras/parser.py` 中将 `import re as _re` 移到文件顶部的 imports 区域；确保没有功能回归并运行相关单元测试。
  - 验收：模块顶部包含 `import re as _re`，代码风格一致，通过 parser 的测试用例。估时：10–30 分钟。

- [ ] 代码清理：将 `re` 模块移到模块顶层导入
  - 步骤：在 `top_loras/parser.py` 中将 `import re as _re` 移到文件顶部的 imports 区域；确保没有功能回归并运行相关单元测试。
  - 验收：模块顶部包含 `import re as _re`，代码风格一致，通过 parser 的测试用例。估时：10–30 分钟。

- [ ] 实现或移除 `MAX_RETRIES` 并补充重试逻辑（`top_loras/inference.py`）
  - 步骤：在 `top_loras/inference.py` 中对外部请求实现重试（针对网络错误/429/5xx，使用指数退避），或者删除未使用的 `MAX_RETRIES` 常量并在文档中说明没有重试行为。
  - 验收：若实现重试，重试逻辑能够在模拟网络错误时触发并在日志中记录重试次数；若删除常量，文件不再包含未使用的变量并通过 lint 检查。估时：30–60 分钟。

## Backlog（中优先）

- [ ] 模块化重构：`top_loras/api.py`、`parser.py`、`filter.py`
  - 目标：拆分职责、明确接口、补充 docstring 与类型注解。拆成小 PR，逐步合并。估时：2–3 天。

- [ ] 单元测试覆盖（parser/filter/cache）
  - 添加边界用例（缺字段、空封面、异常网络、下载失败回退等）。估时：1–2 天。

- [ ] CI：可选生成测试（当且仅当 `MODELSCOPE_API_TOKEN` secret 可用时运行）
  - 在 workflow 中用条件判断跳过敏感测试以避免泄露。估时：半天。

## Docs 与流程（低优先）

- [ ] 提交流程与草稿保护（Agent.md 已有说明）
  - 增加 pre-commit 或 CI 阶段检查，阻止带 `<!-- DRAFT -->` 的文件被合并到主分支。估时：3–4 小时。

## Done（最近完成）

- [x] 修复 Gallery.select 回调的鲁棒性（支持多种 evt 形态并返回一致输出）
- [x] 修复回调 arity mismatch 问题（所有分支返回正确数量的 outputs）
- [x] 在 `Agent.md` 记录代码规范与历史问题/教训
- [x] 创建 `Agents.md` 并弃用 `Agent.md`（内容复用与改进）
- [x] 验证 Selection → Generate（手动端到端）
  - 验收：运行 `python app.py`，选择 Gallery 卡片并在 Generate 页确认 `Selected Model ID` 与 `gen_model_info` 更新；终端显示 `[DBG] Matched selected id: <id>`，未出现回调 arity/None image 异常。
- [x] Generation 原型（后端 wrapper，feature 分支）
  - 说明：已实现 `top_loras/inference.py` 原型，UI 可提交生成并显示返回结果；UI 端不持久化图片/JSON（如需持久化应由后台或显式开关控制）。
- [x] 更新 `DATA_INTERFACE.md`（outputs schema 草稿）
  - 把 `cache/outputs` 的数据契约写入文档（job meta/status/result/error 示例）；保持为草稿并在 `Agent.md` 标注。
- [x] 移除 app.py 中将生成结果持久化为图片/JSON 的逻辑
  - 说明：UI 不再在客户端写入 `cache/outputs`；生成結果仅在界面展示，若需要持久化應通過後台或顯式開關控制。已完成（本地改动）。

## 下一步（请回复一个选项）

- A：我现在更新 `DATA_INTERFACE.md`，把 outputs schema 写为草稿（仅保留工作区，不提交）；
- B：我创建 feature 分支 `feature/generate-proto` 并开始实现 `top_loras/inference.py` 的原型；
- C：我先执行手动 E2E 验证（Selection → Generate），并把终端日志与发现贴回给你。

回复 A / B / C，我立即开始执行并在完成后汇报结果。
