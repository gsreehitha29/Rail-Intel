"""E-717 - build graph v1.4.1. One command, deterministic, gated.

    python run.py              the stages of the current milestone, in order
    python run.py <stage>      one stage: overrides | graph | service | gates

Milestone A1 runs overrides, graph, service and gates. The docs and manifest stages
are added at A3, when v1.4.1 is frozen; until then graph_v1_4_1/ is a working build,
not a release.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v141                                                           # noqa: E402
from v141 import v14                                                  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "03_graph_construction" / f"graph_{v141.SLUG}"
ORDER = ["overrides", "graph", "service", "gates"]


def run(stage):
    OUT.mkdir(parents=True, exist_ok=True)
    if stage == "overrides": return v141.stage_overrides(ROOT, OUT)
    if stage == "graph":     return v141.stage_graph(ROOT, OUT)
    if stage == "service":   return v14.stage_service(ROOT, OUT)
    if stage == "gates":
        r = v14.stage_gates(ROOT, OUT)
        (OUT / "gates.json").write_text(json.dumps(r, indent=1, default=str))
        return r
    raise SystemExit(f"unknown stage {stage!r}; one of {ORDER}")


def main():
    failed = False
    for s in sys.argv[1:] or ORDER:
        r = run(s)
        print(f"\n=== {s}\n{json.dumps(r, indent=1, default=str)[:2500]}")
        if s == "gates" and not r["all_passed"]:
            failed = [k for k, v in r["gates"].items() if not v]
    if failed:
        print(f"\nBUILD FAILED - gates not met: {failed}")
        raise SystemExit(1)
    print(f"\ngraph {v141.VERSION} (working build) in {OUT}")


if __name__ == "__main__":
    main()
