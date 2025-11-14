from pathlib import Path
from base64 import b64decode
import json
import os
from typing import Any, Iterable, Optional

from top_loras import cache as tl_cache
import fetch_top_models as fetch_module
from top_loras.download import sanitize_filename

# Tiny transparent PNG data URI as fallback placeholder used by the UI
_PLACEHOLDER_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
)
_PLACEHOLDER_PATH: Optional[str] = None


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


def _ensure_placeholder_image() -> str:
    global _PLACEHOLDER_PATH
    if _PLACEHOLDER_PATH is not None:
        return _PLACEHOLDER_PATH

    placeholder_path = Path("cache").joinpath("placeholder.png")
    placeholder_path.parent.mkdir(parents=True, exist_ok=True)
    if not placeholder_path.exists():
        payload = _PLACEHOLDER_DATA_URI.split("base64,")[-1]
        try:
            placeholder_path.write_bytes(b64decode(payload))
        except Exception:
            placeholder_path.write_text("", encoding="utf-8")
    _PLACEHOLDER_PATH = str(placeholder_path)
    return _PLACEHOLDER_PATH


def sanitize_models(models: Iterable[dict[str, Any]] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize raw model dicts and build gallery items.

    Returns (normalized_models, gallery_items) where each gallery item is a
    small dict carrying enough information for selection callbacks without
    depending on Gradio's internal event types.
    """

    normalized: list[dict[str, Any]] = []
    gallery_items: list[dict[str, Any]] = []

    for idx, model in enumerate(models or []):
        if not isinstance(model, dict):
            continue

        cover_uri = (
            _resolve_cover_uri(model.get("cover_local"))
            or _resolve_cover_uri(model.get("cover"))
            or _resolve_cover_uri(model.get("cover_url"))
            or _ensure_placeholder_image()
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
        gallery_items.append(
            {
                "idx": idx,
                "id": normalized_model.get("id"),
                "title": title,
                "cover": cover_uri or _ensure_placeholder_image(),
            }
        )

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
            or _ensure_placeholder_image()
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
