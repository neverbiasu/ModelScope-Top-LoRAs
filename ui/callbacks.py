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


def on_gallery_select(evt, models):
    """Handle gallery selection.
    
    Args:
        evt: SelectData event with .index attribute (auto-injected by Gradio)
        models: models_state (list[dict]) passed from gr.State
    
    Returns:
        (summary_html, selected_model_dict, generate_md, model_id)
    """
    model_list = list(models or [])
    models_len = len(model_list)

    # Extract index from event object
    idx = getattr(evt, 'index', None)

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
    default_gallery_update = gr.update(value=None, visible=True) if gr else None

    if not model_id or model_id == "None":
        error_msg = "**错误：** 未选择模型。请先在 Selection 标签页中点击一个模型卡片。"
        return default_img_update, error_msg, "", default_gallery_update
    
    if not prompt_text or not prompt_text.strip():
        error_msg = "**错误：** Prompt 不能为空。请输入描述要生成的图像内容。"
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
    
    # Show submitting status
    if not effective_token:
        status_md = "⚠️ **模拟模式：** 未提供 API Token，将返回模拟结果。\n\n如需真实推理，请在 Generate 页输入 ModelScope API Token 并点击 Save Token。"
    else:
        status_md = "🔄 **提交中...** 正在向 ModelScope API 提交任务，请稍候..."
    
    try:
        job = submit_job(effective_model, params, token=effective_token)
    except Exception as exc:
        error_detail = str(exc)
        status_md = (
            f"**❌ 提交失败**\n\n"
            f"**错误信息：** {error_detail}\n\n"
            f"**可能原因：**\n"
            f"- 模型 ID 格式不正确（需要 `组织名/模型名` 格式）\n"
            f"- API Token 无效或已过期\n"
            f"- 网络连接问题\n"
            f"- 模型不支持当前任务类型\n\n"
            f"**建议操作：**\n"
            f"1. 检查 'API Model (override)' 字段，确保格式为 `owner/model-name`\n"
            f"2. 验证 API Token 是否有效\n"
            f"3. 尝试刷新页面重新选择模型"
        )
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

    job_id = job.get('meta', {}).get('job_id', '')
    is_remote = job.get('remote', False)
    is_mock = job.get('mock', False)
    job_error = job.get('error')
    
    status_md = f"### 生成结果\n\n"
    
    if is_mock:
        status_md += "**模式：** 🎭 模拟模式（未提供有效 Token）\n\n"
        status_md += "_这是一个模拟结果。要获得真实的图像生成，请提供 ModelScope API Token。_\n\n"
    else:
        status_md += f"**模式：** {'☁️ 远程推理' if is_remote else '📦 本地模拟'}\n\n"
    
    status_md += f"**任务 ID：** `{job_id}`\n\n"
    status_md += f"**使用模型：** `{effective_model}`\n\n"
    status_md += f"**状态：** {job.get('status', 'unknown')}\n\n"
    
    if incomplete:
        status_md += "⚠️ **注意：** 模型 ID 可能不完整（缺少组织前缀）。如遇到 400 错误，请在 'API Model Override' 字段输入完整格式，例如 `black-forest-labs/FLUX.1-dev`\n\n"
    
    if job_error:
        status_md += f"**⚠️ 警告：** {job_error}\n\n"

    if imgs:
        status_md += f"**生成的图片数量：** {len(imgs)}\n\n"
        status_md += "✅ **成功！** 图像已生成，请在右侧查看。"
        gallery_update = gr.update(value=imgs, visible=True) if gr else None
        if isinstance(img, str) and img.startswith("data:"):
            img_exists = True
        elif isinstance(img, str) and Path(str(img)).exists():
            img_exists = True
        else:
            img_exists = False
        img_update = gr.update(value=img if img_exists else (img if isinstance(img, str) and img.startswith("http") else None), visible=bool(img)) if gr else None
    else:
        status_md += "⚠️ **未返回图像**\n\n"
        status_md += "可能原因：\n"
        status_md += "- 生成任务失败\n"
        status_md += "- API 响应格式异常\n"
        status_md += "- 模型不支持此类任务\n\n"
        status_md += "请检查上述错误信息或尝试其他模型。"
        gallery_update = default_gallery_update
        img_update = default_img_update

    return img_update, status_md, job_id, gallery_update
