"""Loop engineering — iterate an agent toward a goal instead of one-shot prompting.

Technique applied from *"Stop Prompting. Start Looping."*: rather than sending a
single prompt and accepting whatever comes back, run the model in a refine loop
(generate -> self-check -> refine) and stop when the goal is met or an iteration
budget is exhausted. A two-agent variant lets one responder generate while another
critiques, which ties the loop into ARIA's multi-agent theme.

The core (`run_loop` / `run_dual_loop` / `run_pipeline`) is model-agnostic: it
drives any ``responder`` callable ``(str) -> str``. The default responder wires up
the repo's Claude client, but you can pass a fake responder for offline testing.

Usage:
    from agent_loop import run_loop, claude_responder

    result = run_loop(
        "Write a regex that matches an ISO-8601 date, then verify it.",
        responder=claude_responder(),
        max_iterations=5,
    )
    print(result.final, f"({result.iterations} iterations, done={result.done})")

    # CLI:
    #   python agent_loop.py "Refine a one-paragraph summary of this repo."
    #   python agent_loop.py "Design a caching layer." --dual      # propose + critique
    #   python agent_loop.py "Build a rate limiter." --pipeline    # Architect->Engineer->Reviewer->Optimizer

Also implements prompt #7 ("Multi-Agent Workflow") from the 8-engineering-prompts
thread via `run_pipeline`: a four-role Architect -> Engineer -> Reviewer ->
Optimizer chain where each role can use a different responder.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Callable, List

# The model emits this marker when it judges the goal met; the loop then stops.
DONE_MARKER = "GOAL_MET"

Responder = Callable[[str], str]


@dataclass
class LoopResult:
    """Outcome of a loop run."""

    final: str
    iterations: int
    done: bool
    history: List[dict] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Outcome of a multi-agent pipeline run."""

    final: str
    stages: List[dict] = field(default_factory=list)


# Roles for the Architect -> Engineer -> Reviewer -> Optimizer workflow (prompt #7
# from the "8 engineering prompts" thread). Each role's instruction is combined
# with the task and the accumulated output of prior roles.
PIPELINE_ROLES: List[tuple] = [
    ("Architect",
     "You are a senior software architect. Design the architecture for the task: "
     "components, data flow, key decisions, and trade-offs. Output a clear design "
     "spec that an engineer can implement."),
    ("Engineer",
     "You are a senior software engineer. Implement the architecture below into "
     "working, well-structured code. Follow the design faithfully."),
    ("Reviewer",
     "You are a meticulous code reviewer. Review the implementation below for "
     "correctness, edge cases, security, and clarity. List concrete, actionable issues."),
    ("Optimizer",
     "You are a performance and quality optimizer. Using the implementation and the "
     "review below, produce a final, polished version that resolves the review issues "
     "and improves performance, readability, and robustness."),
]


def _refine_prompt(goal: str, previous: str | None, step: int, total: int) -> str:
    """Build the prompt for one iteration, folding in the prior answer."""
    header = (
        f"You are working toward this goal, iteratively:\n\n"
        f"GOAL: {goal}\n\n"
        f"This is iteration {step} of at most {total}. Improve on the previous "
        f"attempt. When — and only when — the goal is fully met, end your reply "
        f"with the exact token {DONE_MARKER} on its own line."
    )
    if previous is None:
        return header + "\n\nProduce your first attempt now."
    return header + f"\n\nPREVIOUS ATTEMPT:\n{previous}\n\nProduce an improved attempt now."


def run_loop(
    goal: str,
    responder: Responder,
    max_iterations: int = 5,
    on_step: Callable[[int, str], None] | None = None,
) -> LoopResult:
    """Iterate ``responder`` toward ``goal`` until it signals done or budget runs out.

    Parameters:
        goal: Natural-language objective to converge on.
        responder: Callable that maps a prompt to a text response.
        max_iterations: Hard cap on iterations (must be >= 1).
        on_step: Optional callback ``(iteration, response)`` for progress.

    Returns:
        LoopResult with the final answer, iteration count, done flag, and history.
    """
    if not goal or not goal.strip():
        raise ValueError("goal must be a non-empty string.")
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1.")

    history: List[dict] = []
    latest: str | None = None
    done = False

    for step in range(1, max_iterations + 1):
        prompt = _refine_prompt(goal, latest, step, max_iterations)
        response = responder(prompt)
        history.append({"iteration": step, "prompt": prompt, "response": response})
        if on_step:
            on_step(step, response)
        latest = response
        if DONE_MARKER in response:
            done = True
            break

    final = (latest or "").replace(DONE_MARKER, "").strip()
    return LoopResult(final=final, iterations=len(history), done=done, history=history)


def run_dual_loop(
    goal: str,
    generator: Responder,
    critic: Responder,
    max_iterations: int = 5,
    on_step: Callable[[int, str, str], None] | None = None,
) -> LoopResult:
    """Two-agent loop: ``generator`` proposes, ``critic`` reviews, repeat until approved.

    The critic ends its reply with ``GOAL_MET`` when the proposal satisfies the
    goal; otherwise its critique is fed back to the generator for another round.

    Returns a LoopResult whose ``final`` is the last generator proposal.
    """
    if not goal or not goal.strip():
        raise ValueError("goal must be a non-empty string.")
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1.")

    history: List[dict] = []
    proposal: str | None = None
    critique: str | None = None
    done = False

    for step in range(1, max_iterations + 1):
        if proposal is None:
            gen_prompt = f"GOAL: {goal}\n\nProduce your best attempt."
        else:
            gen_prompt = (
                f"GOAL: {goal}\n\nYOUR PREVIOUS ATTEMPT:\n{proposal}\n\n"
                f"REVIEWER FEEDBACK:\n{critique}\n\nProduce an improved attempt."
            )
        proposal = generator(gen_prompt)

        crit_prompt = (
            f"GOAL: {goal}\n\nPROPOSED ANSWER:\n{proposal}\n\n"
            f"Critique this against the goal. If it fully meets the goal, reply with "
            f"only the token {DONE_MARKER}. Otherwise give specific, actionable feedback."
        )
        critique = critic(crit_prompt)
        history.append(
            {"iteration": step, "proposal": proposal, "critique": critique}
        )
        if on_step:
            on_step(step, proposal, critique)
        if DONE_MARKER in critique:
            done = True
            break

    return LoopResult(
        final=(proposal or "").strip(), iterations=len(history), done=done, history=history
    )


def run_pipeline(
    task: str,
    responder: Responder | None = None,
    responders: dict | None = None,
    on_step: Callable[[str, str], None] | None = None,
) -> PipelineResult:
    """Multi-agent workflow (prompt #7): Architect -> Engineer -> Reviewer -> Optimizer.

    Each role receives the task plus the accumulated output of all prior roles, so
    the design flows into implementation, review, and finally optimization.

    Parameters:
        task: The engineering task to run through the pipeline.
        responder: Fallback responder used for any role not in ``responders``.
        responders: Optional ``{role_name: responder}`` map to assign a different
            responder per role.
        on_step: Optional callback ``(role, output)`` for progress.

    Returns:
        PipelineResult with per-stage outputs and the final optimized answer.
    """
    if not task or not task.strip():
        raise ValueError("task must be a non-empty string.")
    responders = responders or {}
    if responder is None and not responders:
        raise ValueError("Provide `responder` and/or `responders`.")

    stages: List[dict] = []
    transcript = ""

    for role, instruction in PIPELINE_ROLES:
        role_responder = responders.get(role, responder)
        if role_responder is None:
            raise ValueError(f"No responder available for role '{role}'.")
        prompt = f"{instruction}\n\nTASK: {task}"
        if transcript:
            prompt += f"\n\nWORK SO FAR:\n{transcript}"
        output = role_responder(prompt)
        stages.append({"role": role, "output": output})
        if on_step:
            on_step(role, output)
        transcript += f"\n\n## {role}\n{output}"

    final = stages[-1]["output"].strip() if stages else ""
    return PipelineResult(final=final, stages=stages)


# --- Default responder backed by the repo's Claude client ------------------

def claude_responder(model: str = "claude-sonnet-4-6") -> Responder:
    """Responder backed by the Anthropic Messages API."""
    def _respond(prompt: str) -> str:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ImportError("The anthropic SDK is not installed. Run: pip install anthropic") from exc
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set in environment variables.")
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if getattr(block, "type", None) == "text")

    return _respond


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    dual = "--dual" in args
    pipeline = "--pipeline" in args
    args = [a for a in args if a not in ("--dual", "--pipeline")]

    if "--model" in args:
        i = args.index("--model")
        del args[i : i + 2]

    goal = " ".join(args) or "Write a haiku about iterating toward a goal."

    def _print(step, *payload):
        print(f"\n--- iteration {step} ---")
        for p in payload:
            print(p)

    try:
        if pipeline:
            print(f"Multi-agent pipeline (Architect->Engineer->Reviewer->Optimizer) — task: {goal}")
            presult = run_pipeline(
                goal, responder=claude_responder(),
                on_step=lambda role, out: print(f"\n--- {role} ---\n{out}"),
            )
            print(f"\n=== final ({len(presult.stages)} stages) ===")
            print(presult.final)
            sys.exit(0)
        if dual:
            print(f"Dual loop (propose + critique) — goal: {goal}")
            result = run_dual_loop(
                goal, generator=claude_responder(), critic=claude_responder(),
                on_step=lambda s, prop, crit: _print(s, f"PROPOSAL:\n{prop}", f"CRITIQUE:\n{crit}"),
            )
        else:
            print(f"Single loop — goal: {goal}")
            result = run_loop(
                goal, responder=claude_responder(),
                on_step=lambda s, resp: _print(s, resp),
            )
        print(f"\n=== done={result.done} after {result.iterations} iteration(s) ===")
        print(result.final)
    except Exception as exc:
        print("An error occurred:", exc)
        sys.exit(1)
