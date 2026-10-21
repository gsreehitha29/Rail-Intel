"""E-708 - build graph v1.4. One command, deterministic, gated.

    python run.py              every stage, in order
    python run.py <stage>      one stage: overrides | graph | service | gates | manifest

The build fails loudly if any gate fails, so a release that drifts cannot be shipped by
accident. Re-running on unchanged inputs reproduces every output hash.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v14                                                            # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "03_graph_construction" / f"graph_{v14.SLUG}"
ORDER = ["overrides", "graph", "service", "gates", "docs", "manifest"]


def run(stage, state):
    OUT.mkdir(parents=True, exist_ok=True)
    if stage == "overrides": return v14.stage_overrides(ROOT, OUT)
    if stage == "graph":     return v14.stage_graph(ROOT, OUT)
    if stage == "service":   return v14.stage_service(ROOT, OUT)
    if stage == "gates":
        r = v14.stage_gates(ROOT, OUT)
        (OUT / "gates.json").write_text(json.dumps(r, indent=1, default=str))
        return r
    if stage == "docs":      return v14.stage_docs(ROOT, OUT, state)
    if stage == "manifest":  return v14.stage_manifest(ROOT, OUT, state)
    raise SystemExit(f"unknown stage {stage!r}; one of {ORDER}")


def main():
    want = sys.argv[1:] or ORDER
    state, failed = {}, False
    for s in want:
        r = run(s, state)
        state[s] = r
        print(f"\n=== {s}\n{json.dumps(r, indent=1, default=str)[:1800]}")
        if s == "gates" and not r["all_passed"]:
            failed = [k for k, v in r["gates"].items() if not v]
    if failed:
        print(f"\nBUILD FAILED - gates not met: {failed}")
        raise SystemExit(1)
    print(f"\ngraph {v14.VERSION} built in {OUT}")


if __name__ == "__main__":
    main()
