class MockLLMClient:
    provider_name = "mock"

    def __init__(self) -> None:
        self.calls = 0

    def judge_json(self, task: str, payload: dict) -> dict:
        self.calls += 1
        text = str(payload).lower()
        if "admin approval" in text or "above standard workflow" in text:
            return {
                "status": "need_confirm",
                "risk_level": "high",
                "classification": "potential_risk",
                "summary": "发现额外审批权限或超标准授权描述，建议人工确认。",
                "reasoning_brief": "该内容超出电子流中的 payment/query 权限范围。",
                "manual_confirm_required": True,
                "manual_confirm_question": "请确认本次申请是否允许新增 admin approval 或超标准审批权限。",
                "suggested_action": "请业务审核人核对权限范围和授权依据。",
            }
        return {
            "status": "pass",
            "risk_level": "low",
            "classification": "acceptable_fill",
            "summary": "未发现明显超出输入证据的风险。",
            "reasoning_brief": "输入内容与电子流或模板约束未出现明显冲突。",
            "manual_confirm_required": False,
            "manual_confirm_question": "",
            "suggested_action": "无需处理。",
        }

