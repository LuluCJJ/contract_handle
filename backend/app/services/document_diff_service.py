from backend.app.schemas import DocumentDiff


class DocumentDiffService:
    def diff_text(self, baseline_text: str, submitted_text: str) -> list[DocumentDiff]:
        baseline_lines = self._to_map(baseline_text)
        submitted_lines = self._to_map(submitted_text)
        diffs: list[DocumentDiff] = []

        for key, baseline_value in baseline_lines.items():
            submitted_value = submitted_lines.get(key)
            if submitted_value is None:
                diffs.append(
                    DocumentDiff(
                        diff_id=f"DIFF-DEL-{len(diffs)+1}",
                        diff_type="deleted",
                        baseline_text=f"{key}: {baseline_value}",
                        submitted_text="",
                    )
                )
            elif submitted_value != baseline_value:
                diffs.append(
                    DocumentDiff(
                        diff_id=f"DIFF-MOD-{len(diffs)+1}",
                        diff_type="modified",
                        baseline_text=f"{key}: {baseline_value}",
                        submitted_text=f"{key}: {submitted_value}",
                    )
                )

        for key, submitted_value in submitted_lines.items():
            if key not in baseline_lines:
                diffs.append(
                    DocumentDiff(
                        diff_id=f"DIFF-ADD-{len(diffs)+1}",
                        diff_type="added",
                        baseline_text="",
                        submitted_text=f"{key}: {submitted_value}",
                    )
                )
        return diffs

    def _to_map(self, text: str) -> dict[str, str]:
        result = {}
        for line in text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
            elif line.strip():
                result[line.strip()] = ""
        return result

