"""
OCR 服务 — PaddleOCR 证件信息提取（离线增强模式）
特别适配 PaddleOCR 3.4.0 (PaddleX) 的 'model_name' 必需字段
"""
import os
import re
import sys
from pathlib import Path

# === 强制离线环境配置 ===
os.environ["PADDLE_PLATFORM_DEVICE"] = "cpu"
os.environ["PADDLE_PLATFORM_DEVICE_LIST"] = "cpu"
os.environ["PYTHONHTTPSVERIFY"] = "0"

_ocr_instance = None


def _ensure_inference_yml(model_dir: str, model_type: str):
    """如果目录下缺少 inference.yml 或配置不完整，则补全标准的配置逻辑"""
    if not model_dir or not os.path.isdir(model_dir):
        return
    
    yml_path = os.path.join(model_dir, "inference.yml")
    
    # 如果文件已存在，检查是否包含 'model_name' (关键校验)
    if os.path.exists(yml_path):
        try:
            with open(yml_path, "r", encoding="utf-8") as f:
                c = f.read()
                if "model_name" in c:
                    return
                else:
                    print(f"[OCR] 旧配置缺失 model_name，准备覆盖: {yml_path}")
        except Exception:
            pass

    print(f"[OCR] 正在由于 PaddleOCR 3.4.0 兼容性需求生成/更新 {model_type} 配置: {yml_path}")
    
    # 定义标准 PP-OCRv4 离线配置模版，补充了必需的 model_name
    configs = {
        "det": """Global:
  model_type: det
  algorithm: DB
  model_name: "PP-OCRv4_det"
  transform_type: OCR
PreProcess:
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
  - DBPostProcess:
      thresh: 0.3
      box_thresh: 0.6
      max_candidates: 1000
      unclip_ratio: 1.5
""",
        "rec": """Global:
  model_type: rec
  algorithm: SVTR_LCNet
  model_name: "PP-OCRv4_rec"
  transform_type: OCR
  use_space_char: true
PreProcess:
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
  model_type: cls
  algorithm: CLS
  model_name: "ch_ppocr_mobile_v2.0_cls"
  transform_type: OCR
PreProcess:
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
            with open(yml_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[OCR] 配置补完成功: {yml_path}")
        except Exception as e:
            print(f"[OCR] 写入配置文件失败: {e}")


def _find_model_dir_from_config() -> str | None:
    """尝试从项目配置中读取自定义模型路径"""
    try:
        from backend.config import get_config
        cfg = get_config()
        if cfg.ocr_model_dir and os.path.isdir(cfg.ocr_model_dir):
            return cfg.ocr_model_dir
    except Exception:
        pass
    return None


def _find_model_sub_dir(base_dir, type_name) -> str | None:
    """在指定的根目录下深度搜索包含 inference.pdmodel 的文件夹"""
    search_path = os.path.join(base_dir, type_name)
    if not os.path.exists(search_path):
        return None
    
    for root, dirs, files in os.walk(search_path):
        if "inference.pdmodel" in files:
            abs_path = os.path.abspath(root)
            print(f"[OCR] 已锁定 {type_name} 离线模型: {abs_path}")
            return abs_path
    return None


def _get_ocr():
    """初始化并返回 PaddleOCR 实例"""
    global _ocr_instance
    if _ocr_instance is None:
        try:
            import paddle
            paddle.device.set_device('cpu')
        except Exception:
            pass

        from paddleocr import PaddleOCR

        # 计算搜索基准目录
        script_path = os.path.abspath(__file__)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
        if not os.path.exists(os.path.join(base_dir, "offline_models")):
            base_dir = os.getcwd()
            
        offline_dir = os.path.join(base_dir, "offline_models", "whl")

        # 1. 寻找路径
        det_path = _find_model_sub_dir(offline_dir, "det")
        rec_path = _find_model_sub_dir(offline_dir, "rec")
        cls_path = _find_model_sub_dir(offline_dir, "cls")

        # 2. 补齐/更新缺失的带有 model_name 字段的 inference.yml
        if det_path: _ensure_inference_yml(det_path, "det")
        if rec_path: _ensure_inference_yml(rec_path, "rec")
        if cls_path: _ensure_inference_yml(cls_path, "cls")

        # 3. 构造参数 - 针对高版本仅保留基础路径和核心逻辑开关
        kwargs = {
            "lang": "ch",
            "enable_mkldnn": False,
            "use_angle_cls": True if cls_path else False
        }
        
        if det_path: kwargs["det_model_dir"] = det_path
        if rec_path: kwargs["rec_model_dir"] = rec_path
        if cls_path: kwargs["cls_model_dir"] = cls_path

        try:
            print(f"[OCR] 正在以 3.4.0 (PaddleX) 兼容模式初始化...")
            _ocr_instance = PaddleOCR(**kwargs)
        except Exception as e:
            print(f"[OCR] 初始化再次失败: {e}。正在尝试极简初始化模式...")
            # 最后的保命方案：完全不传任何额外参数，只传基础路径
            try:
                minimal_kwargs = {"lang": "ch"}
                if det_path: minimal_kwargs["det_model_dir"] = det_path
                if rec_path: minimal_kwargs["rec_model_dir"] = rec_path
                _ocr_instance = PaddleOCR(**minimal_kwargs)
            except Exception as e2:
                print(f"[OCR] 实例化彻底失败: {e2}")
                _ocr_instance = PaddleOCR() # 最后的回退

    return _ocr_instance


def extract_id_info(image_path: str) -> dict:
    """从证件图片中提取姓名和证件号"""
    ocr = _get_ocr()
    try:
        result = ocr.ocr(image_path)
    except Exception as e:
        print(f"[OCR] 运行遭遇底层异常: {e}")
        result = None

    if not result or not result[0]:
        return {"name": "", "id_number": "", "id_type": "unknown", "all_text": [], "confidence": 0.0}

    texts = []
    # 兼容 List[Line] 和 Dict 结构
    if isinstance(result[0], list):
        for line in result[0]:
            try:
                text = line[1][0]
                conf = line[1][1]
                texts.append({"text": text, "confidence": conf})
            except Exception: pass
    elif isinstance(result[0], dict):
        rec_texts = result[0].get('rec_texts', [])
        rec_scores = result[0].get('rec_scores', [])
        for t, s in zip(rec_texts, rec_scores):
            texts.append({"text": t, "confidence": s})

    all_text = [t["text"] for t in texts]
    full_text = " ".join(all_text)

    name = ""
    id_number = ""
    id_type = "unknown"

    if _is_cn_id_card(all_text, full_text):
        id_type = "id_card"
        name = _extract_cn_id_name(all_text)
        id_number = _extract_cn_id_number(all_text)
    elif _is_passport(all_text, full_text):
        id_type = "passport"
        name = _extract_passport_name(all_text, full_text)
        id_number = _extract_passport_number(all_text, full_text)
    elif _is_driver_license(all_text, full_text):
        id_type = "driver_license"
        name = _extract_dl_name(all_text, full_text)
        id_number = _extract_dl_number(all_text, full_text)

    if not name or not id_number:
        fb = _generic_extract(all_text, full_text)
        name = name or fb.get("name", "")
        id_number = id_number or fb.get("id_number", "")

    avg_conf = sum(t["confidence"] for t in texts) / len(texts) if texts else 0
    return {
        "name": name.strip(),
        "id_number": id_number.strip(),
        "id_type": id_type,
        "all_text": all_text,
        "confidence": round(avg_conf, 3),
    }


# ========== 逻辑辅助函数 ==========

def _is_cn_id_card(texts, full) -> bool:
    return any(k in full for k in ["姓名", "性别", "民族", "公民身份号码", "身份证"])

def _extract_cn_id_name(texts) -> str:
    for i, t in enumerate(texts):
        if "姓名" in t:
            p = t.replace("姓名", "").strip()
            if p: return p
            if i + 1 < len(texts): return texts[i + 1]
    return ""

def _extract_cn_id_number(texts) -> str:
    for t in texts:
        m = re.search(r'\d{17}[\dXx]', t)
        if m: return m.group()
    return ""

def _is_passport(texts, full) -> bool:
    up = full.upper()
    return any(k in up for k in ["PASSPORT", "P<", "DOCUMENT NO"])

def _extract_passport_name(texts, full) -> str:
    for t in texts:
        if t.startswith("P<") and len(t) > 5:
            return t[5:].replace("<", " ").strip()
    return ""

def _extract_passport_number(texts, full) -> str:
    for t in texts:
        m = re.search(r'[A-Z]\d{6,8}', t)
        if m: return m.group()
    return ""

def _is_driver_license(texts, full) -> bool:
    up = full.upper()
    return any(k in up for k in ["DRIVER", "LICENSE", "CLASS"])

def _extract_dl_name(texts, full) -> str:
    for i, t in enumerate(texts):
        if "1" in t and i + 1 < len(texts): return texts[i + 1]
    return ""

def _extract_dl_number(texts, full) -> str:
    for t in texts:
        if "DL" in t.upper(): return re.sub(r'[^A-Z0-9]', '', t.split("DL")[-1])
    return ""

def _generic_extract(texts, full) -> dict:
    name, id_num = "", ""
    for t in texts:
        m = re.search(r'[A-Za-z]?\d{6,18}[A-Za-zXx]?', t)
        if m and not id_num: id_num = m.group()
        if not name and 2 <= len(t) <= 4 and re.match(r'^[\u4e00-\u9fff]+$', t): name = t
    return {"name": name, "id_number": id_num}


if __name__ == "__main__":
    import json
    test_img = sys.argv[1] if len(sys.argv) > 1 else "test_data/case_001_pass/id_document.jpg"
    print(f"\n--- PaddleOCR 3.4.0 兼容补丁 2.0 ---\n测试图片: {test_img}\n")
    if not os.path.exists(test_img):
         print(f"找不到测试图片: {test_img}")
    else:
        try:
            res = extract_id_info(test_img)
            print("[结果报告]:")
            print(json.dumps(res, indent=4, ensure_ascii=False))
        except Exception as e:
            print(f"执行失败: {e}")
            import traceback
            traceback.print_exc()
