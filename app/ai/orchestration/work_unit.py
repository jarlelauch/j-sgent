from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from typing import Any


class WorkState(str, Enum):

    PENDING = "pending"
    ASSIGNED = "assigned"
    WORKING = "working"
    SUBMITTED = "submitted"
    VALIDATING = "validating"
    PASSED = "passed"
    REWORK = "rework"
    FAILED = "failed"


@dataclass
class WorkUnit:

    objective: str

    role: str

    expected_output: str

    required_capabilities: set[str] = field(
        default_factory=set
    )

    id: str = field(
        default_factory=lambda:
        uuid4().hex[:12]
    )

    state: WorkState = WorkState.PENDING

    assigned_provider: str | None = None

    input_data: dict[str, Any] = field(
        default_factory=dict
    )

    output: Any = None

    evidence: list[str] = field(
        default_factory=list
    )

    validation_score: float = 0.0

    attempts: int = 0

    max_attempts: int = 3

    priority: float = 0.5

    dependencies: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def ready(self, completed_ids):

        return (
            self.state == WorkState.PENDING
            and all(
                dependency in completed_ids
                for dependency in self.dependencies
            )
        )

    def assign(self, provider):

        self.assigned_provider = provider
        self.state = WorkState.ASSIGNED

    def start(self):

        if self.state not in {
            WorkState.ASSIGNED,
            WorkState.REWORK,
        }:
            raise RuntimeError(
                f"Work unit {self.id} cannot start "
                f"from state {self.state.value}"
            )

        self.attempts += 1
        self.state = WorkState.WORKING

    def submit(self, output):

        self.output = output
        self.state = WorkState.SUBMITTED

    def begin_validation(self):

        self.state = WorkState.VALIDATING

    def pass_validation(self, score):

        self.validation_score = score
        self.state = WorkState.PASSED

    def request_rework(self):

        if self.attempts >= self.max_attempts:
            self.state = WorkState.FAILED
        else:
            self.state = WorkState.REWORK
