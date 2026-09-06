from dataclasses import dataclass


@dataclass
class RotationDecision:

    provider: str

    score: float

    reason: str


class RotationScheduler:

    def __init__(self, router):

        self.router = router

        self.last_provider = None

        self.provider_stats = {}

    def _ensure(self, name):

        if name not in self.provider_stats:

            self.provider_stats[name] = {
                "assignments": 0,
                "successes": 0,
                "failures": 0,
                "score": 0.0,
            }

    def _score(
        self,
        provider,
        excluded,
    ):

        self._ensure(provider)

        stats = self.provider_stats[
            provider
        ]

        assignments = stats[
            "assignments"
        ]

        if assignments:

            reliability = (
                stats["successes"]
                / assignments
            )

            quality = (
                stats["score"]
                / max(
                    1,
                    stats["successes"]
                )
            )

        else:

            reliability = 0.50
            quality = 0.50

        diversity_bonus = (
            0.20
            if provider != self.last_provider
            else -0.25
        )

        excluded_penalty = (
            -10
            if provider in excluded
            else 0
        )

        return (
            reliability * 0.35
            + quality * 0.35
            + diversity_bonus
            + excluded_penalty
        )

    def choose(
        self,
        required_capabilities=None,
        excluded=None,
    ):

        required_capabilities = (
            required_capabilities or set()
        )

        excluded = excluded or set()

        available = (
            self.router.available()
        )

        candidates = []

        for name, ready in available.items():

            if not ready:
                continue

            provider = self.router.get(name)

            capabilities = set(
                getattr(
                    provider,
                    "capabilities",
                    set(),
                )
            )

            if required_capabilities:

                matched = (
                    capabilities
                    & required_capabilities
                )

                capability_score = (
                    len(matched)
                    / len(required_capabilities)
                )

            else:

                capability_score = 1.0

            score = (
                capability_score * 0.50
                + self._score(
                    name,
                    excluded
                ) * 0.50
            )

            candidates.append(
                (name, score)
            )

        if not candidates:

            raise RuntimeError(
                "Tidak ada AI provider yang tersedia."
            )

        candidates.sort(
            key=lambda x: x[1],
            reverse=True,
        )

        name, score = candidates[0]

        self._ensure(name)

        self.provider_stats[
            name
        ][
            "assignments"
        ] += 1

        self.last_provider = name

        return RotationDecision(
            provider=name,
            score=score,
            reason=(
                "capability + quality "
                "+ reliability + rotation"
            ),
        )

    def record(
        self,
        provider,
        success,
        quality,
    ):

        self._ensure(provider)

        stats = self.provider_stats[
            provider
        ]

        if success:
            stats["successes"] += 1
            stats["score"] += quality

        else:
            stats["failures"] += 1

    def report(self):

        return self.provider_stats
