#!/usr/bin/env python3
"""
04 - Supplementary Analysis

Generates supplementary tables:
- STable: Genderize.io identification rates by World Bank region
- STable: MIMIC version-stratified citation counts

Usage:
    python 04_supplementary_analysis.py
"""

import gzip
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
AUTHORS_DIR = DATA_DIR / "authors"
SECOND_DEGREE_DIR = DATA_DIR / "second_degree"
SUPPLEMENTARY_DIR = SCRIPT_DIR.parent / "manuscript" / "supplementary"
SUPPLEMENTARY_DIR.mkdir(parents=True, exist_ok=True)

INCOME_FILE = DATA_DIR / "world_bank_income.json"

# Dataset author files
DATASET_FILES = {
    "MIMIC-I": "mimic-i_with_gender.json",
    "MIMIC-II": "mimic-ii_with_gender.json",
    "MIMIC-III": "mimic-iii_with_gender.json",
    "MIMIC-IV": "mimic-iv_with_gender.json",
    "UK-Biobank": "uk-biobank_with_gender.json.gz",
    "OpenSAFELY": "opensafely_with_gender.json.gz",
    "All-of-Us": "all-of-us_with_gender.json",
}

# Second-degree files
SECOND_DEGREE_FILES = {
    "MIMIC-I": "mimic-i.json.gz",
    "MIMIC-II": "mimic-ii.json.gz",
    "MIMIC-III": "mimic-iii.json.gz",
    "MIMIC-IV": "mimic-iv.json.gz",
}

# ISO-2 country code to World Bank region mapping
# Based on the World Bank's standard regional classification
COUNTRY_TO_REGION = {
    # East Asia & Pacific
    "AS": "East Asia & Pacific", "AU": "East Asia & Pacific",
    "BN": "East Asia & Pacific", "KH": "East Asia & Pacific",
    "CN": "East Asia & Pacific", "FJ": "East Asia & Pacific",
    "GU": "East Asia & Pacific", "HK": "East Asia & Pacific",
    "ID": "East Asia & Pacific", "JP": "East Asia & Pacific",
    "KI": "East Asia & Pacific", "KP": "East Asia & Pacific",
    "KR": "East Asia & Pacific", "LA": "East Asia & Pacific",
    "MO": "East Asia & Pacific", "MH": "East Asia & Pacific",
    "FM": "East Asia & Pacific", "MN": "East Asia & Pacific",
    "MM": "East Asia & Pacific", "NR": "East Asia & Pacific",
    "NC": "East Asia & Pacific", "NZ": "East Asia & Pacific",
    "MP": "East Asia & Pacific", "PW": "East Asia & Pacific",
    "PG": "East Asia & Pacific", "PH": "East Asia & Pacific",
    "WS": "East Asia & Pacific", "SG": "East Asia & Pacific",
    "SB": "East Asia & Pacific", "TW": "East Asia & Pacific",
    "TH": "East Asia & Pacific", "TL": "East Asia & Pacific",
    "TO": "East Asia & Pacific", "TV": "East Asia & Pacific",
    "VU": "East Asia & Pacific", "VN": "East Asia & Pacific",
    "MY": "East Asia & Pacific",
    # Europe & Central Asia
    "AL": "Europe & Central Asia", "AD": "Europe & Central Asia",
    "AM": "Europe & Central Asia", "AT": "Europe & Central Asia",
    "AZ": "Europe & Central Asia", "BY": "Europe & Central Asia",
    "BE": "Europe & Central Asia", "BA": "Europe & Central Asia",
    "BG": "Europe & Central Asia", "HR": "Europe & Central Asia",
    "CY": "Europe & Central Asia", "CZ": "Europe & Central Asia",
    "DK": "Europe & Central Asia", "EE": "Europe & Central Asia",
    "FI": "Europe & Central Asia", "FR": "Europe & Central Asia",
    "GE": "Europe & Central Asia", "DE": "Europe & Central Asia",
    "GR": "Europe & Central Asia", "GL": "Europe & Central Asia",
    "HU": "Europe & Central Asia", "IS": "Europe & Central Asia",
    "IE": "Europe & Central Asia", "IT": "Europe & Central Asia",
    "KZ": "Europe & Central Asia", "XK": "Europe & Central Asia",
    "KG": "Europe & Central Asia", "LV": "Europe & Central Asia",
    "LI": "Europe & Central Asia", "LT": "Europe & Central Asia",
    "LU": "Europe & Central Asia", "MK": "Europe & Central Asia",
    "MD": "Europe & Central Asia", "MC": "Europe & Central Asia",
    "ME": "Europe & Central Asia", "NL": "Europe & Central Asia",
    "NO": "Europe & Central Asia", "PL": "Europe & Central Asia",
    "PT": "Europe & Central Asia", "RO": "Europe & Central Asia",
    "RU": "Europe & Central Asia", "SM": "Europe & Central Asia",
    "RS": "Europe & Central Asia", "SK": "Europe & Central Asia",
    "SI": "Europe & Central Asia", "ES": "Europe & Central Asia",
    "SE": "Europe & Central Asia", "CH": "Europe & Central Asia",
    "TJ": "Europe & Central Asia", "TR": "Europe & Central Asia",
    "TM": "Europe & Central Asia", "UA": "Europe & Central Asia",
    "GB": "Europe & Central Asia", "UZ": "Europe & Central Asia",
    "FO": "Europe & Central Asia", "GI": "Europe & Central Asia",
    "IM": "Europe & Central Asia", "JE": "Europe & Central Asia",
    "GG": "Europe & Central Asia", "MT": "Europe & Central Asia",
    # Latin America & Caribbean
    "AG": "Latin America & Caribbean", "AR": "Latin America & Caribbean",
    "AW": "Latin America & Caribbean", "BS": "Latin America & Caribbean",
    "BB": "Latin America & Caribbean", "BZ": "Latin America & Caribbean",
    "BO": "Latin America & Caribbean", "BR": "Latin America & Caribbean",
    "VG": "Latin America & Caribbean", "KY": "Latin America & Caribbean",
    "CL": "Latin America & Caribbean", "CO": "Latin America & Caribbean",
    "CR": "Latin America & Caribbean", "CU": "Latin America & Caribbean",
    "CW": "Latin America & Caribbean", "DM": "Latin America & Caribbean",
    "DO": "Latin America & Caribbean", "EC": "Latin America & Caribbean",
    "SV": "Latin America & Caribbean", "GD": "Latin America & Caribbean",
    "GT": "Latin America & Caribbean", "GY": "Latin America & Caribbean",
    "HT": "Latin America & Caribbean", "HN": "Latin America & Caribbean",
    "JM": "Latin America & Caribbean", "MX": "Latin America & Caribbean",
    "NI": "Latin America & Caribbean", "PA": "Latin America & Caribbean",
    "PY": "Latin America & Caribbean", "PE": "Latin America & Caribbean",
    "PR": "Latin America & Caribbean", "KN": "Latin America & Caribbean",
    "LC": "Latin America & Caribbean", "MF": "Latin America & Caribbean",
    "VC": "Latin America & Caribbean", "SX": "Latin America & Caribbean",
    "SR": "Latin America & Caribbean", "TT": "Latin America & Caribbean",
    "TC": "Latin America & Caribbean", "UY": "Latin America & Caribbean",
    "VE": "Latin America & Caribbean", "VI": "Latin America & Caribbean",
    # Middle East & North Africa
    "DZ": "Middle East & North Africa", "BH": "Middle East & North Africa",
    "DJ": "Middle East & North Africa", "EG": "Middle East & North Africa",
    "IR": "Middle East & North Africa", "IQ": "Middle East & North Africa",
    "IL": "Middle East & North Africa", "JO": "Middle East & North Africa",
    "KW": "Middle East & North Africa", "LB": "Middle East & North Africa",
    "LY": "Middle East & North Africa", "MA": "Middle East & North Africa",
    "OM": "Middle East & North Africa", "PS": "Middle East & North Africa",
    "QA": "Middle East & North Africa", "SA": "Middle East & North Africa",
    "SY": "Middle East & North Africa", "TN": "Middle East & North Africa",
    "AE": "Middle East & North Africa", "YE": "Middle East & North Africa",
    # North America
    "BM": "North America", "CA": "North America", "US": "North America",
    # South Asia
    "AF": "South Asia", "BD": "South Asia", "BT": "South Asia",
    "IN": "South Asia", "MV": "South Asia", "NP": "South Asia",
    "PK": "South Asia", "LK": "South Asia",
    # Sub-Saharan Africa
    "AO": "Sub-Saharan Africa", "BJ": "Sub-Saharan Africa",
    "BW": "Sub-Saharan Africa", "BF": "Sub-Saharan Africa",
    "BI": "Sub-Saharan Africa", "CV": "Sub-Saharan Africa",
    "CM": "Sub-Saharan Africa", "CF": "Sub-Saharan Africa",
    "TD": "Sub-Saharan Africa", "KM": "Sub-Saharan Africa",
    "CG": "Sub-Saharan Africa", "CD": "Sub-Saharan Africa",
    "CI": "Sub-Saharan Africa", "GQ": "Sub-Saharan Africa",
    "ER": "Sub-Saharan Africa", "SZ": "Sub-Saharan Africa",
    "ET": "Sub-Saharan Africa", "GA": "Sub-Saharan Africa",
    "GM": "Sub-Saharan Africa", "GH": "Sub-Saharan Africa",
    "GN": "Sub-Saharan Africa", "GW": "Sub-Saharan Africa",
    "KE": "Sub-Saharan Africa", "LS": "Sub-Saharan Africa",
    "LR": "Sub-Saharan Africa", "MG": "Sub-Saharan Africa",
    "MW": "Sub-Saharan Africa", "ML": "Sub-Saharan Africa",
    "MR": "Sub-Saharan Africa", "MU": "Sub-Saharan Africa",
    "MZ": "Sub-Saharan Africa", "NA": "Sub-Saharan Africa",
    "NE": "Sub-Saharan Africa", "NG": "Sub-Saharan Africa",
    "RW": "Sub-Saharan Africa", "ST": "Sub-Saharan Africa",
    "SN": "Sub-Saharan Africa", "SC": "Sub-Saharan Africa",
    "SL": "Sub-Saharan Africa", "SO": "Sub-Saharan Africa",
    "ZA": "Sub-Saharan Africa", "SS": "Sub-Saharan Africa",
    "SD": "Sub-Saharan Africa", "TZ": "Sub-Saharan Africa",
    "TG": "Sub-Saharan Africa", "UG": "Sub-Saharan Africa",
    "ZM": "Sub-Saharan Africa", "ZW": "Sub-Saharan Africa",
}

# Canonical region order for output
REGION_ORDER = [
    "North America",
    "Europe & Central Asia",
    "East Asia & Pacific",
    "Middle East & North Africa",
    "Latin America & Caribbean",
    "South Asia",
    "Sub-Saharan Africa",
]


def load_author_data(filename):
    """Load a dataset author JSON file (supports .json and .json.gz)."""
    filepath = AUTHORS_DIR / filename
    if filename.endswith('.gz'):
        with gzip.open(filepath, 'rt') as f:
            return json.load(f)
    with open(filepath) as f:
        return json.load(f)


def get_author_country(author):
    """Get the primary country code for an author."""
    countries = author.get("countries", [])
    if countries:
        return countries[0]
    institutions = author.get("institutions", [])
    for inst in institutions:
        country = inst.get("country")
        if country:
            return country
    return None


def get_region(country_code):
    """Map a country code to a World Bank region."""
    if not country_code:
        return None
    return COUNTRY_TO_REGION.get(country_code)


# =============================================================================
# Part 1: Genderize.io Identification Rates by World Bank Region
# =============================================================================

def analyze_genderize_by_region():
    """
    For each dataset, group authors by World Bank region and calculate the
    percentage whose gender was successfully identified by Genderize.io.
    """
    print("=" * 70)
    print("Genderize.io Identification Rates by World Bank Region")
    print("=" * 70)

    # Collect results: {region: {dataset: {total, identified}}}
    results = defaultdict(lambda: defaultdict(lambda: {"total": 0, "identified": 0}))

    for dataset_name, filename in DATASET_FILES.items():
        print(f"\nProcessing {dataset_name}...")
        data = load_author_data(filename)
        papers = data.get("papers", [])

        # Deduplicate authors by ID to avoid counting the same person multiple times
        seen_authors = {}
        for paper in papers:
            for author in paper.get("authors", []):
                author_id = author.get("id")
                if author_id and author_id not in seen_authors:
                    seen_authors[author_id] = author

        print(f"  Unique authors: {len(seen_authors)}")

        for author_id, author in seen_authors.items():
            country = get_author_country(author)
            region = get_region(country)
            if region is None:
                region = "Unknown/Unclassified"

            gender = author.get("gender")
            results[region][dataset_name]["total"] += 1
            if gender and gender in ("male", "female"):
                results[region][dataset_name]["identified"] += 1

    # Build table
    all_regions = [r for r in REGION_ORDER if r in results]
    if "Unknown/Unclassified" in results:
        all_regions.append("Unknown/Unclassified")

    all_datasets = list(DATASET_FILES.keys())

    rows = []
    for region in all_regions:
        row = {"Region": region}
        for ds in all_datasets:
            total = results[region][ds]["total"]
            identified = results[region][ds]["identified"]
            if total > 0:
                pct = identified / total * 100
                row[f"{ds} (n)"] = total
                row[f"{ds} (%)"] = round(pct, 1)
            else:
                row[f"{ds} (n)"] = 0
                row[f"{ds} (%)"] = "-"
        rows.append(row)

    # Add totals row
    total_row = {"Region": "Total"}
    for ds in all_datasets:
        total_n = sum(results[r][ds]["total"] for r in all_regions)
        total_id = sum(results[r][ds]["identified"] for r in all_regions)
        total_row[f"{ds} (n)"] = total_n
        total_row[f"{ds} (%)"] = round(total_id / total_n * 100, 1) if total_n > 0 else "-"
    rows.append(total_row)

    df = pd.DataFrame(rows)

    # Save CSV
    csv_path = SUPPLEMENTARY_DIR / "stable_genderize_regional.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved CSV: {csv_path}")

    # Save LaTeX
    tex_path = SUPPLEMENTARY_DIR / "stable_genderize_regional.tex"
    _save_genderize_latex(df, all_datasets, tex_path)
    print(f"Saved LaTeX: {tex_path}")

    # Print summary
    print(f"\n{df.to_string(index=False)}")

    return df


def _save_genderize_latex(df, datasets, tex_path):
    """Save the Genderize.io regional table as a LaTeX file."""
    n_ds = len(datasets)
    col_spec = "l" + "rr" * n_ds

    lines = []
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{Genderize.io gender identification rates by World Bank region and dataset.}")
    lines.append("\\label{tab:genderize_regional}")
    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
    lines.append("\\toprule")

    # Header row 1: dataset names spanning two columns each
    header1 = "Region"
    for ds in datasets:
        header1 += f" & \\multicolumn{{2}}{{c}}{{{ds}}}"
    header1 += " \\\\"
    lines.append(header1)

    # Cmidrule under each dataset
    cmidrules = ""
    for i, ds in enumerate(datasets):
        col_start = 2 + i * 2
        col_end = col_start + 1
        cmidrules += f"\\cmidrule(lr){{{col_start}-{col_end}}} "
    lines.append(cmidrules)

    # Header row 2: n and %
    header2 = ""
    for ds in datasets:
        header2 += " & $n$ & \\%"
    header2 += " \\\\"
    lines.append(header2)
    lines.append("\\midrule")

    # Data rows
    for _, row in df.iterrows():
        region = row["Region"]
        if region == "Total":
            lines.append("\\midrule")
        parts = [region.replace("&", "\\&")]
        for ds in datasets:
            n_val = row[f"{ds} (n)"]
            pct_val = row[f"{ds} (%)"]
            parts.append(f"{n_val:,}" if isinstance(n_val, (int, float)) and n_val > 0 else "--")
            parts.append(f"{pct_val}" if pct_val != "-" else "--")
        lines.append(" & ".join(str(p) for p in parts) + " \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    with open(tex_path, "w") as f:
        f.write("\n".join(lines) + "\n")


# =============================================================================
# Part 2: MIMIC Version-Stratified Citation Counts
# =============================================================================

def analyze_mimic_versions():
    """
    For each MIMIC version, count first-degree and second-degree papers
    and calculate the citation amplification ratio.
    """
    print("\n" + "=" * 70)
    print("MIMIC Version-Stratified Citation Counts")
    print("=" * 70)

    rows = []
    total_first = 0
    total_second = 0

    for version in ["MIMIC-I", "MIMIC-II", "MIMIC-III", "MIMIC-IV"]:
        # First-degree papers from author file
        author_file = DATASET_FILES[version]
        author_data = load_author_data(author_file)
        first_degree = author_data.get("total_papers", 0)

        # Second-degree papers from second_degree file
        sd_file = SECOND_DEGREE_DIR / SECOND_DEGREE_FILES[version]
        with gzip.open(sd_file, "rt") as f:
            sd_data = json.load(f)
        second_degree = sd_data.get("total_papers", 0)

        # Citation amplification ratio
        amplification = second_degree / first_degree if first_degree > 0 else 0

        rows.append({
            "MIMIC Version": version,
            "Launch Year": author_data.get("launch_year", ""),
            "First-Degree Papers": first_degree,
            "Second-Degree Papers": second_degree,
            "Amplification Ratio": round(amplification, 1),
        })

        total_first += first_degree
        total_second += second_degree

        print(f"  {version}: 1st={first_degree:,}, 2nd={second_degree:,}, ratio={amplification:.1f}x")

    # Add totals row
    total_amp = total_second / total_first if total_first > 0 else 0
    rows.append({
        "MIMIC Version": "Total (Combined)",
        "Launch Year": "",
        "First-Degree Papers": total_first,
        "Second-Degree Papers": total_second,
        "Amplification Ratio": round(total_amp, 1),
    })

    df = pd.DataFrame(rows)

    # Save CSV
    csv_path = SUPPLEMENTARY_DIR / "stable_mimic_versions.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved CSV: {csv_path}")

    # Save LaTeX
    tex_path = SUPPLEMENTARY_DIR / "stable_mimic_versions.tex"
    _save_mimic_latex(df, tex_path)
    print(f"Saved LaTeX: {tex_path}")

    # Print summary
    print(f"\n{df.to_string(index=False)}")

    return df


def _save_mimic_latex(df, tex_path):
    """Save the MIMIC version table as a LaTeX file."""
    lines = []
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{Citation counts and amplification ratios by MIMIC version.}")
    lines.append("\\label{tab:mimic_versions}")
    lines.append("\\begin{tabular}{llrrr}")
    lines.append("\\toprule")
    lines.append("Version & Launch Year & First-Degree & Second-Degree & Amplification \\\\")
    lines.append(" & & Papers & Papers & Ratio \\\\")
    lines.append("\\midrule")

    for _, row in df.iterrows():
        version = row["MIMIC Version"]
        if version == "Total (Combined)":
            lines.append("\\midrule")
        launch = row["Launch Year"]
        first = f"{row['First-Degree Papers']:,}"
        second = f"{row['Second-Degree Papers']:,}"
        amp = f"{row['Amplification Ratio']}x"
        lines.append(f"{version} & {launch} & {first} & {second} & {amp} \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    with open(tex_path, "w") as f:
        f.write("\n".join(lines) + "\n")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("04 - Supplementary Analysis")
    print()
    analyze_genderize_by_region()
    analyze_mimic_versions()
    print("\nDone.")
