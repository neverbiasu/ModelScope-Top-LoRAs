# Gallery 选择逻辑（基于 LoraTheExplorer）

本文档总结并归纳了 HuggingFace 空间 `LoraTheExplorer` 中的 gallery 选择逻辑，说明其设计原则、实现要点、常见坑（特别是不同 Gradio 版本下的差异），并给出针对当前仓库（Top‑LoRAs）的重构建议与可执行步骤。

目标：用户点击 Gallery 中的某张卡片时，能够稳定且确定性地将对应模型（完整 dict）选中并传递到 Generate 页用于推理。

---

## 设计要点（核心原则）

- UI 展示数据（`gallery.value`）和业务数据（`models_state`）分离：
  - `gallery.value`：仅用于展示，通常为 `[(image, title), ...]`。
  - `models_state`：`gr.State`，存放完整模型条目（list[dict]），包含 `id`, `title`, `title_cn`, `cover_local` 等字段。
- 点击回调不通过字符串匹配 title 来查找模型（脆弱）；而是使用“索引”映射：回调获取当前点击的 index（`SelectData.index`），然后用该 index 去 `models_state[index]` 获取完整模型。
- 保持 `gallery.value` 与 `models_state` 顺序一致（swap/sort/refresh 操作总要同时更新两者）。
- 不要在回调上添加容易触发 Gradio `typing.get_type_hints` 的复杂类型注解（例如直接引用 `gradio.events.SelectData`），以免在不同版本下触发解析异常。

---

## LoraTheExplorer 的关键实现要点（摘录并解读）

1. 有一个 `gr.State` 保存完整数据：

```py
gr_sdxl_loras = gr.State(value=sdxl_loras_raw)
```

2. `gallery` 用 `(image, title)` 列表做展示，排序/刷新函数 `swap_gallery` 返回 `(gallery_items, sdxl_loras)`，并通过 `outputs=[gallery, gr_sdxl_loras]` 保证 UI 与 state 同步：

```py
def swap_gallery(order, sdxl_loras):
    # 根据 order 排序 sdxl_loras 并返回 gallery items
    return [(item["image"], item["title"]) for item in sorted_loras], sorted_loras

order_gallery.change(fn=swap_gallery, inputs=[order_gallery, gr_sdxl_loras], outputs=[gallery, gr_sdxl_loras])
```

3. 点击回调签名采用 `SelectData` 为第一个参数，`sdxl_loras` 为第二个参数：

```py
def update_selection(selected_state: gr.SelectData, sdxl_loras):
    idx = selected_state.index
    selected = sdxl_loras[idx]
    # 构造 UI 输出

gallery.select(fn=update_selection, inputs=[gr_sdxl_loras], outputs=[...])
```

注意：HF 代码的运行环境会把 `SelectData`（或等效事件对象）作为回调的第一个参数自动传入，而 `inputs` 列表中的组件按顺序传入后续参数。

---

## 常见坑与诊断（尤其是你当前遇到的问题）

1. 回调第一个参数不是事件对象而是 `gallery.value`（一个 `list`）
   - 现象：`getattr(arg, "index", None)` 返回 `<built-in method index of list object ...>`（这是 Python list 自带的 `.index` 方法），或者 `arg` 是整个列表，`.index` 不是我们需要的“点击索引”。
   - 成因：`gallery.select` 的 `inputs`/绑定写法不符合当前 Gradio 版本的事件注入规则，导致第一个位置传入的是 `gallery.value` 而非 `SelectData`。
   - 解决思路：让回调第一个参数为“事件对象”，方法：a) 在 `gallery.select` 中不把 `gallery` 放入 `inputs`（这样第一个自动注入的位置通常是事件对象），同时把 `models_state` 作为 `inputs` 的第一个元素；或 b) 显式使用 `gr.EventData()`（视 Gradio 版本而定）作为 `inputs` 的第一项以强制注入事件对象。

2. `models_state` 在回调中为空（`models_len == 0`）
   - 现象：第二个参数是空，说明 `models_state` 没被正确传给回调，或在调用路径里被覆盖为 `None`/空列表。
   - 成因：可能是 `gallery.select` 被多次绑定或绑定顺序与当前函数签名不一致；也可能是刷新函数没有正确返回 `norm`（完整模型列表）到 `models_state`。
   - 解决思路：确保所有更新 gallery 的函数都返回 `(ui_items, norm)`，并在 `task_dd.change`、`refresh_btn.click` 等地方把 `models_state` 放到 outputs 中；并简化 `gallery.select` 的绑定，保持单一入口。

3. Gradio 版本差异
   - 早期版本（HF 空间）的 Gradio 在回调参数注入上可能更宽松/自动；新版本可能需要显式指明 `EventData()`。务必在本地环境中以当前安装的 Gradio 版本测试。

---

## 针对 Top‑LoRAs 的重构建议（最小可行改动）

下面给出可复制粘贴的改动片段与逐步说明，目标是把行为改成与 HF 示例逻辑一致：回调第一个参数为事件对象且可通过 `.index` 访问，第二个参数为 `models_state`。

### A. 统一 `gallery.select` 绑定（`app.py`）

删除重复且冲突的绑定，保留一处：

将（示例）替换为：

```py
# from ui.callbacks import on_gallery_select, do_generate
gallery.select(
    fn=on_gallery_select,
    inputs=[models_state],
    outputs=[selected_md, selected_state, gen_model_info, selected_id_display],
    queue=False,
)
```

说明：在多数 Gradio 版本中，上面这行会导致回调收到第一个隐式注入的事件对象（`SelectData` 相当的 object）作为第一个参数，`models_state` 作为第二个参数；回调签名应为 `on_gallery_select(selected_state, models)`。

> 备用方案（针对某些 Gradio 版本）
> 如果你的 Gradio 不自动注入事件对象，可以改成显式把事件对象放在 inputs：
>
> ```py
> gallery.select(
>     fn=on_gallery_select,
>     inputs=[gr.EventData(), models_state],
>     outputs=[...],
>     queue=False,
> )
> ```
>
> 注意：有些旧版本 `gr.EventData()` 要求额外初始化参数；首选上面简洁方式（只传 `models_state`）并在回调里接收隐式事件对象。


### B. 重写回调（`ui/callbacks.py`）

把 `on_gallery_select` 改为下面实现：

```py
def on_gallery_select(selected_state, models):
    """当用户点击 gallery 卡片时：
    selected_state: 事件对象，含 .index
    models: models_state（list[dict]）
    返回 (summary_html, selected_model_dict, generate_md, model_id)
    """
    model_list = list(models or [])
    models_len = len(model_list)

    # 调试日志：打印事件对象（便于在不同 gradio 版本下观察）
    print("[DBG] gallery.select raw_event:", type(selected_state), repr(selected_state)[:400])
    print("[DBG] gallery.select models_len:", models_len)

    idx = getattr(selected_state, "index", None)
    print("[DBG] gallery.select idx:", idx)

    if not isinstance(idx, int) or not (0 <= idx < models_len):
        summary = "No model selected."
        return summary, None, summary, ""

    selected = model_list[idx]

    title_cn = selected.get("title_cn") or selected.get("title") or ""
    title_en = selected.get("title_en") or ""
    model_id = str(selected.get("id") or "")

    summary_md = (
        "### 当前选择模型\n\n"
        f"- 标题：{title_cn}\n"
        f"- 英文名：{title_en}\n"
        f"- ID：`{model_id}`"
    )
    gen_md = f"已选择模型：`{model_id}`"

    return summary_md, selected, gen_md, model_id
```

说明：不要在函数签名上写 `SelectData` 的类型注解（避免 get_type_hints 问题）。在实际部署后，如果 `raw_event` 打印仍然是 `list`，说明绑定方式仍然不正确，再诊断。


### C. 保证 `models_state` 与 `gallery.value` 同步

- 所有负责生成 gallery 列表的函数（如 `_models_for_dropdown`, `_refresh_and_update`）必须返回 `(ui_items, norm)`，其中 `ui_items` 为 `[(cover,title), ...]`，`norm` 为完整模型 dict 列表。
- 这些函数在 `task_dd.change`、`refresh_btn.click` 等地方一定要把 `outputs=[gallery, models_state]`。示例：

```py
def _models_for_dropdown(...):
    norm, gallery_items = sanitize_models(models)
    ui_items = [(item.get('cover'), item.get('title')) for item in gallery_items]
    return _safe_update(value=ui_items), norm
```

---

## 测试清单（手动验证）

1. 静态检查并启动

```bash
python -m py_compile app.py ui/callbacks.py
python app.py
```

2. 浏览器操作验证

- 打开页面到 Selection 标签；确认 Gallery 正常加载图片与标题；
- 点击第 1、2、3 张卡片，观察后端日志：
  - `raw_event` 应该是事件对象或包含 `.index`；
  - `idx` 应分别为 0、1、2；
  - `models_len` 应等于 models_state 的长度（例如 20）；
  - `using idx: ... id: ...` 日志应展示对应模型 id。
- 切到 Generate 页并确认 `Selected Model ID` 显示与点击的模型 id 一致；尝试发起一次生成请求，确保 `do_generate` 使用的是选中模型。

3. 如果 `raw_event` 仍然是 `list` 或 `idx` 为非 int：
- 回溯 `gallery.select` 的绑定，确保没有把 `gallery` 放到 `inputs` 列表中（那会使第一个参数变成 gallery.value）；
- 尝试显式使用 `inputs=[gr.EventData(), models_state]`，并重新观察 `raw_event` 输出；
- 如果显式 `EventData()` 也不生效，请贴出 `raw_event` 的完整 repr 供进一步诊断（通常可看到 `.index` 字段或其它有用信息）。

---

## 提交/分支建议

- 建议创建分支：`feature/gallery-select-fix`。
- 先提交 `docs/selection_logic.md`（本文件）到该分支，再逐步实现代码改动（`app.py`、`ui/callbacks.py`），每次改动都运行 `py_compile` 并手动测试。

---

## 结论

按上述原则重构后，回调将与 LoraTheExplorer 的逻辑对齐：通过 `SelectData.index` + `models_state` 实现稳定、索引驱动的模型选择，避免了字符串匹配脆弱性与 Gradio 参数注入陷阱。

如果你确认要我在代码里直接应用改动，我可以接着按 TODO 列表依次实现（我会在每一步完成后运行静态检查并报告结果）。
