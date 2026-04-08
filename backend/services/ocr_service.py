"""
OCR Service - PaddleOCR Identity Extraction (Offline V22.0)
Strategy: STOP overwriting inference.yml - let PaddleX read its own model files.
           Only fix the mean/std scalar issue if files are missing/corrupted.
"""
import os
import re
import sys
import json
import traceback
from pathlib import Path

# === VSCode / Direct Running Path Fix ===
script_dir = Path(__file__).resolve().parent
project_root = str(script_dir.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.config import get_config
from backend.services.llm_client import chat_json

# === Global ENV Flags (set before any paddle import) ===
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_new_executor"] = "0"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PADDLE_PLATFORM_DEVICE"] = "cpu"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ocr_instance = None


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
        paddle.device.set_device('cpu')

        from paddleocr import PaddleOCR
        off_d = os.path.join(project_root, "offline_models", "whl")
        if not os.path.exists(off_d):
            off_d = os.path.join(os.getcwd(), "whl")

        det_p = _find_model_sub_dir(off_d, "det")
        rec_p = _find_model_sub_dir(off_d, "rec")

        print(f"[OCR] det={det_p}")
        print(f"[OCR] rec={rec_p}")

        # DO NOT write/overwrite inference.yml - let PaddleX use the model's own config
        # Use new PaddleOCR 3.4.0 API parameters; disable orientation classifier (CLS)
        base_kw = {
            "enable_mkldnn": False,
            "text_detection_model_dir": det_p,
            "text_recognition_model_dir": rec_p,
            "use_textline_orientation": False,
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
                    if "PASSPORT" in full_t or "DOC" in full_t:
                        return {"name": "", "id_number": val, "id_type": "passport"}
    return {}


def extract_id_info(image_path: str) -> dict:
    ocr = _get_ocr()
    try:
        r = ocr.ocr(image_path)
    except Exception as e:
        print(f"[OCR] Inference Crash: {e}")
        traceback.print_exc()
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
        res["confidence"] = round(sum(x["confidence"] for x in texts) / len(texts), 3)
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


if __name__ == "__main__":
    img = sys.argv[1] if len(sys.argv) > 1 else "id.jpg"
    if os.path.exists(img):
        print(json.dumps(extract_id_info(img), indent=4, ensure_ascii=False))
    else:
        print(f"Image not found: {img}")
