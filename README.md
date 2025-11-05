---
# 详细文档见https://modelscope.cn/docs/%E5%88%9B%E7%A9%BA%E9%97%B4%E5%8D%A1%E7%89%87
domain: #领域：cv/nlp/audio/multi-modal/AutoML
# - cv
tags: #自定义标签
-
datasets: #关联数据集
  evaluation:
  #- iic/ICDAR13_HCTR_Dataset
  test:
  #- iic/MTWI
  train:
  #- iic/SIBR
models: #关联模型
#- iic/ofa_ocr-recognition_general_base_zh

## 启动文件(若SDK为Gradio/Streamlit，默认为app.py, 若为Static HTML, 默认为index.html)
# deployspec:
#   entry_file: app.py
license: MIT License
---
# Top-LoRAs

## Project Summary

This repository provides a pipeline and a small read-only Gradio UI to build a "Top LoRAs" leaderboard from ModelScope frontend responses. It:

- Fetches the ModelScope frontend JSON and extracts model metadata.
- Applies conservative LoRA detection and filtering rules to avoid false positives.
- Caches a compact JSON file (no raw blobs) and optionally downloads cover images to `cache/`.
- Exposes a CLI (`fetch_top_models.py`) to refresh caches and tune paging/limits.
- Includes a lightweight Gradio app (`app.py`) that reads the cache and renders a styled card grid.

## Quick start

1. Create and activate a Python environment (example using conda):

```bash
conda create -n ms python=3.10 -y
conda activate ms
pip install -r requirements.txt
```

2. Run the Gradio app (reads cache from `cache/top_loras_text-to-image-synthesis.json` by default):

```bash
python app.py
```

Open http://127.0.0.1:7860 in your browser.

3. Refresh the cache from ModelScope (optional):

```bash
python fetch_top_models.py --limit 20 --task text-to-image-synthesis --force-refresh
```

The CLI supports flags like `--limit`, `--page-size`, `--max-pages`, `--no-images`, `--no-per-task-cache`, and `--cache-file`.

## Cache schema (short)

The cache JSON contains at top level a `_cached_at` timestamp and `results` array. Each result includes fields such as:

- `id`, `title_cn`, `title_en`, `author`, `author_avatar` (optional),
- `cover_url`, `cover_local` (if downloaded), `downloads`, `likes`,
- `tags_cn`, `tags_en`, `base_models`, `stable_diffusion_version`,
- `trigger_words`, `vision_foundation`, `updated_at`, `modelscope_url`.

See `DATA_INTERFACE.md` for a full table of fields and extraction fallbacks.

## Two-remote workflow (GitHub + ModelScope)

If you want to keep this repository in two remotes (for example GitHub and a ModelScope studio git), you can add both remotes locally and push to both:

```bash
# add GitHub remote
git remote add github git@github.com:<user>/<repo>.git

# add ModelScope remote (example)
git remote add modelscope git@github.com:...  # replace with your ModelScope git URL or use HTTPS token

# push to both
git push -u github main
git push -u modelscope main
```

If ModelScope does not expose a git remote, consider using GitHub Actions to upload `cache/*.json` artifacts or call ModelScope's API to publish artifacts; I can provide a workflow template if you want.

## Tests and CI

Run tests locally with:

```bash
pytest -q
```

CI (GitHub Actions) is included and can be configured to run tests and optionally run scheduled fetches. To let CI access ModelScope, add the appropriate secrets (API token or SSH key) in GitHub repository settings.

## Notes

- The UI intentionally uses a conservative LoRA detection heuristic. If you want to broaden or tighten detection, edit `top_loras/filter.py`.
- Cached images and the `cache/` folder are typically not committed; add `cache/` to `.gitignore` if you want to avoid checking images in.

---

If you'd like, I can commit these README changes and prepare a GitHub Actions workflow to publish cache artifacts to ModelScope (requires knowing whether ModelScope accepts git pushes or an upload API).
