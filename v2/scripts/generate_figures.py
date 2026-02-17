#!/usr/bin/env python3
"""
Generate all figures for Power of Data Communities v2 analysis.

Uses Google Scholar citation data (complete historical record) combined with
dataset metadata for funding, consent, and reidentification analysis.

Usage:
    python generate_figures.py

Output:
    Creates PNG figures in ../figures/
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy import stats
from pathlib import Path

# Configure matplotlib
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['figure.figsize'] = (8, 6)
plt.rcParams['font.size'] = 12

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
FIGURES_DIR = SCRIPT_DIR.parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

# Analysis parameters
CURRENT_YEAR = 2025
MAX_YEAR = 2024  # Last complete year of data


def load_data():
    """Load and prepare all data for analysis."""
    # Load Google Scholar citations
    citations_raw = pd.read_csv(DATA_DIR / 'google_scholar_citations.csv')
    
    # Filter to max year
    citations_raw = citations_raw[citations_raw['year'] <= MAX_YEAR]
    
    # Combine MIMIC datasets into All-MIMIC
    mimic_datasets = ['MIMIC-I', 'MIMIC-II', 'MIMIC-III', 'MIMIC-IV']
    mimic_df = citations_raw[citations_raw['dataset'].isin(mimic_datasets)].copy()
    other_df = citations_raw[~citations_raw['dataset'].isin(mimic_datasets)].copy()
    
    # Aggregate MIMIC by year
    mimic_combined = mimic_df.groupby('year').agg({
        'citation_count': 'sum',
    }).reset_index()
    mimic_combined['dataset'] = 'All-MIMIC'
    mimic_combined['source'] = 'google_scholar'
    
    # Combine
    citations_df = pd.concat([mimic_combined, other_df], ignore_index=True)
    
    # Calculate cumulative citations for each dataset
    for dataset in citations_df['dataset'].unique():
        mask = citations_df['dataset'] == dataset
        citations_df.loc[mask, 'cumulative_citations'] = citations_df.loc[mask, 'citation_count'].cumsum()
    
    # Load metadata
    metadata_df = pd.read_csv(DATA_DIR / 'datasets_metadata.csv')
    
    print(f"Loaded {len(citations_df)} citation records")
    print(f"Datasets: {citations_df['dataset'].unique()}")
    print(f"Year range: {citations_df['year'].min()} - {citations_df['year'].max()}")
    
    return citations_df, metadata_df


def plot_cumulative_citations(citations_df, metadata_df):
    """Plot cumulative citations over time with launch year markers."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Styles matching original
    styles = {
        'All-MIMIC': {'color': 'firebrick', 'marker': 'o', 'linestyle': '-'},
        'UK-Biobank': {'color': 'black', 'marker': 'o', 'linestyle': '--'},
        'OpenSAFELY': {'color': 'black', 'marker': '^', 'linestyle': '--'},
        'All-of-Us': {'color': 'black', 'marker': 's', 'linestyle': '--'}
    }
    
    launch_years = metadata_df.set_index('dataset')['launch_year'].to_dict()
    
    for dataset in ['All-MIMIC', 'UK-Biobank', 'OpenSAFELY', 'All-of-Us']:
        df = citations_df[citations_df['dataset'] == dataset].sort_values('year')
        if len(df) == 0:
            continue
        style = styles.get(dataset, {'color': 'gray', 'marker': 'o', 'linestyle': '-'})
        
        ax.plot(df['year'], df['cumulative_citations'],
                marker=style['marker'], linestyle=style['linestyle'],
                color=style['color'], label=dataset, linewidth=2, markersize=6)
        
        # Vertical line at launch year
        if dataset in launch_years:
            ax.axvline(x=launch_years[dataset], color=style['color'], 
                      linestyle=':', alpha=0.5, linewidth=1)
    
    ax.set_xlim(1996, 2025)
    ax.set_ylim(bottom=0)
    ax.set_xlabel('Year', fontsize=16)
    ax.set_ylabel('Cumulative Number of Citations', fontsize=16)
    ax.legend(loc='upper left', fontsize=12)
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.grid(True, alpha=0.3, axis='y')
    ax.text(0.98, 0.02, 'Dotted lines indicate launch years', transform=ax.transAxes,
            fontsize=10, ha='right', va='bottom', style='italic', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'cumulative_citations.png', dpi=150)
    plt.close()
    print("Saved: cumulative_citations.png")


def plot_years_since_publication(citations_df, metadata_df):
    """Plot cumulative citations aligned by years since publication."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    styles = {
        'All-MIMIC': {'color': 'firebrick', 'marker': 'o', 'linestyle': '-'},
        'UK-Biobank': {'color': 'black', 'marker': 'o', 'linestyle': '--'},
        'OpenSAFELY': {'color': 'black', 'marker': '^', 'linestyle': '--'},
        'All-of-Us': {'color': 'black', 'marker': 's', 'linestyle': '--'}
    }
    
    launch_years = metadata_df.set_index('dataset')['launch_year'].to_dict()
    
    for dataset in ['All-MIMIC', 'UK-Biobank', 'OpenSAFELY', 'All-of-Us']:
        df = citations_df[citations_df['dataset'] == dataset].sort_values('year')
        if len(df) == 0 or dataset not in launch_years:
            continue
        style = styles.get(dataset, {'color': 'gray', 'marker': 'o', 'linestyle': '-'})
        
        launch = launch_years[dataset]
        years_since = df['year'] - launch
        
        ax.plot(years_since, df['cumulative_citations'],
                marker=style['marker'], linestyle=style['linestyle'],
                color=style['color'], label=dataset, linewidth=2, markersize=6)
    
    ax.set_xlim(left=-1)
    ax.set_ylim(bottom=0)
    ax.set_xlabel('Years Since Publication', fontsize=16)
    ax.set_ylabel('Cumulative Number of Citations', fontsize=16)
    ax.legend(loc='upper left', fontsize=12)
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'citations_years_since_pub.png', dpi=150)
    plt.close()
    print("Saved: citations_years_since_pub.png")


def plot_citation_ratios(citations_df):
    """Plot MIMIC citations relative to other datasets."""
    # Pivot to have years as rows, datasets as columns
    pivot_df = citations_df.pivot(index='year', columns='dataset', values='cumulative_citations')
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    comparisons = [
        ('UK-Biobank', 'o', '#1f77b4'),
        ('OpenSAFELY', '^', '#ff7f0e'),
        ('All-of-Us', 's', '#2ca02c')
    ]
    
    for dataset, marker, color in comparisons:
        if dataset not in pivot_df.columns or 'All-MIMIC' not in pivot_df.columns:
            continue
        
        valid = pivot_df[(pivot_df[dataset] > 0) & (pivot_df['All-MIMIC'] > 0)].index
        if len(valid) == 0:
            continue
            
        ratios = pivot_df.loc[valid, 'All-MIMIC'] / pivot_df.loc[valid, dataset]
        mean_ratio = ratios.mean()
        
        ax.plot(valid, ratios, marker=marker, linestyle='-', color=color,
               label=f'{dataset} (mean: {mean_ratio:.2f}x)', linewidth=2, markersize=6)
    
    ax.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel('Year', fontsize=16)
    ax.set_ylabel('All-MIMIC / Dataset Citation Ratio', fontsize=16)
    ax.set_title('MIMIC Citations Relative to Other Datasets')
    ax.legend(loc='upper right', fontsize=12)
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'citation_ratios.png', dpi=150)
    plt.close()
    print("Saved: citation_ratios.png")


def plot_longevity_comparison(citations_df, metadata_df):
    """Plot total citations vs citations per year."""
    results = []
    launch_years = metadata_df.set_index('dataset')['launch_year'].to_dict()
    
    for dataset in citations_df['dataset'].unique():
        df = citations_df[citations_df['dataset'] == dataset]
        total = df['cumulative_citations'].max()
        
        if dataset in launch_years:
            years_active = CURRENT_YEAR - launch_years[dataset]
            citations_per_year = total / years_active if years_active > 0 else 0
        else:
            years_active = 0
            citations_per_year = 0
        
        results.append({
            'dataset': dataset,
            'total_citations': total,
            'years_active': years_active,
            'citations_per_year': citations_per_year
        })
    
    longevity_df = pd.DataFrame(results).sort_values('citations_per_year', ascending=False)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Total citations
    ax1 = axes[0]
    bars1 = ax1.bar(longevity_df['dataset'], longevity_df['total_citations'], color='steelblue')
    ax1.set_ylabel('Total Citations', fontsize=14)
    ax1.set_title('Raw Total Citations', fontsize=14)
    ax1.tick_params(axis='x', rotation=45, labelsize=12)
    ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # Citations per year
    ax2 = axes[1]
    bars2 = ax2.bar(longevity_df['dataset'], longevity_df['citations_per_year'], color='coral')
    ax2.set_ylabel('Citations per Year', fontsize=14)
    ax2.set_title('Longevity-Adjusted: Citations per Year', fontsize=14)
    ax2.tick_params(axis='x', rotation=45, labelsize=12)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'longevity_comparison.png', dpi=150)
    plt.close()
    print("Saved: longevity_comparison.png")
    
    return longevity_df


def plot_funding_normalized(longevity_df, metadata_df):
    """Plot citations normalized by funding."""
    merged = longevity_df.merge(metadata_df[['dataset', 'funding_usd']], on='dataset')
    merged['citations_per_million_usd'] = merged['total_citations'] / (merged['funding_usd'] / 1_000_000)
    
    plot_df = merged.sort_values('citations_per_million_usd', ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.barh(plot_df['dataset'], plot_df['citations_per_million_usd'], color='forestgreen')
    
    ax.set_xlabel('Citations per $1M USD Funding', fontsize=14)
    ax.set_title('Funding-Normalized Citations\n(Citations per Million USD of Dataset Funding)', fontsize=14)
    ax.grid(True, alpha=0.3, axis='x')
    ax.tick_params(axis='both', labelsize=12)
    
    # Add value labels
    for bar, val in zip(bars, plot_df['citations_per_million_usd']):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
               f'{val:.1f}', va='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'funding_normalized.png', dpi=150)
    plt.close()
    print("Saved: funding_normalized.png")


def plot_consent_comparison(metadata_df):
    """Plot consent and access model distributions."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Access model distribution
    ax1 = axes[0]
    access_counts = metadata_df['access_model'].value_counts()
    colors1 = ['#2ecc71', '#f39c12', '#e74c3c']
    ax1.pie(access_counts.values, labels=access_counts.index, autopct='%1.0f%%',
           colors=colors1[:len(access_counts)], startangle=90)
    ax1.set_title('Distribution of Access Models', fontsize=14)
    
    # Reidentification risk
    ax2 = axes[1]
    risk_order = ['Low', 'Moderate', 'High']
    risk_counts = metadata_df['reidentification_risk'].value_counts().reindex(risk_order, fill_value=0)
    colors2 = ['#2ecc71', '#f39c12', '#e74c3c']
    ax2.bar(risk_counts.index, risk_counts.values, color=colors2)
    ax2.set_ylabel('Number of Datasets', fontsize=14)
    ax2.set_title('Distribution of Reidentification Risk', fontsize=14)
    ax2.set_ylim(0, max(risk_counts.values) + 1)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'consent_comparison.png', dpi=150)
    plt.close()
    print("Saved: consent_comparison.png")


def plot_growth_rates(citations_df):
    """Plot growth rates with confidence intervals."""
    results = []
    
    for dataset in citations_df['dataset'].unique():
        df = citations_df[citations_df['dataset'] == dataset].sort_values('year')
        
        if len(df) < 3:
            continue
        
        citations = df['citation_count'].values
        growth_rates = []
        for i in range(1, len(citations)):
            if citations[i-1] > 0:
                growth = (citations[i] - citations[i-1]) / citations[i-1] * 100
                growth_rates.append(growth)
        
        if len(growth_rates) < 2:
            continue
        
        growth_rates = np.array(growth_rates)
        mean_growth = np.mean(growth_rates)
        std_growth = np.std(growth_rates, ddof=1)
        n = len(growth_rates)
        se = std_growth / np.sqrt(n)
        ci_95 = stats.t.interval(0.95, n-1, loc=mean_growth, scale=se)
        
        results.append({
            'dataset': dataset,
            'mean_growth_rate': mean_growth,
            'ci_95_lower': ci_95[0],
            'ci_95_upper': ci_95[1]
        })
    
    if not results:
        print("No growth rate data available")
        return
    
    growth_df = pd.DataFrame(results).sort_values('mean_growth_rate', ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    yerr_lower = growth_df['mean_growth_rate'] - growth_df['ci_95_lower']
    yerr_upper = growth_df['ci_95_upper'] - growth_df['mean_growth_rate']
    
    ax.barh(growth_df['dataset'], growth_df['mean_growth_rate'],
           xerr=[yerr_lower, yerr_upper],
           color='purple', alpha=0.7, capsize=5)
    
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_xlabel('Mean Year-over-Year Growth Rate (%)', fontsize=14)
    ax.set_title('Citation Growth Rates with 95% Confidence Intervals', fontsize=14)
    ax.grid(True, alpha=0.3, axis='x')
    ax.tick_params(axis='both', labelsize=12)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'growth_rates_ci.png', dpi=150)
    plt.close()
    print("Saved: growth_rates_ci.png")


def generate_summary(citations_df, metadata_df, longevity_df):
    """Generate and save summary table."""
    summary = longevity_df.merge(
        metadata_df[['dataset', 'funding_usd', 'consent_model', 'reidentification_risk']],
        on='dataset'
    )
    summary['citations_per_million_usd'] = summary['total_citations'] / (summary['funding_usd'] / 1_000_000)
    
    summary.to_csv(DATA_DIR / 'analysis_summary.csv', index=False)
    print(f"Saved: analysis_summary.csv")
    
    return summary


def main():
    """Generate all figures."""
    print("=" * 60)
    print("Power of Data Communities - Figure Generation")
    print("=" * 60)
    
    # Load data
    citations_df, metadata_df = load_data()
    
    # Generate figures
    print("\nGenerating figures...")
    plot_cumulative_citations(citations_df, metadata_df)
    plot_years_since_publication(citations_df, metadata_df)
    plot_citation_ratios(citations_df)
    longevity_df = plot_longevity_comparison(citations_df, metadata_df)
    plot_funding_normalized(longevity_df, metadata_df)
    plot_consent_comparison(metadata_df)
    plot_growth_rates(citations_df)
    
    # Generate summary
    summary = generate_summary(citations_df, metadata_df, longevity_df)
    
    print("\n" + "=" * 60)
    print("All figures generated successfully!")
    print(f"Output directory: {FIGURES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
