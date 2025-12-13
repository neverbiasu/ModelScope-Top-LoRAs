"""UI callbacks for Top‑LoRAs Gradio app."""

from __future__ import annotations

from typing import Iterable, Any, Optional
import os
from pathlib import Path
from base64 import b64decode
import uuid

try:
    import gradio as gr
except Exception:  # pragma: no cover - optional UI dependency
    gr = None

from top_loras.inference import submit_job


def on_gallery_select(evt, models, lang="zh"):
    """Handle gallery selection.
    
    Args:
        evt: SelectData event with .index attribute (auto-injected by Gradio)
        models: models_state (list[dict]) passed from gr.State
        lang: current language ("zh" or "en"), defaults to "zh"
    
    Returns:
        (summary_html, selected_model_dict, generate_md, model_id)
    """
    from ui.i18n import t
    
    # Extract index from SelectData event
    idx = None
    try:
        idx = getattr(evt, "index", None)
        if idx is None and isinstance(evt, dict):
            idx = evt.get("index")
    except Exception as e:
        print(f"[ERROR] Failed to extract index from event: {e}")

    if isinstance(idx, (tuple, list)) and idx:
        first = idx[0]
        if isinstance(first, int):
            idx = first
    
    # Ensure lang is valid
    if lang not in ("zh", "en"):
        lang = "zh"
    
    model_list = list(models or [])
    models_len = len(model_list)

    # Validate index
    if not isinstance(idx, int) or idx < 0 or idx >= models_len:
        no_model_text = t("no_model_selected", lang)
        return f"<div style='padding:12px;background:rgba(255,255,255,0.05);border-radius:8px;'><strong>{no_model_text}</strong></div>", None, t("select_first", lang), ""

    selected = model_list[idx]

    title = selected.get("title_en") or selected.get("title") or selected.get("title_cn") or ""
    model_id = str(selected.get("id") or "")
    author = selected.get("author") or ""
    downloads = selected.get("downloads") or 0
    likes = selected.get("likes") or 0

    name_label = t("model_name", lang)  # type: ignore
    author_label = t("model_author", lang)  # type: ignore
    stats_label = t("model_stats", lang)  # type: ignore
    selected_label = t("model_selected", lang)  # type: ignore

    summary_html = f"""
<div style="padding: 12px; border-radius: 8px; background: rgba(255,255,255,0.04);">
    <h3 style="margin: 0 0 8px 0;">{selected_label}</h3>
    <p style="margin: 4px 0;"><strong>{name_label}:</strong> {title}</p>
    <p style="margin: 4px 0;"><strong>{author_label}:</strong> {author}</p>
    <p style="margin: 4px 0; opacity: 0.7;">{downloads} · {likes}</p>
</div>
"""
    gen_md = f"{selected_label} {title}"

    return summary_html, selected, gen_md, model_id


def do_generate(model, model_id, prompt_text, neg_text, size_v, steps_v, guidance_v, seed_v, api_model, token, lang="zh"):
    from ui.i18n import t
    
    # Ensure lang is valid
    if lang not in ("zh", "en"):
        lang = "zh"
    
    # Default updates: do NOT use a placeholder image value — leave image empty/hidden
    default_img_update = gr.update(value=None, visible=False) if gr else None
    default_gallery_update = gr.update(value=None, visible=True) if gr else None

    # Prefer the selected model dict's canonical repo id (`owner/name`) over the textbox value.
    selected_repo_id = None
    try:
        if isinstance(model, dict):
            candidate = str(model.get("id") or "").strip()
            if "/" in candidate:
                selected_repo_id = candidate
    except Exception:
        selected_repo_id = None

    selected_model_id = (selected_repo_id or str(model_id or "").strip())

    if not selected_model_id or selected_model_id == "None":
        error_msg = t("error_no_model", lang)
        return default_img_update, error_msg, "", default_gallery_update
    
    if not prompt_text or not prompt_text.strip():
        error_msg = t("error_empty_prompt", lang)
        return default_img_update, error_msg, "", default_gallery_update

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
    effective_model = (effective_model or selected_model_id or "").strip()

    # If the selected item looks like a LoRA (has base_models metadata) and user did NOT override,
    # default to the first recommended base model and pass the selected repo id via `loras`.
    # This prevents accidentally submitting a LoRA repo id as the base `model`.
    base_from_meta = None
    try:
        if (not api_model) and isinstance(model, dict):
            bases = model.get("base_models")
            if isinstance(bases, (list, tuple)) and bases:
                candidate = str(bases[0] or "").strip()
                if "/" in candidate:
                    base_from_meta = candidate

            # FLUX LoRA: prefer the known working base checkpoint repo.
            # Some entries may list a generic FLUX.1-dev base; use the correct MusePublic base instead.
            if base_from_meta:
                sd_ver = str(model.get("stable_diffusion_version") or "").strip().upper()
                vf = str(model.get("vision_foundation") or "").strip().upper()
                is_flux = (sd_ver == "FLUX_1") or (vf == "FLUX_1")
                base_l = base_from_meta.lower()
                if is_flux and base_l.endswith("/flux.1-dev"):
                    base_from_meta = "MusePublic/489_ckpt_FLUX_1"
    except Exception:
        base_from_meta = None
    if base_from_meta and effective_model == selected_model_id:
        effective_model = base_from_meta

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

    # If user provides API Model Override, treat it as the *base* model and use the selected model
    # as LoRA(s) via the official `loras` parameter.
    # This matches ModelScope's examples like: model=Qwen/Qwen-Image, loras=<lora-repo-id>
    if api_model and selected_model_id and selected_model_id != effective_model:
        params["loras"] = selected_model_id

    # If base was derived from metadata, also attach LoRA automatically.
    if base_from_meta and selected_model_id and selected_model_id != effective_model:
        params["loras"] = selected_model_id
    params = {k: v for k, v in params.items() if v is not None}

    debug = os.environ.get("MODELSCOPE_DEBUG", "").lower() in ("1", "true", "yes")
    if debug:
        print(f"[DEBUG] UI selected_model_id: {selected_model_id!r}")
        print(f"[DEBUG] UI effective_model(base): {effective_model!r}")
        print(f"[DEBUG] UI loras: {params.get('loras')!r}")

    effective_token = token or os.environ.get("MODELSCOPE_API_TOKEN")
    if isinstance(effective_token, str):
        effective_token = effective_token.strip().strip('"').strip("'")
        if effective_token.lower().startswith("bearer "):
            effective_token = effective_token.split(None, 1)[-1].strip()
        if not effective_token:
            effective_token = None
    
    # Show submitting status
    status_md = t("status_submitting", lang) if effective_token else t("status_mock_mode", lang)
    
    try:
        job = submit_job(effective_model, params, token=effective_token)
    except Exception as exc:
        error_detail = str(exc)

        loras_used = params.get("loras")
        loras_line = f"- LoRA(s): `{loras_used}`\n" if loras_used else ""

        # Always surface raw provider error detail (do not rewrite it).
        status_md = (
            f"{t('error_submit_failed', lang)}\n\n"
            f"{t('error_details', lang)} {error_detail}\n\n"
            f"---\n\n"
            f"- Base 模型: `{effective_model}`\n"
            f"{loras_line}"
            f"- Token 状态: {'已提供' if effective_token else '未提供'}\n"
            f"- 需要更多请求/响应信息: `export MODELSCOPE_DEBUG=1` 后重试"
        )

        return default_img_update, status_md, "", default_gallery_update

    result = job.get("result") or {}

    imgs = []
    try:
        if isinstance(result, dict):
            # Prefer local paths if present to avoid expiring URLs.
            images_local = result.get("images_local")
            images_remote = result.get("images")
            merged: list[str] = []
            if isinstance(images_local, (list, tuple)):
                merged.extend([i for i in images_local if isinstance(i, str)])
            if isinstance(images_remote, (list, tuple)):
                for i in images_remote:
                    if isinstance(i, str) and i not in merged:
                        merged.append(i)
            if merged:
                imgs = merged
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

    job_id = job.get('meta', {}).get('job_id', '')
    is_remote = job.get('remote', False)
    is_mock = job.get('mock', False)
    job_error = job.get('error')
    
    status_md = f"{t('status_result', lang)}\n\n"
    
    if is_mock:
        mode_text = t("status_mode_mock", lang)
        status_md += f"{t('status_mode', lang)} {mode_text}\n\n"
        status_md += f"_{t('status_mock_note', lang)}_\n\n"
    else:
        mode_text = t("status_mode_remote", lang) if is_remote else t("status_mode_local", lang)
        status_md += f"{t('status_mode', lang)} {mode_text}\n\n"
    
    status_md += f"{t('status_job_id', lang)} `{job_id}`\n\n"
    status_md += f"{t('status_model', lang)} `{effective_model}`\n\n"
    if params.get("loras") is not None:
        status_md += f"LoRA(s): `{params.get('loras')}`\n\n"

    try:
        submitted_model = result.get("submitted_model") if isinstance(result, dict) else None
        submitted_loras = result.get("submitted_loras") if isinstance(result, dict) else None
    except Exception:
        submitted_model = None
        submitted_loras = None
    if submitted_model and submitted_model != effective_model:
        status_md += f"实际提交 Base: `{submitted_model}`\n\n"
    if submitted_loras is not None and submitted_loras != params.get("loras"):
        status_md += f"实际提交 LoRA(s): `{submitted_loras}`\n\n"
    status_md += f"{t('status_state', lang)} {job.get('status', 'unknown')}\n\n"
    
    if incomplete:
        status_md += f"{t('status_warning_incomplete', lang)}\n\n"
    
    if job_error:
        status_md += f"{t('status_job_error', lang)} {job_error}\n\n"

    if imgs:
        status_md += f"{t('status_generated_count', lang)} {len(imgs)}\n\n"
        status_md += t("status_success", lang)

        # Show history (persisted) on the right, and keep the main output as the current image.
        # This avoids displaying the same image twice.
        history_imgs = []
        try:
            from ui.loaders import load_generated_images

            history_imgs = load_generated_images("text-to-image-synthesis", limit=40)
        except Exception:
            history_imgs = []

        if isinstance(img, str) and img.startswith("data:"):
            img_exists = True
        elif isinstance(img, str) and Path(str(img)).exists():
            img_exists = True
        else:
            img_exists = False
        img_update = gr.update(value=img if img_exists else (img if isinstance(img, str) and img.startswith("http") else None), visible=bool(img)) if gr else None

        # Exclude current output from history to avoid duplication.
        if isinstance(img, str) and img:
            history_imgs = [h for h in history_imgs if h != img]
        gallery_update = gr.update(value=history_imgs or None, visible=True) if gr else None
    else:
        status_md += f"{t('status_no_images', lang)}\n\n"
        status_md += f"{t('status_no_images_reasons', lang)}\n"
        status_md += f"{t('status_reason_1', lang)}\n"
        status_md += f"{t('status_reason_2', lang)}\n"
        status_md += f"{t('status_reason_3', lang)}\n\n"
        status_md += t("status_check_error", lang)
        # Still show persisted history even if this run produced no images.
        history_imgs = []
        try:
            from ui.loaders import load_generated_images

            history_imgs = load_generated_images("text-to-image-synthesis", limit=40)
        except Exception:
            history_imgs = []
        gallery_update = gr.update(value=history_imgs or None, visible=True) if gr else default_gallery_update
        img_update = default_img_update

    return img_update, status_md, job_id, gallery_update
