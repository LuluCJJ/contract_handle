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
from backend.models.schemas import AuditReport, ExtractedData, Severity, CheckResult, PersonInfo
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


def _run_pipeline(task_id: str, eflow_path: str, doc_path: str, img_paths: list[str]) -> dict:
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

    # === Step 3: OCR 证件 (多图循环) ===
    ocr_data = ExtractedData(source="ocr")
    all_ocr_raw = []
    
    for i, img_p in enumerate(img_paths):
        print(f"[Audit] Processing OCR for image {i+1}/{len(img_paths)}: {img_p}")
        ocr_result = ocr_service.extract_id_info(img_p)
        all_ocr_raw.append(ocr_result)
        
        person = PersonInfo(
            name=ocr_result.get("name", ""),
            id_number=ocr_result.get("id_number", ""),
            id_type=ocr_result.get("id_type", ""),
            expiry_date=ocr_result.get("expiry_date", "")
        )
        if person.name or person.id_number:
            ocr_data.operators.append(person)
            
    _save_intermediate(out_dir, "step3_ocr_result", {
        "raw_ocr_list": all_ocr_raw,
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
            source_a_label=item.get("source_a_label", ""),
            source_a_value=item.get("source_a_value", ""),
            source_b_label=item.get("source_b_label", ""),
            source_b_value=item.get("source_b_value", ""),
            source_c_label=item.get("source_c_label", ""),
            source_c_value=item.get("source_c_value", ""),
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
        "img_paths": img_paths,
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
    id_documents: list[UploadFile] = File(..., description="证件图片列表 (支持多选上传)"),
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

        img_paths = []
        for i, img_f in enumerate(id_documents):
            img_ext = Path(img_f.filename or "id.jpg").suffix
            path = _save_upload(img_f, task_dir, f"id_document_{i}{img_ext}")
            img_paths.append(path)

        return _run_pipeline(task_id, eflow_path, doc_path, img_paths)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-from-testcase")
async def run_from_testcase(case_id: str = Form(...)):
    """
    使用预置的测试用例运行审核。
    从 test_data/{case_id}/ 目录读取文件。支持多证件识别。
    """
    test_dir = Path(__file__).parent.parent.parent / "test_data" / case_id
    if not test_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"测试用例不存在: {case_id}")

    eflow_path = test_dir / "eflow.json"
    doc_path = None
    img_paths = []

    for f in test_dir.iterdir():
        if f.suffix in (".doc", ".docx", ".pdf") and f.stem != "eflow":
            doc_path = f
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".pdf") and "bank_app" not in f.name:
            # 排除掉作为申请表的 pdf，剩下的 pdf/图片视为证件
            if f.suffix.lower() == ".pdf" and doc_path and f == doc_path:
                continue
            img_paths.append(str(f))

    if not eflow_path.exists():
        raise HTTPException(status_code=404, detail="缺少 eflow.json")
    if not doc_path:
        raise HTTPException(status_code=404, detail="缺少银行申请文档 (.doc/.docx/.pdf)")
    if not img_paths:
        raise HTTPException(status_code=404, detail="缺少证件图片/PDF")

    return _run_pipeline(case_id, str(eflow_path), str(doc_path), img_paths)


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
    raw_ops = raw.get("operator") or raw.get("operators") or []
    if isinstance(raw_ops, dict): raw_ops = [raw_ops]
    elif not isinstance(raw_ops, list): raw_ops = []
    
    # 兼容单个扁平字段情况 (如 eflow 直接定义 applicant_name)
    if not raw_ops and raw.get("applicant_name"):
        raw_ops = [{"name": raw.get("applicant_name"), "id_number": raw.get("id_number"), "id_type": raw.get("id_type")}]

    for op in raw_ops:
        if not isinstance(op, dict): continue
        data.operators.append(PersonInfo(
            name=op.get("name") or op.get("applicant_name") or "",
            id_type=op.get("id_type") or "",
            id_number=op.get("id_number") or "",
            expiry_date=op.get("expiry_date") or "",
            role=op.get("role") or "",
            phone=op.get("phone") or op.get("mobile_phone") or ""
        ))

    # --- 3.1 指派人/开户人 (Handler) ---
    raw_hds = raw.get("handler") or raw.get("handlers") or []
    if isinstance(raw_hds, dict): raw_hds = [raw_hds]
    elif not isinstance(raw_hds, list): raw_hds = []

    for hd in raw_hds:
        if not isinstance(hd, dict): continue
        data.handlers.append(PersonInfo(
            name=hd.get("name", ""),
            id_type=hd.get("id_type", ""),
            id_number=hd.get("id_number", ""),
            expiry_date=hd.get("expiry_date", ""),
            role=hd.get("role", ""),
            phone=hd.get("phone") or hd.get("mobile_phone") or ""
        ))

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
