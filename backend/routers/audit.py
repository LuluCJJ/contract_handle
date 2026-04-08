"""
审核流程 API — Phase 1 骨架
"""
import os
import uuid
import json
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.models.schemas import AuditReport, ExtractedData
from backend.services import doc_parser, ocr_service, extractor, comparator, reporter

router = APIRouter(prefix="/api/audit", tags=["audit"])

# 上传文件临时存储
UPLOAD_BASE = Path(__file__).parent.parent.parent / "uploads"


def _save_upload(file: UploadFile, task_dir: Path, filename: str) -> str:
    """保存上传文件到任务目录"""
    dest = task_dir / filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(dest)


@router.post("/run")
async def run_audit(
    eflow_json: UploadFile = File(..., description="E-Flow JSON 文件"),
    bank_doc: UploadFile = File(..., description="银行申请表 (.doc/.docx)"),
    id_document: UploadFile = File(..., description="证件图片 (.jpg/.png)"),
):
    """
    执行完整的预审流程：
    1. 解析 E-Flow JSON
    2. 解析银行申请表
    3. OCR 证件图片
    4. 信息提取（LLM）
    5. 交叉比对
    6. 生成报告
    """
    # 创建任务目录
    task_id = str(uuid.uuid4())[:8]
    task_dir = UPLOAD_BASE / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    try:
        # === Step 1: 保存上传文件 ===
        eflow_path = _save_upload(eflow_json, task_dir, "eflow.json")
        
        doc_ext = Path(bank_doc.filename or "doc.docx").suffix
        doc_path = _save_upload(bank_doc, task_dir, f"bank_app{doc_ext}")
        
        img_ext = Path(id_document.filename or "id.jpg").suffix
        img_path = _save_upload(id_document, task_dir, f"id_document{img_ext}")

        # === Step 2: 解析 E-Flow ===
        with open(eflow_path, "r", encoding="utf-8") as f:
            eflow_raw = json.load(f)

        eflow_data = _parse_eflow(eflow_raw)

        # === Step 3: 解析银行文档 ===
        parsed_doc = doc_parser.parse_document(doc_path)
        doc_full_text = doc_parser.get_full_text_for_llm(parsed_doc)

        # === Step 4: OCR 证件 ===
        ocr_result = ocr_service.extract_id_info(img_path)
        ocr_data = ExtractedData(
            source="ocr",
        )
        ocr_data.operator.name = ocr_result.get("name", "")
        ocr_data.operator.id_number = ocr_result.get("id_number", "")
        ocr_data.operator.id_type = ocr_result.get("id_type", "")

        # === Step 5: 信息提取 (LLM for Word) ===
        word_dict = extractor.extract_information(doc_full_text)
        if isinstance(word_dict, dict) and word_dict:
            word_data = _parse_eflow(word_dict)
            word_data.source = "word"
        else:
            word_data = ExtractedData(source="word")

        # === Step 6: 交叉比对 ===
        combined_data = {
            "eflow": eflow_data.model_dump(),
            "word": word_dict,
            "ocr": ocr_data.model_dump()
        }
        rules = "规则：对比各渠道中的公司名称、法人及证件是否一致。"
        comp_dict = comparator.run_comparisons(combined_data, rules)
        
        checks = []
        for item in comp_dict.get("items", []):
            field = item.get("field", "综合比对")
            status = item.get("status", "PASS")
            msg = item.get("message", "")
            
            from backend.models.schemas import Severity, CheckResult
            sev = Severity.PASS
            if status in ["FAIL", "CRITICAL"]: sev = Severity.CRITICAL
            elif status == "WARNING": sev = Severity.WARNING
            
            checks.append(CheckResult(
                check_name=f"{field}比对",
                field_name=field,
                result="MATCH" if sev == Severity.PASS else "MISMATCH",
                severity=sev,
                detail=msg
            ))

        # === Step 7: 生成报告 ===
        report = reporter.generate_report(eflow_data, word_data, ocr_data, checks)

        return {
            "task_id": task_id,
            "status": "completed",
            "report": report.model_dump()
        }

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
        if f.suffix in (".doc", ".docx") and f.stem != "eflow":
            doc_path = f
        if f.suffix in (".jpg", ".jpeg", ".png"):
            img_path = f

    if not eflow_path.exists():
        raise HTTPException(status_code=404, detail="缺少 eflow.json")
    if not doc_path:
        raise HTTPException(status_code=404, detail="缺少银行申请文档")
    if not img_path:
        raise HTTPException(status_code=404, detail="缺少证件图片")

    # 解析
    with open(eflow_path, "r", encoding="utf-8") as f:
        eflow_raw = json.load(f)
    eflow_data = _parse_eflow(eflow_raw)

    parsed_doc = doc_parser.parse_document(str(doc_path))
    doc_full_text = doc_parser.get_full_text_for_llm(parsed_doc)

    ocr_result = ocr_service.extract_id_info(str(img_path))

    # 提取 & 比对
    word_dict = extractor.extract_information(doc_full_text)
    if isinstance(word_dict, dict) and word_dict:
        word_data = _parse_eflow(word_dict)
        word_data.source = "word"
    else:
        word_data = ExtractedData(source="word")
    
    ocr_data = ExtractedData(source="ocr")
    ocr_data.operator.name = ocr_result.get("name", "")
    ocr_data.operator.id_number = ocr_result.get("id_number", "")
    ocr_data.operator.id_type = ocr_result.get("id_type", "")

    combined_data = {
        "eflow": eflow_data.model_dump(),
        "word": word_dict,
        "ocr": ocr_data.model_dump()
    }
    rules = "规则：对比各渠道中的公司名称、法人及证件是否一致。"
    comp_dict = comparator.run_comparisons(combined_data, rules)
    
    checks = []
    for item in comp_dict.get("items", []):
        field = item.get("field", "综合比对")
        status = item.get("status", "PASS")
        msg = item.get("message", "")
        
        from backend.models.schemas import Severity, CheckResult
        sev = Severity.PASS
        if status in ["FAIL", "CRITICAL"]: sev = Severity.CRITICAL
        elif status == "WARNING": sev = Severity.WARNING
        
        checks.append(CheckResult(
            check_name=f"{field}比对",
            field_name=field,
            result="MATCH" if sev == Severity.PASS else "MISMATCH",
            severity=sev,
            detail=msg
        ))

    report = reporter.generate_report(eflow_data, word_data, ocr_data, checks)

    return {
        "task_id": case_id,
        "status": "completed",
        "report": report.model_dump()
    }


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


def _parse_eflow(raw: dict) -> ExtractedData:
    """将 E-Flow JSON 转为统一的 ExtractedData，增加对 LLM 非标返回（如字符串代替字典）的兼容性"""
    data = ExtractedData(source="eflow")
    if not isinstance(raw, dict):
        data.raw_text = str(raw)
        return data

    # 1. 公司信息 (Company)
    company = raw.get("company")
    if isinstance(company, str):
        data.company.name = company
    elif isinstance(company, dict):
        data.company.name = company.get("name") or company.get("name_cn", "")
        data.company.name_en = company.get("name_en", "")
        data.company.cert_type = company.get("cert_type", "")
        data.company.cert_number = company.get("cert_number", "")
    else:
        # 兼容旧版/扁平格式
        data.company.name = raw.get("company_name", "")

    # 2. 账号信息 (Account)
    account = raw.get("account")
    if isinstance(account, str):
        data.account.account_number = account
    elif isinstance(account, dict):
        data.account.bank_name = account.get("bank_name", "")
        data.account.branch = account.get("branch", "")
        data.account.account_number = account.get("account_number", "")

    # 3. 经办人/申请人 (Operator)
    operator = raw.get("operator")
    if isinstance(operator, str):
        data.operator.name = operator
    elif isinstance(operator, dict):
        data.operator.name = operator.get("name", "")
        data.operator.id_type = operator.get("id_type", "")
        data.operator.id_number = operator.get("id_number", "")
    else:
        # 兼容旧版/扁平格式
        data.operator.name = raw.get("applicant_name", "")
        data.operator.id_type = raw.get("id_type", "")
        data.operator.id_number = raw.get("id_number", "")

    # 4. 指派人 (Handler)
    handler = raw.get("handler")
    if isinstance(handler, str):
        data.handler.name = handler
    elif isinstance(handler, dict):
        data.handler.name = handler.get("name", "")
        data.handler.id_type = handler.get("id_type", "")
        data.handler.id_number = handler.get("id_number", "")

    # 5. 权限信息 (Permissions)
    perms = raw.get("permissions")
    if isinstance(perms, str):
        data.permissions.level = perms
    elif isinstance(perms, dict):
        data.permissions.level = perms.get("level", "")
        data.permissions.single_limit = perms.get("single_limit", 0)
        data.permissions.daily_limit = perms.get("daily_limit", 0)

    data.activity = str(raw.get("activity", ""))
    data.raw_text = json.dumps(raw, ensure_ascii=False)

    return data
