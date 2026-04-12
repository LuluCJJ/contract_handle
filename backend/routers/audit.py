"""
审核流程 API — V2.0 with PDF support & Intermediate Result Saving
"""
import os
import uuid
import json
import shutil
import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.models.schemas import AuditReport, ExtractedData, Severity, CheckResult
from backend.services import doc_parser, ocr_service, extractor, comparator, reporter

router = APIRouter(prefix="/api/audit", tags=["audit"])

# 上传文件临时存储
UPLOAD_BASE = Path(__file__).parent.parent.parent / "uploads"
# 中间结果保存目录
OUTPUTS_BASE = Path(__file__).parent.parent.parent / "outputs"


def _save_upload(file: UploadFile, task_dir: Path, filename: str) -> str:
    """保存上传文件到任务目录"""
    dest = task_dir / filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(dest)


def _save_intermediate(output_dir: Path, step_name: str, data, is_text=False):
    """保存中间步骤的结果到 outputs 目录，方便 debug 和逐步复盘"""
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{step_name}.json"
    try:
        if is_text:
            filepath = output_dir / f"{step_name}.txt"
            filepath.write_text(str(data), encoding="utf-8")
        elif isinstance(data, str):
            filepath.write_text(data, encoding="utf-8")
        else:
            filepath.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8"
            )
        print(f"[Audit] Saved intermediate: {filepath}")
    except Exception as e:
        print(f"[Audit] Warning: Failed to save intermediate {step_name}: {e}")


def _run_pipeline(task_id: str, eflow_path: str, doc_path: str, img_path: str) -> dict:
    """
    核心审核管线（共享逻辑），每步结果保存到 outputs/{task_id}/
    """
    # 中间结果存储目录
    out_dir = OUTPUTS_BASE / task_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # === Step 1: 解析 E-Flow ===
    with open(eflow_path, "r", encoding="utf-8") as f:
        eflow_raw = json.load(f)
    eflow_data = _parse_eflow(eflow_raw)
    _save_intermediate(out_dir, "step1_eflow_parsed", eflow_data.model_dump())

    # === Step 2: 解析银行文档（支持 .doc/.docx/.pdf） ===
    parsed_doc = doc_parser.parse_document(doc_path)
    doc_full_text = doc_parser.get_full_text_for_llm(parsed_doc)
    _save_intermediate(out_dir, "step2a_doc_structure", {
        "num_paragraphs": parsed_doc["num_paragraphs"],
        "num_tables": parsed_doc["num_tables"],
        "paragraphs": parsed_doc["paragraphs"][:20],  # 保存前20个段落
        "tables_raw_sample": [t[:3] for t in parsed_doc["tables_raw"]],  # 每表前3行
    })
    _save_intermediate(out_dir, "step2b_doc_full_text_for_llm", doc_full_text, is_text=True)

    # === Step 3: OCR 证件 ===
    ocr_result = ocr_service.extract_id_info(img_path)
    ocr_data = ExtractedData(source="ocr")
    ocr_data.operator.name = ocr_result.get("name", "")
    ocr_data.operator.id_number = ocr_result.get("id_number", "")
    ocr_data.operator.id_type = ocr_result.get("id_type", "")
    ocr_data.operator.expiry_date = ocr_result.get("expiry_date", "")
    _save_intermediate(out_dir, "step3_ocr_result", {
        "raw_ocr": ocr_result,
        "structured": ocr_data.model_dump()
    })

    # === Step 4: 信息提取 (LLM for 文档) ===
    word_dict = extractor.extract_information(doc_full_text)
    _save_intermediate(out_dir, "step4_llm_extraction", word_dict)
    
    if isinstance(word_dict, dict) and word_dict:
        word_data = _parse_eflow(word_dict)
        word_data.source = "word"
    else:
        word_data = ExtractedData(source="word")

    # === Step 5: 交叉比对 ===
    combined_data = {
        "eflow": eflow_data.model_dump(),
        "word": word_dict,
        "ocr": ocr_data.model_dump()
    }
    rules = "规则：对比各渠道中的公司名称、法人及证件是否一致。"
    comp_dict = comparator.run_comparisons(combined_data, rules)
    _save_intermediate(out_dir, "step5_comparison_result", comp_dict)

    checks = []
    for item in comp_dict.get("items", []):
        field = item.get("field", "综合比对")
        status = item.get("status", "PASS")
        msg = item.get("message", "")

        sev = Severity.PASS
        if status in ["FAIL", "CRITICAL"]: sev = Severity.CRITICAL
        elif status == "WARNING": sev = Severity.WARNING
        elif status == "INFO": sev = Severity.INFO

        checks.append(CheckResult(
            check_name=f"{field}比对",
            field_name=field,
            result="MATCH" if sev == Severity.PASS else "MISMATCH",
            severity=sev,
            detail=msg
        ))

    # === Step 6: 生成报告 ===
    report = reporter.generate_report(eflow_data, word_data, ocr_data, checks)
    _save_intermediate(out_dir, "step6_final_report", report.model_dump())

    # 保存运行元数据
    _save_intermediate(out_dir, "_metadata", {
        "task_id": task_id,
        "run_time": datetime.datetime.now().isoformat(),
        "doc_path": doc_path,
        "eflow_path": eflow_path,
        "img_path": img_path,
    })

    return {
        "task_id": task_id,
        "status": "completed",
        "report": report.model_dump(),
        "intermediate_dir": str(out_dir),
    }


@router.post("/run")
async def run_audit(
    eflow_json: UploadFile = File(..., description="E-Flow JSON 文件"),
    bank_doc: UploadFile = File(..., description="银行申请表 (.doc/.docx/.pdf)"),
    id_document: UploadFile = File(..., description="证件图片 (.jpg/.png)"),
):
    """
    执行完整的预审流程
    """
    task_id = str(uuid.uuid4())[:8]
    task_dir = UPLOAD_BASE / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    try:
        eflow_path = _save_upload(eflow_json, task_dir, "eflow.json")

        doc_ext = Path(bank_doc.filename or "doc.docx").suffix
        doc_path = _save_upload(bank_doc, task_dir, f"bank_app{doc_ext}")

        img_ext = Path(id_document.filename or "id.jpg").suffix
        img_path = _save_upload(id_document, task_dir, f"id_document{img_ext}")

        return _run_pipeline(task_id, eflow_path, doc_path, img_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-from-testcase")
async def run_from_testcase(case_id: str = Form(...)):
    """
    使用预置的测试用例运行审核。
    从 test_data/{case_id}/ 目录读取文件。
    """
    test_dir = Path(__file__).parent.parent.parent / "test_data" / case_id
    if not test_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"测试用例不存在: {case_id}")

    eflow_path = test_dir / "eflow.json"
    doc_path = None
    img_path = None

    for f in test_dir.iterdir():
        if f.suffix in (".doc", ".docx", ".pdf") and f.stem != "eflow":
            doc_path = f
        if f.suffix in (".jpg", ".jpeg", ".png"):
            img_path = f

    if not eflow_path.exists():
        raise HTTPException(status_code=404, detail="缺少 eflow.json")
    if not doc_path:
        raise HTTPException(status_code=404, detail="缺少银行申请文档 (.doc/.docx/.pdf)")
    if not img_path:
        raise HTTPException(status_code=404, detail="缺少证件图片")

    return _run_pipeline(case_id, str(eflow_path), str(doc_path), str(img_path))


@router.get("/testcases")
def list_testcases():
    """列出所有可用的测试用例"""
    test_dir = Path(__file__).parent.parent.parent / "test_data"
    cases = []
    if test_dir.is_dir():
        for d in sorted(test_dir.iterdir()):
            if d.is_dir():
                readme = d / "README.md"
                desc = ""
                if readme.exists():
                    desc = readme.read_text(encoding="utf-8").strip()
                cases.append({
                    "case_id": d.name,
                    "description": desc,
                    "files": [f.name for f in d.iterdir() if f.is_file()],
                })
    return {"cases": cases}


def _format_activity(raw_activity) -> str:
    """
    将复杂的业务勾选 JSON 转换为人类可读的优雅描述文字。
    处理 application_type, services, selected 等嵌套结构。
    """
    if not raw_activity: return "未录入业务"
    if isinstance(raw_activity, str): return raw_activity
    if not isinstance(raw_activity, dict): return str(raw_activity)

    parts = []
    
    # 1. 尝试提取应用类型
    app_type = raw_activity.get("application_type") or raw_activity.get("type")
    if app_type:
        parts.append(f"申请业务：{app_type}")
    
    # 2. 尝试提取勾选的功能列表
    # 适配结构: {"services": {"web": {"selected": [...]}}}
    services = raw_activity.get("services", {})
    web_selected = []
    if isinstance(services, dict):
        web_selected = services.get("web", {}).get("selected", [])
    
    # 也可以适配扁平结构 {"permissions": {"web_channel": [...]}}
    if not web_selected:
        web_selected = raw_activity.get("permissions", {}).get("web_channel", [])

    if web_selected and isinstance(web_selected, list):
        parts.append(f"功能清单：{', '.join(web_selected)}")

    # 3. 适配 LLM 直接提取的表格多行选项 (new_account, modification, deletion)
    if not parts:
        for k, v in raw_activity.items():
            if isinstance(v, list) and v:
                parts.append(f"{k}: {', '.join(v)}")
            elif isinstance(v, str) and v:
                parts.append(f"{k}: {v}")

    # 最后的回退机制：把所有信息转化为文本
    if not parts:
        try:
            import json
            return json.dumps(raw_activity, ensure_ascii=False)
        except:
            return str(raw_activity)

    return " | ".join(parts)


def _parse_eflow(raw: dict) -> ExtractedData:
    """
    将原始字典（可能是 E-Flow 或 LLM 提取结果）转为统一的 ExtractedData。
    具有极强的鲁棒性，支持多种命名变体和嵌套深度。
    """
    # 强制将原始 JSON 存入 raw_text 以便底层回溯
    data = ExtractedData(source="unknown")
    if not isinstance(raw, dict):
        data.raw_text = str(raw)
        return data

    # --- 1. 公司信息 (Company) ---
    co = raw.get("company") or {}
    # 如果 co 只是字符串，则直接设为名字
    if isinstance(co, str):
        data.company.name = co
    elif isinstance(co, dict):
        data.company.name = co.get("name") or co.get("name_cn") or raw.get("company_name", "")
        data.company.name_en = co.get("name_en", "")
        data.company.cert_type = co.get("cert_type") or co.get("id_type", "")
        data.company.cert_number = co.get("cert_number") or co.get("id_number") or raw.get("cert_number", "")
        data.company.legal_representative = co.get("legal_representative") or co.get("legal_person") or ""
        data.company.phone = co.get("phone") or co.get("telephone", "")
        data.company.industry = co.get("industry") or co.get("market_segment", "")

    # --- 2. 账号信息 (Account) ---
    # 大模型通常返回列表，E-Flow 通常返回单个字典
    accs = raw.get("account") or raw.get("accounts") or []
    if isinstance(accs, list) and len(accs) > 0:
        first_acc = accs[0]
    else:
        first_acc = accs if isinstance(accs, dict) else {}

    data.account.bank_name = first_acc.get("bank_name", "")
    data.account.branch = first_acc.get("branch", "")
    data.account.account_number = first_acc.get("account_number") or first_acc.get("number") or raw.get("account_number", "")

    # --- 3. 经办人/操作员 (Operator) ---
    # 逻辑同账号：支持列表降维
    ops = raw.get("operator") or raw.get("operators") or {}
    if isinstance(ops, list) and len(ops) > 0:
        first_op = ops[0]
    else:
        first_op = ops if isinstance(ops, dict) else {}

    data.operator.name = first_op.get("name") or raw.get("applicant_name", "")
    data.operator.id_type = first_op.get("id_type") or raw.get("id_type", "")
    data.operator.id_number = first_op.get("id_number") or raw.get("id_number", "")
    data.operator.expiry_date = first_op.get("expiry_date", "")
    data.operator.role = first_op.get("role", "")
    data.operator.phone = first_op.get("phone") or first_op.get("mobile_phone", "")

    # --- 3.1 指派人/开户人 (Handler) ---
    hds = raw.get("handler") or raw.get("handlers") or {}
    if isinstance(hds, list) and len(hds) > 0:
        first_hd = hds[0]
    else:
        first_hd = hds if isinstance(hds, dict) else {}

    data.handler.name = first_hd.get("name", "")
    data.handler.id_type = first_hd.get("id_type", "")
    data.handler.id_number = first_hd.get("id_number", "")
    data.handler.expiry_date = first_hd.get("expiry_date", "")
    data.handler.role = first_hd.get("role", "")
    data.handler.phone = first_hd.get("phone") or first_hd.get("mobile_phone", "")

    # --- 4. 权限与限额 (Permissions) ---
    def _parse_limit(val):
        if not val: return 0
        if isinstance(val, (int, float)): return float(val)
        try:
            return float(str(val).replace(",", "").replace("，", ""))
        except:
            return 0

    perms = raw.get("permissions") or {}
    if isinstance(perms, dict):
        data.permissions.level = perms.get("level") or perms.get("authorization_level", "")
        data.permissions.single_limit = _parse_limit(perms.get("single_limit") or 0)
        data.permissions.daily_limit = _parse_limit(perms.get("daily_limit") or 0)
    
    # 尝试从账号信息中补全限额（针对某些大模型把限额放在账号里的情况）
    if not data.permissions.single_limit and first_acc:
        data.permissions.single_limit = _parse_limit(first_acc.get("single_limit") or 0)
        data.permissions.daily_limit = _parse_limit(first_acc.get("daily_accumulated_limit") or 0)

    # --- 5. 业务活动 (Activity) ---
    data.activity = _format_activity(raw.get("activity") or raw.get("permissions", {}))
    
    data.raw_text = json.dumps(raw, ensure_ascii=False)
    return data
