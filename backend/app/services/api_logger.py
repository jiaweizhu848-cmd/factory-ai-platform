import json
from pathlib import Path
from typing import Any


def write_api_call_log(path: str, entry: dict[str, Any]) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def summarize_api_call_logs(path: str) -> dict[str, Any]:
    log_path = Path(path)
    if not log_path.exists():
        return {
            "status": "ok",
            "total_calls": 0,
            "ok_calls": 0,
            "error_calls": 0,
            "avg_duration_ms": 0,
            "by_caller": {},
            "by_error_code": {},
        }

    total_calls = 0
    ok_calls = 0
    error_calls = 0
    total_duration_ms = 0
    by_caller: dict[str, dict[str, int]] = {}
    by_error_code: dict[str, int] = {}

    with log_path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            total_calls += 1
            status = entry.get("status")
            caller = entry.get("caller") or "unknown"
            duration_ms = int(entry.get("duration_ms") or 0)
            total_duration_ms += duration_ms

            caller_stats = by_caller.setdefault(
                caller,
                {"total": 0, "ok": 0, "error": 0},
            )
            caller_stats["total"] += 1

            if status == "ok":
                ok_calls += 1
                caller_stats["ok"] += 1
            else:
                error_calls += 1
                caller_stats["error"] += 1
                error_code = entry.get("error_code") or "unknown"
                by_error_code[error_code] = by_error_code.get(error_code, 0) + 1

    avg_duration_ms = round(total_duration_ms / total_calls) if total_calls else 0
    return {
        "status": "ok",
        "total_calls": total_calls,
        "ok_calls": ok_calls,
        "error_calls": error_calls,
        "avg_duration_ms": avg_duration_ms,
        "by_caller": by_caller,
        "by_error_code": by_error_code,
    }
