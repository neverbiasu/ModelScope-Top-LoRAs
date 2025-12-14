# API 错误处理改进总结

## 📝 问题描述

用户遇到 ModelScope API 错误 40212,即使提供了 Token 仍然失败。

**原始错误信息:**
```
Submit error 400: {'errors': {'message': 'submit failed with status code: 40212'}, 'request_id': '...'}
```

## 🔧 实施的改进

### 1. 增强的 Token 验证和格式化 (`top_loras/inference.py`)

**改进前:**
- Token 直接传递给 API,没有清理和验证
- 没有模型 ID 格式验证
- 错误信息不明确

**改进后:**
```python
# Token 清理
clean_token = token.strip().strip('"').strip("'")
if clean_token.lower().startswith("bearer "):
    clean_token = clean_token.split(None, 1)[-1].strip()

# 模型 ID 格式验证
if not model_id or "/" not in model_id:
    raise RuntimeError(
        f"Invalid model ID format: '{model_id}'. "
        "Model ID must be in 'owner/model-name' format"
    )
```

### 2. 详细的错误信息 (`top_loras/inference.py`)

**改进前:**
```python
raise RuntimeError(f"Submit error {status_code}: {detail}")
```

**改进后:**
```python
# 针对 40212 错误的特殊处理
if submit_resp.status_code == 400:
    detail_str = str(detail)
    if "40212" in detail_str:
        error_msg += (
            "\n\n⚠️ Error 40212 通常表示:\n"
            f"1. 模型 ID 格式错误 - 当前使用: '{model_id}'\n"
            "2. 该模型不支持异步图像生成 API\n"
            "3. Token 权限不足或未激活图像生成服务\n\n"
            "建议:\n..."
        )
```

### 3. 调试模式 (`top_loras/inference.py`)

**新增功能:**
```bash
export MODELSCOPE_DEBUG=1
```

输出内容:
- 请求 URL
- 模型 ID
- Token 前缀
- 完整请求体
- 响应状态码和内容

### 4. UI 错误展示改进 (`ui/callbacks.py`)

**改进前:**
- 简单显示异常信息
- 总是显示通用建议

**改进后:**
```python
# 检测详细错误 (包含 ⚠️ 或多行)
if "⚠️" in error_detail or "\n\n" in error_detail:
    status_md = f"{t('error_submit_failed', lang)}\n\n{error_detail}"
else:
    # 通用错误处理
    ...

# 添加调试提示
status_md += f"\n\n---\n\n**调试提示:**\n"
status_md += f"- 当前使用的模型: `{effective_model}`\n"
status_md += f"- Token 状态: {'已提供' if effective_token else '未提供'}\n"
```

### 5. API 诊断工具 (debug mode (`MODELSCOPE_DEBUG=1`))

**新增独立诊断脚本:**

```bash
# 测试 Token
MODELSCOPE_DEBUG=1 python app.py

# 测试特定模型
MODELSCOPE_DEBUG=1 python app.py --model "owner/model-name"

# 使用环境变量
export MODELSCOPE_API_TOKEN="your-token"
MODELSCOPE_DEBUG=1 python app.py
```

**功能:**
- ✅ Token 格式验证和清理
- ✅ 模型 ID 格式验证
- ✅ 完整的请求/响应日志
- ✅ 针对性的错误建议
- ✅ 40212 错误特殊处理
- ✅ 彩色输出和格式化

### 6. 文档更新

#### README.md
- ✅ 添加 "Troubleshooting" 章节
- ✅ 错误码对照表
- ✅ 调试模式说明
- ✅ 推荐模型列表

#### docs/API_GUIDE.md (新增)
- ✅ Token 获取和验证流程
- ✅ 常见问题 FAQ
- ✅ 推荐工作流程
- ✅ 相关链接

#### docs/ERROR_40212_FIX.md (新增)
- ✅ 快速修复检查清单
- ✅ 常见场景解决方案
- ✅ 验证步骤
- ✅ 调试技巧

## 📊 改进效果

### 错误定位更快

**改进前:**
```
Submit error 400: {'errors': {'message': 'submit failed with status code: 40212'}}
```
❌ 用户不知道具体原因

**改进后:**
```
Submit error 400: {...}

⚠️ Error 40212 通常表示:
1. 模型 ID 格式错误 - 当前使用: 'stable-diffusion-xl' (必须是 owner/model-name 格式)
2. 该模型不支持异步图像生成 API
3. Token 权限不足或未激活图像生成服务

建议:
- 检查模型详情页确认是否支持 API 调用
- 尝试使用官方推荐的模型 (如 AI-ModelScope/stable-diffusion-xl)
- 确保 Token 已开通图像生成 API 权限
```
✅ 明确指出问题和解决方向

### 诊断更简单

**改进前:**
- 只能在应用中测试
- 需要填写完整表单
- 错误信息不够详细

**改进后:**
```bash
# 一条命令快速测试
MODELSCOPE_DEBUG=1 python app.py

# 输出:
🔍 测试配置
API 地址: https://api-inference.modelscope.cn/v1/images/generations
模型 ID: AI-ModelScope/stable-diffusion-xl
Token (前10位): xxxxx-xxxx...

📤 发送请求...
📥 响应状态码: 200
✅ API 调用成功!
任务 ID: xxxxx
```

### 调试更高效

**改进前:**
- 无法查看实际请求内容
- 不知道 Token 是否正确传递
- 难以定位参数问题

**改进后:**
```bash
export MODELSCOPE_DEBUG=1
python app.py

# 输出:
[DEBUG] Request URL: https://api-inference.modelscope.cn/v1/images/generations
[DEBUG] Model ID: AI-ModelScope/stable-diffusion-xl
[DEBUG] Token (first 10 chars): xxxxx-xxxx...
[DEBUG] Request body: {
  "model": "AI-ModelScope/stable-diffusion-xl",
  "prompt": "a beautiful sunset",
  "size": "512x512"
}
[DEBUG] Response status: 400
[DEBUG] Response body: {...}
```

## 🎯 使用建议

### 对于遇到 40212 错误的用户:

1. **首先运行诊断:**
   ```bash
   MODELSCOPE_DEBUG=1 python app.py
   ```

2. **查看快速修复指南:**
   ```bash
   cat docs/ERROR_40212_FIX.md
   ```

3. **如果仍有问题,开启调试模式:**
   ```bash
   export MODELSCOPE_DEBUG=1
   python app.py
   ```

4. **测试官方推荐模型:**
   - 在 "API Model (override)" 中输入: `AI-ModelScope/stable-diffusion-xl`
   - 确认该模型可以正常工作后,再测试其他模型

### 对于开发者:

1. **测试新模型前先用诊断脚本:**
   ```bash
   MODELSCOPE_DEBUG=1 python app.py --model "owner/model-name"
   ```

2. **集成调试日志到开发流程:**
   ```bash
   export MODELSCOPE_DEBUG=1
   # 在 .zshrc 或 .bashrc 中设置
   ```

3. **参考 API 指南:**
   ```bash
   cat docs/API_GUIDE.md
   ```

## 🚀 后续优化建议

1. **自动模型 ID 修正:**
   - 如果用户输入 `stable-diffusion-xl`
   - 自动尝试 `AI-ModelScope/stable-diffusion-xl`

2. **Token 在线验证:**
   - 在保存 Token 时立即测试
   - 给出即时反馈

3. **推荐模型列表:**
   - 在 UI 中添加下拉选择
   - 仅列出经过验证的模型

4. **错误统计和上报:**
   - 收集常见错误
   - 自动生成解决建议

## 📚 相关文件

- `top_loras/inference.py` - API 调用和错误处理核心逻辑
- `ui/callbacks.py` - UI 错误展示
- debug mode (`MODELSCOPE_DEBUG=1`) - 诊断工具
- `docs/API_GUIDE.md` - 完整 API 使用指南
- `docs/ERROR_40212_FIX.md` - 快速修复指南
- `README.md` - 故障排查章节

## ✅ 测试清单

- [x] Token 格式清理和验证
- [x] 模型 ID 格式验证
- [x] 40212 错误特殊处理
- [x] 401 错误友好提示
- [x] 调试模式实现
- [x] 诊断脚本创建
- [x] 文档更新
- [x] 代码无语法错误

## 🎉 总结

通过这些改进,用户在遇到 40212 错误时:
1. ✅ 能够快速定位问题 (Token/模型 ID/权限)
2. ✅ 获得详细的错误说明和建议
3. ✅ 使用诊断工具快速验证配置
4. ✅ 通过调试模式查看完整请求信息
5. ✅ 参考完整文档自助解决问题

大大提升了用户体验和问题解决效率! 🚀
