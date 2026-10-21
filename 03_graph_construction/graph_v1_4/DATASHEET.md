# Datasheet — Indian Railway Network Physical Station Graph, v1.4

Following Gebru et al., *Datasheets for Datasets* (CACM 64(12), 2021).
Release date 2026-10-12 · supersedes v1.3 · `graph_v1_4/`

Two companion documents are not optional reading: **`FITNESS.md`** states which
conclusions this dataset supports and which it never will, and **`docs/STABILITY.md`** is
the contract for code that builds on it.

---

## Motivation

**Why was it created?** Every published graph of the Indian railway network is built from
timetables — Sen et al. (2003, 587 stations), Ghosh et al., Bhatia et al. (2015, 809
stations). A timetable graph is necessarily small (it sees only served stations),
externally unvalidatable (its source is its only reference) and attribute-free (a
timetable records no track). The field has studied Indian Railways as a *service* system
and never as a *physical* one. This dataset is the physical network: nodes are stations,
edges are the track sections between consecutive stations.

**Who created it?** Bhuvanesh Vinjamuri (data engineering and provenance), as the primary
research dataset of the Rail-Intel project.

**Who funded it?** No external funding.

---

## Composition

**What do the instances represent?** 9,095 nodes — 8,621 stations with a known code and
474 operational junctions with no passenger stop — and 9,759 undirected physical track
sections totalling 74,849.7 route kilometres. A derived service layer adds 16,703 directed
station pairs with observed running times and trains per day.

**Is it a sample or the whole population?** It aims at the whole Indian Railways network
and falls short in known, enumerated ways. 228 station codes that appear in timetables are
absent from the graph (`station_code_crosswalk.csv`), 39 more are unresolvable, and 82 node
pairs hold one real station as two nodes. It is a near-census with a documented deficit
register, not a sample.

**What does each instance consist of?** Per node: identity, name, WGS84 position, state,
zone, component membership, degree, and the provenance of each derived value. Per edge:
endpoints, route kilometres with its source and a lower-bound flag, straight-line chord,
official timetable distance where one exists, gauge, track count, zone, corridor,
bridge/tunnel presence, and service load. Full per-column reference in `SCHEMA.md`, which
is generated from the shipped files.

**Is any information missing?** Yes, and it is flagged rather than imputed:

- **25.3% of route kilometres is a straight-line floor**, not a measurement
  (`length_is_lower_bound`). Any kilometre total must state this.
- **Declared sectional speeds are unusable**, and so is `travel_time_min`, which derives
  from them. Use `observed_speed_kmph` from the service layer.
- 1,312 sections carry no recorded service, largely because suburban trains are absent
  from the source timetable. Zero there means *unmeasured*, not unused.
- No capacity, no signalling, no turn restrictions, no electrification per section, no
  freight.
- 17 components (0.41% of nodes) sit outside the giant component.

**Are there errors or redundancies?** Known and enumerated: 823 unadjudicated
length disagreements against official distances, 90 edges still shorter than their own
straight line, 71 OSM station-code collisions that kept a coordinate-correction queue from
being applied, and the 82 duplicate node pairs above. `FITNESS.md` §6 is the register.

**Does it contain confidential or personal data?** No. It describes infrastructure.
No personal data at any stage.

---

## Collection

**How was it acquired?** From three independent kinds of source, kept deliberately
separate by role:

| role | source | scale |
|---|---|---|
| **construction** | national railway GIS polylines | 119,446 segments |
| **validation** | timetables 2015, 2017, 2024 | 416,970 stop records |
| **validation** | IIT Kharagpur RSTGCN consecutive-stop distances | 8,873 comparable pairs |

**The separation is the methodological point.** Topology was built from geometry alone.
The timetables were never used in construction, which leaves them available as an external
test set — something no prior Indian-railway graph has, because each had a single source
and could only check itself.

**Over what timeframe?** Sources span 2015–2025; the GIS layer was last modified January
2025. Construction and repair ran September–October 2026.

**Ethical review?** Not applicable — infrastructure data, no human subjects.

---

## Preprocessing

**What was done?** Segments → corridors → reconstructed spines → tiered station matching →
ordering along the spine → ordered chains → **junction stitching** → attribute enrichment.
Junction stitching is the named operator that resolves rail-specific chain fragmentation
and raises the giant component from 59.4% to 99.6%; it is the dataset's main methodological
contribution. Five repair modules (E-702…E-706) then corrected station-code identity,
trunk wiring, missing links, the service layer and train frequency.

**Is the raw data available?** The inputs are retained and hashed in the manifest. Every
output regenerates from `make v14` in about a minute.

**Are manual corrections traceable?** Yes, and only through one channel. 179 rows in
`OVERRIDES.csv`, each carrying its evidence, reapplied on every rebuild. A row without
evidence stops the build, and nobody edits exported files by hand (D-054). A correction
that is not in the overrides file does not exist.

---

## Uses

**What has it been used for?** Severance criticality of the national network (E-709):
283 corridors with no alternative route, the stations each isolates and the daily traffic
depending on it. It independently recovered the Siliguri "Chicken's Neck" corridor from
geometry alone — isolating all 327 Northeast-state stations — and correctly predicted the
blast radius of the July 2025 Lumding–Badarpur landslide. Also the degree-distribution
theory check (E-710) and a conclusion-robustness sweep (E-711).

**What is it suitable for?** Connectivity and reachability; shortest physical route
distance (median error 0.72% against the 2024 timetable, 95.69% of train routes within
5%); cut points and bridges; corridor and regional load using `trains_per_day`; detour and
circuity; observed section runtimes.

**What should it not be used for?** These are not "not yet" — they need data no held source
contains:

- **Node-level criticality ranking.** 228 absent stations and 82 duplicate node pairs
  understate exactly the junctions a ranking is about. Betweenness is unstable: 15 of the
  top 50 moved under one round of repair.
- **Absolute path kilometres**, given the 25.3% lower bound.
- **Capacity, congestion or delay as a mechanism** — no capacity, no signalling,
  undirected, no turn restrictions.
- **Anything involving freight.**
- **Exact centrality values.** Report ranks and classes.

**Is there anything that might cause harm or unfair treatment?** The dataset could be used
to reason about where the network is most vulnerable to disruption. That information is
already extensively published and debated in the Indian press and in policy documents —
the Siliguri corridor's significance is not a secret this dataset reveals. Accessibility
results computed from it should not be read as statements about communities, since station
absence is a data artifact and would understate service to exactly the places most likely
to be under-recorded.

---

## Distribution

**How will it be distributed?** Not yet distributed. The graph derives from a GIS source
whose redistribution terms are restrictive: schema evidence identifies it as an export of
Esri India's Living Atlas "Railway Tracks" layer, whose portal terms do not permit export
for offline use (`publication/SOURCE_LICENCE_INVENTORY.md` §8, D-057).

The honest position, publishable as it stands:

> The construction pipeline, the analysis code and the documentation are released under an
> open licence. Redistribution terms for the underlying GIS source have not been
> established, so the derived graph is described and fully reproducible from the pipeline,
> with deposit of the artifact itself pending that determination.

**What licence applies?** Code MIT, prose CC BY 4.0, dataset not yet licensable — see
`LICENSES.md`. The split is deliberate: the method and the code remain citable even if the
artifact cannot be deposited.

**Route to an open release.** Rebuild the topology from the OpenStreetMap extracts already
held in `external_data/` (ODbL, pinned by commit and hash). That is weeks of construction
work, because the corridor and spine logic is shaped around the current source's junction
semantics, and it is a roadmap item.

---

## Maintenance

**Who maintains it?** Bhuvanesh Vinjamuri.

**Will it be updated?** v1.4 is frozen under D-055 and is never edited in place. An
amendment is a new release with its own gates and manifest, and the grounds are narrow: an
analysis result demonstrably wrong *because of* the graph, on a named reproducible case.
Discovering a defect is not grounds; defects are recorded as properties in `FITNESS.md` §6.

**How is drift prevented?** Nine release gates must pass or the build fails. A regression
suite (`make test`, 30 tests) asserts the counts, the schema, the gate thresholds, the
manifest hashes and the published findings against reviewed golden values. The suite has
already caught a hand-edited release file and a published caveat that had drifted from its
own measurement.

**Is it reproducible?** `make v14` rebuilds it deterministically. Within one environment
all 24 outputs are byte-identical on rebuild. Across two machines 10 of 12 release files
are byte-identical; the two exceptions are the parquet copies, because Arrow embeds its
writer version, so each file carries a `byte_reproducible` flag and CSV is canonical.

**How can someone contribute or report a problem?** Through `OVERRIDES.csv` with evidence,
or by raising a case that meets the D-055 grounds for a new release.
