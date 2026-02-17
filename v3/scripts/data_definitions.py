#!/usr/bin/env python3
"""
01 - Data Definitions

Contains all citation data from Google Scholar and funding information.
This is the source of truth for all analyses.

Data collected manually from Google Scholar using the method described below.

Methods for manually collecting Google Scholar citations:
1. Go to: https://scholar.google.com/
2. Type a query to get a specific DB, i.e., "mimic-iv" for MIMIC-IV
3. Find the original paper (usually the first result, or top cited one)
4. Click on "Cited by ###" underneath the brief abstract
5. On the left side, click "Custom range..."
6. In both boxes, type the year you want, i.e., "2023 - 2023"
7. At the top, under the search bar is the number of citations that year
"""

import numpy as np
import pandas as pd
from pathlib import Path

# =============================================================================
# MIMIC DATASETS (Open Data)
# =============================================================================

google_scholar_mimic_pubs = {
    # DOI: 10.1109/CIC.1996.542622
    'mimic-i': {
        '1997':  2, '1998':  1, '1999':  2, '2000':  4, '2001':  4,
        '2002':  4, '2003':  3, '2004':  7, '2005':  5, '2006': 10,
        '2007': 12, '2008':  3, '2009':  9, '2010': 10, '2011': 12,
        '2012':  7, '2013':  9, '2014':  7, '2015': 13, '2016': 18,
        '2017': 25, '2018': 14, '2019': 17, '2020': 30, '2021': 29,
        '2022': 24, '2023': 27, '2024': 23, '2025': 23
    },
    # DOI: 10.1109/CIC.2002.1166854
    'mimic-ii': {
        '1997':  0, '1998':  0, '1999':  0, '2000':  0, '2001':  0,
        '2002':  0, '2003':  2, '2004':  8, '2005': 10, '2006': 10,
        '2007': 15, '2008': 11, '2009': 11, '2010': 15, '2011': 11,
        '2012': 22, '2013': 20, '2014': 21, '2015': 24, '2016': 26,
        '2017': 15, '2018': 18, '2019': 16, '2020': 23, '2021': 20,
        '2022': 15, '2023': 19, '2024': 21
    },
    # DOI: 10.1038/sdata.2016.35
    'mimic-iii': {
        '1997':    0, '1998':    0, '1999':    0, '2000':    0, '2001':    0,
        '2002':    0, '2003':    0, '2004':    0, '2005':    0, '2006':    0,
        '2007':    0, '2008':    0, '2009':    0, '2010':    0, '2011':    0,
        '2012':    0, '2013':    0, '2014':    0, '2015':    0, '2016':   24,
        '2017':  147, '2018':  428, '2019':  650, '2020':  960, '2021': 1260,
        '2022': 1440, '2023': 1510, '2024': 1595
    },
    # DOI: 10.1038/s41597-022-01899-x
    'mimic-iv': {
        '1997':   0, '1998':   0, '1999':   0, '2000':   0, '2001':   0,
        '2002':   0, '2003':   0, '2004':   0, '2005':   0, '2006':   0,
        '2007':   0, '2008':   0, '2009':   0, '2010':   0, '2011':   0,
        '2012':   0, '2013':   0, '2014':   0, '2015':   0, '2016':   0,
        '2017':   0, '2018':   0, '2019':   0, '2020':   0, '2021':   0,
        '2022':   2, '2023': 173, '2024': 799
    },
}

# DOIs for reference
MIMIC_DOIS = {
    'mimic-i':   '10.1109/CIC.1996.542622',
    'mimic-ii':  '10.1109/CIC.2002.1166854',
    'mimic-iii': '10.1038/sdata.2016.35',
    'mimic-iv':  '10.1038/s41597-022-01899-x',
}

# =============================================================================
# COMPARISON DATASETS (Closed/Restricted Data)
# =============================================================================

closed_datasets = {
    # DOI: 10.1371/journal.pmed.1001779
    'UK Biobank': {
        '2015':   18, '2016':   98, '2017':  238, '2018':  462,
        '2019':  693, '2020':  921, '2021': 1257, '2022': 1596,
        '2023': 1902, '2024': 2397
    },
    # DOI: 10.1038/s41586-020-2521-4
    'OpenSAFELY': {
        '2019':  332, '2020': 2100, '2021': 1693, '2022': 1109,
        '2023':  731, '2024':  288
    },
    # DOI: 10.1056/NEJMsr1809937
    'All of Us': {
        '2018':   1, '2019':  21, '2020': 108, '2021': 175,
        '2022': 222, '2023': 325, '2024': 454
    },
}

CLOSED_DOIS = {
    'UK Biobank': '10.1371/journal.pmed.1001779',
    'OpenSAFELY': '10.1038/s41586-020-2521-4',
    'All of Us':  '10.1056/NEJMsr1809937',
}

# =============================================================================
# OTHER DATASETS (Commented out in original)
# =============================================================================

other_datasets = {
    # DOI: 10.1038/sdata.2018.178
    # 'eICU-CRD': {
    #     '2018':   4, '2019':  45, '2020': 136, '2021': 194,
    #     '2022': 263, '2023': 323, '2024':  51
    # },
    # DOI: 10.1038/s41591-020-0789-4
    # 'HiRID': {'2021': 3, '2022': 6, '2023': 15, '2024': 2},
    # DOI: 10.1097/CCM.0000000000004916
    # 'AmsterdamUMCdb': {'2021': 7, '2022': 22, '2023': 40, '2024': 4},
}

# =============================================================================
# FUNDING DATA
# =============================================================================

def load_mimic_funding(funding_file=None):
    """
    Load MIMIC funding from CSV file or use default.
    
    Args:
        funding_file: Path to all-MIMIC.csv funding file
    
    Returns:
        Total MIMIC funding in USD
    """
    if funding_file and Path(funding_file).exists():
        df = pd.read_csv(funding_file)
        return df[~df['Application ID'].isna()]['Total Cost IC'].sum()
    else:
        # Default value from original notebook
        return 14427192.0


# Funding amounts in USD
total_funding = {
    # NIH Reporter - combined MIMIC grants
    'All MIMIC': 14427192.0,  # From funding_sources/all-MIMIC.csv
    
    # https://www.ukbiobank.ac.uk/media/wgsfd0qg/uk-biobank-funding-details-summary.pdf
    # Total = 413.8 million GBP = 525,546,276.20 USD (June 9, 2024 conversion rate)
    'UK Biobank': 525546276.20,
    
    # Multiple grants:
    # Wellcome Trust (222097), MRC (MR/W016729/1), MRC (MR/V015757/1)?, 
    # MC_PC_20051, MC_PC_20058, MC_PC_20059, NIHR135559, COV-LT-0009, COV-LT2-0073
    'OpenSAFELY': (2874941.71 + 774508.54 + 0 + 6055626.76 + 
                  19188252.00 + 11454881.49 + 403228.32 + 
                  12109587.17 + 854028.70),  # = 53,715,054.69
    
    # DOI: 10.1056/NEJMsr1809937
    'All of Us': 2.16e9,
    
    # Others (from original notebook)
    'eICU-CRD': 0,
    'HiRID': 756819 + 1420850,  # CHF, need conversion
    'PIC': np.nan,
    'AmsterdamUMCdb': np.nan,
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_start_year(dataset_name):
    """Get the first year with citations for a dataset."""
    if dataset_name in google_scholar_mimic_pubs:
        data = google_scholar_mimic_pubs[dataset_name]
    elif dataset_name in closed_datasets:
        data = closed_datasets[dataset_name]
    else:
        return None
    
    for year, count in data.items():
        if count > 0:
            return int(year)
    return None


def get_all_citations_df():
    """Convert all citation data to a pandas DataFrame."""
    rows = []
    
    # MIMIC datasets
    for dataset, years in google_scholar_mimic_pubs.items():
        doi = MIMIC_DOIS.get(dataset, '')
        for year, citations in years.items():
            rows.append({
                'dataset': dataset.upper(),
                'year': int(year),
                'citations': citations,
                'source': 'google_scholar',
                'doi': doi,
                'data_type': 'open'
            })
    
    # Closed datasets
    for dataset, years in closed_datasets.items():
        doi = CLOSED_DOIS.get(dataset, '')
        for year, citations in years.items():
            rows.append({
                'dataset': dataset,
                'year': int(year),
                'citations': citations,
                'source': 'google_scholar',
                'doi': doi,
                'data_type': 'closed'
            })
    
    return pd.DataFrame(rows)


def get_combined_mimic_citations():
    """Combine all MIMIC versions into a single 'All MIMIC' dataset."""
    combined = {}
    
    for dataset, years in google_scholar_mimic_pubs.items():
        for year, citations in years.items():
            year_int = int(year)
            if year_int not in combined:
                combined[year_int] = 0
            combined[year_int] += citations
    
    return dict(sorted(combined.items()))


# =============================================================================
# MAIN - Print summary when run directly
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Data Definitions Summary")
    print("=" * 60)
    
    print("\n--- MIMIC Datasets ---")
    for name in google_scholar_mimic_pubs:
        start = get_start_year(name)
        total = sum(google_scholar_mimic_pubs[name].values())
        print(f"  {name.upper()}: {total} citations (since {start})")
    
    combined = get_combined_mimic_citations()
    print(f"  ALL MIMIC: {sum(combined.values())} total citations")
    
    print("\n--- Closed Datasets ---")
    for name in closed_datasets:
        start = get_start_year(name)
        total = sum(closed_datasets[name].values())
        print(f"  {name}: {total} citations (since {start})")
    
    print("\n--- Funding (USD) ---")
    for name, amount in total_funding.items():
        if pd.notna(amount) and amount > 0:
            print(f"  {name}: ${amount:,.2f}")
