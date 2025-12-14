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


# =============================================================================
# Base Model 替换映射表
# 将不支持 API 或不推荐的 base model 替换为已知可用的版本
# =============================================================================
BASE_MODEL_REPLACEMENTS = {
    # FLUX.1-dev 系列 → 使用 MusePublic 的可用版本
    "AI-ModelScope/FLUX.1-dev": "MusePublic/489_ckpt_FLUX_1",
    "ai-modelscope/flux.1-dev": "MusePublic/489_ckpt_FLUX_1",
    "black-forest-labs/FLUX.1-dev": "MusePublic/489_ckpt_FLUX_1",
    "black-forest-labs/flux.1-dev": "MusePublic/489_ckpt_FLUX_1",
    # 可以继续添加其他替换规则...
}

# 根据 vision_foundation / stable_diffusion_version 推断默认 base model
# 当 LoRA 没有配置 base_models 时使用
DEFAULT_BASE_BY_FOUNDATION = {
    "FLUX_1": "MusePublic/489_ckpt_FLUX_1",
    "QWEN_IMAGE_20_B": "MusePublic/Qwen-image@v1",
    # 可以继续添加...
}


def normalize_base_model(base: str) -> str:
    """Apply base model replacement rules.
    
    Args:
        base: Original base model ID
    
    Returns:
        Replaced base model ID if a rule matches, otherwise original
    """
    if not base:
        return base
    
    # Exact match first
    if base in BASE_MODEL_REPLACEMENTS:
        return BASE_MODEL_REPLACEMENTS[base]
    
    # Case-insensitive match
    base_lower = base.lower()
    for pattern, replacement in BASE_MODEL_REPLACEMENTS.items():
        if base_lower == pattern.lower():
            return replacement
    
    # Partial match for FLUX.1-dev variations (handles @version suffixes)
    if "flux.1-dev" in base_lower or "flux.1dev" in base_lower:
        # Check if it's NOT already a MusePublic or known working repo
        if not base_lower.startswith("musepublic/"):
            return "MusePublic/489_ckpt_FLUX_1"
    
    return base


def infer_default_base(model: dict) -> str | None:
    """Infer a default base model from LoRA metadata when base_models is empty.
    
    Args:
        model: Model dict with vision_foundation, stable_diffusion_version, etc.
    
    Returns:
        Default base model ID or None
    """
    if not isinstance(model, dict):
        return None
    
    # Check vision_foundation first, then stable_diffusion_version
    vf = str(model.get("vision_foundation") or "").strip().upper()
    sd_ver = str(model.get("stable_diffusion_version") or "").strip().upper()
    
    foundation = vf or sd_ver
    
    return DEFAULT_BASE_BY_FOUNDATION.get(foundation)


def parse_api_error(error_info: dict | str, lang: str = "zh") -> str:
    """Parse API error and return user-friendly message.
    
    Args:
        error_info: Error dict from API response or error string
        lang: Language code ("zh" or "en")
    
    Returns:
        Friendly error message string
    """
    from ui.i18n import t
    
    # Convert to string for pattern matching
    error_str = str(error_info).lower() if error_info else ""
    
    # Extract error code and message if dict
    error_code = None
    error_message = ""
    model_id = ""
    
    if isinstance(error_info, dict):
        errors = error_info.get("errors", {})
        if isinstance(errors, dict):
            error_code = errors.get("code")
            error_message = errors.get("message", "")
        model_id = error_info.get("submitted_model", "")
    
    # Match common error patterns
    if "task not found" in error_str:
        return t("err_task_not_found", lang)
    
    if error_code == 401 or "401" in error_str or "unauthorized" in error_str or "token" in error_str and "invalid" in error_str:
        return t("err_token_invalid", lang)
    
    if error_code == 429 or "429" in error_str or "rate limit" in error_str or "too many" in error_str:
        return t("err_rate_limit", lang)
    
    if error_code == 500 or "500" in error_str or "internal server error" in error_str:
        return t("err_server_error", lang)
    
    if "timeout" in error_str:
        return t("err_timeout", lang)
    
    if "40212" in error_str or "not support" in error_str or "not supported" in error_str:
        msg = t("err_model_not_supported", lang)
        if model_id:
            msg = msg.replace("{model}", model_id)
        else:
            msg = msg.replace("`{model}`", "this model")
        return msg
    
    # Unknown error - return generic message
    return t("err_unknown", lang)


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
            
            # If base_models is empty, try to infer from vision_foundation
            if not base_from_meta:
                base_from_meta = infer_default_base(model)
            
            # Apply base model replacement rules
            if base_from_meta:
                base_from_meta = normalize_base_model(base_from_meta)
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
        # Parse error and show friendly message
        friendly_error = parse_api_error(result if isinstance(result, dict) else job_error, lang)
        status_md += f"{friendly_error}\n\n"
        status_md += f"---\n\n<details><summary>原始错误信息 / Raw Error</summary>\n\n```\n{job_error}\n```\n\n</details>\n\n"

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
