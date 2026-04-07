import os
import zipfile
import json
import shutil
from pathlib import Path

def mask_config():
    """清空/脱密个人密钥"""
    config_file = Path('config.json')
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'llm' in data and 'api_key' in data['llm']:
            data['llm']['api_key'] = '' # 空脱敏
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("个人密钥已成功脱敏。")

def create_zip():
    exclude_dirs = ['.venv', 'venv', '__pycache__', '.git', '.gemini', '.agent', 'uploads']
    exclude_exts = ['.pyc', '.zip']
    zip_filename = "Bank_PreAudit_Demo_V1.zip"
    
    print(f"正在创建打包压缩文件: {zip_filename} ...")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # 过滤排除目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if any(file.endswith(ext) for ext in exclude_exts):
                    continue
                if file == zip_filename:
                    continue
                    
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, '.')
                zipf.write(filepath, arcname)
                
    print(f"打包成功！大小: {os.path.getsize(zip_filename) / (1024*1024):.2f} MB")
    print(f"产出文件位置: {os.path.abspath(zip_filename)}")

if __name__ == '__main__':
    mask_config()
    create_zip()
