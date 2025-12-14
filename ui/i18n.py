"""Internationalization (i18n) support for Top-LoRAs UI."""

from typing import Dict, Literal

Language = Literal["zh", "en"]

TRANSLATIONS: Dict[Language, Dict[str, str]] = {
    "zh": {
        # Header
        "title": "Top‑LoRAs",
        
        # Selection Tab
        "selection_tab": "选择模型",
        "task_label": "任务 (选择)",
        "per_task_cache": "按任务缓存",
        "refresh_btn": "刷新缓存",
        "refresh_hint": "提示：点击 Refresh 从 ModelScope 获取最新数据并更新本地缓存。",
        "selected_model": "已选择模型：",
        "no_model": "无",
        "no_model_selected": "未选择模型",
        "top_loras": "Top LoRAs",
        
        # Generate Tab
        "generate_tab": "生成图像",
        "select_first": "请先在 **Selection** 标签页选择一个模型",
        "model_id_label": "当前选中模型 ID",
        "prompt_label": "Prompt（提示词）",
        "prompt_placeholder": "描述你想生成的图像，例如：a beautiful sunset over mountains",
        "neg_prompt_label": "Negative Prompt（负面提示词）",
        "neg_prompt_placeholder": "不想出现的内容，例如：blurry, low quality",
        "size_label": "尺寸",
        "size_placeholder": "例如 1024x1024",
        "steps_label": "Steps（步数）",
        "guidance_label": "Guidance Scale",
        "seed_label": "Seed（种子）",
        "seed_info": "0=随机",
        "api_model_label": "API Model Override（高级）",
        "api_model_placeholder": "完整模型路径，例如 black-forest-labs/FLUX.1-dev",
        "api_model_info": "仅在自动解析的模型 ID 不正确时使用",
        "generate_btn": "生成图像",
        "auth_title": "### API 认证",
        "token_label": "ModelScope API Token",
        "token_placeholder": "粘贴你的 API Token（仅本次会话有效）",
        "token_save": "保存 Token",
        "token_clear": "清除 Token",
        "token_status_empty": "**状态：** Token 为空，未保存",
        "token_status_saved": "**状态：** Token 已保存（仅本次会话有效）",
        "token_status_cleared": "**状态：** 未提供 Token（将使用模拟模式）",
        "token_status_default": "**状态：** 未提供 Token（将使用模拟模式）",
        "output_label": "本次输出",
        "results_label": "历史结果",
        "language": "Language",
        
        # Errors
        "error_no_model": "**错误：** 未选择模型。请先在 Selection 标签页中点击一个模型卡片。",
        "error_empty_prompt": "**错误：** Prompt 不能为空。请输入描述要生成的图像内容。",
        "error_submit_failed": "**提交失败**",
        "error_reasons": "**可能原因：**",
        "error_model_format": "- 模型 ID 格式不正确（需要 `组织名/模型名` 格式）",
        "error_token_invalid": "- API Token 无效或已过期",
        "error_network": "- 网络连接问题",
        "error_task_support": "- 模型不支持当前任务类型",
        "error_details": "**错误信息：** ",
        "suggest_actions": "**建议操作：**",
        "suggest_1": "1. 检查 'API Model (override)' 字段，确保格式为 `owner/model-name`",
        "suggest_2": "2. 验证 API Token 是否有效",
        "suggest_3": "3. 尝试刷新页面重新选择模型",
        
        # Status messages
        "status_submitting": "**提交中...** 正在向 ModelScope API 提交任务，请稍候...",
        "status_mock_mode": "**模拟模式：** 未提供 API Token，将返回模拟结果。\n\n如需真实推理，请在 Generate 页输入 ModelScope API Token 并点击 Save Token。",
        "status_result": "### 生成结果",
        "status_mode": "**模式：** ",
        "status_mode_mock": "模拟模式",
        "status_mode_remote": "远程推理",
        "status_mode_local": "本地模拟",
        "status_mock_note": "这是一个模拟结果。要获得真实的图像生成，请提供 ModelScope API Token。",
        "status_job_id": "**任务 ID：** ",
        "status_model": "**使用模型：** ",
        "status_state": "**状态：** ",
        "status_warning_incomplete": "**注意：** 模型 ID 可能不完整（缺少组织前缀）。如遇到 400 错误，请在 'API Model Override' 字段输入完整格式，例如 `black-forest-labs/FLUX.1-dev`",
        "status_job_error": "**警告：** ",
        "status_success": "**成功！** 图像已生成，请在右侧查看。",
        "status_generated_count": "**生成的图片数量：** ",
        "status_no_images": "**未返回图像**",
        "status_no_images_reasons": "可能原因：",
        "status_reason_1": "- 生成任务失败",
        "status_reason_2": "- API 响应格式异常",
        "status_reason_3": "- 模型不支持此类任务",
        "status_check_error": "请检查上述错误信息或尝试其他模型。",
        
        # Common API errors with friendly messages
        "err_task_not_found": "**❌ 任务未找到 (task not found)**\n\n这通常表示 ModelScope 后端未能正确处理任务，可能原因：\n- 所选模型不支持在线推理 API\n- 模型当前不可用或负载过高\n- LoRA 与 Base 模型不兼容\n\n**建议：** 尝试选择其他模型，或稍后重试。",
        "err_model_not_supported": "**❌ 模型不支持 API 推理**\n\n该模型 (`{model}`) 未开放在线推理接口。\n\n**建议：** 选择官方支持的模型如 `AI-ModelScope/stable-diffusion-xl`。",
        "err_token_invalid": "**❌ Token 无效或已过期**\n\n请检查您的 API Token 是否正确。\n\n**获取新 Token：** https://modelscope.cn/my/myaccesstoken",
        "err_rate_limit": "**⏳ 请求过于频繁**\n\n您的请求被限流，请稍后再试。",
        "err_server_error": "**⚠️ 服务器内部错误 (500)**\n\nModelScope 服务端出现问题。\n\n**建议：** 稍后重试，或联系 ModelScope 支持。",
        "err_timeout": "**⏱️ 请求超时**\n\n生成任务耗时过长或网络问题。\n\n**建议：** 检查网络连接，稍后重试。",
        "err_unknown": "**❓ 未知错误**\n\n遇到未预期的错误。\n\n**建议：** 设置 `MODELSCOPE_DEBUG=1` 后重试以获取详细信息。",
        
        # Model selection messages
        "model_selected": "已选择：",
        "model_name": "Name",
        "model_author": "Author",
        "model_stats": "Downloads · Likes",
    },
    "en": {
        # Header
        "title": "Top‑LoRAs",
        
        # Selection Tab
        "selection_tab": "Selection",
        "task_label": "Task (select)",
        "per_task_cache": "Per-task cache",
        "refresh_btn": "Refresh Cache",
        "refresh_hint": "Tip: Click Refresh to fetch the latest data from ModelScope and update the local cache.",
        "selected_model": "Selected Model: ",
        "no_model": "None",
        "no_model_selected": "No model selected",
        "top_loras": "Top LoRAs",
        
        # Generate Tab
        "generate_tab": "Generate",
        "select_first": "Please select a model first in the **Selection** tab",
        "model_id_label": "Current Model ID",
        "prompt_label": "Prompt",
        "prompt_placeholder": "Describe the image you want to generate, e.g.: a beautiful sunset over mountains",
        "neg_prompt_label": "Negative Prompt",
        "neg_prompt_placeholder": "Content you don't want, e.g.: blurry, low quality",
        "size_label": "Size",
        "size_placeholder": "e.g. 1024x1024",
        "steps_label": "Steps",
        "guidance_label": "Guidance Scale",
        "seed_label": "Seed",
        "seed_info": "0=random",
        "api_model_label": "API Model Override (Advanced)",
        "api_model_placeholder": "Full model path, e.g.: black-forest-labs/FLUX.1-dev",
        "api_model_info": "Use only if the automatically parsed model ID is incorrect",
        "generate_btn": "Generate Image",
        "auth_title": "### API Authentication",
        "token_label": "ModelScope API Token",
        "token_placeholder": "Paste your API Token (valid for this session only)",
        "token_save": "Save Token",
        "token_clear": "Clear Token",
        "token_status_empty": "**Status:** Token is empty, not saved",
        "token_status_saved": "**Status:** Token saved (valid for this session only)",
        "token_status_cleared": "**Status:** No token provided (will use mock mode)",
        "token_status_default": "**Status:** No token provided (will use mock mode)",
        "output_label": "Current output",
        "results_label": "History",
        "language": "Language",
        
        # Errors
        "error_no_model": "**Error:** No model selected. Please click a model card in the Selection tab first.",
        "error_empty_prompt": "**Error:** Prompt cannot be empty. Please describe what you want to generate.",
        "error_submit_failed": "**❌ Submission Failed**",
        "error_reasons": "**Possible Reasons:**",
        "error_model_format": "- Model ID format is incorrect (should be `organization/model-name`)",
        "error_token_invalid": "- API Token is invalid or expired",
        "error_network": "- Network connection issue",
        "error_task_support": "- Model does not support this task type",
        "error_details": "**Error Details:** ",
        "suggest_actions": "**Suggested Actions:**",
        "suggest_1": "1. Check the 'API Model Override' field, ensure format is `owner/model-name`",
        "suggest_2": "2. Verify that your API Token is valid",
        "suggest_3": "3. Try refreshing the page and selecting a model again",
        
        # Status messages
        "status_submitting": "**Submitting...** Sending task to ModelScope API, please wait...",
        "status_mock_mode": "**Mock Mode:** No API Token provided, will return mock results.\n\nFor real inference, please enter your ModelScope API Token in the Generate tab and click Save Token.",
        "status_result": "### Generation Result",
        "status_mode": "**Mode:** ",
        "status_mode_mock": "Mock Mode",
        "status_mode_remote": "Remote Inference",
        "status_mode_local": "Local Mock",
        "status_mock_note": "This is a mock result. To get real image generation, please provide a ModelScope API Token.",
        "status_job_id": "**Job ID:** ",
        "status_model": "**Model Used:** ",
        "status_state": "**Status:** ",
        "status_warning_incomplete": "**Note:** Model ID may be incomplete (missing organization prefix). If you encounter a 400 error, please enter the full format in 'API Model Override', e.g. `black-forest-labs/FLUX.1-dev`",
        "status_job_error": "**Warning:** ",
        "status_success": "**Success!** Image generated, see results on the right.",
        "status_generated_count": "**Number of images generated:** ",
        "status_no_images": "**No images returned**",
        "status_no_images_reasons": "Possible reasons:",
        "status_reason_1": "- Generation task failed",
        "status_reason_2": "- API response format is abnormal",
        "status_reason_3": "- Model does not support this task type",
        "status_check_error": "Please check the above error message or try another model.",
        
        # Common API errors with friendly messages
        "err_task_not_found": "**❌ Task Not Found**\n\nThe ModelScope backend failed to process this task. Possible causes:\n- The selected model does not support online inference API\n- Model is currently unavailable or overloaded\n- LoRA is incompatible with the base model\n\n**Suggestion:** Try a different model or retry later.",
        "err_model_not_supported": "**❌ Model Does Not Support API Inference**\n\nThis model (`{model}`) does not have an online inference endpoint.\n\n**Suggestion:** Use an officially supported model like `AI-ModelScope/stable-diffusion-xl`.",
        "err_token_invalid": "**❌ Token Invalid or Expired**\n\nPlease check if your API Token is correct.\n\n**Get a new Token:** https://modelscope.cn/my/myaccesstoken",
        "err_rate_limit": "**⏳ Rate Limited**\n\nToo many requests. Please wait and try again.",
        "err_server_error": "**⚠️ Server Error (500)**\n\nModelScope backend encountered an issue.\n\n**Suggestion:** Retry later or contact ModelScope support.",
        "err_timeout": "**⏱️ Request Timeout**\n\nThe generation task took too long or there was a network issue.\n\n**Suggestion:** Check your network and try again.",
        "err_unknown": "**❓ Unknown Error**\n\nAn unexpected error occurred.\n\n**Suggestion:** Set `MODELSCOPE_DEBUG=1` and retry for detailed info.",
        
        # Model selection messages
        "model_selected": "Selected: ",
        "model_name": "Name",
        "model_author": "Author",
        "model_stats": "Downloads · Likes",
    },
}


def t(key: str, lang: Language = "zh") -> str:
    """Translate a key to the specified language.
    
    Args:
        key: Translation key (e.g., "title", "error_no_model")
        lang: Language code ("zh" for Chinese, "en" for English)
    
    Returns:
        Translated string, or the key itself if not found
    """
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key, key)


def get_translations(lang: Language = "zh") -> Dict[str, str]:
    """Get all translations for a specific language.
    
    Args:
        lang: Language code
    
    Returns:
        Dictionary of all translations for that language
    """
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"])
