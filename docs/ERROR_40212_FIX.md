# 🚨 错误 40212 快速修复指南

## ⚡ 立即尝试

```bash
# 1. 测试你的 Token 和模型
MODELSCOPE_DEBUG=1 python app.py

# 2. 开启调试模式查看详细错误
export MODELSCOPE_DEBUG=1
python app.py
```

## 🔍 问题检查清单

### ✅ Token 格式检查

- [ ] Token 没有引号
- [ ] Token 没有 "Bearer " 前缀
- [ ] Token 没有多余空格
- [ ] Token 已在 [ModelScope](https://modelscope.cn/my/myaccesstoken) 生成

**正确格式示例:**
```
xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### ✅ 模型 ID 格式检查

- [ ] 模型 ID 包含 `/` (owner/model-name)
- [ ] 模型 ID 没有多余的路径前缀
- [ ] 模型支持 API 调用 (访问模型页面确认)

**正确格式示例:**
```
✅ AI-ModelScope/stable-diffusion-xl
✅ damo/text-to-video-synthesis
❌ stable-diffusion-xl (缺少 owner)
❌ models/AI-ModelScope/stable-diffusion-xl (多余前缀)
```

### ✅ 应用配置检查

在 UI 中:
1. Generate 页面
2. 输入 Token 并点击 "Save Token"
3. 检查 "API Model (override)" 字段格式
4. 如果该字段为空,会使用左侧选择的模型

## 🎯 常见场景解决方案

### 场景 1: 使用左侧选择的模型

**问题:** 左侧选择的模型可能不支持 API

**解决:**
1. 不要填写 "API Model (override)"
2. 或者在 "API Model (override)" 中输入官方支持的模型:
   - `AI-ModelScope/stable-diffusion-xl`
   - `damo/cv_diffusion_text-to-image-synthesis_base`

### 场景 2: 使用自定义模型

**问题:** 输入的模型 ID 格式不对

**解决:**
1. 访问模型页面: `https://modelscope.cn/models/{你的模型}`
2. 从 URL 复制完整的 `owner/model-name`
3. 确认模型详情页有 "API 调用" 说明

### 场景 3: Token 权限问题

**问题:** Token 没有图像生成权限

**解决:**
1. 删除旧 Token
2. 重新生成 Token (可能需要实名认证)
3. 确认账号已开通图像生成 API 服务

## 🧪 验证步骤

### 第一步: 测试 Token

```bash
MODELSCOPE_DEBUG=1 python app.py
```

**预期输出 (成功):**
```
✅ API 调用成功!
任务 ID: xxxxx
```

**预期输出 (失败):**
```
❌ 测试失败: Submit error 400: {...}
💡 建议:
   错误码 40212 通常表示:
   1. 模型不支持此 API (检查模型详情页)
   ...
```

### 第二步: 测试特定模型

```bash
# 测试官方模型
MODELSCOPE_DEBUG=1 python app.py --model "AI-ModelScope/stable-diffusion-xl"

# 测试你想用的模型
MODELSCOPE_DEBUG=1 python app.py --model "owner/model-name"
```

### 第三步: 在应用中测试

```bash
# 设置环境变量
export MODELSCOPE_API_TOKEN="你的Token"
export MODELSCOPE_DEBUG=1

# 启动应用
python app.py
```

在浏览器中:
1. 切换到 Generate 页面
2. 在 "API Model (override)" 中输入: `AI-ModelScope/stable-diffusion-xl`
3. 输入 Prompt: `a beautiful sunset`
4. 点击 Generate
5. 查看终端输出的调试信息

## 📞 仍然无法解决?

1. **查看完整文档:**
   ```bash
   cat docs/API_GUIDE.md
   ```

2. **查看 README 故障排查部分:**
   ```bash
   cat README.md | grep -A 50 "Troubleshooting"
   ```

3. **提交 Issue:**
   - 包含诊断脚本的完整输出
   - 包含调试模式的终端日志
   - 说明使用的模型 ID

4. **联系 ModelScope 支持:**
   - 确认你的账号是否有 API 使用权限
   - 确认特定模型是否支持 API 调用

## 🔧 调试技巧

### 查看完整请求

```bash
export MODELSCOPE_DEBUG=1
python app.py
```

会显示:
- 请求 URL
- 请求头 (包括 Token 前缀)
- 请求体 (完整参数)
- 响应状态码
- 响应内容

### 使用模拟模式

不提供 Token 测试 UI 功能:

```bash
# 不设置 MODELSCOPE_API_TOKEN
python app.py
```

此时点击 Generate 会返回模拟图像。

### 对比正常请求

使用 curl 直接测试 API:

```bash
curl -X POST "https://api-inference.modelscope.cn/v1/images/generations" \
  -H "Authorization: Bearer 你的Token" \
  -H "Content-Type: application/json" \
  -H "X-ModelScope-Async-Mode: true" \
  -d '{
    "model": "AI-ModelScope/stable-diffusion-xl",
    "prompt": "a beautiful sunset",
    "size": "512x512"
  }'
```

成功会返回:
```json
{
  "task_id": "xxxxx-xxxx-xxxx..."
}
```

失败会返回错误详情。
