"""Export record-derived metrics without changing results or skills."""
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from lab.compare import build_table, load_runs


def main():
    runs = load_runs()
    groups = defaultdict(list)
    for run in runs:
        groups[(run["condition"], run["role"])].append(run)
    metrics = {}
    for (condition, role), records in groups.items():
        checks = [c for r in records for c in r["checks"]]
        tech = [c for c in checks if not c["name"].startswith("rule_")]
        rules = [c for c in checks if c["name"].startswith("rule_")]
        metrics[f"{condition}/{role}"] = {
            "score": mean(r["score"] for r in records),
            "tokens": mean(r["tokens"]["total"] for r in records),
            "seconds": mean(r["seconds"] for r in records),
            "technical": [sum(c["passed"] for c in tech), len(tech)],
            "rules": [sum(c["passed"] for c in rules), len(rules)],
            "subagent_calls": sum(r["subagent_calls"] for r in records),
            "skill_reads": [r["skills_read"] for r in records],
        }
    dev = {}
    for path in sorted(Path("results/repeat-learning/skills-auto").glob("*/run.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        final = next((x for x in runs if x["condition"] == "skills-auto" and x["task"] == r["task"]), None)
        dev[r["task"]] = {"dev_score": r["score"], "dev_tokens": r["tokens"]["total"],
                           "dev_skills_read": r["skills_read"],
                           "final_score": final["score"] if final else None,
                           "delta": final["score"] - r["score"] if final else None}
    output = {"groups": metrics, "dev_comparison": dev,
              "runs": [{k: r[k] for k in ("task", "condition", "passed", "total", "tokens", "seconds",
                                          "subagent_calls", "skills_read", "error", "skills_modified")} for r in runs]}
    Path("report/metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path("report/table.md").write_text(build_table(runs) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
