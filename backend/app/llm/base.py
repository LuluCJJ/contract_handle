from typing import Protocol


class LLMClient(Protocol):
    provider_name: str
    calls: int

    def judge_json(self, task: str, payload: dict) -> dict:
        ...

