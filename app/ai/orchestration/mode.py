from enum import Enum
from dataclasses import dataclass


class AgentMode(str, Enum):

    FAST = "fast"
    NORMAL = "normal"
    HIGH = "high"
    ULTRA = "ultra"


class SystemMode(str, Enum):
    ORBITAL = "orbital"
    AGENT = "agent"
    CHATBOT = "chatbot"


@dataclass(frozen=True)
class ModePolicy:

    mode: AgentMode

    max_orbits: int

    min_orbits: int

    enable_parallel: bool

    enable_debate: bool

    enable_research: bool

    enable_cross_provider_review: bool

    enable_adversarial_review: bool

    convergence_threshold: float

    context_window: int


POLICIES = {

    AgentMode.FAST: ModePolicy(
        mode=AgentMode.FAST,
        max_orbits=1,
        min_orbits=1,
        enable_parallel=False,
        enable_debate=False,
        enable_research=False,
        enable_cross_provider_review=False,
        enable_adversarial_review=False,
        convergence_threshold=0.92,
        context_window=6000,
    ),

    AgentMode.NORMAL: ModePolicy(
        mode=AgentMode.NORMAL,
        max_orbits=5,
        min_orbits=5,
        enable_parallel=False,
        enable_debate=False,
        enable_research=False,
        enable_cross_provider_review=True,
        enable_adversarial_review=False,
        convergence_threshold=0.90,
        context_window=9000,
    ),

    AgentMode.HIGH: ModePolicy(
        mode=AgentMode.HIGH,
        max_orbits=15,
        min_orbits=15,
        enable_parallel=True,
        enable_debate=True,
        enable_research=False,
        enable_cross_provider_review=True,
        enable_adversarial_review=True,
        convergence_threshold=0.91,
        context_window=12000,
    ),

    AgentMode.ULTRA: ModePolicy(
        mode=AgentMode.ULTRA,
        max_orbits=50,
        min_orbits=50,
        enable_parallel=True,
        enable_debate=True,
        enable_research=True,
        enable_cross_provider_review=True,
        enable_adversarial_review=True,
        convergence_threshold=0.95,
        context_window=18000,
    ),

}


def get_policy(mode):

    if isinstance(mode, str):
        # backward compat: handle old 'agent'/'chatbot' as speed aliases
        low = mode.lower()
        if low == "agent":
            low = "high"
        if low == "chatbot":
            low = "fast"
        mode = AgentMode(low)

    return POLICIES[mode]
