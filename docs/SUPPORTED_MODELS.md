# ModelScope API 支持的官方模型列表

## ✅ 已验证支持 API 的模型

以下模型已确认支持 ModelScope 的标准图像生成 API (`/v1/images/generations`):

### Stable Diffusion 系列

| 模型 ID | 描述 | 推荐用途 |
|---------|------|----------|
| `AI-ModelScope/stable-diffusion-xl` | Stable Diffusion XL 基础模型 | 高质量图像生成 (推荐) |
| `AI-ModelScope/stable-diffusion-v1-5` | Stable Diffusion 1.5 | 快速图像生成 |
| `AI-ModelScope/stable-diffusion-v2-1` | Stable Diffusion 2.1 | 通用图像生成 |

### 达摩院模型

| 模型 ID | 描述 | 推荐用途 |
|---------|------|----------|
| `damo/text-to-image-synthesis` | 达摩院文生图基础模型 | 中文 prompt 支持 |
| `damo/cv_diffusion_text-to-image-synthesis_base` | 达摩院扩散模型 | 中文场景生成 |

## ❌ 不支持 API 的模型类型

以下类型的模型**通常不支持**标准 API，会返回 40212 错误:

### 1. 用户上传的 LoRA 模型

示例:
- `yiwanji/FLUX_xiao_hong_shu_ji_zhi_zhen_shi_V2` ❌
- `user/custom-lora-model` ❌
- 任何包含 "LoRA", "FLUX", "fine-tune" 的用户模型 ❌

**原因:** LoRA 是在基础模型上的微调权重，需要在 Studio 环境中加载基础模型后应用 LoRA 权重，无法直接通过 API 调用。

### 2. 社区微调模型

示例:
- 个人上传的角色模型 ❌
- 风格化训练模型 ❌
- DreamBooth 训练模型 ❌

**原因:** 这些模型需要特定的推理环境和依赖，只能在 ModelScope Studio 中运行。

### 3. 实验性或研究模型

示例:
- 未认证的研究项目模型 ❌
- Beta 版本模型 ❌

**原因:** 这些模型可能还在开发中，未开放 API 访问。

## 🔍 如何判断模型是否支持 API

### 方法 1: 查看模型主页

访问模型页面: `https://modelscope.cn/models/{owner}/{model-name}`

查找以下标识:
- ✅ **有 "API 调用" 标签页** → 支持 API
- ❌ **只有 "在线体验" 或 "Studio"** → 不支持 API

### 方法 2: 使用诊断工具

```bash
MODELSCOPE_DEBUG=1 python app.py --model "owner/model-name"
```

- 返回 200 → 支持 ✅
- 返回 40212 → 不支持 ❌

### 方法 3: 查看模型所有者

一般规律:
- `AI-ModelScope/*` → 官方模型，**通常支持** ✅
- `damo/*`, `iic/*`, `pai/*` → 机构模型，**可能支持** ⚠️
- `个人用户/*` → 社区模型，**通常不支持** ❌

## 💡 解决方案

### 如果你想使用 LoRA 模型的效果:

#### 选项 1: 使用基础模型 + 调整 prompt

```
原模型: yiwanji/FLUX_xiao_hong_shu_ji_zhi_zhen_shi_V2 (不支持 API)
↓
替代方案: AI-ModelScope/stable-diffusion-xl (支持 API)
+ 优化的 prompt (描述 LoRA 的风格特征)
```

示例:
```
原 prompt: 一个女孩
LoRA 风格: 小红书极致真实风格

优化后的 prompt: 
a beautiful young woman, photorealistic, high quality, 
natural lighting, instagram style, xiaohongshu aesthetic, 
ultra detailed, 8k
```

#### 选项 2: 在 Studio 中使用原模型

访问: `https://modelscope.cn/models/yiwanji/FLUX_xiao_hong_shu_ji_zhi_zhen_shi_V2`

点击 "在线体验" 或 "Studio" 按钮

#### 选项 3: 本地部署

如果你有 GPU，可以:
1. 下载模型到本地
2. 使用 ComfyUI/Stable Diffusion WebUI
3. 加载 LoRA 进行推理

## 🧪 测试推荐模型

在 UI 的 "API Model Override" 字段中输入以下模型 ID 进行测试:

### 快速测试 (推荐)
```
AI-ModelScope/stable-diffusion-xl
```

### 中文支持
```
damo/text-to-image-synthesis
```

### 高性能
```
AI-ModelScope/stable-diffusion-v2-1
```

## 📝 API 调用示例

### 使用 curl 测试

```bash
curl -X POST "https://api-inference.modelscope.cn/v1/images/generations" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-ModelScope-Async-Mode: true" \
  -d '{
    "model": "AI-ModelScope/stable-diffusion-xl",
    "prompt": "a beautiful sunset over mountains",
    "size": "1024x1024",
    "steps": 30
  }'
```

### 使用 Python

```python
import requests

url = "https://api-inference.modelscope.cn/v1/images/generations"
headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json",
    "X-ModelScope-Async-Mode": "true"
}
data = {
    "model": "AI-ModelScope/stable-diffusion-xl",
    "prompt": "a beautiful sunset over mountains",
    "size": "1024x1024",
    "steps": 30
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## 🔗 相关链接

- [ModelScope API 文档](https://modelscope.cn/docs/api-inference/intro)
- [图像生成 API 说明](https://modelscope.cn/docs/api-inference/images)
- [官方模型列表](https://modelscope.cn/models?page=1&tasks=text-to-image-synthesis)
- [提交问题](https://github.com/neverbiasu/ModelScope-Top-LoRAs/issues)

## 🆘 常见问题

### Q: 为什么我在 Top-LoRAs 列表中看到的模型大多不支持 API?

A: 因为这个应用的目的是展示**热门的 LoRA 模型**，而 LoRA 模型通常是用户上传的微调权重，不支持标准 API。如果你想使用 API，请在 "API Model Override" 字段中手动输入官方模型 ID。

### Q: 能否让应用自动切换到支持 API 的模型?

A: 可以，但这会改变原始模型的效果。我们建议你明确知道自己在使用哪个模型，所以需要手动在 "API Model Override" 中指定。

### Q: 官方会增加对 LoRA 模型的 API 支持吗?

A: 这取决于 ModelScope 平台的规划。目前 LoRA 模型需要动态加载基础模型和权重，技术上比较复杂，所以暂时只支持在 Studio 中使用。

### Q: 我该如何知道某个新模型是否支持 API?

A: 使用诊断工具:
```bash
MODELSCOPE_DEBUG=1 python app.py --model "owner/model-name"
```

如果返回 200 或成功的 task_id，说明支持 API。如果返回 40212，说明不支持。
