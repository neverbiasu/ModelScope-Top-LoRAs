"""Test UI callback functions."""

import pytest
from ui.callbacks import on_gallery_select


def test_on_gallery_select_with_valid_index():
    """Test gallery selection with valid index."""
    # Mock event object with index
    class MockEvent:
        def __init__(self, idx):
            self.index = idx
    
    # Mock models list
    models = [
        {"id": "model1", "title_en": "Model One", "author": "Author A", "downloads": 100, "likes": 10},
        {"id": "model2", "title_en": "Model Two", "author": "Author B", "downloads": 200, "likes": 20},
    ]
    
    evt = MockEvent(0)
    summary, selected, gen_md, model_id = on_gallery_select(evt, models, lang="en")
    
    assert "Model One" in summary
    assert selected == models[0]
    assert model_id == "model1"
    assert "Selected:" in gen_md


def test_on_gallery_select_with_invalid_index():
    """Test gallery selection with invalid index."""
    class MockEvent:
        def __init__(self, idx):
            self.index = idx
    
    models = [{"id": "model1", "title_en": "Model One"}]
    
    # Test out of range
    evt = MockEvent(10)
    summary, selected, gen_md, model_id = on_gallery_select(evt, models, lang="en")
    
    assert "No model selected" in summary
    assert selected is None
    assert model_id == ""


def test_on_gallery_select_with_empty_models():
    """Test gallery selection with empty models list."""
    class MockEvent:
        def __init__(self, idx):
            self.index = idx
    
    evt = MockEvent(0)
    summary, selected, gen_md, model_id = on_gallery_select(evt, [], lang="en")
    
    assert "No model selected" in summary
    assert selected is None


def test_on_gallery_select_with_missing_index():
    """Test gallery selection when event has no index attribute."""
    class MockEvent:
        pass
    
    models = [{"id": "model1", "title_en": "Model One"}]
    evt = MockEvent()
    
    summary, selected, gen_md, model_id = on_gallery_select(evt, models, lang="en")
    
    assert "No model selected" in summary
    assert selected is None
