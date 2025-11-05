import time
from top_loras import parser


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
    assert parser.extract_cover_url(item) == "https://example.com/cover.jpg"


def test_extract_downloads_various():
    assert parser.extract_downloads({"Downloads": 123}) == 123
    assert parser.extract_downloads({"stats": {"downloads": 456}}) == 456
    assert parser.extract_downloads({"ViewCount": 789}) == 789
    assert parser.extract_downloads({}) == 0


def test_parse_model_entry_basic():
    item = {
        "Name": "owner/model-a",
        "ChineseName": "示例模型",
        "LikeCount": 12,
        "GmtModified": "2024-01-01T00:00:00Z",
    }
    info = parser.parse_model_entry(item)
    assert info["id"] == "owner/model-a"
    assert info["title_cn"] == "示例模型"
    assert info["likes"] == 12
    assert info["updated_at"] == "2024-01-01T00:00:00Z"
