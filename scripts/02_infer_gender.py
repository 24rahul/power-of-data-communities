#!/usr/bin/env python3
"""
02 - Infer Author Gender using Genderize.io

Uses the genderize.io API to infer gender from first names.
With API key for higher rate limits.

Features:
- Works with JSON data files (preserves nested structure)
- Caches all results to avoid repeated API calls
- Checkpoints every 100 batches
- Logs all API calls for reproducibility

Usage:
    python 02_infer_gender.py
    python 02_infer_gender.py --test  # Only process 100 names
"""

import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path
import requests

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CITING_PAPERS_DIR = DATA_DIR / "citing_papers"
AUTHORS_DIR = DATA_DIR / "authors"
LOGS_DIR = SCRIPT_DIR.parent / "logs"
AUTHORS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Cache file for gender lookups
GENDER_CACHE_FILE = AUTHORS_DIR / "gender_cache.json"

# Genderize.io configuration
GENDERIZE_URL = "https://api.genderize.io"
GENDERIZE_API_KEY = "ff8573b1dafc9ecea41145cd405664ad"
BATCH_SIZE = 10  # Max names per request
CHECKPOINT_INTERVAL = 100  # Save cache every N batches

# Setup logging
LOG_FILE = LOGS_DIR / f"gender_inference_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def setup_logging():
    """Setup logging to both file and console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def load_gender_cache() -> dict:
    """Load cached gender results."""
    if GENDER_CACHE_FILE.exists():
        with open(GENDER_CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_gender_cache(cache: dict):
    """Save gender cache to file."""
    with open(GENDER_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def extract_first_name(full_name: str) -> str:
    """
    Extract first name from full name.
    
    Args:
        full_name: Full author name (e.g., "John Smith" or "J. Smith")
    
    Returns:
        First name or empty string if cannot extract
    """
    import unicodedata
    
    if not full_name:
        return ""
    
    # Split and get parts
    parts = full_name.strip().split()
    if not parts:
        return ""
    
    def is_initial(s):
        """Check if string is an initial like 'J', 'J.', 'A-B', etc."""
        s = s.rstrip(".")
        # Single char or single char with hyphen pattern (A-B, Y.-M.)
        if len(s) <= 1:
            return True
        if len(s) <= 4 and '-' in s and all(len(p) <= 1 for p in s.split('-')):
            return True
        return False
    
    # Find first non-initial word (handles "N. M. Anoop Krishnan" -> "Anoop")
    first = None
    for part in parts:
        if not is_initial(part):
            first = part
            break
    
    if first is None:
        return ""  # All parts are initials
    
    # Remove any trailing periods
    first = first.rstrip(".")
    
    # Skip if it's just an initial
    if is_initial(first):
        return ""
    
    # Handle hyphenated names (e.g., "Li-wei", "Jean-Pierre")
    # Normalize various unicode hyphens to regular hyphen
    for hyphen_char in ['‐', '‑', '–', '—', '−']:
        first = first.replace(hyphen_char, '-')
    
    # For hyphenated names, try the first part (e.g., "Li" from "Li-wei")
    # unless it's too short, then use the full hyphenated name
    if '-' in first:
        first_part = first.split('-')[0]
        if len(first_part) >= 2:
            first = first_part
        # else keep the full hyphenated name for genderize
    
    # Skip if it contains numbers
    if any(c.isdigit() for c in first):
        return ""
    
    # Try to normalize accented characters to ASCII (é -> e, ñ -> n, etc.)
    # This helps with names like "José" -> "jose", "François" -> "francois"
    if not first.isascii():
        normalized = unicodedata.normalize('NFKD', first).encode('ASCII', 'ignore').decode('ASCII')
        if len(normalized) >= 2:
            first = normalized
        else:
            # Can't normalize to ASCII (e.g., Chinese/Japanese characters)
            return ""
    
    # Remove any remaining special chars but allow letters and hyphens
    cleaned = ''.join(c for c in first if c.isalpha() or c == '-')
    if not cleaned or len(cleaned) <= 1:
        return ""
    
    return cleaned.lower()


def genderize_batch(names: list, logger) -> dict:
    """
    Query genderize.io for a batch of names.
    
    Args:
        names: List of first names (max 10)
        logger: Logger instance
    
    Returns:
        Dictionary mapping name -> {gender, probability, count}
    """
    if not names:
        return {}
    
    # Build query params
    params = [("name[]", name) for name in names[:BATCH_SIZE]]
    params.append(("apikey", GENDERIZE_API_KEY))
    
    try:
        response = requests.get(GENDERIZE_URL, params=params, timeout=30)
        response.raise_for_status()
        results = response.json()
        
        # Log the API call
        logger.debug(f"API call: {len(names)} names -> {len(results)} results")
        
        return {
            r["name"]: {
                "gender": r.get("gender"),
                "probability": r.get("probability", 0),
                "count": r.get("count", 0),
            }
            for r in results
        }
    except Exception as e:
        logger.error(f"Error querying genderize.io: {e}")
        return {}


def infer_genders(names: list, cache: dict, logger, max_requests: int = None) -> dict:
    """
    Infer genders for a list of names, using cache.
    
    Args:
        names: List of first names
        cache: Existing gender cache
        logger: Logger instance
        max_requests: Maximum API requests to make
    
    Returns:
        Updated cache dictionary
    """
    # Find names not in cache
    unique_names = list(set(n for n in names if n and n not in cache))
    
    logger.info(f"Total unique names: {len(set(n for n in names if n))}")
    logger.info(f"Already cached: {len(set(n for n in names if n)) - len(unique_names)}")
    logger.info(f"Need to lookup: {len(unique_names)}")
    
    if not unique_names:
        return cache
    
    # Batch requests
    requests_made = 0
    max_requests = max_requests or 100000
    
    for i in range(0, len(unique_names), BATCH_SIZE):
        if requests_made >= max_requests:
            logger.warning(f"Reached request limit ({max_requests})")
            break
        
        batch = unique_names[i:i + BATCH_SIZE]
        results = genderize_batch(batch, logger)
        
        # Update cache
        cache.update(results)
        requests_made += 1
        
        # Progress logging
        processed = min(i + BATCH_SIZE, len(unique_names))
        if requests_made % 50 == 0:
            logger.info(f"Progress: {processed}/{len(unique_names)} names ({processed*100//len(unique_names)}%)")
        
        # Checkpoint: save cache periodically
        if requests_made % CHECKPOINT_INTERVAL == 0:
            save_gender_cache(cache)
            logger.info(f"Checkpoint saved: {len(cache)} names in cache")
        
        # Be polite - small delay between requests
        time.sleep(0.1)
    
    # Final save
    save_gender_cache(cache)
    logger.info(f"Final cache saved: {len(cache)} names")
    
    return cache


def collect_names_from_json(json_file: Path, logger) -> set:
    """
    Collect all unique first names from a JSON data file.
    
    Args:
        json_file: Path to JSON file
        logger: Logger instance
    
    Returns:
        Set of unique first names
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    first_names = set()
    for paper in data.get("papers", []):
        for author in paper.get("authors", []):
            name = author.get("name", "")
            first_name = extract_first_name(name)
            if first_name:
                first_names.add(first_name)
    
    logger.info(f"  {len(first_names)} unique first names from {data.get('total_papers', 0)} papers")
    return first_names


def apply_genders_to_json(json_file: Path, cache: dict, output_dir: Path, logger):
    """
    Apply gender labels to all authors in a JSON file.
    
    Args:
        json_file: Input JSON file path
        cache: Gender cache dictionary
        output_dir: Output directory
        logger: Logger instance
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Count statistics
    gender_counts = {"male": 0, "female": 0, "unknown": 0}
    
    # Add gender to each author
    for paper in data.get("papers", []):
        for author in paper.get("authors", []):
            name = author.get("name", "")
            first_name = extract_first_name(name)
            
            if first_name and first_name in cache:
                gender_info = cache[first_name]
                author["gender"] = gender_info.get("gender")
                author["gender_probability"] = gender_info.get("probability", 0)
                author["first_name"] = first_name
                
                # Count
                g = gender_info.get("gender")
                if g == "male":
                    gender_counts["male"] += 1
                elif g == "female":
                    gender_counts["female"] += 1
                else:
                    gender_counts["unknown"] += 1
            else:
                author["gender"] = None
                author["gender_probability"] = 0
                author["first_name"] = first_name
                gender_counts["unknown"] += 1
    
    # Add metadata
    data["gender_inference"] = {
        "inferred_at": datetime.now().isoformat(),
        "cache_size": len(cache),
        "gender_distribution": gender_counts,
    }
    
    # Save to output directory
    output_file = output_dir / json_file.name.replace(".json", "_with_gender.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"  Saved: {output_file.name}")
    logger.info(f"  Gender distribution: male={gender_counts['male']}, female={gender_counts['female']}, unknown={gender_counts['unknown']}")
    
    return gender_counts


def process_all_datasets(cache: dict, logger, max_requests: int = None) -> dict:
    """
    Process all datasets to collect unique names and infer genders.
    
    Args:
        cache: Existing gender cache
        logger: Logger instance
        max_requests: Max API requests
    
    Returns:
        Updated cache
    """
    # Find JSON files (exclude test files and files with _with_gender suffix)
    json_files = [f for f in CITING_PAPERS_DIR.glob("*.json") 
                  if not f.name.endswith("_with_gender.json")]
    
    if not json_files:
        logger.warning("No JSON files found in citing_papers directory!")
        return cache
    
    logger.info("=" * 60)
    logger.info("Phase 1: Collecting unique first names from all datasets")
    logger.info("=" * 60)
    
    # Collect all unique first names
    all_first_names = set()
    for json_file in sorted(json_files):
        logger.info(f"Reading: {json_file.name}")
        names = collect_names_from_json(json_file, logger)
        all_first_names.update(names)
    
    logger.info(f"\nTotal unique first names across all datasets: {len(all_first_names)}")
    
    # Infer genders for all unique names
    logger.info("=" * 60)
    logger.info("Phase 2: Inferring genders via genderize.io API")
    logger.info("=" * 60)
    
    cache = infer_genders(list(all_first_names), cache, logger, max_requests=max_requests)
    
    # Apply genders to each dataset
    logger.info("=" * 60)
    logger.info("Phase 3: Applying gender labels to datasets")
    logger.info("=" * 60)
    
    total_counts = {"male": 0, "female": 0, "unknown": 0}
    for json_file in sorted(json_files):
        logger.info(f"Processing: {json_file.name}")
        counts = apply_genders_to_json(json_file, cache, AUTHORS_DIR, logger)
        for k in total_counts:
            total_counts[k] += counts[k]
    
    logger.info("\n" + "-" * 60)
    logger.info(f"TOTAL across all datasets:")
    logger.info(f"  Male: {total_counts['male']}")
    logger.info(f"  Female: {total_counts['female']}")
    logger.info(f"  Unknown: {total_counts['unknown']}")
    
    return cache


def main():
    parser = argparse.ArgumentParser(description="Infer author genders")
    parser.add_argument("--test", action="store_true", help="Test mode (limit requests)")
    parser.add_argument("--max-requests", type=int, default=10000, help="Max API requests")
    args = parser.parse_args()
    
    max_requests = 10 if args.test else args.max_requests
    
    # Setup logging
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Gender Inference using Genderize.io")
    logger.info("=" * 60)
    logger.info(f"Log file: {LOG_FILE}")
    logger.info(f"Max API requests: {max_requests}")
    logger.info(f"API key: {GENDERIZE_API_KEY[:8]}...")
    
    # Load cache
    cache = load_gender_cache()
    logger.info(f"Loaded cache with {len(cache)} names")
    
    # Process all datasets
    cache = process_all_datasets(cache, logger, max_requests=max_requests)
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total names in cache: {len(cache)}")
    
    # Count genders in cache
    genders = {"male": 0, "female": 0, "unknown": 0}
    for name, data in cache.items():
        g = data.get("gender")
        if g == "male":
            genders["male"] += 1
        elif g == "female":
            genders["female"] += 1
        else:
            genders["unknown"] += 1
    
    logger.info(f"  Male names: {genders['male']}")
    logger.info(f"  Female names: {genders['female']}")
    logger.info(f"  Unknown: {genders['unknown']}")
    logger.info(f"\nCache saved to: {GENDER_CACHE_FILE}")
    logger.info(f"Log saved to: {LOG_FILE}")


if __name__ == "__main__":
    main()
