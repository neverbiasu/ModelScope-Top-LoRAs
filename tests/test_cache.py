import tempfile
from pathlib import Path
from top_loras import cache as tl_cache


def test_save_and_load_cache_roundtrip(tmp_path):
    cache_file = tmp_path / 'cache.json'
    results = [
        {
            'id': 'owner/model-a',
            'title_en': 'model-a',
            'cover_local': str(tmp_path / 'images' / 'model-a.jpg')
        }
    ]
    tl_cache.save_cache(str(cache_file), results)
    loaded = tl_cache.load_cache(str(cache_file), ttl=1000)
    assert isinstance(loaded, list)
    assert loaded[0]['id'] == 'owner/model-a'
