import json
import os
from pathlib import Path

import pytest

from top_loras import parser as tl_parser
from top_loras import api as tl_api
from top_loras import download as tl_download
from top_loras import cache as tl_cache


def test_extract_cover_url_basic():
    item = {
        "MuseInfo": {
            "versions": [
                {
                    "coverImages": [
                        {"url": "https://example.com/cover.jpg"}
                    ]
                }
            ]
        }
    }
    assert tl_parser.extract_cover_url(item) == "https://example.com/cover.jpg"


def test_extract_cover_url_missing():
    assert tl_parser.extract_cover_url({}) is None


def test_extract_downloads_various():
    assert tl_parser.extract_downloads({"Downloads": 123}) == 123
    assert tl_parser.extract_downloads({"stats": {"downloads": 456}}) == 456
    assert tl_parser.extract_downloads({"ViewCount": 789}) == 789
    assert tl_parser.extract_downloads({}) == 0


def test_extract_model_info_likes_and_updated():
    item = {
        "Name": "owner/model-a",
        "ChineseName": "示例模型",
        "LikeCount": 12,
        "GmtModified": "2024-01-01T00:00:00Z",
    }
    info = tl_parser.parse_model_entry(item)
    assert info["id"] == "owner/model-a"
    assert info["title_cn"] == "示例模型"
    assert info["likes"] == 12
    assert info["updated_at"] == "2024-01-01T00:00:00Z"


def test_build_search_body_with_task():
    body = tl_api.build_search_body(10, tag='lora', task='text-to-image-synthesis')
    # ensure Criterion contains a tasks category with the value
    cats = [c.get('category') for c in body.get('Criterion', [])]
    assert 'tasks' in cats


def test_extract_model_info_lastupdated():
    # LastUpdatedTime is epoch seconds and should be converted to ISO8601 UTC
    ts = 1760696097
    item = {
        "Name": "owner/model-b",
        "LastUpdatedTime": ts,
    }
    info = tl_parser.parse_model_entry(item)
    import time as _time
    expected = _time.strftime('%Y-%m-%dT%H:%M:%SZ', _time.gmtime(ts))
    assert info['updated_at'] == expected


def test_extract_model_info_user_and_tags():
    item = {
        "Name": "owner/model-c",
        "AigcAttributes": "{\"foo\": \"bar\"}",
        "Avatar": "https://example.com/avatar.png",
        "OfficialTags": [
            {"ChineseName": "写实", "Name": "Photography"},
            {"ChineseName": "风格", "Name": "Style"}
        ],
        "BaseModel": ["Qwen/Qwen-Image"],
        "TriggerWords": ["摄影", "人像"],
        "VisionFoundation": "QWEN_IMAGE_20_B",
        "MuseInfo": {
            "model": {
                "showName": "示例Muse名",
                "operatorName": "opname",
                "operatorEmpId": "12345",
                "stableDiffusionVersion": "QWEN_IMAGE_20_B"
            }
        }
    }

    info = tl_parser.parse_model_entry(item)
    assert info['title_cn'] == '示例Muse名'
    assert info['avatar'] == 'https://example.com/avatar.png'
    assert info['user_name'] == 'opname'
    assert info['user_profile'] == 'https://modelscope.cn/profile/12345'
    assert '写实' in info['tags_cn'] and '风格' in info['tags_cn']
    assert 'Photography' in info['tags_en'] and 'Style' in info['tags_en']
    assert info['base_models'] == ['Qwen/Qwen-Image']
    assert info['trigger_words'] == ['摄影', '人像']
    assert info['vision_foundation'] == 'QWEN_IMAGE_20_B'


def test_download_images_for_results_monkeypatch(tmp_path, monkeypatch):
    # Prepare a fake download_image that writes a file and returns True
    def fake_download(url, dest_path, session=None, retries=2):
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(b"fakeimage")
        return True

    # monkeypatch the download_image in our top_loras.download module
    monkeypatch.setattr('top_loras.download.download_image', fake_download)

    results = [{
        'id': 'owner/model-a',
        'title_en': 'model-a',
        'cover_url': 'https://example.com/cover.png'
    }]

    images_dir = tmp_path / 'images'
    tl_download.download_images_for_results(results, str(images_dir))

    # cover_local should be set and file should exist
    cl = results[0].get('cover_local')
    assert cl is not None
    assert Path(cl).exists()


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


# A simple smoke test that ensures download_image returns False for non-existing URL
# without network access; it's allowed to be flaky if run offline, so we skip on CI if
# HTTP requests are unavailable.
@pytest.mark.skipif(os.getenv('CI') == 'true', reason='Skip live download in CI')
def test_download_image_live(tmp_path):
    dest = tmp_path / 'live.jpg'
    ok = tl_download.download_image('https://example.com/nonexistent.jpg', dest, retries=1)
    # We don't assert success; ensure function returns bool
    assert isinstance(ok, bool)
