"""
OCR 服务 — PaddleOCR 证件信息提取（离线增强模式 V4.0）
深度兼容 PaddleX 3.0 (3.4.0) 的全量元数据需求
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

_ocr_instance = None


def _ensure_inference_yml(model_dir: str, model_type: str):
    """
    补齐 PaddleX 3.0 必需的全量元数据。
    如果 model_name mismatch，很大原因是缺少了 version 或 task_type。
    """
    if not model_dir or not os.path.isdir(model_dir):
        return
    
    yml_path = os.path.join(model_dir, "inference.yml")
    deploy_path = os.path.join(model_dir, "deploy.yml")
    
    # 强制清理旧配置以重新生成 (重要：确保 V4.0 补丁生效)
    print(f"[OCR] 正在清理并重建 {model_type} 核心配置: {model_dir}")
    for p in [yml_path, deploy_path]:
        if os.path.exists(p):
            try: os.remove(p)
            except: pass

    # 适配 PaddleX 3.0.0 的全字段配置模板
    configs = {
        "det": """Global:
  model_name: "ch_PP-OCRv4_mobile_det"
  model_type: det
  algorithm: DB
  task_type: OCR
  version: "3.0.0"
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
  model_name: "ch_PP-OCRv4_mobile_rec"
  model_type: rec
  algorithm: SVTR_LCNet
  task_type: OCR
  version: "3.0.0"
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
  model_name: "ch_ppocr_mobile_v2.0_cls"
  model_type: cls
  algorithm: CLS
  task_type: OCR
  version: "3.0.0"
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
            # 同时生成两个文件以兼容不同加载器
            for p in [yml_path, deploy_path]:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
            print(f"[OCR] 核心元数据补丁已写入 {model_type} 目录")
        except Exception as e:
            print(f"[OCR] 写入离线配置文件失败: {e}")


def _find_model_sub_dir(base_dir, type_name) -> str | None:
    search_path = os.path.join(base_dir, type_name)
    if not os.path.exists(search_path): return None
    for root, dirs, files in os.walk(search_path):
        if "inference.pdmodel" in files:
            return os.path.abspath(root)
    return None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        try:
            import paddle
            paddle.device.set_device('cpu')
        except: pass
        from paddleocr import PaddleOCR

        # 基准路径探测
        script_p = os.path.abspath(__file__)
        base_d = os.path.dirname(os.path.dirname(os.path.dirname(script_p)))
        if not os.path.exists(os.path.join(base_d, "offline_models")):
            base_d = os.getcwd()
        off_d = os.path.join(base_d, "offline_models", "whl")

        # 路径与元数据补丁
        det_p = _find_model_sub_dir(off_d, "det")
        rec_p = _find_model_sub_dir(off_d, "rec")
        cls_p = _find_model_sub_dir(off_d, "cls")

        if det_p: _ensure_inference_yml(det_p, "det")
        if rec_p: _ensure_inference_yml(rec_p, "rec")
        if cls_p: _ensure_inference_yml(cls_p, "cls")

        # 参数集
        base_kw = {"lang": "ch", "enable_mkldnn": False}
        if det_p: base_kw["det_model_dir"] = det_p
        if rec_p: base_kw["rec_model_dir"] = rec_p
        if cls_p:
            base_kw["cls_model_dir"] = cls_p
            base_kw["use_angle_cls"] = True
        else:
            base_kw["use_angle_cls"] = False

        try:
            print(f"[OCR] 正在以深度兼容模式 (Metadata V4.0) 初始化 PaddleOCR...")
            _ocr_instance = PaddleOCR(**base_kw)
        except Exception as e:
            print(f"[OCR] 初始化失败，正在打印详细堆栈定位原因:")
            traceback.print_exc()
            try:
                # 最后的终极尝试：完全不带参数初始化看是否能读取默认
                _ocr_instance = PaddleOCR(lang="ch", use_gpu=False)
            except:
                print(f"[OCR] 底层依赖库不完整或版本冲突，实例化无法继续。")

    return _ocr_instance


def extract_id_info(image_path: str) -> dict:
    ocr = _get_ocr()
    try:
        r = ocr.ocr(image_path)
    except Exception as e:
        print(f"[OCR] 引擎运行期底层报错: {e}")
        r = None

    if not r or not r[0]:
        return {"name": "", "id_number": "", "id_type": "unknown", "all_text": [], "confidence": 0.0}

    # 数据解析
    texts = []
    if isinstance(r[0], list):
        for line in r[0]:
            try:
                texts.append({"text": line[1][0], "confidence": line[1][1]})
            except: pass
    elif isinstance(r[0], dict):
        texts = [{"text": t, "confidence": s} for t, s in zip(r[0].get('rec_texts', []), r[0].get('rec_scores', []))]

    all_t = [x["text"] for x in texts]
    full_t = " ".join(all_t)
    name, id_n, id_type = "", "", "unknown"

    # 正则规则组
    if any(k in full_t for k in ["姓名", "性别", "身份号码", "身份证"]):
        id_type = "id_card"
        for i, t in enumerate(all_t):
            if "姓名" in t:
                p = t.replace("姓名", "").strip()
                name = p if p else (all_t[i+1] if i+1 < len(all_t) else "")
                break
        for t in all_t:
            m = re.search(r'\d{17}[\dXx]', t)
            if m: id_n = m.group(); break
    elif any(k in full_t.upper() for k in ["PASSPORT", "P<", "DOCUMENT NO"]):
        id_type = "passport"
        for t in all_t:
            if t.startswith("P<"): name = t[5:].replace("<", " ").strip(); break
        for t in all_t:
            m = re.search(r'[A-Z]\d{6,8}', t); 
            if m: id_n = m.group(); break
    elif any(k in full_t.upper() for k in ["DRIVER", "LICENSE", "驾驶证"]):
        id_type = "driver_license"
        for i, t in enumerate(all_t):
            if "1" in t and i+1 < len(all_t): name = all_t[i+1]; break
        for t in all_t:
            if "DL" in t.upper(): id_n = re.sub(r'[^A-Z0-9]', '', t.split("DL")[-1]); break

    # 兜底通用提取
    if not name or not id_n:
        for t in all_t:
            if not id_n:
                m = re.search(r'[A-Za-z]?\d{6,18}[A-Za-zXx]?', t)
                if m: id_n = m.group()
            if not name and 2 <= len(t) <= 4 and re.match(r'^[\u4e00-\u9fff]+$', t):
                name = t

    avg_conf = sum(x["confidence"] for x in texts) / len(texts) if texts else 0
    return {
        "name": name.strip(),
        "id_number": id_n.strip(),
        "id_type": id_type,
        "all_text": all_t,
        "confidence": round(avg_conf, 3)
    }


if __name__ == "__main__":
    import json
    img = sys.argv[1] if len(sys.argv) > 1 else "test_data/case_001_pass/id_document.jpg"
    print(f"\n--- PaddleOCR 3.4.0 绝技补丁 V4.0 ---\n测试图片: {img}\n")
    if not os.path.exists(img):
        print(f"找不到图片: {img}")
    else:
        try:
            res = extract_id_info(img)
            print(json.dumps(res, indent=4, ensure_ascii=False))
        except Exception:
            traceback.print_exc()
