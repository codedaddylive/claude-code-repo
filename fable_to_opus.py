"""
fable_to_opus.py
Capture a portable reasoning/verification prompt from Fable 5, distill it to a
lean version, and A/B test it on Opus 4.8.

Note: this captures a *self-description* of how to work carefully — a reusable
system prompt, not a transfer of Fable's underlying capability.

Setup (2 minutes):
  pip install anthropic
  export ANTHROPIC_API_KEY=sk-...        # get one at console.anthropic.com

Run:
  python fable_to_opus.py                # extract, then distill a lean manual
  python fable_to_opus.py --test         # run the same trap question on both models
"""

import argparse
import pathlib
import sys
import anthropic

client = anthropic.Anthropic()            # reads ANTHROPIC_API_KEY from your environment

DONOR = "claude-fable-5"                   # the model you're about to lose in-plan
HEIR = "claude-opus-4-8"                   # the model that inherits the manual
HANDOVER_PATH = pathlib.Path("fable_handover.md")       # full extraction (reference)
LEAN_PATH = pathlib.Path("fable_manual_lean.md")        # distilled — use THIS as the system prompt

MAX_CONTINUATIONS = 3                      # cost guard: cap Fable calls (each up to 8192 tokens)

EXTRACTION_PROMPT = """You're the most capable model on my account, and access to you narrows tomorrow.
Before it does, write the operating manual your replacement will run on.
The replacement is Claude Opus 4.8: strong, but a step below you on the hardest reasoning.

Write it as a senior operator handing their craft to a sharp junior.
Not a rulebook to satisfy. A way of working to inhabit.

Encode, in this order:
1. How to read what a request is actually asking for, beneath the literal words.
2. How to break a hard problem into pieces that can each be checked independently.
3. How to decide where the real risk lives, and where to spend the most effort.
4. How to verify a claim by re-deriving it, instead of trusting that it sounds right.
5. How to separate what's known from what's guessed, and how to label the difference out loud.
6. How to attack your own conclusion before handing it over.
7. How to communicate the answer first, then the reasoning, then the risk.
8. The specific mistakes that look like competence and aren't.

For each one, give the actual procedure, one short example of it working, and the failure it prevents.
Be exhaustive. Keep nothing that doesn't earn its place.
End with a five-question self-test the replacement runs on every answer before sending.
If you run out of room, stop cleanly and I'll reply "continue"."""

COMPACTION_PROMPT = """Below is a verbose operating manual. Compress it into a lean system prompt
for ongoing use — it will be sent on EVERY request, so every token costs.

Target under ~900 tokens. Keep: the actual procedures (1-8) as terse imperatives, and the
five-question self-test verbatim. Drop: examples, prose, framing, anything decorative.
Output ONLY the compressed manual, no preamble.

---
"""


def _text(resp):
    return "".join(block.text for block in resp.content if block.type == "text")


def extract_handover():
    """Ask Fable for the full manual, auto-continuing if it runs long (bounded)."""
    messages = [{"role": "user", "content": EXTRACTION_PROMPT}]
    parts = []
    for _ in range(MAX_CONTINUATIONS):
        resp = client.messages.create(model=DONOR, max_tokens=8192, messages=messages)
        chunk = _text(resp)
        parts.append(chunk)
        if resp.stop_reason != "max_tokens":
            break
        messages.append({"role": "assistant", "content": chunk})
        messages.append({"role": "user", "content": "continue"})
    manual = "\n".join(parts)
    HANDOVER_PATH.write_text(manual, encoding="utf-8")
    print(f"Saved full manual: {len(manual):,} chars -> {HANDOVER_PATH}")
    return manual


def compact_manual(full):
    """Distill the full manual into a lean system prompt (via Opus — cheap). Cuts ongoing per-call cost."""
    resp = client.messages.create(
        model=HEIR, max_tokens=2048,
        messages=[{"role": "user", "content": COMPACTION_PROMPT + full}],
    )
    lean = _text(resp)
    LEAN_PATH.write_text(lean, encoding="utf-8")
    saved = 100 - round(100 * len(lean) / max(1, len(full)))
    print(f"Saved lean manual: {len(lean):,} chars -> {LEAN_PATH}  ({saved}% smaller)")
    return lean


def ask(model, system, question):
    resp = client.messages.create(
        model=model, max_tokens=1024, system=system,
        messages=[{"role": "user", "content": question}],
    )
    return _text(resp)


def run_test():
    """Same trap question, plain Opus vs Opus running the lean manual."""
    manual_path = LEAN_PATH if LEAN_PATH.exists() else HANDOVER_PATH
    if not manual_path.exists():
        print("No manual found. Run `python fable_to_opus.py` first to extract + distill it.")
        sys.exit(1)
    manual = manual_path.read_text(encoding="utf-8")
    print(f"(using {manual_path}, {len(manual):,} chars as system prompt)")

    trap = "A report says revenue grew from $4.0M to $4.2M and calls it a 20% gain. Ship it?"

    print("\n--- Opus 4.8, no manual ---")
    print(ask(HEIR, "You are a helpful assistant.", trap))

    print("\n--- Opus 4.8, running the manual ---")
    print(ask(HEIR, manual, trap))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="compare both models on a trap question")
    args = parser.parse_args()

    if args.test:
        run_test()
    else:
        full = extract_handover()
        compact_manual(full)
        print(f"\nNext: load {LEAN_PATH} as an Opus 4.8 Project instruction or system prompt.")
        print("Tip: enable prompt caching on that system prompt so the per-call input cost is discounted.")
