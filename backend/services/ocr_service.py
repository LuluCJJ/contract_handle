"""
OCR Service - PaddleOCR Identity Extraction (Offline V22.2)
Fix: Write CORRECT inference.yml using exact operator names from PaddleX 3.x source.
     PIR is disabled via env flags, so array mean/std values are safe to use.
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
# PIR disabled => array mean/std values are safe (no ArrayAttribute bug)
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_new_executor"] = "0"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PADDLE_PLATFORM_DEVICE"] = "cpu"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ocr_instance = None

# === Correct YAML templates verified against PaddleX 3.x predictor source ===
# det: registered funcs are DetResizeForTest, NormalizeImage, ToCHWImage
# rec: registered funcs are RecResizeImg
# PostProcess: dict format with 'name' key (not list)
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

    # For recognition, PaddleX 3.x requires the actual list of characters in YAML,
    # NOT a path. If not provided, it defaults to a-z and crashes on Chinese indices.
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

        # Write verified yml files (correct operator names from PaddleX source)
        _write_correct_yml(det_p, "det")
        _write_correct_yml(rec_p, "rec")

        # Use new PaddleOCR 3.4.0 API; disable orientation classifier (CLS)
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
    name = ""
    id_n = ""
    expiry_date = ""
    # ICAO 9303 TD3 MRZ Line 2: 9-char ID + 1 check + 3 nationality + 6 DOB + 1 check + 1 Sex + 6 Expiry(21-27)
    mrz2_regex = re.compile(r'([A-Z0-9<]{9})[0-9A-Z<][A-Z<]{3}[\d<]{6}[0-9A-Z<][MFX<]([\d<]{6})')

    for t in all_text:
        t_clean = t.upper().replace(" ", "").replace(":", "")

        # Try extract ID and Expiry from MRZ Line 2
        m_line2 = mrz2_regex.search(t_clean)
        if m_line2:
            id_n = m_line2.group(1).replace("<", "")
            raw_expiry = m_line2.group(2)
            if raw_expiry.isdigit():
                # Convert YYMMDD to YYYY-MM-DD (assume 20xx for expiry)
                expiry_date = f"20{raw_expiry[0:2]}-{raw_expiry[2:4]}-{raw_expiry[4:6]}"

        # Try extract Name from MRZ Line 1 (Wait: some OCR might miss the leading 'P')
        # Logic: If it has '<<' and is long enough, it's likely the name line
        if "<<" in t_clean and len(t_clean) > 20:
            try:
                # Find the country code (3 chars) usually preceded by P< or just at start
                # We'll look for the first << and take the part before it as surname
                parts = t_clean.split("<<")
                if len(parts) >= 2:
                    # Surname is at the end of the first part (preceded by type/country)
                    # For simplicity in OCR noise: take the last block of letters before <<
                    surname_raw = re.sub(r'^.*?([A-Z]+)$', r'\1', parts[0])
                    given_raw = parts[1].replace("<", " ").strip()
                    name = f"{surname_raw} {given_raw}".strip()
            except Exception:
                pass

    if id_n:
        return {"name": name, "id_number": id_n, "id_type": "passport", "expiry_date": expiry_date}
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
    res_obj = r[0]
    try:
        # PaddleX 3.4.0 dict-like format
        if "rec_texts" in res_obj and "rec_scores" in res_obj:
            for t, s in zip(res_obj["rec_texts"], res_obj["rec_scores"]):
                texts.append({"text": str(t), "confidence": float(s)})
        else:
            raise KeyError("fallback")
    except (TypeError, KeyError):
        # PaddleOCR 2.x standard list format
        for line in res_obj:
            try:
                texts.append({"text": str(line[1][0]), "confidence": float(line[1][1])})
            except Exception:
                pass
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
    # Test with ID card and passport images
    test_cases = [
        ("test_data/case_001_pass/id_document.jpg", "身份证测试"),
        ("test_data/case_007_risk_idtype/id_document.jpg", "护照/异型证件测试"),
    ]
    for img_path, label in test_cases:
        print(f"\n{'='*50}")
        print(f"[TEST] {label}: {img_path}")
        if os.path.exists(img_path):
            result = extract_id_info(img_path)
            print(json.dumps(result, indent=4, ensure_ascii=False))
        else:
            print(f"  [SKIP] 图片不存在: {img_path}")
