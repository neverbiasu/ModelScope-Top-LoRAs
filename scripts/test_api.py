#!/usr/bin/env python3
"""
ModelScope API 诊断工具

用于测试 API Token 和模型配置是否正确。
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_token(token: str, model_id: str = "AI-ModelScope/stable-diffusion-xl") -> dict:
    """测试 API Token 和模型是否可用"""
    try:
        import requests
    except ImportError:
        return {
            "success": False,
            "error": "requests 库未安装。请运行: pip install requests"
        }
    
    # Clean token
    clean_token = token.strip().strip('"').strip("'")
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token.split(None, 1)[-1].strip()
    
    if not clean_token:
        return {
            "success": False,
            "error": "Token 为空"
        }
    
    # Validate model ID format
    if "/" not in model_id:
        return {
            "success": False,
            "error": f"模型 ID 格式错误: '{model_id}' (应该是 owner/model-name 格式)"
        }
    
    base_url = os.environ.get("MODELSCOPE_INFER_BASE", "https://api-inference.modelscope.cn/")
    gen_url = base_url.rstrip("/") + "/v1/images/generations"
    
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Content-Type": "application/json",
        "X-ModelScope-Async-Mode": "true",
    }
    
    body = {
        "model": model_id,
        "prompt": "a beautiful sunset",
        "size": "512x512",
    }
    
    print(f"\n{'='*60}")
    print(f"🔍 测试配置")
    print(f"{'='*60}")
    print(f"API 地址: {gen_url}")
    print(f"模型 ID: {model_id}")
    print(f"Token (前10位): {clean_token[:10]}...")
    print(f"请求体: {json.dumps(body, ensure_ascii=False, indent=2)}")
    print(f"{'='*60}\n")
    
    try:
        print("📤 发送请求...")
        response = requests.post(gen_url, json=body, headers=headers, timeout=30)
        
        print(f"📥 响应状态码: {response.status_code}")
        print(f"响应头: {json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}")
        
        try:
            response_data = response.json()
            print(f"响应体: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        except Exception:
            print(f"响应体 (文本): {response.text[:500]}")
            response_data = {"text": response.text}
        
        if response.status_code == 401:
            return {
                "success": False,
                "error": "Token 无效或已过期",
                "status_code": 401,
                "response": response_data,
                "suggestion": "请检查 Token 是否正确: https://modelscope.cn/my/myaccesstoken"
            }
        elif response.status_code == 400:
            error_detail = str(response_data)
            suggestions = []
            
            if "40212" in error_detail:
                suggestions = [
                    "错误码 40212 通常表示:",
                    "1. 模型不支持此 API (检查模型详情页)",
                    "2. 参数格式不正确",
                    "3. Token 权限不足",
                    "",
                    "建议尝试:",
                    f"- 访问模型页面确认支持 API: https://modelscope.cn/models/{model_id}",
                    "- 尝试其他模型 (如 AI-ModelScope/stable-diffusion-xl)",
                    "- 检查 Token 权限设置"
                ]
            
            return {
                "success": False,
                "error": f"请求失败 (400): {error_detail}",
                "status_code": 400,
                "response": response_data,
                "suggestions": suggestions
            }
        elif response.status_code >= 400:
            return {
                "success": False,
                "error": f"请求失败 ({response.status_code})",
                "status_code": response.status_code,
                "response": response_data
            }
        else:
            return {
                "success": True,
                "message": "✅ API 调用成功!",
                "status_code": response.status_code,
                "response": response_data,
                "task_id": response_data.get("task_id")
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "请求超时"
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "error": f"网络连接错误: {e}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"未知错误: {e}"
        }


def main():
    parser = argparse.ArgumentParser(description="测试 ModelScope API Token 和模型配置")
    parser.add_argument("--token", help="API Token (或通过环境变量 MODELSCOPE_API_TOKEN 提供)")
    parser.add_argument("--model", default="AI-ModelScope/stable-diffusion-xl", 
                       help="模型 ID (格式: owner/model-name)")
    
    args = parser.parse_args()
    
    # Get token from args or environment
    token = args.token or os.environ.get("MODELSCOPE_API_TOKEN")
    
    if not token:
        print("❌ 错误: 未提供 API Token")
        print("\n使用方法:")
        print("  1. 通过参数: python scripts/test_api.py --token YOUR_TOKEN")
        print("  2. 通过环境变量: export MODELSCOPE_API_TOKEN=YOUR_TOKEN && python scripts/test_api.py")
        print("\n获取 Token: https://modelscope.cn/my/myaccesstoken")
        sys.exit(1)
    
    result = test_token(token, args.model)
    
    print(f"\n{'='*60}")
    print(f"📊 测试结果")
    print(f"{'='*60}")
    
    if result["success"]:
        print(f"✅ {result['message']}")
        if result.get("task_id"):
            print(f"任务 ID: {result['task_id']}")
        print("\n您的配置正常,可以使用 API 进行图像生成!")
    else:
        print(f"❌ 测试失败: {result['error']}")
        if result.get("suggestions"):
            print("\n💡 建议:")
            for suggestion in result["suggestions"]:
                print(f"   {suggestion}")
    
    print(f"{'='*60}\n")
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
