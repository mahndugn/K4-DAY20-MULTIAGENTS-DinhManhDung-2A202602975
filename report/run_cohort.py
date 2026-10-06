"""Run a separate, sequential comparison without changing frozen skills.

Run inside the original Linux lab image. Resume skips recorded model outcomes,
including recursion failures; API/infrastructure errors stop the cohort.
"""
import argparse
import json
import os
from pathlib import Path

from lab.runner import run_task
from lab.tasks import list_tasks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--repeat-learning", action="store_true")
    args = parser.parse_args()
    conditions = ("skills-auto",) if args.repeat_learning else ("baseline", "subagents", "skills-auto")
    tasks = list_tasks("learn") if args.repeat_learning else list_tasks()
    for condition in conditions:
        for task in tasks:
            path = Path(args.results) / condition / task.id / "run.json"
            if path.exists():
                record = json.loads(path.read_text(encoding="utf-8"))
                assert record["model"] == os.environ["LAB_MODEL"], "Mixed models"
                assert record["recursion_limit"] == 100, "Mixed recursion limits"
                # Older records predate the temperature metadata; the manifest
                # documents their explicit Docker environment override.
                assert record.get("temperature_requested", 0) == float(os.getenv("LAB_TEMPERATURE", "0")), "Mixed temperatures"
            else:
                record = run_task(task.id, condition, args.results, recursion_limit=100)
            print(json.dumps({k: record[k] for k in
                              ("condition", "task", "passed", "total", "tokens", "seconds", "error")}, ensure_ascii=False), flush=True)
            assert not record["skills_modified"], "Frozen skills were modified"
            if record["error"] and not record["error"].startswith("GraphRecursionError:"):
                raise RuntimeError("Infrastructure/model API failure retained; stop rather than mix results")


if __name__ == "__main__":
    main()
