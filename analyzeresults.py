#!/usr/bin/env python3
"""
analyze_results.py
==================
Reads OpenSimRoot simulation outputs from results/MaizeSCD<rep>_<pheno>_<env>/
and compares them against the published Schäfer et al. (2022) supplementary
data (supplementary/Table 1.csv).

Usage
-----
    python analyze_results.py

Outputs
-------
    plots/shoot_dw.png          — bar chart, your sims vs published
    plots/root_carbon.png       — bar chart, root carbon cost comparison
    plots/deep_carbon.png       — bar chart, deep soil carbon comparison
    plots/pvalue_heatmap.png    — heatmap of p-values per env x phenotype
    analysis_results.csv        — full comparison table with t-test results
"""

import os
import re
import glob
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT     = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR   = os.path.join(REPO_ROOT, "results")
PUBLISHED_CSV = os.path.expanduser("~/Documents/01 - Roots/OpenSimRoot/schafer2022/supplementary/table1.csv")
PLOTS_DIR     = os.path.join(REPO_ROOT, "plots")
OUTPUT_CSV    = os.path.join(REPO_ROOT, "analysis_results.csv")

FINAL_DAY     = 42   # OpenSimRoot simulates 42 days
DEEP_SOIL_CM  = 50   # depth threshold for deep carbon (cm)

os.makedirs(PLOTS_DIR, exist_ok=True)


# ── Step 1: Parse simulation output files ────────────────────────────────────

def parse_tabled_output(filepath):
    """
    Read tabled_output.tab (long format: name, time, value columns).
    Returns a wide DataFrame indexed by time with one column per metric.
    """
    df = pd.read_csv(filepath, sep="\t", skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df["name"] = df["name"].str.strip().str.strip('"')

    core_metrics = [
        "shootDryWeight",
        "rootDryWeight",
        "rootCarbonCostOfExudates",
        "rootRespiration",
    ]

    deep_metrics = [
        c for c in df["name"].unique()
        if ("RootDryWeightProfile" in c or "RootExudationProfile" in c)
        and any(("_%d-" % d) in c for d in range(DEEP_SOIL_CM, 200, 10))
    ]

    keep = core_metrics + deep_metrics
    wide = (df[df["name"].isin(keep)][["name", "time", "value"]]
              .pivot_table(index="time", columns="name", values="value")
              .reset_index())
    wide.columns.name = None

    wide["total_root_carbon_g"] = (
        wide.get("rootDryWeight",            pd.Series(0, index=wide.index)) +
        wide.get("rootCarbonCostOfExudates", pd.Series(0, index=wide.index)) +
        wide.get("rootRespiration",          pd.Series(0, index=wide.index))
    )

    deep_cols = [c for c in wide.columns
                 if ("RootDryWeightProfile" in c or "RootExudationProfile" in c)
                 and any(("_%d-" % d) in c for d in range(DEEP_SOIL_CM, 200, 10))]
    wide["deep_carbon_g"] = wide[deep_cols].sum(axis=1) if deep_cols else 0.0

    return wide


def value_at_day(df, value_col, target_day):
    """Return the value and actual day closest to target_day."""
    if df is None or df.empty or value_col not in df.columns:
        return np.nan, np.nan
    idx = (df["time"] - target_day).abs().idxmin()
    return float(df.loc[idx, value_col]), float(df.loc[idx, "time"])


print("=" * 60)
print("Step 1: Scanning results directory")
print("=" * 60)

sim_folders = sorted([
    d for d in glob.glob(os.path.join(RESULTS_DIR, "MaizeSCD*"))
    if os.path.isdir(d) and os.path.exists(os.path.join(d, "tabled_output.tab"))
])

print("Found %d simulation folders." % len(sim_folders))
if not sim_folders:
    raise FileNotFoundError(
        "No MaizeSCD* folders found in %s.\n"
        "Make sure results are present in the repo." % RESULTS_DIR
    )

records = []
for folder in sim_folders:
    raw_name   = os.path.basename(folder)
    folder_key = re.sub(r"^MaizeSCD\d+_", "", raw_name)

    try:
        df   = parse_tabled_output(os.path.join(folder, "tabled_output.tab"))
        sdw,  sdw_day = value_at_day(df, "shootDryWeight",     FINAL_DAY)
        rcc,  _       = value_at_day(df, "total_root_carbon_g", FINAL_DAY)
        deep, _       = value_at_day(df, "deep_carbon_g",       FINAL_DAY)
    except Exception as e:
        print("  WARNING: could not parse %s: %s" % (raw_name, e))
        sdw = rcc = deep = sdw_day = np.nan

    records.append({
        "folder":            folder_key,
        "last_day":          round(sdw_day, 1) if not np.isnan(sdw_day) else np.nan,
        "sim_shoot_dw_g":    round(sdw,  4)    if not np.isnan(sdw)     else np.nan,
        "sim_root_carbon_g": round(rcc,  4)    if not np.isnan(rcc)     else np.nan,
        "sim_deep_carbon_g": round(deep, 4)    if not np.isnan(deep)    else np.nan,
    })

sim_df = pd.DataFrame(records)
print("Parsed %d simulations." % len(sim_df))


# ── Step 2: Load published results ───────────────────────────────────────────

print("\n" + "=" * 60)
print("Step 2: Loading published CSV")
print("=" * 60)

if not os.path.isfile(PUBLISHED_CSV):
    raise FileNotFoundError(
        "Published CSV not found at %s.\n"
        "Make sure supplementary/Table 1.csv is in the repo." % PUBLISHED_CSV
    )

pub = pd.read_csv(PUBLISHED_CSV, index_col=0)
pub.index   = pub.index.astype(str).str.strip()
pub.columns = pub.columns.str.strip()
pub = pub.reset_index().rename(columns={"index": "folder"})
pub["folder"] = pub["folder"].str.strip()

dw_deep = [c for c in pub.columns
            if "RootDryWeightProfile" in c
            and int(c.split("_")[1].split("-")[0]) >= DEEP_SOIL_CM]
ex_deep = [c for c in pub.columns
            if "RootExudationProfile" in c
            and int(c.split("_")[1].split("-")[0]) >= DEEP_SOIL_CM]

pub["pub_deep_carbon_g"] = (
    pub[dw_deep + ex_deep].sum(axis=1) if (dw_deep or ex_deep) else 0.0
)
pub["pub_root_carbon_g"] = (
    pub["rootDryWeight (g)"] +
    pub["rootCarbonCostOfExudates (g)"] +
    pub["rootRespiration (g)"]
)

pub_slim = (pub[["folder", "Environment (-)", "Phenotype",
                 "shootDryWeight (g)", "pub_root_carbon_g", "pub_deep_carbon_g"]]
              .rename(columns={"shootDryWeight (g)": "pub_shoot_dw_g"})
              .copy())
pub_slim["Environment (-)"] = pub_slim["Environment (-)"].str.strip()
pub_slim["Phenotype"]       = pub_slim["Phenotype"].str.strip()

print("Published CSV: %d rows, %d environments, %d phenotypes." % (
    len(pub_slim),
    pub_slim["Environment (-)"].nunique(),
    pub_slim["Phenotype"].nunique()
))


# ── Step 3: Merge ─────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("Step 3: Merging")
print("=" * 60)

merged = sim_df.merge(pub_slim, on="folder", how="left")
matched = merged["pub_shoot_dw_g"].notna().sum()
print("Matched %d / %d rows to published data." % (matched, len(merged)))
if matched < len(merged):
    unmatched = merged[merged["pub_shoot_dw_g"].isna()]["folder"].tolist()
    print("  Unmatched (first 10): %s" % unmatched[:10])

merged["diff_shoot_dw_g"]    = merged["sim_shoot_dw_g"]    - merged["pub_shoot_dw_g"]
merged["diff_root_carbon_g"] = merged["sim_root_carbon_g"] - merged["pub_root_carbon_g"]
merged["diff_deep_carbon_g"] = merged["sim_deep_carbon_g"] - merged["pub_deep_carbon_g"]


# ── Step 4: Statistical tests ─────────────────────────────────────────────────

print("\n" + "=" * 60)
print("Step 4: Paired t-tests per environment x phenotype")
print("=" * 60)
print("\n%-22s %-28s %-18s %10s %7s %8s  %s" % (
    "Environment", "Phenotype", "Metric", "mean diff", "t", "p", "sig"))
print("-" * 100)

stat_rows = []
for (env, pheno), grp in merged.groupby(["Environment (-)", "Phenotype"]):
    for diff_col, label in [
        ("diff_shoot_dw_g",    "Shoot DW (g)"),
        ("diff_root_carbon_g", "Root carbon (g)"),
        ("diff_deep_carbon_g", "Deep carbon (g)"),
    ]:
        vals = grp[diff_col].dropna()
        if len(vals) < 3:
            continue
        t, p = stats.ttest_1samp(vals, popmean=0)
        sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
        print("%-22s %-28s %-18s %+10.3f %7.3f %8.4f  %s" % (
            env, pheno, label, vals.mean(), t, p, sig))
        stat_rows.append(dict(
            environment=env, phenotype=pheno, metric=label,
            n=len(vals), mean_diff=round(vals.mean(), 4),
            t=round(t, 3), p=round(p, 4),
            significant=p < 0.05, sig_label=sig
        ))

stats_df = pd.DataFrame(stat_rows)
n_sig = stats_df["significant"].sum()
print("\n%d / %d comparisons significant at p < 0.05" % (n_sig, len(stats_df)))


# ── Step 5: Save CSV ──────────────────────────────────────────────────────────

merged.to_csv(OUTPUT_CSV, index=False)
print("\nFull comparison table saved to: %s" % OUTPUT_CSV)


# ── Step 6: Plots ─────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("Step 5: Generating plots")
print("=" * 60)

BLUE   = "#2196F3"
ORANGE = "#FF9800"


def bar_comparison(df, sim_col, pub_col, ylabel, title, outpath):
    """Side-by-side bar chart per replicate."""
    g = df.dropna(subset=[sim_col, pub_col]).copy()
    labels = [
        "%s\n%s\n%s" % (row["folder"], row["Environment (-)"][:10], row["Phenotype"][:10])
        for _, row in g.iterrows()
    ]
    x = np.arange(len(labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(max(14, len(labels) * 0.35), 5))
    ax.bar(x - w/2, g[pub_col], w, label="Published (Schäfer 2022)",
           color=ORANGE, alpha=0.85)
    ax.bar(x + w/2, g[sim_col], w, label="This simulation",
           color=BLUE, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6, rotation=45, ha="right")
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved: %s" % outpath)


bar_comparison(merged, "sim_shoot_dw_g", "pub_shoot_dw_g",
               "Shoot dry weight (g)",
               "Shoot Dry Weight: Simulation vs Published (Schäfer 2022)",
               os.path.join(PLOTS_DIR, "shoot_dw.png"))

bar_comparison(merged, "sim_root_carbon_g", "pub_root_carbon_g",
               "Total root carbon cost (g)",
               "Root Carbon Cost: Simulation vs Published (Schäfer 2022)",
               os.path.join(PLOTS_DIR, "root_carbon.png"))

bar_comparison(merged, "sim_deep_carbon_g", "pub_deep_carbon_g",
               "Deep soil carbon >50 cm (g)",
               "Deep Soil Carbon: Simulation vs Published (Schäfer 2022)",
               os.path.join(PLOTS_DIR, "deep_carbon.png"))


# p-value heatmap (shoot DW)
if not stats_df.empty:
    sdw_stats = stats_df[stats_df["metric"] == "Shoot DW (g)"]
    if not sdw_stats.empty:
        pivot = sdw_stats.pivot(index="phenotype", columns="environment", values="p")
        fig, ax = plt.subplots(figsize=(
            max(8, pivot.shape[1] * 1.8),
            max(5, pivot.shape[0] * 0.7)
        ))
        im = ax.imshow(pivot.values, cmap="RdYlGn_r", vmin=0, vmax=0.1, aspect="auto")
        ax.set_xticks(range(pivot.shape[1]))
        ax.set_xticklabels(pivot.columns, rotation=30, ha="right", fontsize=9)
        ax.set_yticks(range(pivot.shape[0]))
        ax.set_yticklabels(pivot.index, fontsize=9)
        for r in range(pivot.shape[0]):
            for c in range(pivot.shape[1]):
                v = pivot.values[r, c]
                if not np.isnan(v):
                    lbl = ("***" if v < 0.001 else
                           ("**"  if v < 0.01  else
                           ("*"   if v < 0.05  else ("%.2f" % v))))
                    ax.text(c, r, lbl, ha="center", va="center", fontsize=8,
                            color="white" if v < 0.02 else "black")
        plt.colorbar(im, ax=ax, label="p-value")
        ax.set_title(
            "Shoot Dry Weight — p-values (t-test, sim vs published)\n"
            "* p<0.05   ** p<0.01   *** p<0.001",
            fontsize=11, fontweight="bold"
        )
        plt.tight_layout()
        path = os.path.join(PLOTS_DIR, "pvalue_heatmap.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print("  Saved: %s" % path)

print("\nDone.")
print("  Plots : %s/" % PLOTS_DIR)
print("  Table : %s"  % OUTPUT_CSV)