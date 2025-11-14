import os, json
from modelscope.hub.api import HubApi

api = HubApi()
token = os.environ.get('MODELSCOPE_API_TOKEN')  # 推荐先 export MODELSCOPE_API_TOKEN
if token:
    api.login(token)
    print("Logged in via token")
else:
    print("No token provided, trying anonymous session (可能受限)")

# 待尝试的可能 path 列表（基于源码与前端习惯）
candidates = [
    '/api/v1/models',           # 可能需要 PUT + body
    '/api/v1/models/search',    # 可能 POST/GET
    '/api/v1/models/',          # 带尾斜线的变体
    '/api/v1/models/list',      # 备选
    '/api/v2/models/search'     # 部分站点有 v2 版本
]

# 常见请求 body（按你在浏览器看到的为准）
body = {
    "filter": "tag:lora",
    "sort": "popularity",
    "page_size": 20,
    "page_number": 1
}
headers = api.builder_headers(api.headers)  # use SDK headers (UA etc)

def try_request(method, full_url, params=None, json_body=None):
    s = api.session
    try:
        if method == 'GET':
            r = s.get(full_url, params=params, headers=headers, timeout=10)
        elif method == 'POST':
            r = s.post(full_url, json=json_body, headers=headers, timeout=10)
        elif method == 'PUT':
            r = s.put(full_url, json=json_body, headers=headers, timeout=10)
        else:
            return None
        print(f"\nTRY {method} {full_url} => {r.status_code}")
        txt = r.text[:2000]
        print("Response snippet:", txt if len(txt) < 2000 else txt[:2000]+"...")
        return r
    except Exception as e:
        print("Exception:", e)
        return None

base = api.endpoint.rstrip('/')
for p in candidates:
    url = base + p if p.startswith('/') else base + '/' + p
    # try GET with params
    try_request('GET', url, params=body)
    # try POST/PUT with json body
    try_request('POST', url, json_body=body)
    try_request('PUT', url, json_body=body)