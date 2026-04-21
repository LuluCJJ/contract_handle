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


def _derive_scenario_summary(eflow: EFlowData, all_docs_reports: list[dict], cross_checks: list[CheckResult]) -> str:
    """优先基于结构化结果生成场景摘要，避免被单边 EFlow 或单次 LLM 总结带偏。"""
    scenario_counts = {}
    action_counts = {}
    user_names = set()
    media_types = set()
    account_numbers = set()
    has_scenario_conflict = False

    for rep in all_docs_reports:
        ed = rep.get("extracted_data", {}) or {}
        sc = (ed.get("scenario_type") or "").strip().upper()
        act = (ed.get("action_type") or "").strip().upper()
        if sc:
            scenario_counts[sc] = scenario_counts.get(sc, 0) + 1
        if act:
            action_counts[act] = action_counts.get(act, 0) + 1

        for u in ed.get("users", []) or []:
            if u.get("user_name"):
                user_names.add(str(u["user_name"]))
            if u.get("account_number"):
                account_numbers.add(str(u["account_number"]))
            media = u.get("media") or {}
            if media.get("media_type"):
                media_types.add(str(media["media_type"]))

        for c in (rep.get("semantic_checks", []) or []) + (rep.get("hard_checks", []) or []):
            detail = str(c.get("detail", ""))
            if c.get("field_group") == "business_scenario" and c.get("severity") == "CRITICAL":
                has_scenario_conflict = True
            if "场景" in detail and ("冲突" in detail or "矛盾" in detail):
                has_scenario_conflict = True

    dominant_scenario = max(scenario_counts, key=scenario_counts.get) if scenario_counts else ""
    dominant_action = max(action_counts, key=action_counts.get) if action_counts else ""

    scenario_map = {
        "OPEN": "权限开通",
        "CANCEL": "权限注销",
        "MODIFY": "权限变更",
        "ATTACH": "权限加挂",
        "UNKNOWN": "待人工确认场景",
    }
    action_map = {
        "OPEN_PERMISSION": "开通权限",
        "CANCEL_PERMISSION": "注销权限",
        "OPEN_MEDIA": "开通介质",
        "CANCEL_MEDIA": "注销介质",
        "UNKNOWN": "待确认动作",
    }

    scenario_text = scenario_map.get(dominant_scenario, eflow.business_scenario or eflow.business_type or "待确认场景")
    action_text = action_map.get(dominant_action, "")

    parts = [f"本次为{scenario_text}场景"]
    if action_text:
        parts.append(f"主动作是{action_text}")
    parts.append(f"涉及{len(user_names) or len(eflow.users) or 0}名义用户")
    parts.append(f"{len(media_types)}个介质对象")
    parts.append(f"{len(account_numbers)}个企业账户")
    summary = "，".join(parts) + "。"
    if has_scenario_conflict:
        summary += " 文档场景与电子流基准存在冲突，需重点人工复核。"
    return summary

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
                field_group=item.get("field_group", ""),
                field_name=item.get("field_name", ""),
                scenario_type=item.get("scenario_type", doc_ext.scenario_type),
                check_mode=item.get("check_mode", ""),
                source_a_label="EFlow系统标准",
                source_a_value=str(item.get("source_a_value", "")),
                source_b_label=f"文档解析",
                source_b_value=str(item.get("source_b_value", "")),
                result=item.get("result", "MATCH"),
                severity=sev,
                manual_confirmation_required=bool(item.get("manual_confirmation_required", False)),
                reason_code=item.get("reason_code", ""),
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
            "scenario_type": rep.get("extracted_data", {}).get("scenario_type", ""),
            "action_type": rep.get("extracted_data", {}).get("action_type", ""),
            "action_summary": rep.get("extracted_data", {}).get("action_summary", ""),
            "semantic_checks": [c.get("detail") for c in rep.get("semantic_checks", []) if c.get("severity") != "PASS"],
            "hard_checks": [c.get("detail") for c in rep.get("hard_checks", []) if c.get("severity") != "PASS"],
            "manual_confirmation_items": [
                c.get("detail") for c in (rep.get("semantic_checks", []) + rep.get("hard_checks", []))
                if c.get("manual_confirmation_required")
            ]
        })

    derived_scenario_summary = _derive_scenario_summary(eflow, all_docs_reports, cross_checks)

    user_prompt = {
         "eflow_business_core": {
             "type": eflow.business_type,
             "scenario": eflow.business_scenario,
             "platform": eflow.platform.platform_name
         },
         "derived_scenario_summary": derived_scenario_summary,
         "documents_risk_findings": cleaned_reports,
         "cross_validation_findings": [c.model_dump() for c in cross_checks]
    }

    try:
        result = chat_json(system_prompt, user_prompt)
        # 场景摘要优先使用结构化派生结果，避免被单次 LLM 总结带偏。
        result["scenario_summary"] = derived_scenario_summary
        return result
    except Exception as e:
        print(f"[Comparator] Error generating summary: {e}")
        return {
            "summary": "无法生成总结",
            "scenario_summary": derived_scenario_summary,
            "risk_insights": []
        }
