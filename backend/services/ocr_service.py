"""
OCR 服务 — PaddleOCR 证件信息提取（离线增强模式 V14.0）
绝命补丁：!!float 强转元数据类型 + 智能分级降级策略
"""
import os
import re
import sys
import traceback
from pathlib import Path

# === 环境禁令：必须在任何导入前从 shell 层面注入 (V14.0) ===
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["PADDLE_INF_PIR_API"] = "0"
os.environ["PADDLE_ONEDNN_ENABLED"] = "0"
os.environ["PADDLE_PLATFORM_DEVICE"] = "cpu"
os.environ["PADDLE_PLATFORM_DEVICE_LIST"] = "cpu"
os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ocr_instance = None


def _ensure_inference_yml(model_dir: str, model_type: str):
    """
    补齐 PaddleX 3.0 的 V14.0 绝技。
    针对 (Unimplemented) ConvertPirAttribute2RuntimeAttribute 报错：
    使用 !!float 显式强转 mean/std，防止 PIR 引擎将其误判为 DoubleAttribute。
    """
    if not model_dir or not os.path.isdir(model_dir):
        return
    
    yml_p = os.path.join(model_dir, "inference.yml")
    deploy_p = os.path.join(model_dir, "deploy.yml")
    
    print(f"[OCR] 正在执行 V14.0 类型强转适配 ({model_type})...")
    for p in [yml_p, deploy_p]:
        if os.path.exists(p):
            try: os.remove(p)
            except: pass

    # === V14.0 绝秘模板：使用 !!float 封锁 DoubleAttribute 转换错误 ===
    # 注意：Det/Rec 依然使用列表，Cls 使用字典。统一增加 !!float 显式声明。
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
    - DetResize:
        limit_side_len: 960
        limit_type: max
    - Normalize:
        mean: [!!float 0.485, !!float 0.456, !!float 0.406]
        std: [!!float 0.229, !!float 0.224, !!float 0.225]
        order: hwc
    - ToCHWImage: null
    - KeepKeys:
        keep_keys: [image, shape]
PostProcess:
  thresh: !!float 0.3
  box_thresh: !!float 0.6
  max_candidates: 1000
  unclip_ratio: !!float 1.5
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
    - RecResize:
        target_size: [3, 48, 320]
    - Normalize:
        mean: [!!float 0.5, !!float 0.5, !!float 0.5]
        std: [!!float 0.5, !!float 0.5, !!float 0.5]
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
    ResizeImage:
      size: [192, 48]
    NormalizeImage:
      mean: [!!float 0.5, !!float 0.5, !!float 0.5]
      std: [!!float 0.5, !!float 0.5, !!float 0.5]
    ToCHWImage: null
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
            print(f"[OCR] V14.0 元数据同步成功 (!!float 模式)")
        except Exception as e:
            print(f"[OCR] V14.0 写入失败: {e}")


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
            paddle.device.set_device('cpu')
            # 再次确认关闭
            paddle.set_flags({"FLAGS_use_mkldnn": 0, "FLAGS_enable_pir_api": 0})
        except: pass
        from paddleocr import PaddleOCR

        # 基准路径探测
        script_p = os.path.abspath(__file__)
        base_d = os.path.dirname(os.path.dirname(os.path.dirname(script_p)))
        if not os.path.exists(os.path.join(base_d, "offline_models")):
            base_d = os.getcwd()
        off_d = os.path.join(base_d, "whl")

        det_p = _find_model_sub_dir(off_d, "det")
        rec_p = _find_model_sub_dir(off_d, "rec")
        cls_p = _find_model_sub_dir(off_d, "cls")

        if det_p: _ensure_inference_yml(det_p, "det")
        if rec_p: _ensure_inference_yml(rec_p, "rec")
        if cls_p: _ensure_inference_yml(cls_p, "cls")

        # === V14.0 保命级分级初始化 ===
        try:
            # 尝试全功能初始化 (Det + Rec + Cls)
            base_kw = {}
            if det_p: base_kw["text_detection_model_dir"] = det_p
            if rec_p: base_kw["text_recognition_model_dir"] = rec_p
            if cls_p:
                base_kw["textline_orientation_model_dir"] = cls_p
                base_kw["use_textline_orientation"] = True
            
            print(f"[OCR] 正在由于 V14.0 全功能初始化模式...")
            _ocr_instance = PaddleOCR(**base_kw)
        except Exception as e:
            print(f"[OCR] 全功能初始化失败，推测分类器 (Cls) 仍存在 PIR 兼容性问题。")
            print(f"[OCR] 正在执行等级降级：禁用方向检测，仅保留检测与识别...")
            try:
                # 降级：彻底砍掉 cls，防止它触发 NormalizeImage 报错
                fallback_kw = {}
                if det_p: fallback_kw["text_detection_model_dir"] = det_p
                if rec_p: fallback_kw["text_recognition_model_dir"] = rec_p
                fallback_kw["use_textline_orientation"] = False
                
                _ocr_instance = PaddleOCR(**fallback_kw)
                print(f"[OCR] 降级初始化成功。')")
            except Exception as e2:
                print(f"[OCR] 降级亦失败。详情:")
                traceback.print_exc()

    return _ocr_instance


def extract_id_info(image_path: str) -> dict:
    ocr = _get_ocr()
    try:
        r = ocr.ocr(image_path)
    except Exception as e:
        print(f"[OCR] 推理引擎底层异常: {e}")
        r = None

    if not r or not r[0]:
        return {"name": "", "id_number": "", "id_type": "unknown", "all_text": [], "confidence": 0.0}

    # 数据解析
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

    # 正则 (UTF-8)
    if any(k in full_t for k in ["姓名", "性别", "身份号码", "身份证"]):
        id_type = "id_card"
        for i, t in enumerate(all_t):
            if "姓名" in t:
                name = t.replace("姓名", "").strip() or (all_t[i+1] if i+1 < len(all_t) else "")
                break
        for t in all_t:
            m = re.search(r'\d{17}[\dXx]', t)
            if m: id_n = m.group(); break

    avg_conf = sum(x["confidence"] for x in texts) / len(texts) if texts else 0
    return {
        "name": name.strip(), "id_number": id_n.strip(), "id_type": id_type,
        "all_text": all_t, "confidence": round(avg_conf, 3)
    }


if __name__ == "__main__":
    import json
    img = sys.argv[1] if len(sys.argv) > 1 else "test_data/case_001_pass/id_document.jpg"
    print(f"\n--- PaddleOCR 3.4.0+ V14.0 (!!float 强转避雷版) ---\n测试图片: {img}\n")
    if not os.path.exists(img): print(f"找不到测试图片")
    else:
        try:
            res = extract_id_info(img)
            print(json.dumps(res, indent=4, ensure_ascii=False))
        except: traceback.print_exc()
