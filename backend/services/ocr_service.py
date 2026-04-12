# === Environment Flags MUST be set before any paddle imports ===
import os
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"
os.environ["FLAGS_enable_new_executor"] = "0"
os.environ["PADDLE_INF_PIR_API"] = "0"
os.environ["PADDLE_ONEDNN_ENABLED"] = "0"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PADDLE_PLATFORM_DEVICE"] = "cpu"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

import re
import sys
import json
import traceback
from pathlib import Path

# === Path Fix ===
script_dir = Path(__file__).resolve().parent
project_root = str(script_dir.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Check if paddle is available
PADDLE_AVAILABLE = False
try:
    import paddle
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    print("[OCR] Warning: paddlepaddle or paddleocr not installed. Running in Fallback/Vision mode.")

from backend.config import get_config
from backend.services.llm_client import chat_json

_ocr_instance = None

# === Correct YAML templates verified against PaddleX 3.x predictor source ===
_CORRECT_YMLS = {
    "det": """\
Global:
  model_name: "PP-OCRv5_server_det"
  model_type: det
PreProcess:
  transform_ops:
    - DetResizeForTest:
        limit_side_len: 960
        limit_type: max
    - NormalizeImage:
        mean: [0.485, 0.456, 0.406]
        std: [0.229, 0.224, 0.225]
        scale: 0.00392156862745098
        order: ""
    - ToCHWImage: null
PostProcess:
  name: DBPostProcess
  thresh: 0.3
  box_thresh: 0.6
  max_candidates: 1000
  unclip_ratio: 2.0
  use_dilation: false
  score_mode: fast
  box_type: quad
""",
    "rec": """\
Global:
  model_name: "PP-OCRv5_server_rec"
  model_type: rec
  use_space_char: true
PreProcess:
  transform_ops:
    - RecResizeImg:
        image_shape: [3, 48, 320]
PostProcess:
  name: CTCLabelDecode
  character_dict: null
""",
}

def _find_model_sub_dir(base_dir, type_name) -> str | None:
    path = os.path.join(base_dir, type_name)
    if not os.path.exists(path): return None
    for root, dirs, files in os.walk(path):
        if "inference.pdmodel" in files: return os.path.abspath(root)
    return None

def _write_correct_yml(model_dir: str, model_type: str):
    """Write the correct inference.yml with verified PaddleX 3.x operator names."""
    if not model_dir or not os.path.isdir(model_dir):
        return
    content = _CORRECT_YMLS.get(model_type)
    if not content:
        return

    # Embed character dictionary into rec yaml (Solving charset index mismatch)
    if model_type == "rec" and "character_dict: null" in content:
        dict_path = os.path.join(project_root, "backend", "services", "ppocr_keys_v1.txt")
        if os.path.exists(dict_path):
            try:
                with open(dict_path, "r", encoding="utf-8") as f:
                    chars = [line.strip("\n") for line in f]
                char_array_str = json.dumps(chars, ensure_ascii=False)
                content = content.replace("character_dict: null", f"character_dict: {char_array_str}")
                print(f"[OCR] Embedded {len(chars)} characters into rec yaml.")
            except Exception as e:
                print(f"[OCR] Failed to embed character dict: {e}")

    for fname in ["inference.yml", "deploy.yml"]:
        fpath = os.path.join(model_dir, fname)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[OCR] Wrote correct yml ({model_type}): {fpath}")
        except Exception as e:
            print(f"[OCR] Failed to write {fpath}: {e}")

def _get_ocr():
    global _ocr_instance
    if not PADDLE_AVAILABLE:
        return None
        
    if _ocr_instance is None:
        try:
            paddle.device.set_device('cpu')
            
            # --- Robust Offline Path Resolution ---
            off_d = os.path.join(project_root, "offline_models", "whl")
            if not os.path.exists(off_d):
                off_d = os.path.join(os.getcwd(), "whl")
            
            det_p = _find_model_sub_dir(off_d, "det")
            rec_p = _find_model_sub_dir(off_d, "rec")
            
            # Auto-injector for inference.yml
            _write_correct_yml(det_p, "det")
            _write_correct_yml(rec_p, "rec")

            base_kw = {
                "text_detection_model_dir": det_p,
                "text_recognition_model_dir": rec_p,
                "use_textline_orientation": False, # CLS often causes unhashable type errors
                "enable_mkldnn": False
            }
            
            print(f"[OCR] Initializing PaddleOCR with Verified Params.")
            _ocr_instance = PaddleOCR(**base_kw)
        except Exception as e:
            print(f"[OCR] Init failure: {e}")
            traceback.print_exc()
            return None
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
    name = ""
    id_n = ""
    # ICAO 9303 TD3 Line 2
    mrz2_regex = re.compile(r'([A-Z0-9<]{9})[0-9A-Z<][A-Z<]{3}[\d<]{6}[0-9A-Z<][MFX<][\d<]{6}')
    for t in all_text:
        t_clean = t.upper().replace(" ", "").replace(":", "")
        m_line2 = mrz2_regex.search(t_clean)
        if m_line2:
            id_n = m_line2.group(1).replace("<", "")
        # Line 1 extraction
        if t_clean.startswith("P") and "<<" in t_clean and len(t_clean) > 20:
            try:
                parts = t_clean[5:].split("<<")
                if len(parts) >= 2:
                    surname = parts[0].replace("<", " ").strip()
                    given = parts[1].replace("<", " ").strip()
                    name = f"{surname} {given}".strip()
            except: pass
    if id_n:
        return {"name": name, "id_number": id_n, "id_type": "passport"}
    return {}

from backend.services.vision_ocr import extract_id_info_vision

def extract_id_info(image_path: str) -> dict:
    cfg = get_config()
    use_vision = getattr(cfg, 'use_vision_ocr', False)
    
    if use_vision or not PADDLE_AVAILABLE:
        return extract_id_info_vision(image_path)

    ocr = _get_ocr()
    if not ocr:
        return extract_id_info_vision(image_path)

    try:
        r = ocr.ocr(image_path)
    except Exception as e:
        print(f"[OCR] Inference Crash: {e}")
        return extract_id_info_vision(image_path)

    if not r or not r[0]:
        return {"name": "", "id_number": "", "id_type": "unknown", "all_text": []}

    texts = []
    res_obj = r[0]
    
    # PaddleX 3.4.0 Dict Format vs PaddleOCR 2.x List Format
    try:
        if isinstance(res_obj, dict) and "rec_texts" in res_obj:
            for t, s in zip(res_obj["rec_texts"], res_obj["rec_scores"]):
                texts.append({"text": str(t), "confidence": float(s)})
        else:
            # Traditional list format
            for line in res_obj:
                texts.append({"text": str(line[1][0]), "confidence": float(line[1][1])})
    except Exception as e:
        print(f"[OCR] Format extraction error: {e}")

    all_t = [x["text"] for x in texts]
    
    # 1. Regex/MRZ Engine
    res = _parse_mrz(all_t)
    if not res: res = _parse_id_card(all_t)
    
    if res and res.get("id_number"):
        res["all_text"] = all_t
        return res

    # 2. LLM Fallback (Normalization)
    system_prompt = cfg.get_prompt("id_extraction_fallback")
    if system_prompt:
        try:
            normalized = chat_json(system_prompt, " ".join(all_t))
            if normalized and normalized.get("id_number"):
                normalized["all_text"] = all_t
                return normalized
        except Exception as e:
            print(f"[OCR] LLM Normalization failed: {e}")

    return {"name": "", "id_number": "", "id_type": "unknown", "all_text": all_t}
