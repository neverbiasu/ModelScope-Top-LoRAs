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
TASK_NOT_FOUND_GRACE_SECONDS = int(os.environ.get("MODELSCOPE_TASK_NOT_FOUND_GRACE", "15"))


def _is_stub_task_response(data: Any) -> bool:
    """Detect a likely "stub" task response (empty task_id/request_id) some gateways return."""
    if not isinstance(data, dict):
        return False
    status = data.get("task_status")
    if status not in ("PENDING", "RUNNING", "PROCESSING"):
        return False
    if data.get("task_id") not in (None, ""):
        return False
    if data.get("request_id") not in (None, ""):
        return False
    outputs = data.get("outputs")
    return outputs == {} or outputs is None


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


def _is_likely_lora_model(model_id: str) -> bool:
    """Check if model is likely a LoRA (fine-tuned) model vs official base model."""
    model_lower = model_id.lower()
    # Official models typically start with AI-ModelScope, damo, iic, etc.
    official_prefixes = ("ai-modelscope/", "damo/", "iic/", "pai/", "zhongjie/")
    if model_lower.startswith(official_prefixes):
        return False
    # LoRA indicators in model name
    lora_indicators = ("lora", "flux", "sdxl", "dreambooth", "finetune", "train", "style", "character")
    return any(indicator in model_lower for indicator in lora_indicators)


def _suggest_alternative_model(model_id: str) -> str:
    """Suggest an alternative official model based on the model name."""
    model_lower = model_id.lower()
    if "flux" in model_lower or "sdxl" in model_lower:
        return "AI-ModelScope/stable-diffusion-xl"
    elif "sd" in model_lower or "stable" in model_lower:
        return "AI-ModelScope/stable-diffusion-v1-5"
    else:
        return "AI-ModelScope/stable-diffusion-xl"


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
    
    # Clean and validate token
    clean_token = token.strip().strip('"').strip("'")
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token.split(None, 1)[-1].strip()
    
    # Validate model_id format (should be owner/model-name)
    if not model_id or "/" not in model_id:
        raise RuntimeError(
            f"Invalid model ID format: '{model_id}'. "
            "Model ID must be in 'owner/model-name' format (e.g., 'AI-ModelScope/stable-diffusion-xl')"
        )
    
    # Debug logging (controlled by environment variable)
    debug = os.environ.get("MODELSCOPE_DEBUG", "").lower() in ("1", "true", "yes")

    # Warn if model is likely a LoRA (debug-only to avoid noisy/incorrect assumptions)
    if debug and _is_likely_lora_model(model_id):
        suggested = _suggest_alternative_model(model_id)
        print(f"[DEBUG] Model '{model_id}' appears to be a LoRA/fine-tuned model.")
        print(f"[DEBUG] Consider using an official base model (example): {suggested}")
    
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Content-Type": "application/json",
        "X-ModelScope-Async-Mode": "true",
    }

    body: Dict[str, Any] = {
        "model": model_id,
        "prompt": params.get("prompt", ""),
    }

    # Optional LoRA(s) parameter per ModelScope examples
    # - str: single lora repo id
    # - str with commas: multiple loras -> list[str]
    # - dict: {lora_repo_id: weight, ...}
    loras_val = params.get("loras")
    if isinstance(loras_val, str):
        loras_val = loras_val.strip()
        if "," in loras_val:
            loras_val = [s.strip() for s in loras_val.split(",") if s.strip()]
    if loras_val is not None:
        body["loras"] = loras_val

    submitted_model = model_id
    submitted_loras = loras_val

    # Optional parameters mapping
    # ModelScope images API commonly accepts: width/height, num_inference_steps, guidance_scale
    if params.get("negative_prompt"):
        body["negative_prompt"] = params.get("negative_prompt")

    size = params.get("size")
    if isinstance(size, str) and "x" in size.lower():
        try:
            w_s, h_s = size.lower().split("x", 1)
            width = int(w_s.strip())
            height = int(h_s.strip())
            if width > 0 and height > 0:
                body["width"] = width
                body["height"] = height
        except Exception:
            # Fall back to raw size if parsing fails
            body["size"] = size
    elif size:
        body["size"] = size

    if params.get("seed") is not None:
        body["seed"] = params.get("seed")
    if params.get("steps") is not None:
        body["num_inference_steps"] = params.get("steps")
    if params.get("guidance") is not None:
        body["guidance_scale"] = params.get("guidance")

    # Minimal body for fallback retries (some models reject extra params)
    minimal_body: Dict[str, Any] = {
        "model": model_id,
        "prompt": params.get("prompt", ""),
    }
    if loras_val is not None:
        minimal_body["loras"] = loras_val
    if params.get("negative_prompt"):
        minimal_body["negative_prompt"] = params.get("negative_prompt")

    if debug:
        print(f"[DEBUG] Request URL: {gen_url}")
        print(f"[DEBUG] Model ID: {model_id}")
        token_info = {
            "len": len(clean_token) if isinstance(clean_token, str) else None,
            "starts_with_ms_dash": bool(isinstance(clean_token, str) and clean_token.startswith("ms-")),
            "prefix": clean_token[:3] if isinstance(clean_token, str) else None,
            "suffix": clean_token[-3:] if isinstance(clean_token, str) else None,
        }
        print(f"[DEBUG] Token info: {token_info}")
        print(f"[DEBUG] Request body(full): {json.dumps(body, ensure_ascii=False)}")
        print(f"[DEBUG] Request body(min): {json.dumps(minimal_body, ensure_ascii=False)}")

    # Submit generation task
    submit_resp = _requests_with_retries("post", gen_url, json=body, headers=headers, timeout=DEFAULT_TIMEOUT)
    if submit_resp.status_code == 401:
        raise RuntimeError(
            "Unauthorized (401): Your API Token is invalid or expired. "
            "Please check your token at https://modelscope.cn/my/myaccesstoken"
        )
    if submit_resp.status_code >= 400:
        # Capture server error detail for visibility (prefer JSON)
        detail: Any
        try:
            detail = submit_resp.json()
        except Exception:
            # Avoid unbounded output but keep more than a tiny snippet
            detail = submit_resp.text[:5000]

        # Retry once with minimal payload on 400 (common for models that don't accept extra params)
        if submit_resp.status_code == 400:
            detail_str = str(detail)
            if debug:
                print("[DEBUG] Submit returned 400; retrying once with minimal payload")
            retry_resp = _requests_with_retries("post", gen_url, json=minimal_body, headers=headers, timeout=DEFAULT_TIMEOUT)
            if retry_resp.status_code < 400:
                submit_resp = retry_resp
                # Refresh detail for debug printing (no longer an error)
                try:
                    detail = submit_resp.json()
                except Exception:
                    detail = submit_resp.text[:5000]
            else:
                try:
                    retry_detail = retry_resp.json()
                except Exception:
                    retry_detail = retry_resp.text[:5000]
                # Prefer the retry error if it differs
                if str(retry_detail) != detail_str:
                    detail = {"first": detail, "retry_minimal": retry_detail}

        # If still 40212, try the official "base model + loras" pattern using Qwen/Qwen-Image as base.
        # - If caller didn't provide loras: treat model_id as the LoRA repo id.
        # - If caller provided loras: keep it and only swap base to Qwen/Qwen-Image.
        if submit_resp.status_code == 400 and "40212" in str(detail):
            target_base = "Qwen/Qwen-Image"
            already_base = (model_id or "").strip() == target_base
            fallback_loras = params.get("loras") if params.get("loras") is not None else model_id
            if not already_base and fallback_loras:
                fallback_body = {
                    "model": target_base,
                    "loras": fallback_loras,
                    "prompt": params.get("prompt", ""),
                }
                if params.get("negative_prompt"):
                    fallback_body["negative_prompt"] = params.get("negative_prompt")
                if debug:
                    print("[DEBUG] 40212 detected; trying fallback base model Qwen/Qwen-Image with loras")
                    print(f"[DEBUG] Fallback body: {json.dumps(fallback_body, ensure_ascii=False)}")
                fb_resp = _requests_with_retries("post", gen_url, json=fallback_body, headers=headers, timeout=DEFAULT_TIMEOUT)
                if fb_resp.status_code < 400:
                    submit_resp = fb_resp
                    submitted_model = target_base
                    submitted_loras = fallback_loras
                    try:
                        detail = submit_resp.json()
                    except Exception:
                        detail = submit_resp.text[:5000]
                else:
                    try:
                        fb_detail = fb_resp.json()
                    except Exception:
                        fb_detail = fb_resp.text[:5000]
                    detail = {"first": detail, "fallback_base_loras": fb_detail}

        if debug:
            print(f"[DEBUG] Response status: {submit_resp.status_code}")
            print(f"[DEBUG] Response headers: {dict(submit_resp.headers)}")
            print(f"[DEBUG] Response body: {detail}")

        # If retries/fallback turned the response into success, continue to normal handling.
        if submit_resp.status_code >= 400:
            # Do NOT rewrite/interpret provider errors here; surface them as-is.
            raise RuntimeError(f"Submit error {submit_resp.status_code}: {detail}")
    submit_data = submit_resp.json()
    task_id = submit_data.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in response: {submit_data}")

    if debug:
        try:
            print(f"[DEBUG] Submit response: {json.dumps(submit_data, ensure_ascii=False)}")
        except Exception:
            print(f"[DEBUG] Submit response: {submit_data}")

    poll_task_type = os.environ.get("MODELSCOPE_TASK_TYPE", "image_generation")

    def _poll_once(task_type: Optional[str]) -> Any:
        headers_local = {
            "Authorization": f"Bearer {clean_token}",
            "Content-Type": "application/json",
        }
        if task_type:
            headers_local["X-ModelScope-Task-Type"] = task_type
        return _requests_with_retries("get", task_url, headers=headers_local, timeout=DEFAULT_TIMEOUT)

    task_url = base + f"v1/tasks/{task_id}"
    deadline = time.time() + IMAGE_POLL_MAX_SECONDS
    started_at = time.time()
    last_data = None
    while time.time() < deadline:
        poll_resp = _poll_once(poll_task_type)
        if poll_resp.status_code == 401:
            raise RuntimeError("Unauthorized (401) while polling task")

        # If the backend says task not found, it may be eventual consistency right after submit.
        if poll_resp.status_code >= 400:
            try:
                detail = poll_resp.json()
            except Exception:
                detail = poll_resp.text[:5000]

            detail_str = str(detail)
            within_grace = (time.time() - started_at) < TASK_NOT_FOUND_GRACE_SECONDS
            if within_grace and ("task not found" in detail_str.lower()):
                if debug:
                    print(f"[DEBUG] Poll got task not found (HTTP {poll_resp.status_code}); retrying within grace window")
                time.sleep(1)
                continue

            raise RuntimeError(f"Poll error {poll_resp.status_code}: {detail}")

        data = poll_resp.json()
        last_data = data

        # Some gateways return a stub response when task type header mismatches.
        # Try again without the task-type header, then with an alternate value.
        if _is_stub_task_response(data):
            if debug:
                print("[DEBUG] Poll returned stub response; retrying without X-ModelScope-Task-Type")
            try:
                alt_resp = _poll_once(None)
                if alt_resp.status_code < 400:
                    alt_data = alt_resp.json()
                    if not _is_stub_task_response(alt_data):
                        poll_resp = alt_resp
                        data = alt_data
                        last_data = alt_data
            except Exception:
                pass

        # If we still have a stub (or later a 'task not found' style FAILED), try alternate task type.
        if (poll_task_type != "aigc") and (_is_stub_task_response(data) or (isinstance(data, dict) and str(data.get("errors", "")).lower().find("task not found") >= 0)):
            if debug:
                print("[DEBUG] Poll trying alternate X-ModelScope-Task-Type: aigc")
            try:
                alt2_resp = _poll_once("aigc")
                if alt2_resp.status_code < 400:
                    alt2_data = alt2_resp.json()
                    if not _is_stub_task_response(alt2_data):
                        poll_resp = alt2_resp
                        data = alt2_data
                        last_data = alt2_data
            except Exception:
                pass

        status = data.get("task_status")
        if status == "SUCCEED":
            output_images = data.get("output_images") or []
            result = {
                "task_id": task_id,
                "images": output_images,
                "model_id": model_id,
                "submitted_model": submitted_model,
                "submitted_loras": submitted_loras,
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
            # If backend returns FAILED with "task not found" shortly after submit, treat as transient.
            within_grace = (time.time() - started_at) < TASK_NOT_FOUND_GRACE_SECONDS
            try:
                errs = data.get("errors") if isinstance(data, dict) else None
                err_msg = (errs.get("message") if isinstance(errs, dict) else None)
            except Exception:
                err_msg = None
            if within_grace and isinstance(err_msg, str) and "task not found" in err_msg.lower():
                if debug:
                    print("[DEBUG] Poll terminal FAILED but task not found; retrying within grace window")
                time.sleep(1)
                continue

            # Some backends may initially return FAILED with an empty errors payload.
            # Re-fetch briefly to capture delayed error details.
            try:
                errs = data.get("errors") if isinstance(data, dict) else None
                empty_err = (
                    isinstance(errs, dict)
                    and errs.get("code") == 0
                    and (errs.get("message") in (None, ""))
                )
            except Exception:
                empty_err = False

            if empty_err:
                for _ in range(2):
                    time.sleep(1)
                    retry_poll = _poll_once(poll_task_type)
                    if retry_poll.status_code >= 400:
                        break
                    try:
                        data = retry_poll.json()
                        last_data = data
                    except Exception:
                        break
                    if debug:
                        try:
                            print(f"[DEBUG] Poll FAILED recheck body: {json.dumps(data, ensure_ascii=False)[:5000]}")
                        except Exception:
                            print(f"[DEBUG] Poll FAILED recheck body: {str(data)[:5000]}")

            # Keep provider response intact, but include task_id for traceability.
            if debug:
                try:
                    print(f"[DEBUG] Poll terminal FAILED body: {json.dumps(data, ensure_ascii=False)}")
                except Exception:
                    print(f"[DEBUG] Poll terminal FAILED body: {data}")
            poll_headers_snapshot = None
            try:
                poll_headers_snapshot = dict(poll_resp.headers)
            except Exception:
                poll_headers_snapshot = None
            if isinstance(data, dict):
                enriched = {
                    "task_id": task_id,
                    "task_url": task_url,
                    # Note: these are *response* headers from the polling request.
                    "poll_response_headers": poll_headers_snapshot,
                    # Back-compat alias (kept for existing logs/tools)
                    "poll_headers": poll_headers_snapshot,
                    "submitted_model": submitted_model,
                    "submitted_loras": submitted_loras,
                    **data,
                }
            else:
                enriched = {
                    "task_id": task_id,
                    "task_url": task_url,
                    "poll_response_headers": poll_headers_snapshot,
                    "poll_headers": poll_headers_snapshot,
                    "submitted_model": submitted_model,
                    "submitted_loras": submitted_loras,
                    "detail": data,
                }
            raise RuntimeError(f"Image generation failed: {enriched}")
        else:
            # Log intermediate or unknown statuses for debugging and clarity
            print(f"[{_now_iso()}] Polling task {task_id}: status={status!r}")
            if debug:
                try:
                    dumped = json.dumps(data, ensure_ascii=False)
                except Exception:
                    dumped = str(data)
                print(f"[DEBUG] Poll body: {dumped[:5000]}")
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
        "loras": params.get("loras"),
        "created_at": _now_iso(),
    }

    # Try remote path if token provided. If remote fails, raise so UI can surface the real error
    # instead of silently returning mock results.
    payload: Dict[str, Any]
    if token:
        remote = _remote_infer(model_id, params, token)
        payload = {"meta": meta, "status": remote.get("status", "succeeded"), "result": remote.get("result"), "remote": True}
    else:
        payload = {"meta": meta, "status": "succeeded", "result": _mock_infer(model_id, params)["result"], "remote": False, "mock": True}

    file_path = _write_job_file(task, job_id, payload)
    payload["file_path"] = file_path
    return payload
