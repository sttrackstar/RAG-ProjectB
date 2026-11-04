"""Observability: log every model and tool call so a run can be inspected later.

Each event is one JSON line in OBSERVABILITY_LOG (default server/data/runs.jsonl,
git-ignored). Events that happen during run_agent share that run's id.
"""
import contextvars
import functools
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_FILE = Path(__file__).resolve().parent / "data" / "runs.jsonl"

_current_run = contextvars.ContextVar("current_run", default=None)
_write_lock = threading.Lock()


def _log_file() -> Path:
    return Path(os.environ.get("OBSERVABILITY_LOG", DEFAULT_LOG_FILE))


def log_event(event: dict) -> None:
    """Append one event (with a timestamp and the current run id) to the log."""
    record = {"time": datetime.now(timezone.utc).isoformat(), "run_id": _current_run.get(), **event}
    path = _log_file()
    try:
        with _write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as log:
                log.write(json.dumps(record, default=str) + "\n")
    except OSError:
        pass  # logging must never break the agent


def start_run(goal: str, user_id=None) -> str:
    run_id = uuid.uuid4().hex
    _current_run.set(run_id)
    log_event({"type": "run_start", "goal": goal, "user_id": user_id})
    return run_id


def end_run(result: dict, duration_ms: float) -> None:
    log_event({
        "type": "run_end",
        "answer": result.get("answer"),
        "steps": len(result.get("steps", [])),
        "duration_ms": round(duration_ms),
    })
    _current_run.set(None)


def observe(kind: str, describe_input=None):
    """Decorator that logs a call's input, output and latency.

    kind: "llm" or "tool". describe_input(*args, **kwargs) picks what to record
    as the input (defaults to the raw arguments).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            event = {
                "type": kind,
                "name": func.__name__,
                "input": describe_input(*args, **kwargs) if describe_input else {"args": args, "kwargs": kwargs},
            }
            try:
                output = func(*args, **kwargs)
            except Exception as exc:
                event.update(error=repr(exc), latency_ms=round((time.perf_counter() - started) * 1000))
                log_event(event)
                raise
            event.update(output=output, latency_ms=round((time.perf_counter() - started) * 1000))
            log_event(event)
            return output
        return wrapper
    return decorator


def _read_events() -> list:
    path = _log_file()
    if not path.exists():
        return []
    events = []
    with path.open(encoding="utf-8") as log:
        for line in log:
            try:
                events.append(json.loads(line))
            except ValueError:
                continue  # skip a partly written or corrupted line
    return events


def list_runs(limit: int = 20, user_id=None) -> list:
    """Summaries of the most recent runs, newest first (only user_id's, if given)."""
    runs = {}
    for event in _read_events():
        run_id = event.get("run_id")
        if not run_id:
            continue
        run = runs.setdefault(run_id, {"run_id": run_id, "llm_calls": 0, "tool_calls": 0})
        if event["type"] == "run_start":
            run.update(goal=event.get("goal"), started=event["time"], user_id=event.get("user_id"))
        elif event["type"] == "run_end":
            run.update(answer=event.get("answer"), duration_ms=event.get("duration_ms"))
        elif event["type"] == "llm":
            run["llm_calls"] += 1
        elif event["type"] == "tool":
            run["tool_calls"] += 1
    if user_id is not None:
        runs = {key: run for key, run in runs.items() if run.get("user_id") == user_id}
    # The log is append-only, so file order is start order (timestamps can tie).
    newest_first = list(runs.values())[::-1]
    return newest_first[:limit]


def get_run(run_id: str, user_id=None) -> list:
    """Every event logged for one run, in order. Empty if it isn't user_id's run."""
    events = [event for event in _read_events() if event.get("run_id") == run_id]
    if user_id is not None:
        start = next((event for event in events if event["type"] == "run_start"), None)
        if start is None or start.get("user_id") != user_id:
            return []
    return events
