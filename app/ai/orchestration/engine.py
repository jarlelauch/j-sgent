from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import time

from .mode import AgentMode, SystemMode, get_policy
from .research import ResearchEngine
from .rotation import RotationScheduler
from .scheduler import OrbitalScheduler
from .validator import QualityGate
from .work_unit import WorkUnit


@dataclass
class OrbitRecord:
    index: int
    purpose: str
    provider: str | None = None
    output: str = ""
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class OrbitalState:
    objective: str
    mode: AgentMode
    system: str = "orbital"
    metadata: dict = field(default_factory=dict)
    core_answer: str = ""
    confidence: float = 0.0
    orbit_count: int = 0
    history: list[OrbitRecord] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)


# purpose -> required capabilities for scheduler
PURPOSE_CAPS = {
    "direct_solve": set(),
    "decompose": {"planning", "reasoning"},
    "solve": {"reasoning", "analysis"},
    "review": {"critique", "reasoning"},
    "refine": {"synthesis", "reasoning"},
    "synthesize": {"synthesis"},
    "problem_mapping": {"analysis", "planning"},
    "specialist_analysis": {"reasoning", "analysis"},
    "evidence_check": {"analysis", "local"},
    "counter_argument": {"critique", "reasoning"},
    "solution_branch": {"reasoning", "coding"},
    "comparison": {"analysis", "synthesis"},
    "critic": {"critique"},
    "repair": {"coding", "reasoning"},
    "second_review": {"critique"},
    "synthesis": {"synthesis"},
    "adversarial_review": {"critique", "reasoning"},
    "finalize": {"synthesis"},
    "hypothesis": {"reasoning"},
    "research": {"local"},
    "evidence_extraction": {"analysis"},
    "source_crosscheck": {"analysis"},
    "alternative_solution": {"reasoning"},
    "contradiction_search": {"critique"},
    "evidence_recheck": {"analysis"},
    "deep_review": {"critique"},
    "research_gap": {"analysis"},
    "source_validation": {"analysis"},
    "claim_validation": {"critique"},
    "logic_validation": {"reasoning", "critique"},
    "consistency_check": {"critique"},
    "refinement": {"synthesis"},
    "compression": {"synthesis"},
    "clarification": {"synthesis"},
    "counterexample": {"critique", "reasoning"},
    "second_synthesis": {"synthesis"},
    "independent_solution": {"reasoning"},
    "final_critic": {"critique"},
    "fact_check": {"analysis"},
    "answer_architecture": {"planning", "synthesis"},
    "final_refinement": {"synthesis"},
    "confidence_check": {"critique"},
    "uncertainty_check": {"critique"},
    "core_extraction": {"synthesis"},
}


class OrbitalEngine:
    def __init__(self, router, memory=None):
        self.router = router
        self.memory = memory
        self.rotation = RotationScheduler(router)
        self.scheduler = OrbitalScheduler(router)
        self.research = ResearchEngine()
        self.validator = QualityGate()
        self._research_cache = {}

    def _memory_context(self, objective, budget):
        if not self.memory:
            return ""
        try:
            if hasattr(self.memory, "recall"):
                return self.memory.recall(objective, budget=budget) or ""
            if hasattr(self.memory, "search"):
                out = []
                for r in self.memory.search(objective[:20])[:2]:
                    out.append((r.get("content") or "")[:600])
                return "\n\n".join(out)[-budget:]
        except Exception:
            pass
        return ""

    def _purpose(self, mode, orbit):
        if mode == AgentMode.FAST:
            return "direct_solve"
        if mode == AgentMode.NORMAL:
            seq = ["decompose", "solve", "review", "refine", "synthesize"]
            return seq[min(orbit, len(seq) - 1)]
        if mode == AgentMode.HIGH:
            seq = [
                "decompose", "problem_mapping", "specialist_analysis", "specialist_analysis", "evidence_check",
                "counter_argument", "solution_branch", "solution_branch", "comparison",
                "critic", "repair", "second_review",
                "synthesis", "adversarial_review", "finalize",
            ]
            return seq[min(orbit, len(seq) - 1)]
        seq = [
            "decompose", "problem_mapping", "hypothesis", "research",
            "research", "evidence_extraction", "source_crosscheck", "specialist_analysis",
            "specialist_analysis", "alternative_solution", "counter_argument",
            "counter_argument", "contradiction_search", "critic", "critic",
            "repair", "repair", "evidence_recheck", "synthesis",
            "synthesis", "deep_review", "deep_review", "adversarial_review", "adversarial_review",
            "research_gap", "source_validation", "claim_validation", "logic_validation", "consistency_check",
            "refinement", "refinement", "compression", "clarification", "counterexample",
            "counterexample", "second_synthesis", "independent_solution", "independent_solution", "comparison",
            "final_critic", "final_critic", "fact_check", "evidence_check", "answer_architecture",
            "final_refinement", "confidence_check", "uncertainty_check", "core_extraction", "finalize",
        ]
        return seq[min(orbit, len(seq) - 1)]

    def _should_parallel(self, purpose, policy):
        if not policy.enable_parallel:
            return False
        return purpose in {"specialist_analysis", "solution_branch", "research", "deep_review", "adversarial_review", "repair", "independent_solution"}

    def _research_if_needed(self, state, purpose, enabled):
        if not enabled:
            return
        research_purposes = {
            "research", "evidence_extraction", "source_crosscheck", "evidence_recheck",
            "research_gap", "source_validation", "fact_check", "evidence_check",
        }
        if purpose not in research_purposes:
            return
        q = state.objective.strip()[:120]
        if q in self._research_cache:
            data = self._research_cache[q]
        else:
            try:
                data = self.research.research(state.objective)
            except Exception as exc:
                data = {"error": str(exc)}
            self._research_cache[q] = data
        state.evidence.append(data)

    def _compact_context(self, state, limit):
        chunks = []
        if state.core_answer:
            chunks.append("CURRENT CORE:\n" + state.core_answer)
        if state.evidence:
            # only last 1 evidence to save tokens
            chunks.append("EVIDENCE:\n" + str(state.evidence[-1])[:800])
        for r in state.history[-4:]:
            chunks.append(f"ORBIT {r.index}: {r.purpose}\n{r.output[:700]}")
        return "\n\n".join(chunks)[-limit:]

    def _build_messages(self, state, purpose, policy):
        # system mode injected via state.metadata["system"] if present
        system_mode = getattr(state, "system", None)
        if isinstance(system_mode, str):
            try:
                system_mode = SystemMode(system_mode)
            except Exception:
                system_mode = SystemMode.ORBITAL
        if system_mode is None:
            # try from state metadata
            try:
                system_mode = SystemMode(state.metadata.get("system", "orbital")) if hasattr(state, "metadata") else SystemMode.ORBITAL
            except Exception:
                system_mode = SystemMode.ORBITAL

        # CHATBOT system: direct concise answer regardless of orbit speed
        if system_mode == SystemMode.CHATBOT:
            brain = self._memory_context(state.objective, 600)
            system_prompt = "You are J. S'GENT CHAT BOT (local). Friendly, concise, helpful. Jawab langsung to the point, bahasa Indonesia santai. Jangan bertele-tele."
            user_content = state.objective + (f"\n\nOTAK RELEVAN:\n{brain}" if brain else "")
            return [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
        if system_mode == SystemMode.AGENT:
            context = self._compact_context(state, policy.context_window)
            brain = self._memory_context(state.objective, 2000)
            brain_block = f"\nMEMORY:\n{brain}\n" if brain else ""
            system = f"You are J. S'GENT AI AGENT (autonomous). SYSTEM:agent MODE:{state.mode.value} ORBIT:{state.orbit_count} PURPOSE:{purpose}\nRules: plan → act → observe → reflect. Otonom, gunakan reasoning + tools jika ada. State uncertainty."
            user = f"OBJECTIVE:\n{state.objective}\n\nSTATE:\n{context}{brain_block}\nPerform: {purpose}\nReturn: CORE_UPDATE, NEW_FINDINGS, OPEN_QUESTIONS, CONFIDENCE 0-1, HANDOFF"
            return [{"role": "system", "content": system}, {"role": "user", "content": user}]
        # ORBITAL default
        if state.mode == AgentMode.FAST:
            brain = self._memory_context(state.objective, 600)
            system_prompt = "You are J. S'GENT ORBITAL. Answer directly, accurately, briefly. No reasoning trace. No plan."
            user_content = state.objective + (f"\n\nOTAK RELEVAN:\n{brain}" if brain else "")
            return [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
        context = self._compact_context(state, policy.context_window)
        brain = self._memory_context(state.objective, 2000)
        brain_block = f"\nMEMORY:\n{brain}\n" if brain else ""
        system = f"You are one worker in J. S'GENT orbital system. MODE:{state.mode.value} ORBIT:{state.orbit_count} PURPOSE:{purpose}\nRules: 1) solve only current purpose 2) preserve useful prior 3) use MEMORY if relevant 4) state uncertainty 5) improve core 6) handoff next."
        user = f"OBJECTIVE:\n{state.objective}\n\nSTATE:\n{context}{brain_block}\nPerform: {purpose}\nReturn: CORE_UPDATE, NEW_FINDINGS, OPEN_QUESTIONS, CONFIDENCE 0-1, HANDOFF"
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _parse(self, output):
        text = output.strip()
        confidence = 0.50
        if "CONFIDENCE:" in text:
            try:
                tail = text.split("CONFIDENCE:", 1)[1].split("\n", 1)[0].strip().replace("%", "")
                confidence = float(tail)
                if confidence > 1:
                    confidence /= 100
            except Exception:
                confidence = 0.50
        return text, max(0.0, min(1.0, confidence))

    def _converged(self, state, policy):
        if state.confidence < policy.convergence_threshold:
            return False
        if len(state.history) < 2:
            return False
        a = state.history[-1].output[-600:]
        b = state.history[-2].output[-600:]
        return bool(a and b and a == b)

    def _choose_provider(self, purpose, excluded):
        caps = PURPOSE_CAPS.get(purpose, set())
        # try OrbitalScheduler first (capability-aware)
        try:
            w = WorkUnit(objective="x", role=purpose, expected_output="y", required_capabilities=caps)
            if excluded:
                w.metadata["excluded"] = excluded
            # use scheduler rank directly to avoid active_jobs blocking when single provider
            ranked = self.scheduler.rank(w, excluded=excluded)
            if ranked:
                # pick top that is available
                name = ranked[0].provider
                # assign via scheduler to track load
                self.scheduler.assign(w, excluded=excluded)
                # release immediately (track stats manually via rotation)
                self.scheduler.release(w, 0.5, True)
                return name
        except Exception:
            pass
        # fallback to rotation
        try:
            dec = self.rotation.choose(excluded=excluded)
            return dec.provider
        except Exception:
            # last fallback: any available
            avail = self.router.available()
            for n, ok in avail.items():
                if ok and n not in (excluded or set()):
                    return n
            for n, ok in avail.items():
                if ok:
                    return n
            raise RuntimeError("Tidak ada AI provider yang tersedia.")

    def _execute_single(self, purpose, state, policy, excluded):
        # prefer muse for agent/chatbot if available
        prefer_muse = getattr(state, "system", "orbital") in ("agent", "chatbot", "chat")
        try:
            avail = self.router.available()
        except Exception:
            avail = {}
        if prefer_muse and avail.get("muse"):
            # if not excluded, force muse
            if "muse" not in (excluded or set()):
                provider_name = "muse"
                provider = self.router.get(provider_name)
                if provider and provider.available():
                    messages = self._build_messages(state, purpose, policy)
                    is_fast = policy.mode == AgentMode.FAST
                    try:
                        try:
                            output = provider.generate(messages, fast=is_fast)
                        except TypeError:
                            output = provider.generate(messages)
                        parsed, conf = self._parse(output)
                        w = WorkUnit(objective=state.objective, role=purpose, expected_output="orbit output", required_capabilities=PURPOSE_CAPS.get(purpose, set()))
                        w.submit(parsed); w.begin_validation()
                        v = self.validator.validate(w)
                        if not v.passed:
                            conf = max(0.1, conf * 0.7)
                        self.rotation.record(provider_name, True, conf)
                        return parsed, conf, provider_name, None
                    except Exception as exc:
                        self.rotation.record(provider_name, False, 0.0)
                        # fallback to normal chooser
                        pass
        provider_name = self._choose_provider(purpose, excluded)
        provider = self.router.get(provider_name)
        messages = self._build_messages(state, purpose, policy)
        is_fast = policy.mode == AgentMode.FAST
        try:
            try:
                output = provider.generate(messages, fast=is_fast)
            except TypeError:
                output = provider.generate(messages)
            parsed, conf = self._parse(output)
            # validate via WorkUnit gate (lightweight)
            w = WorkUnit(objective=state.objective, role=purpose, expected_output="orbit output", required_capabilities=PURPOSE_CAPS.get(purpose, set()))
            w.submit(parsed)
            w.begin_validation()
            v = self.validator.validate(w)
            if not v.passed:
                conf = max(0.1, conf * 0.7)
            self.rotation.record(provider_name, True, conf)
            # update scheduler stats
            try:
                prof = self.scheduler.profiles.get(provider_name)
                if prof:
                    prof.completed_jobs += 1
                    prof.total_score += conf
            except Exception:
                pass
            return parsed, conf, provider_name, None
        except Exception as exc:
            self.rotation.record(provider_name, False, 0.0)
            try:
                prof = self.scheduler.profiles.get(provider_name)
                if prof:
                    prof.failed_jobs += 1
            except Exception:
                pass
            return f"ERROR: {exc}", 0.0, provider_name, exc

    def run(self, objective, mode=AgentMode.NORMAL, system="orbital", on_orbit=None):
        policy = get_policy(mode)
        # normalize system
        try:
            sys_val = SystemMode(system.lower()).value if isinstance(system, str) else system.value
        except Exception:
            sys_val = "orbital"
        state = OrbitalState(objective=objective, mode=policy.mode, system=sys_val, metadata={"system": sys_val})
        # sync scheduler profiles with router capabilities
        try:
            self.scheduler.sync_router()
            for name, prov in self.router.providers.items():
                if name not in self.scheduler.profiles:
                    continue
                prof = self.scheduler.profiles[name]
                prof.capabilities = set(getattr(prov, "capabilities", set()))
                prof.max_parallel = int(getattr(prov, "max_parallel", 1))
        except Exception:
            pass

        for index in range(policy.max_orbits):
            state.orbit_count = index + 1
            purpose = self._purpose(policy.mode, index)
            self._research_if_needed(state, purpose, policy.enable_research)
            excluded = set()
            if state.history and policy.enable_cross_provider_review:
                excluded.add(state.history[-1].provider)

            # Parallel fan-out for HIGH/ULTRA
            if self._should_parallel(purpose, policy):
                # determine workers: 2 for most, 3 for ULTRA heavy
                workers = 2
                if policy.mode == AgentMode.ULTRA and purpose in {"specialist_analysis", "deep_review"}:
                    workers = 3
                # check available providers count
                avail_count = sum(1 for v in self.router.available().values() if v)
                if avail_count < 2:
                    workers = 1
                if workers == 1:
                    parsed, conf, prov, err = self._execute_single(purpose, state, policy, excluded)
                    rec = OrbitRecord(index=index+1, purpose=purpose, provider=prov, output=parsed, confidence=conf)
                    state.history.append(rec)
                    state.core_answer = parsed
                    state.confidence = conf
                    if on_orbit:
                        on_orbit(state, rec)
                else:
                    # parallel execution
                    futures = {}
                    results = []
                    with ThreadPoolExecutor(max_workers=workers) as ex:
                        for i in range(workers):
                            # avoid picking same provider twice if possible
                            ex_excluded = set(excluded)
                            if i > 0:
                                # exclude already chosen in this batch
                                for _, _, p, _ in results:
                                    ex_excluded.add(p)
                            futures[ex.submit(self._execute_single, f"{purpose}#{i+1}", state, policy, ex_excluded)] = i
                        for fut in as_completed(futures):
                            try:
                                parsed, conf, prov, err = fut.result()
                                results.append((parsed, conf, prov, err))
                            except Exception as exc:
                                results.append((f"ERROR: {exc}", 0.0, None, exc))
                    # merge: pick best confidence
                    results.sort(key=lambda x: x[1], reverse=True)
                    best_parsed, best_conf, best_prov, _ = results[0]
                    # create single orbit record merged
                    merged = best_parsed
                    if len(results) > 1:
                        merged += f"\n\n[PARALLEL {workers} branch, best {best_conf:.2f}]"
                    rec = OrbitRecord(index=index+1, purpose=purpose, provider=best_prov, output=merged, confidence=best_conf, metadata={"parallel": workers, "branches": len(results)})
                    state.history.append(rec)
                    state.core_answer = merged
                    state.confidence = best_conf
                    if on_orbit:
                        on_orbit(state, rec)
            else:
                parsed, conf, prov, err = self._execute_single(purpose, state, policy, excluded)
                rec = OrbitRecord(index=index+1, purpose=purpose, provider=prov, output=parsed, confidence=conf)
                state.history.append(rec)
                state.core_answer = parsed
                state.confidence = conf
                if on_orbit:
                    on_orbit(state, rec)

            if index + 1 >= policy.min_orbits and self._converged(state, policy):
                break

        try:
            if self.memory and hasattr(self.memory, "log_task"):
                self.memory.log_task(state)
            elif self.memory and hasattr(self.memory, "experience_log"):
                self.memory.experience_log(f"task {state.mode.value}", state.core_answer[:2000])
        except Exception:
            pass
        return state
