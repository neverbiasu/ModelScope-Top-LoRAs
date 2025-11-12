import os
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# Tiny transparent PNG data URI as fallback/mock image
_PLACEHOLDER_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
)

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_job_file(task: str, job_id: str, payload: Dict[str, Any]) -> str:
    out_dir = Path("cache") / "outputs" / task
    _ensure_dir(str(out_dir))
    out_file = out_dir / f"{job_id}.json"
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_file)


def _remote_infer(model_id: str, params: Dict[str, Any], token: str) -> Dict[str, Any]:
    """
    Best-effort HTTP call to ModelScope-like inference endpoint.
    If any error occurs, raise to caller to allow fallback to mock.
    """
    try:
        import requests  # optional dependency
    except Exception as e:
        raise RuntimeError(f"requests not available: {e}")

    # Heuristic endpoint; replace with concrete service URL if available.
    endpoint = os.environ.get("MODELSCOPE_INFER_ENDPOINT", "https://www.modelscope.cn/api/v1/inference")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "model": model_id,
        "task": params.get("task"),
        "inputs": {
            "prompt": params.get("prompt", ""),
            "steps": params.get("steps", 20),
            "guidance": params.get("guidance", 7.5),
            "seed": params.get("seed", 0),
        },
    }

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 401:
                raise RuntimeError("Unauthorized (401)")
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": data.get("status") or "succeeded",
                "result": data.get("result") or data.get("output") or {},
                "raw": data,
            }
        except Exception as e:
            last_err = e
            if attempt >= MAX_RETRIES:
                break
            time.sleep(min(1.0 * attempt, 3.0))
    raise RuntimeError(str(last_err))


def _mock_infer(model_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # Return a quick mock including an example image data URI and echo of inputs
    result = {
        "image": _PLACEHOLDER_DATA_URI,
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
            payload = {"meta": meta, "status": "succeeded", "result": _mock_infer(model_id, params)["result"], "remote": False, "error": str(e)}
    else:
        payload = {"meta": meta, "status": "succeeded", "result": _mock_infer(model_id, params)["result"], "remote": False}

    file_path = _write_job_file(task, job_id, payload)
    payload["file_path"] = file_path
    return payload
