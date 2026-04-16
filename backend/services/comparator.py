"""
Comparator Service - Compares extracted data against rules and identifies risks
V3.0 - Semantic Risk Analyzer for Multi-doc Pipeline
"""
import sys
import datetime
from pathlib import Path

# VSCode Path Fix
script_dir = Path(__file__).resolve().parent
project_root = str(script_dir.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.llm_client import chat_json
from backend.config import get_config
from backend.models.schemas import EFlowData, DocExtractedData, CheckResult, Severity

def run_semantic_analyzer(eflow: EFlowData, doc_ext: DocExtractedData) -> list[CheckResult]:
    """让 LLM 通过语义理解比对 eflow 体系与 doc 抽取结果之间的逻辑差异"""
    cfg = get_config()
    system_prompt = cfg.get_prompt("semantic_risk_analyzer")
    if not system_prompt: return []
    
    user_prompt = {
        "current_date": datetime.date.today().strftime("%Y-%m-%d"),
        "instruction": f"请针对文件 '{doc_ext.source_file}' 的提取结果与 EFlow 标准进行比对。",
        "eflow_standard": eflow.model_dump(exclude={'raw_text'}), 
        "doc_extraction": doc_ext.model_dump(exclude={'raw_text'})
    }
    
    try:
        res = chat_json(system_prompt, user_prompt)
        checks = []
        for item in res.get("semantic_checks", []):
            sev_str = item.get("severity", "PASS").upper()
            sev = Severity.PASS
            if sev_str in ["FAIL", "CRITICAL"]: sev = Severity.CRITICAL
            elif sev_str == "WARNING": sev = Severity.WARNING
            elif sev_str == "INFO": sev = Severity.INFO
            
            # 分类映射
            cat = item.get("category", "业务要素核对")
            
            checks.append(CheckResult(
                check_name=item.get("check_name", "语义比对测试"),
                category=cat,
                source_a_label="EFlow系统标准",
                source_a_value=str(item.get("source_a_value", "")),
                source_b_label=f"文档解析",
                source_b_value=str(item.get("source_b_value", "")),
                result=item.get("result", "MATCH"),
                severity=sev,
                detail=item.get("detail", "")
            ))
        return checks
    except Exception as e:
        print(f"[Comparator] Error running semantic check for {doc_ext.source_file}: {e}")
        return []

def generate_global_summary(eflow: EFlowData, all_docs_reports: list[dict], cross_checks: list[CheckResult]) -> dict:
    """生成包含全部报告汇总视角的最终审阅"""
    cfg = get_config()
    system_prompt = cfg.get_prompt("multi_doc_summary")
    if not system_prompt: return {"summary": "无总述Prompt", "risk_insights": []}

    # 精简数据发给模型
    cleaned_reports = []
    for rep in all_docs_reports:
        # rep 是一个 Dict，我们要剔除冗余字段减小体量
        cleaned_reports.append({
            "doc_name": rep.get("doc_name"),
            "doc_type": rep.get("doc_type"),
            "semantic_checks": [c.get("detail") for c in rep.get("semantic_checks", []) if c.get("severity") != "PASS"],
            "hard_checks": [c.get("detail") for c in rep.get("hard_checks", []) if c.get("severity") != "PASS"]
        })

    user_prompt = {
         "eflow_business_core": {
             "type": eflow.business_type,
             "scenario": eflow.business_scenario,
             "platform": eflow.platform.platform_name
         },
         "documents_risk_findings": cleaned_reports,
         "cross_validation_findings": [c.model_dump() for c in cross_checks]
    }

    try:
        return chat_json(system_prompt, user_prompt)
    except Exception as e:
        print(f"[Comparator] Error generating summary: {e}")
        return {"summary": "无法生成总结", "risk_insights": []}
