"""UI callbacks for Top‑LoRAs Gradio app."""

from __future__ import annotations

from typing import Iterable, Any, Optional
import os
from pathlib import Path
from base64 import b64decode
import uuid

try:
    from gradio.events import SelectData as _SelectData
except ImportError:  # pragma: no cover - optional runtime dependency
    _SelectData = None

if _SelectData is None:  # pragma: no cover - fallback stub used only if Gradio is absent
    class SelectData:  # type: ignore[no-redef]
        pass
else:
    SelectData = _SelectData

try:
    import gradio as gr
except Exception:  # pragma: no cover - optional UI dependency
    gr = None

from top_loras.inference import submit_job

# Import SelectData for type hint - this is how Gradio 5 injects event data
if gr is not None:
    SelectData = gr.SelectData
else:
    SelectData = None

# Module-level cache so the app can keep a current copy of models_state.
_CACHED_MODELS: list[dict] = []


def set_models_cache(models: list[dict] | None) -> None:
    """Update the module-level models cache from `app.py`.

    The UI will call this whenever it refreshes the model list so
    `on_gallery_select` can reliably look up full model metadata.
    """
    global _CACHED_MODELS
    _CACHED_MODELS = list(models or [])


def on_gallery_select(evt: "gr.SelectData"):
    """Handle gallery selection using Gradio 5's SelectData event.

    When using type hint `gr.SelectData`, Gradio automatically passes:
      - evt.index: int index of the clicked item
      - evt.value: the value of the clicked item (cover, title) tuple
    """
    global _CACHED_MODELS
    model_list = _CACHED_MODELS
    models_len = len(model_list)

    idx = evt.index

    # Validate index
    if not isinstance(idx, int) or idx < 0 or idx >= models_len:
        return "No model selected.", None, "No model selected", ""

    selected = model_list[idx]

    title = selected.get("title_en") or selected.get("title") or selected.get("title_cn") or ""
    model_id = str(selected.get("id") or "")
    author = selected.get("author") or ""
    downloads = selected.get("downloads") or 0
    likes = selected.get("likes") or 0

    summary_html = f"""
<div style="padding: 12px; border-radius: 8px; background: #1a1a2e;">
    <h3 style="margin: 0 0 8px 0; color: #fff;">Selected Model</h3>
    <p style="margin: 4px 0; color: #ccc;"><strong>Name:</strong> {title}</p>
    <p style="margin: 4px 0; color: #ccc;"><strong>Author:</strong> {author}</p>
    <p style="margin: 4px 0; color: #888;">Downloads: {downloads} · Likes: {likes}</p>
</div>
"""
    gen_md = f"Selected: {title}"

    return summary_html, selected, gen_md, model_id


def do_generate(model, model_id, prompt_text, neg_text, size_v, steps_v, guidance_v, seed_v, api_model, token):
    # Default updates: do NOT use a placeholder image value — leave image empty/hidden
    default_img_update = gr.update(value=None, visible=False) if gr else None
    default_gallery_update = gr.update(value=None, visible=False) if gr else None

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
        tail = url.split(marker, 1)[-1]
        tail = tail.split("?", 1)[0].strip("/")
        parts = tail.split("/")
        if len(parts) >= 2:
            candidate = parts[0] + "/" + parts[1]
            return candidate
        return None

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
    params = {k: v for k, v in params.items() if v is not None}

    effective_token = token or os.environ.get("MODELSCOPE_API_TOKEN")
    try:
        job = submit_job(effective_model, params, token=effective_token)
    except Exception as exc:
        status_md = f"**Job:** failed to submit  \n**Error:** {exc}"
        return default_img_update, status_md, "", default_gallery_update

    result = job.get("result") or {}

    imgs = []
    try:
        if isinstance(result, dict):
            images_field = result.get("images")
            if isinstance(images_field, (list, tuple)):
                imgs = [i for i in images_field if isinstance(i, str)]
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

    img = imgs[0] if imgs else None

    if isinstance(img, str) and img.startswith("data:"):
        imgs[0] = img

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
        gallery_update = gr.update(value=imgs, visible=True) if gr else None
        if isinstance(img, str) and img.startswith("data:"):
            img_exists = True
        elif isinstance(img, str) and Path(str(img)).exists():
            img_exists = True
        else:
            img_exists = False
        img_update = gr.update(value=img if img_exists else (img if isinstance(img, str) and img.startswith("http") else None), visible=bool(img)) if gr else None
    else:
        status_md += "  \n_No image returned; using empty state_"
        gallery_update = default_gallery_update
        img_update = default_img_update

    return img_update, status_md, job.get("meta", {}).get("job_id", ""), gallery_update
