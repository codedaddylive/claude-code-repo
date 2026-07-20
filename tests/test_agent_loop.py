#!/usr/bin/env python3
"""Offline tests for agent_loop — no API key or network required.

Uses fake responders (plain callables) to verify loop control flow:
  1. Loop stops when the responder emits the DONE_MARKER
  2. Loop respects max_iterations when the goal is never signalled met
  3. DONE_MARKER is stripped from the final answer
  4. Dual loop stops when the critic approves
  5. Input guards reject empty goals / bad budgets

Usage:  python tests/test_agent_loop.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_loop import (  # noqa: E402
    DONE_MARKER,
    PIPELINE_ROLES,
    run_dual_loop,
    run_loop,
    run_pipeline,
)


def test_stops_on_done_marker():
    calls = {"n": 0}

    def responder(prompt):
        calls["n"] += 1
        # Signal done on the 3rd iteration.
        return "answer" + (f"\n{DONE_MARKER}" if calls["n"] == 3 else "")

    result = run_loop("some goal", responder, max_iterations=10)
    assert result.done is True, "should have stopped on the done marker"
    assert result.iterations == 3, f"expected 3 iterations, got {result.iterations}"
    assert DONE_MARKER not in result.final, "done marker should be stripped"
    print("PASS: stops on done marker (3 iterations)")


def test_respects_max_iterations():
    result = run_loop("never done", lambda p: "still working", max_iterations=4)
    assert result.done is False, "should not report done"
    assert result.iterations == 4, f"expected 4 iterations, got {result.iterations}"
    assert result.final == "still working"
    print("PASS: respects max_iterations budget")


def test_dual_loop_stops_on_approval():
    rounds = {"n": 0}

    def generator(prompt):
        return f"proposal v{rounds['n'] + 1}"

    def critic(prompt):
        rounds["n"] += 1
        return DONE_MARKER if rounds["n"] == 2 else "needs more detail"

    result = run_dual_loop("build X", generator, critic, max_iterations=5)
    assert result.done is True
    assert result.iterations == 2, f"expected 2 iterations, got {result.iterations}"
    assert result.final == "proposal v2"
    print("PASS: dual loop stops when critic approves (2 iterations)")


def test_pipeline_runs_all_roles_in_order():
    calls = {"n": 0}

    def responder(prompt):
        calls["n"] += 1
        return f"output-{calls['n']}"

    result = run_pipeline("build a thing", responder=responder)
    assert len(result.stages) == len(PIPELINE_ROLES) == 4
    roles = [s["role"] for s in result.stages]
    assert roles == ["Architect", "Engineer", "Reviewer", "Optimizer"], roles
    assert result.final == "output-4", result.final
    print("PASS: pipeline runs all 4 roles in order, final = optimizer output")


def test_pipeline_per_role_models():
    def make(tag):
        return lambda prompt: f"{tag}-said-something"

    responders = {
        "Architect": make("claude"),
        "Engineer": make("grok"),
        "Reviewer": make("gemini"),
        "Optimizer": make("claude"),
    }
    result = run_pipeline("task", responders=responders)
    outputs = {s["role"]: s["output"] for s in result.stages}
    assert outputs["Architect"] == "claude-said-something"
    assert outputs["Engineer"] == "grok-said-something"
    assert outputs["Reviewer"] == "gemini-said-something"
    assert result.final == "claude-said-something"
    print("PASS: pipeline assigns a different model per role")


def test_pipeline_transcript_accumulates():
    def responder(prompt):
        return "X"

    # Capture the prompt each role receives via on_step is not enough; inspect stages.
    captured = []
    run_pipeline("t", responder=lambda p: (captured.append(p) or "X"))
    # Optimizer (4th) prompt must contain earlier role headers.
    optimizer_prompt = captured[-1]
    for role in ("Architect", "Engineer", "Reviewer"):
        assert f"## {role}" in optimizer_prompt, f"{role} missing from optimizer context"
    print("PASS: pipeline accumulates prior-role output into later prompts")


def test_input_guards():
    for bad_goal in ("", "   "):
        try:
            run_loop(bad_goal, lambda p: "x")
            raise AssertionError("expected ValueError for empty goal")
        except ValueError:
            pass
    try:
        run_loop("ok", lambda p: "x", max_iterations=0)
        raise AssertionError("expected ValueError for max_iterations=0")
    except ValueError:
        pass
    print("PASS: input guards reject empty goal / bad budget")


if __name__ == "__main__":
    tests = [
        test_stops_on_done_marker,
        test_respects_max_iterations,
        test_dual_loop_stops_on_approval,
        test_pipeline_runs_all_roles_in_order,
        test_pipeline_per_role_models,
        test_pipeline_transcript_accumulates,
        test_input_guards,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"FAIL: {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
