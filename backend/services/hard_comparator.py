"""
Hard Comparator - 精确执行关键字段的代码级硬比对
V3.0 - 负责姓名、账户、证件等不可由大模型主观猜测的刚性字段对比
"""
import re
from backend.models.schemas import EFlowData, DocExtractedData, CheckResult, Severity
from backend.services.check_taxonomy import CheckBlock, CheckLayer, tag_check

def _clean_str(val: str) -> str:
    """清理字符串：大写、去空格、去特殊字符以便对齐比对"""
    if not val:
        return ""
    # 去除中间和两边的空格，统一转大写
    clean = re.sub(r'[\s\-:：_]', '', str(val)).upper()
    return clean

def _is_name_match(name1: str, name2: str) -> bool:
    if not name1 or not name2:
        return False
    c1 = _clean_str(name1)
    c2 = _clean_str(name2)
    # 允许包含关系 (例如 "Wang Wei" vs "WangWei(CEO)")
    return c1 in c2 or c2 in c1

def _clean_account_name(val: str) -> str:
    clean = _clean_str(val)
    for suffix in ["基本存款账户", "一般存款账户", "专用存款账户", "临时存款账户"]:
        clean = clean.replace(_clean_str(suffix), "")
    replacements = {
        "LIMITED": "LTD",
        "LTD.": "LTD",
        "INCORPORATED": "INC",
        "INC.": "INC",
    }
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    return clean

def _valid_mainland_id(id_number: str) -> bool:
    value = re.sub(r"[\s\-:：]", "", str(id_number))
    return bool(re.fullmatch(r"\d{17}[\dX]", value))

def _append_check(
    checks: list[CheckResult],
    *,
    check_name: str,
    field_group: str,
    field_name: str,
    source_a_label: str,
    source_a_value: str,
    source_b_label: str,
    source_b_value: str,
    matched: bool,
    reason_code: str,
    detail: str,
    scenario_type: str = "",
    manual: bool = False,
    severity: Severity | None = None,
) -> None:
    checks.append(CheckResult(
        check_name=check_name,
        category="核心信息一致性检查",
        field_group=field_group,
        field_name=field_name,
        scenario_type=scenario_type,
        check_mode="exact_or_normalized_match",
        source_a_label=source_a_label,
        source_a_value=str(source_a_value or ""),
        source_b_label=source_b_label,
        source_b_value=str(source_b_value or ""),
        result="MATCH" if matched else "MISMATCH",
        severity=Severity.PASS if matched else (severity or Severity.CRITICAL),
        manual_confirmation_required=manual,
        reason_code=reason_code,
        detail=detail,
    ))

def run_hard_comparisons(eflow: EFlowData, doc_ext: DocExtractedData) -> list[CheckResult]:
    """对单份文档提取的数据进行硬比对"""
    checks = []
    
    doc_type = doc_ext.source_type # "word" / "ocr" / "pdf"

    # A1.1 网银平台/开户银行名称。只在两边都能稳定提取时执行，避免制造无意义噪音。
    eflow_bank = eflow.platform.bank_name or eflow.platform.platform_name
    doc_bank = doc_ext.platform.bank_name or doc_ext.platform.platform_name
    if eflow_bank and doc_bank:
        matched = _is_name_match(eflow_bank, doc_bank)
        _append_check(
            checks,
            check_name="网银平台名称核对",
            field_group="account",
            field_name="bank_platform",
            source_a_label="EFlow登记平台",
            source_a_value=eflow_bank,
            source_b_label=f"材料识别-{doc_type}",
            source_b_value=doc_bank,
            matched=matched,
            reason_code="BANK_PLATFORM_MATCH" if matched else "BANK_PLATFORM_MISMATCH",
            detail="网银平台/开户银行名称一致。" if matched else "电子流中的网银平台与材料中的银行名称不一致，建议确认是否存在跨银行错配。",
            scenario_type=doc_ext.scenario_type,
        )

    # 1. 对比公司信用代码
    if eflow.company.cert_number and doc_ext.company.cert_number:
        e_cmp = _clean_str(eflow.company.cert_number)
        d_cmp = _clean_str(doc_ext.company.cert_number)
        if e_cmp != d_cmp:
            checks.append(CheckResult(
                check_name="公司证件号精确比对",
                field_group="subject",
                field_name="company_cert",
                scenario_type=doc_ext.scenario_type,
                check_mode="consistency",
                source_a_label="EFlow", source_a_value=str(eflow.company.cert_number),
                source_b_label=f"提取-{doc_type}", source_b_value=str(doc_ext.company.cert_number),
                result="MISMATCH", severity=Severity.CRITICAL,
                reason_code="COMPANY_CERT_MISMATCH",
                detail=f"公司信用代码不一致"
            ))
        else:
            checks.append(CheckResult(
                check_name="公司证件号精确比对",
                field_group="subject",
                field_name="company_cert",
                scenario_type=doc_ext.scenario_type,
                check_mode="consistency",
                source_a_label="EFlow", source_a_value=str(eflow.company.cert_number),
                source_b_label=f"提取-{doc_type}", source_b_value=str(doc_ext.company.cert_number),
                result="MATCH", severity=Severity.PASS,
                reason_code="COMPANY_CERT_MATCH",
                detail="公司信用代码核对一致"
            ))

    # 2. 对于 OCR 提取的证件：重点在于核对人员信息是否属于 EFlow 的名单
    if doc_type == "ocr" and doc_ext.persons:
        # 构建 eflow 全量人员池（申请人 + 用户）
        eflow_names = []
        eflow_ids = []
        if eflow.applicant.name: eflow_names.append(eflow.applicant.name)
        if eflow.applicant.id_number: eflow_ids.append(eflow.applicant.id_number)
        
        for u in eflow.users:
            if u.user_name: eflow_names.append(u.user_name)
        
        for p in doc_ext.persons:
            # 查身份证号
            id_matched = False
            if p.id_number:
                p_id_clean = _clean_str(p.id_number)
                for eid in eflow_ids:
                    if _clean_str(eid) == p_id_clean:
                        id_matched = True
                        break
            
            # 查姓名
            name_matched = False
            if p.name:
                for ename in eflow_names:
                    if _is_name_match(p.name, ename):
                        name_matched = True
                        break
                        
            if not id_matched and not name_matched:
                if p.name or p.id_number:
                    checks.append(CheckResult(
                        check_name="证件实体收录核查",
                        category="身份一致性",
                        field_group="subject",
                        field_name="person_whitelist",
                        scenario_type=doc_ext.scenario_type,
                        check_mode="manual_confirmation",
                        source_a_label="EFlow配置名单", source_a_value=str(f"姓名池:{eflow_names}"),
                        source_b_label="OCR解析名字", source_b_value=str(p.name),
                        result="MISMATCH", severity=Severity.WARNING,
                        manual_confirmation_required=True,
                        reason_code="PERSON_NOT_IN_EFLOW_WHITELIST",
                        detail="发现不在 EFlow 审批名单内的持证人，请核实是否有未报备人员"
                    ))
            else:
                checks.append(CheckResult(
                    check_name="证件白名单归属",
                    category="身份一致性",
                    field_group="subject",
                    field_name="person_whitelist",
                    scenario_type=doc_ext.scenario_type,
                    check_mode="consistency",
                    source_a_label="EFlow白名单", source_a_value="系统名册",
                    source_b_label="OCR身份", source_b_value=str(p.name or p.id_number),
                    result="MATCH", severity=Severity.PASS,
                    reason_code="PERSON_IN_EFLOW_WHITELIST",
                    detail=f"证件实体 ({p.name}) 在审批范畴内"
                ))
            if p.id_number and re.fullmatch(r"\d{17}[\dXx]", _clean_str(p.id_number)):
                id_valid = _valid_mainland_id(p.id_number)
                checks.append(CheckResult(
                    check_name="身份证号码格式核对",
                    category="身份一致性",
                    field_group="subject",
                    field_name="id_number",
                    scenario_type=doc_ext.scenario_type,
                    check_mode="format_validation",
                    source_a_label="证件号码规则",
                    source_a_value="18位，末位X需大写",
                    source_b_label="OCR证件号码",
                    source_b_value=str(p.id_number),
                    result="MATCH" if id_valid else "MISMATCH",
                    severity=Severity.PASS if id_valid else Severity.WARNING,
                    manual_confirmation_required=not id_valid,
                    reason_code="ID_NUMBER_FORMAT_OK" if id_valid else "ID_NUMBER_FORMAT_REVIEW",
                    detail="身份证号码格式符合基础规则。" if id_valid else "身份证号码格式需复核，末位 X 需大写且号码应为18位。",
                ))
    
    # 3. 对于 Word/PDF 表单：提取的多个 users 与 eflow 的 users 对比
    if doc_type in ["word", "pdf"] and doc_ext.users:
        eflow_users = eflow.users
        for doc_u in doc_ext.users:
            # 根据 name 或 account 找匹配项
            matched_ef_u = None
            for ef_u in eflow_users:
                if doc_u.user_name and ef_u.user_name and _is_name_match(doc_u.user_name, ef_u.user_name):
                    matched_ef_u = ef_u
                    break
            
            # 如果名字对上，校验他们的账号
            if matched_ef_u and matched_ef_u.account_number and doc_u.account_number:
                ef_acc = _clean_str(matched_ef_u.account_number)
                doc_acc = _clean_str(doc_u.account_number)
                if ef_acc != doc_acc:
                     checks.append(CheckResult(
                        check_name=f"操作员({doc_u.user_name})账号绑定校验",
                        field_group="account",
                        field_name="user_account",
                        scenario_type=doc_ext.scenario_type,
                        check_mode="consistency",
                        source_a_label="EFlow下发", source_a_value=str(matched_ef_u.account_number),
                        source_b_label="表单填写", source_b_value=str(doc_u.account_number),
                        result="MISMATCH", severity=Severity.CRITICAL,
                        reason_code="USER_ACCOUNT_MISMATCH",
                        detail="绑定账号与系统电子流账号打架，存在被篡改的重大合规风险"
                    ))
                else:
                    checks.append(CheckResult(
                        check_name=f"操作员({doc_u.user_name})账号绑定校验",
                        field_group="account",
                        field_name="user_account",
                        scenario_type=doc_ext.scenario_type,
                        check_mode="consistency",
                        source_a_label="EFlow下发", source_a_value=str(matched_ef_u.account_number),
                        source_b_label="表单填写", source_b_value=str(doc_u.account_number),
                        result="MATCH", severity=Severity.PASS,
                        reason_code="USER_ACCOUNT_MATCH",
                        detail="绑定账号精准一致"
                    ))

            if matched_ef_u:
                if matched_ef_u.account_name and doc_u.account_name:
                    matched = _clean_account_name(matched_ef_u.account_name) == _clean_account_name(doc_u.account_name)
                    _append_check(
                        checks,
                        check_name="账户名称核对",
                        field_group="account",
                        field_name="account_name",
                        source_a_label="EFlow账户名称",
                        source_a_value=matched_ef_u.account_name,
                        source_b_label="材料账户名称",
                        source_b_value=doc_u.account_name,
                        matched=matched,
                        reason_code="ACCOUNT_NAME_MATCH" if matched else "ACCOUNT_NAME_MISMATCH",
                        detail="账户名称一致。" if matched else "账户名称与电子流不一致，需关注简称、后缀、英文大小写或标点是否被改写。",
                        scenario_type=doc_ext.scenario_type,
                    )
                if matched_ef_u.account_name_en and doc_u.account_name_en:
                    matched = _clean_account_name(matched_ef_u.account_name_en) == _clean_account_name(doc_u.account_name_en)
                    _append_check(
                        checks,
                        check_name="账户英文名称核对",
                        field_group="account",
                        field_name="account_name_en",
                        source_a_label="EFlow英文账户名称",
                        source_a_value=matched_ef_u.account_name_en,
                        source_b_label="材料英文账户名称",
                        source_b_value=doc_u.account_name_en,
                        matched=matched,
                        reason_code="ACCOUNT_NAME_EN_MATCH" if matched else "ACCOUNT_NAME_EN_MISMATCH",
                        detail="英文账户名称一致。" if matched else "英文账户名称与电子流不一致，英文大小写、缩写或标点需按银行备案信息复核。",
                        scenario_type=doc_ext.scenario_type,
                    )
                if matched_ef_u.account_status:
                    status_text = str(matched_ef_u.account_status)
                    abnormal = any(word in status_text for word in ["注销", "冻结", "挂失", "停用", "CANCEL", "FROZEN", "LOST", "DISABLED"])
                    _append_check(
                        checks,
                        check_name="账户状态核对",
                        field_group="account",
                        field_name="account_status",
                        source_a_label="EFlow账户状态",
                        source_a_value=status_text,
                        source_b_label="材料/业务要求",
                        source_b_value="账户应为正常使用状态",
                        matched=not abnormal,
                        reason_code="ACCOUNT_STATUS_OK" if not abnormal else "ACCOUNT_STATUS_ABNORMAL",
                        detail="账户状态未发现异常。" if not abnormal else "电子流账户状态显示可能为注销、冻结、挂失或停用，建议确认是否可继续办理。",
                        scenario_type=doc_ext.scenario_type,
                        manual=abnormal,
                        severity=Severity.WARNING,
                    )
                if (matched_ef_u.single_limit and doc_u.single_limit and matched_ef_u.single_limit != doc_u.single_limit) or (
                    matched_ef_u.daily_limit and doc_u.daily_limit and matched_ef_u.daily_limit != doc_u.daily_limit
                ):
                    _append_check(
                        checks,
                        check_name="权限限额核对",
                        field_group="permission",
                        field_name="permission_limit",
                        source_a_label="EFlow限额",
                        source_a_value=f"single={matched_ef_u.single_limit}, daily={matched_ef_u.daily_limit}",
                        source_b_label="材料限额",
                        source_b_value=f"single={doc_u.single_limit}, daily={doc_u.daily_limit}",
                        matched=False,
                        reason_code="PERMISSION_LIMIT_MISMATCH",
                        detail="材料中的单笔或日累计限额与电子流不一致，建议按电子流需求复核金额和币种单位。",
                        scenario_type=doc_ext.scenario_type,
                    )
                if matched_ef_u.media.media_number and doc_u.media.media_number:
                    matched = _clean_str(matched_ef_u.media.media_number) == _clean_str(doc_u.media.media_number)
                    _append_check(
                        checks,
                        check_name="介质编号核对",
                        field_group="media",
                        field_name="media_number",
                        source_a_label="EFlow介质编号",
                        source_a_value=matched_ef_u.media.media_number,
                        source_b_label="材料介质编号",
                        source_b_value=doc_u.media.media_number,
                        matched=matched,
                        reason_code="MEDIA_NUMBER_MATCH" if matched else "MEDIA_NUMBER_MISMATCH",
                        detail="介质编号一致。" if matched else "材料中的介质编号与电子流不一致，建议确认是否为正确介质。",
                        scenario_type=doc_ext.scenario_type,
                    )

    return [
        tag_check(c, layer=CheckLayer.EFLOW_BASED, block=CheckBlock.A1_EXACT, confidence=1.0)
        for c in checks
    ]
