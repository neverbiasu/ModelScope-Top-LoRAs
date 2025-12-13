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
    load_generated_images,
)
from ui.i18n import t

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
    initial_history = load_generated_images(initial_task, limit=40)

    with gr.Blocks(
        fill_width=True,
        css=(
            "body { background: #0f1117; }\n"
            "body .gradio-container { max-width: none !important; width: 100% !important; margin: 0 auto; padding: 20px; }\n"
            "body .gradio-container .container { max-width: none !important; width: 100% !important; }\n"
            "body .gradio-container .wrap { max-width: none !important; width: 100% !important; }\n"
            "#tl-header { gap: 12px; }\n"
            "#tl_gallery { min-height: 600px; }\n"
            "@media (min-width: 1400px) { body .gradio-container { padding: 20px 60px; } }\n"
        ),
    ) as demo:
        # Language state (default to Chinese)
        lang_state = gr.State(value="zh")
        
        with gr.Row(elem_id="tl-header", variant="panel"):
            gr.Markdown("<div style='font-size:18px;font-weight:700'>Top‑LoRAs</div>")
            with gr.Column(scale=1):
                lang_dropdown = gr.Dropdown(
                    choices=["中文", "English"], 
                    value="中文",
                    label=None,
                    show_label=False,
                    scale=1
                )

        with gr.Tabs():
            with gr.TabItem(label="Selection / 选择"):
                with gr.Row():
                    with gr.Column(scale=2, min_width=250):
                        task_dd = gr.Dropdown(
                            choices=tasks,
                            value=initial_task if tasks else None,
                            label=t("task_label", "zh"),
                        )
                        per_task_cb = gr.Checkbox(value=True, label=t("per_task_cache", "zh"))
                        refresh_btn = gr.Button(t("refresh_btn", "zh"), variant="secondary")
                        refresh_hint_md = gr.Markdown(t("refresh_hint", "zh"))
                        selected_md = gr.HTML(f"<div style='padding:12px;background:rgba(255,255,255,0.05);border-radius:8px;'><strong>{t('selected_model', 'zh')}</strong> {t('no_model', 'zh')}</div>")
                        selected_state = gr.State(value=None)
                    with gr.Column(scale=10):
                        gallery = gr.Gallery(
                            label=t("top_loras", "zh"),
                            value=initial_gallery_ui or None,
                            columns=5,
                            show_label=False,
                            elem_id="tl_gallery",
                            height=600,
                        )
                        models_state = gr.State(value=initial_norm)

            with gr.TabItem(label="Generate / 生成"):
                with gr.Row():
                    with gr.Column(scale=7, min_width=400):
                        gen_model_info = gr.Markdown(t("select_first", "zh"))
                        # Visible field to confirm the selected model ID is propagated
                        selected_id_display = gr.Textbox(label=t("model_id_label", "zh"), value=t("no_model", "zh"), interactive=False)
                        prompt = gr.Textbox(label=t("prompt_label", "zh"), placeholder=t("prompt_placeholder", "zh"), lines=3)
                        neg_prompt = gr.Textbox(label=t("neg_prompt_label", "zh"), placeholder=t("neg_prompt_placeholder", "zh"), lines=2)
                        
                        with gr.Row():
                            size_text = gr.Textbox(
                                label=t("size_label", "zh"),
                                placeholder=t("size_placeholder", "zh"),
                                value="1024x1024",
                                scale=2,
                            )
                            steps = gr.Slider(minimum=1, maximum=150, value=20, step=1, label=t("steps_label", "zh"), scale=3)
                        
                        with gr.Row():
                            guidance = gr.Slider(minimum=1.0, maximum=30.0, value=7.5, step=0.1, label=t("guidance_label", "zh"), scale=3)
                            seed = gr.Number(value=42, label=t("seed_label", "zh"), scale=2)
                        seed_info_md = gr.Markdown(t("seed_info", "zh"))
                        
                        api_model_override = gr.Textbox(
                            label=t("api_model_label", "zh"), 
                            placeholder=t("api_model_placeholder", "zh"),
                        )
                        api_model_info_md = gr.Markdown(t("api_model_info", "zh"))
                        
                        generate_btn = gr.Button(t("generate_btn", "zh"), variant="primary", size="lg")
                        
                        gr.Markdown("---")
                        auth_title_md = gr.Markdown(t("auth_title", "zh"))
                        token_input = gr.Textbox(label=t("token_label", "zh"), placeholder=t("token_placeholder", "zh"), type="password")
                        with gr.Row():
                            token_save = gr.Button(t("token_save", "zh"), variant="secondary")
                            token_clear = gr.Button(t("token_clear", "zh"), variant="secondary")
                        auth_md = gr.Markdown(t("token_status_default", "zh"))
                        token_state = gr.State(value=None)
                    with gr.Column(scale=5, min_width=350):
                        # Image starts hidden and shows only after generation
                        out_image = gr.Image(label=t("output_label", "zh"), value=None, visible=False)
                        # History gallery for all generated images
                        results_gallery = gr.Gallery(label=t("results_label", "zh"), value=initial_history or None, columns=2, show_label=True, elem_id="gen_results", visible=True)
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
            history = load_generated_images(sel or "", limit=40)
            return _safe_update(value=ui_items), norm, _safe_update(value=history or None)

        task_dd.change(
            fn=_models_for_dropdown,
            inputs=[task_dd, per_task_cb, token_state],
            outputs=[gallery, models_state, results_gallery],
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
            history = load_generated_images(sel or "", limit=40)
            return _safe_update(value=ui_items), norm, _safe_update(value=history or None)

        refresh_btn.click(
            fn=_refresh_and_update,
            inputs=[task_dd, per_task_cb, token_state],
            outputs=[gallery, models_state, results_gallery],
        )

        def _load_initial():
            return initial_gallery_ui

        demo.load(fn=_load_initial, inputs=None, outputs=[gallery])

        def _on_lang_change(lang_choice):
            from ui.i18n import t
            if gr is None:
                return [None] * 25
            lang_code = "zh" if lang_choice == "中文" else "en"
            return (
                gr.update(label=t("task_label", lang_code)),
                gr.update(label=t("per_task_cache", lang_code)),
                gr.update(value=t("refresh_btn", lang_code)),
                gr.update(value=t("refresh_hint", lang_code)),
                gr.update(label=t("top_loras", lang_code)),
                gr.update(value=t("select_first", lang_code)),
                gr.update(label=t("model_id_label", lang_code)),
                gr.update(label=t("prompt_label", lang_code), placeholder=t("prompt_placeholder", lang_code)),
                gr.update(label=t("neg_prompt_label", lang_code), placeholder=t("neg_prompt_placeholder", lang_code)),
                gr.update(label=t("size_label", lang_code), placeholder=t("size_placeholder", lang_code)),
                gr.update(label=t("steps_label", lang_code)),
                gr.update(label=t("guidance_label", lang_code)),
                gr.update(label=t("seed_label", lang_code)),
                gr.update(value=t("seed_info", lang_code)),
                gr.update(label=t("api_model_label", lang_code), placeholder=t("api_model_placeholder", lang_code)),
                gr.update(value=t("api_model_info", lang_code)),
                gr.update(value=t("generate_btn", lang_code)),
                gr.update(value=t("auth_title", lang_code)),
                gr.update(label=t("token_label", lang_code), placeholder=t("token_placeholder", lang_code)),
                gr.update(value=t("token_save", lang_code)),
                gr.update(value=t("token_clear", lang_code)),
                gr.update(value=t("token_status_default", lang_code)),
                gr.update(label=t("output_label", lang_code)),
                gr.update(label=t("results_label", lang_code)),
                lang_code,
            )

        lang_dropdown.change(
            fn=_on_lang_change,
            inputs=[lang_dropdown],
            outputs=[
                task_dd,
                per_task_cb,
                refresh_btn,
                refresh_hint_md,
                gallery,
                gen_model_info,
                selected_id_display,
                prompt,
                neg_prompt,
                size_text,
                steps,
                guidance,
                seed,
                seed_info_md,
                api_model_override,
                api_model_info_md,
                generate_btn,
                auth_title_md,
                token_input,
                token_save,
                token_clear,
                auth_md,
                out_image,
                results_gallery,
                lang_state,
            ],
        )

        def _save_token(token, _state, lang):
            from ui.i18n import t
            lang_code = lang if lang in ("zh", "en") else "zh"
            if not token or not str(token).strip():
                return t("token_status_empty", lang_code), None
            raw = str(token).strip().strip('"').strip("'")
            if raw.lower().startswith("bearer "):
                raw = raw.split(None, 1)[-1].strip()
            if not raw:
                return t("token_status_empty", lang_code), None
            os.environ["MODELSCOPE_API_TOKEN"] = raw
            return t("token_status_saved", lang_code), raw

        def _clear_token(_state, lang):
            from ui.i18n import t
            lang_code = lang if lang in ("zh", "en") else "zh"
            return t("token_status_cleared", lang_code), None

        token_save.click(fn=_save_token, inputs=[token_input, token_state, lang_state], outputs=[auth_md, token_state])
        token_input.submit(fn=_save_token, inputs=[token_input, token_state, lang_state], outputs=[auth_md, token_state])
        token_clear.click(fn=_clear_token, inputs=[token_state, lang_state], outputs=[auth_md, token_state])

        from top_loras.inference import submit_job
        from ui.callbacks import on_gallery_select, do_generate

        # SelectData is auto-injected by Gradio when callback param is annotated.
        from gradio import SelectData

        def _on_gallery_select(evt: SelectData, models, lang):
            return on_gallery_select(evt, models, lang=lang)

        gallery.select(
            fn=_on_gallery_select,
            inputs=[models_state, lang_state],
            outputs=[selected_md, selected_state, gen_model_info, selected_id_display],
        )

        generate_btn.click(
            fn=do_generate,
            inputs=[selected_state, selected_id_display, prompt, neg_prompt, size_text, steps, guidance, seed, api_model_override, token_state, lang_state],
            outputs=[out_image, job_status, last_job_file, results_gallery],
        )

        demo.launch()


if __name__ == "__main__":
    build_ui()
