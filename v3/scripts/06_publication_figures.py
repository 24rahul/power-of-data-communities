#!/usr/bin/env python3
"""
06 - Publication Figures

Generate publication-ready figures and tables that directly address
editor feedback on longevity adjustment and funding attribution.

Key outputs:
1. Figure: Citation trajectories (years since publication)
2. Figure: Funding efficiency comparison (bar chart)
3. Table: Summary metrics at comparable time points

Usage:
    python 06_publication_figures.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

from data_definitions import (
    google_scholar_mimic_pubs,
    closed_datasets,
    total_funding,
    get_combined_mimic_citations
)

# Configure matplotlib for publication
from matplotlib import rcParams
rcParams['font.sans-serif'] = 'Arial'
rcParams['font.size'] = 12
rcParams['axes.linewidth'] = 1.2

# Paths
SCRIPT_DIR = Path(__file__).parent
FIGURES_DIR = SCRIPT_DIR.parent / "figures"
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DATA PREPARATION
# =============================================================================

def get_cumulative_by_age(dataset_name, max_age=10):
    """
    Get cumulative citations by years since first publication.
    
    Returns:
        dict with 'ages' (0 to max_age) and 'cumulative' citations
    """
    if dataset_name == 'All MIMIC':
        # Combine all MIMIC versions, aligned by their individual start years
        mimic_versions = ['mimic-i', 'mimic-ii', 'mimic-iii', 'mimic-iv']
        all_trajectories = []
        
        for version in mimic_versions:
            data = google_scholar_mimic_pubs[version]
            # Find first non-zero year
            start_year = None
            for y, v in data.items():
                if v > 0:
                    start_year = int(y)
                    break
            
            if start_year is None:
                continue
            
            # Build trajectory from start year
            trajectory = [0]
            for y, v in data.items():
                if int(y) >= start_year:
                    trajectory.append(v)
            
            all_trajectories.append(np.cumsum(trajectory))
        
        # Combine by padding and summing
        max_len = max(len(t) for t in all_trajectories)
        combined = np.sum([
            np.pad(t, (0, max_len - len(t)), 'edge')
            for t in all_trajectories
        ], axis=0)
        
        ages = list(range(min(len(combined), max_age + 1)))
        cumulative = combined[:max_age + 1].tolist()
        
    else:
        # Single dataset
        if dataset_name in closed_datasets:
            data = closed_datasets[dataset_name]
        else:
            return None
        
        years = sorted(data.keys())
        values = [data[y] for y in years]
        cumulative = [0] + list(np.cumsum(values))
        ages = list(range(min(len(cumulative), max_age + 1)))
        cumulative = cumulative[:max_age + 1]
    
    return {'ages': ages, 'cumulative': cumulative}


def get_metrics_at_age(age=5):
    """
    Get key metrics for all datasets at a specific age.
    
    Args:
        age: Years since publication to compare
    
    Returns:
        DataFrame with metrics
    """
    datasets = ['All MIMIC', 'UK Biobank', 'OpenSAFELY', 'All of Us']
    
    rows = []
    for ds in datasets:
        traj = get_cumulative_by_age(ds, max_age=age)
        if traj is None or len(traj['cumulative']) <= age:
            continue
        
        citations_at_age = traj['cumulative'][age]
        funding = total_funding.get(ds, 0)
        
        if funding > 0:
            citations_per_million = citations_at_age / (funding / 1_000_000)
        else:
            citations_per_million = 0
        
        rows.append({
            'Dataset': ds,
            'Citations at Year {}'.format(age): int(citations_at_age),
            'Funding ($M)': round(funding / 1_000_000, 1),
            'Citations per $1M': round(citations_per_million, 1)
        })
    
    return pd.DataFrame(rows)


# =============================================================================
# FIGURE 1: CITATION TRAJECTORIES
# =============================================================================

def figure_citation_trajectories(max_age=9, save=True):
    """
    Publication-ready figure showing citation growth by years since publication.
    
    Addresses: "adjusting for the longevity of each project"
    """
    datasets = ['All MIMIC', 'UK Biobank', 'OpenSAFELY', 'All of Us']
    
    # Style configuration
    styles = {
        'All MIMIC': {'color': '#c0392b', 'linestyle': '-', 'marker': None, 'linewidth': 2.5},
        'UK Biobank': {'color': '#2c3e50', 'linestyle': '--', 'marker': 'o', 'linewidth': 1.5},
        'OpenSAFELY': {'color': '#2c3e50', 'linestyle': '--', 'marker': '^', 'linewidth': 1.5},
        'All of Us': {'color': '#2c3e50', 'linestyle': '--', 'marker': 's', 'linewidth': 1.5},
    }
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    for ds in datasets:
        traj = get_cumulative_by_age(ds, max_age=max_age)
        if traj is None:
            continue
        
        style = styles[ds]
        ax.plot(traj['ages'], traj['cumulative'], 
                label=ds, 
                color=style['color'],
                linestyle=style['linestyle'],
                marker=style['marker'],
                linewidth=style['linewidth'],
                markersize=6,
                markerfacecolor='white',
                markeredgewidth=1.5)
    
    ax.set_xlabel('Years Since Publication', fontsize=14, fontweight='medium')
    ax.set_ylabel('Cumulative Citations', fontsize=14, fontweight='medium')
    ax.set_xlim([0, max_age])
    ax.set_xticks(range(0, max_age + 1))
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.tick_params(axis='both', labelsize=12)
    ax.legend(loc='upper left', fontsize=12, frameon=True, fancybox=False, edgecolor='gray')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    if save:
        filepath = FIGURES_DIR / 'fig1_citation_trajectories.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Saved: {filepath.name}")
    
    plt.show()


# =============================================================================
# FIGURE 2: FUNDING EFFICIENCY
# =============================================================================

def figure_funding_efficiency(comparison_age=5, save=True):
    """
    Publication-ready bar chart showing citations per $1M funding.
    
    Addresses: "the amount of funding attributable to the dataset specifically"
    """
    datasets = ['All MIMIC', 'UK Biobank', 'OpenSAFELY', 'All of Us']
    
    # Calculate metrics at comparison age
    data = []
    for ds in datasets:
        traj = get_cumulative_by_age(ds, max_age=comparison_age)
        if traj is None or len(traj['cumulative']) <= comparison_age:
            continue
        
        citations = traj['cumulative'][comparison_age]
        funding = total_funding.get(ds, 0)
        
        if funding > 0:
            efficiency = citations / (funding / 1_000_000)
            data.append({
                'dataset': ds,
                'citations': citations,
                'funding_millions': funding / 1_000_000,
                'efficiency': efficiency
            })
    
    df = pd.DataFrame(data)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Bar colors: MIMIC in red, others in gray
    colors = ['#c0392b' if d == 'All MIMIC' else '#7f8c8d' for d in df['dataset']]
    
    bars = ax.bar(df['dataset'], df['efficiency'], color=colors, edgecolor='white', linewidth=1.5)
    
    # Add value labels on bars
    for bar, eff in zip(bars, df['efficiency']):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f'{eff:.1f}', ha='center', va='bottom', fontsize=11, fontweight='medium')
    
    ax.set_ylabel(f'Citations per $1M Funding\n(at Year {comparison_age})', fontsize=13, fontweight='medium')
    ax.set_xlabel('')
    ax.tick_params(axis='x', labelsize=12)
    ax.tick_params(axis='y', labelsize=11)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim([0, max(df['efficiency']) * 1.15])
    
    plt.tight_layout()
    
    if save:
        filepath = FIGURES_DIR / 'fig2_funding_efficiency.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Saved: {filepath.name}")
    
    plt.show()
    
    return df


# =============================================================================
# TABLE 1: SUMMARY METRICS
# =============================================================================

def table_summary_metrics(ages=[3, 5, 7], save=True):
    """
    Generate summary table with metrics at multiple time points.
    """
    datasets = ['All MIMIC', 'UK Biobank', 'OpenSAFELY', 'All of Us']
    
    rows = []
    for ds in datasets:
        traj = get_cumulative_by_age(ds, max_age=max(ages))
        if traj is None:
            continue
        
        funding = total_funding.get(ds, 0)
        funding_millions = funding / 1_000_000 if funding > 0 else 0
        
        row = {
            'Dataset': ds,
            'Funding ($M)': f'{funding_millions:,.1f}',
        }
        
        for age in ages:
            if age < len(traj['cumulative']):
                citations = traj['cumulative'][age]
                row[f'Citations (Yr {age})'] = f'{citations:,}'
                
                if funding > 0:
                    eff = citations / funding_millions
                    row[f'Cit/$M (Yr {age})'] = f'{eff:.1f}'
                else:
                    row[f'Cit/$M (Yr {age})'] = '-'
            else:
                row[f'Citations (Yr {age})'] = '-'
                row[f'Cit/$M (Yr {age})'] = '-'
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    if save:
        filepath = OUTPUT_DIR / 'table1_summary_metrics.csv'
        df.to_csv(filepath, index=False)
        print(f"Saved: {filepath.name}")
    
    print("\n" + "=" * 70)
    print("TABLE 1: Summary Metrics by Years Since Publication")
    print("=" * 70)
    print(df.to_string(index=False))
    print()
    
    return df


# =============================================================================
# MIMIC ADVANTAGE CALCULATION
# =============================================================================

def calculate_mimic_advantage(age=5):
    """
    Calculate how many times more efficient MIMIC is than other datasets.
    """
    datasets = ['All MIMIC', 'UK Biobank', 'OpenSAFELY', 'All of Us']
    
    efficiencies = {}
    for ds in datasets:
        traj = get_cumulative_by_age(ds, max_age=age)
        if traj is None or len(traj['cumulative']) <= age:
            continue
        
        citations = traj['cumulative'][age]
        funding = total_funding.get(ds, 0)
        
        if funding > 0:
            efficiencies[ds] = citations / (funding / 1_000_000)
    
    mimic_eff = efficiencies.get('All MIMIC', 0)
    
    print("\n" + "=" * 70)
    print(f"MIMIC FUNDING EFFICIENCY ADVANTAGE (at Year {age})")
    print("=" * 70)
    print(f"\nAll MIMIC: {mimic_eff:.1f} citations per $1M\n")
    
    for ds, eff in efficiencies.items():
        if ds != 'All MIMIC' and eff > 0:
            ratio = mimic_eff / eff
            print(f"  vs {ds}: {ratio:.0f}x more efficient")
    
    print()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("PUBLICATION FIGURES - Addressing Editor Feedback")
    print("=" * 70)
    print()
    print("Editor concerns addressed:")
    print("  (a) Longevity adjustment → Figure 1: Citation trajectories")
    print("  (b) Funding attribution → Figure 2: Funding efficiency")
    print()
    
    # Generate outputs
    print("-" * 70)
    print("Generating Figure 1: Citation Trajectories...")
    print("-" * 70)
    figure_citation_trajectories(max_age=9)
    
    print("-" * 70)
    print("Generating Figure 2: Funding Efficiency...")
    print("-" * 70)
    df_efficiency = figure_funding_efficiency(comparison_age=5)
    
    print("-" * 70)
    print("Generating Table 1: Summary Metrics...")
    print("-" * 70)
    table_summary_metrics(ages=[3, 5, 7])
    
    # Calculate advantage
    calculate_mimic_advantage(age=5)
    
    print("=" * 70)
    print("DONE - Figures saved to v3/figures/")
    print("=" * 70)
