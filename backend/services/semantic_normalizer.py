"""A2 semantic normalization checks backed by confirmed phrase mappings.

This module is intentionally lightweight. It does not replace the LLM semantic
review; it adds a deterministic first pass for high-frequency business phrases
that can be confirmed and maintained as configuration.
"""

import json
from pathlib import Path
from typing import Any

from backend.models.schemas import EFlowData, DocExtractedData, CheckResult, Severity
from backend.services.check_taxonomy import CheckBlock, CheckLayer, tag_check


RULE_PATH = Path(__file__).resolve().parent.parent / "rules" / "semantic_mappings.json"


def _load_rules() -> dict[str, Any]:
    try:
        return json.loads(RULE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[SemanticNormalizer] Failed to load semantic mappings: {exc}")
        return {}


def _norm_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def _infer_from_mapping(text: str, mapping: dict[str, list[str]]) -> tuple[str, str]:
    for normalized_value, phrases in mapping.items():
        for phrase in phrases:
            if phrase and _contains_phrase(text, phrase):
                return normalized_value, phrase
    return "", ""


def _doc_text(doc_ext: DocExtractedData) -> str:
    parts = [
        doc_ext.business_activity,
        doc_ext.scenario_type,
        doc_ext.action_type,
        doc_ext.action_summary,
        doc_ext.evidence_summary,
    ]
    for user in doc_ext.users:
        parts.extend([
            user.permission_sub_type,
            user.action_on_permission,
            user.action_on_media,
            user.permission_scope.raw_text,
            user.media.media_type,
            user.media.existing_media,
        ])
    return "\n".join(_norm_text(p) for p in parts if _norm_text(p))


def _eflow_text(eflow: EFlowData) -> str:
    parts = [eflow.business_type, eflow.business_scenario]
    for user in eflow.users:
        parts.extend([
            user.permission_sub_type,
            user.action_on_permission,
            user.action_on_media,
            user.permission_scope.raw_text,
            user.media.media_type,
            user.media.existing_media,
        ])
    return "\n".join(_norm_text(p) for p in parts if _norm_text(p))


def _combined_permission_scope(doc_ext: DocExtractedData, rules: dict[str, Any]) -> tuple[dict[str, bool], list[str]]:
    scope = {"authorize": False, "payment": False, "query": False, "upload": False}
    evidence: list[str] = []
    mapping = rules.get("permission_scope", {})
    for user in doc_ext.users:
        current = user.permission_scope
        for key in scope:
            if getattr(current, key, False):
                scope[key] = True
        raw_text = _norm_text(current.raw_text)
        for key, phrases in mapping.items():
            for phrase in phrases:
                if phrase and _contains_phrase(raw_text, phrase):
                    scope[key] = True
                    evidence.append(f"{phrase}->{key}")
    return scope, evidence


def _eflow_permission_scope(eflow: EFlowData) -> dict[str, bool]:
    scope = {"authorize": False, "payment": False, "query": False, "upload": False}
    for user in eflow.users:
        current = user.permission_scope
        for key in scope:
            if getattr(current, key, False):
                scope[key] = True
    return scope


def run_semantic_normalization_checks(eflow: EFlowData, doc_ext: DocExtractedData) -> list[CheckResult]:
    """Run deterministic A2 checks before the broader LLM semantic review."""
    rules = _load_rules()
    checks: list[CheckResult] = []

    scenario_map = rules.get("scenario", {})
    eflow_scenario, eflow_phrase = _infer_from_mapping(_eflow_text(eflow), scenario_map)
    doc_text = _doc_text(doc_ext)
    doc_scenario = (doc_ext.scenario_type or "").strip().upper()
    inferred_doc_scenario, doc_phrase = _infer_from_mapping(doc_text, scenario_map)
    if doc_scenario in ("", "UNKNOWN"):
        doc_scenario = inferred_doc_scenario

    if eflow_scenario and doc_scenario:
        if eflow_scenario == doc_scenario:
            checks.append(CheckResult(
                check_name="办理事项语义归一检查",
                category="业务要素核对",
                field_group="business_scenario",
                field_name="scenario_type",
                scenario_type=doc_scenario,
                check_mode="semantic_normalization",
                source_a_label="EFlow登记事项",
                source_a_value=eflow.business_scenario or eflow.business_type,
                source_b_label="文档语义识别",
                source_b_value=doc_ext.scenario_type or inferred_doc_scenario,
                result="MATCH",
                severity=Severity.PASS,
                reason_code="SCENARIO_SEMANTIC_MATCH",
                detail="文档办理事项与电子流登记事项语义一致。",
                evidence=f"EFlow命中:{eflow_phrase}; 文档命中:{doc_phrase}",
                confidence=0.9,
            ))
        else:
            checks.append(CheckResult(
                check_name="办理事项不一致",
                category="业务要素核对",
                field_group="business_scenario",
                field_name="scenario_type",
                scenario_type=doc_scenario,
                check_mode="semantic_normalization",
                source_a_label="EFlow登记事项",
                source_a_value=eflow.business_scenario or eflow.business_type,
                source_b_label="文档语义识别",
                source_b_value=doc_ext.scenario_type or inferred_doc_scenario,
                result="MISMATCH",
                severity=Severity.CRITICAL,
                manual_confirmation_required=True,
                reason_code="SCENARIO_SEMANTIC_MISMATCH",
                detail="电子流登记事项与文档表述的办理事项不一致，建议审核人重点复核。",
                evidence=f"EFlow命中:{eflow_phrase}; 文档命中:{doc_phrase}",
                confidence=0.85,
                requires_config_review=True,
            ))
    elif eflow_scenario and not doc_scenario and doc_ext.source_type in ("word", "pdf"):
        checks.append(CheckResult(
            check_name="办理事项需要确认",
            category="业务要素核对",
            field_group="business_scenario",
            field_name="scenario_type",
            check_mode="semantic_normalization",
            source_a_label="EFlow登记事项",
            source_a_value=eflow.business_scenario or eflow.business_type,
            source_b_label="文档语义识别",
            source_b_value="未稳定识别",
            result="MISSING",
            severity=Severity.WARNING,
            manual_confirmation_required=True,
            reason_code="SCENARIO_SEMANTIC_UNKNOWN",
            detail="文档中未稳定识别出办理事项，建议审核人结合材料标题和正文确认。",
            confidence=0.45,
            requires_config_review=True,
        ))

    if doc_ext.source_type in ("word", "pdf") and doc_ext.users:
        eflow_scope = _eflow_permission_scope(eflow)
        doc_scope, scope_evidence = _combined_permission_scope(doc_ext, rules)
        exceeded = [key for key, value in doc_scope.items() if value and not eflow_scope.get(key, False)]
        missing = [key for key, value in eflow_scope.items() if value and not doc_scope.get(key, False)]
        if exceeded:
            checks.append(CheckResult(
                check_name="权限范围超出电子流",
                category="业务要素核对",
                field_group="permission",
                field_name="permission_scope",
                scenario_type=doc_scenario or doc_ext.scenario_type,
                check_mode="semantic_normalization",
                source_a_label="EFlow登记权限",
                source_a_value=str(eflow_scope),
                source_b_label="文档识别权限",
                source_b_value=str(doc_scope),
                result="MISMATCH",
                severity=Severity.CRITICAL,
                manual_confirmation_required=True,
                reason_code="DOC_PERMISSION_SCOPE_EXCEEDS_EFLOW",
                detail="文档中识别到的权限范围超出电子流登记范围，建议重点复核权限范围。",
                evidence="; ".join(scope_evidence),
                confidence=0.8,
                requires_config_review=True,
            ))
        elif missing:
            checks.append(CheckResult(
                check_name="权限范围需要确认",
                category="业务要素核对",
                field_group="permission",
                field_name="permission_scope",
                scenario_type=doc_scenario or doc_ext.scenario_type,
                check_mode="semantic_normalization",
                source_a_label="EFlow登记权限",
                source_a_value=str(eflow_scope),
                source_b_label="文档识别权限",
                source_b_value=str(doc_scope),
                result="MISSING",
                severity=Severity.WARNING,
                manual_confirmation_required=True,
                reason_code="DOC_PERMISSION_SCOPE_MISSING",
                detail="电子流登记的部分权限未能在文档中稳定识别，建议审核人确认材料是否已完整说明。",
                evidence="; ".join(scope_evidence),
                confidence=0.65,
                requires_config_review=True,
            ))

    return [
        tag_check(
            check,
            layer=CheckLayer.EFLOW_BASED,
            block=CheckBlock.A2_SEMANTIC,
            confidence=check.confidence or None,
            requires_config_review=check.requires_config_review,
            requires_engineering_change=check.requires_engineering_change,
        )
        for check in checks
    ]
