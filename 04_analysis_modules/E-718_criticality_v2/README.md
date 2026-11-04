# E-718 — severance criticality on v2.x-open (remediation Step 9)

E-709's analysis (stable class, D-055), rerun on `graph_v2_0_open` and `graph_v2_1_open` with the 2024 trains-per-day layer.

```bash
python sever_v2.py v2_1_open structure   # ~45 s
python sever_v2.py v2_1_open exposure    # ~10 s
python sever_v2.py v2_1_open load        # ~4 s
python sever_v2.py v2_1_open corridors   # ~1 s
```

Changes from E-709, each forced by v2:
- **No duplicate-pair contraction.** v2 has no known same-place duplicates (V2-25 closed).
- **"Stations severed" counts stations only.** The v2 physical graph also holds junction nodes.
- **Two views (D-066).** `physical` carries traffic and is used for exposure and load; `places` is structure only.
- **Exposure via the bridge tree.** A simple path crosses a bridge exactly when the bridge separates its ends, so exposure is computed on the bridge tree (same answer as E-709's shortest-path test, 17× faster).

## Headline figures

| | v1.4 (E-709) | v2.0-open | **v2.1-open** |
|---|---|---|---|
| Bridges (physical giant) | 1,231 (merged view) | 1,823 | **1,663** |
| Share of route km on bridges (physical / places) | — | 17.2% / 17.5% | **16.2% / 16.5%** |
| Intra-station artifact bridges (< 1 km, sever 1 station) | 82 | 48 | **13** |
| Daily train movements crossing a bridge | 5.6% | 9.2% | **7.0%** |
| Severance corridors / with traffic | 283 / 83 | 222 / 110 | **227 / 111** |
| Corridors severing > 200 stations | 2 | 0 | **0** |
| Busiest 100 sections: detour > 3× / median detour | 90 / ×53.3 | 76 / 29 km | **86 / 202 km (×98.8)** |
| Busiest 100 sections that are bridges | 4 | 5 | **2** |

## What changed, and why

- **Exposure falls from 9.2% to 7.0% (v2.0 → v2.1).** v2.0's spurious terminal and stub-station bridges (V2-26, V2-27) carried 918 trains a day of false "no alternative route" traffic.
- **Detours of the busiest sections rise from 29 km to 202 km.** v2.0 kept duplicate parallel routes between consecutive stations (Step 5), which offered short fake detours. v2.1's detours are real alternative lines, which brings it back in line with v1.4.
- **No corridor severs more than 200 stations.** v1.4's worst corridor (Barsoi–Makuria–Radhikapur, isolating the Northeast) is no longer a single point of failure, because the Araria–Galgalia line (commissioned 2024–25, E-725) gives a second route. Removing that line from v2.1 recreates 18 bridges near Barsoi and Mukuria that each sever more than 500 stations. The v1.4 finding was right for its network; the network has changed.
- **Worst corridor in v2.1:** the Lumding–Badarpur hill line towards Silchar, Manipur and Mizoram (65 sections, 444 km, up to 109 stations severed).
