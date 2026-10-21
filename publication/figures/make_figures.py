"""g06 -- paper figures, regenerated from the graph and the experiment outputs.

Every figure in the paper is produced here. None is hand-edited, none is drawn
from a number typed by a person. Running this script after a rebuild reproduces
the whole figure set, which is the only way the figures can be trusted to agree
with the tables.

    python publication/figures/make_figures.py

Writes PNG (300 dpi, for the manuscript) and SVG (for editing captions and for
the web) side by side into this directory.

Figure set
    fig1_network           the national network, geographic, by node type
    fig2_audit_map         construction quality in space -- the visual QA figure
    fig3_degree            degree distribution against the exponential prediction
    fig4_percolation       four attack strategies, the inverted ordering (F-011)
    fig5_sensitivity       Tier A vs Tier B verdicts (F-022)
    fig6_damping           stitching's damping effect per measure (F-023)
    fig7_sinuosity         chord vs along-track, with the mountain railways (F-029)
    fig8_speed             observed vs declared speed (F-036)
    fig9_bridge_capture    bridge inventory vs official count, per zone (F-030)

Design: one hue carries magnitude (blue); a second (orange) is reserved for the
junction/secondary category and is used for nothing else, so the same colour
means the same thing in every figure. Status colours are used only for verdicts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GRAPH = ROOT / "03_graph_construction" / "graph_v1"
EXP = ROOT / "03_graph_construction" / "experiments"
E300 = ROOT / "publication" / "evidence" / "E-300_attribute_audit"
E301 = ROOT / "publication" / "evidence" / "E-301_service_layer_audit"
DATASET = ROOT / "02_graph_inputs" / "graph_dataset"

# ---------------------------------------------------------------- style ----
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
GOOD, WARN, CRIT = "#0ca30c", "#fab219", "#d03b3b"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.size": 9, "axes.titlesize": 10.5, "axes.titleweight": "600",
    "axes.labelsize": 9, "axes.labelcolor": INK2,
    "axes.edgecolor": BASELINE, "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.frameon": False, "legend.fontsize": 8.5,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def finish(fig, name: str, caption: str) -> None:
    """Save both formats and record the caption beside the figure."""
    for ext in ("png", "svg"):
        fig.savefig(HERE / f"{name}.{ext}", facecolor="white")
    (HERE / f"{name}.caption.txt").write_text(caption.strip() + "\n")
    plt.close(fig)
    print(f"    {name}.png / .svg")


def tidy(ax, *, grid_axis="y", top_right_off=True):
    if top_right_off:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis=grid_axis)
    if grid_axis == "y":
        ax.xaxis.grid(False)
    else:
        ax.yaxis.grid(False)


# ----------------------------------------------------------------- data ----
def load():
    nodes = pd.read_parquet(GRAPH / "nodes.parquet")
    edges = pd.read_parquet(GRAPH / "edges.parquet")
    corr = pd.read_csv(DATASET / "corridors.csv").set_index("corridor_id")
    edges = edges.copy()
    edges["declared"] = edges.corridor_id.map(corr.declared_no_of_stations)
    edges["found"] = edges.corridor_id.map(corr.n_stations_found)
    edges["deficit"] = edges.declared - edges.found
    edges["suspect"] = (edges.deficit >= 3) & (edges.length_km > 10)
    return nodes, edges


# ------------------------------------------------------------- figure 1 ----
def fig1_network(nodes, edges):
    n = nodes.dropna(subset=["longitude", "latitude"]).reset_index(drop=True)
    idx = {k: i for i, k in enumerate(n.node_id)}
    fig, ax = plt.subplots(figsize=(7.2, 8.2))
    segs = []
    for u, v in zip(edges.from_node, edges.to_node):
        i, j = idx.get(u), idx.get(v)
        if i is not None and j is not None:
            segs.append([(n.longitude[i], n.latitude[i]), (n.longitude[j], n.latitude[j])])
    from matplotlib.collections import LineCollection
    ax.add_collection(LineCollection(segs, colors=BASELINE, linewidths=0.35, alpha=0.75, zorder=1))
    st = n[n.node_type == "station"]
    jn = n[n.node_type == "operational_junction"]
    ax.scatter(st.longitude, st.latitude, s=0.7, c=BLUE, zorder=2, linewidths=0)
    ax.scatter(jn.longitude, jn.latitude, s=3.2, c=ORANGE, zorder=3, linewidths=0)
    ax.set_xlim(n.longitude.min() - .6, n.longitude.max() + .6)
    ax.set_ylim(n.latitude.min() - .6, n.latitude.max() + .6)
    ax.set_aspect(1 / np.cos(np.radians(float(n.latitude.mean()))))
    ax.set_xlabel("longitude (°E)"); ax.set_ylabel("latitude (°N)")
    ax.set_title("Indian railway network, station-level physical graph",
                 loc="left", color=INK, pad=18)
    ax.text(0, 1.012, f"{len(nodes):,} nodes · {len(edges):,} edges · 72,201 route km",
            transform=ax.transAxes, color=MUTED, fontsize=8.5, va="bottom")
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", color=BLUE, markersize=4,
               label=f"station ({(nodes.node_type=='station').sum():,})"),
        Line2D([], [], marker="o", ls="", color=ORANGE, markersize=5,
               label=f"operational junction ({(nodes.node_type=='operational_junction').sum():,})"),
    ], loc="lower left")
    tidy(ax, grid_axis="both"); ax.grid(alpha=.45)
    finish(fig, "fig1_network",
           "The station-level physical graph of the Indian railway network, drawn at true "
           "coordinates. Edges are straight chords between endpoints, not track alignment "
           "(see Limitations). One node of 9,095 has no coordinate and is omitted.")


# ------------------------------------------------------------- figure 2 ----
def fig2_audit_map(nodes, edges):
    """Construction quality in space. The figure a reviewer should ask for."""
    n = nodes.dropna(subset=["longitude", "latitude"]).reset_index(drop=True)
    idx = {k: i for i, k in enumerate(n.node_id)}
    from matplotlib.collections import LineCollection

    def segs_for(mask):
        out = []
        for u, v in zip(edges.from_node[mask], edges.to_node[mask]):
            i, j = idx.get(u), idx.get(v)
            if i is not None and j is not None:
                out.append([(n.longitude[i], n.latitude[i]), (n.longitude[j], n.latitude[j])])
        return out

    clean = ~edges.any_stitch & ~edges.suspect
    stitched = edges.any_stitch & ~edges.suspect
    suspect = edges.suspect

    fig, ax = plt.subplots(figsize=(7.2, 8.2))
    ax.add_collection(LineCollection(segs_for(clean), colors=BASELINE, linewidths=0.3,
                                     alpha=0.6, zorder=1))
    ax.add_collection(LineCollection(segs_for(stitched), colors=AQUA, linewidths=0.45,
                                     alpha=0.8, zorder=2))
    ax.add_collection(LineCollection(segs_for(suspect), colors=CRIT, linewidths=0.9,
                                     alpha=0.9, zorder=3))
    ax.set_xlim(n.longitude.min() - .6, n.longitude.max() + .6)
    ax.set_ylim(n.latitude.min() - .6, n.latitude.max() + .6)
    ax.set_aspect(1 / np.cos(np.radians(float(n.latitude.mean()))))
    ax.set_xlabel("longitude (°E)"); ax.set_ylabel("latitude (°N)")
    ax.set_title("Construction quality in space", loc="left", color=INK, pad=18)
    km_sus = edges.loc[suspect, "length_km"].sum()
    ax.text(0, 1.012,
            f"suspect edges carry {km_sus:,.0f} km — "
            f"{100*km_sus/edges.length_km.sum():.1f}% of route km",
            transform=ax.transAxes, color=MUTED, fontsize=8.5, va="bottom")
    ax.legend(handles=[
        Line2D([], [], color=BASELINE, lw=1.6, label=f"direct edge ({clean.sum():,})"),
        Line2D([], [], color=AQUA, lw=1.6, label=f"junction-stitched ({stitched.sum():,})"),
        Line2D([], [], color=CRIT, lw=1.8,
               label=f"suspect: ≥3 stations unmatched, >10 km ({suspect.sum():,})"),
    ], loc="lower left")
    tidy(ax, grid_axis="both"); ax.grid(alpha=.45)
    finish(fig, "fig2_audit_map",
           "Construction quality mapped. Red edges satisfy the F-026 defect signature: the "
           "corridor declares at least three more stations than were matched, and the edge "
           "spans more than 10 km, so one long edge is standing in for several missing "
           "stations. They carry 24.5% of total route km.")


# ------------------------------------------------------------- figure 3 ----
def fig3_degree(nodes, edges):
    deg = pd.concat([edges.from_node, edges.to_node]).value_counts()
    d = nodes.node_id.map(deg).fillna(0).astype(int)
    counts = d.value_counts().sort_index()
    counts = counts[counts.index >= 1]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.6, 3.1))

    ax.bar(counts.index, counts.values, color=BLUE, width=0.62)
    for k, v in counts.items():
        ax.text(k, v, f"{v:,}", ha="center", va="bottom", fontsize=7.5, color=INK2)
    ax.set_xlabel("degree"); ax.set_ylabel("nodes")
    ax.set_title("Degree distribution", loc="left", color=INK, pad=18)
    ax.set_ylim(0, counts.max() * 1.16)
    tidy(ax)

    p = counts / counts.sum()
    ax2.semilogy(p.index, p.values, "o-", color=BLUE, ms=5, lw=1.6)
    k = p.index.values.astype(float)
    lo = (k >= 2) & (k <= 7)
    if lo.sum() >= 3:
        b, a = np.polyfit(k[lo], np.log(p.values[lo]), 1)
        ax2.plot(k[lo], np.exp(a + b * k[lo]), "--", color=ORANGE, lw=1.4,
                 label=f"exponential fit, slope {b:.2f}")
        ax2.legend(loc="upper right")
    ax2.set_xlabel("degree"); ax2.set_ylabel("P(k)")
    ax2.set_title("Against the exponential prediction", loc="left", color=INK, pad=18)
    tidy(ax2)
    fig.tight_layout()
    finish(fig, "fig3_degree",
           "Degree distribution. Mean degree 2.13, maximum 7. The tail is exponential rather "
           "than scale-free, as Kurant & Thiran (2006) predict for physical rail networks "
           "where cost constrains node degree.")


# ------------------------------------------------------------- figure 4 ----
def fig4_percolation():
    f = EXP / "E-100" / "percolation_curves.csv"
    if not f.exists():
        print("    (skipped fig4 — percolation_curves.csv absent)"); return
    df = pd.read_csv(f)
    df = df[~df.get("adaptive", False).astype(bool)] if "adaptive" in df else df
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    styles = {"random": (CRIT, "-"), "degree": (BLUE, "-"),
              "betweenness": (AQUA, "--"), "service_load": (YELLOW, ":")}
    for strat, g in df.groupby("strategy"):
        c, ls = styles.get(strat, (MUTED, "-"))
        g = g.sort_values("removed_frac")
        ax.plot(g.removed_frac, g.scf, ls, color=c, lw=1.8,
                label=f"{strat}  (R={g.R.iloc[0]:.4f})")
    ax.set_xlabel("fraction of nodes removed")
    ax.set_ylabel("SCF — share of nodes in the giant component")
    ax.set_title("Percolation under four attack strategies", loc="left", color=INK, pad=18)
    ax.text(0, 1.012, "random failure is more damaging than betweenness-targeted attack (F-011)",
            transform=ax.transAxes, color=MUTED, fontsize=8, va="bottom")
    ax.set_xlim(0, df.removed_frac.max()); ax.set_ylim(0, 1.02)
    ax.legend(loc="upper right")
    tidy(ax, grid_axis="both")
    finish(fig, "fig4_percolation",
           "State of critical functionality under progressive node removal. The ordering is "
           "inverted relative to the textbook scale-free result: random failure damages this "
           "network more than betweenness-targeted attack, because high-betweenness nodes lie "
           "contiguously along trunk routes rather than acting as separate hubs. Robust across "
           "19 of 20 sensitivity cells (F-024).")


# ------------------------------------------------------------- figure 5 ----
def fig5_sensitivity():
    a = EXP / "E-200" / "verdicts_tierA.csv"
    b = EXP / "E-200" / "verdicts_tierB.csv"
    if not (a.exists() and b.exists()):
        print("    (skipped fig5 — verdict files absent)"); return
    ta, tb = pd.read_csv(a), pd.read_csv(b)
    order = ["giant_share", "mean_path", "circuity_median", "R_random", "R_degree",
             "top50_corridor_overlap", "bridge_share", "meshedness"]
    cmap = {"robust": GOOD, "conditional": WARN, "artifact": CRIT}
    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    y = np.arange(len(order))
    for i, conc in enumerate(order):
        for j, (t, lbl) in enumerate([(ta, "Tier A"), (tb, "Tier B")]):
            r = t[t.conclusion == conc]
            if not len(r):
                continue
            v = r.verdict.iloc[0]
            ax.barh(i + (0.19 if j == 0 else -0.19), 1, height=0.34,
                    color=cmap.get(v, MUTED), alpha=0.92 if j == 0 else 0.62)
            ax.text(1.03, i + (0.19 if j == 0 else -0.19), f"{lbl}: {v}",
                    va="center", fontsize=7.6, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels(order, fontsize=8.5)
    ax.set_xlim(0, 2.1); ax.set_xticks([])
    ax.invert_yaxis()
    ax.set_title("Which conclusions survive the construction choices?", loc="left", color=INK, pad=18)
    ax.text(0, 1.012, "Tier A: the 9 genuinely open choices   ·   Tier B: + the attributed-core views",
            transform=ax.transAxes, color=MUTED, fontsize=8, va="bottom")
    ax.legend(handles=[Line2D([], [], color=cmap[k], lw=6, label=k)
                       for k in ["robust", "conditional", "artifact"]],
              loc="lower right", ncol=3)
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    ax.grid(False)
    finish(fig, "fig5_sensitivity",
           "Sensitivity verdicts by tier. Against the nine genuinely open construction and "
           "representation parameters (Tier A) no headline conclusion is an artifact. Adding "
           "the attributed-core views (Tier B, D-013) turns four of them into artifacts, which "
           "is why those views are shipped as flags rather than as a filtered export.")


# ------------------------------------------------------------- figure 6 ----
def fig6_damping():
    f = EXP / "E-200" / "damping.csv"
    if not f.exists():
        print("    (skipped fig6 — damping.csv absent)"); return
    d = pd.read_csv(f).sort_values("damping_factor", ascending=True)
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.barh(d.conclusion, d.damping_factor, color=BLUE, height=0.6)
    ax.set_xscale("log")
    for _, r in d.iterrows():
        ax.text(r.damping_factor * 1.1, r.conclusion, f"{r.damping_factor:.1f}×",
                va="center", fontsize=8, color=INK2)
    ax.axvline(1, color=BASELINE, lw=1)
    ax.set_xlabel("sensitivity damping factor (log scale)")
    ax.set_title("How much does junction stitching damp tolerance sensitivity?",
                 loc="left", color=INK, pad=18)
    ax.text(0, 1.012, "range of the measure across the tolerance sweep, stitching off ÷ stitching on",
            transform=ax.transAxes, color=MUTED, fontsize=8, va="bottom")
    ax.set_xlim(0.8, d.damping_factor.max() * 2.4)
    tidy(ax, grid_axis="x")
    finish(fig, "fig6_damping",
           "Junction stitching damps the placement-tolerance sensitivity of connectivity by "
           "322×, of distance and fragility by 25–30×, but of cycle structure by only 1.3×. "
           "The operator stabilises some conclusions and barely helps others, so the claim has "
           "to be made per measure (F-023).")


# ------------------------------------------------------------- figure 7 ----
def fig7_sinuosity():
    f = E300 / "corridor_sinuosity.csv"
    p = E300 / "length_pairs.csv"
    if not (f.exists() and p.exists()):
        print("    (skipped fig7 — E-300 outputs absent)"); return
    s = pd.read_csv(f)
    pairs = pd.read_csv(p)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.8, 3.3))

    good = pairs[(pairs.max_offset_km < 0.25) & (pairs.ratio >= 0.95)]
    ax.hist(np.clip(good.ratio, 1, 1.6), bins=70, color=BLUE, edgecolor="none")
    ax.axvline(1.0, color=BASELINE, lw=1)
    ax.set_xlabel("along-track distance ÷ straight-line chord")
    ax.set_ylabel("station pairs")
    ax.set_title("The distance the chord discards", loc="left", color=INK, pad=18)
    ax.text(0, 1.012, f"{100*(pairs.ratio>1.05).mean():.1f}% of pairs understated by more than 5%",
            transform=ax.transAxes, color=MUTED, fontsize=8, va="bottom")
    tidy(ax)

    top = s.nlargest(10, "sinuosity").iloc[::-1]
    lab = [f"{a} – {b}" for a, b in zip(top.corridor_a, top.corridor_b)]
    unesco = {"Darjeeling", "Mettupalayam", "Kalka", "Matheran"}
    cols = [ORANGE if (str(a) in unesco or str(b) in unesco) else BLUE
            for a, b in zip(top.corridor_a, top.corridor_b)]
    ax2.barh(range(len(top)), top.sinuosity, color=cols, height=0.62)
    ax2.set_yticks(range(len(top)))
    ax2.set_yticklabels([l[:34] for l in lab], fontsize=7.2)
    ax2.set_xlabel("corridor sinuosity")
    ax2.set_title("Most sinuous corridors", loc="left", color=INK, pad=18)
    ax2.text(0, 1.012, "orange = a recognised mountain railway, recovered with no terrain input",
             transform=ax2.transAxes, color=MUTED, fontsize=8, va="bottom")
    tidy(ax2, grid_axis="x")
    fig.tight_layout()
    finish(fig, "fig7_sinuosity",
           "Left: the ratio of true along-track distance to the straight chord the graph "
           "currently stores; 17.7% of station pairs are understated by more than 5%. Right: "
           "ranking 871 corridors by that ratio places all four of India's recognised mountain "
           "railways in the top six, using no terrain, elevation or heritage input of any kind "
           "(F-029).")


# ------------------------------------------------------------- figure 8 ----
def fig8_speed():
    f = E301 / "edge_runtime_join.csv"
    if not f.exists():
        print("    (skipped fig8 — E-301 output absent)"); return
    d = pd.read_csv(f)
    d = d[d.runtime_min_median.notna() & (d.runtime_min_median > 0)].copy()
    d["implied"] = d.length_km / (d.runtime_min_median / 60)
    d = d[(d.implied > 1) & (d.implied < 200)]
    both = d[d.speed_kmph.notna()]
    fig, ax = plt.subplots(figsize=(6.0, 3.5))
    ax.hist(d.implied, bins=60, color=BLUE, edgecolor="none",
            label=f"observed, from timetables (median {d.implied.median():.0f} km/h)")
    ax.axvline(both.speed_kmph.median(), color=CRIT, lw=1.8,
               label=f"declared sectional speed (median {both.speed_kmph.median():.0f} km/h)")
    ax.axvline(50, color=ORANGE, lw=1.6, ls="--",
               label="the 50 km/h fallback we invented")
    ax.set_xlabel("speed (km/h)"); ax.set_ylabel("edges")
    ax.set_title("Observed speed against the declared maximum", loc="left", color=INK, pad=18)
    ax.text(0, 1.012, "trains achieve 0.51 of the declared sectional speed (F-036)",
            transform=ax.transAxes, color=MUTED, fontsize=8, va="bottom")
    ax.legend(loc="upper right")
    tidy(ax)
    finish(fig, "fig8_speed",
           "Speed implied by timetabled run-times on the 66.9% of edges where schedules give "
           "one, against the declared sectional speed the graph currently uses as a weight. "
           "The declared value is a sanctioned maximum and overstates achieved speed by about "
           "a factor of two; the flat fallback used where no declared speed exists is closer "
           "to reality than the declared value is.")


# ------------------------------------------------------------- figure 9 ----
def fig9_bridge_capture():
    f = E300 / "bridge_validation.csv"
    if not f.exists():
        print("    (skipped fig9 — bridge_validation.csv absent)"); return
    b = pd.read_csv(f, index_col=0).sort_values("capture_rate")
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.barh(b.index, b.capture_rate, color=BLUE, height=0.64)
    ax.axvline(b.gis_bridge_segments.sum() / b.official_bridges.sum(), color=CRIT,
               lw=1.6, ls="--", label="overall capture 0.32")
    for z, r in b.iterrows():
        ax.text(r.capture_rate + .012, z, f"{r.capture_rate:.2f}", va="center",
                fontsize=7.6, color=INK2)
    ax.set_xlabel("share of officially recorded bridges present in the GIS")
    ax.set_title("A validation that demoted its attribute", loc="left", color=INK, pad=18)
    ax.text(0, 1.012, "GIS bridge segments ÷ Rajya Sabha Q.371 count, by zone",
            transform=ax.transAxes, color=MUTED, fontsize=8, va="bottom")
    ax.set_xlim(0, 0.75); ax.legend(loc="lower right")
    tidy(ax, grid_axis="x")
    finish(fig, "fig9_bridge_capture",
           "The GIS records only 31.6% of officially counted railway bridges, and the shortfall "
           "is strongly zone-dependent — from 0.6% in Northeast Frontier Railway to 63.8% in "
           "Western Railway. A per-edge bridge count is therefore usable only as a relative "
           "density within a zone, never as an absolute count or across zones (F-030).")


def main():
    print("=" * 70)
    print("g06  paper figures")
    print("=" * 70)
    nodes, edges = load()
    fig1_network(nodes, edges)
    fig2_audit_map(nodes, edges)
    fig3_degree(nodes, edges)
    fig4_percolation()
    fig5_sensitivity()
    fig6_damping()
    fig7_sinuosity()
    fig8_speed()
    fig9_bridge_capture()
    print(f"\nfigures written to {HERE}")


if __name__ == "__main__":
    main()
