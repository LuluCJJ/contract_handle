from typing import Protocol

from backend.app.schemas import MaterialPackage, ReviewReport, Scenario


class PreauditStrategy(Protocol):
    strategy_name: str

    def run(self, package: MaterialPackage, scenario: Scenario) -> ReviewReport:
        ...

