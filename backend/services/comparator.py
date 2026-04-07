"""
比对引擎 — 执行硬编码规则检查和 LLM 语义检查
"""
import json
from backend.models.schemas import ExtractedData, CheckResult, Severity
from backend.services.llm_client import chat_json, safe_parse_json
from backend.prompts.comparison import SEMANTIC_COMPARISON_SYSTEM_PROMPT, SEMANTIC_COMPARISON_USER_PROMPT_TEMPLATE


def run_comparisons(eflow: ExtractedData, word: ExtractedData, ocr: ExtractedData) -> list[CheckResult]:
    """执行全面的交叉比对"""
    results = []

    # 1. ==== 硬编码规则对比 ====

    # 1.1 证件号码一致性检查 (E-Flow vs Word vs OCR)
    eflow_id = eflow.operator.id_number.strip().upper()
    word_id = word.operator.id_number.strip().upper()
    ocr_id = ocr.operator.id_number.strip().upper()

    id_match = True
    if word_id and eflow_id and word_id != eflow_id:
        id_match = False
    elif ocr_id and eflow_id and ocr_id not in eflow_id and eflow_id not in ocr_id: # 简单容错
        id_match = False

    if id_match:
        results.append(CheckResult(
            check_name="身份证明一致性",
            field_name="id_number",
            source_a_label="E-Flow审批", source_a_value=eflow_id,
            source_b_label="Word申请表", source_b_value=word_id,
            source_c_label="证件OCR", source_c_value=ocr_id,
            result="MATCH", severity=Severity.PASS,
            detail="操作员证件号码在三个信息源中一致"
        ))
    else:
        results.append(CheckResult(
            check_name="身份证明不一致风险",
            field_name="id_number",
            source_a_label="E-Flow审批", source_a_value=eflow_id,
            source_b_label="Word申请表", source_b_value=word_id,
            source_c_label="证件OCR", source_c_value=ocr_id,
            result="MISMATCH", severity=Severity.CRITICAL,
            detail="检测到证件号码存在冲突，请重点核实经办人身份有效性"
        ))

    # 1.2 操作员姓名一致性检查
    eflow_name = eflow.operator.name.strip().upper()
    word_name = word.operator.name.strip().upper()
    ocr_name = ocr.operator.name.strip().upper()

    # 中英文宽松匹配
    name_match = True
    if word_name and eflow_name and word_name != eflow_name:
        name_match = False
    if ocr_name and eflow_name and ocr_name != eflow_name:
         if ocr_name not in eflow_name and eflow_name not in ocr_name:
             name_match = False

    if not name_match:
        severity = Severity.CRITICAL
        # 若仅仅大小写、空格不一样，已经通过 upper 和 in 过滤。差异大则是CRITICAL。
        results.append(CheckResult(
            check_name="操作人姓名不一致风险",
            field_name="name",
            source_a_label="E-Flow审批", source_a_value=eflow_name,
            source_b_label="Word申请表", source_b_value=word_name,
            source_c_label="证件OCR", source_c_value=ocr_name,
            result="MISMATCH", severity=severity,
            detail="电子审批单、申请文件与实体证件上的姓名不完全符合"
        ))

    # 1.3 账号一致性 (E-Flow vs Word)
    if eflow.account.account_number and word.account.account_number:
        # 去掉空格和横线
        ef_acc = eflow.account.account_number.replace(" ", "").replace("-", "")
        wd_acc = word.account.account_number.replace(" ", "").replace("-", "")
        
        # 容忍前缀差异 (有时只验证部分网银账号前缀)
        if ef_acc != wd_acc and ef_acc not in wd_acc and wd_acc not in ef_acc:
             results.append(CheckResult(
                check_name="关联账号一致性",
                field_name="account_number",
                source_a_label="E-Flow审批", source_a_value=eflow.account.account_number,
                source_b_label="Word申请表", source_b_value=word.account.account_number,
                result="MISMATCH", severity=Severity.WARNING,
                detail="Word 表填报的账号与 E-Flow 审批的账号不一致"
            ))

    # 1.4 证件类型可疑
    ef_type = eflow.operator.id_type
    wd_type = word.operator.id_type
    ocr_type = ocr.operator.id_type # 'id_card', 'passport'

    if ocr_type == 'passport' and ("身份" in ef_type or "身份" in wd_type):
        results.append(CheckResult(
            check_name="证件实体不符",
            field_name="id_type",
            source_a_label="单据声明类型", source_a_value=ef_type + " / " + wd_type,
            source_c_label="证件OCR识别为", source_c_value=ocr_type,
            result="MISMATCH", severity=Severity.WARNING,
            detail="申请表注明身份证件，但实际上载图档似为护照，请复核"
        ))

    # 2. ==== LLM 语义对比 ====
    
    # 组装脱敏数据送给 LLM
    eflow_json = eflow.model_dump_json(include={'activity', 'permissions'})
    word_json = word.model_dump_json(include={'activity', 'permissions'})

    prompt = SEMANTIC_COMPARISON_USER_PROMPT_TEMPLATE.format(
        eflow_data=eflow_json,
        word_data=word_json
    )

    llm_resp = chat_json(SEMANTIC_COMPARISON_SYSTEM_PROMPT, prompt)

    # 使用安全解析
    semantic_data = safe_parse_json(llm_resp)
    checks = semantic_data.get("semantic_checks", [])
    
    for c in checks:
        sev_str = c.get("severity", "PASS").upper()
        try:
            sev = Severity(sev_str)
        except ValueError:
            sev = Severity.PASS

        results.append(CheckResult(
            check_name=c.get("check_name", "语义检查项"),
            result=c.get("result", "PASS"),
            severity=sev,
            detail=c.get("detail", "")
        ))

    return results
