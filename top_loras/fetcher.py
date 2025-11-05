"""
Fetcher module moved into package for cleaner imports.

Exports fetch_top_loras and fetch_top20_loras for compatibility.
"""
import traceback
import json
import logging
from typing import Optional
from pathlib import Path

from .download import sanitize_filename, download_images_for_results
from .cache import load_cache, save_cache
from . import api as tl_api
from . import filter as tl_filter
from . import parser as tl_parser

import requests
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return None
try:
    from modelscope.hub.api import HubApi
except Exception:
    class HubApi:
        def __init__(self):
            self.endpoint = 'https://www.modelscope.cn'
            self.headers = {}
            class _S:
                def put(self, *a, **k):
                    raise RuntimeError('HubApi.put not available in stub')
            self.session = _S()
        def builder_headers(self, headers):
            return {}
        def login(self, token):
            return None

# Load .env from repository root for MODELSCOPE_API_TOKEN
load_dotenv()

# Constants (re-exported for backward compatibility)
DEFAULT_LIMIT = 20
DEFAULT_TAG = 'lora'
DEFAULT_TIMEOUT = 20
DEFAULT_CACHE_FILE = 'cache/top_loras.json'
DEFAULT_IMAGES_DIR = 'cache/images'

# Preset tasks we support for batch runs
TASK_PRESETS = {
    'text-to-image': 'text-to-image-synthesis',
    'image-to-video': 'image-to-video',
}

# Logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def fetch_top_loras(limit=DEFAULT_LIMIT, tag=DEFAULT_TAG, token_env='MODELSCOPE_API_TOKEN', debug=False,
                    cache_file: str = DEFAULT_CACHE_FILE, images_dir: str = DEFAULT_IMAGES_DIR,
                    ttl: int = 300, force_refresh: bool = False, download_images: bool = True,
                    task: Optional[str] = None, page_size: Optional[int] = None, max_pages: int = 5,
                    per_task_cache: bool = True):
    """Fetch top LoRA models from ModelScope (package version).

    Logic preserved from top-level script, but using package-relative imports.
    """
    # per-task cache defaulting
    if per_task_cache and cache_file == DEFAULT_CACHE_FILE and task:
        safe_task = sanitize_filename(task)
        cache_file = f"cache/top_loras_{safe_task}.json"
        if images_dir == DEFAULT_IMAGES_DIR:
            images_dir = f"cache/images/{safe_task}"

    if not force_refresh:
        cached = load_cache(cache_file, ttl=ttl)
        if cached:
            if debug:
                print(f"[debug] Using cached results from {cache_file}")
            return cached

    # Fetch raw models via API helper
    models = tl_api.fetch_models(limit=limit, tag=tag, task=task, debug=debug, token_env=token_env,
                                 page_size=page_size, max_pages=max_pages)

    if debug:
        print(f"[debug] Extracted {len(models)} models")

    # Process and filter models
    results = tl_filter.process_models(models, debug=debug)

    if debug:
        print(f"[debug] Found {len(results)} LoRA candidates after filtering")

    final_results = tl_filter.deduplicate_models(results, limit)

    if debug:
        print(f"[debug] Returning top {len(final_results)} models")

    if download_images:
        try:
            download_images_for_results(final_results, images_dir)
            if debug:
                print(f"[debug] Downloaded images to {images_dir}")
        except Exception as e:
            logger.warning(f"Failed to download images: {e}")

    try:
        save_cache(cache_file, final_results)
        if debug:
            print(f"[debug] Saved cache to {cache_file}")
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")

    return final_results


def fetch_top20_loras(limit=20, tag='lora', token_env='MODELSCOPE_API_TOKEN', debug=False):
    return fetch_top_loras(limit=limit, tag=tag, token_env=token_env, debug=debug)


def main():
    try:
        from . import cli
        cli.main()
    except Exception as e:
        logger.error(f"CLI failed: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    main()
