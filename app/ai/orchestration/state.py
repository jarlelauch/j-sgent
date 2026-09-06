from enum import Enum


class TaskState(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    READY = "ready"
    WORKING = "working"
    VALIDATING = "validating"
    REWORK = "rework"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkState(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    WORKING = "working"
    SUBMITTED = "submitted"
    PASSED = "passed"
    REWORK = "rework"
    FAILED = "failed"


class OrbitState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
