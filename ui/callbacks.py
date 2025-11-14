"""UI callbacks for Top‑LoRAs Gradio app."""

from __future__ import annotations

from typing import Iterable, Any
import os
from pathlib import Path
from base64 import b64decode
import uuid

try:
    import gradio as gr
except Exception:  # pragma: no cover - optional UI dependency
    gr = None

from top_loras.inference import submit_job


def on_gallery_select(evt: Any = None, models: Iterable[dict[str, Any]] | None = None, **kwargs):
    """Handle gallery selection and return model details.

    ``SelectData`` exposes ``index`` and ``value``, so we can map the
    selected card directly to the normalized ``models`` list without
    depending on arbitrary event payloads.
    """

    model_list = list(models or [])

    print("[DBG] gallery.select triggered evt type:", type(evt).__name__)
    print("[DBG] gallery.select index:", getattr(evt, "index", None))
    print("[DBG] gallery.select value repr:", repr(getattr(evt, "value", None))[:200])
    if kwargs:
        print("[DBG] gallery.select kwargs:", {k: type(v).__name__ for k, v in kwargs.items()})

    selected = None
    idx_candidate = None
    idx_value = getattr(evt, "index", None)
    if isinstance(idx_value, (int, float)):
        idx_candidate = int(idx_value)
    elif isinstance(idx_value, (tuple, list)) and idx_value:
        try:
            idx_candidate = int(idx_value[0])
        except Exception:
            idx_candidate = None

    if idx_candidate is not None and 0 <= idx_candidate < len(model_list):
        selected = model_list[idx_candidate]
    else:
        candidate_value = getattr(evt, "value", None)
        candidate_title: str | None = None
        if isinstance(candidate_value, (list, tuple)) and len(candidate_value) == 2:
            _, maybe_title = candidate_value
            if isinstance(maybe_title, str):
                candidate_title = maybe_title
        elif isinstance(candidate_value, dict):
            candidate_title = candidate_value.get("title")
        if candidate_title is not None:
            for m in model_list:
                if str(m.get("title")) == candidate_title:
                    selected = m
                    break

    if selected is None and model_list:
        selected = model_list[0]

    if selected is None:
        summary_html = "<div><strong>Selected model:</strong> None</div>"
        generate_md = "No model selected"
        return summary_html, None, generate_md, ""

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

    return summary_html, selected, generate_md, str(selected.get("id"))


def do_generate(model, model_id, prompt_text, neg_text, size_v, steps_v, guidance_v, seed_v, api_model, token):
    # Default updates: do NOT use a placeholder image value — leave image empty/hidden
    default_img_update = gr.update(value=None, visible=False) if gr else None
    default_gallery_update = gr.update(value=None, visible=False) if gr else None

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

    try:
        print("[DBG] job keys=", list(job.keys()))
        print("[DBG] job.meta=", job.get("meta"))
        print("[DBG] job.status=", job.get("status"), "remote=", job.get("remote"), "error=", job.get("error"))
        if isinstance(result, dict):
            print("[DBG] result keys=", list(result.keys()))
        else:
            print("[DBG] result type=", type(result), "repr=", repr(result)[:120])
    except Exception as _dbg_exc:
        print("[DBG] logging error:", _dbg_exc)

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

    print("[DBG] parsed imgs count=", len(imgs))

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
        if img_exists:
            print("[DBG] image available for display:", img)
        else:
            print("[DBG] image not available as path; may be remote URL or invalid:", img)
        img_update = gr.update(value=img if img_exists else (img if isinstance(img, str) and img.startswith("http") else None), visible=bool(img)) if gr else None
    else:
        status_md += "  \n_No image returned; using empty state_"
        gallery_update = default_gallery_update
        img_update = default_img_update

    return img_update, status_md, job.get("meta", {}).get("job_id", ""), gallery_update
