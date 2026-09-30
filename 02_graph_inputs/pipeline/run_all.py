"""
Run the whole graph-input pipeline end-to-end, deterministically, from the raw
source files. No notebook kernel state involved.

    python pipeline/run_all.py

Every stage is idempotent and rewrites its own outputs. Stage 03 is the only
slow one (it streams the 88 MB GeoJSON); it caches to pipeline/cache/ so later
runs of stages 04+ are instant.
"""

from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

STAGES = [
    ("s01_canonical_junctions", "Canonical junction layer"),
    ("s02_corridors", "Authoritative corridor table"),
    ("s03_extract_geometry", "Segment geometry extraction"),
    ("s04_corridor_paths", "Corridor spine reconstruction"),
    ("s05_junction_coordinates", "Geometry-derived junction coordinates"),
    ("s06_station_matching", "Tiered station matching"),
    ("s07_station_sequences", "Ordered station sequences"),
    ("s08_assemble_and_validate", "Assemble package + QA"),
    ("s09_graph_dataset", "Clean normalised dataset for Phase 3"),
    ("s10_verify_dataset", "Verify shipped dataset"),
]


def main() -> None:
    t0 = time.time()
    for mod_name, label in STAGES:
        print("\n" + "#" * 78)
        print(f"# {label}   ({mod_name}.py)")
        print("#" * 78)
        t = time.time()
        importlib.import_module(mod_name).main()
        print(f"\n[{label} finished in {time.time() - t:.1f}s]")
    print("\n" + "=" * 78)
    print(f"PIPELINE COMPLETE in {time.time() - t0:.1f}s")
    print("=" * 78)


if __name__ == "__main__":
    main()
