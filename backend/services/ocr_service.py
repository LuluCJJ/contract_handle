"""
OCR Service - PaddleOCR Identity Extraction (Offline V21.0 Robust)
Fix: Removed paddle.set_flags dict call to prevent 'unhashable type: dict'
"""
import os
import re
import sys
import json
import traceback
from pathlib import Path
from backend.config import get_config
from backend.services.llm_client import chat_json

# === Global Physical Environment Flags ===
ENV_FLAGS = {
    "FLAGS_use_mkldnn": "0",
    "FLAGS_use_onednn": "0",
    "FLAGS_enable_pir_api": "0",
    "FLAGS_enable_new_executor": "0",
    "KMP_DUPLICATE_LIB_OK": "TRUE",
    "PADDLE_PLATFORM_DEVICE": "cpu"
}
for k, v in ENV_FLAGS.items():
    os.environ[k] = v

_ocr_instance = None

def _ensure_inference_yml(model_dir: str, model_type: str):
    if not model_dir or not os.path.isdir(model_dir): return
    yml_p = os.path.join(model_dir, "inference.yml")
    deploy_p = os.path.join(model_dir, "deploy.yml")
    
    configs = {
        "det": "Global:\n  model_name: \"PP-OCRv5_server_det\"\n  model_type: det\nPreProcess:\n  transform_ops:\n    - DetResize:\n        limit_side_len: 960\n        limit_type: max\n    - Normalize:\n        mean: 0.5\n        std: 0.5\nPostProcess:\n  thresh: 0.3\n  box_thresh: 0.6\n",
        "rec": "Global:\n  model_name: \"PP-OCRv5_server_rec\"\n  model_type: rec\n  use_space_char: true\nPreProcess:\n  transform_ops:\n    - RecResize:\n        target_size: [3, 48, 320]\n    - Normalize:\n        mean: 0.5\n        std: 0.5\nPostProcess:\n  - CTCLabelDecode: null\n",
        "cls": "Global:\n  model_name: \"PP-LCNet_x1_0_textline_ori\"\n  model_type: cls\nPreProcess:\n  transform_ops:\n    - ResizeImage:\n        size: [192, 48]\n    - NormalizeImage:\n        mean: 0.5\n        std: 0.5\n    - ToCHWImage: null\nPostProcess:\n  - ClsPostProcess: null\n"
    }
    content = configs.get(model_type)
    if content:
        for p in [yml_p, deploy_p]:
            with open(p, "w", encoding="utf-8") as f: f.write(content)

def _find_model_sub_dir(base_dir, type_name) -> str | None:
    path = os.path.join(base_dir, type_name)
    if not os.path.exists(path): return None
    for root, dirs, files in os.walk(path):
        if "inference.pdmodel" in files: return os.path.abspath(root)
    return None

def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        import paddle
        # Using native os.environ for flags is more robust than set_flags(dict)
        paddle.device.set_device('cpu')
        
        from paddleocr import PaddleOCR
        script_p = os.path.abspath(__file__)
        base_d = os.path.dirname(os.path.dirname(os.path.dirname(script_p)))
        off_d = os.path.join(base_d, "offline_models", "whl")
        if not os.path.exists(off_d): off_d = os.path.join(os.getcwd(), "whl")

        det_p = _find_model_sub_dir(off_d, "det")
        rec_p = _find_model_sub_dir(off_d, "rec")
        cls_p = _find_model_sub_dir(off_d, "cls")

        if det_p: _ensure_inference_yml(det_p, "det")
        if rec_p: _ensure_inference_yml(rec_p, "rec")
        if cls_p: _ensure_inference_yml(cls_p, "cls")

        base_kw = {
            "use_gpu": False, "enable_mkldnn": False, 
            "det_model_dir": det_p, "rec_model_dir": rec_p, "cls_model_dir": cls_p,
            "use_angle_cls": (cls_p is not None)
        }
        _ocr_instance = PaddleOCR(**base_kw)
    return _ocr_instance

def _parse_id_card(all_text: list) -> dict:
    full_t = " ".join(all_text)
    name, id_n = "", ""
    if any(k in full_t for k in ["姓名", "身份", "公民"]):
        for i, t in enumerate(all_text):
            if "姓名" in t:
                name = t.replace("姓名", "").strip() or (all_text[i+1] if i+1 < len(all_text) else "")
                break
        for t in all_text:
            m = re.search(r'\d{17}[\dXx]', t)
            if m: id_n = m.group(); break
        if id_n: return {"name": name, "id_number": id_n, "id_type": "id_card"}
    return {}

def _parse_mrz(all_text: list) -> dict:
    full_t = "".join(all_text).upper()
    if "P<" in full_t or any(k in full_t for k in ["PASSPORT", "DOCNO", "DOCUMENT NO"]):
        for t in all_text:
            t_clean = t.upper().replace(" ", "").replace(":", "")
            m = re.search(r'([A-Z0-9]{9})\d[A-Z]{3}\d{6}', t_clean)
            if m: return {"name": "Extracted via MRZ", "id_number": m.group(1), "id_type": "passport"}
            m_simple = re.search(r'([A-Z0-9]{7,12})', t_clean)
            if m_simple:
                val = m_simple.group(1)
                if val not in ["PASSPORT", "DOCUMENTNO", "IDENTITY"]:
                    if ("PASSPORT" in full_t or "DOC" in full_t):
                        return {"name": "", "id_number": val, "id_type": "passport"}
    return {}

def extract_id_info(image_path: str) -> dict:
    ocr = _get_ocr()
    try:
        r = ocr.ocr(image_path)
    except Exception as e:
        print(f"[OCR] Inference Crash: {e}")
        r = None

    if not r or not r[0]:
        return {"name": "", "id_number": "", "id_type": "unknown", "all_text": []}

    texts = []
    for line in r[0]:
        try: texts.append({"text": line[1][0], "confidence": line[1][1]})
        except: pass
    all_t = [x["text"] for x in texts]
    
    res = _parse_mrz(all_t)
    if not res: res = _parse_id_card(all_t)
    
    if res and res.get("id_number"):
        res["all_text"] = all_t
        res["confidence"] = round(sum(x["confidence"] for x in texts)/len(texts), 3)
        return res

    print("[OCR] Regex/MRZ failed. Triggering LLM Fallback...")
    cfg = get_config()
    fallback_prompt = cfg.get_prompt("id_extraction_fallback")
    if fallback_prompt:
        try:
            llm_res = chat_json(fallback_prompt, "\n".join(all_t))
            if llm_res and isinstance(llm_res, dict) and llm_res.get("id_number"):
                llm_res["all_text"] = all_t
                return llm_res
        except Exception as e:
            print(f"[OCR] LLM Fallback Error: {e}")

    return {"name": "", "id_number": "", "id_type": "unknown", "all_text": all_t}
