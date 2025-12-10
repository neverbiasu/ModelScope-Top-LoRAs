"""Gradio read-only UI for Top-LoRAs cache."""

from pathlib import Path
import base64
import json
import os
from typing import Any, Iterable, Optional
import uuid

from top_loras import cache as tl_cache
from top_loras import fetcher as fetch_module
from top_loras.download import sanitize_filename
from ui.loaders import (
    get_cache_path,
    load_results_from_cache,
    sanitize_models,
    render_markdown_for_models,
    _tasks_from_presets,
)

try:
    import gradio as gr
except Exception:  # pragma: no cover - optional UI dependency
    gr = None


def _safe_update(**kwargs):
    if gr is None:
        return None
    return gr.update(**kwargs)


_PLACEHOLDER_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
)





def build_ui() -> None:
    if gr is None:
        print("Gradio is not installed. Run `pip install gradio` to launch the UI.")
        return

    tasks = _tasks_from_presets()
    default_task = "text-to-image-synthesis"
    if default_task in tasks:
        initial_task = default_task
    elif tasks:
        initial_task = tasks[0]
    else:
        initial_task = default_task

    cache_file = get_cache_path(initial_task, per_task_cache=True)
    initial_models = load_results_from_cache(cache_file)
    initial_norm, initial_gallery = sanitize_models(initial_models)
    # Gallery expects items like (cover, title); keep UI values as tuples
    initial_gallery_ui = [(item.get("cover"), item.get("title")) for item in initial_gallery]

    with gr.Blocks(css="body { background: #0f1117; }") as demo:
        with gr.Row(elem_id="tl-header", variant="panel"):
            gr.Markdown(
                "<div style='display:flex;align-items:center;gap:8px'>"
                "<img src='' alt='' style='width:28px;height:28px;border-radius:6px;background:#fff20;'/>"
                "<span style='font-size:18px;font-weight:700'>Top‑LoRAs</span>"
                "</div>"
            )

        with gr.Tabs():
            with gr.TabItem("Selection"):
                with gr.Row():
                    with gr.Column(scale=3):
                        task_dd = gr.Dropdown(
                            choices=tasks,
                            value=initial_task if tasks else None,
                            label="Task (select)",
                        )
                        per_task_cb = gr.Checkbox(value=True, label="Per-task cache")
                        refresh_btn = gr.Button("🔄 Refresh Cache", variant="secondary")
                        gr.Markdown(
                            "💡 **提示：** 点击 Refresh 从 ModelScope 获取最新数据并更新本地缓存。"
                        )
                        selected_md = gr.HTML("<div style='padding:12px;background:rgba(255,255,255,0.05);border-radius:8px;'><strong>已选择模型：</strong> 无</div>")
                        selected_state = gr.State(value=None)
                    with gr.Column(scale=9):
                        gallery = gr.Gallery(
                            label="Top LoRAs",
                            value=initial_gallery_ui or None,
                            columns=3,
                            show_label=False,
                            elem_id="tl_gallery",
                            height=520,
                        )
                        models_state = gr.State(value=initial_norm)

            with gr.TabItem("Generate"):
                with gr.Row():
                    with gr.Column(scale=8):
                        gen_model_info = gr.Markdown("💡 请先在 **Selection** 标签页选择一个模型")
                        # Visible field to confirm the selected model ID is propagated
                        selected_id_display = gr.Textbox(label="📋 当前选中模型 ID", value="无", interactive=False)
                        prompt = gr.Textbox(label="✨ Prompt（提示词）", placeholder="描述你想生成的图像，例如：a beautiful sunset over mountains", lines=3)
                        neg_prompt = gr.Textbox(label="🚫 Negative Prompt（负面提示词）", placeholder="不想出现的内容，例如：blurry, low quality", lines=2)
                        
                        with gr.Row():
                            size_text = gr.Textbox(label="📐 尺寸", placeholder="例如 1024x1024", scale=2)
                            steps = gr.Slider(minimum=1, maximum=150, value=20, step=1, label="🔢 Steps（步数）", scale=3)
                        
                        with gr.Row():
                            guidance = gr.Slider(minimum=1.0, maximum=30.0, value=7.5, step=0.1, label="🎯 Guidance Scale", scale=3)
                            seed = gr.Number(value=42, label="🎲 Seed（种子）", info="0=随机", scale=2)
                        
                        api_model_override = gr.Textbox(
                            label="🔧 API Model Override（高级）", 
                            placeholder="完整模型路径，例如 black-forest-labs/FLUX.1-dev",
                            info="仅在自动解析的模型 ID 不正确时使用"
                        )
                        
                        generate_btn = gr.Button("🎨 Generate Image", variant="primary", size="lg")
                        
                        gr.Markdown("---")
                        gr.Markdown("### 🔐 API 认证")
                        token_input = gr.Textbox(label="ModelScope API Token", placeholder="粘贴你的 API Token（仅本次会话有效）", type="password")
                        with gr.Row():
                            token_save = gr.Button("💾 保存 Token", variant="secondary")
                            token_clear = gr.Button("🗑️ 清除 Token", variant="secondary")
                        auth_md = gr.Markdown("**状态：** 未提供 Token（将使用模拟模式）")
                        token_state = gr.State(value=None)
                    with gr.Column(scale=4):
                        # Image starts hidden and shows only after generation
                        out_image = gr.Image(label="Output", value=None, visible=False)
                        # History gallery for all generated images
                        results_gallery = gr.Gallery(label="Generated outputs", value=None, columns=2, show_label=True, elem_id="gen_results", visible=True)
                        job_status = gr.Markdown("")
                        last_job_file = gr.Textbox(label="Job File", value="", interactive=False, visible=False)

        def _models_for_dropdown(task_value, per_task_enabled, token):
            sel = task_value or None
            cache_file = get_cache_path(sel, per_task_cache=per_task_enabled)
            models = load_results_from_cache(cache_file)
            norm, gallery_items = sanitize_models(models)
            # Gallery now expects a list of dicts with keys
            # {"cover": ..., "title": ...}. We only expose these two
            # to the UI; idx/id 仍保留在 item 中供回调使用。
            # gallery_items is list[dict]; Gallery expects (cover, title) tuples
            ui_items = [(item.get("cover"), item.get("title")) for item in gallery_items]
            return _safe_update(value=ui_items), norm

        task_dd.change(
            fn=_models_for_dropdown,
            inputs=[task_dd, per_task_cb, token_state],
            outputs=[gallery, models_state],
        )

        def _refresh_cache(task_value, per_task_enabled, token):
            if token:
                os.environ["MODELSCOPE_API_TOKEN"] = token
            try:
                results = fetch_module.fetch_top_loras(
                    force_refresh=True,
                    task=task_value,
                    per_task_cache=per_task_enabled,
                    download_images=True,
                    debug=False,
                )
            except Exception as exc:  # pragma: no cover - UI message only
                return f"<div class='empty'>Refresh failed: {exc}</div>"
            return render_markdown_for_models(results)

        def _refresh_and_update(task_value, per_task_enabled, token):
            _refresh_cache(task_value, per_task_enabled, token)
            sel = task_value or None
            cache_file = get_cache_path(sel, per_task_cache=per_task_enabled)
            models = load_results_from_cache(cache_file)
            norm, gallery_items = sanitize_models(models)
            ui_items = [(item.get("cover"), item.get("title")) for item in gallery_items]
            return _safe_update(value=ui_items), norm

        refresh_btn.click(
            fn=_refresh_and_update,
            inputs=[task_dd, per_task_cb, token_state],
            outputs=[gallery, models_state],
        )

        def _load_initial():
            return initial_gallery_ui

        demo.load(fn=_load_initial, inputs=None, outputs=gallery)

        def _save_token(token, _state):
            if not token or not token.strip():
                return "**状态：** ❌ Token 为空，未保存", None
            return "**状态：** ✅ Token 已保存（仅本次会话有效）", token.strip()

        def _clear_token(_state):
            return "**状态：** 未提供 Token（将使用模拟模式）", None

        token_save.click(fn=_save_token, inputs=[token_input, token_state], outputs=[auth_md, token_state])
        token_clear.click(fn=_clear_token, inputs=[token_state], outputs=[auth_md, token_state])

        from top_loras.inference import submit_job
        from ui.callbacks import on_gallery_select, do_generate

        # Gradio pattern: SelectData is auto-injected as first parameter,
        # followed by inputs list. We pass models_state to enable index lookup.
        gallery.select(
            fn=on_gallery_select,
            inputs=[models_state],
            outputs=[selected_md, selected_state, gen_model_info, selected_id_display],
        )

        generate_btn.click(
            fn=do_generate,
            inputs=[selected_state, selected_id_display, prompt, neg_prompt, size_text, steps, guidance, seed, api_model_override, token_state],
            outputs=[out_image, job_status, last_job_file, results_gallery],
        )

        demo.launch()


if __name__ == "__main__":
    build_ui()
