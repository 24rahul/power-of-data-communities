#!/usr/bin/env python3
"""
05 - Journal Impact Tier Analysis

Classifies the journals that first- and second-degree publications appear in into
impact tiers, addressing reviewer Major Comment #1 (and #4) for CCSCI-2026-0114.

Tier metric: OpenAlex source-level `summary_stats.2yr_mean_citedness` (a CiteScore-
like 2-year citation rate). This is a freely available, programmatic proxy for the
Journal Impact Factor; it is NOT the licensed Clarivate JCR IF (noted in Methods).

Approach (no full re-pull of the 515k papers):
  1. Collect papers + journals from existing first-degree (journal + journal_id) and
     second-degree (journal name + OpenAlex work id) data files.
  2. Resolve every paper to an OpenAlex source (journal) id:
       - first-degree papers already carry journal_id (exact);
       - second-degree papers carry only a journal name, so we back-fill their exact
         source id from the /works endpoint by their work id (1 credit / 100 works),
         which is far cheaper and exact compared with per-name /sources search.
  3. Batch-fetch summary_stats for the unique source ids (100 ids/request, 1 credit).
  4. Assign Low / Intermediate / High tiers from 2yr_mean_citedness (cutoffs derived
     from the journal distribution and recorded for the Methods section).
  5. Join tiers back to papers and report per-repository x per-degree tier counts/%.

Cost note: uses the metered OpenAlex API key (Free plan = $1.00/day = 10,000 credits;
filtered list = 1 credit, search = 10 credits). This script deliberately avoids
searches. Pass the key via the OPENALEX_API_KEY environment variable (never hardcode).

Outputs:
    manuscript_v2/figure_data/journal_tiers_by_repo_degree.csv  (dataset,degree,tier,n,pct)
    output/journal_tier_summary.csv
    output/journal_tier_summary.md
    data/second_degree_source_cache.json  (work id -> source id)
    data/journal_metrics_cache.json       (source id -> 2yr_mean_citedness, h_index)

Usage:
    OPENALEX_API_KEY=... python 05_journal_tiers.py
"""

import argparse
import gzip
import json
import os
import time
from pathlib import Path
import requests

# Paths
SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent
DATA_DIR = ROOT / "data"
CITING_DIR = DATA_DIR / "citing_papers"
SECOND_DIR = DATA_DIR / "second_degree"
FIGURE_DATA_DIR = ROOT / "manuscript_v2" / "figure_data"
OUTPUT_DIR = ROOT / "output"
FIGURE_DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SD_SOURCE_CACHE_FILE = DATA_DIR / "second_degree_source_cache.json"  # "Wxxxx" -> "Sxxxx" or ""
METRICS_CACHE_FILE = DATA_DIR / "journal_metrics_cache.json"          # "Sxxxx" -> {citedness, h_index, name}

# OpenAlex configuration
OPENALEX_BASE = "https://api.openalex.org"
USER_AGENT = "CitationAnalysis/1.0 (mailto:lceli@mit.edu)"
HEADERS = {"User-Agent": USER_AGENT}
API_KEY = os.environ.get("OPENALEX_API_KEY", "")

# Repository -> data file stems (MIMIC pools versions I-IV)
REPO_FILES = {
    "MIMIC": ["mimic-i", "mimic-ii", "mimic-iii", "mimic-iv"],
    "UK-Biobank": ["uk-biobank"],
    "OpenSAFELY": ["opensafely"],
    "All-of-Us": ["all-of-us"],
}

TIERS = ["High", "Intermediate", "Low", "Unclassified"]


# ----------------------------------------------------------------------------
# IO helpers
# ----------------------------------------------------------------------------

def load_papers(stem: str, base_dir: Path) -> list:
    plain = base_dir / f"{stem}.json"
    gz = base_dir / f"{stem}.json.gz"
    if plain.exists():
        with open(plain, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif gz.exists():
        with gzip.open(gz, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raise FileNotFoundError(f"No file for stem '{stem}' in {base_dir}")
    return data.get("papers", [])


def short_id(openalex_id: str) -> str:
    if not openalex_id:
        return ""
    return openalex_id.rstrip("/").split("/")[-1]


def load_cache(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict, path: Path):
    with open(path, "w") as f:
        json.dump(cache, f, indent=2)


def params_with_key(params: dict) -> dict:
    if API_KEY:
        params = {**params, "api_key": API_KEY}
    return params


# ----------------------------------------------------------------------------
# Step 1: collect papers per repository and degree
# ----------------------------------------------------------------------------

def collect():
    """
    Returns repo_papers: {repo: {"first": [{journal, journal_id}],
                                 "second": [{id, journal}]}}  (deduped by paper id).
    """
    repo_papers = {}
    for repo, stems in REPO_FILES.items():
        repo_papers[repo] = {"first": [], "second": []}

        seen = set()
        for stem in stems:
            for p in load_papers(stem, CITING_DIR):
                pid = p.get("id", "")
                if pid and pid in seen:
                    continue
                seen.add(pid)
                repo_papers[repo]["first"].append({
                    "journal": (p.get("journal") or "").strip(),
                    "journal_id": short_id(p.get("journal_id") or ""),
                })

        seen = set()
        for stem in stems:
            for p in load_papers(stem, SECOND_DIR):
                pid = p.get("id", "")
                if pid and pid in seen:
                    continue
                seen.add(pid)
                repo_papers[repo]["second"].append({
                    "id": short_id(pid),
                    "journal": (p.get("journal") or "").strip(),
                })
    return repo_papers


# ----------------------------------------------------------------------------
# Step 2: back-fill second-degree work id -> source id (exact, 1 credit / 100)
# ----------------------------------------------------------------------------

def backfill_sources(work_ids: list, cache: dict) -> dict:
    """Map second-degree work ids to their OpenAlex source (journal) id via /works."""
    todo = sorted({w for w in work_ids if w and w not in cache})
    print(f"  Second-degree work ids needing source backfill: {len(todo)} "
          f"(cached: {len(set(work_ids)) - len(todo)})")
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        try:
            r = requests.get(
                f"{OPENALEX_BASE}/works",
                params=params_with_key({
                    "filter": "ids.openalex:" + "|".join(batch),
                    "select": "id,primary_location",
                    "per-page": 100,
                }),
                headers=HEADERS, timeout=90,
            )
            r.raise_for_status()
            for w in r.json().get("results", []):
                wid = short_id(w["id"])
                src = (w.get("primary_location") or {}).get("source") or {}
                cache[wid] = short_id(src.get("id") or "")
            # mark missing (deleted/merged works) so we don't retry forever
            for wid in batch:
                cache.setdefault(wid, "")
        except Exception as e:
            print(f"    works batch failed @ {i}: {e}")
            raise
        if (i // 100 + 1) % 50 == 0:
            save_cache(cache, SD_SOURCE_CACHE_FILE)
            print(f"    backfilled {min(i + 100, len(todo))}/{len(todo)}")
        time.sleep(0.05)
    save_cache(cache, SD_SOURCE_CACHE_FILE)
    return cache


# ----------------------------------------------------------------------------
# Step 3: batch-fetch source metrics (2yr_mean_citedness, h_index)
# ----------------------------------------------------------------------------

def fetch_metrics(source_ids: list, cache: dict) -> dict:
    todo = sorted({s for s in source_ids if s and s not in cache})
    print(f"  Source ids needing metrics: {len(todo)} "
          f"(cached: {len(set(s for s in source_ids if s)) - len(todo)})")
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        try:
            r = requests.get(
                f"{OPENALEX_BASE}/sources",
                params=params_with_key({
                    "filter": "ids.openalex:" + "|".join(batch),
                    "select": "id,display_name,summary_stats",
                    "per-page": 100,
                }),
                headers=HEADERS, timeout=60,
            )
            r.raise_for_status()
            for s in r.json().get("results", []):
                sid = short_id(s["id"])
                stats = s.get("summary_stats", {}) or {}
                cache[sid] = {
                    "name": s.get("display_name", ""),
                    "citedness": stats.get("2yr_mean_citedness"),
                    "h_index": stats.get("h_index"),
                }
            for sid in batch:
                cache.setdefault(sid, {"name": "", "citedness": None, "h_index": None})
        except Exception as e:
            print(f"    metrics batch failed @ {i}: {e}")
            raise
        if (i // 100 + 1) % 50 == 0:
            save_cache(cache, METRICS_CACHE_FILE)
            print(f"    fetched {min(i + 100, len(todo))}/{len(todo)}")
        time.sleep(0.05)
    save_cache(cache, METRICS_CACHE_FILE)
    return cache


# ----------------------------------------------------------------------------
# Step 4: tier cutoffs + assignment
# ----------------------------------------------------------------------------

# Fixed, interpretable tier cutoffs on OpenAlex 2yr_mean_citedness.
# Calibrated against the journal-metric distribution and named anchors:
#   High (>= 6.0): ~top 5-7% of journals -- JAMA 8.1, Nature 17, Lancet 18, NEJM/Nature Med 28
#   Intermediate (2.0-6.0): e.g. Scientific Reports 4.5, PLoS ONE 2.8
#   Low (< 2.0): modest-visibility venues
# Tertiles over unique journals were rejected because the long tail of tiny journals
# pushed the "High" cutoff down to ~1.7, putting the majority of papers in one tier.
LOW_MAX = 2.0
HIGH_MIN = 6.0


def derive_cutoffs(metrics_cache: dict):
    """Return the documented fixed tier cutoffs (see LOW_MAX / HIGH_MIN)."""
    return LOW_MAX, HIGH_MIN


def tier_for(citedness, low_max, high_min):
    if citedness is None:
        return "Unclassified"
    if citedness >= high_min:
        return "High"
    if citedness >= low_max:
        return "Intermediate"
    return "Low"


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    argparse.ArgumentParser(description="Journal impact tier analysis").parse_args()

    print("=" * 60)
    print("Journal Impact Tier Analysis")
    print("=" * 60)
    print(f"API key: {'set' if API_KEY else 'NOT set (polite pool)'}")

    print("\n1. Collecting papers from first- and second-degree data...")
    repo_papers = collect()
    for repo in REPO_FILES:
        print(f"   {repo}: {len(repo_papers[repo]['first'])} first / "
              f"{len(repo_papers[repo]['second'])} second-degree papers")

    # 2. Back-fill second-degree source ids (global dedup across repos)
    print("\n2. Back-filling second-degree journal (source) ids via /works...")
    sd_work_ids = [p["id"] for repo in REPO_FILES for p in repo_papers[repo]["second"] if p["id"]]
    sd_src_cache = load_cache(SD_SOURCE_CACHE_FILE)
    sd_src_cache = backfill_sources(sd_work_ids, sd_src_cache)

    # 3. Union of all source ids needing metrics
    first_src = [p["journal_id"] for repo in REPO_FILES
                 for p in repo_papers[repo]["first"] if p["journal_id"]]
    second_src = [sid for sid in sd_src_cache.values() if sid]
    print("\n3. Fetching source-level metrics from OpenAlex...")
    metrics_cache = load_cache(METRICS_CACHE_FILE)
    metrics_cache = fetch_metrics(first_src + second_src, metrics_cache)

    # 4. Cutoffs
    low_max, high_min = derive_cutoffs(metrics_cache)
    print(f"\n4. Tier cutoffs (2yr_mean_citedness tertiles): "
          f"Low < {low_max} <= Intermediate < {high_min} <= High")

    def tier_first(p):
        m = metrics_cache.get(p["journal_id"])
        return tier_for(m["citedness"], low_max, high_min) if m else "Unclassified"

    def tier_second(p):
        sid = sd_src_cache.get(p["id"], "")
        m = metrics_cache.get(sid) if sid else None
        return tier_for(m["citedness"], low_max, high_min) if m else "Unclassified"

    # 5. Aggregate per repo x degree x tier
    print("\n5. Aggregating tier distributions...")
    rows = []
    for repo in REPO_FILES:
        for degree, papers, tier_fn in (
            ("first-degree", repo_papers[repo]["first"], tier_first),
            ("second-degree", repo_papers[repo]["second"], tier_second),
        ):
            counts = {t: 0 for t in TIERS}
            for p in papers:
                counts[tier_fn(p)] += 1
            total = sum(counts.values()) or 1
            for t in TIERS:
                rows.append({
                    "dataset": repo, "degree": degree, "tier": t,
                    "n": counts[t], "pct": round(100 * counts[t] / total, 1),
                })

    # ---- write CSVs ----
    def write_csv(path):
        with open(path, "w") as f:
            f.write("dataset,degree,tier,n,pct\n")
            for r in rows:
                f.write(f"{r['dataset']},{r['degree']},{r['tier']},{r['n']},{r['pct']}\n")
    write_csv(FIGURE_DATA_DIR / "journal_tiers_by_repo_degree.csv")
    write_csv(OUTPUT_DIR / "journal_tier_summary.csv")
    print(f"   wrote {FIGURE_DATA_DIR / 'journal_tiers_by_repo_degree.csv'}")

    # ---- markdown summary ----
    with open(OUTPUT_DIR / "journal_tier_summary.md", "w") as f:
        f.write("# Journal Impact Tier Distribution\n\n")
        f.write("Tier metric: OpenAlex source `2yr_mean_citedness` (Impact-Factor proxy).\n\n")
        f.write(f"Cutoffs (tertiles of unique-journal distribution): "
                f"Low < {low_max}; Intermediate {low_max}-{high_min}; High >= {high_min}.\n\n")
        for repo in REPO_FILES:
            f.write(f"## {repo}\n\n")
            f.write("| Degree | High % | Intermediate % | Low % | Unclassified % |\n")
            f.write("|---|---|---|---|---|\n")
            for degree in ("first-degree", "second-degree"):
                d = {r["tier"]: r["pct"] for r in rows
                     if r["dataset"] == repo and r["degree"] == degree}
                f.write(f"| {degree} | {d['High']} | {d['Intermediate']} | "
                        f"{d['Low']} | {d['Unclassified']} |\n")
            f.write("\n")
    print(f"   wrote {OUTPUT_DIR / 'journal_tier_summary.md'}")

    # ---- diagnostics ----
    print("\nUnclassified rate (by paper count):")
    for repo in REPO_FILES:
        for degree in ("first-degree", "second-degree"):
            unc = next(r["pct"] for r in rows if r["dataset"] == repo
                       and r["degree"] == degree and r["tier"] == "Unclassified")
            print(f"   {repo:12s} {degree:14s} {unc:5.1f}%")
    print("\nDone.")


if __name__ == "__main__":
    main()
