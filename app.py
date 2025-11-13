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
                            value=initial_gallery or None,
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
            return gr.update(value=gallery_items), norm

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
            return gr.update(value=gallery_items), norm

        refresh_btn.click(
            fn=_refresh_and_update,
            inputs=[task_dd, per_task_cb, token_state],
            outputs=[gallery, models_state],
        )

        def _load_initial():
            return initial_gallery

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

        def _on_gallery_select(evt, models=None, **kwargs):
            # Accept kwargs to be tolerant of extra arguments Gradio may pass
            models = models or []
            # Log the full event payload (trimmed to 1000 chars to avoid huge dumps)
            evt_repr = repr(evt)
            print(f"[DBG] gallery.select evt type: {type(evt).__name__} evt repr: {evt_repr[:1000]}")

            def find_by_id(identifier):
                for item in models:
                    if str(item.get("id")) == str(identifier):
                        return item
                return None

            def find_by_title(name):
                for item in models:
                    if str(item.get("title")) == str(name):
                        return item
                return None

            def find_by_cover(uri):
                for item in models:
                    if item.get("cover") == uri or item.get("cover_local") == uri or item.get("cover_url") == uri:
                        return item
                return None

            def match_candidate(candidate):
                if candidate is None:
                    return None
                if isinstance(candidate, dict):
                    # If the candidate already looks like a full model dict (contains id + metadata),
                    # accept it directly rather than requiring it to be found in `models`.
                    if candidate.get("id") and any(
                        k in candidate for k in ("downloads", "likes", "author", "modelscope_url", "cover_url", "cover_local")
                    ):
                        return candidate

                    # Otherwise try matching by common identifier keys (id/model_id/value)
                    for key in ("id", "model_id", "value"):
                        if candidate.get(key) is not None:
                            match = find_by_id(candidate.get(key))
                            if match:
                                return match

                    # Try matching by title-like keys
                    for key in ("title", "caption", "label"):
                        if candidate.get(key):
                            match = find_by_title(candidate.get(key))
                            if match:
                                return match

                    # Try matching by cover/image uri
                    cover = candidate.get("cover") or candidate.get("image") or candidate.get("src") or candidate.get("cover_url") or candidate.get("cover_local")
                    if cover:
                        found = find_by_cover(cover)
                        if found:
                            return found

                    return None
                if isinstance(candidate, int):
                    if 0 <= candidate < len(models):
                        return models[candidate]
                    return None
                if isinstance(candidate, str):
                    if candidate.isdigit():
                        idx = int(candidate)
                        if 0 <= idx < len(models):
                            return models[idx]
                    match = find_by_id(candidate)
                    if match:
                        return match
                    return find_by_title(candidate)
                if isinstance(candidate, (list, tuple)):
                    for item in candidate:
                        match = match_candidate(item)
                        if match:
                            return match
                    return None
                if hasattr(candidate, "value"):
                    return match_candidate(getattr(candidate, "value"))
                if hasattr(candidate, "index"):
                    try:
                        idx = int(getattr(candidate, "index"))
                    except Exception:
                        idx = None
                    if idx is not None and 0 <= idx < len(models):
                        return models[idx]
                return None

            candidates = [evt]
            if hasattr(evt, "value"):
                candidates.append(getattr(evt, "value"))
            if hasattr(evt, "data"):
                candidates.append(getattr(evt, "data"))
            if hasattr(evt, "index"):
                candidates.append(getattr(evt, "index"))

            selected = None
            for candidate in candidates:
                selected = match_candidate(candidate)
                if selected:
                    break

            if not selected:
                # Ensure we always return 4 outputs: html, state, markdown, selected_id
                print("[DBG] No matching model found for candidates:\n", candidates[:3])
                return "<div><strong>Selected model:</strong> None</div>", None, "No model selected", ""

            title = (
                selected.get("title_cn")
                or selected.get("title_en")
                or selected.get("title")
                or selected.get("id")
                or "Unknown model"
            )

            summary_html = (
                f"<div><strong>Selected model:</strong> {title}</div>"
                f"<div style='margin-top:8px; font-size:13px; color:#a6adc8'>ID: {selected.get('id')} · "
                f"Author: {selected.get('author')} · Downloads: {selected.get('downloads')} · "
                f"Likes: {selected.get('likes')}</div>"
            )

            generate_md = (
                f"### {title}\n\n"
                f"- **ID:** {selected.get('id')}  \n"
                f"- **Author:** {selected.get('author')}  \n"
                f"- **Downloads:** {selected.get('downloads')}  \n"
                f"- **Likes:** {selected.get('likes')}  \n"
                f"- **Updated:** {selected.get('updated_at') or ''}  \n"
                f"- **URL:** [{selected.get('modelscope_url')}]({selected.get('modelscope_url')})"
            )

            canonical = find_by_id(selected.get("id")) or selected

            print(f"[DBG] Matched selected id: {selected.get('id')} -> canonical id: {canonical.get('id')}")

            # return (selected_md_html, selected_state_obj, generate_md, selected_id_str)
            return summary_html, canonical, generate_md, str(canonical.get("id"))

        gallery.select(
            fn=_on_gallery_select,
            inputs=[models_state],
            outputs=[selected_md, selected_state, gen_model_info, selected_id_display],
            queue=False,
        )

        def _do_generate(model, model_id, prompt_text, neg_text, size_v, steps_v, guidance_v, seed_v, api_model, token):
            """Submit a job and return UI updates: (out_image_update, status_md, job_file, gallery_update).

            This function is defensive: it always returns 4 outputs and uses a placeholder image
            when no real image is available.
            """
            # Default updates: do NOT use a placeholder image value — leave image empty/hidden
            default_img_update = gr.update(value=None, visible=False)
            default_gallery_update = gr.update(value=None, visible=False)

            print("[DBG] _do_generate invoked model_id=", model_id, "prompt=", (prompt_text or "")[:60], "steps=", steps_v, "guidance=", guidance_v, "seed=", seed_v, "token?", bool(token))

            if not model_id or model_id == "None":
                return default_img_update, "No model selected", "", default_gallery_update

            def _derive_from_url(m: dict | None) -> str | None:
                if not isinstance(m, dict):
                    return None
                url = m.get("modelscope_url") or m.get("url")
                if not isinstance(url, str):
                    return None
                marker = "/models/"
                if marker not in url:
                    return None
                # Extract path after /models/
                tail = url.split(marker, 1)[-1]
                # Remove query and trailing fragments
                tail = tail.split("?", 1)[0].strip("/")
                # Expect org/name[/...] -> we take first two segments as canonical ID
                parts = tail.split("/")
                if len(parts) >= 2:
                    candidate = parts[0] + "/" + parts[1]
                    return candidate
                return None

            # Determine effective model id for API: UI override > explicit api_model key > derived from modelscope_url > selected_id
            effective_model = None
            try:
                if api_model:
                    effective_model = str(api_model).strip()
                elif isinstance(model, dict) and model.get("api_model"):
                    effective_model = str(model.get("api_model")).strip()
                if not effective_model:
                    derived = _derive_from_url(model if isinstance(model, dict) else None)
                    effective_model = derived
            except Exception:
                effective_model = None
            effective_model = (effective_model or model_id or "").strip()

            # Auto-warn if effective_model seems incomplete (no slash)
            incomplete = "/" not in effective_model

            params = {
                "task": "text-to-image-synthesis",
                "prompt": prompt_text or "",
                "negative_prompt": (neg_text or "") if neg_text else None,
                "size": (size_v or "").strip() if size_v else None,
                "steps": int(steps_v),
                "guidance": float(guidance_v),
                "seed": int(seed_v or 0),
            }
            # Remove Nones from params
            params = {k: v for k, v in params.items() if v is not None}

            # Allow falling back to environment variable if token not saved in session state
            effective_token = token or os.environ.get("MODELSCOPE_API_TOKEN")
            try:
                job = submit_job(effective_model, params, token=effective_token)
            except Exception as exc:  # pragma: no cover - runtime robustness
                status_md = f"**Job:** failed to submit  \n**Error:** {exc}"
                return default_img_update, status_md, "", default_gallery_update

            result = job.get("result") or {}

            # Debug print job structure
            try:
                print("[DBG] job keys=", list(job.keys()))
                print("[DBG] job.meta=", job.get("meta"))
                print("[DBG] job.status=", job.get("status"), "remote=", job.get("remote"), "error=", job.get("error"))
                if isinstance(result, dict):
                    print("[DBG] result keys=", list(result.keys()))
                else:
                    print("[DBG] result type=", type(result), "repr=", repr(result)[:120])
            except Exception as _dbg_exc:  # pragma: no cover
                print("[DBG] logging error:", _dbg_exc)

            # Normalize possible result shapes into a list of image URIs
            imgs = []
            try:
                if isinstance(result, dict):
                    if isinstance(result.get("images"), (list, tuple)):
                        imgs = [i for i in result.get("images") if isinstance(i, str)]
                    elif isinstance(result.get("image"), str):
                        imgs = [result.get("image")]
                    else:
                        for v in result.values():
                            if isinstance(v, str) and v.startswith("data:"):
                                imgs.append(v)
                                break
                elif isinstance(result, (list, tuple)):
                    imgs = [i for i in result if isinstance(i, str)]
            except Exception:
                imgs = []

            print("[DBG] parsed imgs count=", len(imgs))

            img = imgs[0] if imgs else None

            # Do NOT persist generated images or JSON to disk from the UI.
            # Keep data URIs or remote URLs as-is and let Gradio display them directly.
            # This avoids writing generated outputs into `cache/outputs`.
            if isinstance(img, str) and img.startswith("data:"):
                # keep data URI directly
                imgs[0] = img
            # otherwise, if img is a path/URL string, leave as-is but do not write new files

            status_md = (
                f"**Job:** {job.get('meta', {}).get('job_id', '')}  \n"
                f"**Status:** {job.get('status')}  \n"
                f"**Remote:** {job.get('remote')}  \n"
                f"**API Model:** {effective_model}"
            )
            if incomplete:
                status_md += "  \n⚠️ 推理模型ID可能不完整（缺少组织前缀），已尝试自动从 URL 解析。如仍 400，请在 API Model Override 输入完整形式例如 org/name。"
            if job.get('mock'):
                status_md += "  \n_Mode: mock (no token detected)_"
            if job.get('error'):
                status_md += f"  \n**Error:** {job.get('error')}"

            if imgs:
                gallery_update = gr.update(value=imgs, visible=True)
                # Consider data URIs and existing file paths as displayable
                if isinstance(img, str) and img.startswith("data:"):
                    img_exists = True
                elif isinstance(img, str) and Path(str(img)).exists():
                    img_exists = True
                else:
                    img_exists = False
                if img_exists:
                    print("[DBG] image available for display:", img)
                else:
                    print("[DBG] image not available as path; may be remote URL or invalid:", img)
                img_update = gr.update(value=img if img_exists else (img if isinstance(img, str) and img.startswith("http") else None), visible=bool(img))
            else:
                status_md += "  \n_No image returned; using empty state_"
                gallery_update = default_gallery_update
                img_update = default_img_update

            # Do not return or rely on a persisted job file path from the UI
            return img_update, status_md, job.get("meta", {}).get("job_id", ""), gallery_update

        generate_btn.click(
            fn=_do_generate,
            inputs=[selected_state, selected_id_display, prompt, neg_prompt, size_text, steps, guidance, seed, api_model_override, token_state],
            outputs=[out_image, job_status, last_job_file, results_gallery],
        )

        demo.launch()


if __name__ == "__main__":
    build_ui()
