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
import os


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
    .tl-container{padding:18px; max-width:1400px; margin:0 auto}
    /* Responsive grid: min column width 320px, with explicit breakpoints for desktop */
    .tl-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; margin-top:12px; align-items:start; grid-auto-rows:1fr}
    @media (min-width:700px){ .tl-grid{grid-template-columns:repeat(2,1fr);} }
    @media (min-width:1000px){ .tl-grid{grid-template-columns:repeat(3,1fr);} }
    @media (min-width:1400px){ .tl-grid{grid-template-columns:repeat(4,1fr);} }
    .tl-grid > .tl-card{background:linear-gradient(180deg, rgba(255,255,255,0.01), rgba(0,0,0,0.04)); border-radius:12px; padding:12px; box-shadow:0 8px 20px rgba(0,0,0,0.6); border:1px solid rgba(255,255,255,0.03); transition:transform .15s ease, box-shadow .15s ease; display:flex; flex-direction:column; height:100%; overflow:hidden; aspect-ratio:1/1}
    .tl-grid > .tl-card:hover{transform:translateY(-6px); box-shadow:0 18px 30px rgba(0,0,0,0.7)}
    /* force a consistent cover aspect ratio so cards have uniform image sizes */
    .tl-cover{width:100%; aspect-ratio:16/9; object-fit:cover; border-radius:8px; background:var(--glass); display:block; flex:0 0 auto}
.tl-body{display:flex; flex-direction:column; flex:1; overflow:visible}
.tl-title{font-weight:700; margin-top:6px; color:var(--text); font-size:14px; line-height:1.2}
.tl-meta{font-size:12px; color:var(--muted); margin-top:4px; white-space:normal; text-overflow:initial; overflow:visible}
.tl-tags{margin-top:8px; display:flex; gap:6px; flex-wrap:wrap; max-height:3.6em; overflow:hidden}
.tl-title{font-weight:700; margin-top:10px; color:var(--text); font-size:15px}
.tl-meta{font-size:13px; color:var(--muted); margin-top:6px}
.tl-row{display:flex; gap:8px; align-items:center;}
.tl-badge{background:var(--accent-2); color:#0b1020; padding:4px 8px; border-radius:999px; font-weight:600; font-size:12px}
.tl-link{color:var(--accent-2); text-decoration:underline}
.tl-tags{margin-top:8px; display:flex; gap:6px; flex-wrap:wrap}
.tl-tag{background:rgba(255,255,255,0.02); color:var(--muted); padding:4px 8px; border-radius:6px; font-size:12px}
.tl-open-btn{background:var(--accent); color:#0b1020; border:none; padding:6px 8px; border-radius:8px; font-weight:700; cursor:pointer}
.empty{color:var(--muted); padding:20px}
.tl-footer{font-size:12px; color:var(--muted); text-align:center; padding:12px}
</style>
"""

    from pathlib import Path
    import base64
    import imghdr

    # placeholder 1x1 transparent PNG
    placeholder = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="

    def to_data_uri(path_or_url):
        if not path_or_url:
            return None
        s = str(path_or_url)
        if s.startswith('http://') or s.startswith('https://'):
            return s
        # treat as local path
        p = Path(s)
        if not p.exists():
            return None
        try:
            data = p.read_bytes()
            # try to determine image type from header or extension
            kind = imghdr.what(None, h=data)
            if not kind:
                ext = p.suffix.lower().lstrip('.')
                kind = ext or 'png'
            mime = f'image/{"jpeg" if kind=="jpg" else kind}'
            b64 = base64.b64encode(data).decode('ascii')
            return f'data:{mime};base64,{b64}'
        except Exception:
            return None

    cards = [css, "<div class='tl-container'><div class='tl-grid'>"]
    for i, m in enumerate(models, 1):
        title = (m.get('title_cn') or m.get('title_en') or m.get('id') or '').replace('<', '&lt;')
        cover_src = to_data_uri(m.get('cover_local') or m.get('cover_url') or '') or placeholder
        avatar_src = to_data_uri(m.get('avatar') or '') or placeholder
        author = m.get('author') or ''
        downloads = m.get('downloads') or 0
        likes = m.get('likes') or 0
        updated = m.get('updated_at') or ''
        model_url = m.get('modelscope_url') or '#'
        tags = m.get('tags_en') or m.get('tags_cn') or []
        tags_html = ''.join([f"<div class='tl-tag'>{t}</div>" for t in tags[:6]])

        card_html = f"""
    <div class='tl-card' onclick="selectModel({i})">
            <div class='tl-body'>
                <div style='display:flex; gap:12px; align-items:flex-start'>
                    <img src='{avatar_src}' alt='avatar' style='width:32px; height:32px; border-radius:50%; object-fit:cover; flex:0 0 32px; background:var(--glass);' onerror="this.style.display='none'" />
                    <div style='flex:1'>
                        <div class='tl-title'>{i}. {title}</div>
                        <div class='tl-meta'>{author} · Downloads: {downloads} · Likes: {likes}</div>
                    </div>
                </div>
                <div style='margin-top:10px'>
                    <img class='tl-cover' src='{cover_src}' alt='cover' onerror="this.style.display='none'" />
                </div>
                <div class='tl-row' style='margin-top:8px'>
                    <div class='tl-badge'>#{i}</div>
                    <div style='flex:1'></div>
                            <a class='tl-link' href='{model_url}' target='_blank'>Model Page</a>
                </div>
                <div class='tl-tags'>{tags_html}</div>
                <div class='tl-meta' style='margin-top:8px'>Updated: {updated}</div>
            </div> <!-- .tl-body -->
        </div> <!-- .tl-card -->
        """
        cards.append(card_html)

    cards.append("</div></div>")
    # small JS bridge: call selectModel(i) to write into hidden textbox with id 'tl_select_box'
    cards.append("""
    <script>
    function selectModel(i){
        try{
            // try exact id then fallback to selectors (some Gradio builds prefix ids)
            var el = document.getElementById('tl_select_box') || document.querySelector("[id$='tl_select_box']") || document.querySelector("input[aria-label='_tl_select_box']");
            if(!el){ console.warn('tl_select_box not found'); return; }
            el.value = String(i);
            // dispatch both input and change to satisfy different listeners
            el.dispatchEvent(new Event('input', {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
        }catch(e){console.warn(e)}
    }
    </script>
    """)
    return '\n'.join(cards)


def build_ui():
    if gr is None:
        print("Gradio is not installed. Install with: pip install gradio")
        return

    # build task list from presets (no global option)
    tasks = []
    try:
        presets = fetch_module.TASK_PRESETS
        tasks = list(presets.values())
    except Exception:
        tasks = []

    # Build an improved header + Tabs layout (Selection -> Generate)
    with gr.Blocks(css="body { background: #0f1117; }") as demo:
        # Header (compact)
        # Simplified header: single title as requested
        with gr.Row(elem_id="tl-header", variant="panel"):
            gr.Markdown("# Top-LoRAs")

        # Tabs: Selection (cards + controls) and Generate (parameters)
        with gr.Tabs() as tabs:
            with gr.TabItem("Selection"):
                    with gr.Row():
                        with gr.Column(scale=3):
                            task_dd = gr.Dropdown(tasks or [], value=None, label="Task (select)")
                            per_task_cb = gr.Checkbox(value=True, label='Per-task cache')
                            refresh_btn = gr.Button("Refresh Cache")
                            refresh_help = gr.Markdown("Refresh will re-fetch the selected task from ModelScope, (re)download covers and update the local cache (session token used if provided).")
                            # Selected model area (single-select)
                            selected_md = gr.Markdown("**Selected model:** None")
                            selected_state = gr.State(value=None)
                        with gr.Column(scale=9):
                            # use Gradio Gallery for cards (click to select)
                            gallery = gr.Gallery(label="Top LoRAs", value=[], columns=3, show_label=False, elem_id="tl_gallery", height=520)
                            # keep a state holding the current list of models (dicts)
                            models_state = gr.State(value=[])

            with gr.TabItem("Generate"):
                with gr.Row():
                    with gr.Column(scale=8):
                        gen_model_info = gr.Markdown("No model selected")
                        prompt = gr.Textbox(label="Prompt", placeholder="Describe the image to generate")
                        steps = gr.Slider(minimum=1, maximum=150, value=20, step=1, label="Steps")
                        guidance = gr.Slider(minimum=1.0, maximum=30.0, value=7.5, step=0.1, label="Guidance Scale")
                        seed = gr.Number(value=42, label="Seed (0=random)")
                        generate_btn = gr.Button("Generate")
                        # token input moved here (Generate page)
                        token_input = gr.Textbox(label="ModelScope API Token", placeholder="Paste token here (session)", type="password")
                        token_save = gr.Button("Save Token")
                        token_clear = gr.Button("Clear Token")
                        auth_md = gr.Markdown("**Auth:** Not provided")
                        token_state = gr.State(value=None)
                    with gr.Column(scale=4):
                        out_image = gr.Image(label="Output", visible=False)
                        job_status = gr.Markdown("")

    # Default task logic (pick a sensible initial task)
        default_task = "text-to-image-synthesis"
        try:
            presets_values = list(fetch_module.TASK_PRESETS.values())
        except Exception:
            presets_values = []
        if default_task in (presets_values or tasks):
            initial_task_value = default_task
        elif tasks:
            initial_task_value = tasks[0]
        else:
            initial_task_value = default_task

        # load initial models
        init_task = initial_task_value
        cache_file = get_cache_path(init_task, per_task_cache=True)
        initial_models = load_results_from_cache(cache_file)
        def sanitize_models(raw_models):
            """Return (normalized_models, gallery_items).
            normalized_models: list of dicts (only valid models)
            gallery_items: list of (img_str, caption)
            
            Gallery expects (img_uri, caption) where img_uri is:
            - HTTP(S) URL
            - data: URI (base64 embedded)
            NOT relative paths (which cause 'Cannot read properties of undefined (reading url)')
            """
            import base64
            import imghdr
            
            placeholder = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
            norm = []
            gallery_items = []
            from pathlib import Path as _Path
            
            def path_to_data_uri(path_str):
                """Convert local path to data URI, fallback to placeholder on error."""
                if not path_str:
                    return placeholder
                path_str = str(path_str)
                # if already HTTP URL, use it
                if path_str.startswith('http://') or path_str.startswith('https://'):
                    return path_str
                # if data URI, use it
                if path_str.startswith('data:'):
                    return path_str
                # treat as local file path
                try:
                    p = _Path(path_str)
                    if not p.exists():
                        return placeholder
                    data = p.read_bytes()
                    # detect mime type
                    kind = imghdr.what(None, h=data)
                    if not kind:
                        ext = p.suffix.lower().lstrip('.')
                        kind = ext if ext else 'png'
                    mime = f'image/{"jpeg" if kind in ("jpg", "jpeg") else kind}'
                    b64 = base64.b64encode(data).decode('ascii')
                    return f'data:{mime};base64,{b64}'
                except Exception as e:
                    print(f"[DEBUG] Failed to convert {path_str} to data URI: {e}")
                    return placeholder
            
            for m in (raw_models or []):
                if not isinstance(m, dict):
                    continue
                # pick image (prefer cover_local to use cached image, fallback to URL)
                img_path = m.get('cover_local') or m.get('cover_url')
                img_uri = path_to_data_uri(img_path) if img_path else placeholder
                
                # caption
                title = (m.get('title_cn') or m.get('title_en') or m.get('id') or '')
                
                # minimal model shape
                nm = {
                    'id': m.get('id'),
                    'title': title,
                    'author': m.get('author'),
                    'downloads': m.get('downloads'),
                    'likes': m.get('likes'),
                    'cover': img_uri,
                    **{k: v for k, v in m.items() if k not in ('cover_local', 'cover_url')}
                }
                norm.append(nm)
                gallery_items.append({'image': img_uri, 'caption': title})
            
            return norm, gallery_items

        # sanitize initial models and populate gallery + state
        norm, gallery_items = sanitize_models(initial_models)
        gallery.value = gallery_items
        models_state.value = norm


        # helper to load models for a task and update gallery + internal state
        def _models_for_dropdown(task_value, per_task_enabled, token):
            sel = None if (not task_value) else task_value
            cache_file = get_cache_path(sel, per_task_cache=per_task_enabled)
            models = load_results_from_cache(cache_file)
            norm, gallery_items = sanitize_models(models)
            return gr.Gallery.update(value=gallery_items), norm

        task_dd.change(fn=_models_for_dropdown, inputs=[task_dd, per_task_cb, token_state], outputs=[gallery, models_state])

        # Refresh cache: force re-fetch from ModelScope and update the view
        def _refresh_cache(task_value, per_task_enabled, token):
            # if a token was provided in the UI, inject it into environment for the fetcher
            if token:
                os.environ['MODELSCOPE_API_TOKEN'] = token
            try:
                # call package fetcher to refresh cache; force_refresh=True to skip cached copy
                results = fetch_module.fetch_top_loras(force_refresh=True, task=task_value, per_task_cache=per_task_enabled, download_images=True, debug=False)
            except Exception as e:
                return f"<div class='empty'>Refresh failed: {e}</div>"
            # render
            html = render_markdown_for_models(results)
            return html

        # Refresh should update the gallery and internal models state
        def _refresh_and_update(task_value, per_task_enabled, token):
            html_or_err = _refresh_cache(task_value, per_task_enabled, token)
            # _refresh_cache returns HTML string; but we want models list instead.
            # Re-load cache and update gallery
            sel = None if (not task_value) else task_value
            cache_file = get_cache_path(sel, per_task_cache=per_task_enabled)
            models = load_results_from_cache(cache_file)
            norm, gallery_items = sanitize_models(models)
            return gr.Gallery.update(value=gallery_items), norm

        refresh_btn.click(fn=_refresh_and_update, inputs=[task_dd, per_task_cb, token_state], outputs=[gallery, models_state])

        # Token callbacks
        def _save_token(token, _state):
            if not token:
                return "**Auth:** Not provided", None
            return "**Auth:** Token saved (session only)", token

        def _clear_token(_state):
            return "**Auth:** Not provided", None

        token_save.click(fn=_save_token, inputs=[token_input, token_state], outputs=[auth_md, token_state])
        token_clear.click(fn=_clear_token, inputs=[token_state], outputs=[auth_md, token_state])

        # Gallery selection handler: set the selected model (single select)
        def _on_gallery_select(evt, models_list):
            # evt.index is the selected index in the gallery
            try:
                idx = int(evt.index)
            except Exception:
                return "**Selected model:** None", None
            models = models_list or []
            if idx < 0 or idx >= len(models):
                return "**Selected model:** None", None
            m = models[idx]
            title = (m.get('title_cn') or m.get('title_en') or m.get('id') or '')
            md = f"**Selected model:** {title}  \n\n- ID: {m.get('id')}  \n- Author: {m.get('author')}  \n- Downloads: {m.get('downloads')}  \n- Likes: {m.get('likes')}"
            # set selected_state to the selected model dict
            return md, m

        gallery.select(fn=_on_gallery_select, inputs=[models_state], outputs=[selected_md, selected_state], queue=False)

        demo.launch()


if __name__ == '__main__':
    build_ui()
