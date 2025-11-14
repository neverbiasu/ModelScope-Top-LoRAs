from modelscope.hub.api import HubApi
import os
from dotenv import load_dotenv
import pprint

load_dotenv()


def probe_filters(limit=50):
    api = HubApi()
    token = os.environ.get('MODELSCOPE_API_TOKEN')
    if token:
        api.login(token)
        print('Logged in via token')
    else:
        print('No token provided: using anonymous session')

    base = api.endpoint.rstrip('/')
    url = base + '/api/v1/models'

    candidate_bodies = [
        {'Filter': 'tag:lora', 'PageNumber': 1, 'PageSize': limit},
        {'Filter': 'tag:LoRA', 'PageNumber': 1, 'PageSize': limit},
        {'Filter': 'Tags:LoRA', 'PageNumber': 1, 'PageSize': limit},
        {'Filter': 'OfficialTags:LoRA', 'PageNumber': 1, 'PageSize': limit},
        {'Filter': 'ModelType:LoRA', 'PageNumber': 1, 'PageSize': limit},
        {'Filter': 'AigcType:LoRA', 'PageNumber': 1, 'PageSize': limit},
        {'Filter': 'Libraries:lora', 'PageNumber': 1, 'PageSize': limit},
        {'Filter': 'q:lora', 'PageNumber': 1, 'PageSize': limit},
        {'Query': 'lora', 'PageNumber': 1, 'PageSize': limit},
        {'Keyword': 'lora', 'PageNumber': 1, 'PageSize': limit},
        # no filter (raw listing)
        {'PageNumber': 1, 'PageSize': limit},
    ]

    headers = api.builder_headers(api.headers)

    def find_lora_paths(obj, path=''):
        """Recursively find paths within obj where 'lora' (case-insensitive) appears.

        Returns list of (path, snippet) tuples where snippet is a short repr of the matching value.
        """
        matches = []
        try:
            if obj is None:
                return matches
            if isinstance(obj, str):
                if 'lora' in obj.lower():
                    matches.append((path or '<root>', obj))
                return matches
            if isinstance(obj, (int, float, bool)):
                return matches
            if isinstance(obj, dict):
                for k, v in obj.items():
                    subpath = f"{path}.{k}" if path else k
                    matches.extend(find_lora_paths(v, subpath))
                return matches
            if isinstance(obj, (list, tuple)):
                for i, v in enumerate(obj):
                    subpath = f"{path}[{i}]" if path else f"[{i}]"
                    matches.extend(find_lora_paths(v, subpath))
                return matches
            # fallback
            s = str(obj)
            if 'lora' in s.lower():
                matches.append((path or '<root>', s))
        except Exception:
            return matches
        return matches

    def contains_lora(obj):
        return len(find_lora_paths(obj)) > 0

    for body in candidate_bodies:
        print('=' * 80)
        print('Trying body:', body)
        try:
            resp = api.session.put(url, json=body, headers=headers, timeout=20)
            print('status', resp.status_code)
            resp.raise_for_status()
            j = resp.json()
            data = j.get('Data') or j
            models = []
            if isinstance(data, dict):
                # try several common keys
                models = data.get('Models') or data.get('models') or data.get('Items') or []
            elif isinstance(data, list):
                models = data

            print('returned models count (len list):', len(models))

            # Print unique name/id counts to detect duplicates like LongCat repeats
            from collections import Counter
            name_keys = []
            for m in models:
                nm = None
                if isinstance(m, dict):
                    nm = m.get('Name') or m.get('name') or m.get('ChineseName') or m.get('Id') or m.get('Path')
                if not nm:
                    nm = '<unknown>'
                name_keys.append(nm)
            counts = Counter(name_keys)
            print('Unique model count:', len(counts))
            print('Top 20 models by occurrence:')
            for name, cnt in counts.most_common(20):
                print(f'  {cnt:3d} x {name}')

            # scan models for lora mentions
            match_count = 0
            first_match = None
            for m in models:
                paths = find_lora_paths(m)
                if paths:
                    match_count += 1
                    if first_match is None:
                        first_match = m
                        first_paths = paths

            print('match_count (contains "lora"):', match_count)
            if first_match is not None:
                print('Sample matching model keys:')
                pprint.pprint(list(first_match.keys())[:200])
                print('\nFields/paths where "lora" was found (path -> snippet):')
                for p, snippet in first_paths[:20]:
                    print(f"  {p}: {repr(snippet)[:400]}")
                # print a few candidate fields to inspect
                for f in ('Name', 'ChineseName', 'Tags', 'OfficialTags', 'Libraries', 'ModelInfos', 'ModelRevisions', 'Description', 'ModelType', 'Path'):
                    if f in first_match:
                        print(f'  {f}:', repr(first_match.get(f))[:400])
            else:
                # show sample model keys to inspect why nothing matched
                if models:
                    print('No matches found; sample model keys:')
                    pprint.pprint(list(models[0].keys())[:200])
            # if data had other list-like keys, display them
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (list, tuple)) and k not in ('Models', 'models', 'Items'):
                        print(f"Data['{k}'] is a list with length={len(v)}")
        except Exception as e:
            print('request failed:', e)


if __name__ == '__main__':
    probe_filters(50)
