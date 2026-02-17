#!/usr/bin/env python3
"""
04 - Google Scholar Citation Scraper

Scrapes citation data from Google Scholar for specified publications.
Based on original notebook by Lucas McConnell.

WARNING: Google Scholar may block requests if too many are made.
         Use with caution and respect rate limits.

Usage:
    python 04_scrape_google_scholar.py --dataset MIMIC-III
    python 04_scrape_google_scholar.py --list
    python 04_scrape_google_scholar.py --dataset MIMIC-III --test
"""

import os
import re
import time
import argparse
import numpy as np
import pandas as pd
from urllib import request as urllib_request
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Please install beautifulsoup4: pip install beautifulsoup4")
    exit(1)

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CITATIONS_DIR = DATA_DIR / "scraped_citations"
CITATIONS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# DATASET CONFIGURATIONS
# =============================================================================

# Google Scholar article IDs for each dataset
DATASET_CONFIG = {
    'UK-Biobank': {
        'article_id': 2590122798384494947,
        'start_year': 2015,
        'doi': '10.1371/journal.pmed.1001779'
    },
    'OpenSAFELY': {
        'article_id': 17080000567303433977,
        'start_year': 2020,
        'doi': '10.1038/s41586-020-2521-4'
    },
    'MIMIC-I': {
        'article_id': 5955822449530493366,
        'start_year': 1997,
        'doi': '10.1109/CIC.1996.542622'
    },
    'MIMIC-II': {
        'article_id': 7755589053673476801,
        'start_year': 2003,
        'doi': '10.1109/CIC.2002.1166854'
    },
    'MIMIC-III': {
        'article_id': 4115250243685522,
        'start_year': 2016,
        'doi': '10.1038/sdata.2016.35'
    },
    'MIMIC-IV': {
        'article_id': 7925337910889488074,
        'start_year': 2020,
        'doi': '10.1038/s41597-022-01899-x'
    },
    'MIMIC-CXR': {
        'article_id': 680754441348545603,
        'start_year': 2020,
        'doi': '10.1038/s41597-019-0322-0'
    },
    'All-of-Us': {
        'article_id': 15378313725393442879,
        'start_year': 2019,
        'doi': '10.1056/NEJMsr1809937'
    },
    'PIC': {
        'article_id': 1274953236010921452,
        'start_year': 2019,
        'doi': ''
    },
    'eICU-CRD': {
        'article_id': 11878669525996073977,
        'start_year': 2018,
        'doi': '10.1038/sdata.2018.178'
    },
    'AmsterdamUMCdb': {
        'article_id': 69090949308303245,
        'start_year': 2021,
        'doi': '10.1097/CCM.0000000000004916'
    }
}

# User-Agent spoofing to avoid detection
# NOTE: This list may get outdated and need updating
USER_AGENTS = [
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0; Touch)',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B179 Safari/7534.48.3',
    'Mozilla/5.0 (iPad; U; CPU iPhone OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B314 Safari/531.21.10',
    'Mozilla/5.0 (Linux; U; Android 4.0.4; en-gb; GT-I9300 Build/IMM76D) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
]


# =============================================================================
# SCRAPING FUNCTIONS
# =============================================================================

def get_citations_for_year(article_id: int, year: int, user_agent: str) -> int:
    """
    Get total citation count for a specific year from Google Scholar.
    
    Args:
        article_id: Google Scholar article ID
        year: Year to query
        user_agent: User agent string
    
    Returns:
        Total citation count for that year
    """
    url = (f'https://scholar.google.com/scholar?start=0&hl=en'
           f'&as_ylo={year}&as_yhi={year}&sciodt=0,5'
           f'&cites={article_id}&scipsc=')
    
    req = urllib_request.Request(url, headers={'User-Agent': user_agent})
    
    try:
        html_page = urllib_request.urlopen(req, timeout=30).read()
        soup = BeautifulSoup(html_page, 'html.parser')
        
        # Parse total citation count
        # Example: "About 1,250 results (0.09 sec)"
        try:
            total = int(re.compile(r'About (.*) results? \(').findall(str(soup))[0].replace(',', ''))
        except IndexError:
            try:
                total = int(re.compile(r'([0-9,]*) results? \(').findall(str(soup))[0].replace(',', ''))
            except IndexError:
                total = 0
        
        return total
        
    except Exception as e:
        print(f"  Error fetching year {year}: {e}")
        return 0


def scrape_full_citations(article_id: int, year: int, user_agent: str, 
                          max_queries: int = 25, delay: int = 10) -> list:
    """
    Scrape individual citation counts for papers citing an article in a year.
    
    WARNING: This is slow and may get blocked by Google Scholar.
    
    Args:
        article_id: Google Scholar article ID
        year: Year to query
        user_agent: User agent string
        max_queries: Maximum number of queries before stopping
        delay: Delay between requests in seconds
    
    Returns:
        List of individual citation counts
    """
    # First, get total count
    url = (f'https://scholar.google.com/scholar?start=0&hl=en'
           f'&as_ylo={year}&as_yhi={year}&sciodt=0,5'
           f'&cites={article_id}&scipsc=')
    
    req = urllib_request.Request(url, headers={'User-Agent': user_agent})
    
    try:
        html_page = urllib_request.urlopen(req, timeout=30).read()
        soup = BeautifulSoup(html_page, 'html.parser')
        
        try:
            total_citations = int(re.compile(r'About (.*) results? \(').findall(str(soup))[0].replace(',', ''))
        except IndexError:
            try:
                total_citations = int(re.compile(r'([0-9,]*) results? \(').findall(str(soup))[0].replace(',', ''))
            except IndexError:
                return []
        
        print(f"  Year {year}: {total_citations} total citations")
        
        # Paginate through results (10 at a time)
        all_citations = []
        total_queries = 1
        
        for start_idx in np.arange(0, min(total_citations, 1000), 10):
            if total_queries >= max_queries:
                print(f"  Query limit reached at index {start_idx}")
                break
            
            url = (f'https://scholar.google.com/scholar?start={int(start_idx)}&hl=en'
                   f'&as_ylo={year}&as_yhi={year}&sciodt=0,5'
                   f'&cites={article_id}&scipsc=')
            
            req = urllib_request.Request(url, headers={'User-Agent': user_agent})
            html_page = urllib_request.urlopen(req, timeout=30).read()
            soup = BeautifulSoup(html_page, 'html.parser')
            
            # Extract citation counts
            temp_citations = [int(c) for c in re.compile(r'Cited by ([0-9]*)').findall(str(soup))]
            expected_len = len(re.compile(r'Related articles').findall(str(soup)))
            all_citations.extend(np.pad(temp_citations, (0, expected_len - len(temp_citations)), 'constant').tolist())
            
            print(f"    Scraped: {len(all_citations)}/{total_citations}")
            total_queries += 1
            time.sleep(delay)
        
        return all_citations
        
    except Exception as e:
        print(f"  Error: {e}")
        return []


def scrape_dataset(dataset_name: str, end_year: int = 2025, 
                   delay: int = 10, test_mode: bool = False):
    """
    Scrape citation counts for a dataset (yearly totals only).
    
    Args:
        dataset_name: Name of dataset (must be in DATASET_CONFIG)
        end_year: Last year to scrape
        delay: Delay between requests in seconds
        test_mode: If True, only scrape one year
    
    Returns:
        DataFrame with results
    """
    if dataset_name not in DATASET_CONFIG:
        print(f"Unknown dataset: {dataset_name}")
        print(f"Available: {list(DATASET_CONFIG.keys())}")
        return None
    
    config = DATASET_CONFIG[dataset_name]
    article_id = config['article_id']
    start_year = config['start_year']
    
    print(f"\nScraping {dataset_name}")
    print(f"  Article ID: {article_id}")
    print(f"  DOI: {config['doi']}")
    print(f"  Year range: {start_year} - {end_year}")
    print()
    
    user_agent = USER_AGENTS[-1]
    results = {}
    
    years = [start_year] if test_mode else range(start_year, end_year + 1)
    
    for year in years:
        print(f"  {year}...", end=" ", flush=True)
        count = get_citations_for_year(article_id, year, user_agent)
        results[year] = count
        print(f"{count} citations")
        
        if not test_mode and year < end_year:
            time.sleep(delay)
    
    # Save results
    df = pd.DataFrame([
        {'year': year, 'citations': count, 'dataset': dataset_name, 'doi': config['doi']}
        for year, count in results.items()
    ])
    
    output_file = CITATIONS_DIR / f'{dataset_name.lower()}_citations.csv'
    df.to_csv(output_file, index=False)
    print(f"\nSaved to: {output_file}")
    
    return df


def save_results(results_dict: dict, dataset_name: str):
    """
    Save scraped results to CSV (append to existing file).
    
    Args:
        results_dict: Dictionary of year -> list of citations
        dataset_name: Name of the dataset
    """
    file_name = CITATIONS_DIR / f'citations___{dataset_name}.csv'
    
    try:
        old_df = pd.read_csv(file_name, index_col=0).dropna()
    except FileNotFoundError:
        with open(file_name, 'w') as f:
            f.write(',Year,Citations\n')
        old_df = pd.read_csv(file_name, index_col=0).dropna()
    
    new_data = [(k, i) for k in results_dict.keys() for i in results_dict[k]]
    new_df = pd.DataFrame(data=new_data, columns=['Year', 'Citations'])
    merged_df = pd.concat([old_df, new_df], ignore_index=True).astype(int)
    merged_df.to_csv(file_name)
    
    print(f"Saved to: {file_name}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Scrape Google Scholar citations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python 04_scrape_google_scholar.py --list
    python 04_scrape_google_scholar.py --dataset MIMIC-III --test
    python 04_scrape_google_scholar.py --dataset MIMIC-III --end-year 2025
        """
    )
    parser.add_argument('--dataset', type=str,
                        help='Dataset to scrape')
    parser.add_argument('--end-year', type=int, default=2025,
                        help='Last year to scrape (default: 2025)')
    parser.add_argument('--delay', type=int, default=10,
                        help='Delay between requests in seconds (default: 10)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: only scrape one year')
    parser.add_argument('--list', action='store_true',
                        help='List available datasets')
    
    args = parser.parse_args()
    
    if args.list:
        print("\nAvailable datasets:")
        print("-" * 60)
        for name, config in DATASET_CONFIG.items():
            print(f"  {name:20s} DOI: {config['doi']}")
            print(f"  {'':20s} Start year: {config['start_year']}")
        return
    
    if not args.dataset:
        parser.print_help()
        return
    
    print("=" * 60)
    print("Google Scholar Citation Scraper")
    print("=" * 60)
    print()
    print("WARNING: Google Scholar may block requests if too many are made.")
    print("         Use with caution and respect rate limits.")
    
    scrape_dataset(
        dataset_name=args.dataset,
        end_year=args.end_year,
        delay=args.delay,
        test_mode=args.test
    )


if __name__ == "__main__":
    main()
