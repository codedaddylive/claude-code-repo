"""Loop engineering — iterate an agent toward a goal instead of one-shot prompting.

Technique applied from *"Stop Prompting. Start Looping."*: rather than sending a
single prompt and accepting whatever comes back, run the model in a refine loop
(generate -> self-check -> refine) and stop when the goal is met or an iteration
budget is exhausted. A two-agent variant lets one model generate while another
critiques — e.g. Claude proposes, Gemini reviews — which ties the loop into
ARIA's multi-agent theme.

The core (`run_loop` / `run_dual_loop`) is model-agnostic: it drives any
``responder`` callable ``(str) -> str``. Default responders wire up the repo's
Claude and Gemini clients, but you can pass a fake responder for offline testing.

Usage:
    from agent_loop import run_loop, gemini_responder, claude_responder

    result = run_loop(
        "Write a regex that matches an ISO-8601 date, then verify it.",
        responder=gemini_responder(),      # or claude_responder()
        max_iterations=5,
    )
    print(result.final, f"({result.iterations} iterations, done={result.done})")

    # CLI:
    #   python agent_loop.py "Refine a one-paragraph summary of this repo." --model gemini
    #   python agent_loop.py "Explain event loops." --model grok
    #   python agent_loop.py "Design a caching layer." --dual   # Claude proposes, Gemini critiques
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


# --- Default responders backed by the repo's clients -----------------------

def gemini_responder(model: str | None = None) -> Responder:
    """Responder backed by gemini_interaction.get_gemini_response."""
    from gemini_interaction import get_gemini_response

    def _respond(prompt: str) -> str:
        return get_gemini_response(prompt, model=model)

    return _respond


def grok_responder(model: str | None = None) -> Responder:
    """Responder backed by grok_interaction.get_grok_response."""
    from grok_interaction import get_grok_response

    def _respond(prompt: str) -> str:
        return get_grok_response(prompt, model=model)

    return _respond


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


def _resolve_responder(name: str) -> Responder:
    name = (name or "gemini").lower()
    if name.startswith("gemini"):
        return gemini_responder()
    if name.startswith("claude"):
        return claude_responder()
    if name.startswith("grok"):
        return grok_responder()
    raise ValueError(f"Unknown model '{name}'. Use 'gemini', 'claude', or 'grok'.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    dual = "--dual" in args
    args = [a for a in args if a != "--dual"]

    model = "gemini"
    if "--model" in args:
        i = args.index("--model")
        model = args[i + 1] if i + 1 < len(args) else model
        del args[i : i + 2]

    goal = " ".join(args) or "Write a haiku about iterating toward a goal."

    def _print(step, *payload):
        print(f"\n--- iteration {step} ---")
        for p in payload:
            print(p)

    try:
        if dual:
            print(f"Dual loop (Claude proposes, Gemini critiques) — goal: {goal}")
            result = run_dual_loop(
                goal, generator=claude_responder(), critic=gemini_responder(),
                on_step=lambda s, prop, crit: _print(s, f"PROPOSAL:\n{prop}", f"CRITIQUE:\n{crit}"),
            )
        else:
            print(f"Single loop ({model}) — goal: {goal}")
            result = run_loop(
                goal, responder=_resolve_responder(model),
                on_step=lambda s, resp: _print(s, resp),
            )
        print(f"\n=== done={result.done} after {result.iterations} iteration(s) ===")
        print(result.final)
    except Exception as exc:
        print("An error occurred:", exc)
        sys.exit(1)
