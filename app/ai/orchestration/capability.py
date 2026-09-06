from dataclasses import dataclass, field


@dataclass
class ProviderProfile:

    name: str

    capabilities: set[str] = field(default_factory=set)

    max_parallel: int = 1

    priority: float = 1.0

    reliability: float = 0.75

    average_latency: float = 1.0

    cost_factor: float = 1.0

    active_jobs: int = 0

    completed_jobs: int = 0

    failed_jobs: int = 0

    total_score: float = 0.0

    def capability_score(self, required):

        if not required:
            return 1.0

        required = set(required)

        matched = (
            self.capabilities & required
        )

        return len(matched) / len(required)

    def reliability_score(self):

        total = (
            self.completed_jobs
            + self.failed_jobs
        )

        if total == 0:
            return self.reliability

        return self.completed_jobs / total

    def quality_score(self):

        if self.completed_jobs == 0:
            return 0.0

        return (
            self.total_score
            / self.completed_jobs
        )

    def load_score(self):

        if self.max_parallel <= 0:
            return 0.0

        return min(
            1.0,
            self.active_jobs / self.max_parallel,
        )

    def utilization_available(self):

        return max(
            0,
            self.max_parallel - self.active_jobs,
        )
