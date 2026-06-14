from backend.app.core.enums import DiffClassification
from backend.app.rules.normalization import normalize_text
from backend.app.schemas import DocumentDiff, MaterialPackage, TemplatePlus


class DiffClassifier:
    def classify(self, diff: DocumentDiff, package: MaterialPackage, template_plus: TemplatePlus) -> DiffClassification:
        submitted = normalize_text(diff.submitted_text)
        baseline = normalize_text(diff.baseline_text)
        eflow = package.eflow

        eflow_values = [
            eflow.applicant,
            eflow.company,
            eflow.account_name,
            eflow.account_number,
            eflow.platform,
        ]
        for user in eflow.users:
            eflow_values.extend([user.name, user.role, user.identity_doc_no])
            eflow_values.extend(user.permissions)
            eflow_values.extend(user.media)

        if any(normalize_text(value) and normalize_text(value) in submitted for value in eflow_values):
            if "admin approval" not in submitted and "above standard workflow" not in submitted:
                return DiffClassification.EFLOW_CHANGE

        fixed_values = [
            item.expected_value
            for item in template_plus.expected_contents
            if item.content_type == "fixed" and item.expected_value
        ]
        if diff.diff_type in {"deleted", "modified"} and any(normalize_text(value) in baseline for value in fixed_values):
            return DiffClassification.TEMPLATE_DEVIATION

        risk_terms = ["admin approval", "approve transactions", "above standard workflow", "extra user", "threshold"]
        if any(term in submitted for term in risk_terms):
            return DiffClassification.POTENTIAL_RISK

        if diff.diff_type == "added":
            return DiffClassification.UNKNOWN
        return DiffClassification.ACCEPTABLE_FILL

