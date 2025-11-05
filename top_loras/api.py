import os
import time
import json
from typing import Optional

DEFAULT_TIMEOUT = 20
MODELSCOPE_ENDPOINT = '/api/v1/dolphin/models'

try:
    from modelscope.hub.api import HubApi
except Exception:
    class HubApi:
        def __init__(self):
            self.endpoint = 'https://www.modelscope.cn'
            self.headers = {}
            class _S:
                def put(self, *a, **k):
                    raise RuntimeError('HubApi.put not available in stub')
            self.session = _S()
        def builder_headers(self, headers):
            return {}
        def login(self, token):
            return None

def build_search_body(limit, tag='lora', task: Optional[str] = None, page_number: int = 1):
    body = {
        'PageSize': limit,
        'PageNumber': page_number,
        'SortBy': 'Default',
        'Target': '',
        'Criterion': [
            {'category': 'tags', 'predicate': 'contains', 'values': [tag]}
        ],
        'SingleCriterion': []
    }
    if task:
        body['Criterion'].append({'category': 'tasks', 'predicate': 'contains', 'values': [task]})
    return body


def build_headers(api, csrf_token=None):
    headers = api.builder_headers(api.headers) if hasattr(api, 'builder_headers') else {}
    if csrf_token:
        headers['X-Csrf-Token'] = csrf_token
    return headers


def fetch_models(limit=20, tag='lora', task: Optional[str] = None,
                 debug: bool = False, token_env: str = 'MODELSCOPE_API_TOKEN',
                 page_size: Optional[int] = None, max_pages: int = 5):
    """
    Return a list of raw model dicts either by reading an offline JSON or by paginated
    requests to the ModelScope frontend API.
    """
    # Online path
    api = HubApi()
    token = os.environ.get(token_env)
    if token:
        try:
            api.login(token)
            if debug:
                print('Logged in via token')
        except Exception:
            if debug:
                print('Token provided but login failed or not supported in stub')
    else:
        if debug:
            print('No token provided: using anonymous session (may be limited)')

    base = api.endpoint.rstrip('/')
    url = base + MODELSCOPE_ENDPOINT
    csrf_token = os.environ.get('MODELSCOPE_CSRF_TOKEN')
    headers = build_headers(api, csrf_token)

    collected_models = []
    # allow caller to control paging for tuning/diagnostics
    page_size = page_size if page_size is not None else min(max(limit * 4, 50), 200)

    for page in range(1, max_pages + 1):
        body = build_search_body(page_size, tag, task, page_number=page)
        if debug:
            print(f"[debug] sending request to: {url} page={page} page_size={page_size}")
        try:
            response = api.session.put(url, json=body, headers=headers, timeout=DEFAULT_TIMEOUT)
        except Exception as e:
            raise RuntimeError(f"Failed to perform API request: {e}\nIf you are running offline, provide --offline-file <path> or install the 'modelscope' package.")
        if getattr(response, 'status_code', None) == 401:
            raise RuntimeError('Unauthorized: API requires login. Export MODELSCOPE_API_TOKEN or login first.')

        response.raise_for_status()
        page_json = response.json()

        # Debug: print status and top-level keys to diagnose empty responses
        if debug:
            try:
                top_keys = list(page_json.keys()) if isinstance(page_json, dict) else type(page_json)
            except Exception:
                top_keys = None
            print(f"[debug] page={page} status={getattr(response, 'status_code', None)} top_keys={top_keys}")
            # Summarize Data field if present
            dp = page_json.get('Data') if isinstance(page_json, dict) else None
            if dp is None:
                print(f"[debug] page={page} Data missing or null; full_response_snippet={str(page_json)[:1000]}")
            else:
                try:
                    if isinstance(dp, dict):
                        print(f"[debug] page={page} Data keys={list(dp.keys())} -> types={[type(v).__name__ for v in dp.values()][:10]}")
                    elif isinstance(dp, list):
                        print(f"[debug] page={page} Data is a list of length {len(dp)}")
                    else:
                        print(f"[debug] page={page} Data type={type(dp)} snippet={str(dp)[:200]}")
                except Exception as e:
                    print(f"[debug] page={page} failed to summarize Data: {e}")

        data_page = page_json.get('Data') or page_json

        # extract models list heuristically
        models_page = []
        for key in ('Models', 'models', 'Items', 'Model', 'List', 'Hits'):
            v = data_page.get(key) if isinstance(data_page, dict) else None
            if isinstance(v, list):
                models_page = v
                break
            # if v is a dict, try to find a list inside it (e.g. Model -> Items)
            if isinstance(v, dict):
                for sub in ('Models', 'models', 'Items', 'List', 'Hits'):
                    vv = v.get(sub)
                    if isinstance(vv, list):
                        models_page = vv
                        break
                if models_page:
                    break
        if not models_page and isinstance(data_page, dict):
            for v in data_page.values():
                # if value is a list, use it
                if isinstance(v, list):
                    models_page = v
                    break
                # if value is a dict, try to find list inside
                if isinstance(v, dict):
                    for vv in v.values():
                        if isinstance(vv, list):
                            models_page = vv
                            break
                    if models_page:
                        break

        if debug:
            print(f"[debug] page {page} extracted {len(models_page)} models")

        if not models_page:
            break

        collected_models.extend(models_page)
        if len(collected_models) >= limit * 4:
            break

    return collected_models
