"""
报告生成引擎
V3.0 - Multi-doc Report Assembly
"""
from backend.models.schemas import AuditReport, CheckResult, Severity, OverallStatus, EFlowData, DocAnalysisReport

def assemble_final_report(
    task_id: str, 
    eflow: EFlowData, 
    doc_reports: list[DocAnalysisReport], 
    cross_checks: list[CheckResult],
    llm_summary: dict
) -> AuditReport:
    """组装所有局部文档审查和交叉校验结果"""
    
    report = AuditReport(
        task_id=task_id,
        eflow_data=eflow,
        document_reports=doc_reports,
        cross_validation_checks=cross_checks,
        llm_summary=llm_summary
    )

    # 评估总等级
    has_critical = False
    has_warning = False

    for dr in doc_reports:
        for c in dr.hard_checks + dr.semantic_checks:
            if c.severity == Severity.CRITICAL: has_critical = True
            if c.severity == Severity.WARNING: has_warning = True
            
    for c in cross_checks:
        if c.severity == Severity.CRITICAL: has_critical = True
        if c.severity == Severity.WARNING: has_warning = True

    if has_critical:
        report.overall_status = OverallStatus.FAILED
    elif has_warning:
        report.overall_status = OverallStatus.RISK_FOUND
    else:
        report.overall_status = OverallStatus.PASSED

    # 兜底
    if not report.summary:
        if has_critical: report.summary = "发现严重风险，审核失败。"
        elif has_warning: report.summary = "存在警告级别差异，请复核。"
        else: report.summary = "多文档交叉比对完成，各项权限与身份核实一致。"

    # 强制将 summary 转为 utf-8 保存 (防止乱码出现在总体总结里)
    return report
