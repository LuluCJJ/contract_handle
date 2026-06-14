from backend.app.core.enums import CheckStatus, RiskLevel, StrategyName
from backend.app.rules.normalization import contains_all, line_value, normalize_activity, normalize_text, parse_amount
from backend.app.schemas import CheckResult, Evidence, MaterialPackage, TemplateBlock


class RuleEngine:
    def run_block_rule(
        self,
        package: MaterialPackage,
        strategy: StrategyName,
        block: TemplateBlock,
        extracted: str,
        evidence: Evidence,
    ) -> CheckResult:
        expected = self._resolve_expected(package, block.expected_eflow_path)
        status = CheckStatus.PASS
        risk = RiskLevel.LOW
        manual_confirm = False
        action = "无需处理"

        if block.check_type == "normalized_match":
            passed = normalize_text(str(expected)) == normalize_text(extracted)
        elif block.check_type == "contains_all":
            values = expected if isinstance(expected, list) else [str(expected)]
            passed = contains_all(extracted, values)
        elif block.check_type == "activity_match":
            passed = normalize_activity(str(expected)) == normalize_activity(extracted)
        elif block.check_type == "count_match":
            passed = str(expected) == normalize_text(extracted)
        elif block.check_type == "max_limit_review":
            extracted_amount = parse_amount(extracted)
            expected_amount = float(expected or 0)
            passed = extracted_amount == expected_amount and extracted_amount <= 5_000_000
        else:
            passed = bool(extracted.strip())

        if not passed:
            status = CheckStatus.NEED_CONFIRM if block.ai_required else CheckStatus.FAIL
            risk = RiskLevel.MEDIUM
            manual_confirm = True
            action = "请核对电子流与申请材料填写是否一致"
            if block.check_type == "max_limit_review":
                status = CheckStatus.WARNING
                risk = RiskLevel.HIGH
                action = "请审核人确认高限额是否有额外授权依据"

        return CheckResult(
            result_id=f"CHK-{block.block_id}",
            package_id=package.package_id,
            strategy=strategy,
            check_item=block.block_name,
            status=status,
            risk_level=risk,
            summary=f"{block.block_name}：{'与电子流一致' if passed else '与电子流不完全一致'}",
            evidence_ids=[evidence.evidence_id],
            owner="config",
            manual_confirm_required=manual_confirm,
            suggested_action=action,
            details={"expected": expected, "extracted": extracted, "instruction": block.fill_instruction},
        )

    def extract_block_text(self, document_text: str, block: TemplateBlock) -> str:
        return line_value(document_text, block.anchor_text)

    def _resolve_expected(self, package: MaterialPackage, path: str | None):
        if not path:
            return ""
        if path == "users_count":
            return len(package.eflow.users)
        if path == "activity":
            return package.eflow.activity
        if path == "account_number":
            return package.eflow.account_number
        if path.startswith("users."):
            parts = path.split(".")
            if len(parts) < 3:
                return ""
            index = int(parts[1])
            field = parts[2]
            user = package.eflow.users[index]
            return getattr(user, field, "")
        return ""
