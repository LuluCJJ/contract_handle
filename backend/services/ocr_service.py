"""
OCR 服务 — PaddleOCR 证件信息提取（离线增强模式 V15.0）
终极补丁：算子标量化 (Scalarization) + 强力执行器回退
"""
import os
import re
import sys
import traceback
from pathlib import Path

# === V15.0 终极环境变量：彻底锁死所有新特性，回退到最稳健路径 ===
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"
os.environ["FLAGS_enable_new_executor"] = "0"  # 强制使用旧版 Executor
os.environ["PADDLE_INF_PIR_API"] = "0"
os.environ["PADDLE_ONEDNN_ENABLED"] = "0"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PADDLE_PLATFORM_DEVICE"] = "cpu"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ocr_instance = None


def _ensure_inference_yml(model_dir: str, model_type: str):
    """
    补齐 PaddleX 3.0 的 V15.0 终极技。
    针对 ArrayAttribute<DoubleAttribute> 的报错：
    将 [0.5, 0.5, 0.5] 这种数组形式全部改为 单个标量 (Scalar)。
    这会迫使 PIR 使用 DoubleAttribute 路径而非 ArrayAttribute 路径，完美绕开 Bug。
    """
    if not model_dir or not os.path.isdir(model_dir):
        return
    
    yml_p = os.path.join(model_dir, "inference.yml")
    deploy_p = os.path.join(model_dir, "deploy.yml")
    
    print(f"[OCR] 正在执行 V15.0 算子标量化避雷补丁 ({model_type})...")
    for p in [yml_p, deploy_p]:
        if os.path.exists(p):
            try: os.remove(p)
            except: pass

    # === V15.0 绝密模板：单值广播模式 ===
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
        mean: 0.5
        std: 0.5
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
    - RecResize:
        target_size: [3, 48, 320]
    - Normalize:
        mean: 0.5
        std: 0.5
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
      mean: 0.5
      std: 0.5
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
            print(f"[OCR] V15.0 标量化同步成功 (mean=0.5, std=0.5)")
        except Exception as e:
            print(f"[OCR] V15.0 写入失败: {e}")


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
            # 打印当前 FLAGS 状态以便调试
            print(f"[OCR] 当前 PIR 状态: {os.environ.get('FLAGS_enable_pir_api')}")
            print(f"[OCR] 当前 oneDNN 状态: {os.environ.get('FLAGS_use_mkldnn')}")
            paddle.device.set_device('cpu')
            paddle.set_flags({"FLAGS_use_mkldnn": 0, "FLAGS_enable_pir_api": 0, "FLAGS_enable_new_executor": 0})
        except: pass
        from paddleocr import PaddleOCR

        # 基准路径探测
        script_p = os.path.abspath(__file__)
        base_d = os.path.dirname(os.path.dirname(os.path.dirname(script_p)))
        if not os.path.exists(os.path.join(base_d, "offline_models")):
            base_d = os.getcwd()
        off_d = os.path.join(base_d, "whl")

        # 强制更新目录下的 YAML
        det_p = _find_model_sub_dir(off_d, "det")
        rec_p = _find_model_sub_dir(off_d, "rec")
        cls_p = _find_model_sub_dir(off_d, "cls")

        print(f"[OCR] 本地模型路径检测: DET={det_p is not None}, REC={rec_p is not None}, CLS={cls_p is not None}")

        if det_p: _ensure_inference_yml(det_p, "det")
        if rec_p: _ensure_inference_yml(rec_p, "rec")
        if cls_p: _ensure_inference_yml(cls_p, "cls")

        # === V15.0 决战参数 ===
        # 显式传递路径，防止库去读 C:\Users 改缓存
        base_kw = {
            "use_gpu": False,
            "enable_mkldnn": False,
            "det_model_dir": det_p,
            "rec_model_dir": rec_p,
            "cls_model_dir": cls_p,
            "use_angle_cls": (cls_p is not None)
        }

        try:
            print(f"[OCR] 正在以 V15.0 标量算子模式强行启动...")
            _ocr_instance = PaddleOCR(**base_kw)
        except Exception as e:
            print(f"[OCR] V15.0 终极启动依然受阻。")
            traceback.print_exc()
            try:
                # 最后的最后：极简启动
                _ocr_instance = PaddleOCR(det_model_dir=det_p, rec_model_dir=rec_p, use_gpu=False)
            except:
                print(f"[OCR] 引擎彻底封死。")

    return _ocr_instance


def extract_id_info(image_path: str) -> dict:
    ocr = _get_ocr()
    try:
        r = ocr.ocr(image_path)
    except Exception as e:
        print(f"[OCR] 推理期崩溃 (V15.0): {e}")
        r = None

    if not r or not r[0]:
        return {"name": "", "id_number": "", "id_type": "unknown", "all_text": [], "confidence": 0.0}

    # 解析逻辑保持兼容
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
    print(f"\n--- PaddleOCR 3.4.0+ V15.0 (标量避雷版) ---\n测试图片: {img}\n")
    if not os.path.exists(img): print(f"找不到图片")
    else:
        try:
            res = extract_id_info(img)
            print(json.dumps(res, indent=4, ensure_ascii=False))
        except: traceback.print_exc()
