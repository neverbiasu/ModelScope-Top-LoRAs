"""Thin compatibility wrapper kept for backward compatibility.

This file simply re-exports the package implementation so callers that do
``python fetch_top_models.py`` or ``from fetch_top_models import fetch_top_loras``
continue to work.
"""
from top_loras.fetcher import fetch_top_loras, fetch_top20_loras, DEFAULT_CACHE_FILE, DEFAULT_IMAGES_DIR, TASK_PRESETS


def main():
    try:
        from top_loras import cli
        cli.main()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"CLI failed: {e}")


if __name__ == '__main__':
    main()
