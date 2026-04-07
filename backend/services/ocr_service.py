"""
OCR 服务 — PaddleOCR 证件信息提取（离线增强模式 V8.0）
修正 PaddleX 3.0 的 PreProcess 字典结构及参数对齐
"""
import os
import re
import sys
import traceback
from pathlib import Path

# === 强制离线环境配置 ===
os.environ["PADDLE_PLATFORM_DEVICE"] = "cpu"
os.environ["PADDLE_PLATFORM_DEVICE_LIST"] = "cpu"
os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ocr_instance = None


def _ensure_inference_yml(model_dir: str, model_type: str):
    """
    补齐 PaddleX 3.0 的 V8.0 补丁。
    核心修正：将 PreProcess 改为字典，包含 transform_ops 键。
    """
    if not model_dir or not os.path.isdir(model_dir):
        return
    
    yml_p = os.path.join(model_dir, "inference.yml")
    deploy_p = os.path.join(model_dir, "deploy.yml")
    
    # 强制每轮清理以确保配置生效
    print(f"[OCR] 正在由于 V8.0 结构对齐更新 {model_type} 目录配置...")
    for p in [yml_p, deploy_p]:
        if os.path.exists(p):
            try: os.remove(p)
            except: pass

    # === V8.0 模型配置：PreProcess 必须是字典并包含 transform_ops ===
    configs = {
        "det": """Global:
  model_name: "PP-OCRv5_server_det"
  model_type: det
  algorithm: DB
  task_type: OCR
  version: "3.0.0"
  transform_type: OCR
PreProcess:
  transform_ops:
    - DetResizeForTest:
        limit_side_len: 960
        limit_type: max
    - Normalize:
        mean: [0.485, 0.456, 0.406]
        std: [0.229, 0.224, 0.225]
        order: hwc
    - ToCHWImage: null
    - KeepKeys:
        keep_keys: [image, shape]
PostProcess:
  thresh: 0.3
  box_thresh: 0.6
  max_candidates: 1000
  unclip_ratio: 1.5
""",
        "rec": """Global:
  model_name: "PP-OCRv5_server_rec"
  model_type: rec
  algorithm: SVTR_LCNet
  task_type: OCR
  version: "3.0.0"
  transform_type: OCR
  use_space_char: true
PreProcess:
  transform_ops:
    - RecResizeImg:
        image_shape: [3, 48, 320]
    - Normalize:
        mean: [0.5, 0.5, 0.5]
        std: [0.5, 0.5, 0.5]
        order: hwc
    - ToCHWImage: null
    - KeepKeys:
        keep_keys: [image]
PostProcess:
  - CTCLabelDecode: null
""",
        "cls": """Global:
  model_name: "PP-LCNet_x1_0_textline_ori"
  model_type: cls
  algorithm: CLS
  task_type: OCR
  version: "3.0.0"
  transform_type: OCR
PreProcess:
  transform_ops:
    - ClsResizeImg:
        image_shape: [3, 48, 192]
    - Normalize:
        mean: [0.5, 0.5, 0.5]
        std: [0.5, 0.5, 0.5]
        order: hwc
    - ToCHWImage: null
    - KeepKeys:
        keep_keys: [image]
PostProcess:
  - ClsPostProcess: null
"""
    }
    
    content = configs.get(model_type)
    if content:
        try:
            for p in [yml_p, deploy_p]:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
            print(f"[OCR] V8.0 PreProcess 结构已就绪")
        except Exception as e:
            print(f"[OCR] V8.0 写入失败: {e}")


def _find_model_sub_dir(base_dir, type_name) -> str | None:
    path = os.path.join(base_dir, type_name)
    if not os.path.exists(path): return None
    for root, dirs, files in os.walk(path):
        if "inference.pdmodel" in files:
            return os.path.abspath(root)
    return None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        try:
            import paddle
            # 设置设备环境变量高于代码参数
            paddle.device.set_device('cpu')
        except: pass
        from paddleocr import PaddleOCR

        # 基准路径探测
        script_p = os.path.abspath(__file__)
        base_d = os.path.dirname(os.path.dirname(os.path.dirname(script_p)))
        if not os.path.exists(os.path.join(base_d, "offline_models")):
            base_d = os.getcwd()
        off_d = os.path.join(base_d, "offline_models", "whl")

        det_p = _find_model_sub_dir(off_d, "det")
        rec_p = _find_model_sub_dir(off_d, "rec")
        cls_p = _find_model_sub_dir(off_d, "cls")

        # 同步元数据配置
        if det_p: _ensure_inference_yml(det_p, "det")
        if rec_p: _ensure_inference_yml(rec_p, "rec")
        if cls_p: _ensure_inference_yml(cls_p, "cls")

        # === V8.0 锁定最简参数集 ===
        # 移除了所有 unknown 参数 (use_gpu, enable_mkldnn 等)
        base_kw = {
            # 仅保留核心路径和必需的 orientation 开关
        }
        
        # 路径参数 (使用从之前 warning 中捕捉到的 text_xxxx 格式)
        if det_p: base_kw["text_detection_model_dir"] = det_p
        if rec_p: base_kw["text_recognition_model_dir"] = rec_p
        if cls_p:
            base_kw["textline_orientation_model_dir"] = cls_p
            base_kw["use_textline_orientation"] = True
        else:
            base_kw["use_textline_orientation"] = False

        try:
            print(f"[OCR] 正在以 V8.0 的字典嵌套配置初始化 PaddleOCR...")
            _ocr_instance = PaddleOCR(**base_kw)
        except Exception as e:
            print(f"[OCR] V8.0 初始化失败。详细堆栈如下:")
            traceback.print_exc()
            try:
                # 保命回退：完全空参数或仅限路径参数
                _ocr_instance = PaddleOCR(text_detection_model_dir=det_p, text_recognition_model_dir=rec_p)
            except:
                print(f"[OCR] 引擎彻底崩溃。")

    return _ocr_instance


def extract_id_info(image_path: str) -> dict:
    ocr = _get_ocr()
    try:
        r = ocr.ocr(image_path)
    except Exception as e:
        print(f"[OCR] 运行期底层报错: {e}")
        r = None

    if not r or not r[0]:
        return {"name": "", "id_number": "", "id_type": "unknown", "all_text": [], "confidence": 0.0}

    texts = []
    if isinstance(r[0], list):
        for line in r[0]:
            try: texts.append({"text": line[1][0], "confidence": line[1][1]})
            except: pass
    elif isinstance(r[0], dict):
        texts = [{"text": t, "confidence": s} for t, s in zip(r[0].get('rec_texts', []), r[0].get('rec_scores', []))]

    all_t = [x["text"] for x in texts]
    if not all_t: return {"name": "", "id_number": "", "id_type": "unknown", "all_text": [], "confidence": 0.0}
    
    full_t = " ".join(all_t)
    name, id_n, id_type = "", "", "unknown"

    # 正则提取规则 (UTF-8)
    if any(k in full_t for k in ["姓名", "性别", "身份号码", "身份证"]):
        id_type = "id_card"
        for i, t in enumerate(all_t):
            if "姓名" in t:
                name = t.replace("姓名", "").strip() or (all_t[i+1] if i+1 < len(all_t) else "")
                break
        for t in all_t:
            m = re.search(r'\d{17}[\dXx]', t)
            if m: id_n = m.group(); break
    elif any(k in full_t.upper() for k in ["PASSPORT", "P<", "DOCUMENT NO"]):
        id_type = "passport"
        for t in all_t:
            if t.startswith("P<"): name = t[5:].replace("<", " ").strip(); break
        for t in all_t:
            m = re.search(r'[A-Z]\d{6,8}', t)
            if m: id_n = m.group(); break

    if not name or not id_n:
        for t in all_t:
            if not id_n:
                m = re.search(r'[A-Za-z]?\d{6,18}[A-Za-zXx]?', t)
                if m: id_n = m.group()
            if not name and 2 <= len(t) <= 4 and re.match(r'^[\u4e00-\u9fff]+$', t):
                name = t

    avg_conf = sum(x["confidence"] for x in texts) / len(texts) if texts else 0
    return {
        "name": name.strip(), "id_number": id_n.strip(), "id_type": id_type,
        "all_text": all_t, "confidence": round(avg_conf, 3)
    }


if __name__ == "__main__":
    import json
    img = sys.argv[1] if len(sys.argv) > 1 else "test_data/case_001_pass/id_document.jpg"
    print(f"\n--- PaddleOCR 3.4.0+ V8.0 (预处理字典化适配) ---\n测试图片: {img}\n")
    if not os.path.exists(img): print(f"找不到测试图片")
    else:
        try:
            res = extract_id_info(img)
            print(json.dumps(res, indent=4, ensure_ascii=False))
        except: traceback.print_exc()
