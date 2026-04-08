"""
报告生成引擎
"""
from backend.models.schemas import AuditReport, CheckResult, Severity, OverallStatus, ExtractedData

def generate_report(eflow: ExtractedData, word: ExtractedData, ocr: ExtractedData, checks: list[CheckResult]) -> AuditReport:
    """包装审核结果"""
    report = AuditReport(
        eflow_data=eflow,
        word_data=word,
        ocr_data=ocr,
        checks=checks
    )

    # 评估总等级
    has_critical = any(c.severity == Severity.CRITICAL for c in checks)
    has_warning = any(c.severity == Severity.WARNING for c in checks)

    if has_critical:
        report.overall_status = OverallStatus.FAILED
    elif has_warning:
        report.overall_status = OverallStatus.RISK_FOUND
    else:
        report.overall_status = OverallStatus.PASSED

    # 汇总
    critical_count = sum(1 for c in checks if c.severity == Severity.CRITICAL)
    warning_count = sum(1 for c in checks if c.severity == Severity.WARNING)

    if critical_count > 0:
        report.summary = f"预审未通过 ❌。共发现 {critical_count} 个阻断级风险冲突，{warning_count} 个一般风险。"
    elif warning_count > 0:
        report.summary = f"存在部分风险 ⚠️。未发现阻断冲突，但检测到 {warning_count} 个需要复核的一般风险。"
    else:
        report.summary = "审核通过 ✅。三方校验信息完全一致，合规无异常。"

    # === 生成全局 LLM 总结报告 ===
    import json
    from backend.services.llm_client import chat_json
    from backend.config import get_config
    
    cfg = get_config()
    sys_prompt = cfg.get_prompt("overall_summary") or "根据提取结果生成包含 summary (字面总结) 和 risk_insights (风险点数组) 的JSON。"
    
    user_prompt = f"""
    请根据以下审核数据生成全局风险报告：
    - EFlow 申请信息: {eflow.model_dump_json(exclude={'raw_text'})}
    - 银行表单解析: {word.model_dump_json(exclude={'raw_text'})}
    - OCR 证件识别: {ocr.model_dump_json(exclude={'raw_text'})}
    - 交叉比对冲突项: {json.dumps([c.model_dump() for c in checks], ensure_ascii=False)}
    """
    
    try:
        llm_resp = chat_json(sys_prompt, user_prompt)
        report.llm_summary = llm_resp if isinstance(llm_resp, dict) else {"summary": str(llm_resp), "risk_insights": []}
    except Exception as e:
        print(f"全局总结报告生成失败: {e}")
        report.llm_summary = {"summary": "整体文档风险审查报告生成失败。", "risk_insights": [f"大模型响应处理异常: {e}"]}

    return report
