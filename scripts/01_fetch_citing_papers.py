#!/usr/bin/env python3
"""
01 - Fetch Citing Papers from OpenAlex

Retrieves all papers that cite each dataset's primary publication,
including author names, affiliations, and citation counts.

OpenAlex API is free and does not require authentication.
Polite pool: include email in User-Agent for higher rate limits.

Usage:
    python 01_fetch_citing_papers.py                    # Fetch all as JSON
    python 01_fetch_citing_papers.py --dataset MIMIC-III
    python 01_fetch_citing_papers.py --test             # Fetch only 25 papers per dataset
    python 01_fetch_citing_papers.py --format csv       # Legacy CSV format
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
import requests
import pandas as pd

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CITING_PAPERS_DIR = DATA_DIR / "citing_papers"
CITING_PAPERS_DIR.mkdir(parents=True, exist_ok=True)

# OpenAlex configuration
OPENALEX_BASE = "https://api.openalex.org"
# Add your email for polite pool (higher rate limits)
USER_AGENT = "CitationAnalysis/1.0 (mailto:your-email@example.com)"


# =============================================================================
# DATASET CONFIGURATIONS
# =============================================================================

DATASETS = {
    'MIMIC-I': {
        'doi': '10.1109/CIC.1996.542622',
        'openalex_id': None,  # Will be looked up
        'launch_year': 1997,
    },
    'MIMIC-II': {
        'doi': '10.1109/CIC.2002.1166854',
        'openalex_id': None,
        'launch_year': 2003,
    },
    'MIMIC-III': {
        'doi': '10.1038/sdata.2016.35',
        'openalex_id': None,
        'launch_year': 2016,
    },
    'MIMIC-IV': {
        'doi': '10.1038/s41597-022-01899-x',
        'openalex_id': None,
        'launch_year': 2022,
    },
    'UK-Biobank': {
        'doi': '10.1371/journal.pmed.1001779',
        'openalex_id': None,
        'launch_year': 2015,
    },
    'OpenSAFELY': {
        'doi': '10.1038/s41586-020-2521-4',
        'openalex_id': None,
        'launch_year': 2020,
    },
    'All-of-Us': {
        'doi': '10.1056/NEJMsr1809937',
        'openalex_id': None,
        'launch_year': 2018,
    },
}


# =============================================================================
# API FUNCTIONS
# =============================================================================

def get_work_by_doi(doi: str) -> dict:
    """
    Get OpenAlex work record by DOI.
    
    Args:
        doi: DOI string (e.g., '10.1038/sdata.2016.35')
    
    Returns:
        OpenAlex work object
    """
    url = f"{OPENALEX_BASE}/works/doi:{doi}"
    headers = {"User-Agent": USER_AGENT}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()


def get_citing_works(openalex_id: str, per_page: int = 200, max_results: int = None, 
                     output_format: str = "json") -> list:
    """
    Get all works that cite a given work.
    
    Args:
        openalex_id: OpenAlex ID (e.g., 'W2125098916')
        per_page: Results per page (max 200)
        max_results: Maximum total results (None for all)
        output_format: 'json' for full data, 'csv' for limited fields
    
    Returns:
        List of work objects
    """
    all_works = []
    cursor = "*"
    page = 1
    
    # Request more fields for JSON format
    if output_format == "json":
        # Full set of fields for comprehensive analysis
        select_fields = ",".join([
            "id", "doi", "title", "publication_year", "publication_date",
            "cited_by_count", "type", "language", "is_retracted",
            "authorships", "primary_location", "open_access",
            "topics", "keywords", "mesh", "fwci", "funders",
        ])
    else:
        select_fields = "id,doi,title,publication_year,cited_by_count,authorships,primary_location"
    
    while True:
        url = f"{OPENALEX_BASE}/works"
        params = {
            "filter": f"cites:{openalex_id}",
            "per-page": per_page,
            "cursor": cursor,
            "select": select_fields,
        }
        headers = {"User-Agent": USER_AGENT}
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        if not results:
            break
        
        all_works.extend(results)
        print(f"  Page {page}: fetched {len(results)} works (total: {len(all_works)})")
        
        if max_results and len(all_works) >= max_results:
            all_works = all_works[:max_results]
            break
        
        # Get next cursor
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        
        page += 1
        time.sleep(0.1)  # Be polite
    
    return all_works


# =============================================================================
# JSON PROCESSING FUNCTIONS
# =============================================================================

def process_author_json(authorship: dict, position: int) -> dict:
    """
    Process an authorship record into JSON structure with all institutions.
    
    Args:
        authorship: OpenAlex authorship object
        position: Author position (1-indexed)
    
    Returns:
        Dictionary with full author details
    """
    author = authorship.get("author", {}) or {}
    institutions = authorship.get("institutions", []) or []
    
    # Process all institutions with full details
    inst_list = []
    for inst in institutions:
        inst_list.append({
            "id": inst.get("id", ""),
            "name": inst.get("display_name", ""),
            "country": inst.get("country_code", ""),
            "type": inst.get("type", ""),
            "ror": inst.get("ror", ""),
            "lineage": inst.get("lineage", []),
        })
    
    return {
        "id": author.get("id", ""),
        "name": author.get("display_name", ""),
        "raw_name": authorship.get("raw_author_name", ""),
        "orcid": author.get("orcid", ""),
        "position": position,
        "position_type": authorship.get("author_position", ""),  # "first", "middle", "last"
        "is_corresponding": authorship.get("is_corresponding", False),
        "countries": authorship.get("countries", []),  # Direct country list from authorship
        "raw_affiliation_strings": authorship.get("raw_affiliation_strings", []),
        "institutions": inst_list,
    }


def process_work_json(work: dict) -> dict:
    """
    Process a single work into JSON structure.
    
    Args:
        work: OpenAlex work object
    
    Returns:
        Dictionary with paper and nested author data
    """
    # Get journal/source info
    primary_location = work.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}
    
    # Get open access info
    open_access = work.get("open_access", {}) or {}
    
    # Process topics (new OpenAlex topic system)
    topics = []
    for topic in (work.get("topics", []) or []):
        topics.append({
            "id": topic.get("id", ""),
            "name": topic.get("display_name", ""),
            "score": topic.get("score", 0),
            "subfield": topic.get("subfield", {}).get("display_name", "") if topic.get("subfield") else "",
            "field": topic.get("field", {}).get("display_name", "") if topic.get("field") else "",
            "domain": topic.get("domain", {}).get("display_name", "") if topic.get("domain") else "",
        })
    
    # Process keywords
    keywords = []
    for kw in (work.get("keywords", []) or []):
        keywords.append({
            "keyword": kw.get("keyword", "") if isinstance(kw, dict) else kw,
            "score": kw.get("score", 0) if isinstance(kw, dict) else 0,
        })
    
    # Process MeSH terms (Medical Subject Headings)
    mesh_terms = []
    for mesh in (work.get("mesh", []) or []):
        mesh_terms.append({
            "descriptor_ui": mesh.get("descriptor_ui", ""),
            "descriptor_name": mesh.get("descriptor_name", ""),
            "qualifier_ui": mesh.get("qualifier_ui", ""),
            "qualifier_name": mesh.get("qualifier_name", ""),
            "is_major_topic": mesh.get("is_major_topic", False),
        })
    
    # Process funders
    funders = []
    for funder in (work.get("funders", []) or []):
        funders.append({
            "id": funder.get("id", ""),
            "name": funder.get("display_name", ""),
            "country": funder.get("country_code", ""),
            "award_id": funder.get("award_id", ""),
        })
    
    # Process authors
    authorships = work.get("authorships", []) or []
    authors = []
    for i, authorship in enumerate(authorships):
        author_data = process_author_json(authorship, position=i + 1)
        authors.append(author_data)
    
    return {
        "id": work.get("id", ""),
        "doi": work.get("doi", ""),
        "title": work.get("title", ""),
        "year": work.get("publication_year"),
        "publication_date": work.get("publication_date", ""),
        "cited_by_count": work.get("cited_by_count", 0),
        "type": work.get("type", ""),
        "language": work.get("language", ""),
        "is_retracted": work.get("is_retracted", False),
        "fwci": work.get("fwci"),  # Field-Weighted Citation Impact
        "journal": source.get("display_name", ""),
        "journal_id": source.get("id", ""),
        "open_access": {
            "is_oa": open_access.get("is_oa", False),
            "oa_status": open_access.get("oa_status", ""),
        },
        "topics": topics,
        "keywords": keywords,
        "mesh": mesh_terms,
        "funders": funders,
        "authors": authors,
    }


def fetch_dataset_json(dataset_name: str, max_results: int = None) -> dict:
    """
    Fetch all citing papers for a dataset and return as JSON structure.
    
    Args:
        dataset_name: Name of dataset (must be in DATASETS)
        max_results: Max papers to fetch (None for all)
    
    Returns:
        Dictionary with full dataset citation data
    """
    if dataset_name not in DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_name}")
    
    config = DATASETS[dataset_name]
    doi = config["doi"]
    
    print(f"\n{'='*60}")
    print(f"Fetching: {dataset_name}")
    print(f"DOI: {doi}")
    print(f"{'='*60}")
    
    # Get the work
    print("\n1. Looking up work in OpenAlex...")
    work = get_work_by_doi(doi)
    openalex_id = work["id"]
    cited_by = work.get("cited_by_count", 0)
    print(f"   OpenAlex ID: {openalex_id}")
    print(f"   Cited by: {cited_by} works")
    
    # Get citing works
    print(f"\n2. Fetching citing works...")
    citing_works = get_citing_works(openalex_id, max_results=max_results, output_format="json")
    print(f"   Retrieved: {len(citing_works)} works")
    
    # Process into JSON structure
    print(f"\n3. Processing papers...")
    papers = []
    total_authors = 0
    for raw_work in citing_works:
        paper = process_work_json(raw_work)
        papers.append(paper)
        total_authors += len(paper["authors"])
    
    print(f"   Total papers: {len(papers)}")
    print(f"   Total author records: {total_authors}")
    
    # Build output structure
    output = {
        "dataset": dataset_name,
        "source_doi": doi,
        "source_openalex_id": openalex_id,
        "launch_year": config["launch_year"],
        "fetched_at": datetime.now().isoformat(),
        "total_papers": len(papers),
        "total_author_records": total_authors,
        "papers": papers,
    }
    
    # Save to JSON
    output_file = CITING_PAPERS_DIR / f"{dataset_name.lower()}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n4. Saved to: {output_file}")
    
    return output


def fetch_all_datasets_json(max_results: int = None):
    """
    Fetch citing papers for all datasets as JSON.
    
    Args:
        max_results: Max papers per dataset (None for all)
    """
    summary = []
    
    for dataset_name in DATASETS:
        try:
            data = fetch_dataset_json(dataset_name, max_results=max_results)
            
            # Count unique countries across all papers
            countries = set()
            for paper in data["papers"]:
                for author in paper["authors"]:
                    for inst in author["institutions"]:
                        if inst["country"]:
                            countries.add(inst["country"])
            
            summary.append({
                "dataset": dataset_name,
                "papers": data["total_papers"],
                "author_records": data["total_author_records"],
                "countries": len(countries),
                "fetch_time": data["fetched_at"],
            })
            
            time.sleep(1)  # Be polite between datasets
            
        except Exception as e:
            print(f"ERROR fetching {dataset_name}: {e}")
            import traceback
            traceback.print_exc()
            summary.append({
                "dataset": dataset_name,
                "papers": 0,
                "error": str(e),
                "fetch_time": datetime.now().isoformat(),
            })
    
    # Save summary
    summary_file = DATA_DIR / "fetch_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY saved to: {summary_file}")
    print(f"{'='*60}")
    for s in summary:
        print(f"  {s['dataset']}: {s.get('papers', 0)} papers, {s.get('author_records', 0)} authors")


# =============================================================================
# CSV PROCESSING FUNCTIONS (Legacy)
# =============================================================================

def extract_author_info(authorship: dict) -> dict:
    """
    Extract author information from an authorship record (CSV format - primary institution only).
    
    Args:
        authorship: OpenAlex authorship object
    
    Returns:
        Dictionary with author details
    """
    author = authorship.get("author", {})
    institutions = authorship.get("institutions", [])
    
    # Get primary institution
    primary_inst = institutions[0] if institutions else {}
    
    return {
        "author_id": author.get("id", ""),
        "author_name": author.get("display_name", ""),
        "author_orcid": author.get("orcid", ""),
        "institution_id": primary_inst.get("id", ""),
        "institution_name": primary_inst.get("display_name", ""),
        "institution_country": primary_inst.get("country_code", ""),
        "institution_type": primary_inst.get("type", ""),
    }


def process_work(work: dict, dataset_name: str) -> list:
    """
    Process a single work into author-level records (CSV format).
    
    Args:
        work: OpenAlex work object
        dataset_name: Name of the dataset being analyzed
    
    Returns:
        List of author records (one per author)
    """
    records = []
    
    work_info = {
        "dataset": dataset_name,
        "work_id": work.get("id", ""),
        "doi": work.get("doi", ""),
        "title": work.get("title", ""),
        "year": work.get("publication_year", ""),
        "cited_by_count": work.get("cited_by_count", 0),
    }
    
    # Get journal/source info
    primary_location = work.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}
    work_info["journal"] = source.get("display_name", "")
    
    # Process each author
    authorships = work.get("authorships", [])
    for i, authorship in enumerate(authorships):
        author_info = extract_author_info(authorship)
        author_info["author_position"] = i + 1
        author_info["total_authors"] = len(authorships)
        
        record = {**work_info, **author_info}
        records.append(record)
    
    return records


def fetch_dataset_csv(dataset_name: str, max_results: int = None) -> pd.DataFrame:
    """
    Fetch all citing papers for a dataset (CSV format).
    
    Args:
        dataset_name: Name of dataset (must be in DATASETS)
        max_results: Max papers to fetch (None for all)
    
    Returns:
        DataFrame with all author-paper records
    """
    if dataset_name not in DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_name}")
    
    config = DATASETS[dataset_name]
    doi = config["doi"]
    
    print(f"\n{'='*60}")
    print(f"Fetching: {dataset_name}")
    print(f"DOI: {doi}")
    print(f"{'='*60}")
    
    # Get the work
    print("\n1. Looking up work in OpenAlex...")
    work = get_work_by_doi(doi)
    openalex_id = work["id"]
    cited_by = work.get("cited_by_count", 0)
    print(f"   OpenAlex ID: {openalex_id}")
    print(f"   Cited by: {cited_by} works")
    
    # Get citing works
    print(f"\n2. Fetching citing works...")
    citing_works = get_citing_works(openalex_id, max_results=max_results, output_format="csv")
    print(f"   Retrieved: {len(citing_works)} works")
    
    # Process into records
    print(f"\n3. Processing author records...")
    all_records = []
    for work in citing_works:
        records = process_work(work, dataset_name)
        all_records.extend(records)
    print(f"   Total author records: {len(all_records)}")
    
    # Create DataFrame
    df = pd.DataFrame(all_records)
    
    # Save to CSV
    output_file = CITING_PAPERS_DIR / f"{dataset_name.lower()}_citing_papers.csv"
    df.to_csv(output_file, index=False)
    print(f"\n4. Saved to: {output_file}")
    
    return df


def fetch_all_datasets_csv(max_results: int = None):
    """
    Fetch citing papers for all datasets (CSV format).
    
    Args:
        max_results: Max papers per dataset (None for all)
    """
    summary = []
    
    for dataset_name in DATASETS:
        try:
            df = fetch_dataset_csv(dataset_name, max_results=max_results)
            
            # Calculate summary stats
            n_papers = df["work_id"].nunique()
            n_authors = df["author_id"].nunique()
            n_countries = df["institution_country"].nunique()
            
            summary.append({
                "dataset": dataset_name,
                "papers": n_papers,
                "author_records": len(df),
                "unique_authors": n_authors,
                "countries": n_countries,
                "fetch_time": datetime.now().isoformat(),
            })
            
            time.sleep(1)  # Be polite between datasets
            
        except Exception as e:
            print(f"ERROR fetching {dataset_name}: {e}")
            summary.append({
                "dataset": dataset_name,
                "papers": 0,
                "error": str(e),
                "fetch_time": datetime.now().isoformat(),
            })
    
    # Save summary
    summary_df = pd.DataFrame(summary)
    summary_file = DATA_DIR / "fetch_summary.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"\n{'='*60}")
    print(f"SUMMARY saved to: {summary_file}")
    print(f"{'='*60}")
    print(summary_df.to_string(index=False))


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Fetch citing papers from OpenAlex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dataset", "-d",
        type=str,
        help="Fetch specific dataset only",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: fetch only 25 papers per dataset",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum papers to fetch per dataset",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "csv"],
        default="json",
        help="Output format: json (default, full data) or csv (legacy, flattened)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available datasets",
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("\nAvailable datasets:")
        for name, config in DATASETS.items():
            print(f"  {name}: {config['doi']} (launched {config['launch_year']})")
        return
    
    max_results = 25 if args.test else args.max
    
    if args.format == "json":
        if args.dataset:
            fetch_dataset_json(args.dataset, max_results=max_results)
        else:
            fetch_all_datasets_json(max_results=max_results)
    else:
        if args.dataset:
            fetch_dataset_csv(args.dataset, max_results=max_results)
        else:
            fetch_all_datasets_csv(max_results=max_results)


if __name__ == "__main__":
    main()
