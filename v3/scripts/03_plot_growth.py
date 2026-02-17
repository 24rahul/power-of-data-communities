#!/usr/bin/env python3
"""
02 - Plot Citation Growth

Plot the growth of each database adjusted from the start time.
This is the main longevity-adjusted comparison figure.

Usage:
    python 02_plot_growth.py
"""

import os
import pprint
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

# Import data definitions
from data_definitions import (
    google_scholar_mimic_pubs,
    closed_datasets,
    total_funding
)

# Configure matplotlib
from matplotlib import rcParams
rcParams['font.sans-serif'] = 'Arial'

# Paths
SCRIPT_DIR = Path(__file__).parent
FIGURES_DIR = SCRIPT_DIR.parent / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def plot_growth_adjusted(
    max_year=2024,
    max_mimic=9,
    xlim_max=10,
    combine_mimic=True,
    save=True
):
    """
    Plot citation growth adjusted from start time.
    
    Args:
        max_year: Last year to include
        max_mimic: Max x-axis value for MIMIC line
        xlim_max: X-axis limit
        combine_mimic: If True, combine all MIMIC versions
        save: If True, save figure to file
    
    Returns:
        Dictionary with all plotted data
    """
    db_order = ['mimic-i', 'mimic-ii', 'mimic-iii', 'mimic-iv']
    colors = ['cornflowerblue', 'lightsteelblue', 'dimgray', 'lightcoral', 'firebrick']
    closed_markers = ['o', '^', 's']
    
    plt.figure(figsize=(8, 6))
    all_data_output = {}
    
    # Process MIMIC datasets
    if combine_mimic:
        all_y_data = []
    
    for i, db in enumerate(db_order):
        # Find start year (first non-zero citation)
        start_year = None
        for y, v in google_scholar_mimic_pubs[db].items():
            if v != 0:
                start_year = int(y)
                break
        
        if start_year is None:
            continue
        
        # Build cumulative data
        y_data = [0]
        for y, v in google_scholar_mimic_pubs[db].items():
            if int(y) >= start_year and int(y) <= max_year:
                y_data.append(v)
        y_data = np.cumsum(y_data)
        x_data = range(len(y_data))
        
        if combine_mimic:
            all_y_data.append(y_data)
        else:
            plt.plot(x_data, y_data, color=colors[i], label=db.upper())
        
        all_data_output[db] = {'x_data': list(x_data), 'y_data': y_data}
    
    # Combine MIMIC if requested
    if combine_mimic:
        max_len = max(len(a) for a in all_y_data)
        all_y_data = np.sum([
            np.pad(a, (0, max_len - len(a)), 'constant') 
            for a in all_y_data
        ], axis=0)
        all_x_data = range(len(all_y_data))
        plt.plot(all_x_data[:max_mimic], all_y_data[:max_mimic], 
                color=colors[-1], label='All MIMIC', linewidth=2)
        all_data_output['All MIMIC'] = {
            'x_data': list(all_x_data),
            'y_data': all_y_data
        }
    
    # Plot closed datasets
    for i, (name, data) in enumerate(closed_datasets.items()):
        start_year = int(list(data.keys())[0])
        y_data = [v for y, v in data.items() 
                  if int(y) >= start_year and int(y) <= max_year]
        y_data = [0] + list(np.cumsum(y_data))
        x_data = range(len(y_data))
        
        plt.plot(x_data[:xlim_max+1], y_data[:xlim_max+1], 
                color='k', linestyle='--', marker=closed_markers[i], 
                label=name, markersize=6)
        
        all_data_output[name] = {'x_data': list(x_data), 'y_data': y_data}
    
    # Formatting
    plt.xlabel('Years Since Publication', fontsize=16)
    plt.ylabel('Cumulative Number of Citations', fontsize=16)
    plt.legend(loc='upper left', fontsize=16)
    plt.xlim([0, xlim_max])
    
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.set_xticks(range(xlim_max))
    plt.tight_layout()
    
    if save:
        ms = 'MIMIC-together' if combine_mimic else 'MIMIC-apart'
        filename = f'growth_adjusted_{ms}.png'
        plt.savefig(FIGURES_DIR / filename, dpi=150)
        print(f"Saved: {filename}")
    
    plt.show()
    return all_data_output


def plot_citation_ratios(all_data_output, x_min=3, x_max=6, save=True):
    """
    Plot citation ratios (MIMIC vs other datasets).
    
    Args:
        all_data_output: Dictionary from plot_growth_adjusted
        x_min: Start of comparison range
        x_max: End of comparison range
        save: If True, save figure
    """
    comparisons = ['UK Biobank', 'OpenSAFELY', 'All of Us']
    
    # Interpolate data
    mimic_data = np.interp(
        np.arange(x_min, x_max, 1),
        all_data_output['All MIMIC']['x_data'],
        all_data_output['All MIMIC']['y_data']
    )
    
    plt.figure(figsize=(6, 6))
    
    for name in comparisons:
        if name not in all_data_output:
            continue
        
        data = np.interp(
            np.arange(x_min, x_max, 1),
            all_data_output[name]['x_data'],
            all_data_output[name]['y_data']
        )
        
        # Avoid division by zero
        data = np.where(data == 0, 1, data)
        ratio = mimic_data / data
        mean_ratio = np.mean(ratio)
        
        plt.plot(np.arange(x_min, x_max, 1), ratio,
                marker='o', label=f'{name} ({mean_ratio:.2f}x)')
    
    plt.xlabel('Years Since Publication', fontsize=14)
    plt.ylabel('All MIMIC / Other Dataset Ratio', fontsize=14)
    plt.title('Citation Ratio Comparison', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save:
        plt.savefig(FIGURES_DIR / 'citation_ratios_growth.png', dpi=150)
        print("Saved: citation_ratios_growth.png")
    
    plt.show()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("02 - Plot Citation Growth (Longevity Adjusted)")
    print("=" * 60)
    
    # Generate main plot
    print("\nGenerating growth plot...")
    data = plot_growth_adjusted(max_year=2024, combine_mimic=True)
    
    # Generate ratio comparison
    print("\nGenerating ratio comparison...")
    plot_citation_ratios(data, x_min=3, x_max=6)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Data Summary:")
    for name, d in data.items():
        if 'y_data' in d:
            max_citations = int(max(d['y_data'])) if len(d['y_data']) > 0 else 0
            print(f"  {name}: {max_citations:,} max citations")
