#!/usr/bin/env python3
"""
03 - Plot Funding-Normalized Citations

Plot the growth of each database normalized by total funding received.
Addresses reviewer concern about funding attribution.

Usage:
    python 03_plot_funding_normalized.py
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


def plot_funding_normalized(
    max_year=2024,
    max_mimic=9,
    xlim_max=10,
    combine_mimic=True,
    log_scale=True,
    save=True
):
    """
    Plot citation growth normalized by funding ($1M USD).
    
    Args:
        max_year: Last year to include
        max_mimic: Max x-axis value for MIMIC line
        xlim_max: X-axis limit
        combine_mimic: If True, combine all MIMIC versions
        log_scale: If True, use log scale for y-axis
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
        # Find start year
        start_year = None
        for y, v in google_scholar_mimic_pubs[db].items():
            if v != 0:
                start_year = int(y)
                break
        
        if start_year is None:
            continue
        
        # Build cumulative data
        y_data = []
        for y, v in google_scholar_mimic_pubs[db].items():
            if int(y) >= start_year and int(y) < max_year:
                y_data.append(v)
        y_data = np.array([0] + list(np.cumsum(y_data)))
        x_data = range(len(y_data))
        
        if combine_mimic:
            all_y_data.append(y_data)
        else:
            plt.plot(x_data, y_data, color=colors[i], label=db.upper())
        
        all_data_output[db] = {'x_data': list(x_data), 'y_data': y_data}
    
    # Combine and normalize MIMIC
    if combine_mimic:
        max_len = max(len(a) for a in all_y_data)
        all_x_data = range(max_len)
        all_y_data = np.sum([
            np.pad(a, (0, max_len - len(a)), 'constant') 
            for a in all_y_data
        ], axis=0)
        
        # Normalize by funding
        funding_millions = total_funding['All MIMIC'] / 1_000_000
        all_y_data_norm = np.array(all_y_data / funding_millions)
        
        plt.plot(all_x_data[:max_mimic], all_y_data_norm[:max_mimic], 
                color=colors[-1], label='All MIMIC', linewidth=2)
        
        all_data_output['All MIMIC'] = {
            'x_data': list(all_x_data),
            'y_data': all_y_data_norm
        }
    
    # Plot closed datasets (normalized)
    for i, (name, data) in enumerate(closed_datasets.items()):
        if name not in total_funding:
            continue
        
        start_year = int(list(data.keys())[0])
        y_data = [v for y, v in data.items() 
                  if int(y) >= start_year and int(y) < max_year]
        y_data = np.array([0] + list(np.cumsum(y_data)))
        x_data = range(len(y_data))
        
        # Normalize by funding
        funding_millions = total_funding[name] / 1_000_000
        y_data_norm = y_data / funding_millions
        
        plt.plot(x_data, y_data_norm, 
                color='k', linestyle='--', marker=closed_markers[i], 
                label=name, markersize=6)
        
        all_data_output[name] = {
            'x_data': list(x_data),
            'y_data': y_data_norm
        }
    
    # Formatting
    plt.xlabel('Years Since Publication', fontsize=16)
    plt.ylabel('Total Citations / $1,000,000 Funding', fontsize=16)
    plt.legend(fontsize=16)
    plt.xlim([0, xlim_max])
    
    if log_scale:
        plt.yscale('log')
        ax = plt.gca()
        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(
                lambda y, pos: ('{{:.{:1d}f}}'.format(
                    int(np.maximum(-np.log10(y), 0))
                )).format(y) if y > 0 else '0'
            )
        )
    
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.set_xticks(range(0, xlim_max))
    plt.tight_layout()
    
    if save:
        ms = 'MIMIC-together' if combine_mimic else 'MIMIC-apart'
        scale = 'log' if log_scale else 'linear'
        filename = f'funding_normalized_{ms}_{scale}.png'
        plt.savefig(FIGURES_DIR / filename, dpi=150)
        print(f"Saved: {filename}")
    
    plt.show()
    return all_data_output


def plot_funding_ratio_comparison(all_data_output, x_min=3, x_max=6, save=True):
    """
    Plot funding-normalized citation ratios.
    
    Args:
        all_data_output: Dictionary from plot_funding_normalized
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
        data = np.where(data == 0, 0.001, data)
        ratio = mimic_data / data
        mean_ratio = np.mean(ratio)
        
        plt.plot(np.arange(x_min, x_max, 1), ratio,
                marker='o', label=f'{name} ({mean_ratio:.2f}x)')
    
    plt.xlabel('Years Since Publication', fontsize=14)
    plt.ylabel('MIMIC / Other (Funding Normalized)', fontsize=14)
    plt.title('Funding-Normalized Citation Ratio', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save:
        plt.savefig(FIGURES_DIR / 'funding_normalized_ratios.png', dpi=150)
        print("Saved: funding_normalized_ratios.png")
    
    plt.show()


def print_funding_summary():
    """Print funding comparison summary."""
    print("\n--- Funding Summary ---")
    for name, amount in total_funding.items():
        if amount > 0 and name in ['All MIMIC', 'UK Biobank', 'OpenSAFELY', 'All of Us']:
            print(f"  {name}: ${amount:,.2f} ({amount/1e6:.1f}M)")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("03 - Plot Funding-Normalized Citations")
    print("=" * 60)
    
    print_funding_summary()
    
    # Generate main plot (log scale)
    print("\nGenerating funding-normalized plot (log scale)...")
    data = plot_funding_normalized(
        max_year=2024, 
        combine_mimic=True, 
        log_scale=True
    )
    
    # Generate ratio comparison
    print("\nGenerating funding-normalized ratio comparison...")
    plot_funding_ratio_comparison(data, x_min=3, x_max=6)
    
    # Print results
    print("\n" + "=" * 60)
    print("Funding-Normalized Data Summary (at year 5):")
    for name, d in data.items():
        if 'y_data' in d and len(d['y_data']) > 5:
            val = d['y_data'][5]
            print(f"  {name}: {val:.2f} citations per $1M")
