"""Gradio read-only UI for Top-LoRAs cache

Features:
- Select a task or use global cache, load cached Top-LoRAs and render cover+metadata
- Refresh button to run fetch_top_loras (uses local fetch implementation) and update cache

Usage:
- Install: pip install gradio
- Run: python app.py

If gradio is not installed the script will print instructions instead of failing.
"""

from pathlib import Path
import json

from top_loras import cache as tl_cache
import fetch_top_models as fetch_module
from top_loras.download import sanitize_filename


def get_cache_path(task: str | None, per_task_cache: bool = True):
    default = fetch_module.DEFAULT_CACHE_FILE
    images_dir = fetch_module.DEFAULT_IMAGES_DIR
    if per_task_cache and task:
        safe = sanitize_filename(task)
        return f"cache/top_loras_{safe}.json"
    return default


def load_results_from_cache(cache_file: str):
    # Prefer using the cache helper which validates _cached_at and returns the
    # `results` list. Use a very large TTL here so the UI will show the cache even
    # if it is older than the CLI's default TTL; the user can Refresh to force an update.
    try:
        results = tl_cache.load_cache(cache_file, ttl=60 * 60 * 24 * 365)
        return results or []
    except Exception:
        # fallback to manual read for unexpected formats
        p = Path(cache_file)
        if not p.exists():
            return []
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            return data.get('results') or []
        except Exception:
            return []


# Try to import gradio lazily
try:
    import gradio as gr
except Exception:
    gr = None


def render_markdown_for_models(models):
    # Generate a responsive HTML card grid using Catppuccin Mocha palette
    if not models:
        return "<div class='empty'>No cached results found. Try <b>Refresh</b> to fetch data.</div>"

    # header + cards style inspired by modelscope-studio, using Catppuccin Mocha-like palette
    css = """
<style>
:root{
    /* Catppuccin Mocha-ish palette (mantle/crust/surface/text/accents) */
    --bg:#1f1d2e;      /* mantle */
    --surface:#292c3c; /* surface1 */
    --muted:#a6adc8;   /* subtext */
    --text:#cdd6f4;    /* text */
    --accent:#f5c2e7;  /* pink */
    --accent-2:#89b4fa;/* blue */
    --card:#232634;    /* surface2 */
    --glass: rgba(255,255,255,0.03);
}
body { background: var(--bg); color: var(--text); font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
.tl-header{display:flex; align-items:center; gap:12px; padding:14px; border-bottom:1px solid rgba(255,255,255,0.03);}
.tl-title-main{font-size:20px; font-weight:700}
.tl-controls{margin-left:auto; display:flex; gap:8px; align-items:center}
.tl-container{padding:18px;}
.tl-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; margin-top:12px}
.tl-card{background:linear-gradient(180deg, rgba(255,255,255,0.01), rgba(0,0,0,0.04)); border-radius:12px; padding:12px; box-shadow:0 8px 20px rgba(0,0,0,0.6); border:1px solid rgba(255,255,255,0.03); transition:transform .15s ease, box-shadow .15s ease}
.tl-card:hover{transform:translateY(-6px); box-shadow:0 18px 30px rgba(0,0,0,0.7)}
.tl-cover{width:100%; height:180px; object-fit:cover; border-radius:8px; background:var(--glass); display:block}
.tl-title{font-weight:700; margin-top:10px; color:var(--text); font-size:15px}
.tl-meta{font-size:13px; color:var(--muted); margin-top:6px}
.tl-row{display:flex; gap:8px; align-items:center;}
.tl-badge{background:var(--accent-2); color:#0b1020; padding:4px 8px; border-radius:999px; font-weight:600; font-size:12px}
.tl-link{color:var(--accent-2); text-decoration:underline}
.tl-tags{margin-top:8px; display:flex; gap:6px; flex-wrap:wrap}
.tl-tag{background:rgba(255,255,255,0.02); color:var(--muted); padding:4px 8px; border-radius:6px; font-size:12px}
.empty{color:var(--muted); padding:20px}
.tl-footer{font-size:12px; color:var(--muted); text-align:center; padding:12px}
</style>
"""

    cards = [css, "<div class='tl-container'><div class='tl-grid'>"]
    for i, m in enumerate(models, 1):
        title = (m.get('title_cn') or m.get('title_en') or m.get('id') or '').replace('<', '&lt;')
        # Prefer local cover if available; convert relative local paths to file:// URIs
        raw_url = m.get('cover_local') or m.get('cover_url') or ''
        url = raw_url
        try:
            from pathlib import Path
            if raw_url and not (raw_url.startswith('http://') or raw_url.startswith('https://') or raw_url.startswith('file://')):
                p = Path(raw_url)
                if p.exists():
                    url = p.resolve().as_uri()
        except Exception:
            url = raw_url
        author = m.get('author') or ''
        downloads = m.get('downloads') or 0
        likes = m.get('likes') or 0
        updated = m.get('updated_at') or ''
        model_url = m.get('modelscope_url') or '#'
        tags = m.get('tags_en') or m.get('tags_cn') or []
        tags_html = ''.join([f"<div class='tl-tag'>{t}</div>" for t in tags[:6]])

        card_html = f"""
        <div class='tl-card'>
            <img class='tl-cover' src='{url}' alt='cover' onerror="this.style.display='none'" />
            <div class='tl-title'>{i}. {title}</div>
            <div class='tl-meta'>{author} · Downloads: {downloads} · Likes: {likes}</div>
            <div class='tl-row' style='margin-top:8px'>
                <div class='tl-badge'>#{i}</div>
                <div style='flex:1'></div>
                <a class='tl-link' href='{model_url}' target='_blank'>Model Page</a>
            </div>
            <div class='tl-tags'>{tags_html}</div>
            <div class='tl-meta' style='margin-top:8px'>Updated: {updated}</div>
        </div>
        """
        cards.append(card_html)

    cards.append("</div></div>")
    return '\n'.join(cards)


def build_ui():
    if gr is None:
        print("Gradio is not installed. Install with: pip install gradio")
        return

    tasks = [None]
    # include presets from fetch module
    try:
        presets = fetch_module.TASK_PRESETS
        tasks += list(presets.values())
    except Exception:
        pass

    with gr.Blocks() as demo:
        gr.Markdown("# Top-LoRAs Cache Viewer")
        # Only keep task selection and per-task-toggle in the header; auto-load default task on startup
        with gr.Row():
            task_dd = gr.Dropdown(["(global)"] + tasks[1:], value="(global)", label="Task (use global to read default cache)")
            per_task_cb = gr.Checkbox(value=True, label='Enable per-task cache (default)')

        # Default task to display immediately on load
        default_task = "text-to-image-synthesis"
        # If presets include the default, set the dropdown to it; otherwise leave as (global)
        try:
            presets_values = list(fetch_module.TASK_PRESETS.values())
        except Exception:
            presets_values = []

        initial_task_value = default_task if default_task in presets_values else "(global)"
        # compute models for initial view
        init_task = None if initial_task_value in (None, "(global)") else initial_task_value
        cache_file = get_cache_path(init_task, per_task_cache=True)
        initial_models = load_results_from_cache(cache_file)
        initial_md = render_markdown_for_models(initial_models)

        # Use HTML component so the generated CSS+cards render correctly
        output_md = gr.HTML(initial_md)

        demo.launch()


if __name__ == '__main__':
    build_ui()
