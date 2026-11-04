# E-726 — v2.1-open build (remediation Step 8)

The E-716 build plus the three v2.1 fixes (D-071):
- **D-073 rev. 1:** the station multi-track snap, always on (`run_c1.py`, `osm_build.o3m_extra`).
- **D-072:** 19 rename aliases (`aliases_v2_1.csv`), appended to the crosswalk the build writes.
- **Versioning:** edge ids `v2.1:` / `v2.1p:`, and outputs in `graph_v2_1_open/` and `service_layer_v2_1_open/`. No v2.0 file is read for writing.

```bash
python run_c2.py --stage=c1        # ~100 s on a 4 GB VM
python run_c2.py --stage=joins     # ~45 s
python run_c2.py --stage=graph     # ~30 s
python run_c2.py --stage=service   # ~50 s: 2024 + 2017 service layers, attributes, C2 gates
python validate_c3.py              # ~40 s: C3 gates
python release.py                  # ~8 s: release/rail-intel-v2.1-open-rc1/ and its zip
```

## Results (rc1)

| | v2.0-open | v2.1-open-rc1 |
|---|---|---|
| Nodes / stations / junctions / sections | 12,301 / 9,507 / 2,794 / 13,560 | 11,809 / 9,507 / 2,302 / 13,051 |
| Route km (vs official 69,439) | 70,304.6 (+1.25%) | 69,200.7 (−0.34%) |
| Places view nodes / sections / cycles | 10,024 / 10,514 / 498 | 9,924 / 10,336 / 420 |
| C2 gates / C3 gates | all pass | all pass |
| Station pairs within max(1 km, 5%) of official | 93.6% | 94.0% |
| 2024 train routes: median error / within 5% | 0.38% / 99.2% | 0.31% / 99.3% |
| 2017 train routes within 5% | 81.4% | 88.2% |
| Served cut points agreeing with v1.4.1 | 96.8% | 97.4% |
| 2017 station pairs unroutable | 121 of 27,952 | 85 of 27,997 |
| Zip sha256 (byte-reproducible: two runs, one hash) | b1e39081…eeda | df623e86…ccd3 |

## Tests

`tests/test_v2_1_release.py` (golden figures and the named fixes) and `tests/test_v2_1_spotcheck.py`.

**One spot-check fails:** train 12123 (CSMT–Pune) measures 185.2 km against its timetable's 191 km (3.04%; the limit is 3%).
- **v2.0:** scored 185.7 km (2.77%).
- **Where the 0.5 km goes:** all of it is the CSMT approach, now measured along the track through Masjid.
- **The older shortfall:** CSMT–Karjat is 94.9 km in v2.0 and 94.5 km in v2.1, against the timetable's 99 km.

This is recorded in D-074 for the owner to decide; the test is not loosened.
