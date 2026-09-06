from dataclasses import dataclass, field

from .orbit import Orbit
from .state import TaskState
from .work_unit import WorkUnit


@dataclass
class Task:

    objective: str

    id: str = field(
        default_factory=lambda: __import__(
            "uuid"
        ).uuid4().hex[:12]
    )

    state: TaskState = TaskState.CREATED

    orbits: list[Orbit] = field(
        default_factory=list
    )

    current_orbit: int = 0

    history: list[dict] = field(
        default_factory=list
    )

    def add_orbit(self, orbit: Orbit):

        self.orbits.append(orbit)

        self.orbits.sort(
            key=lambda item: item.order
        )

    def current(self):

        if self.current_orbit >= len(
            self.orbits
        ):
            return None

        return self.orbits[
            self.current_orbit
        ]

    def advance(self):

        current = self.current()

        if current:

            self.history.append({
                "orbit": current.name,
                "state": current.state.value,
            })

        self.current_orbit += 1

        if self.current_orbit >= len(
            self.orbits
        ):

            self.state = TaskState.COMPLETED

        else:

            self.state = TaskState.READY


class OrbitController:

    def __init__(
        self,
        scheduler,
        validator,
    ):

        self.scheduler = scheduler
        self.validator = validator

    def build_default_orbits(self):

        return [

            Orbit(
                name="decompose",
                order=0,
                worker_role="planner",
            ),

            Orbit(
                name="plan",
                order=1,
                worker_role="planner",
            ),

            Orbit(
                name="execute",
                order=2,
                worker_role="executor",
                validator_role="validator",
            ),

            Orbit(
                name="verify",
                order=3,
                worker_role="validator",
            ),

            Orbit(
                name="synthesize",
                order=4,
                worker_role="synthesizer",
            ),

            Orbit(
                name="final_verify",
                order=5,
                worker_role="validator",
            ),

        ]

    def create_task(self, objective):

        task = Task(
            objective=objective
        )

        for orbit in self.build_default_orbits():

            task.add_orbit(orbit)

        return task

    def assign_work(
        self,
        work: WorkUnit,
    ):

        return self.scheduler.assign(work)

    def validate_work(
        self,
        work: WorkUnit,
    ):

        return self.validator.validate(work)
