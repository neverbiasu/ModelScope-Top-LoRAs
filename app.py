"""Gradio read-only UI for Top-LoRAs cache."""

from pathlib import Path
import base64
import json
import os
from typing import Any, Iterable, Optional
import uuid

from top_loras import cache as tl_cache
import fetch_top_models as fetch_module
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
                        refresh_btn = gr.Button("Refresh Cache")
                        gr.Markdown(
                            "Refresh fetches the selected task from ModelScope, updates the "
                            "local cache, and downloads covers when available."
                        )
                        selected_md = gr.HTML("<div><strong>Selected model:</strong> None</div>")
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
                        gen_model_info = gr.Markdown("No model selected")
                        # Visible field to confirm the selected model ID is propagated
                        selected_id_display = gr.Textbox(label="Selected Model ID", value="None", interactive=False)
                        prompt = gr.Textbox(label="Prompt", placeholder="Describe the image to generate")
                        neg_prompt = gr.Textbox(label="Negative Prompt", placeholder="Optional negative prompt")
                        size_text = gr.Textbox(label="Size (e.g., 1024x1024)", placeholder="Optional size like 1024x1024")
                        steps = gr.Slider(minimum=1, maximum=150, value=20, step=1, label="Steps")
                        guidance = gr.Slider(minimum=1.0, maximum=30.0, value=7.5, step=0.1, label="Guidance Scale")
                        seed = gr.Number(value=42, label="Seed (0=random)")
                        api_model_override = gr.Textbox(label="API Model (override)", placeholder="e.g. black-forest-labs/FLUX.1-Krea-dev")
                        generate_btn = gr.Button("Generate")
                        token_input = gr.Textbox(label="ModelScope API Token", placeholder="Paste token here (session)", type="password")
                        token_save = gr.Button("Save Token")
                        token_clear = gr.Button("Clear Token")
                        auth_md = gr.Markdown("**Auth:** Not provided")
                        token_state = gr.State(value=None)
                    with gr.Column(scale=4):
                        # Keep the image component visible but do NOT pre-fill it with a placeholder value
                        out_image = gr.Image(label="Output", value=None, visible=True)
                        # A small gallery/history area to show generated outputs (persisted)
                        results_gallery = gr.Gallery(label="Generated outputs", value=None, columns=2, show_label=True, elem_id="gen_results", visible=False)
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
            if not token:
                return "**Auth:** Not provided", None
            return "**Auth:** Token saved (session only)", token

        def _clear_token(_state):
            return "**Auth:** Not provided", None

        token_save.click(fn=_save_token, inputs=[token_input, token_state], outputs=[auth_md, token_state])
        token_clear.click(fn=_clear_token, inputs=[token_state], outputs=[auth_md, token_state])

        from top_loras.inference import submit_job
        from ui.callbacks import on_gallery_select, do_generate

        # When a gallery item is selected, Gradio passes the selected
        # item value, which we configured as [cover, title]. We only use
        # the title here to look up the full model from models_state.
        gallery.select(
            fn=on_gallery_select,
            inputs=[models_state],
            outputs=[selected_md, selected_state, gen_model_info, selected_id_display],
            queue=False,
        )

        generate_btn.click(
            fn=do_generate,
            inputs=[selected_state, selected_id_display, prompt, neg_prompt, size_text, steps, guidance, seed, api_model_override, token_state],
            outputs=[out_image, job_status, last_job_file, results_gallery],
        )

        demo.launch()


if __name__ == "__main__":
    build_ui()
