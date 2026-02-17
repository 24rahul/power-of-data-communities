#!/usr/bin/env python3
"""
05 - H-Index Analysis

Visualize paper-level citation distributions and calculate h-index.
This analysis requires individual paper citation counts (from scraping).

The h-index is the maximum value h such that the dataset has h papers
that have each been cited at least h times.

Usage:
    python 05_h_index_analysis.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

# Import data definitions
from data_definitions import total_funding

# Configure matplotlib
from matplotlib import rcParams
rcParams['font.sans-serif'] = 'Arial'

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CITATIONS_DIR = DATA_DIR / "scraped_citations"
FIGURES_DIR = SCRIPT_DIR.parent / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def calculate_h_index(citations: np.ndarray) -> int:
    """
    Calculate h-index from citation counts.
    
    The h-index is h if h papers have at least h citations each.
    
    Args:
        citations: Array of citation counts per paper
    
    Returns:
        h-index value
    """
    c = np.array(sorted(citations, reverse=True))
    h_index = 0
    for i in range(len(c)):
        if c[i] >= i + 1:
            h_index = i + 1
        else:
            break
    return h_index


def load_paper_citations(dataset_name: str) -> np.ndarray:
    """
    Load individual paper citation counts for a dataset.
    
    Args:
        dataset_name: Name of dataset
    
    Returns:
        Array of citation counts, or empty array if file not found
    """
    # Try different filename patterns
    patterns = [
        f'citations___{dataset_name}.csv',
        f'{dataset_name.lower()}_citations.csv',
        f'{dataset_name.replace(" ", "-")}_citations.csv',
    ]
    
    for pattern in patterns:
        file_path = CITATIONS_DIR / pattern
        if file_path.exists():
            df = pd.read_csv(file_path, index_col=0)
            return df['Citations'].values.flatten()
    
    # Also check parent citations folder
    parent_citations = DATA_DIR.parent / "citations"
    if parent_citations.exists():
        for pattern in patterns:
            file_path = parent_citations / pattern
            if file_path.exists():
                df = pd.read_csv(file_path, index_col=0)
                return df['Citations'].values.flatten()
    
    return np.array([])


def plot_h_index_curves(
    funding_adjusted=False,
    x_percent_adjusted=False,
    show_y_max=False,
    save=True
):
    """
    Plot citation distribution curves with h-index.
    
    This replicates the original notebook's visualization.
    
    Args:
        funding_adjusted: Normalize by funding
        x_percent_adjusted: Use percentage on x-axis
        show_y_max: Show full y-range
        save: Save figure to file
    
    Returns:
        Dictionary with plotted data
    """
    db_names = ['All MIMIC', 'UK Biobank', 'OpenSAFELY', 'All of Us']
    all_markers = [None, 'o', '^', 's']
    linestyles = ['-', '--', '--', '--']  # Open = solid, Closed = dashed
    
    # Load MIMIC data (combine all versions)
    mimic_citations = []
    for version in ['MIMIC-I', 'MIMIC-II', 'MIMIC-III', 'MIMIC-IV']:
        data = load_paper_citations(version)
        if len(data) > 0:
            mimic_citations.extend(data.tolist())
    mimic_citations = np.array(mimic_citations)
    
    all_data_output = {}
    plt.figure(figsize=(8, 6))
    
    for tbn, temp_db_name in enumerate(db_names):
        # Load data
        if temp_db_name == 'All MIMIC':
            total_df = mimic_citations
            plot_color = 'firebrick'
        else:
            total_df = load_paper_citations(temp_db_name)
            plot_color = 'k'
        
        if len(total_df) == 0:
            print(f"  No data found for {temp_db_name}")
            continue
        
        total_df = np.array(total_df)
        
        # Calculate h-index
        c = np.array(sorted(total_df, reverse=True))
        h_index = calculate_h_index(total_df)
        
        # Calculate funding-adjusted h-index
        if temp_db_name in total_funding and total_funding[temp_db_name] > 0:
            c_adj = c / (total_funding[temp_db_name] / 1_000_000)
            h_index_adj = calculate_h_index(total_df / (total_funding[temp_db_name] / 1_000_000))
        else:
            c_adj = c
            h_index_adj = h_index
        
        # Apply adjustments
        if funding_adjusted:
            if temp_db_name in total_funding and total_funding[temp_db_name] > 0:
                total_df = total_df / (total_funding[temp_db_name] / 1_000_000)
        
        # Create labels
        if x_percent_adjusted:
            plot_label = temp_db_name
        else:
            if funding_adjusted:
                plot_label = f'{temp_db_name} (h-index = {h_index_adj})'
            else:
                plot_label = f'{temp_db_name} (h-index = {h_index})'
        
        # Plot
        if x_percent_adjusted:
            markevery = max(1, int(len(total_df) / 10))
            temp_x_data = 100 * np.arange(1, len(total_df) + 1) / len(total_df)
        else:
            if show_y_max:
                x_max = 30
            else:
                x_max = 1000
            markevery = max(1, int(x_max / 10))
            temp_x_data = np.arange(1, len(total_df) + 1)
        
        temp_y_data = np.array(sorted(total_df, reverse=True))
        
        plt.plot(temp_x_data, temp_y_data, 
                marker=all_markers[tbn], markevery=markevery,
                linestyle=linestyles[tbn], color=plot_color, 
                label=plot_label)
        
        all_data_output[temp_db_name] = {
            'x_data': temp_x_data,
            'y_data': temp_y_data,
            'h_index': h_index
        }
    
    # Formatting
    if x_percent_adjusted:
        xlabel = 'Percentage of Papers (Ranked by Citations)'
        plt.xlim([0, 100])
        plt.yscale('log')
        ax = plt.gca()
        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(
                lambda y, pos: ('{{:.{:1d}f}}'.format(
                    int(np.maximum(-np.log10(y), 0))
                )).format(y) if y > 0 else '0'
            )
        )
    else:
        xlabel = 'Number of Papers (Ranked by Citations)'
        if show_y_max:
            x_max = 30
            if funding_adjusted:
                y_min, y_max = 25, 1000
            else:
                y_min, y_max = 0, 20000
        else:
            x_max = 1000
            if funding_adjusted:
                y_min, y_max = 0, 25
            else:
                y_min, y_max = 0, 500
        plt.xlim([0, x_max])
        plt.ylim([y_min, y_max])
    
    if funding_adjusted:
        ylabel = 'Number of Citations / $1,000,000 Funding'
    else:
        ylabel = 'Number of Citations'
    
    plt.xlabel(xlabel, fontsize=16)
    plt.ylabel(ylabel, fontsize=16)
    plt.legend(fontsize=14)
    
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=14)
    plt.tight_layout()
    
    if save:
        s_funding = 'fadj' if funding_adjusted else ''
        s_xpercent = 'xper' if x_percent_adjusted else ''
        s_ymax = 'ymax' if show_y_max else ''
        filename = f'h_index_{s_funding}_{s_xpercent}_{s_ymax}.png'.replace('__', '_').strip('_')
        filename = filename.replace('_.png', '.png')
        plt.savefig(FIGURES_DIR / filename, dpi=150)
        print(f"Saved: {filename}")
    
    plt.show()
    return all_data_output


def generate_all_h_index_plots():
    """Generate all combinations of h-index plots."""
    combinations = [
        (False, False, False),
        (True, False, False),
        (False, True, True),
        (True, True, True),
    ]
    
    all_results = {}
    for funding_adj, x_pct, y_max in combinations:
        print(f"\nPlot: funding_adj={funding_adj}, x_percent={x_pct}, y_max={y_max}")
        key = (funding_adj, x_pct, y_max)
        all_results[key] = plot_h_index_curves(
            funding_adjusted=funding_adj,
            x_percent_adjusted=x_pct,
            show_y_max=y_max
        )
    
    return all_results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("05 - H-Index Analysis")
    print("=" * 60)
    print()
    print("NOTE: This analysis requires individual paper citation data")
    print("      from Google Scholar scraping. If files are not found,")
    print("      run 04_scrape_google_scholar.py first.")
    print()
    
    # Check for available data
    print("Checking for data files...")
    datasets = ['MIMIC-I', 'MIMIC-II', 'MIMIC-III', 'MIMIC-IV', 
                'UK Biobank', 'OpenSAFELY', 'All of Us']
    
    found_any = False
    for ds in datasets:
        data = load_paper_citations(ds)
        if len(data) > 0:
            h = calculate_h_index(data)
            print(f"  {ds}: {len(data)} papers, h-index = {h}")
            found_any = True
    
    if not found_any:
        print("\n  No citation data files found!")
        print("  This analysis requires scraped individual paper citations.")
        print("  Run: python 04_scrape_google_scholar.py --dataset <name>")
    else:
        print("\nGenerating h-index plots...")
        generate_all_h_index_plots()
