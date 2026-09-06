from dataclasses import dataclass, field

from .mode import (
    AgentMode,
    get_policy,
)

from .research import ResearchEngine
from .rotation import RotationScheduler


@dataclass
class OrbitRecord:

    index: int

    purpose: str

    provider: str | None = None

    output: str = ""

    confidence: float = 0.0

    metadata: dict = field(
        default_factory=dict
    )


@dataclass
class OrbitalState:

    objective: str

    mode: AgentMode

    core_answer: str = ""

    confidence: float = 0.0

    orbit_count: int = 0

    history: list[OrbitRecord] = field(
        default_factory=list
    )

    evidence: list[dict] = field(
        default_factory=list
    )

    open_questions: list[str] = field(
        default_factory=list
    )


class OrbitalEngine:

    def __init__(self, router, memory=None):

        self.router = router

        self.memory = memory

        self.rotation = (
            RotationScheduler(
                router
            )
        )

        self.research = (
            ResearchEngine()
        )

    def _memory_context(
        self,
        objective,
        budget,
    ):

        if not self.memory:
            return ""

        try:
            if hasattr(self.memory, "recall"):
                return self.memory.recall(
                    objective,
                    budget=budget,
                ) or ""

            if hasattr(self.memory, "search"):
                out = []
                for r in self.memory.search(
                    objective[:20]
                )[:2]:
                    out.append(
                        (r.get("content") or "")[:600]
                    )
                return "\n\n".join(out)[-budget:]
        except Exception:
            pass

        return ""

    def _purpose(
        self,
        mode,
        orbit,
    ):

        if mode == AgentMode.FAST:

            return "direct_solve"

        if mode == AgentMode.NORMAL:

            sequence = [
                "decompose",
                "solve",
                "review",
                "refine",
                "synthesize",
            ]

            return sequence[
                min(
                    orbit,
                    len(sequence) - 1,
                )
            ]

        if mode == AgentMode.HIGH:

            sequence = [

                "decompose",
                "problem_mapping",
                "specialist_analysis",
                "specialist_analysis",
                "evidence_check",

                "counter_argument",
                "solution_branch",
                "solution_branch",
                "comparison",

                "critic",
                "repair",
                "second_review",

                "synthesis",
                "adversarial_review",
                "finalize",
            ]

            return sequence[
                min(
                    orbit,
                    len(sequence) - 1,
                )
            ]

        sequence = [

            "decompose",
            "problem_mapping",
            "hypothesis",
            "research",

            "research",
            "evidence_extraction",
            "source_crosscheck",
            "specialist_analysis",

            "specialist_analysis",
            "alternative_solution",
            "counter_argument",

            "counter_argument",
            "contradiction_search",
            "critic",
            "critic",

            "repair",
            "repair",
            "evidence_recheck",
            "synthesis",

            "synthesis",
            "deep_review",
            "deep_review",
            "adversarial_review",
            "adversarial_review",

            "research_gap",
            "source_validation",
            "claim_validation",
            "logic_validation",
            "consistency_check",

            "refinement",
            "refinement",
            "compression",
            "clarification",
            "counterexample",

            "counterexample",
            "second_synthesis",
            "independent_solution",
            "independent_solution",
            "comparison",

            "final_critic",
            "final_critic",
            "fact_check",
            "evidence_check",
            "answer_architecture",

            "final_refinement",
            "confidence_check",
            "uncertainty_check",
            "core_extraction",
            "finalize",
        ]

        return sequence[
            min(
                orbit,
                len(sequence) - 1,
            )
        ]

    def _research_if_needed(
        self,
        state,
        purpose,
        enabled,
    ):

        if not enabled:
            return

        research_purposes = {
            "research",
            "evidence_extraction",
            "source_crosscheck",
            "evidence_recheck",
            "research_gap",
            "source_validation",
            "fact_check",
            "evidence_check",
        }

        if purpose not in research_purposes:
            return

        data = self.research.research(
            state.objective
        )

        state.evidence.append(
            data
        )

    def _compact_context(
        self,
        state,
        limit,
    ):

        chunks = []

        if state.core_answer:

            chunks.append(
                "CURRENT CORE:\\n"
                + state.core_answer
            )

        if state.evidence:

            chunks.append(
                "EVIDENCE:\\n"
                + str(
                    state.evidence[
                        -2:
                    ]
                )
            )

        history = state.history[
            -5:
        ]

        for record in history:

            chunks.append(
                f"ORBIT {record.index}: "
                f"{record.purpose}\\n"
                f"{record.output}"
            )

        text = "\n\n".join(chunks)

        return text[-limit:]

    def _build_messages(
        self,
        state,
        purpose,
        policy,
    ):

        if state.mode == AgentMode.FAST:

            brain = self._memory_context(
                state.objective,
                600,
            )

            user_content = state.objective

            if brain:
                user_content = (
                    f"{state.objective}\n\n"
                    f"OTAK RELEVAN:\n{brain}"
                )

            return [
                {
                    "role": "system",
                    "content": (
                        "You are J. S'GENT. "
                        "Answer the user's question "
                        "directly, accurately, and briefly. "
                        "Do not explain your reasoning. "
                        "Do not create a plan."
                    ),
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ]

        context = (
            self._compact_context(
                state,
                policy.context_window,
            )
        )

        brain = self._memory_context(
            state.objective,
            2000,
        )

        brain_block = (
            f"\nMEMORY (Obsidian):\n{brain}\n"
            if brain
            else ""
        )

        system = f"""
You are one worker inside J. S'GENT's
orbital multi-AI system.

MODE:
{state.mode.value}

CURRENT ORBIT:
{state.orbit_count}

ORBIT PURPOSE:
{purpose}

Rules:

1. Solve only the current orbit objective.
2. Do not pretend the entire task is finished.
3. Preserve useful findings from previous orbits.
4. Use MEMORY when relevant, ignore when not.
5. Identify uncertainty explicitly.
6. Improve the current core.
7. Produce a useful handoff.
8. Be concise when previous work is already correct.
"""

        user = f"""
ORIGINAL OBJECTIVE:
{state.objective}

CURRENT STATE:
{context}
{brain_block}
Perform this orbit:
{purpose}

Return:

CORE_UPDATE:
The best current core answer/state.

NEW_FINDINGS:
New information created by this orbit.

OPEN_QUESTIONS:
Remaining uncertainty.

CONFIDENCE:
A number from 0.00 to 1.00.

HANDOFF:
What the next orbit should focus on.
"""

        return [
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": user,
            },
        ]

    def _parse(
        self,
        output,
    ):

        text = output.strip()

        confidence = 0.50

        marker = "CONFIDENCE:"

        if marker in text:

            tail = text.split(
                marker,
                1
            )[1].split(
                "\n",
                1
            )[0
            ].strip()

            try:
                confidence = float(
                    tail
                    .replace(
                        "%",
                        ""
                    )
                )

                if confidence > 1:
                    confidence /= 100

            except ValueError:
                confidence = 0.50

        return text, max(
            0.0,
            min(
                1.0,
                confidence
            ),
        )

    def _converged(
        self,
        state,
        policy,
    ):

        if state.confidence < (
            policy.convergence_threshold
        ):
            return False

        if len(
            state.history
        ) < 2:

            return False

        latest = state.history[
            -1
        ]

        previous = state.history[
            -2
        ]

        if not latest.output:
            return False

        if not previous.output:
            return False

        return latest.output[
            -600:
        ] == previous.output[
            -600:
        ]

    def run(
        self,
        objective,
        mode=AgentMode.NORMAL,
        on_orbit=None,
    ):

        policy = get_policy(mode)

        state = OrbitalState(
            objective=objective,
            mode=policy.mode,
        )

        for index in range(
            policy.max_orbits
        ):

            state.orbit_count = (
                index + 1
            )

            purpose = self._purpose(
                policy.mode,
                index,
            )

            self._research_if_needed(
                state,
                purpose,
                policy.enable_research,
            )

            excluded = set()

            previous = (
                state.history[-1]
                if state.history
                else None
            )

            if previous and (
                policy.enable_cross_provider_review
            ):

                excluded.add(
                    previous.provider
                )

            decision = (
                self.rotation.choose(
                    excluded=excluded,
                )
            )

            provider = self.router.get(
                decision.provider
            )

            messages = self._build_messages(
                state,
                purpose,
                policy,
            )

            try:

                is_fast = (
                    policy.mode
                    == AgentMode.FAST
                )

                try:
                    output = provider.generate(
                        messages,
                        fast=is_fast,
                    )
                except TypeError:
                    output = provider.generate(
                        messages
                    )

                parsed, confidence = (
                    self._parse(
                        output
                    )
                )

                record = OrbitRecord(
                    index=index + 1,
                    purpose=purpose,
                    provider=(
                        decision.provider
                    ),
                    output=parsed,
                    confidence=confidence,
                )

                state.history.append(
                    record
                )

                state.core_answer = (
                    parsed
                )

                state.confidence = (
                    confidence
                )

                self.rotation.record(
                    decision.provider,
                    True,
                    confidence,
                )

                if on_orbit:
                    on_orbit(
                        state,
                        record,
                    )

            except Exception as exc:

                self.rotation.record(
                    decision.provider,
                    False,
                    0.0,
                )

                record = OrbitRecord(
                    index=index + 1,
                    purpose=purpose,
                    provider=(
                        decision.provider
                    ),
                    output=(
                        f"ERROR: {exc}"
                    ),
                    confidence=0.0,
                )

                state.history.append(
                    record
                )

                if on_orbit:
                    on_orbit(
                        state,
                        record,
                    )

            # FAST/NORMAL/HIGH can stop early
            # only if there is genuine convergence.
            if (
                index + 1
                >= policy.min_orbits
                and
                self._converged(
                    state,
                    policy,
                )
            ):

                break

        try:
            if self.memory and hasattr(
                self.memory, "log_task"
            ):
                self.memory.log_task(state)
            elif self.memory and hasattr(
                self.memory, "experience_log"
            ):
                self.memory.experience_log(
                    f"task {state.mode.value}",
                    state.core_answer[:2000],
                )
        except Exception:
            pass

        return state
