import re
import traceback
from .parser import parse_model_entry


def contains_lora(obj):
    try:
        if obj is None:
            return False
        if isinstance(obj, str):
            return 'lora' in obj.lower()
        if isinstance(obj, (list, tuple)):
            return any(contains_lora(x) for x in obj)
        if isinstance(obj, dict):
            return any(contains_lora(v) for v in obj.values())
        return 'lora' in str(obj).lower()
    except Exception:
        return False


def is_lora_candidate(item):
    if not isinstance(item, dict):
        return False
    try:
        if str(item.get('AigcType') or '').strip().lower() == 'lora':
            return True
        muse = item.get('MuseInfo') or {}
        muse_model = muse.get('model') if isinstance(muse, dict) else None
        if isinstance(muse_model, dict) and str(muse_model.get('modelType') or '').strip().lower() == 'lora':
            return True

        ot = item.get('OfficialTags') or []
        if isinstance(ot, list) and any(isinstance(t, dict) and (('lora' in (t.get('Tag') or '').lower()) or ('lora' in (t.get('Name') or '').lower())) for t in ot):
            return True

        if contains_lora(item.get('Name')) or contains_lora(item.get('NickName')):
            return True

        minfo = item.get('ModelInfos') or {}
        if isinstance(minfo, dict):
            for v in minfo.values():
                if isinstance(v, dict):
                    files = v.get('files') or []
                    if isinstance(files, list):
                        for f in files:
                            fname = f.get('name') if isinstance(f, dict) else f
                            if fname and 'lora' in str(fname).lower():
                                return True

        return False
    except Exception:
        return False


def process_models(models, debug=False):
    results = []
    for idx, item in enumerate(models):
        try:
            if not isinstance(item, dict):
                continue
            name_field = (item.get('Name') or item.get('name') or '')
            if isinstance(name_field, str) and re.search(r'(light|distill)', name_field, flags=re.IGNORECASE):
                if debug:
                    print(f"[debug] Skipping model due to name filter (Light/Distill): {name_field}")
                continue

            if not is_lora_candidate(item):
                continue

            model_info = parse_model_entry(item)
            results.append(model_info)
        except Exception as e:
            if debug:
                print(f"[error] Exception processing model index={idx}: {e}")
                traceback.print_exc()
            continue
    return results


def deduplicate_models(results, limit):
    unique = {}
    for idx, r in enumerate(results):
        rid = r.get('id') or r.get('title_en') or r.get('title_cn')
        if rid is None:
            rid = f"unknown-{idx}"
        existing = unique.get(rid)
        if existing is None or r.get('downloads', 0) > existing.get('downloads', 0):
            unique[rid] = r
    return sorted(unique.values(), key=lambda x: x.get('downloads', 0), reverse=True)[:limit]
