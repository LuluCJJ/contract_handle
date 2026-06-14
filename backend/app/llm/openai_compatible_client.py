import json
import re
import time
import urllib.error
import urllib.request


class OpenAICompatibleClient:
    provider_name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.calls = 0
        self.max_retries = 2

    def judge_json(self, task: str, payload: dict) -> dict:
        self.calls += 1
        body = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You are a controlled bank document preaudit assistant. Return JSON only.",
                },
                {
                    "role": "user",
                    "content": json.dumps({"task": task, "payload": payload}, ensure_ascii=False),
                },
            ],
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        data = self._post_with_retry(req)
        content = data["choices"][0]["message"]["content"]
        return self._normalize_result(self._parse_json_content(content))

    def _post_with_retry(self, req: urllib.request.Request) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError:
                raise
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(0.8 * (attempt + 1))
        raise last_error or RuntimeError("LLM request failed without an error")

    def _parse_json_content(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.S)
            if not match:
                raise
            return json.loads(match.group(0))

    def _normalize_result(self, result: dict) -> dict:
        if "status" in result and "risk_level" in result and "summary" in result:
            return result

        audit = result.get("audit_result") if isinstance(result.get("audit_result"), dict) else {}
        diff = result.get("diff_analysis") if isinstance(result.get("diff_analysis"), dict) else {}

        raw_status = str(
            audit.get("status")
            or result.get("status")
            or self._find_first(result, ["automated_decision", "decision", "action"])
            or ""
        ).lower()
        raw_risk = str(
            audit.get("risk_level")
            or diff.get("severity")
            or result.get("risk_level")
            or self._find_first(result, ["risk_level", "severity", "risk"])
            or "medium"
        ).lower()
        classification = (
            audit.get("classification")
            or audit.get("violation_type")
            or diff.get("risk_classification")
            or result.get("risk_type")
            or result.get("explanation_type")
            or result.get("classification")
            or self._find_first(result, ["risk_type", "risk_classification", "violation_type", "classification"])
            or "unknown"
        )

        if raw_status in {"pass", "passed", "ok", "approved"}:
            status = "pass"
        elif raw_status in {"fail", "failed", "reject", "rejected"}:
            status = "need_confirm"
        elif raw_status in {"warning", "warn"}:
            status = "warning"
        else:
            status = "need_confirm"

        if raw_risk in {"critical", "high"}:
            risk_level = "high"
        elif raw_risk in {"low", "minor"}:
            risk_level = "low"
        else:
            risk_level = "medium"

        summary = (
            audit.get("summary")
            or audit.get("explanation")
            or diff.get("rationale")
            or result.get("summary")
            or result.get("explanation")
            or self._find_first(result, ["summary", "explanation", "rationale", "analysis", "justification"])
            or "模型返回了非标准结构，已转为人工确认项。"
        )
        recommendation = result.get("recommendation")
        if isinstance(recommendation, dict):
            recommendation_text = recommendation.get("action") or recommendation.get("justification") or str(recommendation)
        else:
            recommendation_text = recommendation
        recommendations = result.get("recommendations")
        if isinstance(recommendations, list):
            recommendations_text = "；".join(str(item) for item in recommendations[:3])
        else:
            recommendations_text = recommendations
        suggested_action = (
            audit.get("suggested_action")
            or audit.get("recommendation")
            or recommendation_text
            or recommendations_text
            or self._find_first(result, ["suggested_action", "recommendation", "recommendations", "required_steps"])
            or result.get("suggested_action")
            or "请审核人结合证据人工确认。"
        )

        normalized = {
            "status": status,
            "risk_level": risk_level,
            "classification": classification,
            "summary": summary,
            "reasoning_brief": audit.get("reasoning_brief") or diff.get("rationale") or "",
            "evidence_refs": result.get("evidence_refs", []),
            "manual_confirm_required": status != "pass",
            "manual_confirm_question": result.get("manual_confirm_question", ""),
            "suggested_action": suggested_action,
            "raw_model_result": result,
        }
        return normalized

    def _find_first(self, value, keys: list[str]):
        if isinstance(value, dict):
            for key in keys:
                if key in value and value[key]:
                    found = value[key]
                    if isinstance(found, list):
                        return "；".join(str(item) for item in found[:3])
                    if isinstance(found, dict):
                        return self._dict_preview(found)
                    return found
            for nested in value.values():
                found = self._find_first(nested, keys)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = self._find_first(item, keys)
                if found:
                    return found
        return None

    def _dict_preview(self, value: dict) -> str:
        parts = []
        for key, item in value.items():
            if isinstance(item, (str, int, float, bool)):
                parts.append(f"{key}: {item}")
            elif isinstance(item, list):
                parts.append(f"{key}: {'；'.join(str(x) for x in item[:3])}")
            if len(parts) >= 3:
                break
        return "；".join(parts) if parts else str(value)
