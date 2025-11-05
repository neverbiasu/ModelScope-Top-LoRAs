import re
import time
from pathlib import Path
from typing import Optional
import requests
import logging

logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """Make a filesystem-safe filename from name."""
    name = name or 'model'
    # remove unsafe chars
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = re.sub(r'\s+', '_', name)
    # limit length
    return name[:200]


def download_image(url: str, dest_path: Path, session: Optional[requests.Session] = None, retries: int = 2) -> bool:
    """Download image to dest_path. Returns True on success."""
    if dest_path.exists():
        return True
    sess = session or requests.Session()
    for attempt in range(1, retries + 1):
        try:
            r = sess.get(url, timeout=15, stream=True)
            r.raise_for_status()
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception as e:
            logger.debug(f"Download attempt {attempt} failed for {url}: {e}")
            time.sleep(1 * attempt)
    return False


def download_images_for_results(results: list, images_dir: str, session: Optional[requests.Session] = None):
    """Download cover images for each result and update `cover_local` field.

    Images are saved as <images_dir>/<sanitized_title>.<ext>
    """
    base = Path(images_dir)
    base.mkdir(parents=True, exist_ok=True)
    sess = session or requests.Session()
    for r in results:
        url = r.get('cover_url')
        # Use English title or ID for filename to avoid issues with special characters
        title = r.get('title_en') or r.get('id') or 'model'
        if not url:
            r['cover_local'] = None
            continue
        # derive extension
        ext = Path(url).suffix.split('?')[0] or '.jpg'
        filename = sanitize_filename(title) + ext
        dest = base / filename
        ok = download_image(url, dest, session=sess)
        r['cover_local'] = str(dest) if ok else None
