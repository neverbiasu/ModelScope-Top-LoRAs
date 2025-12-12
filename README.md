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
- Exposes a CLI (via `python -m top_loras`) to refresh caches and tune paging/limits.
- Includes a lightweight Gradio app (`app.py`) that reads the cache and renders a styled card grid.









## 📊 Daily Statistics

![Daily Stats](docs/daily_stats.png)

*Statistics updated automatically every day*


## 🏆 Top 3 Models

| # | Cover | Model | Author | Downloads | Likes |
| --- | --- | --- | --- | --- | --- |
| 1 | ![FLUX_xiao_hong_shu_ji_zhi_zhen_shi_V2](https://www.modelscope.cn/models/yiwanji/FLUX_xiao_hong_shu_ji_zhi_zhen_shi_V2/resolve/master/_cover_images_/ee17cac0-5da3-4adc-a052-7d3b187b3609.png) | [FLUX_xiao_hong_shu_ji_zhi_zhen_shi_V2](https://modelscope.cn/yiwanji/FLUX_xiao_hong_shu_ji_zhi_zhen_shi_V2?revision=v1.0) | yiwanji | 61,362 | 237 |
| 2 | ![ArtAug-lora-FLUX.1dev-v1](https://resouces.modelscope.cn/cover-images/1db17e27-74ab-45e2-b2dc-1ed105ac5fe2.jpg) | [ArtAug-lora-FLUX.1dev-v1](https://modelscope.cn/DiffSynth-Studio/ArtAug-lora-FLUX.1dev-v1?revision=v1.0) | Artiprocher | 38,582 | 74 |
| 3 | ![MAJICFLUS-photo](https://www.modelscope.cn/models/WANGMOON/MAJICFLUS-photo/resolve/master/_cover_images_/d1d2079f-66ef-4900-baae-4a0cb571d5e1.png) | [MAJICFLUS-photo](https://modelscope.cn/WANGMOON/MAJICFLUS-photo?revision=v1.0) | WANGMOON | 16,491 | 85 |


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
python -m top_loras --limit 20 --task text-to-image-synthesis --force-refresh
```

Images are downloaded from each record's `cover_url` (HTTP/HTTPS) by default; in typical cases these are public URLs and do not require a ModelScope API token. The CLI supports flags like `--limit`, `--page-size`, `--max-pages`, `--no-per-task-cache`, and `--cache-file`. If a specific resource is protected (returns 401/403), you can provide `MODELSCOPE_API_TOKEN` in the environment or let CI inject it as a secret — but note that tokens are primarily used for generation workflows and are not required for normal image downloads.

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

CI (GitHub Actions) is included and can be configured to run tests and optionally run scheduled fetches. In most cases CI does not need a ModelScope token because images are downloaded via public `cover_url` links; only add `MODELSCOPE_API_TOKEN` as a secret if you need to access protected resources or to run generation steps that require authentication.

## Notes

- The UI intentionally uses a conservative LoRA detection heuristic. If you want to broaden or tighten detection, edit `top_loras/filter.py`.
- Cached images and the `cache/` folder are typically not committed; add `cache/` to `.gitignore` if you want to avoid checking images in.

---

If you'd like, I can commit these README changes and prepare a GitHub Actions workflow to publish cache artifacts to ModelScope (requires knowing whether ModelScope accepts git pushes or an upload API).
