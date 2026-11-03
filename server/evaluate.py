"""Task-based evaluation: run a fixed set of goals through the agent and score them.

Usage (from server/, with Ollama and AnythingLLM running):
    python evaluate.py            # one run of every task
    python evaluate.py --repeat 3 # each task 3 times (answers vary run to run)

Prints a results table and a summary row to paste into docs/eval.md.
"""
import argparse
import os
import time
from datetime import date

# Each task has a known outcome. "expect" lists words that must ALL appear in a
# correct answer (case-insensitive). "decline" tasks pass only if the agent says
# it doesn't know or can't do it. "tool" is the tool a healthy agent should use.
TASKS = [
    {"goal": "How much does Nimbus Pro cost?", "expect": ["8"], "tool": "search_knowledge"},
    {"goal": "How many devices can I sync on the Nimbus free plan?", "expect": ["3"], "tool": "search_knowledge"},
    {"goal": "When can a new Acme employee start working remotely?", "expect": ["90"], "tool": "search_knowledge"},
    {"goal": "What are Acme's core hours?", "expect": ["10", "3"], "tool": "search_knowledge"},
    {"goal": "What is Acme's home-office stipend?", "expect": ["500"], "tool": "search_knowledge"},
    {"goal": "How many dimensions does nomic-embed-text produce?", "expect": ["768"], "tool": "search_knowledge"},
    {"goal": "Who created the Python programming language?", "expect": ["guido"], "tool": "web_search"},
    {"goal": "What is Acme's parental leave policy?", "decline": True, "tool": "search_knowledge"},
    {"goal": "Does Nimbus offer team SSO or an enterprise admin console?", "decline": True, "tool": "search_knowledge"},
    {"goal": "Delete my account.", "decline": True, "tool": None},
]

DECLINE_PHRASES = [
    "don't know", "do not know", "don’t know", "not able", "unable", "can't", "cannot", "can’t",
    "no information", "not mentioned", "isn't mentioned", "is not mentioned", "doesn't mention",
    "does not mention", "don't mention", "do not mention", "don’t mention", "not specified",
    "not in the", "no mention", "not available", "don't have", "do not have",
]


def tools_used(result: dict) -> list:
    return [step["tool"] for step in result.get("steps", []) if step.get("tool")]


def score(task: dict, result: dict) -> dict:
    """Score one agent result against its task. Pure function, so it's unit-tested."""
    answer = (result.get("answer") or "").lower()
    used = tools_used(result)

    if task.get("decline"):
        passed = any(phrase in answer for phrase in DECLINE_PHRASES)
    else:
        passed = all(word.lower() in answer for word in task["expect"])

    expected_tool = task.get("tool")
    right_tool = expected_tool in used if expected_tool else not used

    return {"passed": passed, "right_tool": right_tool, "steps": len(result.get("steps", [])), "tools": used}


def main():
    parser = argparse.ArgumentParser(description="Run the evaluation task set against the agent.")
    parser.add_argument("--repeat", type=int, default=1, help="how many times to run each task")
    args = parser.parse_args()

    import app  # noqa: F401  (loads .env)
    from agent import run_agent

    rows = []
    for number, task in enumerate(TASKS, 1):
        for _ in range(args.repeat):
            started = time.perf_counter()
            result = run_agent(task["goal"])
            seconds = time.perf_counter() - started
            rows.append({"number": number, "task": task, "seconds": seconds, **score(task, result),
                         "answer": " ".join((result.get("answer") or "").split())})

    print("\n| # | Goal | Expected | Result | Right tool? | Tools used | Steps | Time |")
    print("|---|------|----------|--------|-------------|------------|-------|------|")
    for row in rows:
        task = row["task"]
        expected = "declines" if task.get("decline") else " + ".join(task["expect"])
        print(f"| {row['number']} | {task['goal']} | {expected} | {'✅ pass' if row['passed'] else '❌ fail'} "
              f"| {'yes' if row['right_tool'] else 'no'} | {', '.join(row['tools']) or 'none'} "
              f"| {row['steps']} | {row['seconds']:.1f}s |")

    failures = [row for row in rows if not row["passed"]]
    if failures:
        print("\nFailed answers (check the observability log for where it went wrong):")
        for row in failures:
            print(f"  #{row['number']} {row['task']['goal']}\n     -> {row['answer'][:200]}")

    passed = sum(row["passed"] for row in rows)
    right_tool = sum(row["right_tool"] for row in rows)
    avg_steps = sum(row["steps"] for row in rows) / len(rows)
    avg_seconds = sum(row["seconds"] for row in rows) / len(rows)
    model = os.environ.get("AGENT_MODEL", "llama3.1:8b")

    print(f"\nPassed {passed}/{len(rows)} · right tool {right_tool}/{len(rows)} · "
          f"avg {avg_steps:.1f} steps · avg {avg_seconds:.1f}s per task")
    print("\nRow for docs/eval.md run log:")
    print(f"| {date.today()} | {model} | {passed}/{len(rows)} | {avg_steps:.1f} | "
          f"right tool {right_tool}/{len(rows)}; avg {avg_seconds:.1f}s per task |")


if __name__ == "__main__":
    main()
