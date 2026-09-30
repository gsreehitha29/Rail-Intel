"""
Stage 01 — Canonical junction layer.

Fixes validation gap #2: the shipped junction/edge files were grouped on raw,
unstripped junction strings, so 36 groups of names that differ only by
whitespace / embedded newlines became separate nodes (and split the graph into
extra components).

Outputs
-------
graph_inputs/junctions_canonical.csv   one row per canonical junction
graph_inputs/junction_name_crosswalk.csv  raw name -> canonical name, with provenance
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    GRAPH_INPUT_VERSION, OUT_DIR, RAW_NETWORK_CSV, banner, classify_junction,
    match_key, normalize_junction_name,
)


def main() -> None:
    banner("STAGE 01 — CANONICAL JUNCTION LAYER")

    df = pd.read_csv(RAW_NETWORK_CSV, low_memory=False)
    print(f"Raw GIS segment rows: {len(df):,}")

    raw_names = pd.concat([df["fromjunction"], df["tojunction"]], ignore_index=True)
    raw_counts = raw_names.value_counts(dropna=True)
    print(f"Distinct raw junction strings (incl. whitespace variants): {len(raw_counts):,}")

    crosswalk = pd.DataFrame({
        "raw_junction_name": raw_counts.index.astype(str),
        "raw_occurrences": raw_counts.values,
    })
    crosswalk["canonical_junction_name"] = crosswalk["raw_junction_name"].apply(
        normalize_junction_name
    )
    crosswalk = crosswalk[crosswalk["canonical_junction_name"] != ""].copy()

    # Flag exactly which raw strings needed repair, and why.
    crosswalk["needed_normalisation"] = (
        crosswalk["raw_junction_name"] != crosswalk["canonical_junction_name"]
    )
    crosswalk["had_embedded_newline"] = crosswalk["raw_junction_name"].str.contains(
        r"[\r\n]", regex=True
    )
    crosswalk["had_edge_whitespace"] = (
        crosswalk["raw_junction_name"].str.strip() != crosswalk["raw_junction_name"]
    )

    n_repaired = int(crosswalk["needed_normalisation"].sum())
    print(f"Raw strings requiring normalisation: {n_repaired}")
    print(f"  with embedded newline/CR: {int(crosswalk['had_embedded_newline'].sum())}")
    print(f"  with leading/trailing whitespace: {int(crosswalk['had_edge_whitespace'].sum())}")

    # Canonical junction table
    grouped = crosswalk.groupby("canonical_junction_name")
    junctions = pd.DataFrame({
        "canonical_junction_name": grouped.size().index,
        "n_raw_variants": grouped.size().values,
        "raw_occurrences": grouped["raw_occurrences"].sum().values,
    })
    junctions["raw_variants"] = grouped["raw_junction_name"].apply(
        lambda s: json.dumps(sorted(s.tolist()))
    ).values
    junctions["merged_from_variants"] = junctions["n_raw_variants"] > 1
    junctions["junction_class"] = junctions["canonical_junction_name"].apply(classify_junction)
    junctions["match_key"] = junctions["canonical_junction_name"].apply(match_key)
    junctions = junctions.sort_values("canonical_junction_name").reset_index(drop=True)
    junctions.insert(0, "junction_id", ["J%05d" % (i + 1) for i in range(len(junctions))])
    junctions["source_file"] = "Railway_Network_.csv"
    junctions["graph_input_version"] = GRAPH_INPUT_VERSION

    crosswalk = crosswalk.merge(
        junctions[["junction_id", "canonical_junction_name"]],
        on="canonical_junction_name", how="left",
    )

    print()
    print(f"Canonical junctions: {len(junctions):,}")
    print(f"  formed by merging >1 raw variant: {int(junctions['merged_from_variants'].sum())}")
    print()
    print("Junction class breakdown:")
    print(junctions["junction_class"].value_counts().to_string())

    junctions.to_csv(OUT_DIR / "junctions_canonical.csv", index=False)
    crosswalk.to_csv(OUT_DIR / "junction_name_crosswalk.csv", index=False)
    print()
    print(f"WROTE {OUT_DIR / 'junctions_canonical.csv'}")
    print(f"WROTE {OUT_DIR / 'junction_name_crosswalk.csv'}")


if __name__ == "__main__":
    main()
