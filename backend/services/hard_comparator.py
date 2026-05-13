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

def _clean_branch_name(value: str) -> str:
    clean = _clean_str(value)
    for prefix in [
        "中国工商银行", "工商银行", "ICBC", "工行",
        "中国银行", "BOC", "中行",
        "中国建设银行", "建设银行", "CCB", "建行",
        "北京", "上海", "深圳", "广州",
    ]:
        clean = clean.replace(_clean_str(prefix), "")
    return clean

def _is_branch_match(branch1: str, branch2: str) -> bool:
    if _is_name_match(branch1, branch2):
        return True
    c1 = _clean_branch_name(branch1)
    c2 = _clean_branch_name(branch2)
    return bool(c1 and c2 and (c1 in c2 or c2 in c1))

def _split_tokens(value: str) -> set[str]:
    """Split account/media fields that may contain multiple values in one cell."""
    if not value:
        return set()
    parts = re.split(r"[,，;；、\n/]+", str(value))
    return {_clean_str(part) for part in parts if _clean_str(part)}

def _has_token_overlap(left: str, right: str) -> bool:
    left_tokens = _split_tokens(left)
    right_tokens = _split_tokens(right)
    if left_tokens and right_tokens:
        return bool(left_tokens & right_tokens)
    return _clean_str(left) == _clean_str(right)

def _scope_dict(user, *, prefer_text: bool = False) -> dict[str, bool]:
    scope = user.permission_scope
    permission_text = " ".join([
        str(user.permission_sub_type or ""),
        str(scope.raw_text or ""),
    ])
    text_has = {
        "payment": any(word in permission_text for word in ["制单", "经办", "录入", "提交", "付款", "支付", "转账", "汇款", "Maker", "Inputter"]),
        "authorize": any(word in permission_text for word in ["授权", "复核", "审批", "放行", "授权员", "复核员", "Checker", "Authorizer", "Approver"]),
        "query": any(word in permission_text for word in ["查询", "余额", "明细", "对账", "Query", "Inquiry"]),
        "upload": any(word in permission_text for word in ["上传", "上载", "导入", "批量", "Upload", "Import"]),
    }
    result = {
        "authorize": bool(scope.authorize),
        "payment": bool(scope.payment),
        "query": bool(scope.query),
        "upload": bool(scope.upload),
    }
    if prefer_text and permission_text.strip():
        result = {key: value for key, value in text_has.items()}
    else:
        for key, value in text_has.items():
            if value:
                result[key] = True
    return result

def _scope_labels(keys: list[str]) -> str:
    labels = {
        "authorize": "授权/复核",
        "payment": "支付/转账",
        "query": "查询",
        "upload": "上传/导入",
    }
    return "、".join(labels.get(k, k) for k in keys)

def _scope_label(key: str) -> str:
    return _scope_labels([key])

def _user_identity(user) -> str:
    parts = [user.user_name, user.account_number, user.media.media_number, user.permission_sub_type]
    return " / ".join(str(p) for p in parts if p)

def _media_summary(media) -> str:
    parts = [
        media.media_type,
        media.media_number,
        f"{media.media_quantity}个" if getattr(media, "media_quantity", 0) else "",
        media.existing_media,
        "需注销" if media.needs_cancellation else "",
    ]
    return " / ".join(str(p) for p in parts if p)

def _has_media_fact(user) -> bool:
    media = user.media
    return bool(
        media.media_type
        or media.media_number
        or getattr(media, "media_quantity", 0)
        or media.existing_media
        or media.is_blank
        or media.is_physical
        or media.needs_cancellation
    )

def _match_score(ef_user, doc_user) -> int:
    score = 0
    if ef_user.user_name and doc_user.user_name and _is_name_match(ef_user.user_name, doc_user.user_name):
        score += 100
    if ef_user.account_number and doc_user.account_number and _has_token_overlap(ef_user.account_number, doc_user.account_number):
        score += 60
    if ef_user.media.media_number and doc_user.media.media_number and _has_token_overlap(ef_user.media.media_number, doc_user.media.media_number):
        score += 50
    if ef_user.permission_sub_type and doc_user.permission_sub_type and _is_name_match(ef_user.permission_sub_type, doc_user.permission_sub_type):
        score += 15
    return score

def _match_users(eflow_users, doc_users) -> tuple[list[tuple[object, object, int]], list[object], list[object]]:
    """Greedy user matcher for multi-operator forms.

    It intentionally requires at least a name/account/media match. Permission role
    alone is too weak and can pair unrelated operators.
    """
    candidates = []
    for e_idx, ef_user in enumerate(eflow_users):
        for d_idx, doc_user in enumerate(doc_users):
            score = _match_score(ef_user, doc_user)
            if score >= 50:
                candidates.append((score, e_idx, d_idx, ef_user, doc_user))
    candidates.sort(reverse=True, key=lambda item: item[0])

    used_e: set[int] = set()
    used_d: set[int] = set()
    matches = []
    for score, e_idx, d_idx, ef_user, doc_user in candidates:
        if e_idx in used_e or d_idx in used_d:
            continue
        used_e.add(e_idx)
        used_d.add(d_idx)
        matches.append((ef_user, doc_user, score))

    unmatched_ef = [u for idx, u in enumerate(eflow_users) if idx not in used_e]
    unmatched_doc = [u for idx, u in enumerate(doc_users) if idx not in used_d]
    return matches, unmatched_ef, unmatched_doc

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

    # A1.1 网银平台/开户银行名称。平台编号不参与核对；优先核对银行全称与分行信息。
    eflow_bank = eflow.platform.bank_name or eflow.platform.platform_name
    doc_bank = doc_ext.platform.bank_name or doc_ext.platform.platform_name
    if eflow_bank and doc_bank:
        matched = _is_name_match(eflow_bank, doc_bank)
        _append_check(
            checks,
            check_name="网银平台名称核对",
            field_group="platform",
            field_name="platform_name",
            source_a_label="EFlow登记平台",
            source_a_value=eflow_bank,
            source_b_label=f"材料识别-{doc_type}",
            source_b_value=doc_bank,
            matched=matched,
            reason_code="BANK_PLATFORM_MATCH" if matched else "BANK_PLATFORM_MISMATCH",
            detail="网银平台/开户银行名称一致。" if matched else "电子流中的网银平台与材料中的银行名称不一致，建议确认是否存在跨银行错配。",
            scenario_type=doc_ext.scenario_type,
        )
        if eflow.platform.branch_name and doc_ext.platform.branch_name:
            branch_matched = _is_branch_match(eflow.platform.branch_name, doc_ext.platform.branch_name)
            _append_check(
                checks,
                check_name="网银平台分行核对",
                field_group="platform",
                field_name="platform_branch",
                source_a_label="EFlow登记分行",
                source_a_value=eflow.platform.branch_name,
                source_b_label=f"材料识别-{doc_type}",
                source_b_value=doc_ext.platform.branch_name,
                matched=branch_matched,
                reason_code="BANK_BRANCH_MATCH" if branch_matched else "BANK_BRANCH_MISMATCH",
                detail="网银平台分行信息一致。" if branch_matched else "材料中的分行信息与电子流不一致，建议确认是否选错办理银行或分支机构。",
                scenario_type=doc_ext.scenario_type,
            )
    elif eflow_bank and doc_type in ["word", "pdf"]:
        _append_check(
            checks,
            check_name="网银平台名称需要确认",
            field_group="platform",
            field_name="platform_name",
            source_a_label="EFlow登记平台",
            source_a_value=eflow_bank,
            source_b_label=f"材料识别-{doc_type}",
            source_b_value="未稳定识别",
            matched=False,
            reason_code="BANK_PLATFORM_NOT_EXTRACTED",
            detail="电子流中存在网银平台，但材料中未稳定识别到办理银行。建议结合文档标题、表头或银行关键位置确认办理平台。",
            scenario_type=doc_ext.scenario_type,
            manual=True,
            severity=Severity.WARNING,
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
        matches, unmatched_ef_users, unmatched_doc_users = _match_users(eflow_users, doc_ext.users)

        if eflow_users:
            for ef_u in unmatched_ef_users:
                checks.append(CheckResult(
                    check_name="电子流用户在材料中未稳定识别",
                    category="核心信息一致性检查",
                    field_group="subject",
                    field_name="user_presence",
                    scenario_type=doc_ext.scenario_type,
                    check_mode="object_matching",
                    source_a_label="EFlow用户",
                    source_a_value=_user_identity(ef_u),
                    source_b_label="材料识别用户",
                    source_b_value="未稳定匹配",
                    result="MISSING",
                    severity=Severity.WARNING,
                    manual_confirmation_required=True,
                    reason_code="EFLOW_USER_NOT_FOUND_IN_DOC",
                    detail="电子流中存在该操作员/权限对象，但材料中未稳定识别到对应对象，建议确认材料是否遗漏或抽取是否不完整。",
                ))
            for doc_u in unmatched_doc_users:
                checks.append(CheckResult(
                    check_name="材料出现电子流外用户",
                    category="核心信息一致性检查",
                    field_group="subject",
                    field_name="user_presence",
                    scenario_type=doc_ext.scenario_type,
                    check_mode="object_matching",
                    source_a_label="EFlow用户清单",
                    source_a_value="; ".join(_user_identity(u) for u in eflow_users),
                    source_b_label="材料识别用户",
                    source_b_value=_user_identity(doc_u),
                    result="MISMATCH",
                    severity=Severity.WARNING,
                    manual_confirmation_required=True,
                    reason_code="DOC_USER_NOT_IN_EFLOW",
                    detail="材料中出现未能与电子流稳定匹配的用户/权限对象，建议确认是否为额外人员、模板联系人或抽取误差。",
                ))

        # 如果 EFlow 没有用户明细，仍保留材料多用户事实，提示审核人确认基准信息是否完整。
        if not eflow_users and len(doc_ext.users) > 1:
            checks.append(CheckResult(
                check_name="材料包含多名操作员但电子流无用户明细",
                category="核心信息一致性检查",
                field_group="subject",
                field_name="user_presence",
                scenario_type=doc_ext.scenario_type,
                check_mode="object_matching",
                source_a_label="EFlow用户清单",
                source_a_value="空",
                source_b_label="材料识别用户",
                source_b_value="; ".join(_user_identity(u) for u in doc_ext.users),
                result="REVIEW",
                severity=Severity.WARNING,
                manual_confirmation_required=True,
                reason_code="DOC_MULTI_USER_WITHOUT_EFLOW_USERS",
                detail="材料中识别到多名操作员/权限对象，但电子流未提供用户明细，建议补齐电子流结构化基准后再进行逐人核对。",
            ))

        for matched_ef_u, doc_u, match_score in matches:
            checks.append(CheckResult(
                check_name=f"操作员({doc_u.user_name or matched_ef_u.user_name})对象匹配",
                category="核心信息一致性检查",
                field_group="subject",
                field_name="user_object",
                scenario_type=doc_ext.scenario_type,
                check_mode="object_matching",
                source_a_label="EFlow用户对象",
                source_a_value=_user_identity(matched_ef_u),
                source_b_label="材料用户对象",
                source_b_value=_user_identity(doc_u),
                result="MATCH",
                severity=Severity.PASS,
                reason_code="USER_OBJECT_MATCH",
                detail="材料中的用户/权限对象已与电子流用户稳定匹配。",
                evidence=f"match_score={match_score}",
            ))
            
            # 如果对象对上，校验该操作员名下办理的企业银行账户账号。
            if matched_ef_u and matched_ef_u.account_number and doc_u.account_number:
                if not _has_token_overlap(matched_ef_u.account_number, doc_u.account_number):
                     checks.append(CheckResult(
                        check_name=f"操作员({doc_u.user_name})银行账户账号核对",
                        field_group="account",
                        field_name="account_number",
                        scenario_type=doc_ext.scenario_type,
                        check_mode="consistency",
                        source_a_label="EFlow用户信息-银行账户账号", source_a_value=str(matched_ef_u.account_number),
                        source_b_label="材料填写-银行账户账号", source_b_value=str(doc_u.account_number),
                        result="MISMATCH", severity=Severity.CRITICAL,
                        reason_code="USER_ACCOUNT_MISMATCH",
                        detail="材料中的银行账户账号与电子流用户信息中的 account_number 不一致，建议优先复核是否填错账户。"
                    ))
                else:
                    checks.append(CheckResult(
                        check_name=f"操作员({doc_u.user_name})银行账户账号核对",
                        field_group="account",
                        field_name="account_number",
                        scenario_type=doc_ext.scenario_type,
                        check_mode="consistency",
                        source_a_label="EFlow用户信息-银行账户账号", source_a_value=str(matched_ef_u.account_number),
                        source_b_label="材料填写-银行账户账号", source_b_value=str(doc_u.account_number),
                        result="MATCH", severity=Severity.PASS,
                        reason_code="USER_ACCOUNT_MATCH",
                        detail="材料中的银行账户账号与电子流用户信息一致。"
                    ))

            if matched_ef_u:
                ef_scope = _scope_dict(matched_ef_u)
                doc_scope = _scope_dict(doc_u, prefer_text=True)
                for permission_key in ["authorize", "payment", "query", "upload"]:
                    ef_enabled = bool(ef_scope.get(permission_key))
                    doc_enabled = bool(doc_scope.get(permission_key))
                    if not ef_enabled and not doc_enabled:
                        continue
                    label = _scope_label(permission_key)
                    if ef_enabled == doc_enabled:
                        result = "MATCH"
                        severity = Severity.PASS
                        manual = False
                        reason = f"USER_PERMISSION_{permission_key.upper()}_MATCH"
                        detail = f"该操作员的{label}权限与电子流登记一致。"
                    elif doc_enabled and not ef_enabled:
                        result = "MISMATCH"
                        severity = Severity.CRITICAL
                        manual = True
                        reason = f"USER_PERMISSION_{permission_key.upper()}_EXCEEDS_EFLOW"
                        detail = f"材料中出现该操作员的{label}权限，但电子流未登记该权限，建议优先复核是否存在权限超配。"
                    else:
                        result = "MISSING"
                        severity = Severity.WARNING
                        manual = True
                        reason = f"USER_PERMISSION_{permission_key.upper()}_MISSING"
                        detail = f"电子流登记该操作员需要{label}权限，但材料中未稳定识别到该权限，建议确认材料是否遗漏或抽取是否不完整。"
                    checks.append(CheckResult(
                        check_name=f"操作员({doc_u.user_name or matched_ef_u.user_name}){label}权限核对",
                        category="核心信息一致性检查",
                        field_group="permission",
                        field_name=f"permission_{permission_key}",
                        scenario_type=doc_ext.scenario_type,
                        check_mode="object_level_consistency",
                        source_a_label=f"EFlow用户权限-{label}",
                        source_a_value="需要" if ef_enabled else "未登记",
                        source_b_label=f"材料识别权限-{label}",
                        source_b_value="出现" if doc_enabled else "未稳定识别",
                        result=result,
                        severity=severity,
                        manual_confirmation_required=manual,
                        reason_code=reason,
                        detail=detail,
                        evidence=doc_u.permission_scope.raw_text,
                    ))

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
                if matched_ef_u.media.media_type or doc_u.media.media_type:
                    if matched_ef_u.media.media_type and doc_u.media.media_type:
                        matched = _is_name_match(matched_ef_u.media.media_type, doc_u.media.media_type)
                        _append_check(
                            checks,
                            check_name="介质类型核对",
                            field_group="media",
                            field_name="media_type",
                            source_a_label="EFlow介质类型",
                            source_a_value=matched_ef_u.media.media_type,
                            source_b_label="材料介质类型",
                            source_b_value=doc_u.media.media_type,
                            matched=matched,
                            reason_code="MEDIA_TYPE_MATCH" if matched else "MEDIA_TYPE_MISMATCH",
                            detail="介质类型一致。" if matched else "材料中的介质类型与电子流不一致，建议确认是 U盾、Token 还是数字证书。",
                            scenario_type=doc_ext.scenario_type,
                            manual=not matched,
                            severity=Severity.WARNING,
                        )
                    elif matched_ef_u.media.media_type and doc_ext.source_type in ["word", "pdf"]:
                        _append_check(
                            checks,
                            check_name="介质类型需要确认",
                            field_group="media",
                            field_name="media_type",
                            source_a_label="EFlow介质类型",
                            source_a_value=matched_ef_u.media.media_type,
                            source_b_label="材料介质类型",
                            source_b_value="未稳定识别",
                            matched=False,
                            reason_code="MEDIA_TYPE_NOT_EXTRACTED",
                            detail="电子流涉及介质办理，但材料中未稳定识别介质类型，建议确认是否申请/加挂了正确介质。",
                            scenario_type=doc_ext.scenario_type,
                            manual=True,
                            severity=Severity.WARNING,
                        )
                if (matched_ef_u.action_on_media or doc_u.action_on_media) and (_has_media_fact(matched_ef_u) or _has_media_fact(doc_u)):
                    ef_action = _clean_str(matched_ef_u.action_on_media)
                    doc_action = _clean_str(doc_u.action_on_media)
                    if ef_action and doc_action:
                        matched = ef_action == doc_action
                        _append_check(
                            checks,
                            check_name="介质办理动作核对",
                            field_group="media",
                            field_name="media_action",
                            source_a_label="EFlow介质办理要求",
                            source_a_value=matched_ef_u.action_on_media,
                            source_b_label="材料介质办理动作",
                            source_b_value=doc_u.action_on_media,
                            matched=matched,
                            reason_code="MEDIA_ACTION_MATCH" if matched else "MEDIA_ACTION_MISMATCH",
                            detail="介质办理动作一致。" if matched else "材料中的介质办理动作与电子流不一致，建议确认是新增、加挂、保留还是注销介质。",
                            scenario_type=doc_ext.scenario_type,
                            manual=not matched,
                            severity=Severity.WARNING,
                        )
                if matched_ef_u.media.media_quantity and doc_u.media.media_quantity:
                    matched = matched_ef_u.media.media_quantity == doc_u.media.media_quantity
                    _append_check(
                        checks,
                        check_name="介质数量核对",
                        field_group="media",
                        field_name="media_quantity",
                        source_a_label="EFlow介质数量",
                        source_a_value=str(matched_ef_u.media.media_quantity),
                        source_b_label="材料介质数量",
                        source_b_value=str(doc_u.media.media_quantity),
                        matched=matched,
                        reason_code="MEDIA_QUANTITY_MATCH" if matched else "MEDIA_QUANTITY_MISMATCH",
                        detail="介质数量一致。" if matched else "材料中的介质数量与电子流不一致，建议确认申请了几个介质。",
                        scenario_type=doc_ext.scenario_type,
                        manual=not matched,
                        severity=Severity.WARNING,
                    )

    return [
        tag_check(c, layer=CheckLayer.EFLOW_BASED, block=CheckBlock.A1_EXACT, confidence=1.0)
        for c in checks
    ]
