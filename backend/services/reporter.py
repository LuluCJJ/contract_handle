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
    from backend.prompts.comparison import OVERALL_SUMMARY_SYSTEM_PROMPT, OVERALL_SUMMARY_USER_PROMPT_TEMPLATE
    
    try:
        user_prompt = OVERALL_SUMMARY_USER_PROMPT_TEMPLATE.format(
            eflow_data=eflow.model_dump_json(exclude={'raw_text'}),
            word_data=word.model_dump_json(exclude={'raw_text'}),
            ocr_data=ocr.model_dump_json(exclude={'raw_text'}),
            checks_data=json.dumps([c.model_dump() for c in checks], ensure_ascii=False)
        )
        
        llm_resp = chat_json(OVERALL_SUMMARY_SYSTEM_PROMPT, user_prompt)
        report.llm_summary = json.loads(llm_resp)
    except Exception as e:
        print(f"全局总结报告生成失败: {e}")
        report.llm_summary = {"summary": "整体文档风险审查报告生成失败。", "risk_insights": ["无法连接大模型或大模型返回格式错误。"]}

    return report
