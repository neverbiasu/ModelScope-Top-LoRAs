import json
import time
from pathlib import Path
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def load_cache(cache_file: str, ttl: int = 300) -> Optional[dict]:
    """Load cached JSON if present and not expired.

    Returns the cached dict or None if missing/expired/invalid.
    """
    p = Path(cache_file)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        ts = data.get('_cached_at')
        if not ts:
            return None
        if time.time() - float(ts) > ttl:
            return None
        return data.get('results')
    except Exception as e:
        logger.warning(f"Failed to load cache {cache_file}: {e}")
        return None


def save_cache(cache_file: str, results: list):
    """Save results to cache file with timestamp."""
    p = Path(cache_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {'_cached_at': time.time(), 'results': results}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
