"""
OCR 服务 — PaddleOCR 证件信息提取（离线模式）
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
        print(f"[OCR] 路径不存在，跳过搜索: {search_path}")
        return None
    
    print(f"[OCR] 正在搜索 {type_name} 模型: {search_path} ...")
    for root, dirs, files in os.walk(search_path):
        if "inference.pdmodel" in files:
            abs_path = os.path.abspath(root)
            print(f"[OCR] 成功找到 {type_name} 模型: {abs_path}")
            return abs_path
    
    print(f"[OCR] 未能在 {search_path} 下找到有效模型文件 (inference.pdmodel)")
    return None


def _get_ocr():
    """初始化并返回 PaddleOCR 实例（双重锁定 CPU 并禁用网络）"""
    global _ocr_instance
    if _ocr_instance is None:
        try:
            import paddle
            paddle.device.set_device('cpu')
        except Exception:
            pass

        from paddleocr import PaddleOCR

        # 计算搜索基准目录
        # 1. 尝试从当前脚本相对于项目根目录的路径计算
        script_path = os.path.abspath(__file__)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
        
        # 2. 如果根目录下没有，尝试使用当前工作目录
        if not os.path.exists(os.path.join(base_dir, "offline_models")):
            base_dir = os.getcwd()
            
        offline_dir = os.path.join(base_dir, "offline_models", "whl")
        print(f"[OCR] 离线模型基准目录: {offline_dir}")

        # 优先读取配置文件中的路径
        det_path = None
        rec_path = None
        cls_path = None
        
        cfg_model_dir = _find_model_dir_from_config()
        if cfg_model_dir:
            print(f"[OCR] 使用 config.json 指定的路径: {cfg_model_dir}")
            det_path = os.path.join(cfg_model_dir, "det") if os.path.exists(os.path.join(cfg_model_dir, "det")) else None
            rec_path = os.path.join(cfg_model_dir, "rec") if os.path.exists(os.path.join(cfg_model_dir, "rec")) else None
            cls_path = os.path.join(cfg_model_dir, "cls") if os.path.exists(os.path.join(cfg_model_dir, "cls")) else None

        # 如果配置中没写或不完整，则从 offline_models 自动深度搜索
        if not det_path: det_path = _find_model_sub_dir(offline_dir, "det")
        if not rec_path: rec_path = _find_model_sub_dir(offline_dir, "rec")
        if not cls_path: cls_path = _find_model_sub_dir(offline_dir, "cls")

        # 构造最终参数
        kwargs = {
            "lang": "ch",
            "use_gpu": False,
            "use_xpu": False,
            "use_npu": False,
            "use_mlu": False,
            "enable_mkldnn": False,
            "show_log": False # 尝试部分版本支持的日志开关
        }
        
        if det_path: kwargs["det_model_dir"] = det_path
        if rec_path: kwargs["rec_model_dir"] = rec_path
        if cls_path: 
            kwargs["cls_model_dir"] = cls_path
            kwargs["use_angle_cls"] = True
        else:
            kwargs["use_angle_cls"] = False

        try:
            print(f"[OCR] 开始创建 PaddleOCR 实例 (模式: {'离线' if det_path else '在线' })")
            _ocr_instance = PaddleOCR(**kwargs)
        except Exception as e:
            print(f"[OCR] 首次加载失败: {e}。正在尝试极简配置模式...")
            # 剔除所有可能引起冲突的参数，仅保留路径
            minimal_kwargs = {"lang": "ch", "use_gpu": False, "use_angle_cls": False}
            if det_path: minimal_kwargs["det_model_dir"] = det_path
            if rec_path: minimal_kwargs["rec_model_dir"] = rec_path
            try:
                _ocr_instance = PaddleOCR(**minimal_kwargs)
            except Exception as e2:
                print(f"[OCR] 极简模式依然失败: {e2}。尝试完全默认启动（可能会触发网络下载）")
                _ocr_instance = PaddleOCR()

    return _ocr_instance


def extract_id_info(image_path: str) -> dict:
    """从证件图片中提取姓名和证件号"""
    ocr = _get_ocr()
    try:
        result = ocr.ocr(image_path)
    except Exception as e:
        print(f"[OCR] 运行时异常: {e}")
        result = None

    if not result or not result[0]:
        # 回退逻辑 (省略硬编码的测试用例匹配，保持生产代码简洁)
        return {"name": "", "id_number": "", "id_type": "unknown", "all_text": [], "confidence": 0.0}

    # 解析文本
    texts = []
    if isinstance(result[0], list):
        for line in result[0]:
            try:
                text = line[1][0]
                conf = line[1][1]
                texts.append({"text": text, "confidence": conf})
            except Exception: pass

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

    # 兜底通用提取
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


# ========== 提取逻辑辅助函数 ==========

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
    return any(k in full.upper() for k in ["PASSPORT", "P<", "DOCUMENT NO"])

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
    return any(k in full.upper() for k in ["DRIVER", "LICENSE", "CLASS"])

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
    print(f"\n--- OCR 独立调试 (UTF-8) ---\n测试图片: {test_img}\n")
    if not os.path.exists(test_img):
        print(f"找不到图片: {test_img}")
    else:
        try:
            res = extract_id_info(test_img)
            print(json.dumps(res, indent=4, ensure_ascii=False))
        except Exception as e:
            print(f"执行失败: {e}")
