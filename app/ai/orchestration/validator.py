from dataclasses import dataclass


@dataclass
class ValidationResult:

    passed: bool

    score: float

    checks: dict

    reason: str


class QualityGate:

    MIN_SCORE = 0.78

    def validate(self, work):

        output = work.output

        checks = {

            "has_output":
                bool(
                    output
                    and str(output).strip()
                ),

            "within_attempt_budget":
                work.attempts
                <= work.max_attempts,

            "expected_output_declared":
                bool(
                    work.expected_output
                ),

            "objective_declared":
                bool(
                    work.objective
                ),
        }

        score = (
            sum(checks.values())
            / len(checks)
        )

        passed = (
            score >= self.MIN_SCORE
            and checks[
                "within_attempt_budget"
            ]
        )

        return ValidationResult(
            passed=passed,
            score=score,
            checks=checks,
            reason=(
                "Quality gate passed."
                if passed
                else "Quality gate failed."
            ),
        )
