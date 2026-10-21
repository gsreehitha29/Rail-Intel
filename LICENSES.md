# Licensing

Three different things in this repository carry three different licences, because
their constraints differ. This split is deliberate: it lets the **method and the code
be shared and cited even if the dataset cannot be** (D-036).

| What | Licence | File |
|---|---|---|
| Code — `railgraph/`, `experiments/`, `04_analysis_modules/*/*.py`, `tests/`, `Makefile` | **MIT** | `LICENSE` |
| Prose — `docs/`, `publication/*.md`, module `README.md` files | **CC BY 4.0** | this file |
| The graph itself — `03_graph_construction/graph_v1*/`, `service_layer_v1*/` | **not yet licensable** | see below |

## Why the dataset has no licence

The graph is a derivative work of `01_data_engineering/Railway_Network_.csv`, which
schema evidence identifies as an export of Esri India's Living Atlas "Railway Tracks"
layer, whose terms do not permit export for offline use
(`publication/SOURCE_LICENCE_INVENTORY.md` §8).

Until that is resolved, the honest position — publishable as it stands — is:

> The construction pipeline, the analysis code and the documentation are released
> under an open licence. Redistribution terms for the underlying GIS source have not
> been established, so the derived graph is described and fully reproducible from the
> pipeline, with deposit of the artifact itself pending that determination.

The route to a depositable dataset is rebuilding the topology from the OpenStreetMap
extracts already in `external_data/` (ODbL, attribution and share-alike).

## Switching the code licence

If the team prefers Apache-2.0 for its patent grant, replace `LICENSE` with the Apache
text and update the table above. Nothing else depends on the choice.

## Third-party inputs

Every input's origin and licence status is inventoried in
`publication/SOURCE_LICENCE_INVENTORY.md`. Upstream licence texts that were shipped
with their data are kept at `external_data/*/upstream_LICENSE`.
