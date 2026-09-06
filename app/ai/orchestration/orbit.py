from dataclasses import dataclass, field
from enum import Enum

from .work_unit import WorkUnit


class OrbitMode(str, Enum):

    SERIAL = "serial"

    PARALLEL = "parallel"

    COMPETITION = "competition"

    DEBATE = "debate"

    VALIDATION = "validation"


class OrbitState(str, Enum):

    PENDING = "pending"

    ACTIVE = "active"

    PASSED = "passed"

    REWORK = "rework"

    FAILED = "failed"

    SKIPPED = "skipped"


@dataclass
class Orbit:

    name: str

    order: int

    mode: OrbitMode

    worker_role: str

    min_workers: int = 1

    max_workers: int = 1

    require_independent_review: bool = False

    allow_rework: bool = True

    state: OrbitState = OrbitState.PENDING

    work_units: list[WorkUnit] = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )

    def add_work(self, work):

        self.work_units.append(work)

    def activate(self):

        self.state = OrbitState.ACTIVE

    def passed(self):

        self.state = OrbitState.PASSED

    def request_rework(self):

        self.state = OrbitState.REWORK

    def failed(self):

        self.state = OrbitState.FAILED

    def complete(self):

        if not self.work_units:
            return False

        return all(
            work.state.value == "passed"
            for work in self.work_units
        )

    def progress(self):

        if not self.work_units:
            return 0.0

        completed = sum(
            work.state.value == "passed"
            for work in self.work_units
        )

        return completed / len(
            self.work_units
        )
