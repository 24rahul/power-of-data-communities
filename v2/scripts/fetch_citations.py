#!/usr/bin/env python3
"""
Fetch citation counts by year from OpenAlex API.

This script queries OpenAlex for citation data for each dataset's primary publication,
providing reproducible bibliometric data for the Power of Data Communities analysis.

Usage:
    python fetch_citations.py

Output:
    Creates CSV files in ../data/citations/ with yearly citation counts.
    Also creates a log file documenting exact API queries for reproducibility.

Author: Power of Data Communities Team
Date: January 2026
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    import pyalex
    from pyalex import Works
except ImportError:
    print("Error: pyalex not installed. Run: pip install pyalex")
    sys.exit(1)

# Configure pyalex with polite pool (faster rate limits)
pyalex.config.email = "research@example.com"  # Replace with your email

# Setup paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CITATIONS_DIR = DATA_DIR / "citations"
LOG_DIR = SCRIPT_DIR.parent / "logs"

# Ensure directories exist
CITATIONS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = LOG_DIR / f"fetch_citations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Dataset DOIs from the original analysis
DATASETS = {
    "MIMIC-I": "10.1109/CIC.1996.542622",
    "MIMIC-II": "10.1109/CIC.2002.1166854",
    "MIMIC-III": "10.1038/sdata.2016.35",
    "MIMIC-IV": "10.1038/s41597-022-01899-x",
    "UK-Biobank": "10.1371/journal.pmed.1001779",
    "OpenSAFELY": "10.1038/s41586-020-2521-4",
    "All-of-Us": "10.1056/NEJMsr1809937",
    # Optional datasets (uncomment to include)
    # "MIMIC-CXR": "10.1038/s41597-019-0322-0",
    # "eICU-CRD": "10.1038/sdata.2018.178",
    # "HiRID": "10.1038/s41591-020-0789-4",
    # "AmsterdamUMCdb": "10.1097/CCM.0000000000004916",
}


def get_work_by_doi(doi: str) -> dict | None:
    """
    Fetch a work from OpenAlex by DOI.
    
    Args:
        doi: The DOI of the publication (without https://doi.org/ prefix)
        
    Returns:
        OpenAlex work object or None if not found
    """
    try:
        # OpenAlex expects DOI in URL format
        doi_url = f"https://doi.org/{doi}"
        work = Works()[doi_url]
        logger.info(f"Found work: {work.get('title', 'Unknown title')[:50]}...")
        return work
    except Exception as e:
        logger.error(f"Error fetching DOI {doi}: {e}")
        return None


def get_citations_by_year(work: dict) -> pd.DataFrame:
    """
    Extract citation counts by year from an OpenAlex work object.
    
    Args:
        work: OpenAlex work object
        
    Returns:
        DataFrame with columns: year, citation_count, cumulative_citations
    """
    # OpenAlex provides counts_by_year for the last 10 years
    counts_by_year = work.get("counts_by_year", [])
    
    if not counts_by_year:
        logger.warning("No citation data available for this work")
        return pd.DataFrame(columns=["year", "citation_count", "cumulative_citations"])
    
    # Convert to DataFrame
    df = pd.DataFrame(counts_by_year)
    
    # Rename columns for clarity
    df = df.rename(columns={"year": "year", "cited_by_count": "citation_count"})
    
    # Sort by year
    df = df.sort_values("year").reset_index(drop=True)
    
    # Add cumulative citations
    df["cumulative_citations"] = df["citation_count"].cumsum()
    
    # Keep only relevant columns
    df = df[["year", "citation_count", "cumulative_citations"]]
    
    return df


def get_total_citations(work: dict) -> int:
    """Get total citation count for a work."""
    return work.get("cited_by_count", 0)


def get_publication_year(work: dict) -> int | None:
    """Get publication year for a work."""
    return work.get("publication_year")


def fetch_all_citations():
    """
    Fetch citation data for all configured datasets and save to CSV files.
    """
    logger.info("=" * 60)
    logger.info("Starting citation data fetch from OpenAlex")
    logger.info(f"Datasets to process: {len(DATASETS)}")
    logger.info("=" * 60)
    
    summary = []
    
    for dataset_name, doi in DATASETS.items():
        logger.info(f"\nProcessing: {dataset_name}")
        logger.info(f"DOI: {doi}")
        
        # Fetch work from OpenAlex
        work = get_work_by_doi(doi)
        
        if work is None:
            logger.error(f"Could not fetch data for {dataset_name}")
            continue
        
        # Extract metadata
        pub_year = get_publication_year(work)
        total_citations = get_total_citations(work)
        title = work.get("title", "Unknown")
        openalex_id = work.get("id", "Unknown")
        
        logger.info(f"Title: {title[:60]}...")
        logger.info(f"Publication year: {pub_year}")
        logger.info(f"Total citations: {total_citations}")
        logger.info(f"OpenAlex ID: {openalex_id}")
        
        # Get citations by year
        citations_df = get_citations_by_year(work)
        
        if citations_df.empty:
            logger.warning(f"No yearly citation data for {dataset_name}")
            continue
        
        # Add metadata columns
        citations_df["dataset"] = dataset_name
        citations_df["doi"] = doi
        citations_df["openalex_id"] = openalex_id
        
        # Save to CSV
        output_file = CITATIONS_DIR / f"{dataset_name.lower().replace(' ', '_')}_citations.csv"
        citations_df.to_csv(output_file, index=False)
        logger.info(f"Saved: {output_file}")
        
        # Add to summary
        summary.append({
            "dataset": dataset_name,
            "doi": doi,
            "openalex_id": openalex_id,
            "publication_year": pub_year,
            "total_citations": total_citations,
            "years_with_data": len(citations_df),
            "latest_year": citations_df["year"].max() if not citations_df.empty else None,
        })
    
    # Save summary
    summary_df = pd.DataFrame(summary)
    summary_file = DATA_DIR / "citation_fetch_summary.csv"
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"\nSummary saved: {summary_file}")
    
    # Log final summary
    logger.info("\n" + "=" * 60)
    logger.info("FETCH COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Datasets processed: {len(summary)}/{len(DATASETS)}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Output directory: {CITATIONS_DIR}")
    
    return summary_df


def combine_all_citations():
    """
    Combine all individual citation CSVs into a single file for analysis.
    """
    all_files = list(CITATIONS_DIR.glob("*_citations.csv"))
    
    if not all_files:
        logger.warning("No citation files found to combine")
        return None
    
    dfs = []
    for f in all_files:
        df = pd.read_csv(f)
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    combined_file = DATA_DIR / "all_citations_combined.csv"
    combined.to_csv(combined_file, index=False)
    logger.info(f"Combined citations saved: {combined_file}")
    
    return combined


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Power of Data Communities - Citation Fetcher")
    print("Using OpenAlex API for reproducible bibliometric data")
    print("=" * 60 + "\n")
    
    # Fetch all citations
    summary = fetch_all_citations()
    
    # Combine into single file
    combined = combine_all_citations()
    
    print("\nDone! Check the logs directory for detailed query information.")
