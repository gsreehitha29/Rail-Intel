"""E-712 - generate SCHEMA.md for the release from the shipped files.

Generated, never written: the data dictionary drifted from the schema once already
(it still described a pre-v1.4 shape), so the per-column reference is computed from
`nodes.csv`, `edges.csv` and the service layer on every run. Descriptions live here;
every number comes from the data.

    python gen_schema.py <root> <out dir = graph_v1_4>
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

NODE_DESC = {
    "node_id": "Primary key. Stable for the lifetime of the release (docs/STABILITY.md). Usually the station code.",
    "node_type": "`station` or `junction` - a junction is an operational point with no passenger stop.",
    "node_name": "Station name as it appears in the source. Not normalised; renames coexist (see FITNESS.md §6).",
    "station_code": "Indian Railways station code where one is known. Join through `load_resolver()`, never directly.",
    "longitude": "WGS84 decimal degrees.",
    "latitude": "WGS84 decimal degrees.",
    "coordinate_source": "Which input supplied the position.",
    "state": "State or union territory, assigned by point-in-polygon against datameet Admin2 (D-052).",
    "state_source": "How `state` was derived.",
    "zone_code": "Indian Railways zone (NFR, SR, ...).",
    "zone_source": "How `zone_code` was derived.",
    "state_v12": "The state this node carried in v1.2, kept for audit.",
    "state_v12_disagrees": "True where the polygon assignment overrode the v1.2 label.",
    "code_identity_suspect": "True where the station code may not identify this place - do not key on it.",
    "coord_fixed": "Which release corrected this node's coordinates, if any.",
    "node_origin": "The release or repair module that introduced this node.",
    "merged_from": "Node ids merged into this one during construction.",
    "match_confidence": "Confidence of the station-to-geometry match that placed this node.",
    "match_method": "Which matching tier placed it.",
    "overrides_applied": "Count of OVERRIDES.csv rows that touched this node.",
    "dataset_version": "Release tag, constant within a release.",
    "component_id": "Connected component index; 0 is the giant component.",
    "in_giant": "True for the 99.59% of nodes in the giant component.",
    "degree": "Number of incident sections. Bounded at 7 - see E-710.",
}

EDGE_DESC = {
    "from_node": "Endpoint node_id. Undirected: the pair is unordered.",
    "to_node": "Endpoint node_id.",
    "origin": "The release this edge came from.",
    "edge_id": "Primary key. Stable for the lifetime of the release.",
    "length_km": "**The length to use.** Route kilometres along track between the two stations.",
    "length_source": "How `length_km` was obtained. `lower_bound_straight_line` means it is a floor, not a measurement.",
    "length_is_lower_bound": "**Check this before summing kilometres.** True where `length_km` is a straight-line floor.",
    "length_chord_km": "Great-circle distance between the endpoints. `length_km` is never below it.",
    "official_km": "Consecutive-stop distance from a timetable, where one exists. Never used to build topology.",
    "official_source": "Which timetable supplied `official_km`.",
    "official_conflict": "True where official sources disagree with each other beyond tolerance.",
    "official_detour": "True where the official distance implies a detour the geometry does not show.",
    "official_sources_disagree": "True where two timetables disagree on this pair.",
    "spine_disagrees_official": "True where the reconstructed spine length disagrees with the official distance.",
    "raised_to_chord": "True where a sub-chord length was raised to the straight-line distance.",
    "length_km_v12": "The length this edge carried in v1.2, kept for audit.",
    "speed_used_kmph": "Declared sectional speed from the source. **Unusable** - use observed runtimes from the service layer.",
    "speed_source": "Where the declared speed came from.",
    "edge_origin": "Construction stage that created this edge.",
    "corridor_id": "The reconstructed corridor this section belongs to.",
    "gauge_code": "BG, MG or NG.",
    "zone_code": "Indian Railways zone.",
    "n_tracks": "Declared track count. A row is a *section*, not a track: parallel tracks collapse to one edge.",
    "bridge_present_edge": "A civil bridge lies on this section (from the source's flag, not a graph bridge).",
    "tunnel_present_edge": "A tunnel lies on this section.",
    "service_direct": "Count of trains calling at both endpoints consecutively.",
    "service_load": "Distinct trains traversing this section. **Overstates daily traffic 2.03x** - use trains_per_day.",
    "suspect_long_edge": "Flagged as implausibly long for manual review.",
    "geometry_unsupported": "True where no source geometry supports this section.",
    "geometry_source": "Which geometry supported it.",
    "station_match_deficit": "Difference between declared and matched station counts on the parent corridor.",
    "speed_expected_abs_error_kmph": "Validated error estimate on the declared speed.",
    "travel_time_min": "Derived from `speed_used_kmph`, therefore **unusable**; kept for audit only.",
    "service_source": "Which service build populated the service columns.",
    "dataset_version": "Release tag.",
}

SVC_DESC = {
    "from_station": "Origin station code. Resolve with `load_resolver()`.",
    "to_station": "Destination station code.",
    "n_trains": "Distinct trains on this ordered pair. Overstates daily traffic.",
    "trains_per_day": "**The load measure to use.** Distinct dates observed / 30, from September 2024 (E-706).",
    "runtime_min_median": "Observed median running time, minutes.",
    "runtime_min_p10": "10th percentile observed running time.",
    "runtime_min_p90": "90th percentile observed running time.",
    "n_runtime_obs": "Observations behind the runtime figures.",
    "is_direct_physical_edge": "True where the pair is one section in the physical graph.",
    "physical_path_km": "Shortest physical route distance between the pair.",
    "physical_hops": "Sections on that route.",
    "observed_speed_kmph": "physical_path_km / runtime. **Use this, not declared speed.**",
    "physical_graph_release": "Which graph release the routing used.",
}


def table(df: pd.DataFrame, desc: dict, name: str) -> str:
    out = [f"### `{name}` — {len(df):,} rows, {len(df.columns)} columns\n",
           "| column | type | non-null | distinct | example | meaning |",
           "|---|---|---|---|---|---|"]
    for c in df.columns:
        s = df[c]
        nn = s.notna().sum()
        ex = s.dropna()
        ex = "—" if ex.empty else str(ex.iloc[0])[:28]
        d = desc.get(c, "**undocumented — add a description**")
        out.append(f"| `{c}` | {s.dtype} | {nn:,} ({nn/len(df):.0%}) | "
                   f"{s.nunique():,} | `{ex}` | {d} |")
    return "\n".join(out) + "\n"


def main():
    root = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        root / "03_graph_construction" / "graph_v1_4"
    g = root / "03_graph_construction" / "graph_v1_4" / "open"
    s = root / "03_graph_construction" / "service_layer_v1_4" / "open"
    nodes, edges = pd.read_csv(g / "nodes.csv"), pd.read_csv(g / "edges.csv")
    svc = pd.read_csv(s / "service_edges_directed.csv")

    lb_km = edges.loc[edges.length_is_lower_bound, "length_km"].sum() / edges.length_km.sum()
    undoc = ([c for c in nodes.columns if c not in NODE_DESC]
             + [c for c in edges.columns if c not in EDGE_DESC]
             + [c for c in svc.columns if c not in SVC_DESC])

    body = f"""# Schema reference — graph v1.4

**Generated** by `04_analysis_modules/E-712_dataset_package/gen_schema.py` from the
shipped files. Do not edit: regenerate with `make schema`. Every count below is measured,
which is why this file exists — the hand-maintained dictionary drifted from the schema and
`docs/DATA_DICTIONARY.md` still describes a pre-v1.4 shape.

Read `FITNESS.md` before using the data and `docs/STABILITY.md` before building on it.
The supported entry point is:

```python
import sys; sys.path.insert(0, "03_graph_construction")
from railgraph.release import load_graph, load_service, load_resolver, release_info
```

## The four columns that decide whether an analysis is valid

| column | file | why it matters |
|---|---|---|
| `length_is_lower_bound` | edges | {lb_km:.1%} of route km is a straight-line floor, not a measurement. Any kilometre total must say so. |
| `speed_used_kmph`, `travel_time_min` | edges | Declared speeds are unusable. Use `observed_speed_kmph` from the service layer. |
| `service_load` vs `trains_per_day` | edges / service | Distinct-train counts overstate daily traffic 2.03× and reorder 49 of the 100 busiest sections. |
| `in_giant` | nodes | 0.41% of nodes sit outside the giant component and are unreachable from it. |

## Tables

{table(nodes, NODE_DESC, "open/nodes.csv")}
{table(edges, EDGE_DESC, "open/edges.csv")}
{table(svc, SVC_DESC, "service_layer_v1_4/open/service_edges_directed.csv")}
## Other files in the release

| file | what it is |
|---|---|
| `open/rail_graph_v1_4_open.graphml` | the same graph as GraphML, for tools that prefer it |
| `open/nodes.parquet`, `open/edges.parquet` | convenience copies; **not byte-reproducible** across machines, CSV is canonical |
| `OVERRIDES.csv` | 179 manual decisions with evidence, reapplied on every build (D-054) |
| `station_code_crosswalk.csv` | 68 aliases, 228 absent stations, 39 unresolved codes |
| `gates.json` | the nine release gates, their thresholds and measured values |
| `graph_v1_4.manifest.json` | SHA-256 per input and output, with a `byte_reproducible` flag |
| `FITNESS.md` | what this graph supports, what it never will, and the rule for changing it |
| `VALIDATION_v1_4.md` | the validation report, generated by the build |

## Service layer views

`load_service(what=...)` takes `edges` (directed station pairs, above), `hourly`
(departures by hour), `per_edge` (trains over each physical section) and `frequency`
(per-train running days).

## Completeness

{"All columns are documented." if not undoc else
 "**Undocumented columns:** " + ", ".join(f"`{c}`" for c in undoc)}
"""
    (out / "SCHEMA.md").write_text(body, encoding="utf-8")
    print(f"wrote {out / 'SCHEMA.md'}  ({len(body.splitlines())} lines)")
    print("undocumented:", undoc or "none")


if __name__ == "__main__":
    main()
