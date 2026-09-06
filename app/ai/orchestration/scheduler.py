from dataclasses import dataclass

from .capability import ProviderProfile


@dataclass
class Assignment:

    provider: str

    score: float


class OrbitalScheduler:

    def __init__(self, router):

        self.router = router

        self.profiles: dict[
            str,
            ProviderProfile
        ] = {}

        self.round_robin_cursor = 0

        self.provider_usage = {}

    def register_profile(
        self,
        profile: ProviderProfile,
    ):

        self.profiles[
            profile.name
        ] = profile

    def sync_router(self):

        for name in self.router.providers:

            if name not in self.profiles:

                self.profiles[name] = (
                    ProviderProfile(
                        name=name
                    )
                )

    def rank(
        self,
        work,
        excluded=None,
    ):

        self.sync_router()

        excluded = excluded or set()

        available = (
            self.router.available()
        )

        candidates = []

        for name, ready in available.items():

            if not ready:
                continue

            if name in excluded:
                continue

            profile = self.profiles.get(name)

            if profile is None:
                continue

            if (
                profile.active_jobs
                >= profile.max_parallel
            ):
                continue

            capability = (
                profile.capability_score(
                    work.required_capabilities
                )
            )

            reliability = (
                profile.reliability_score()
            )

            quality = (
                profile.quality_score()
            )

            load = profile.load_score()

            utilization = (
                profile.utilization_available()
            )

            score = (

                capability * 0.35

                + reliability * 0.20

                + quality * 0.20

                + min(
                    1.0,
                    utilization / max(
                        1,
                        profile.max_parallel
                    )
                ) * 0.10

                + profile.priority * 0.10

                + (1.0 - load) * 0.05
            )

            candidates.append(
                Assignment(
                    provider=name,
                    score=score,
                )
            )

        return sorted(
            candidates,
            key=lambda item: item.score,
            reverse=True,
        )

    def assign(
        self,
        work,
        excluded=None,
    ):

        ranked = self.rank(
            work,
            excluded,
        )

        if not ranked:

            raise RuntimeError(
                "Tidak ada provider yang "
                "mampu menerima WorkUnit."
            )

        selected = ranked[0]

        profile = self.profiles[
            selected.provider
        ]

        profile.active_jobs += 1

        work.assign(
            selected.provider
        )

        return selected

    def release(
        self,
        work,
        score,
        success,
    ):

        provider = (
            work.assigned_provider
        )

        if not provider:
            return

        profile = self.profiles[
            provider
        ]

        profile.active_jobs = max(
            0,
            profile.active_jobs - 1,
        )

        if success:

            profile.completed_jobs += 1

            profile.total_score += score

        else:

            profile.failed_jobs += 1

    def choose_diverse_reviewers(
        self,
        work,
        count=1,
    ):

        ranked = self.rank(work)

        selected = []

        used = set()

        for item in ranked:

            if (
                item.provider
                == work.assigned_provider
            ):
                continue

            if item.provider in used:
                continue

            selected.append(
                item.provider
            )

            used.add(
                item.provider
            )

            if len(selected) >= count:
                break

        return selected

    def report(self):

        self.sync_router()

        return {

            name: {

                "capabilities": sorted(
                    profile.capabilities
                ),

                "active_jobs":
                    profile.active_jobs,

                "max_parallel":
                    profile.max_parallel,

                "completed":
                    profile.completed_jobs,

                "failed":
                    profile.failed_jobs,

                "reliability": round(
                    profile.reliability_score(),
                    3,
                ),

                "quality": round(
                    profile.quality_score(),
                    3,
                ),

                "load": round(
                    profile.load_score(),
                    3,
                ),
            }

            for name, profile
            in self.profiles.items()
        }
