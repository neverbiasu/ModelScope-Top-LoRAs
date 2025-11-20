#!/usr/bin/env python3
"""
Entry point script for fetching top LoRA models from ModelScope.
This script wraps the CLI functionality provided by the top_loras package.

When imported as a module, it re-exports key attributes from top_loras.fetcher
for backward compatibility with app.py and ui/loaders.py.
"""

from top_loras.cli import main
from top_loras.fetcher import (
    DEFAULT_CACHE_FILE,
    DEFAULT_IMAGES_DIR,
    TASK_PRESETS,
    fetch_top_loras,
    fetch_top20_loras,
)

# Re-export for backward compatibility
__all__ = [
    'main',
    'DEFAULT_CACHE_FILE',
    'DEFAULT_IMAGES_DIR',
    'TASK_PRESETS',
    'fetch_top_loras',
    'fetch_top20_loras',
]

if __name__ == '__main__':
    main()
