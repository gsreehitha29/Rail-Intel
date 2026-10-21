"""G5 - split the proposals into what the verification accepted and what it did not.

Accepted: the topology repairs (remove_edge, add_edge). They improve every measure
and leave connectivity untouched.

Deferred: set_length and move_node. Both were tested as classes and both made things
worse, so they are handed on with their evidence rather than applied here:
  set_length  worsens route error in 2017 and 2024 and worsens structure, even on
              top of the fixed topology. Lengths need per-edge adjudication against
              audit lists 03/04/05 - they are the lengths gap, not a wiring repair.
  move_node   changes no route at all (lengths are explicit), and moving all 361
              nodes to their OSM positions exposes ~290 further under-measured edges.
              It belongs to a coordinates gap of its own.

Run:  python finalize.py <repairs dir> <output dir>
"""
import json, sys
from pathlib import Path

import pandas as pd

REP, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
rp = pd.read_csv(REP / "repairs_proposed.csv")

ACCEPTED = {"remove_edge", "add_edge"}
acc = rp[rp.action.isin(ACCEPTED)].copy()
def_ = rp[~rp.action.isin(ACCEPTED)].copy()

ov = pd.DataFrame(dict(
    audit_file="G5_trunk_wiring",
    item_id=acc.item,
    field=acc.action.map({"remove_edge": "edge", "add_edge": "edge"}),
    current_value=acc.current,
    new_value=acc.new.fillna(""),
    action=acc.action,
    evidence=acc.evidence,
    source_url="",
    reviewer="",
    review_date="",
    notes=("attested by " + acc.trains.astype(int).astype(str) + " trains"
           + acc.restores.fillna("").map(lambda s: f"; restores {s}" if s else "")),
))
ov.to_csv(OUT / "OVERRIDES_G5.csv", index=False)
def_.to_csv(OUT / "deferred_findings.csv", index=False)

summary = dict(
    accepted={k: int(v) for k, v in acc.action.value_counts().items()},
    deferred={k: int(v) for k, v in def_.action.value_counts().items()},
    accepted_note="applied: verified to improve route error and structure",
    deferred_note="not applied: each class made the graph worse when tested on its own")
json.dump(summary, open(OUT / "finalize.json", "w"), indent=2)
print(json.dumps(summary, indent=1))
