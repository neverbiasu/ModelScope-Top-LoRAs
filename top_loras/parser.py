import time
import time as _time
import json
import re as _re

# =============================================================================
# Base Model 替换映射表
# 将不支持 API 或不推荐的 base model 替换为已知可用的 MusePublic 版本
# =============================================================================
BASE_MODEL_REPLACEMENTS = {
    # FLUX.1-dev 系列
    "AI-ModelScope/FLUX.1-dev": "MusePublic/489_ckpt_FLUX_1",
    "ai-modelscope/flux.1-dev": "MusePublic/489_ckpt_FLUX_1",
    "black-forest-labs/FLUX.1-dev": "MusePublic/489_ckpt_FLUX_1",
    "black-forest-labs/flux.1-dev": "MusePublic/489_ckpt_FLUX_1",
    
    # FLUX.1 Kontext Dev
    "black-forest-labs/FLUX.1-Kontext-dev": "MusePublic/FLUX.1-Kontext-Dev",
    
    # Qwen-Image 系列
    "Qwen/Qwen-Image": "MusePublic/Qwen-image@v1",
    "Qwen/Qwen-Image-Edit": "MusePublic/Qwen-Image-Edit",
    "Qwen/Qwen-Image-Edit-2509": "MusePublic/Qwen-Image-Edit",
    
    # SDXL 系列
    "stabilityai/stable-diffusion-xl-base-1.0": "MusePublic/stable-diffusion-xl-base",
    "AI-ModelScope/stable-diffusion-xl-base-1.0": "MusePublic/stable-diffusion-xl-base",
    
    # SD3
    "stabilityai/stable-diffusion-3-medium": "MusePublic/stable-diffusion-3-medium",
    "AI-ModelScope/stable-diffusion-3-medium": "MusePublic/stable-diffusion-3-medium",
    
    # Pony Diffusion
    "Pony-Diffusion/pony-diffusion-v6-xl": "MusePublic/Pony_Diffusion_V6_XL_SD_XL",
    
    # Anything XL (万象熔炉)
    "AI-ModelScope/anything-xl": "MusePublic/14_ckpt_SD_XL",
}

# 根据 stable_diffusion_version / vision_foundation 推断默认 base model
# 当 LoRA 没有配置 base_models 时使用
DEFAULT_BASE_BY_VERSION = {
    "FLUX_1": "MusePublic/489_ckpt_FLUX_1",
    "QWEN_IMAGE_20_B": "MusePublic/Qwen-image@v1",
    "SD_XL": "MusePublic/stable-diffusion-xl-base",
    "SD_3": "MusePublic/stable-diffusion-3-medium",
    "PONY_V6": "MusePublic/Pony_Diffusion_V6_XL_SD_XL",
}


def normalize_base_model(base: str) -> str:
    """Apply base model replacement rules.
    
    Args:
        base: Original base model ID (may include @version suffix)
    
    Returns:
        Replaced base model ID if a rule matches, otherwise original (with @version stripped)
    """
    if not base:
        return base
    
    # Strip @version suffix for matching (e.g., "MusePublic/xxx@v1" -> "MusePublic/xxx")
    base_clean = base.split("@")[0].strip() if "@" in base else base.strip()
    
    # Exact match first
    if base_clean in BASE_MODEL_REPLACEMENTS:
        return BASE_MODEL_REPLACEMENTS[base_clean]
    
    # Case-insensitive match
    base_lower = base_clean.lower()
    for pattern, replacement in BASE_MODEL_REPLACEMENTS.items():
        if base_lower == pattern.lower():
            return replacement
    
    # Partial match for FLUX.1-dev variations
    if "flux.1-dev" in base_lower or "flux.1dev" in base_lower:
        if not base_lower.startswith("musepublic/"):
            return "MusePublic/489_ckpt_FLUX_1"
    
    # Return cleaned version (without @version suffix)
    return base_clean


def normalize_base_models(base_models: list, sd_version: str = None, vision_foundation: str = None) -> list:
    """Normalize and fill base_models list.
    
    1. Apply replacement rules to each base model
    2. If empty, infer from sd_version or vision_foundation
    
    Args:
        base_models: Original base_models list
        sd_version: stable_diffusion_version field
        vision_foundation: vision_foundation field
    
    Returns:
        Normalized base_models list
    """
    result = []
    
    # Apply replacement rules to existing base models
    if isinstance(base_models, (list, tuple)):
        for base in base_models:
            if isinstance(base, str) and base.strip():
                normalized = normalize_base_model(base.strip())
                if normalized and normalized not in result:
                    result.append(normalized)
    
    # If still empty, infer from sd_version or vision_foundation
    if not result:
        version_key = (sd_version or "").strip().upper()
        foundation_key = (vision_foundation or "").strip().upper()
        
        # Try sd_version first, then vision_foundation
        default_base = DEFAULT_BASE_BY_VERSION.get(version_key) or DEFAULT_BASE_BY_VERSION.get(foundation_key)
        if default_base:
            result.append(default_base)
    
    return result


def extract_downloads(item):
    d_raw = item.get('Downloads')
    if isinstance(d_raw, (int, float)):
        return int(d_raw)
    stats = item.get('stats')
    if isinstance(stats, dict):
        downloads = stats.get('downloads')
        if isinstance(downloads, (int, float)):
            return int(downloads)
    view_count = item.get('ViewCount') or item.get('views')
    if isinstance(view_count, (int, float)):
        return int(view_count)
    return 0


def extract_cover_url(item):
    muse_info = item.get("MuseInfo")
    if not isinstance(muse_info, dict):
        return None
    versions = muse_info.get("versions")
    if not isinstance(versions, (list, tuple)) or len(versions) == 0:
        return None
    first_version = versions[0]
    if not isinstance(first_version, dict):
        return None
    cover_images = first_version.get("coverImages")
    if not isinstance(cover_images, (list, tuple)) or len(cover_images) == 0:
        return None
    first_image = cover_images[0]
    if not isinstance(first_image, dict):
        return None
    return first_image.get("url")


def extract_modelscope_url(it):
    muse = it.get('MuseInfo') or {}
    if isinstance(muse, dict):
        versions = muse.get('versions') or []
        if isinstance(versions, (list, tuple)) and len(versions) > 0:
            for v in versions:
                if not isinstance(v, dict):
                    continue
                mv = v.get('modelVersion') or v.get('model_version') or v
                if isinstance(mv, dict):
                    for key in ('modelUrl', 'openlmUrl', 'sourceUrl', 'ossUrl'):
                        url = mv.get(key)
                        if url and isinstance(url, str):
                            return url
                for key in ('modelUrl', 'openlmUrl', 'sourceUrl'):
                    url = v.get(key)
                    if url and isinstance(url, str):
                        return url
    md = it.get('ModelDetail') or {}
    if isinstance(md, dict):
        u = md.get('url')
        if u and isinstance(u, str):
            return u
    path = it.get('Path')
    name = it.get('Name')
    if path and name:
        return f"https://modelscope.cn/{path}/{name}"
    return None


def extract_updated_at(it):
    lut = it.get('LastUpdatedTime') or it.get('LastUpdateTime')
    if isinstance(lut, (int, float)):
        try:
            return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(lut)))
        except Exception:
            pass
    for k in ('GmtModified', 'gmt_modified', 'UpdatedAt', 'updated_at'):
        v = it.get(k)
        if v:
            return v
    muse = it.get('MuseInfo') or {}
    try:
        mmodel = muse.get('model') if isinstance(muse, dict) else None
        if isinstance(mmodel, dict):
            gm = mmodel.get('gmtModified')
            if isinstance(gm, (int, float)):
                return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(gm) // 1000))
    except Exception:
        pass
    return None


def parse_model_entry(item):
    """Parse a raw model dict into the normalized form used by the cache/UI.

    This function is a direct refactor of the original `extract_model_info`.
    """
    # Prefer MuseInfo.model.modelName when available (this contains the canonical
    # ModelScope model identifier like 'Org/Model-Name'). Fall back to older
    # fields (Name/name/ModelId/Id) when not present.
    muse = item.get('MuseInfo') or {}
    muse_model = muse.get('model') if isinstance(muse, dict) else None
    model_id = None
    try:
        if isinstance(muse_model, dict):
            mn = muse_model.get('modelName') or muse_model.get('model_name') or muse_model.get('showName')
            if isinstance(mn, str) and mn.strip():
                model_id = mn.strip()
    except Exception:
        model_id = None

    if not model_id:
        model_id = item.get('Name') or item.get('name') or item.get('ModelId') or item.get('Id')

    def extract_likes(it):
        for k in ('LikeCount', 'Likes', 'Like', 'like_count', 'like'):
            v = it.get(k)
            if isinstance(v, (int, float)):
                return int(v)
        stats = it.get('stats') or it.get('Stats')
        if isinstance(stats, dict):
            for k in ('likes', 'like_count', 'likes_count'):
                v = stats.get(k)
                if isinstance(v, (int, float)):
                    return int(v)
        v = it.get('Stars') or it.get('star')
        if isinstance(v, (int, float)):
            return int(v)
        muse = it.get('MuseInfo') or {}
        try:
            mmodel = muse.get('model') if isinstance(muse, dict) else None
            if isinstance(mmodel, dict):
                fav = mmodel.get('favoriteCount') or mmodel.get('favorite')
                if isinstance(fav, (int, float)):
                    return int(fav)
        except Exception:
            pass
        return 0

    # `muse` and `muse_model` already extracted above for id/title extraction

    title_cn = item.get('ChineseName') or None
    # fallback: MuseInfo.model.showName or modelName
    try:
        if not title_cn and isinstance(muse_model, dict):
            title_cn = muse_model.get('showName') or muse_model.get('modelName') or title_cn
    except Exception:
        pass

    title_en = item.get('Name') or (muse_model.get('modelName') if isinstance(muse_model, dict) else None) or item.get('NickName')

    organization = item.get('Organization') or {}
    org_id = organization.get('Id') if isinstance(organization, dict) else None
    avatar = None
    if isinstance(organization, dict) and org_id:
        avatar = organization.get('Avatar') or item.get('Avatar')
    else:
        avatar = item.get('Avatar')

    user_name = None
    if isinstance(organization, dict) and org_id:
        user_name = organization.get('FullName') or item.get('NickName') or item.get('CreatedBy')
    else:
        user_name = (muse_model.get('operatorName') if isinstance(muse_model, dict) else None) or item.get('NickName') or item.get('CreatedBy')

    operator_emp = None
    if isinstance(muse_model, dict):
        operator_emp = muse_model.get('operatorEmpId')

    user_profile = f"https://modelscope.cn/profile/{operator_emp}" if operator_emp else None

    tags_cn = []
    tags_en = []
    ot = item.get('OfficialTags') or []
    if isinstance(ot, list):
        for t in ot:
            if isinstance(t, dict):
                cn = t.get('ChineseName')
                en = t.get('Name')
                if cn:
                    tags_cn.append(cn)
                if en:
                    tags_en.append(en)

    base_models_raw = item.get('BaseModel') or []
    sd_version = None
    if isinstance(muse_model, dict):
        sd_version = muse_model.get('stableDiffusionVersion') or item.get('VisionFoundation')
    if not sd_version:
        sd_version = item.get('VisionFoundation')

    trigger_words = item.get('TriggerWords')
    vision_foundation = item.get('VisionFoundation')
    
    # Normalize base_models: apply replacements and fill from sd_version if empty
    base_models = normalize_base_models(base_models_raw, sd_version, vision_foundation)

    raw_modelscope = extract_modelscope_url(item)
    modelscope_url = None
    if raw_modelscope:
        if raw_modelscope.startswith('modelscope://'):
            modelscope_url = 'https://modelscope.cn/' + raw_modelscope[len('modelscope://'):]
        else:
            modelscope_url = raw_modelscope

    # If model_id is still missing or not canonical (no org/name), try deriving from modelscope_url
    try:
        if (not model_id or ('/' not in str(model_id))) and isinstance(modelscope_url, str):
            # Expected formats: https://modelscope.cn/<org>/<name>(/summary|...)? or modelscope://<org>/<name>
            m = _re.search(r"modelscope\.cn/([^/]+)/([^/?#]+)", modelscope_url)
            if m:
                org, name = m.group(1), m.group(2)
                # Only allow org and name with alphanumerics, underscores, hyphens, and dots
                if (_re.fullmatch(r"[A-Za-z0-9_.-]+", org) and _re.fullmatch(r"[A-Za-z0-9_.-]+", name)):
                    derived = f"{org}/{name}"
                    if derived and derived.strip():
                        model_id = derived.strip()
    except Exception:
        # Ignore errors in model_id extraction from modelscope_url; fallback to original model_id if extraction fails.
        pass
    return {
        'id': model_id,
        'title_cn': title_cn,
        'title_en': title_en,
        'author': item.get('CreatedBy') or item.get('Owner') or item.get('Author'),
    'avatar': avatar,
        'user_name': user_name,
        'user_profile': user_profile,
        'cover_url': extract_cover_url(item),
        'cover_local': None,
        'downloads': extract_downloads(item),
        'likes': extract_likes(item),
        'license': item.get('License'),
        'tags_cn': tags_cn,
        'tags_en': tags_en,
        'base_models': base_models,
        'stable_diffusion_version': sd_version,
        'trigger_words': trigger_words,
        'vision_foundation': vision_foundation,
        'updated_at': extract_updated_at(item),
        'modelscope_url': modelscope_url or (f"https://modelscope.cn/models/{model_id}/summary" if model_id else None),
        
    }
