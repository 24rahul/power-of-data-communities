#!/usr/bin/env python3
"""
03 - Analysis and Visualization

Generates figures and tables for the paper:
- Figure 1: Cumulative citations over calendar time (1997-2024)
- Figure 2: Two-panel impact plot (h-index style)
- Table 2: Author demographics (gender, countries, HIC/LMIC)

Usage:
    python 03_analysis.py
    python 03_analysis.py --figure 1
    python 03_analysis.py --table 2
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from scipy import stats

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
AUTHORS_DIR = DATA_DIR / "authors"
FIGURES_DIR = SCRIPT_DIR.parent / "figures"
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# World Bank income classification
INCOME_FILE = DATA_DIR / "world_bank_income.json"

# Dataset configuration (for loading individual files)
DATASET_FILES = {
    'MIMIC-I': {'launch_year': 1997},
    'MIMIC-II': {'launch_year': 2003},
    'MIMIC-III': {'launch_year': 2016},
    'MIMIC-IV': {'launch_year': 2022},
    'UK-Biobank': {'launch_year': 2015},
    'OpenSAFELY': {'launch_year': 2020},
    'All-of-Us': {'launch_year': 2018},
}

# Analysis configuration (MIMIC combined)
DATASETS = {
    'MIMIC': {'color': '#1f77b4', 'launch_year': 1997, 'funding_m': 14.4, 'marker': 'o'},
    'UK-Biobank': {'color': '#2ca02c', 'launch_year': 2015, 'funding_m': 525.5, 'marker': 's'},
    'OpenSAFELY': {'color': '#ff7f0e', 'launch_year': 2020, 'funding_m': 53.7, 'marker': '^'},
    'All-of-Us': {'color': '#d62728', 'launch_year': 2018, 'funding_m': 2160.0, 'marker': 'D'},
}

# MIMIC components (to be combined)
MIMIC_COMPONENTS = ['MIMIC-I', 'MIMIC-II', 'MIMIC-III', 'MIMIC-IV']


def load_income_classification():
    """Load World Bank income classification."""
    with open(INCOME_FILE) as f:
        return json.load(f)


def classify_income(country_code, income_data):
    """
    Classify country as HIC or LMIC.
    
    Returns: 'HIC', 'LMIC', or 'Unknown'
    """
    if not country_code:
        return 'Unknown'
    
    info = income_data.get(country_code, {})
    level = info.get('income_level', '')
    
    if level == 'HIC':
        return 'HIC'
    elif level in ['UMC', 'LMC', 'LIC']:
        return 'LMIC'
    else:
        return 'Unknown'


def load_dataset_file(dataset_name):
    """Load a single dataset's JSON file with gender data."""
    # Map dataset name to filename
    filename = dataset_name.lower() + '_with_gender.json'
    filepath = AUTHORS_DIR / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Could not find {filepath}")
    
    with open(filepath) as f:
        return json.load(f)


def combine_mimic_datasets():
    """Combine all MIMIC datasets into one."""
    combined_papers = []
    
    for mimic_name in MIMIC_COMPONENTS:
        try:
            data = load_dataset_file(mimic_name)
            papers = data.get('papers', [])
            # Add source tag to each paper
            for paper in papers:
                paper['_source'] = mimic_name
            combined_papers.extend(papers)
        except FileNotFoundError:
            print(f"Warning: Could not load {mimic_name}")
    
    return {
        'dataset': 'MIMIC',
        'papers': combined_papers,
        'total_papers': len(combined_papers),
    }


def load_all_datasets():
    """Load all datasets, combining MIMIC versions."""
    datasets = {}
    
    # Load combined MIMIC
    print("  Combining MIMIC-I, II, III, IV...")
    datasets['MIMIC'] = combine_mimic_datasets()
    print(f"    Combined: {datasets['MIMIC']['total_papers']} papers")
    
    # Load other datasets
    for name in ['UK-Biobank', 'OpenSAFELY', 'All-of-Us']:
        try:
            datasets[name] = load_dataset_file(name)
            print(f"  Loaded {name}: {len(datasets[name].get('papers', []))} papers")
        except FileNotFoundError:
            print(f"  Warning: Could not load {name}")
    
    return datasets


# =============================================================================
# FIGURE 1: Cumulative Citations Over Time
# =============================================================================

def figure1_cumulative_citations(datasets):
    """
    Create Figure 1: Cumulative citations over calendar time.
    Shows citation growth trajectories starting from each dataset's launch year.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for dataset_name, config in DATASETS.items():
        if dataset_name not in datasets:
            continue
        
        data = datasets[dataset_name]
        papers = data.get('papers', [])
        
        # Count papers by year
        year_counts = defaultdict(int)
        for paper in papers:
            year = paper.get('year')
            if year:
                year_counts[year] += 1
        
        if not year_counts:
            continue
        
        # Start from launch year (or first citation year if later)
        launch_year = config['launch_year']
        first_citation_year = min(year_counts.keys())
        start_year = max(launch_year, first_citation_year)
        
        # Calculate cumulative citations starting from launch
        year_range = []
        cumulative = []
        total = 0
        
        # Include up to 2025
        for year in range(start_year, 2026):
            total += year_counts.get(year, 0)
            year_range.append(year)
            cumulative.append(total)
        
        if not cumulative:
            continue
        
        # Plot with marker for every year
        ax.plot(year_range, cumulative, 
                color=config['color'],
                marker=config['marker'],
                markersize=5,
                linewidth=2,
                label=f"{dataset_name} ({config['launch_year']})",
                alpha=0.9)
    
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('Cumulative Citing Papers', fontsize=12)
    ax.set_title('Figure 1: Citation Growth Over Time', fontsize=14)
    ax.legend(loc='upper left', fontsize=10)
    ax.set_xlim(1996, 2026)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'figure1_cumulative_citations.png', dpi=300, bbox_inches='tight')
    plt.savefig(FIGURES_DIR / 'figure1_cumulative_citations.pdf', bbox_inches='tight')
    print(f"Saved: {FIGURES_DIR / 'figure1_cumulative_citations.png'}")
    plt.close()


# =============================================================================
# FIGURE 2: Citation Impact Distribution (Two Panels)
# =============================================================================

def figure2_impact_distribution(datasets):
    """
    Create Figure 2: Two-panel impact distribution.
    (A) Citations per paper vs. paper rank (h-index style)
    (B) Same, normalized by funding per $1M
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    for dataset_name, config in DATASETS.items():
        if dataset_name not in datasets:
            continue
        
        data = datasets[dataset_name]
        papers = data.get('papers', [])
        
        # Get citation counts for each paper
        citations = [p.get('cited_by_count', 0) for p in papers]
        if not citations:
            continue
        
        # Sort descending
        citations_sorted = sorted(citations, reverse=True)
        
        # Panel A: Raw distribution
        x_vals = list(range(1, len(citations_sorted) + 1))
        axes[0].plot(x_vals, citations_sorted,
                    color=config['color'],
                    linewidth=2,
                    label=dataset_name,
                    alpha=0.8)
        
        # Panel B: Funding-normalized (per $1M)
        funding = config['funding_m']
        normalized = [c / funding for c in citations_sorted]
        axes[1].plot(x_vals, normalized,
                    color=config['color'],
                    linewidth=2,
                    label=dataset_name,
                    alpha=0.8)
    
    # Panel A styling
    axes[0].set_xlabel('Paper Rank (by citations)', fontsize=11)
    axes[0].set_ylabel('Citations', fontsize=11)
    axes[0].set_title('(A) Citation Distribution', fontsize=12)
    axes[0].set_xscale('log')
    axes[0].set_yscale('log')
    axes[0].legend(loc='upper right', fontsize=10)
    axes[0].grid(True, alpha=0.3)
    
    # Panel B styling
    axes[1].set_xlabel('Paper Rank (by citations)', fontsize=11)
    axes[1].set_ylabel('Citations per $1M Funding', fontsize=11)
    axes[1].set_title('(B) Funding-Normalized Distribution', fontsize=12)
    axes[1].set_xscale('log')
    axes[1].set_yscale('log')
    axes[1].legend(loc='upper right', fontsize=10)
    axes[1].grid(True, alpha=0.3)
    
    fig.suptitle('Figure 2: Citation Impact Distribution', fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'figure2_impact_distribution.png', dpi=300, bbox_inches='tight')
    plt.savefig(FIGURES_DIR / 'figure2_impact_distribution.pdf', bbox_inches='tight')
    print(f"Saved: {FIGURES_DIR / 'figure2_impact_distribution.png'}")
    plt.close()


# =============================================================================
# TABLE 2: Author Demographics
# =============================================================================

def table2_demographics(datasets):
    """
    Create Table 2: Author demographics analysis.
    - Gender distribution
    - Country distribution  
    - HIC vs LMIC breakdown
    - International collaboration metrics
    """
    income_data = load_income_classification()
    
    results = []
    
    for dataset_name, config in DATASETS.items():
        if dataset_name not in datasets:
            continue
        
        data = datasets[dataset_name]
        papers = data.get('papers', [])
        
        # Collect statistics
        total_papers = len(papers)
        total_authors = 0
        
        gender_counts = {'male': 0, 'female': 0, 'unknown': 0}
        country_counts = defaultdict(int)
        income_counts = {'HIC': 0, 'LMIC': 0, 'Unknown': 0}
        
        # Track international collaboration
        papers_with_hic_lmic_collab = 0
        papers_with_multi_country = 0
        unique_countries_per_paper = []
        
        for paper in papers:
            authors = paper.get('authors', [])
            total_authors += len(authors)
            
            paper_countries = set()
            paper_income_levels = set()
            
            for author in authors:
                # Gender
                gender = author.get('gender')
                if gender == 'male':
                    gender_counts['male'] += 1
                elif gender == 'female':
                    gender_counts['female'] += 1
                else:
                    gender_counts['unknown'] += 1
                
                # Countries from author's direct countries field
                author_countries = author.get('countries', [])
                for country in author_countries:
                    country_counts[country] += 1
                    paper_countries.add(country)
                    
                    income_level = classify_income(country, income_data)
                    income_counts[income_level] += 1
                    paper_income_levels.add(income_level)
                
                # Also check institutions
                for inst in author.get('institutions', []):
                    country = inst.get('country')
                    if country and country not in author_countries:
                        country_counts[country] += 1
                        paper_countries.add(country)
                        
                        income_level = classify_income(country, income_data)
                        income_counts[income_level] += 1
                        paper_income_levels.add(income_level)
            
            # Track collaboration
            unique_countries_per_paper.append(len(paper_countries))
            if len(paper_countries) > 1:
                papers_with_multi_country += 1
            if 'HIC' in paper_income_levels and 'LMIC' in paper_income_levels:
                papers_with_hic_lmic_collab += 1
        
        # Calculate metrics
        total_gendered = gender_counts['male'] + gender_counts['female']
        female_pct = (gender_counts['female'] / total_gendered * 100) if total_gendered > 0 else 0
        
        total_with_income = income_counts['HIC'] + income_counts['LMIC']
        lmic_pct = (income_counts['LMIC'] / total_with_income * 100) if total_with_income > 0 else 0
        
        multi_country_pct = (papers_with_multi_country / total_papers * 100) if total_papers > 0 else 0
        hic_lmic_collab_pct = (papers_with_hic_lmic_collab / total_papers * 100) if total_papers > 0 else 0
        
        avg_countries = np.mean(unique_countries_per_paper) if unique_countries_per_paper else 0
        
        results.append({
            'Dataset': dataset_name,
            'Total Papers': total_papers,
            'Total Authors': total_authors,
            'Male': gender_counts['male'],
            'Female': gender_counts['female'],
            'Unknown Gender': gender_counts['unknown'],
            'Gender Identified %': round(total_gendered / total_authors * 100, 1) if total_authors > 0 else 0,
            'Female % (of identified)': round(female_pct, 1),
            'Unique Countries': len(country_counts),
            'HIC Authors': income_counts['HIC'],
            'LMIC Authors': income_counts['LMIC'],
            'LMIC % (of classified)': round(lmic_pct, 1),
            'Multi-Country Papers %': round(multi_country_pct, 1),
            'HIC-LMIC Collab %': round(hic_lmic_collab_pct, 1),
            'Avg Countries/Paper': round(avg_countries, 2),
        })
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Save detailed CSV
    df.to_csv(OUTPUT_DIR / 'table2_demographics_detailed.csv', index=False)
    print(f"Saved: {OUTPUT_DIR / 'table2_demographics_detailed.csv'}")
    
    # Create publication-ready markdown table
    md_lines = [
        "# Table 2: Author Demographics",
        "",
        "## Summary",
        "",
        "| Dataset | Papers | Authors | Female %* | Countries | LMIC %** | HIC-LMIC Collab % |",
        "|---------|-------:|--------:|----------:|----------:|---------:|------------------:|",
    ]
    for _, row in df.iterrows():
        md_lines.append(
            f"| {row['Dataset']} | {row['Total Papers']:,} | {row['Total Authors']:,} | "
            f"{row['Female % (of identified)']:.1f}% | {row['Unique Countries']} | "
            f"{row['LMIC % (of classified)']:.1f}% | {row['HIC-LMIC Collab %']:.1f}% |"
        )
    
    md_lines.extend([
        "",
        "*Female % calculated from authors with identified gender (excluding unknown)",
        "**LMIC % calculated from authors with identified country income classification",
        "",
        "## Detailed Breakdown",
        "",
        "### Gender Distribution",
        "",
        "| Dataset | Male | Female | Unknown | Identification Rate |",
        "|---------|-----:|-------:|--------:|--------------------:|",
    ])
    for _, row in df.iterrows():
        md_lines.append(
            f"| {row['Dataset']} | {row['Male']:,} | {row['Female']:,} | "
            f"{row['Unknown Gender']:,} | {row['Gender Identified %']:.1f}% |"
        )
    
    md_lines.extend([
        "",
        "### Geographic Distribution",
        "",
        "| Dataset | HIC Authors | LMIC Authors | Unique Countries | Avg Countries/Paper |",
        "|---------|------------:|-------------:|-----------------:|--------------------:|",
    ])
    for _, row in df.iterrows():
        md_lines.append(
            f"| {row['Dataset']} | {row['HIC Authors']:,} | {row['LMIC Authors']:,} | "
            f"{row['Unique Countries']} | {row['Avg Countries/Paper']:.2f} |"
        )
    
    md_content = "\n".join(md_lines)
    
    # Save markdown
    with open(OUTPUT_DIR / 'table2_demographics.md', 'w') as f:
        f.write(md_content)
    print(f"Saved: {OUTPUT_DIR / 'table2_demographics.md'}")
    
    # Also save summary CSV
    summary_cols = ['Dataset', 'Total Papers', 'Total Authors', 'Female % (of identified)', 
                   'Unique Countries', 'LMIC % (of classified)', 'HIC-LMIC Collab %']
    df_summary = df[summary_cols].copy()
    df_summary.to_csv(OUTPUT_DIR / 'table2_demographics_summary.csv', index=False)
    print(f"Saved: {OUTPUT_DIR / 'table2_demographics_summary.csv'}")
    
    # Print summary
    print("\n" + "="*80)
    print("TABLE 2: Author Demographics Summary")
    print("="*80)
    print(md_content)
    
    return df


# =============================================================================
# TABLE 3: Author Position Analysis
# =============================================================================

def table3_author_positions(datasets):
    """
    Analyze gender and country by author position (first, middle, last).
    """
    income_data = load_income_classification()
    
    results = []
    position_details = []
    
    for dataset_name, config in DATASETS.items():
        if dataset_name not in datasets:
            continue
        
        data = datasets[dataset_name]
        papers = data.get('papers', [])
        
        # Track by position
        position_stats = {
            'first': {'male': 0, 'female': 0, 'unknown': 0, 'HIC': 0, 'LMIC': 0, 'Unknown_income': 0},
            'middle': {'male': 0, 'female': 0, 'unknown': 0, 'HIC': 0, 'LMIC': 0, 'Unknown_income': 0},
            'last': {'male': 0, 'female': 0, 'unknown': 0, 'HIC': 0, 'LMIC': 0, 'Unknown_income': 0},
        }
        
        for paper in papers:
            authors = paper.get('authors', [])
            
            for author in authors:
                pos_type = author.get('position_type', 'middle')
                if pos_type not in position_stats:
                    pos_type = 'middle'
                
                # Gender
                gender = author.get('gender')
                if gender == 'male':
                    position_stats[pos_type]['male'] += 1
                elif gender == 'female':
                    position_stats[pos_type]['female'] += 1
                else:
                    position_stats[pos_type]['unknown'] += 1
                
                # Country income
                countries = author.get('countries', [])
                if countries:
                    # Use first country
                    income = classify_income(countries[0], income_data)
                    if income == 'HIC':
                        position_stats[pos_type]['HIC'] += 1
                    elif income == 'LMIC':
                        position_stats[pos_type]['LMIC'] += 1
                    else:
                        position_stats[pos_type]['Unknown_income'] += 1
                else:
                    position_stats[pos_type]['Unknown_income'] += 1
        
        # Calculate percentages for each position
        for pos in ['first', 'middle', 'last']:
            stats = position_stats[pos]
            total_gender = stats['male'] + stats['female']
            total_income = stats['HIC'] + stats['LMIC']
            
            female_pct = (stats['female'] / total_gender * 100) if total_gender > 0 else 0
            lmic_pct = (stats['LMIC'] / total_income * 100) if total_income > 0 else 0
            
            position_details.append({
                'Dataset': dataset_name,
                'Position': pos.capitalize(),
                'Total': stats['male'] + stats['female'] + stats['unknown'],
                'Male': stats['male'],
                'Female': stats['female'],
                'Female %': round(female_pct, 1),
                'HIC': stats['HIC'],
                'LMIC': stats['LMIC'],
                'LMIC %': round(lmic_pct, 1),
            })
        
        # Summary row for this dataset
        first = position_stats['first']
        last = position_stats['last']
        
        first_total_g = first['male'] + first['female']
        last_total_g = last['male'] + last['female']
        first_total_i = first['HIC'] + first['LMIC']
        last_total_i = last['HIC'] + last['LMIC']
        
        results.append({
            'Dataset': dataset_name,
            'First Author Female %': round((first['female'] / first_total_g * 100) if first_total_g > 0 else 0, 1),
            'Last Author Female %': round((last['female'] / last_total_g * 100) if last_total_g > 0 else 0, 1),
            'First Author LMIC %': round((first['LMIC'] / first_total_i * 100) if first_total_i > 0 else 0, 1),
            'Last Author LMIC %': round((last['LMIC'] / last_total_i * 100) if last_total_i > 0 else 0, 1),
        })
    
    # Create DataFrames
    df_summary = pd.DataFrame(results)
    df_detail = pd.DataFrame(position_details)
    
    # Save CSVs
    df_detail.to_csv(OUTPUT_DIR / 'table3_positions_detailed.csv', index=False)
    print(f"Saved: {OUTPUT_DIR / 'table3_positions_detailed.csv'}")
    
    df_summary.to_csv(OUTPUT_DIR / 'table3_positions_summary.csv', index=False)
    print(f"Saved: {OUTPUT_DIR / 'table3_positions_summary.csv'}")
    
    # Create markdown report
    md_lines = [
        "# Table 3: Author Position Analysis",
        "",
        "## Summary: First vs Last Author",
        "",
        "| Dataset | First Author Female % | Last Author Female % | First Author LMIC % | Last Author LMIC % |",
        "|---------|----------------------:|---------------------:|--------------------:|-------------------:|",
    ]
    for _, row in df_summary.iterrows():
        md_lines.append(
            f"| {row['Dataset']} | {row['First Author Female %']:.1f}% | {row['Last Author Female %']:.1f}% | "
            f"{row['First Author LMIC %']:.1f}% | {row['Last Author LMIC %']:.1f}% |"
        )
    
    md_lines.extend([
        "",
        "## Detailed Breakdown by Position",
        "",
        "### Gender by Position",
        "",
        "| Dataset | Position | Male | Female | Female % |",
        "|---------|----------|-----:|-------:|---------:|",
    ])
    for _, row in df_detail.iterrows():
        md_lines.append(
            f"| {row['Dataset']} | {row['Position']} | {row['Male']:,} | {row['Female']:,} | {row['Female %']:.1f}% |"
        )
    
    md_lines.extend([
        "",
        "### Income Classification by Position",
        "",
        "| Dataset | Position | HIC | LMIC | LMIC % |",
        "|---------|----------|----:|-----:|-------:|",
    ])
    for _, row in df_detail.iterrows():
        md_lines.append(
            f"| {row['Dataset']} | {row['Position']} | {row['HIC']:,} | {row['LMIC']:,} | {row['LMIC %']:.1f}% |"
        )
    
    md_content = "\n".join(md_lines)
    
    # Save markdown
    with open(OUTPUT_DIR / 'table3_positions.md', 'w') as f:
        f.write(md_content)
    print(f"Saved: {OUTPUT_DIR / 'table3_positions.md'}")
    
    # Print
    print("\n" + "="*80)
    print("TABLE 3: Author Position Analysis")
    print("="*80)
    print(md_content)
    
    return df_summary, df_detail


# =============================================================================
# TABLE S4: Gender x Income x Position (Intersectional)
# =============================================================================

def table_s4_intersectional(datasets):
    """
    Supplementary Table S4: Authorship position by both gender and income.
    Cross-tabulates HIC/LMIC x Male/Female by first/middle/last position.
    """
    income_data = load_income_classification()
    
    rows = []
    
    for dataset_name, config in DATASETS.items():
        if dataset_name not in datasets:
            continue
        
        data = datasets[dataset_name]
        papers = data.get('papers', [])
        
        # Track: position -> (income, gender) -> count
        counts = {}
        for pos in ['first', 'middle', 'last']:
            counts[pos] = {
                'HIC_male': 0, 'HIC_female': 0, 'HIC_unknown': 0,
                'LMIC_male': 0, 'LMIC_female': 0, 'LMIC_unknown': 0,
                'Unknown_male': 0, 'Unknown_female': 0, 'Unknown_unknown': 0,
            }
        
        for paper in papers:
            for author in paper.get('authors', []):
                pos_type = author.get('position_type', 'middle')
                if pos_type not in counts:
                    pos_type = 'middle'
                
                # Gender
                gender = author.get('gender')
                if gender == 'male':
                    g = 'male'
                elif gender == 'female':
                    g = 'female'
                else:
                    g = 'unknown'
                
                # Income
                author_countries = author.get('countries', [])
                if author_countries:
                    income = classify_income(author_countries[0], income_data)
                    if income == 'HIC':
                        inc = 'HIC'
                    elif income == 'LMIC':
                        inc = 'LMIC'
                    else:
                        inc = 'Unknown'
                else:
                    inc = 'Unknown'
                
                key = f"{inc}_{g}"
                counts[pos_type][key] += 1
        
        # Build rows for each position
        for pos in ['first', 'middle', 'last']:
            c = counts[pos]
            
            hic_male = c['HIC_male']
            hic_female = c['HIC_female']
            lmic_male = c['LMIC_male']
            lmic_female = c['LMIC_female']
            
            hic_total = hic_male + hic_female
            lmic_total = lmic_male + lmic_female
            total_identified = hic_total + lmic_total
            
            rows.append({
                'Dataset': dataset_name,
                'Position': pos.capitalize(),
                'HIC Male': hic_male,
                'HIC Female': hic_female,
                'HIC Female %': round((hic_female / hic_total * 100) if hic_total > 0 else 0, 1),
                'LMIC Male': lmic_male,
                'LMIC Female': lmic_female,
                'LMIC Female %': round((lmic_female / lmic_total * 100) if lmic_total > 0 else 0, 1),
                'Total Identified': total_identified,
                'LMIC Female % of All': round((lmic_female / total_identified * 100) if total_identified > 0 else 0, 1),
                'HIC Male % of All': round((hic_male / total_identified * 100) if total_identified > 0 else 0, 1),
            })
    
    df = pd.DataFrame(rows)
    
    # Save CSV
    df.to_csv(OUTPUT_DIR / 'table_s4_intersectional.csv', index=False)
    print(f"Saved: {OUTPUT_DIR / 'table_s4_intersectional.csv'}")
    
    # Create markdown
    md_lines = [
        "# Supplementary Table S4. Intersectional Analysis: Authorship Position by Gender and Income Classification",
        "",
        "## Counts by Position",
        "",
        "| Dataset | Position | HIC Male | HIC Female | HIC Female % | LMIC Male | LMIC Female | LMIC Female % |",
        "|---------|----------|:--------:|:----------:|:------------:|:---------:|:-----------:|:-------------:|",
    ]
    
    for _, row in df.iterrows():
        ds = f"**{row['Dataset']}**" if row['Position'] == 'First' else ''
        md_lines.append(
            f"| {ds} | {row['Position']} | "
            f"{row['HIC Male']:,} | {row['HIC Female']:,} | {row['HIC Female %']:.1f}% | "
            f"{row['LMIC Male']:,} | {row['LMIC Female']:,} | {row['LMIC Female %']:.1f}% |"
        )
    
    md_lines.extend([
        "",
        "## Proportion of All Identified Authors by Position",
        "",
        "| Dataset | Position | HIC Male % | HIC Female % | LMIC Male % | LMIC Female % |",
        "|---------|----------|:----------:|:------------:|:-----------:|:-------------:|",
    ])
    
    for _, row in df.iterrows():
        ds = f"**{row['Dataset']}**" if row['Position'] == 'First' else ''
        total = row['Total Identified']
        if total > 0:
            hm_pct = row['HIC Male'] / total * 100
            hf_pct = row['HIC Female'] / total * 100
            lm_pct = row['LMIC Male'] / total * 100
            lf_pct = row['LMIC Female'] / total * 100
        else:
            hm_pct = hf_pct = lm_pct = lf_pct = 0
        
        md_lines.append(
            f"| {ds} | {row['Position']} | "
            f"{hm_pct:.1f}% | {hf_pct:.1f}% | {lm_pct:.1f}% | {lf_pct:.1f}% |"
        )
    
    md_content = "\n".join(md_lines)
    
    # Save markdown
    with open(OUTPUT_DIR / 'table_s4_intersectional.md', 'w') as f:
        f.write(md_content)
    print(f"Saved: {OUTPUT_DIR / 'table_s4_intersectional.md'}")
    
    # Print
    print("\n" + "="*80)
    print("TABLE S4: Intersectional Analysis")
    print("="*80)
    print(md_content)
    
    return df


# =============================================================================
# TABLE S5: Unique Authors by Gender and Income
# =============================================================================

def table_s5_unique_authors(datasets):
    """
    Supplementary Table S5: Unique author counts by gender and income.
    Deduplicates authors by OpenAlex ID within each dataset.
    """
    income_data = load_income_classification()
    
    rows = []
    
    for dataset_name, config in DATASETS.items():
        if dataset_name not in datasets:
            continue
        
        data = datasets[dataset_name]
        papers = data.get('papers', [])
        
        # Track unique authors by ID
        seen = {}  # author_id -> {gender, income, positions}
        
        for paper in papers:
            for author in paper.get('authors', []):
                author_id = author.get('id', '')
                if not author_id:
                    continue
                
                if author_id not in seen:
                    # Gender
                    gender = author.get('gender')
                    if gender not in ('male', 'female'):
                        gender = 'unknown'
                    
                    # Income (from first country)
                    countries = author.get('countries', [])
                    if countries:
                        income = classify_income(countries[0], income_data)
                        if income not in ('HIC', 'LMIC'):
                            income = 'Unknown'
                    else:
                        income = 'Unknown'
                    
                    seen[author_id] = {
                        'gender': gender,
                        'income': income,
                        'positions': set(),
                    }
                
                pos_type = author.get('position_type', 'middle')
                seen[author_id]['positions'].add(pos_type)
        
        # Count unique authors
        total_unique = len(seen)
        
        # Gender counts
        male = sum(1 for a in seen.values() if a['gender'] == 'male')
        female = sum(1 for a in seen.values() if a['gender'] == 'female')
        unknown_gender = sum(1 for a in seen.values() if a['gender'] == 'unknown')
        gendered = male + female
        
        # Income counts
        hic = sum(1 for a in seen.values() if a['income'] == 'HIC')
        lmic = sum(1 for a in seen.values() if a['income'] == 'LMIC')
        unknown_income = sum(1 for a in seen.values() if a['income'] == 'Unknown')
        classified = hic + lmic
        
        # Cross-tabulation
        hic_male = sum(1 for a in seen.values() if a['income'] == 'HIC' and a['gender'] == 'male')
        hic_female = sum(1 for a in seen.values() if a['income'] == 'HIC' and a['gender'] == 'female')
        lmic_male = sum(1 for a in seen.values() if a['income'] == 'LMIC' and a['gender'] == 'male')
        lmic_female = sum(1 for a in seen.values() if a['income'] == 'LMIC' and a['gender'] == 'female')
        
        # Authors who ever held first/last position
        ever_first = sum(1 for a in seen.values() if 'first' in a['positions'])
        ever_last = sum(1 for a in seen.values() if 'last' in a['positions'])
        first_female = sum(1 for a in seen.values() if 'first' in a['positions'] and a['gender'] == 'female')
        last_female = sum(1 for a in seen.values() if 'last' in a['positions'] and a['gender'] == 'female')
        first_lmic = sum(1 for a in seen.values() if 'first' in a['positions'] and a['income'] == 'LMIC')
        last_lmic = sum(1 for a in seen.values() if 'last' in a['positions'] and a['income'] == 'LMIC')
        
        rows.append({
            'Dataset': dataset_name,
            'Unique Authors': total_unique,
            'Male': male,
            'Female': female,
            'Unknown Gender': unknown_gender,
            'Female % (of identified)': round((female / gendered * 100) if gendered > 0 else 0, 1),
            'HIC': hic,
            'LMIC': lmic,
            'Unknown Income': unknown_income,
            'LMIC % (of classified)': round((lmic / classified * 100) if classified > 0 else 0, 1),
            'HIC Male': hic_male,
            'HIC Female': hic_female,
            'LMIC Male': lmic_male,
            'LMIC Female': lmic_female,
            'Ever First Author': ever_first,
            'Ever Last Author': ever_last,
            'First Author Female %': round((first_female / ever_first * 100) if ever_first > 0 else 0, 1),
            'Last Author Female %': round((last_female / ever_last * 100) if ever_last > 0 else 0, 1),
            'First Author LMIC %': round((first_lmic / ever_first * 100) if ever_first > 0 else 0, 1),
            'Last Author LMIC %': round((last_lmic / ever_last * 100) if ever_last > 0 else 0, 1),
        })
    
    df = pd.DataFrame(rows)
    
    # Save CSV
    df.to_csv(OUTPUT_DIR / 'table_s5_unique_authors.csv', index=False)
    print(f"Saved: {OUTPUT_DIR / 'table_s5_unique_authors.csv'}")
    
    # Create markdown
    md_lines = [
        "# Supplementary Table S5. Unique Author Analysis by Gender and Income Classification",
        "",
        "Authors deduplicated by OpenAlex author ID within each dataset.",
        "",
        "## Overall Unique Author Demographics",
        "",
        "| Dataset | Unique Authors | Male | Female | Female %* | HIC | LMIC | LMIC %** |",
        "|---------|:--------------:|:----:|:------:|:---------:|:---:|:----:|:--------:|",
    ]
    
    for _, row in df.iterrows():
        md_lines.append(
            f"| {row['Dataset']} | {row['Unique Authors']:,} | {row['Male']:,} | {row['Female']:,} | "
            f"{row['Female % (of identified)']:.1f}% | {row['HIC']:,} | {row['LMIC']:,} | "
            f"{row['LMIC % (of classified)']:.1f}% |"
        )
    
    md_lines.extend([
        "",
        "*Of authors with identified gender",
        "**Of authors with classified country income",
        "",
        "## Unique Authors: Gender x Income Cross-Tabulation",
        "",
        "| Dataset | HIC Male | HIC Female | LMIC Male | LMIC Female |",
        "|---------|:--------:|:----------:|:---------:|:-----------:|",
    ])
    
    for _, row in df.iterrows():
        md_lines.append(
            f"| {row['Dataset']} | {row['HIC Male']:,} | {row['HIC Female']:,} | "
            f"{row['LMIC Male']:,} | {row['LMIC Female']:,} |"
        )
    
    md_lines.extend([
        "",
        "## Unique Authors Who Held First or Last Author Position",
        "",
        "| Dataset | Ever First Author | First Author Female % | First Author LMIC % | Ever Last Author | Last Author Female % | Last Author LMIC % |",
        "|---------|:-----------------:|:---------------------:|:-------------------:|:----------------:|:--------------------:|:------------------:|",
    ])
    
    for _, row in df.iterrows():
        md_lines.append(
            f"| {row['Dataset']} | {row['Ever First Author']:,} | {row['First Author Female %']:.1f}% | "
            f"{row['First Author LMIC %']:.1f}% | {row['Ever Last Author']:,} | "
            f"{row['Last Author Female %']:.1f}% | {row['Last Author LMIC %']:.1f}% |"
        )
    
    md_content = "\n".join(md_lines)
    
    with open(OUTPUT_DIR / 'table_s5_unique_authors.md', 'w') as f:
        f.write(md_content)
    print(f"Saved: {OUTPUT_DIR / 'table_s5_unique_authors.md'}")
    
    print("\n" + "="*80)
    print("TABLE S5: Unique Author Analysis")
    print("="*80)
    print(md_content)
    
    return df


# =============================================================================
# STATISTICAL ANALYSIS
# =============================================================================

def statistical_analysis(datasets):
    """
    Perform statistical tests for publication:
    1. Chi-square tests with Cramér's V for effect size
    2. Odds ratios for 2x2 pairwise comparisons
    3. Bonferroni-corrected p-values for pairwise tests
    """
    income_data = load_income_classification()
    
    def cramers_v(contingency_table):
        """Calculate Cramér's V from a contingency table (list of lists)."""
        ct = np.array(contingency_table)
        chi2, p, dof, _ = stats.chi2_contingency(ct)
        n = ct.sum()
        r, k = ct.shape
        v = np.sqrt(chi2 / (n * (min(r, k) - 1))) if n > 0 and min(r, k) > 1 else 0
        return chi2, p, dof, round(v, 4)
    
    def odds_ratio_2x2(table):
        """
        Calculate odds ratio and 95% CI for a 2x2 table.
        table = [[a, b], [c, d]]
        OR = (a*d) / (b*c)
        """
        a, b = table[0]
        c, d = table[1]
        # Add 0.5 continuity correction if any cell is 0
        if a == 0 or b == 0 or c == 0 or d == 0:
            a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        or_val = (a * d) / (b * c)
        log_or = np.log(or_val)
        se = np.sqrt(1/a + 1/b + 1/c + 1/d)
        ci_lower = np.exp(log_or - 1.96 * se)
        ci_upper = np.exp(log_or + 1.96 * se)
        return round(or_val, 3), round(ci_lower, 3), round(ci_upper, 3)
    
    def format_p(p, bonferroni_n=1):
        """Format p-value, applying Bonferroni correction if n > 1."""
        p_adj = min(p * bonferroni_n, 1.0)
        if p_adj < 0.001:
            return f"{p_adj:.2e}"
        else:
            return f"{p_adj:.4f}"
    
    # Collect raw counts for each dataset
    dataset_counts = {}
    
    for dataset_name, config in DATASETS.items():
        if dataset_name not in datasets:
            continue
        
        data = datasets[dataset_name]
        papers = data.get('papers', [])
        
        counts = {
            'male': 0, 'female': 0,
            'HIC': 0, 'LMIC': 0,
            'first_male': 0, 'first_female': 0,
            'last_male': 0, 'last_female': 0,
            'first_HIC': 0, 'first_LMIC': 0,
            'last_HIC': 0, 'last_LMIC': 0,
        }
        
        for paper in papers:
            for author in paper.get('authors', []):
                pos_type = author.get('position_type', 'middle')
                
                gender = author.get('gender')
                if gender == 'male':
                    counts['male'] += 1
                    if pos_type == 'first':
                        counts['first_male'] += 1
                    elif pos_type == 'last':
                        counts['last_male'] += 1
                elif gender == 'female':
                    counts['female'] += 1
                    if pos_type == 'first':
                        counts['first_female'] += 1
                    elif pos_type == 'last':
                        counts['last_female'] += 1
                
                countries = author.get('countries', [])
                if countries:
                    income_cat = classify_income(countries[0], income_data)
                    if income_cat == 'HIC':
                        counts['HIC'] += 1
                        if pos_type == 'first':
                            counts['first_HIC'] += 1
                        elif pos_type == 'last':
                            counts['last_HIC'] += 1
                    elif income_cat == 'LMIC':
                        counts['LMIC'] += 1
                        if pos_type == 'first':
                            counts['first_LMIC'] += 1
                        elif pos_type == 'last':
                            counts['last_LMIC'] += 1
        
        dataset_counts[dataset_name] = counts
    
    dataset_names = list(dataset_counts.keys())
    n_pairwise = len(dataset_names) - 1  # Bonferroni correction factor for MIMIC vs others
    
    results = []
    
    # =========================================================================
    # 1. Overall chi-square tests with Cramér's V
    # =========================================================================
    contingency_lmic = [[dataset_counts[n]['HIC'], dataset_counts[n]['LMIC']] for n in dataset_names]
    chi2, p, dof, v = cramers_v(contingency_lmic)
    results.append({
        'Test': 'Overall LMIC distribution',
        'Comparison': 'All datasets',
        'Chi-square': round(chi2, 2),
        'df': dof,
        'p-value': format_p(p),
        'Cramers_V': v,
        'OR (95% CI)': '—',
        'Significant': 'Yes' if p < 0.05 else 'No',
    })
    
    contingency_gender = [[dataset_counts[n]['male'], dataset_counts[n]['female']] for n in dataset_names]
    chi2, p, dof, v = cramers_v(contingency_gender)
    results.append({
        'Test': 'Overall gender distribution',
        'Comparison': 'All datasets',
        'Chi-square': round(chi2, 2),
        'df': dof,
        'p-value': format_p(p),
        'Cramers_V': v,
        'OR (95% CI)': '—',
        'Significant': 'Yes' if p < 0.05 else 'No',
    })
    
    # =========================================================================
    # 2. Pairwise: MIMIC vs each other (Bonferroni-corrected, with OR)
    # =========================================================================
    mc = dataset_counts.get('MIMIC', {})
    
    for other_name in dataset_names:
        if other_name == 'MIMIC':
            continue
        oc = dataset_counts[other_name]
        
        # LMIC: OR = odds of LMIC authorship in MIMIC vs other
        table_lmic = [
            [mc['LMIC'], mc['HIC']],
            [oc['LMIC'], oc['HIC']],
        ]
        chi2, p, dof, v = cramers_v(table_lmic)
        or_val, ci_lo, ci_hi = odds_ratio_2x2(table_lmic)
        results.append({
            'Test': 'LMIC representation',
            'Comparison': f'MIMIC vs {other_name}',
            'Chi-square': round(chi2, 2),
            'df': dof,
            'p-value': format_p(p, n_pairwise),
            'Cramers_V': v,
            'OR (95% CI)': f"{or_val} ({ci_lo}–{ci_hi})",
            'Significant': 'Yes' if p * n_pairwise < 0.05 else 'No',
        })
        
        # Gender: OR = odds of female authorship in MIMIC vs other
        table_gender = [
            [mc['female'], mc['male']],
            [oc['female'], oc['male']],
        ]
        chi2, p, dof, v = cramers_v(table_gender)
        or_val, ci_lo, ci_hi = odds_ratio_2x2(table_gender)
        results.append({
            'Test': 'Gender distribution',
            'Comparison': f'MIMIC vs {other_name}',
            'Chi-square': round(chi2, 2),
            'df': dof,
            'p-value': format_p(p, n_pairwise),
            'Cramers_V': v,
            'OR (95% CI)': f"{or_val} ({ci_lo}–{ci_hi})",
            'Significant': 'Yes' if p * n_pairwise < 0.05 else 'No',
        })
    
    # =========================================================================
    # 3. Position effects: First vs Last within each dataset
    # =========================================================================
    for name in dataset_names:
        c = dataset_counts[name]
        
        # Gender
        table_g = [
            [c['first_female'], c['first_male']],
            [c['last_female'], c['last_male']],
        ]
        chi2, p, dof, v = cramers_v(table_g)
        or_val, ci_lo, ci_hi = odds_ratio_2x2(table_g)
        results.append({
            'Test': 'First vs Last author (gender)',
            'Comparison': name,
            'Chi-square': round(chi2, 2),
            'df': dof,
            'p-value': format_p(p),
            'Cramers_V': v,
            'OR (95% CI)': f"{or_val} ({ci_lo}–{ci_hi})",
            'Significant': 'Yes' if p < 0.05 else 'No',
        })
        
        # LMIC
        table_i = [
            [c['first_LMIC'], c['first_HIC']],
            [c['last_LMIC'], c['last_HIC']],
        ]
        chi2, p, dof, v = cramers_v(table_i)
        or_val, ci_lo, ci_hi = odds_ratio_2x2(table_i)
        results.append({
            'Test': 'First vs Last author (LMIC)',
            'Comparison': name,
            'Chi-square': round(chi2, 2),
            'df': dof,
            'p-value': format_p(p),
            'Cramers_V': v,
            'OR (95% CI)': f"{or_val} ({ci_lo}–{ci_hi})",
            'Significant': 'Yes' if p < 0.05 else 'No',
        })
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Save CSV
    df.to_csv(OUTPUT_DIR / 'statistical_tests.csv', index=False)
    print(f"Saved: {OUTPUT_DIR / 'statistical_tests.csv'}")
    
    # Create markdown report
    md_lines = [
        "# Statistical Analysis",
        "",
        "All tests are Pearson's chi-square tests with Cramér's V for effect size.",
        "Odds ratios (OR) with 95% confidence intervals are reported for 2×2 comparisons.",
        "Pairwise comparisons use Bonferroni correction (n=3).",
        "Significance level: α = 0.05.",
        "",
        "## Overall Tests (All Datasets)",
        "",
        "| Test | χ² | df | p-value | Cramér's V |",
        "|------|---:|---:|--------:|-----------:|",
    ]
    
    for _, row in df[df['Comparison'] == 'All datasets'].iterrows():
        md_lines.append(
            f"| {row['Test']} | {row['Chi-square']} | {row['df']} | {row['p-value']} | {row['Cramers_V']} |"
        )
    
    md_lines.extend([
        "",
        "## Pairwise Comparisons (MIMIC vs Others, Bonferroni-corrected)",
        "",
        "| Comparison | Test | χ² | p-value (adj) | Cramér's V | OR (95% CI) |",
        "|------------|------|---:|:-------------:|-----------:|:-----------:|",
    ])
    
    for _, row in df[df['Comparison'].str.startswith('MIMIC vs')].iterrows():
        md_lines.append(
            f"| {row['Comparison']} | {row['Test']} | {row['Chi-square']} | {row['p-value']} | {row['Cramers_V']} | {row['OR (95% CI)']} |"
        )
    
    md_lines.extend([
        "",
        "OR for LMIC: odds of LMIC authorship in MIMIC relative to comparator (OR > 1 = higher LMIC in MIMIC).",
        "OR for gender: odds of female authorship in MIMIC relative to comparator (OR < 1 = lower female in MIMIC).",
        "",
        "## Position Effects (First vs Last Author Within Each Dataset)",
        "",
        "| Dataset | Test | χ² | p-value | Cramér's V | OR (95% CI) |",
        "|---------|------|---:|--------:|-----------:|:-----------:|",
    ])
    
    position_tests = df[df['Test'].str.contains('First vs Last')]
    for _, row in position_tests.iterrows():
        label = row['Test'].replace('First vs Last author ', '')
        md_lines.append(
            f"| {row['Comparison']} | {label} | {row['Chi-square']} | {row['p-value']} | {row['Cramers_V']} | {row['OR (95% CI)']} |"
        )
    
    md_lines.extend([
        "",
        "OR for position: odds of female (or LMIC) authorship in first author position relative to last author (OR > 1 = higher in first).",
    ])
    
    md_content = "\n".join(md_lines)
    
    with open(OUTPUT_DIR / 'statistical_tests.md', 'w') as f:
        f.write(md_content)
    print(f"Saved: {OUTPUT_DIR / 'statistical_tests.md'}")
    
    print("\n" + "="*80)
    print("STATISTICAL ANALYSIS")
    print("="*80)
    print(md_content)
    
    return df


# =============================================================================
# ADDITIONAL ANALYSIS: Top Countries
# =============================================================================

def analyze_top_countries(datasets, top_n=10):
    """Analyze top countries per dataset."""
    income_data = load_income_classification()
    
    for dataset_name in DATASETS:
        if dataset_name not in datasets:
            continue
        
        data = datasets[dataset_name]
        papers = data.get('papers', [])
        
        country_counts = defaultdict(int)
        
        for paper in papers:
            for author in paper.get('authors', []):
                for country in author.get('countries', []):
                    country_counts[country] += 1
        
        # Sort and get top N
        top_countries = sorted(country_counts.items(), key=lambda x: -x[1])[:top_n]
        
        print(f"\n{dataset_name} - Top {top_n} Countries:")
        for country, count in top_countries:
            income = classify_income(country, income_data)
            income_info = income_data.get(country, {})
            name = income_info.get('name', country)
            print(f"  {country} ({name}): {count:,} [{income}]")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate analysis figures and tables")
    parser.add_argument('--figure', type=int, choices=[1, 2], help="Generate specific figure")
    parser.add_argument('--table', type=str, choices=['2', '3', 's4', 's5'], help="Generate specific table")
    parser.add_argument('--stats', action='store_true', help="Run statistical analysis")
    parser.add_argument('--countries', action='store_true', help="Show top countries analysis")
    args = parser.parse_args()
    
    print("Loading datasets...")
    datasets = load_all_datasets()
    print(f"Loaded {len(datasets)} datasets")
    
    if args.figure == 1:
        print("\nGenerating Figure 1...")
        figure1_cumulative_citations(datasets)
    elif args.figure == 2:
        print("\nGenerating Figure 2...")
        figure2_impact_distribution(datasets)
    elif args.table == '2':
        print("\nGenerating Table 2...")
        table2_demographics(datasets)
    elif args.table == '3':
        print("\nGenerating Table 3...")
        table3_author_positions(datasets)
    elif args.table == 's4':
        print("\nGenerating Table S4...")
        table_s4_intersectional(datasets)
    elif args.table == 's5':
        print("\nGenerating Table S5...")
        table_s5_unique_authors(datasets)
    elif args.stats:
        print("\nRunning Statistical Analysis...")
        statistical_analysis(datasets)
    elif args.countries:
        analyze_top_countries(datasets)
    else:
        # Generate all
        print("\nGenerating Figure 1: Cumulative Citations...")
        figure1_cumulative_citations(datasets)
        
        print("\nGenerating Figure 2: Impact Distribution...")
        figure2_impact_distribution(datasets)
        
        print("\nGenerating Table 2: Author Demographics...")
        table2_demographics(datasets)
        
        print("\nGenerating Table 3: Author Positions...")
        table3_author_positions(datasets)
        
        print("\nGenerating Table S4: Intersectional Analysis...")
        table_s4_intersectional(datasets)
        
        print("\nGenerating Table S5: Unique Authors...")
        table_s5_unique_authors(datasets)
        
        print("\nRunning Statistical Analysis...")
        statistical_analysis(datasets)
        
        print("\nTop Countries Analysis...")
        analyze_top_countries(datasets)
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print(f"Figures saved to: {FIGURES_DIR}")
    print(f"Tables saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
