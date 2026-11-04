# E-725 — manual case pass (remediation Step 7)

One time-boxed pass over the individual cases the Phase 2 audit listed (D-071). Evidence held in the repo: the 2017
timetable (consecutive stops and distances), OSM tags and geometry, station snaps. One web check was made, for
Thakurganj–Araria. A case enters v2.1 only on a **fix** verdict. **None did.**

| Case | Evidence | Verdict |
|---|---|---|
| Sections shorter than the straight line between their end coordinates by more than 200 m (DSS\|STJT, GRX\|MBDD, ADH\|JOS, KRTN, KBJ\|TRKR, LMN\|RCP, AMQ, CBF, DHN, GKPI\|KRA) | In every case with a large shortfall, one end station is two OSM points 200–1,300 m apart that D-063 merged into one node (STJT 1,298 m, GRX 1,295, KRTN 954, TRKR 831, JOS 563, LMN 219). The track attaches at one point; the node's coordinate is the other. CBF and DHN: station point vs track point (≈ 235 m). GKPI\|KRA: 203 m, within geometry simplification | **property** (V2-32): lengths are real track; the chord check misleads where a node has several OSM points |
| KRTN node name "Kirti Nagar (Green Line)" | The name comes from one of the two merged OSM points, a Delhi Metro station | **property** (V2-32), naming only |
| ANVT throat (1.84 km, 68 trains) | 2017 trains from ANVT to GZB (41), CNB (25), ALJN (11), MB (8), SBB, KRJ; the throat is the terminal's access | **confirmed, no change** |
| TKMG\|UDPR (19.5 km, throat tag) | 2017 timetable TKMG–UDPR 20 km, 2 trains; the throat tag comes from the 30 m construction gap fixed in V2-01 | **confirmed, no change** (tag: V2-30) |
| Thakurganj–Araria (PWKHI edges 83.4 + 22.0 km, 0 trains) | OSM: 92 ways `railway=rail`, `usage=main`, "Thakurganj - Araria New Line". Sections commissioned Apr 2024 – Jul 2025, CRS cleared Jul 2025 ([Morung Express, 12 Jul 2025](https://morungexpress.com/araria-galgalia-rail-line-clears-final-safety-check-set-for-launch)); inauguration announced for 15 Sep 2025 ([Patna Press, 10 Sep 2025](https://patnapress.com/araria-galgalia-rail-line-pm-modi-inauguration/)) | **confirmed, no change**: a post-2017 line, correct for the Oct 2026 snapshot; no 2017 service is expected. Severance claims about the Siliguri corridor must use this line |
| PTP–KKD gap; KKD isolated (Mhow–Kalakund heritage line) | 2017 timetable: 8 trains PTP–KKD (10 km) and KKD–CRL (10 km); OSM has no track there | **property** (V2-33): would need a chained timetable join, a new join type, out of v2.1 scope |
| INDR, MHBD code conflicts | Neither code appears in the 2017 timetable, so no neighbour can arbitrate | **property** (already listed): harmless |
| LNLA, MFR isolated | No 2017 trains | **property** (already listed) |
