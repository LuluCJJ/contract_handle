"""Build business-facing check points from low-level check results."""

from __future__ import annotations

from typing import Any

from backend.models.schemas import (
    CheckPoint,
    CheckPointEvidence,
    CheckResult,
    DocAnalysisReport,
    Severity,
)


CHECK_POINT_DEFS = {
    "platform": ("网银平台", 10),
    "business_type": ("办理事项", 20),
    "permission_scope": ("权限范围", 30),
    "media": ("网银介质", 40),
    "account_name": ("账户名称", 50),
    "account_number": ("账户账号", 55),
    "identity_number": ("证件号码", 60),
    "identity_name": ("操作员身份", 65),
    "document_compliance": ("填写规范", 80),
    "risk_clause": ("风险条款/敏感词", 90),
}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _check_point_key(check: CheckResult) -> str:
    group = (check.field_group or "").lower()
    name = (check.field_name or "").lower()
    code = (check.reason_code or "").upper()
    block = (check.check_block or "").upper()

    if block == "B2_RISK_CLAUSE":
        return "risk_clause"
    if group == "platform" or "platform" in name or "BANK_PLATFORM" in code or "BANK_BRANCH" in code:
        return "platform"
    if group == "business_scenario" or "SCENARIO" in code or "ACTION" in code:
        return "business_type"
    if group == "permission" or "permission" in name or "PERMISSION" in code or "SCOPE" in code:
        return "permission_scope"
    if group == "media" or "media" in name or "TOKEN" in code:
        return "media"
    if group == "account" and ("account_name" in name or "ACCOUNT_NAME" in code):
        return "account_name"
    if group == "account" or "account" in name or "ACCOUNT" in code:
        return "account_number"
    if "id" in name or "ID_NUMBER" in code or code.startswith("ID_"):
        return "identity_number"
    if group == "subject" or "USER_" in code or "PERSON" in code or "WHITELIST" in code or "applicant" in name:
        return "identity_name"
    if group == "compliance":
        return "document_compliance"
    return f"supplement_{group or name or code or 'other'}"


def _traffic_rank(light: str) -> int:
    return {"RED": 0, "YELLOW": 1, "GREEN": 2}.get((light or "").upper(), 3)


def _severity_from_light(light: str) -> Severity:
    if light == "RED":
        return Severity.CRITICAL
    if light == "YELLOW":
        return Severity.WARNING
    return Severity.PASS


def _worst_light(checks: list[CheckResult]) -> str:
    lights = [(c.traffic_light or "").upper() for c in checks]
    if "RED" in lights:
        return "RED"
    if "YELLOW" in lights:
        return "YELLOW"
    return "GREEN"


def _format_value(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, dict):
        enabled = []
        labels = {
            "authorize": "授权/复核",
            "payment": "支付/转账",
            "query": "查询",
            "upload": "上传/导入",
        }
        for key, label in labels.items():
            if value.get(key) is True:
                enabled.append(label)
        if enabled or any(key in value for key in labels):
            return "、".join(enabled) if enabled else "未包含授权/支付/查询/上传权限"
    return str(value)


def _side_value(checks: list[CheckResult], side: str) -> str:
    display_checks = _display_checks(checks)
    values: list[str] = []
    for check in display_checks:
        label = check.source_a_label if side == "a" else check.source_b_label
        value = check.source_a_value if side == "a" else check.source_b_value
        formatted = _format_value(value)
        if not formatted:
            continue
        text = f"{label}：{formatted}" if label else formatted
        if text not in values:
            values.append(text)
    if not values:
        return "电子流未提供可展示值" if side == "a" else "材料未稳定识别可展示值"
    return "\n".join(values[:6])


def _display_checks(checks: list[CheckResult]) -> list[CheckResult]:
    active = [c for c in checks if (c.traffic_light or "").upper() != "GREEN"]
    return active or checks


def _permission_label(check: CheckResult) -> str:
    text = f"{check.field_name} {check.reason_code} {check.check_name}"
    if "AUTHORIZE" in text or "授权" in text or "复核" in text:
        return "授权/复核"
    if "PAYMENT" in text or "支付" in text or "转账" in text or "付款" in text:
        return "支付/转账"
    if "QUERY" in text or "查询" in text:
        return "查询"
    if "UPLOAD" in text or "上传" in text or "上载" in text:
        return "上传/导入"
    return check.check_name


def _summary_for(key: str, checks: list[CheckResult], light: str) -> str:
    active = [c for c in checks if (c.traffic_light or "").upper() != "GREEN"]
    base = active or checks
    if key == "permission_scope" and active:
        labels = []
        for check in active:
            label = _permission_label(check)
            if label not in labels:
                labels.append(label)
        return f"权限范围按授权、支付、查询、上传拆分核对；当前需关注：{'、'.join(labels)}。"
    if key == "identity_name":
        return "人员身份相关核对已合并展示，包含操作员、申请人或证件持有人与电子流人员池的匹配情况。"
    if light == "GREEN":
        return "该检查点按当前规则未发现明显不一致。"
    details = []
    for check in base[:4]:
        detail = _text(check.detail)
        if detail and detail not in details:
            details.append(detail)
    return "；".join(details) if details else "该检查点需要业务人员复核。"


def _suggestion_for(light: str, key: str) -> str:
    if light == "GREEN":
        return "可作为已检查底稿保留"
    if light == "RED":
        return "建议优先核实并补充/修正"
    if key in {"permission_scope", "media", "business_type"}:
        return "建议人工确认后再按原流程办理"
    return "建议审核人结合材料确认"


def _evidence_items(doc_name: str, doc_type: str, checks: list[CheckResult]) -> list[CheckPointEvidence]:
    items: list[CheckPointEvidence] = []
    for check in checks:
        items.append(CheckPointEvidence(
            doc_name=doc_name,
            doc_type=doc_type,
            check_name=check.check_name,
            traffic_light=check.traffic_light,
            reason_code=check.reason_code,
            source_a_label=check.source_a_label,
            source_a_value=str(check.source_a_value or ""),
            source_b_label=check.source_b_label,
            source_b_value=str(check.source_b_value or ""),
            evidence=check.evidence,
            detail=check.detail,
            field_group=check.field_group,
            field_name=check.field_name,
            check_block=check.check_block,
            check_mode=check.check_mode,
        ))
    return items


def build_check_points(
    document_reports: list[DocAnalysisReport],
    cross_checks: list[CheckResult] | None = None,
) -> list[CheckPoint]:
    buckets: dict[str, list[tuple[str, str, CheckResult]]] = {}
    for doc in document_reports:
        for check in [*doc.hard_checks, *doc.semantic_checks]:
            key = _check_point_key(check)
            buckets.setdefault(key, []).append((doc.doc_name, doc.doc_type, check))
    for check in cross_checks or []:
        key = _check_point_key(check)
        buckets.setdefault(key, []).append(("跨文档检查", "cross_validation", check))

    points: list[CheckPoint] = []
    for key, entries in buckets.items():
        title, order = CHECK_POINT_DEFS.get(key, ("补充检查", 99))
        checks = [check for _, _, check in entries]
        checks.sort(key=lambda c: (_traffic_rank(c.traffic_light), c.reason_code, c.check_name))
        light = _worst_light(checks)
        doc_names = []
        evidence_snippets = []
        evidence_rows: list[CheckPointEvidence] = []
        for doc_name, doc_type, check in entries:
            if check not in _display_checks(checks):
                continue
            if doc_name and doc_name not in doc_names:
                doc_names.append(doc_name)
            snippet = _text(check.evidence or check.source_b_value or check.detail)
            if snippet and snippet not in evidence_snippets:
                evidence_snippets.append(snippet)
            evidence_rows.extend(_evidence_items(doc_name, doc_type, [check]))

        points.append(CheckPoint(
            key=key,
            title=title,
            order=order,
            traffic_light=light,
            severity=_severity_from_light(light),
            business_status="PASS" if light == "GREEN" else ("REVIEW" if light == "YELLOW" else "NEED_FIX"),
            summary=_summary_for(key, checks, light),
            suggestion=_suggestion_for(light, key),
            source_a_value=_side_value(checks, "a"),
            source_b_value=_side_value(checks, "b"),
            doc_names=doc_names,
            evidence_snippets=evidence_snippets[:6],
            evidence_items=evidence_rows,
        ))

    points.sort(key=lambda p: (_traffic_rank(p.traffic_light), p.order, p.title))
    return points
