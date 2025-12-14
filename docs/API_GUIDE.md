# ModelScope API 使用指南

## 🔑 获取 API Token

1. 访问 [ModelScope Token 管理页](https://modelscope.cn/my/myaccesstoken)
2. 点击 "生成新 Token"
3. 复制生成的 Token (格式类似: `xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

## ✅ 验证 Token

使用诊断工具测试 Token 是否有效:

```bash
# 方法 1: 直接传入 Token
MODELSCOPE_DEBUG=1 python app.py

# 方法 2: 使用环境变量
export MODELSCOPE_API_TOKEN="your-token-here"
MODELSCOPE_DEBUG=1 python app.py

# 测试特定模型
MODELSCOPE_DEBUG=1 python app.py --model "AI-ModelScope/stable-diffusion-xl"
```

## 🎨 在应用中使用

### 方法 1: 通过 UI 输入 (推荐)

1. 启动应用: `python app.py`
2. 打开浏览器访问显示的地址
3. 切换到 "Generate" 标签页
4. 在 "ModelScope API Token" 输入框中粘贴你的 Token
5. 点击 "Save Token" 按钮
6. Token 会保存在当前会话中 (关闭浏览器后需要重新输入)

### 方法 2: 使用环境变量

在启动应用前设置环境变量:

```bash
export MODELSCOPE_API_TOKEN="your-token-here"
python app.py
```

或在 `.zshrc`/`.bashrc` 中永久设置:

```bash
echo 'export MODELSCOPE_API_TOKEN="your-token-here"' >> ~/.zshrc
source ~/.zshrc
```

## 🚨 常见问题

### 错误: 40212

**原因:**
- 模型 ID 格式不正确 (必须是 `owner/model-name` 格式)
- 模型不支持 API 调用
- Token 权限不足

**解决方法:**

1. **检查模型 ID 格式**
   ```
   ❌ stable-diffusion-xl
   ✅ AI-ModelScope/stable-diffusion-xl
   ```

2. **确认模型支持 API**
   - 访问模型主页: `https://modelscope.cn/models/{owner}/{model-name}`
   - 查看是否有 "API 调用" 说明
   - 某些模型仅支持 Studio 部署,不支持 API

3. **检查 Token 权限**
   - 重新生成 Token 并确保开通图像生成权限
   - 某些 API 需要实名认证或额外申请

4. **测试官方推荐模型**
   ```bash
   MODELSCOPE_DEBUG=1 python app.py --model "AI-ModelScope/stable-diffusion-xl"
   ```

### 错误: 401 Unauthorized

**原因:** Token 无效或已过期

**解决方法:**
1. 访问 [Token 管理页](https://modelscope.cn/my/myaccesstoken)
2. 删除旧 Token
3. 生成新 Token
4. 使用新 Token 重新测试

### Token 格式问题

Token 应该是纯字符串,不包含:
- ❌ 引号: `"xxxxx"`
- ❌ Bearer 前缀: `Bearer xxxxx`
- ❌ 空格或换行符

正确格式:
```
xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

诊断脚本会自动清理这些问题,但建议直接粘贴纯 Token。

## 🐛 调试模式

如果遇到问题,开启调试模式查看详细信息:

```bash
export MODELSCOPE_DEBUG=1
python app.py
```

调试信息包括:
- API 请求 URL
- 模型 ID
- Token 前缀 (前10个字符)
- 完整请求体
- 响应状态码和内容

## 📝 推荐的工作流程

1. **首次使用:**
   ```bash
   # 测试 Token
   MODELSCOPE_DEBUG=1 python app.py
   
   # 测试成功后设置环境变量
   export MODELSCOPE_API_TOKEN="your-token"
   
   # 启动应用
   python app.py
   ```

2. **日常使用:**
   ```bash
   # Token 已在环境变量中
   python app.py
   ```

3. **遇到问题:**
   ```bash
   # 开启调试
   export MODELSCOPE_DEBUG=1
   python app.py
   
   # 查看详细日志排查问题
   ```

## 🔗 相关链接

- [ModelScope API 文档](https://modelscope.cn/docs/api-inference/intro)
- [Token 管理](https://modelscope.cn/my/myaccesstoken)
- [模型库](https://modelscope.cn/models)
- [提交问题](https://github.com/neverbiasu/ModelScope-Top-LoRAs/issues)

## 💡 提示

- 使用 "API Model (override)" 字段可以覆盖默认模型
- 模拟模式 (不提供 Token) 可用于测试 UI 功能
- Token 保存在会话中,关闭浏览器后需要重新输入
- 环境变量方式更适合开发和测试
