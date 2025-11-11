"""Gradio read-only UI for Top-LoRAs cache."""

from pathlib import Path
import json
import os
from typing import Any, Iterable, Optional

from top_loras import cache as tl_cache
import fetch_top_models as fetch_module
from top_loras.download import sanitize_filename

try:
    import gradio as gr
except Exception:  # pragma: no cover - optional UI dependency
    gr = None


_PLACEHOLDER_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
)


def get_cache_path(task: Optional[str], per_task_cache: bool = True) -> str:
    default = fetch_module.DEFAULT_CACHE_FILE
    if per_task_cache and task:
        safe = sanitize_filename(task)
        return f"cache/top_loras_{safe}.json"
    return default


def load_results_from_cache(cache_file: str) -> list[dict[str, Any]]:
    try:
        results = tl_cache.load_cache(cache_file, ttl=60 * 60 * 24 * 365)
        return results or []
    except Exception:
        path = Path(cache_file)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        results = data.get("results")
        return results or []


def _resolve_cover_uri(raw_cover: Optional[str]) -> Optional[str]:
    if not raw_cover:
        return None
    candidate = Path(raw_cover)
    if candidate.exists():
        return str(candidate)
    return raw_cover


def sanitize_models(models: Iterable[dict[str, Any]] | None) -> tuple[list[dict[str, Any]], list[tuple[Optional[str], str]]]:
    normalized: list[dict[str, Any]] = []
    gallery_items: list[tuple[Optional[str], str]] = []

    for idx, model in enumerate(models or []):
        if not isinstance(model, dict):
            continue

        cover_uri = _resolve_cover_uri(
            model.get("cover_local")
            or model.get("cover")
            or model.get("cover_url")
        )

        title = (
            model.get("title_cn")
            or model.get("title_en")
            or model.get("title")
            or model.get("id")
            or f"Model {idx + 1}"
        )

        normalized_model = {
            **model,
            "title": title,
            "cover": cover_uri,
        }

        normalized.append(normalized_model)
        gallery_items.append((cover_uri or _PLACEHOLDER_DATA_URI, title))

    return normalized, gallery_items


def render_markdown_for_models(models: Iterable[dict[str, Any]] | None) -> str:
    if not models:
        return "<div class='empty'>No cached results found. Try <b>Refresh</b> to fetch data.</div>"

    cards: list[str] = []

    for model in models:
        if not isinstance(model, dict):
            continue

        title = (
            model.get("title_cn")
            or model.get("title_en")
            or model.get("title")
            or model.get("id")
            or "Unknown model"
        )
        cover_uri = (
            _resolve_cover_uri(model.get("cover"))
            or _resolve_cover_uri(model.get("cover_local"))
            or _resolve_cover_uri(model.get("cover_url"))
        )
        author = model.get("author") or "Unknown"
        downloads = model.get("downloads") or 0
        likes = model.get("likes") or 0
        description = model.get("description") or ""

        if cover_uri:
            image_html = f"<img src='{cover_uri}' alt='{title}' loading='lazy'/>"
        else:
            image_html = "<div class='card-placeholder'>No cover</div>"

        truncated_desc = description[:160]
        if description and len(description) > 160:
            truncated_desc += "…"

        cards.append(
            """
            <div class='tl-card'>
                <div class='tl-card-image'>%s</div>
                <div class='tl-card-body'>
                    <div class='tl-card-title'>%s</div>
                    <div class='tl-card-meta'>
                        <span>ID: %s</span>
                        <span>Author: %s</span>
                    </div>
                    <div class='tl-card-stats'>
                        <span>Downloads: %s</span>
                        <span>Likes: %s</span>
                    </div>
                    <div class='tl-card-desc'>%s</div>
                </div>
            </div>
            """
            % (
                image_html,
                title,
                model.get("id", "n/a"),
                author,
                downloads,
                likes,
                truncated_desc,
            )
        )

    css = """
<style>
body { background-color: #111322; color: #d9e0ee; font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
.tl-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-top: 12px; }
.tl-card { background: rgba(255,255,255,0.04); border-radius: 16px; overflow: hidden; border: 1px solid rgba(255,255,255,0.04); display: flex; flex-direction: column; min-height: 320px; }
.tl-card-image { position: relative; width: 100%; padding-top: 62%; background: rgba(255,255,255,0.06); }
.tl-card-image img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.card-placeholder { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 12px; color: rgba(255,255,255,0.5); }
.tl-card-body { padding: 14px 16px 18px; display: flex; flex-direction: column; gap: 8px; }
.tl-card-title { font-size: 15px; font-weight: 600; line-height: 1.3; color: #f8f8f2; }
.tl-card-meta, .tl-card-stats { display: flex; gap: 12px; font-size: 12px; color: rgba(231,229,250,0.78); }
.tl-card-desc { font-size: 12px; line-height: 1.4; color: rgba(231,229,250,0.65); }
.empty { padding: 42px; text-align: center; border: 1px dashed rgba(255,255,255,0.12); border-radius: 16px; background: rgba(255,255,255,0.03); }
</style>
"""

    body = """
<div class='tl-grid'>
%s
</div>
""" % ("\n".join(cards))

    return css + body


def _tasks_from_presets() -> list[str]:
    try:
        presets = fetch_module.TASK_PRESETS
    except Exception:
        return []

    if isinstance(presets, dict):
        values = list(presets.values())
        return values or list(presets.keys())

    try:
        return list(presets)  # type: ignore[arg-type]
    except TypeError:
        return []


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
                        steps = gr.Slider(minimum=1, maximum=150, value=20, step=1, label="Steps")
                        guidance = gr.Slider(minimum=1.0, maximum=30.0, value=7.5, step=0.1, label="Guidance Scale")
                        seed = gr.Number(value=42, label="Seed (0=random)")
                        generate_btn = gr.Button("Generate")
                        token_input = gr.Textbox(label="ModelScope API Token", placeholder="Paste token here (session)", type="password")
                        token_save = gr.Button("Save Token")
                        token_clear = gr.Button("Clear Token")
                        auth_md = gr.Markdown("**Auth:** Not provided")
                        token_state = gr.State(value=None)
                    with gr.Column(scale=4):
                        out_image = gr.Image(label="Output", visible=False)
                        job_status = gr.Markdown("")

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

        demo.launch()


if __name__ == "__main__":
    build_ui()
