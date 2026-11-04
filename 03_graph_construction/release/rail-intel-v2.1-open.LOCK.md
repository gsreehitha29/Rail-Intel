# Lock record — Rail-Intel v2.1-open

Locked: 2026-11-03, on the owner's decision (D-074). Publication and a DOI are deferred, as for v2.0-open.

- Zip: `rail-intel-v2.1-open.zip`, 1394474 bytes, sha256 `adcbcd1f64cb73106cd8d5ff5b090e9217ca3c3af2850f49d8736da844e9f8b4`
- Built by `03_graph_construction/experiments/E-726_v2_1_build` (`run_c2.py` stages, `validate_c3.py`, `release.py --version=v2.1-open`). Two runs gave identical bytes.
- Data files are identical to release candidate rc1; only the version text, the citation file, the datasheet and the manifest differ.
- What changed from v2.0-open (D-071):
  - station multi-track snap (D-073 rev. 1);
  - 19 rename aliases (D-072);
  - edge ids `v2.1:`.
- Checks passed before the lock:
  - gates C2a–d and C3a–d;
  - 102 tests, including the v2.1 golden figures and named fixes;
  - spot-check, with train 12123 recorded as V2-34 (3.04% short; its own 3.5% bound).
- v2.0-open is unchanged. Its known issues found after its lock are in `rail-intel-v2.0-open.ERRATA.md`.

## Hashes of the files inside the package
```
fe25052ab57dff588bdc87f16aea208deb8e8a1c4313fe023f8f8de2d4fa9172  ATTRIBUTION.md
6af6e4154e1853fc8c3a2cf3d2fd5677dd24e34802f569a85913dc9199943b44  CITATION.cff
7cb01bb8dd06169c7eae7c864ce4a8e66de5435e33539702e0ac0c305ea08509  DATASHEET.md
a9968b039602575548f39db818c69a1d6dd0b197ffad1c0ea76e355833b32fd2  LICENSE
9b345d48a9d087864c1cb0ffaaa54773414c6095b5ae493872bdb39caae8650a  README.md
ee0cccf96d6c0995a8cd1dbf923e4c2ea8e172829dd976a5f0081b76878fd964  graph/edges.csv
75cd6c812c1907fc84ff5d627ee3bfcd0ff856d864dfeabe5e507ec8e0e0dbe7  graph/nodes.csv
fda19f962708b95b9b53c22bf7ae35c1b31c1368368328dfb68a35750bed09e6  graph/station_code_crosswalk.csv
f777406433a68bba683e991032645a4f671daca10fef1fd22a8b49a0cd06ea9f  places/edges.csv
2f3fce0e1328ec40e9685d797d60008607de4d0c599dd91091a0a9786a0592b4  places/nodes.csv
b93fb445e050dcdfd224f78fc0a7c4365f01525c987228b1aa66da041e338dfd  provenance/code_conflicts.csv
f2b831cdf5ff81e008c996a1730957ca3ea8c3725e69535440740dc3709f120e  provenance/joins.csv
f9080e33d0c14af00d073cf72aef7a97b750bdf4edf62d29a9812ca8ee11f957  provenance/throat_links.csv
7ac6745a78f61e4b12d0ff2af8ce389552b359aef110d9ff4cdb6fdacad0fe8c  provenance/wikidata_placements.csv
338e29b415f10ac9ab7c5c28102491b5e4b1011214089738eac58fee2e176c68  service_2017/station_pairs.csv
e92643d487bb8f5bc0ba7dda09fb47d0d814a68efbf638b702070f0ace024b6a  manifest.json
```

Anything that changes a data file after this point is a new version, not an edit.
