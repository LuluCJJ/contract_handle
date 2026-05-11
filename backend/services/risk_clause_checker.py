"""B2 high-risk clause scanner."""

import json
from pathlib import Path
from typing import Any

from backend.models.schemas import CheckResult, DocExtractedData, Severity
from backend.services.check_taxonomy import CheckBlock, CheckLayer, TrafficLight, BusinessStatus, tag_check


RULE_PATH = Path(__file__).resolve().parent.parent / "rules" / "risk_clauses.json"


def _load_rules() -> dict[str, Any]:
    try:
        return json.loads(RULE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[RiskClauseChecker] Failed to load risk clause rules: {exc}")
        return {}


def _snippet(text: str, phrase: str, radius: int = 80) -> str:
    pos = text.find(phrase)
    if pos < 0:
        return phrase
    start = max(0, pos - radius)
    end = min(len(text), pos + len(phrase) + radius)
    return text[start:end].replace("\n", " ").strip()


def run_risk_clause_checks(doc_ext: DocExtractedData, document_text: str = "") -> list[CheckResult]:
    rules = _load_rules()
    text = "\n".join([document_text or "", doc_ext.raw_text or "", doc_ext.evidence_summary or ""])
    checks: list[CheckResult] = []
    seen: set[str] = set()
    for phrase in rules.get("high_risk_phrases", []):
        if phrase and phrase in text and phrase not in seen:
            seen.add(phrase)
            checks.append(tag_check(
                CheckResult(
                    check_name="高风险条款提示",
                    category="风险条款扫描",
                    field_group="risk_clause",
                    field_name="high_risk_phrase",
                    scenario_type=doc_ext.scenario_type,
                    check_mode="keyword_scan",
                    source_a_label="业务风险词库",
                    source_a_value=phrase,
                    source_b_label="材料原文",
                    source_b_value=_snippet(text, phrase),
                    result="REVIEW",
                    severity=Severity.CRITICAL,
                    manual_confirmation_required=True,
                    reason_code="HIGH_RISK_CLAUSE_FOUND",
                    detail=f"材料中出现“{phrase}”等高风险表述，请重点审核该条款是否符合业务接受范围。",
                    evidence=_snippet(text, phrase, radius=160),
                    confidence=0.95,
                    requires_config_review=True,
                ),
                layer=CheckLayer.DOCUMENT_ONLY,
                block=CheckBlock.B2_RISK_CLAUSE,
                traffic_light=TrafficLight.RED,
                business_status=BusinessStatus.REVIEW,
                requires_config_review=True,
            ))
    return checks
