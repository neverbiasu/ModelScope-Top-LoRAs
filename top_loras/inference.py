import os
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from base64 import b64decode

# Tiny transparent PNG data URI as fallback/mock image
_PLACEHOLDER_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
)

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
IMAGE_POLL_INTERVAL = float(os.environ.get("MODELSCOPE_IMAGE_POLL_INTERVAL", "3"))
IMAGE_POLL_MAX_SECONDS = int(os.environ.get("MODELSCOPE_IMAGE_POLL_MAX_SECONDS", "60"))


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _requests_with_retries(method: str, url: str, max_retries: int = MAX_RETRIES, **kwargs):
    """Simple requests wrapper with retry on network errors, 429 and 5xx responses.

    Returns the requests.Response object or raises the last exception.
    """
    try:
        import requests
    except Exception as e:  # pragma: no cover - network optional
        raise RuntimeError(f"requests not available: {e}")

    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            func = getattr(requests, method.lower())
            resp = func(url, **kwargs)
            # Retry on rate limit or server errors
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == max_retries:
                    return resp
                print(f"[{_now_iso()}] Request {method.upper()} {url} returned {resp.status_code}; retry {attempt}/{max_retries}")
                time.sleep(backoff)
                backoff *= 2
                continue
            return resp
        except Exception as exc:
            # Network-level errors (ConnectionError, Timeout, etc.) -> retry
            if attempt == max_retries:
                raise
            print(f"[{_now_iso()}] Request exception for {method.upper()} {url}: {exc}; retry {attempt}/{max_retries}")
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError("Request retries exhausted")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_job_file(task: str, job_id: str, payload: Dict[str, Any]) -> str:
    out_dir = Path("cache") / "outputs" / task
    _ensure_dir(str(out_dir))
    out_file = out_dir / f"{job_id}.json"
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_file)


def _remote_infer_image(model_id: str, params: Dict[str, Any], token: str) -> Dict[str, Any]:
    """Image generation via ModelScope async API.

    Flow:
      1. POST /v1/images/generations with model + prompt (+ optional params) and header X-ModelScope-Async-Mode: true
      2. Poll /v1/tasks/{task_id} with header X-ModelScope-Task-Type: image_generation until SUCCEED/FAILED or timeout.
    Returns dict with status/result/raw.
    """
    try:
        import requests
    except Exception as e:  # pragma: no cover - network optional
        raise RuntimeError(f"requests not available: {e}")

    base = os.environ.get("MODELSCOPE_INFER_BASE", "https://api-inference.modelscope.cn/").rstrip("/") + "/"
    gen_url = base + "v1/images/generations"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-ModelScope-Async-Mode": "true",
    }

    body: Dict[str, Any] = {
        "model": model_id,
        "prompt": params.get("prompt", ""),
    }

    # Optional parameters mapping
    if params.get("negative_prompt"):
        body["negative_prompt"] = params.get("negative_prompt")
    if params.get("size"):
        body["size"] = params.get("size")
    if params.get("seed") is not None:
        body["seed"] = params.get("seed")
    if params.get("steps") is not None:
        body["steps"] = params.get("steps")
    if params.get("guidance") is not None:
        body["guidance"] = params.get("guidance")

    # Submit generation task
    submit_resp = _requests_with_retries("post", gen_url, json=body, headers=headers, timeout=DEFAULT_TIMEOUT)
    if submit_resp.status_code == 401:
        raise RuntimeError("Unauthorized (401) image generation")
    if submit_resp.status_code >= 400:
        # Capture error detail for visibility
        detail = None
        try:
            detail = submit_resp.json()
        except Exception:
            detail = submit_resp.text[:500]
        raise RuntimeError(f"Submit error {submit_resp.status_code}: {detail}")
    submit_data = submit_resp.json()
    task_id = submit_data.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in response: {submit_data}")

    poll_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-ModelScope-Task-Type": "image_generation",
    }
    task_url = base + f"v1/tasks/{task_id}"
    deadline = time.time() + IMAGE_POLL_MAX_SECONDS
    last_data = None
    while time.time() < deadline:
        poll_resp = _requests_with_retries("get", task_url, headers=poll_headers, timeout=DEFAULT_TIMEOUT)
        if poll_resp.status_code == 401:
            raise RuntimeError("Unauthorized (401) while polling task")
        if poll_resp.status_code >= 400:
            detail = None
            try:
                detail = poll_resp.json()
            except Exception:
                detail = poll_resp.text[:500]
            raise RuntimeError(f"Poll error {poll_resp.status_code}: {detail}")
        data = poll_resp.json()
        last_data = data
        status = data.get("task_status")
        if status == "SUCCEED":
            output_images = data.get("output_images") or []
            result = {
                "task_id": task_id,
                "images": output_images,
                "model_id": model_id,
                "prompt": body.get("prompt", ""),
            }
            # Optionally download first image for local display convenience
            local_paths = []
            try:
                if output_images:
                    first = output_images[0]
                    if isinstance(first, str) and first.startswith("http"):
                        img_resp = _requests_with_retries("get", first, timeout=DEFAULT_TIMEOUT)
                        try:
                            img_resp.raise_for_status()
                        except Exception:
                            raise
                        img_dir = Path("cache") / "outputs" / "images"
                        img_dir.mkdir(parents=True, exist_ok=True)
                        file_path = img_dir / f"gen_{uuid.uuid4().hex[:10]}.jpg"
                        file_path.write_bytes(img_resp.content)
                        local_paths.append(str(file_path))
                        result["images_local"] = local_paths
            except Exception as _dl_exc:  # pragma: no cover
                result["download_error"] = str(_dl_exc)
            return {"status": "succeeded", "result": result, "raw": data}
        if status == "FAILED":
            err = data.get("error") or data
            raise RuntimeError(f"Image generation failed: {err}")
        else:
            # Log intermediate or unknown statuses for debugging and clarity
            print(f"[{_now_iso()}] Polling task {task_id}: status={status!r}")
        time.sleep(IMAGE_POLL_INTERVAL)
    raise RuntimeError(f"Image generation timeout after {IMAGE_POLL_MAX_SECONDS}s; last data={last_data}")


def _remote_infer(model_id: str, params: Dict[str, Any], token: str) -> Dict[str, Any]:
    """Dispatch remote inference by task type.

    For text-to-image / image generation tasks, use async image endpoint.
    Otherwise raise (or could extend later for other modalities).
    """
    task = (params.get("task") or "").lower()
    if "image" in task or "text-to-image" in task:
        return _remote_infer_image(model_id, params, token)
    raise RuntimeError(f"Unsupported remote task for this prototype: {task}")


def _mock_infer(model_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a mock result and write a tiny transparent PNG file so that gr.Image can display it.

    Gradio Image component prefers file paths / PIL images over data URIs, so we persist a PNG file.
    """
    # Decode the 1x1 transparent PNG from the data URI for actual file output
    png_b64 = _PLACEHOLDER_DATA_URI.split(",", 1)[-1]
    img_bytes = b64decode(png_b64)
    out_dir = Path("cache") / "outputs" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"mock_{uuid.uuid4().hex[:10]}.png"
    file_path = out_dir / file_name
    try:
        file_path.write_bytes(img_bytes)
    except Exception:
        # Fallback: still return data URI if write fails
        file_path = None

    result = {
        "image": str(file_path) if file_path else _PLACEHOLDER_DATA_URI,
        "model_id": model_id,
        "prompt": params.get("prompt", ""),
        "seed": params.get("seed", 0),
    }
    return {"status": "succeeded", "result": result}


def submit_job(model_id: str, params: Dict[str, Any], token: Optional[str] = None) -> Dict[str, Any]:
    """
    Submit a generation job. If token is provided, try remote inference with retries.
    Otherwise or on failure, return a local mock result.

    Writes job payload to cache/outputs/{task}/{job_id}.json with meta/status/result.
    """
    task = (params.get("task") or "unknown").replace("/", "_")
    job_id = params.get("job_id") or uuid.uuid4().hex[:12]

    meta = {
        "job_id": job_id,
        "task": task,
        "model_id": model_id,
        "created_at": _now_iso(),
    }

    # Try remote path if token provided
    payload: Dict[str, Any]
    if token:
        try:
            remote = _remote_infer(model_id, params, token)
            payload = {"meta": meta, "status": remote.get("status", "succeeded"), "result": remote.get("result"), "remote": True}
        except Exception as e:
            # Fall back to mock but preserve error for UI visibility
            payload = {"meta": meta, "status": "succeeded", "result": _mock_infer(model_id, params)["result"], "remote": False, "error": str(e), "mock": True}
    else:
        payload = {"meta": meta, "status": "succeeded", "result": _mock_infer(model_id, params)["result"], "remote": False, "mock": True}

    file_path = _write_job_file(task, job_id, payload)
    payload["file_path"] = file_path
    return payload
