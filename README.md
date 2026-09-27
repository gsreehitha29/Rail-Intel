# Rail-Intell — Indian Railway Network Analysis

A data-engineering and graph-analysis project for the Indian Railway Network.

## Project Overview

This repository contains:
- Exploratory data analysis of the Indian Railway GIS network
- Cleaned and validated station, train, and schedule datasets
- An initial junction-level graph representation derived from 119,446 raw GIS segments
- Supporting reference data (historical statistics, electrification data)

---

## Current Graph-Ready Data

> **For the graph-design teammate:** Start here.

The EDA and preprocessing phases are complete. The following files are the handoff point for graph construction.

### Physical Graph (Junction Level)

| File | Rows | Description |
|------|------|-------------|
| `rail_edges_initial.csv` | 2,257 | Conceptual directed edges — one per unique junction pair |
| `junction_nodes_initial.csv` | 2,024 | Junction nodes with degree statistics and component membership |
| `railway_components_initial.csv` | 113 | Connected-component summary (main component: 1,758 nodes / 2,101 edges) |

### Station Master

| File | Rows | Description |
|------|------|-------------|
| `processed_data/cleaned_stations.csv` | 8,990 | Cleaned station master — 8,697 with coordinates, 0 duplicate codes |

### Service Data (Validated, Not Yet Used as Graph Edges)

| File | Rows | Description |
|------|------|-------------|
| `processed_data/cleaned_schedules.csv` | 416,970 | Stop records for 5,208 trains — validated against station master |
| `processed_data/cleaned_trains.csv` | 5,208 | Train metadata with quality flags |

### Documentation

| File | Description |
|------|-------------|
| `docs/GRAPH_HANDOFF.md` | **Start here** — complete handoff briefing for the graph-design phase |
| `docs/DATA_DICTIONARY.md` | Column-level schema for all graph-relevant datasets |

---

## Notebooks

| Notebook | Purpose | Status |
|----------|---------|--------|
| `Railway_networks_EDA.ipynb` | EDA of `Railway_Network_.csv`; produces edge/node/component CSV files | Complete |
| `01_Final_Data_Preprocessing_and_Validation.ipynb` | Cleans stations, trains, schedules; partial spatial analysis | Mostly complete (haversine validation section not executed — see notebook Cell 210) |
| `Untitled.ipynb` | Historical statistics EDA (gauge history, electrification) | Exploratory — no output files |

---

## Repository Structure

```
Rail-Intell/
├── docs/
│   ├── GRAPH_HANDOFF.md          ← Graph teammate: read this first
│   └── DATA_DICTIONARY.md        ← Column schemas for all key datasets
│
├── processed_data/
│   ├── cleaned_stations.csv      ← Station master (8,990 stations)
│   ├── cleaned_trains.csv        ← Train metadata (5,208 trains)
│   └── cleaned_schedules.csv     ← Schedule stops (416,970 records)
│
├── railways-master/              ← Raw source data (JSON)
│   ├── stations.json
│   ├── trains.json
│   ├── schedules.json
│   └── README.md
│
├── rail_edges_initial.csv        ← Graph edges (2,257)
├── junction_nodes_initial.csv    ← Graph nodes (2,024)
├── railway_components_initial.csv← Component summary (113)
│
├── Railway_Network_.csv          ← Raw GIS network (119,446 segments)
├── Railway_Network_.geojson      ← Raw GIS geometry (88 MB)
│
├── Railway_networks_EDA.ipynb
├── 01_Final_Data_Preprocessing_and_Validation.ipynb
└── Untitled.ipynb
```

---

## Large Files

The following files are too large for standard Git commits and require Git LFS or external storage:

| File | Size | Note |
|------|------|------|
| `Railway_Network_.geojson` | ~88 MB | Required for spatial analysis; use Git LFS |
| `railways-master/schedules.json` | ~78 MB | Raw source; use Git LFS |
| `processed_data/cleaned_schedules.csv` | ~62 MB | Processed output; use Git LFS |
| `railways-master/trains.json` | ~14 MB | Raw source; consider Git LFS |
| `processed_data/cleaned_trains.csv` | ~13 MB | Processed output; consider Git LFS |
| `Railway_Network_.csv` | ~13 MB | Raw source; consider Git LFS |
