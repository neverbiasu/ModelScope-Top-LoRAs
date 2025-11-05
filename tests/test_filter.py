from top_loras import filter as tl_filter


def test_contains_lora():
    assert tl_filter.contains_lora('This is a LoRA model')
    assert tl_filter.contains_lora(['foo', 'lora'])
    assert not tl_filter.contains_lora('checkpoint')


def test_is_lora_candidate_by_aigc():
    item = {'AigcType': 'LoRA'}
    assert tl_filter.is_lora_candidate(item)


def test_process_models_skips_light_distill():
    models = [
        {'Name': 'Good-Lora', 'AigcType': 'lora'},
        {'Name': 'Some-Light-Variant', 'AigcType': 'lora'},
    ]
    res = tl_filter.process_models(models, debug=False)
    ids = [r.get('id') for r in res]
    assert any('Good-Lora' in (i or '') for i in ids)
    assert not any('Some-Light-Variant' in (i or '') for i in ids)
