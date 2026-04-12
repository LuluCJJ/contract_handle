"""
专项测试脚本：验证大模型双模式连通性
支持测试：
1. Requests 模式 (公司内网专用，强制 verify=False)
2. OpenAI SDK 模式 (通过 httpx_client 强制 verify=False)
"""
import os
import sys
import json

# 确保能导入 backend
sys.path.append(os.getcwd())

try:
    from backend.services.llm_client import chat, test_connection
    from backend.config import get_config, update_config
except ImportError:
    print("Error: Please run this script from the project root directory.")
    sys.exit(1)

def print_banner(text):
    print("\n" + "="*50)
    print(f" {text}")
    print("="*50)

def run_requests_mode_test():
    print_banner("Test Mode 1: Requests (Internal/Kimi)")
    cfg = get_config()
    
    # Force switch to requests mode for testing
    update_config(api_type="requests")
    
    print(f"[*] Current API Base: {cfg.llm.requests.api_base}")
    print(f"[*] API Key (Prefix): {cfg.llm.requests.api_key[:10]}...")
    
    print("[*] Sending test request...")
    try:
        reply = chat(
            system_prompt="You are a connectivity assistant.",
            user_prompt="Hello, please reply with 'Requests OK' and a brief self-introduction."
        )
        if reply:
            print(f"[OK] Response received!\nContent: {reply}")
        else:
            print("[FAIL] Empty response received.")
    except Exception as e:
        print(f"[ERROR] Exception occurred: {str(e)}")

def run_openai_sdk_test():
    print_banner("Test Mode 2: OpenAI SDK (Standard)")
    cfg = get_config()
    
    # Force switch to openai mode for testing
    update_config(api_type="openai")
    
    print(f"[*] Current API Base: {cfg.llm.openai.api_base}")
    print(f"[*] API Key (Prefix): {cfg.llm.openai.api_key[:10]}...")
    
    print("[*] Sending test request...")
    try:
        reply = chat(
            system_prompt="You are a connectivity assistant.",
            user_prompt="Hello, please reply with 'SDK OK' and a brief self-introduction."
        )
        if reply:
            print(f"[OK] Response received!\nContent: {reply}")
        else:
            print("[FAIL] Empty response received.")
    except Exception as e:
        print(f"[ERROR] Exception occurred: {str(e)}")

def run_connectivity_test_api():
    print_banner("Testing Global API: test_connection()")
    res = test_connection()
    print(f"[*] API returned: {json.dumps(res, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    # Backup current mode
    cfg_initial = get_config()
    original_type = cfg_initial.llm.api_type
    
    try:
        run_requests_mode_test()
        run_openai_sdk_test()
        run_connectivity_test_api()
    finally:
        # Restore original mode
        update_config(api_type=original_type)
        print_banner("Test finished. Original config restored.")
