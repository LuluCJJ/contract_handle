"""
审核流程 API — V3.0 The Multi-doc Iterative Pipeline
"""
import os
import uuid
import json
import shutil
import datetime
from pathlib import Path
from typing import List, Annotated
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.encoders import jsonable_encoder

from backend.models.schemas import (
    AuditReport, Severity, CheckResult, PersonInfo, EFlowData, 
    DocExtractedData, DocAnalysisReport, UserPermission, PermissionScope, 
    MediaInfo, CompanyInfo, PlatformInfo
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
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUTS_BASE / f"{task_id}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # === 1. 构建金标准 (E-Flow) ===
    with open(eflow_path, "r", encoding="utf-8") as f:
        eflow_raw = json.load(f)
    eflow = _parse_eflow_v3(eflow_raw)
    _save_intermediate(out_dir, "m1_eflow", eflow.model_dump())

    document_reports = []

    # === 2. 逐件处理文档 (Word/PDF) ===
    for dp in docs_paths:
        fname = Path(dp).name
        parsed_doc = doc_parser.parse_document(dp)
        doc_full_text = doc_parser.get_full_text_for_llm(parsed_doc)
        
        # 2.1 泛化抽取
        extracted = extractor.extract_information(doc_full_text, filename=fname, doc_type="word")
        
        # 2.2 硬比对
        h_checks = hard_comparator.run_hard_comparisons(eflow, extracted)
        
        # 2.3 语义分析
        s_checks = comparator.run_semantic_analyzer(eflow, extracted)
        
        dr = DocAnalysisReport(
            doc_name=fname,
            doc_type="word",
            extracted_data=extracted,
            hard_checks=h_checks,
            semantic_checks=s_checks
        )
        document_reports.append(dr)
        _save_intermediate(out_dir, f"m2_doc_{fname}", dr.model_dump())


    # === 3. 并发处理证件 (OCR - 安全并发) ===
    # 证件扫描是独立的 IO/计算密集型，可以并发而不影响效果
    def _process_single_img(ip):
        fname = Path(ip).name
        ocr_result = ocr_service.extract_id_info(ip)
        
        person = PersonInfo(
            name=ocr_result.get("name", ""),
            id_number=ocr_result.get("id_number", ""),
            id_type=ocr_result.get("id_type", ""),
            expiry_date=ocr_result.get("expiry_date", "")
        )
        extracted = DocExtractedData(
            source_file=fname,
            source_type="ocr",
            persons=[person] if person.name or person.id_number else []
        )
        extracted.raw_text = json.dumps(ocr_result, ensure_ascii=False)
        
        h_checks = hard_comparator.run_hard_comparisons(eflow, extracted)
        curr = datetime.date.today().strftime("%Y-%m-%d")
        if person.expiry_date and person.expiry_date <= curr:
            h_checks.append(CheckResult(
                check_name="证件有效期核查", field_name="expiry_date",
                source_a_label="系统当前日期", source_a_value=curr,
                source_b_label="证件票面", source_b_value=person.expiry_date,
                result="MISMATCH", severity=Severity.CRITICAL, detail="实名证件已过期失效"
            ))
        
        return DocAnalysisReport(
            doc_name=fname,
            doc_type="ocr",
            extracted_data=extracted,
            hard_checks=h_checks,
            semantic_checks=[]
        )

    with ThreadPoolExecutor(max_workers=3) as executor:
        ocr_reports = list(executor.map(_process_single_img, img_paths))
    
    for dr in ocr_reports:
        document_reports.append(dr)
        _save_intermediate(out_dir, f"m3_ocr_{dr.doc_name}", dr.model_dump())

    # === 4. 交叉检验 (Cross Validation) ===
    # 查找各个提取报告间的矛盾，比如文档1说是Token，文档2说是U盾
    cross_checks = []
    # 留作后续功能延展...可以纯代码写，也可以给一个特定的 LLM Cross Checker

    # === 5. 全局智脑 (Global Aggregator) ===
    all_reps_dump = [dr.model_dump() for dr in document_reports]
    llm_sum = comparator.generate_global_summary(eflow, all_reps_dump, cross_checks)
    _save_intermediate(out_dir, "m5_llm_summary", llm_sum)

    # === 6. 报告封装 ===
    report = reporter.assemble_final_report(task_id, eflow, document_reports, cross_checks, llm_sum)
    _save_intermediate(out_dir, "m6_final_report", report.model_dump())

    # 使用 jsonable_encoder 确保 Pydantic 模型能被正确序列化
    return jsonable_encoder({
        "status": "completed",
        "task_id": task_id,
        "report": report
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
        eflow_path = _save_upload(eflow_json, task_dir, "eflow.json")

        d_paths = []
        for i, f in enumerate(bank_doc):
            ext = Path(f.filename or ".docx").suffix
            d_paths.append(_save_upload(f, task_dir, f"bank_app_{i}{ext}"))

        i_paths = []
        for i, img_f in enumerate(id_documents):
            img_ext = Path(img_f.filename or ".jpg").suffix
            i_paths.append(_save_upload(img_f, task_dir, f"id_doc_{i}{img_ext}"))

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
        if f.suffix in (".doc", ".docx", ".pdf") and f.stem != "eflow":
            if "bank_app" in f.name or "form" in f.name:
                doc_paths.append(str(f))
            else:
                img_paths.append(str(f))
        elif f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            img_paths.append(str(f))

    if not eflow_path.exists():
        raise HTTPException(status_code=404, detail="缺少 eflow.json")

    return _run_pipeline(case_id, str(eflow_path), doc_paths, img_paths)
