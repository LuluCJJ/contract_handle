"""
审核流程 API — V3.0 The Multi-doc Iterative Pipeline
"""
import os
import uuid
import json
import shutil
import traceback
from datetime import datetime, date
from pathlib import Path
from typing import List, Annotated, Optional
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.encoders import jsonable_encoder

from backend.models.schemas import (
    AuditReport, Severity, CheckResult, PersonInfo, EFlowData, 
    DocExtractedData, DocAnalysisReport, UserPermission, PermissionScope, 
    MediaInfo, CompanyInfo, PlatformInfo, OverallStatus
)
from backend.services import doc_parser, ocr_service, extractor, comparator, reporter, hard_comparator

router = APIRouter(prefix="/api/audit", tags=["audit"])

UPLOAD_BASE = Path(__file__).parent.parent.parent / "uploads"
OUTPUTS_BASE = Path(__file__).parent.parent.parent / "outputs"

def _save_upload(file: UploadFile, task_dir: Path, filename: str) -> str:
    dest = task_dir / filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(dest)

def _save_intermediate(output_dir: Path, step_name: str, data, is_text=False):
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

def _parse_eflow_v3(raw: dict) -> EFlowData:
    """强制转换为 V3 版本的 EFlow 数据标准"""
    try:
        edata = EFlowData(**raw)
        edata.raw_text = json.dumps(raw, ensure_ascii=False)
        return edata
    except Exception as e:
        print(f"[Audit] V3 EFlow Parse fallback due to: {e}")
        # 兼容老版，尽力构建
        edata = EFlowData(raw_text=json.dumps(raw, ensure_ascii=False))
        edata.business_type = raw.get("activity", "")
        # ... 可以加更多 fallback，这里假设测试环境用新数据
        return edata

def _run_pipeline(task_id: str, eflow_path: str, docs_paths: list[str], img_paths: list[str]) -> dict:
    """
    核心审核管线 V3 - 支持动态数量文本与图片附件
    """
    import time
    timing = {}
    t_start = time.time()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUTS_BASE / f"{timestamp}_{task_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # === 1. 构建金标准 (E-Flow) ===
    t0 = time.time()
    with open(eflow_path, "r", encoding="utf-8") as f:
        eflow_raw = json.load(f)
    eflow = _parse_eflow_v3(eflow_raw)
    _save_intermediate(out_dir, "m1_eflow", eflow.model_dump())
    timing["M1_eflow_parse_ms"] = round((time.time() - t0) * 1000)

    document_reports = []

    # === 2. 逐件处理文档 (Word/PDF) ===
    timing["M2_docs"] = []
    for dp in docs_paths:
        fname = Path(dp).name
        t0 = time.time()
        parsed_doc = doc_parser.parse_document(dp)
        doc_full_text = doc_parser.get_full_text_for_llm(parsed_doc)
        t_parse = time.time()

        # 2.1 泛化抽取
        extracted = extractor.extract_information(doc_full_text, filename=fname, doc_type="word")
        t_extract = time.time()

        # 2.2 硬比对
        h_checks = hard_comparator.run_hard_comparisons(eflow, extracted)

        # 2.3 语义分析
        s_checks = comparator.run_semantic_analyzer(eflow, extracted)
        t_semantic = time.time()

        dr = DocAnalysisReport(
            doc_name=fname,
            doc_type="word",
            extracted_data=extracted,
            hard_checks=h_checks,
            semantic_checks=s_checks
        )
        document_reports.append(dr)
        _save_intermediate(out_dir, f"m2_doc_{fname}", dr.model_dump())
        timing["M2_docs"].append({
            "file": fname,
            "parse_ms":    round((t_parse   - t0)       * 1000),
            "extract_ms":  round((t_extract - t_parse)  * 1000),
            "semantic_ms": round((t_semantic - t_extract) * 1000),
            "total_ms":    round((t_semantic - t0)       * 1000),
        })


    # === 3. 逐件处理证件 (OCR - 稳健串行模式) ===
    timing["M3_ocr"] = []
    for ip in img_paths:
        fname = Path(ip).name
        t0 = time.time()
        ocr_result = ocr_service.extract_id_info(ip)
        t_ocr = time.time()
        timing["M3_ocr"].append({"file": fname, "ocr_ms": round((t_ocr - t0) * 1000)})
        
        person = PersonInfo(
            name=ocr_result.get("name", ""),
            id_number=ocr_result.get("id_number", ""),
            expiry_date=ocr_result.get("expiry_date", "")
        )
        extracted = DocExtractedData(
            source_file=fname,
            source_type="ocr",
            persons=[person] if person.name or person.id_number else []
        )
        extracted.raw_text = json.dumps(ocr_result, ensure_ascii=False)
        
        h_checks = hard_comparator.run_hard_comparisons(eflow, extracted)
        
        # 恢复：证件过期自动核查
        from datetime import date as dt_date
        curr = dt_date.today().strftime("%Y-%m-%d")
        if person.expiry_date and person.expiry_date <= curr:
            h_checks.append(CheckResult(
                check_name="证件有效期核查", category="身份一致性", field_group="subject", field_name="expiry_date",
                scenario_type=extracted.scenario_type, check_mode="reverse_review",
                source_a_label="系统当前日期", source_a_value=curr,
                source_b_label="证件票面", source_b_value=person.expiry_date,
                result="MISMATCH", severity=Severity.CRITICAL, reason_code="ID_EXPIRED", detail="实名证件已过期失效"
            ))
        
        dr = DocAnalysisReport(
            doc_name=fname,
            doc_type="ocr",
            extracted_data=extracted,
            hard_checks=h_checks,
            semantic_checks=[]
        )
        document_reports.append(dr)
        _save_intermediate(out_dir, f"m3_ocr_{dr.doc_name}", dr.model_dump())

    # === 4. 交叉检验 (Cross Validation) ===
    cross_validator_checks = []

    # === 5. 全局智脑 (Global Aggregator) ===
    t0 = time.time()
    all_reps_dump = [dr.model_dump() for dr in document_reports]
    global_summary = comparator.generate_global_summary(eflow, all_reps_dump, cross_validator_checks)
    timing["M5_global_summary_ms"] = round((time.time() - t0) * 1000)
    timing["M_total_ms"] = round((time.time() - t_start) * 1000)
    _save_intermediate(out_dir, "m5_llm_summary", global_summary)
    _save_intermediate(out_dir, "m0_timing", timing)
    print(f"[Timing] 总耗时 {timing['M_total_ms']}ms | EFlow={timing['M1_eflow_parse_ms']}ms | GlobalSummary={timing['M5_global_summary_ms']}ms")

    # === 6. 报告封装 (V15.6 逻辑) ===
    # 汇总计算综述
    has_critical = any(c.severity == Severity.CRITICAL for c in cross_validator_checks)
    for dr in document_reports:
        if any(c.severity == Severity.CRITICAL for c in (dr.hard_checks + dr.semantic_checks)):
            has_critical = True
    
    has_warning = any(c.severity == Severity.WARNING for c in cross_validator_checks)
    for dr in document_reports:
        if any(c.severity == Severity.WARNING for c in (dr.hard_checks + dr.semantic_checks)):
            has_warning = True

    final_status = OverallStatus.ZERO_RISK
    if has_critical: final_status = OverallStatus.HIGH_RISK
    elif has_warning: final_status = OverallStatus.MED_RISK
    elif len(document_reports) > 0: final_status = OverallStatus.LOW_RISK

    final_report = AuditReport(
        task_id=task_id,
        overall_status=final_status,
        eflow_data=eflow,
        document_reports=document_reports,
        cross_validation_checks=cross_validator_checks,
        llm_summary=global_summary,
        scenario_summary=global_summary.get("scenario_summary", "")
    )
    manual_confirmation_items = []
    for dr in document_reports:
        for c in dr.hard_checks + dr.semantic_checks:
            if c.manual_confirmation_required:
                manual_confirmation_items.append({
                    "doc_name": dr.doc_name,
                    "check_name": c.check_name,
                    "field_group": c.field_group,
                    "detail": c.detail,
                    "reason_code": c.reason_code,
                })
    for c in cross_validator_checks:
        if c.manual_confirmation_required:
            manual_confirmation_items.append({
                "doc_name": "cross_validation",
                "check_name": c.check_name,
                "field_group": c.field_group,
                "detail": c.detail,
                "reason_code": c.reason_code,
            })
    if global_summary.get("manual_confirmation_items"):
        for item in global_summary.get("manual_confirmation_items", []):
            manual_confirmation_items.append({
                "doc_name": "llm_summary",
                "check_name": "人工确认项",
                "field_group": "summary",
                "detail": str(item),
                "reason_code": "LLM_MANUAL_CONFIRMATION",
            })
    final_report.manual_confirmation_items = manual_confirmation_items
    _save_intermediate(out_dir, "m6_final_report", final_report.model_dump())

    # 关键修复：显式进行 model_dump() 避免 Pydantic 500 序列化报错
    return jsonable_encoder({
        "status": "completed",
        "task_id": task_id,
        "report": final_report.model_dump()
    })

@router.get("/testcases")
async def list_testcases():
    cases = []
    test_dir = Path(__file__).parent.parent.parent / "test_data"
    if test_dir.is_dir():
        for d in sorted(test_dir.iterdir()):
            if d.is_dir() and (d / "eflow.json").exists():
                cases.append({"case_id": d.name, "description": "标准测试用例"})
    return {"cases": cases}

@router.post("/run")
async def run_audit(
    eflow_json: Annotated[UploadFile, File(...)],
    bank_doc: Annotated[List[UploadFile], File(...)], # 兼容前端单数命名
    id_documents: Annotated[List[UploadFile], File(...)],
):
    task_id = str(uuid.uuid4())[:8]
    task_dir = UPLOAD_BASE / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. 保存 EFlow
        eflow_orig_name = eflow_json.filename or "eflow.json"
        eflow_path = _save_upload(eflow_json, task_dir, eflow_orig_name)

        # 2. 保存合同文档 (保留原名)
        d_paths = []
        for f in bank_doc:
            orig_name = f.filename or f"bank_doc_{uuid.uuid4().hex[:4]}.docx"
            d_paths.append(_save_upload(f, task_dir, orig_name))

        # 3. 保存证件原件 (保留原名)
        i_paths = []
        for f in id_documents:
            orig_name = f.filename or f"id_doc_{uuid.uuid4().hex[:4]}.jpg"
            i_paths.append(_save_upload(f, task_dir, orig_name))

        return _run_pipeline(task_id, eflow_path, d_paths, i_paths)
    except Exception as e:
        # 即使报错也要尽力返回 status, 避免前端卡死
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/run-from-testcase")
async def run_from_testcase(case_id: str = Form(...)):
    test_dir = Path(__file__).parent.parent.parent / "test_data" / case_id
    if not test_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"测试用例不存在: {case_id}")

    eflow_path = test_dir / "eflow.json"
    doc_paths = []
    img_paths = []

    for f in test_dir.iterdir():
        ext = f.suffix.lower()
        if ext in (".doc", ".docx", ".pdf") and f.stem != "eflow":
            # 只要是文档类后缀，一律归为申请表
            doc_paths.append(str(f))
        elif ext in (".jpg", ".jpeg", ".png"):
            # 只要是图片类后缀，一律归为证件
            img_paths.append(str(f))

    if not eflow_path.exists():
        raise HTTPException(status_code=404, detail="缺少 eflow.json")

    return _run_pipeline(case_id, str(eflow_path), doc_paths, img_paths)
