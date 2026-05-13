"""B1 SOP checks for document-only compliance and business reasonableness.

These checks are intentionally conservative: they surface review points from
business SOPs without turning the demo into an approval/control gate.
"""

import json
import re
from pathlib import Path
from typing import Any

from backend.models.schemas import CheckResult, DocExtractedData, EFlowData, Severity
from backend.services.check_taxonomy import CheckBlock, CheckLayer, TrafficLight, BusinessStatus, tag_check


RULE_PATH = Path(__file__).resolve().parent.parent / "rules" / "sop_rules.json"


def _load_rules() -> dict[str, Any]:
    try:
        return json.loads(RULE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[SopChecker] Failed to load SOP rules: {exc}")
        return {}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _combined_text(doc_ext: DocExtractedData, document_text: str = "") -> str:
    parts = [
        document_text,
        doc_ext.raw_text,
        doc_ext.business_activity,
        doc_ext.scenario_type,
        doc_ext.action_type,
        doc_ext.action_summary,
        doc_ext.evidence_summary,
        doc_ext.company.name,
        doc_ext.company.cert_number,
    ]
    for person in doc_ext.persons:
        parts.extend([person.name, person.id_number, person.phone, person.department])
    for user in doc_ext.users:
        parts.extend([
            user.user_name,
            user.account_number,
            user.account_name,
            user.account_name_en,
            user.permission_sub_type,
            user.permission_scope.raw_text,
            user.media.media_type,
            user.media.media_number,
        ])
    return "\n".join(_text(p) for p in parts if _text(p).strip())


def _contains_any(text: str, phrases: list[str]) -> list[str]:
    lowered = text.lower()
    return [p for p in phrases if p and p.lower() in lowered]


def _placeholder_hits(text: str, phrases: list[str]) -> list[str]:
    hits: list[str] = []
    for phrase in phrases:
        if not phrase:
            continue
        if re.fullmatch(r"[A-Za-z0-9/]+", phrase):
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(phrase)}(?![A-Za-z0-9])", text, re.IGNORECASE):
                hits.append(phrase)
        elif phrase in text:
            hits.append(phrase)
    return hits


def _review_check(
    *,
    name: str,
    field_group: str,
    field_name: str,
    source_value: str,
    doc_value: str,
    reason_code: str,
    detail: str,
    evidence: str = "",
    severity: Severity = Severity.WARNING,
    red: bool = False,
) -> CheckResult:
    return tag_check(
        CheckResult(
            check_name=name,
            category="材料合规与合理性检查",
            field_group=field_group,
            field_name=field_name,
            check_mode="sop_review",
            source_a_label="业务SOP",
            source_a_value=source_value,
            source_b_label="材料扫描结果",
            source_b_value=doc_value,
            result="REVIEW",
            severity=severity,
            manual_confirmation_required=not red,
            reason_code=reason_code,
            detail=detail,
            evidence=evidence,
            confidence=0.72 if not red else 0.82,
        ),
        layer=CheckLayer.DOCUMENT_ONLY,
        block=CheckBlock.B1_SOP,
        traffic_light=TrafficLight.RED if red else TrafficLight.YELLOW,
        business_status=BusinessStatus.NEED_FIX if red else BusinessStatus.REVIEW,
        requires_config_review=True,
    )


def _pass_check(name: str, field_group: str, field_name: str, detail: str) -> CheckResult:
    return tag_check(
        CheckResult(
            check_name=name,
            category="材料合规与合理性检查",
            field_group=field_group,
            field_name=field_name,
            check_mode="sop_review",
            source_a_label="业务SOP",
            source_a_value="未发现明显异常",
            source_b_label="材料扫描结果",
            source_b_value="通过",
            result="MATCH",
            severity=Severity.PASS,
            reason_code=f"{field_name.upper()}_SOP_PASS",
            detail=detail,
            confidence=0.7,
        ),
        layer=CheckLayer.DOCUMENT_ONLY,
        block=CheckBlock.B1_SOP,
    )


def _infer_scenario(value: str) -> str:
    value_upper = value.upper()
    if "CANCEL" in value_upper or any(w in value for w in ["注销", "取消", "撤销", "停用", "停止使用", "关闭权限", "Terminate", "Cancel"]):
        return "CANCEL"
    if "OPEN" in value_upper or any(w in value for w in ["开通", "开立", "新增", "启用", "申请", "办理", "加挂", "issuance", "new"]):
        return "OPEN"
    if "MODIFY" in value_upper or any(w in value for w in ["变更", "修改", "维护", "更改服务", "调整"]):
        return "MODIFY"
    return ""


def _scenario_evidence_text(doc_ext: DocExtractedData) -> str:
    """Use extracted intent evidence instead of scanning the whole template."""
    parts = [
        doc_ext.business_activity,
        doc_ext.scenario_type,
        doc_ext.action_type,
        doc_ext.action_summary,
        doc_ext.evidence_summary,
    ]
    for user in doc_ext.users:
        parts.extend([user.action_on_permission, user.action_on_media])
    return "\n".join(_text(p) for p in parts if _text(p).strip())


def _is_hard_scenario_conflict(eflow_scenario: str, doc_scenario: str) -> bool:
    if not eflow_scenario or not doc_scenario or eflow_scenario == doc_scenario:
        return False
    # 维护/变更表格经常承载新增用户、加挂介质或权限配置，不能只因
    # MODIFY 与 OPEN/CANCEL 不同就判断为实质冲突。
    if "MODIFY" in {eflow_scenario, doc_scenario}:
        return False
    return True


def run_sop_checks(eflow: EFlowData, doc_ext: DocExtractedData, document_text: str = "") -> list[CheckResult]:
    rules = _load_rules()
    text = _combined_text(doc_ext, document_text)
    checks: list[CheckResult] = []

    placeholders = _placeholder_hits(text, rules.get("placeholder_tokens", []))
    if placeholders:
        checks.append(_review_check(
            name="必填信息完整性复核",
            field_group="compliance",
            field_name="required_fields",
            source_value="申请材料中的必填项不应为空白、占位符或待填内容",
            doc_value="、".join(placeholders[:6]),
            reason_code="DOC_PLACEHOLDER_FOUND",
            detail="材料中出现疑似占位或待补充内容，建议确认必填信息是否已经完整填写。",
            evidence="、".join(placeholders),
        ))
    elif doc_ext.source_type in ("word", "pdf"):
        checks.append(_pass_check("必填信息完整性复核", "compliance", "required_fields", "未发现明显占位符或待填内容。"))

    phone_candidates = re.findall(
        r"(?:手机|电话|联系电话|手机号|Phone|Mobile|Tel)[^\d]{0,12}(\d{5,13})",
        text,
        flags=re.IGNORECASE,
    )
    invalid_phone = [p for p in phone_candidates if len(p) != 11]
    if invalid_phone:
        checks.append(_review_check(
            name="联系方式格式复核",
            field_group="compliance",
            field_name="phone_format",
            source_value="中国大陆手机号通常为11位数字",
            doc_value="、".join(invalid_phone[:5]),
            reason_code="PHONE_FORMAT_REVIEW",
            detail="材料中存在疑似手机号但位数不符合常见格式，建议人工确认联系方式。",
            evidence="、".join(invalid_phone[:10]),
        ))

    employee_ids = re.findall(
        r"(?:工号|员工号|Employee\s*ID|Staff\s*ID)[^\d]{0,12}(\d{4,12})",
        text,
        flags=re.IGNORECASE,
    )
    abnormal_employee_ids = [v for v in employee_ids if len(v) != 8]
    if abnormal_employee_ids:
        checks.append(_review_check(
            name="工号格式复核",
            field_group="compliance",
            field_name="employee_id_format",
            source_value="公司工号通常应为8位纯数字",
            doc_value="、".join(abnormal_employee_ids[:5]),
            reason_code="EMPLOYEE_ID_FORMAT_REVIEW",
            detail="材料中存在疑似工号但不符合8位数字规则，建议确认是否为工号或其他编号。",
            evidence="、".join(abnormal_employee_ids[:10]),
        ))

    eflow_scenario = _infer_scenario(f"{eflow.business_type} {eflow.business_scenario}")
    scenario_evidence = _scenario_evidence_text(doc_ext)
    explicit_doc_scenario = (doc_ext.scenario_type or "").strip().upper()
    doc_scenario = explicit_doc_scenario if explicit_doc_scenario in {"OPEN", "CANCEL", "MODIFY"} else _infer_scenario(scenario_evidence)
    conflict_words = rules.get("business_conflicts", {}).get(eflow_scenario, []) if eflow_scenario else []
    hits = _contains_any(scenario_evidence, conflict_words)
    if _is_hard_scenario_conflict(eflow_scenario, doc_scenario):
        checks.append(_review_check(
            name="办理事项实质冲突复核",
            field_group="business_scenario",
            field_name="scenario_conflict",
            source_value=f"EFlow登记场景：{eflow_scenario}",
            doc_value=f"材料识别场景：{doc_scenario}",
            reason_code="BUSINESS_SUBSTANCE_CONFLICT",
            detail="材料抽取出的办理方向与电子流登记方向相反，建议确认材料描述是否与本次办理事项一致。",
            evidence=scenario_evidence,
            red=True,
        ))
    elif eflow_scenario and hits and not doc_scenario:
        checks.append(_review_check(
            name="办理事项表述需要确认",
            field_group="business_scenario",
            field_name="scenario_conflict",
            source_value=f"EFlow登记场景：{eflow_scenario}",
            doc_value="、".join(hits[:6]),
            reason_code="BUSINESS_SUBSTANCE_REVIEW",
            detail="材料场景未稳定识别，但抽取证据中出现可能与电子流方向相反的表述，建议人工确认。",
            evidence=scenario_evidence,
            severity=Severity.WARNING,
            red=False,
        ))
    elif eflow_scenario and doc_scenario:
        checks.append(_pass_check("办理事项合理性复核", "business_scenario", "scenario_consistency", "未发现与电子流办理方向明显相反的表述。"))

    for user in doc_ext.users:
        scope = user.permission_scope
        if scope.authorize and scope.payment:
            checks.append(_review_check(
                name="权限组合合理性复核",
                field_group="permission",
                field_name="permission_conflict",
                source_value="同一操作员不宜同时具备授权和支付等高敏权限",
                doc_value=f"{user.user_name or '未识别用户'} 同时包含授权和支付",
                reason_code="AUTHORIZE_PAYMENT_COMBINATION_REVIEW",
                detail="材料中同一操作员疑似同时申请授权和支付权限，建议结合岗位职责和业务需要重点复核。",
                evidence=scope.raw_text,
                severity=Severity.WARNING,
            ))
        has_limit = bool(user.single_limit or user.daily_limit)
        has_currency = bool(_contains_any(text, rules.get("currency_tokens", [])))
        if has_limit and not has_currency:
            checks.append(_review_check(
                name="权限限额币种复核",
                field_group="permission",
                field_name="limit_currency",
                source_value="涉及限额时应明确币种单位",
                doc_value=f"single={user.single_limit}, daily={user.daily_limit}",
                reason_code="LIMIT_CURRENCY_MISSING",
                detail="材料中识别到权限限额，但未稳定识别到币种单位，建议确认金额单位是否完整。",
                evidence=user.permission_scope.raw_text,
            ))

    allowed_suffixes = rules.get("allowed_email_suffixes", [])
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if allowed_suffixes:
        abnormal_emails = [email for email in emails if not any(email.lower().endswith(s.lower()) for s in allowed_suffixes)]
        if abnormal_emails:
            checks.append(_review_check(
                name="邮箱后缀复核",
                field_group="subject",
                field_name="email_suffix",
                source_value="用户邮箱应使用公司统一后缀",
                doc_value="、".join(abnormal_emails[:5]),
                reason_code="EMAIL_SUFFIX_REVIEW",
                detail="材料中存在非配置范围内的邮箱后缀，建议确认是否为公司邮箱。",
                evidence="、".join(abnormal_emails[:10]),
            ))

    return checks
