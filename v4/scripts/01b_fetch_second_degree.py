#!/usr/bin/env python3
"""
01b - Fetch Second-Degree Citations (Ripple Effect)

Produces the ground-truth second-degree data: data/second_degree/<dataset>.json.gz
(all-of-us, mimic-i, mimic-ii, mimic-iii, mimic-iv, opensafely, uk-biobank).
All second-degree analyses use only these .json.gz files; no other outputs.

For each first-degree citing paper (from data/citing_papers/), fetches papers
that cite IT but do NOT mention the original dataset in their abstract.
These represent the invisible downstream influence of the datasets.

Concurrency: uses a thread pool + token-bucket rate limiter to sustain ~90 req/s
against the OpenAlex API (100 req/s limit with API key).

Checkpointing: progress is saved per-paper so long runs can be resumed.

Usage:
    python 01b_fetch_second_degree.py                         # All datasets (skips if output exists)
    python 01b_fetch_second_degree.py --dataset mimic-iii     # One dataset
    python 01b_fetch_second_degree.py --test                  # 10 first-degree papers each
    python 01b_fetch_second_degree.py --resume                # Resume interrupted run
    python 01b_fetch_second_degree.py --force                # Re-run even when output exists
    python 01b_fetch_second_degree.py --max-first-degree 100  # Cap first-degree papers
"""

import argparse
import gzip
import json
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CITING_DIR = DATA_DIR / "citing_papers"
SECOND_DIR = DATA_DIR / "second_degree"
CHECKPOINT_DIR = SECOND_DIR / "_checkpoints"

SECOND_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# OpenAlex configuration
# ---------------------------------------------------------------------------
OPENALEX_BASE = "https://api.openalex.org"


def _load_api_keys():
    """Load API keys from .env file (OPENALEX_KEYS=key1:email1,key2:email2,...)."""
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("OPENALEX_KEYS="):
                raw = line.split("=", 1)[1]
                return [
                    {"api_key": pair.split(":")[0], "email": pair.split(":")[1]}
                    for pair in raw.split(",") if ":" in pair
                ]
    env_val = os.environ.get("OPENALEX_KEYS", "")
    if env_val:
        return [
            {"api_key": pair.split(":")[0], "email": pair.split(":")[1]}
            for pair in env_val.split(",") if ":" in pair
        ]
    raise RuntimeError("No API keys found. Set OPENALEX_KEYS in .env or environment.")


OPENALEX_KEYS = _load_api_keys()
_key_lock = threading.Lock()
_current_key_index = 0

TARGET_RPS = 90  # requests per second
WORKERS = 15     # concurrent threads (~90 rps / ~6 rps per thread ≈ 15)

# Select fields for second-degree papers
SELECT_FIELDS = ",".join([
    "id", "doi", "title", "publication_year", "cited_by_count",
    "type", "language", "abstract_inverted_index", "primary_location",
])

# ---------------------------------------------------------------------------
# Dataset name → terms to search in abstracts
# ---------------------------------------------------------------------------
DATASET_TERMS = {
    "mimic-i":    ["MIMIC", "Medical Information Mart for Intensive Care"],
    "mimic-ii":   ["MIMIC", "Medical Information Mart for Intensive Care"],
    "mimic-iii":  ["MIMIC", "Medical Information Mart for Intensive Care"],
    "mimic-iv":   ["MIMIC", "Medical Information Mart for Intensive Care"],
    "uk-biobank": ["UK Biobank", "UK-Biobank", "United Kingdom Biobank"],
    "opensafely": ["OpenSAFELY"],
    "all-of-us":  ["All of Us", "All-of-Us"],
}

DATASET_NAMES = list(DATASET_TERMS.keys())


# ===========================================================================
# Token-bucket rate limiter (thread-safe)
# ===========================================================================

class RateLimiter:
    """Token-bucket rate limiter. Call .acquire() before each request."""

    def __init__(self, rate: float):
        self._rate = rate            # tokens per second
        self._tokens = rate          # start full
        self._max = rate             # bucket capacity = 1 second burst
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self):
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self._max, self._tokens + elapsed * self._rate)
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                # How long until a token is available
                wait = (1.0 - self._tokens) / self._rate
            time.sleep(wait)


# Global rate limiter — initialised in main()
_limiter: RateLimiter = None


def _get_current_key() -> str:
    """Thread-safe: return the API key currently in use."""
    with _key_lock:
        return OPENALEX_KEYS[_current_key_index]["api_key"]


def _get_current_user_agent() -> str:
    """Thread-safe: User-Agent (mailto) for the current API key."""
    with _key_lock:
        email = OPENALEX_KEYS[_current_key_index]["email"]
    return f"CitationAnalysis/1.0 (mailto:{email})"


def _rotate_key():
    """Switch to the next API key (on rate limit or budget low)."""
    global _current_key_index
    with _key_lock:
        old = _current_key_index
        _current_key_index = (_current_key_index + 1) % len(OPENALEX_KEYS)
        print(f"    Rotating to next API key (#{old + 1} -> #{_current_key_index + 1})")


# ===========================================================================
# Helper functions
# ===========================================================================

def reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct plain-text abstract from OpenAlex abstract_inverted_index."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)


def mentions_dataset(abstract: str, dataset_name: str) -> bool:
    """Return True if the abstract mentions the dataset (case-insensitive)."""
    if not abstract:
        return False  # No abstract → conservative: keep the paper
    terms = DATASET_TERMS.get(dataset_name, [])
    abstract_lower = abstract.lower()
    for term in terms:
        if term.lower() in abstract_lower:
            return True
    return False


def citing_papers_file_exists(dataset_name: str) -> bool:
    """True if data/citing_papers/{dataset_name}.json or .json.gz exists."""
    return (CITING_DIR / f"{dataset_name}.json").exists() or (CITING_DIR / f"{dataset_name}.json.gz").exists()


def load_first_degree_papers(dataset_name: str) -> list:
    """Load first-degree papers from data/citing_papers/."""
    json_path = CITING_DIR / f"{dataset_name}.json"
    gz_path = CITING_DIR / f"{dataset_name}.json.gz"

    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif gz_path.exists():
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raise FileNotFoundError(f"No citing papers file for {dataset_name}")

    return data.get("papers", [])


# Shared requests.Session per thread for connection pooling
_session_local = threading.local()


def _get_session() -> requests.Session:
    """Return a thread-local requests.Session with connection pooling."""
    if not hasattr(_session_local, "session"):
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=WORKERS,
            pool_maxsize=WORKERS,
            max_retries=0,  # we handle retries ourselves
        )
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _session_local.session = s
    return _session_local.session


_budget_lock = threading.Lock()
_budget_depleted = False


def _check_budget(resp):
    """If daily budget nearly exhausted: switch to next key if available, else pause until reset."""
    global _budget_depleted
    remaining = resp.headers.get("X-RateLimit-Remaining")
    reset_in = resp.headers.get("X-RateLimit-Reset")
    if remaining is None:
        return
    remaining = int(remaining)
    if remaining > 50:
        return
    if len(OPENALEX_KEYS) > 1:
        _rotate_key()
        return
    with _budget_lock:
        if _budget_depleted:
            return
        _budget_depleted = True
    wait = int(reset_in) + 5 if reset_in else 3600
    print(f"\n  *** Budget nearly exhausted ({remaining} left). "
          f"Pausing {wait}s until reset... ***\n")
    time.sleep(wait)
    with _budget_lock:
        _budget_depleted = False


def api_request_with_retry(url: str, params: dict, max_retries: int = 5) -> dict:
    """Rate-limited request; on 429 or low budget, rotate to next API key if available."""
    session = _get_session()

    for attempt in range(max_retries):
        _limiter.acquire()
        req_params = {**params, "api_key": _get_current_key()}
        try:
            resp = session.get(
                url, params=req_params,
                headers={"User-Agent": _get_current_user_agent()},
                timeout=30,
            )
            if resp.status_code == 200:
                _check_budget(resp)
                return resp.json()
            if resp.status_code == 429:
                if len(OPENALEX_KEYS) > 1:
                    _rotate_key()
                else:
                    wait = min(2 ** attempt * 2, 60)
                    print(f"    Rate limited (429), waiting {wait}s...")
                    time.sleep(wait)
                continue
            if resp.status_code == 503:
                wait = min(2 ** attempt * 2, 60)
                print(f"    Server 503, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            wait = min(2 ** attempt * 2, 60)
            print(f"    Timeout, waiting {wait}s...")
            time.sleep(wait)
            continue
        except requests.exceptions.ConnectionError:
            wait = min(2 ** attempt * 2, 60)
            print(f"    Connection error, waiting {wait}s...")
            time.sleep(wait)
            continue

    raise RuntimeError(f"Failed after {max_retries} retries: {url}")


def fetch_citing_papers(openalex_id: str) -> list:
    """Fetch all papers citing a given OpenAlex work (page-based pagination, 200/page)."""
    short_id = openalex_id
    if "/" in short_id:
        short_id = short_id.rsplit("/", 1)[-1]

    all_works = []
    page = 1

    while True:
        params = {
            "filter": f"cites:{short_id}",
            "per-page": 200,
            "page": page,
            "select": SELECT_FIELDS,
        }
        data = api_request_with_retry(f"{OPENALEX_BASE}/works", params)
        if not isinstance(data, dict) or "results" not in data:
            raise ValueError("Invalid API response: missing or invalid 'results'")
        results = data.get("results", [])
        if not results:
            break
        all_works.extend(results)

        # Check if we've fetched all results
        total_count = data.get("meta", {}).get("count", 0)
        if len(all_works) >= total_count:
            break
        page += 1

    return all_works


def process_paper_for_output(work: dict, abstract: str) -> dict:
    """Extract the output fields from a raw OpenAlex work."""
    primary_location = work.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}

    return {
        "id": work.get("id", ""),
        "doi": work.get("doi", ""),
        "title": work.get("title", ""),
        "abstract": abstract,
        "cited_by_count": work.get("cited_by_count", 0),
        "year": work.get("publication_year"),
        "type": work.get("type", ""),
        "language": work.get("language", ""),
        "journal": source.get("display_name", ""),
    }


# ===========================================================================
# Checkpoint helpers (thread-safe)
# ===========================================================================

_checkpoint_lock = threading.Lock()


def load_done_set(dataset_name: str) -> set:
    """Load the set of already-processed first-degree paper IDs."""
    done_file = CHECKPOINT_DIR / f"{dataset_name}_done.txt"
    if not done_file.exists():
        return set()
    return set(done_file.read_text().splitlines())


def append_checkpoint(dataset_name: str, paper_id: str, kept_papers: list):
    """Atomically append kept papers to JSONL and mark first-degree paper as done."""
    with _checkpoint_lock:
        if kept_papers:
            jsonl_file = CHECKPOINT_DIR / f"{dataset_name}_papers.jsonl"
            with open(jsonl_file, "a", encoding="utf-8") as f:
                for p in kept_papers:
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
        done_file = CHECKPOINT_DIR / f"{dataset_name}_done.txt"
        with open(done_file, "a") as f:
            f.write(paper_id + "\n")


# ===========================================================================
# Per-paper worker (runs in thread pool)
# ===========================================================================

def _process_one_paper(first_paper: dict, dataset_name: str) -> tuple:
    """Fetch citers for one first-degree paper, filter, checkpoint.

    Returns (raw_count, filtered_count, kept_count, failed_paper_or_None).
    On failure (API error / invalid response), does NOT checkpoint; returns failed paper for retry.
    """
    first_id = first_paper.get("id", "")

    try:
        citers = fetch_citing_papers(first_id)
    except Exception as e:
        print(f"    ERROR fetching citers for {first_id}: {e}")
        return (0, 0, 0, first_paper)

    raw_count = len(citers)
    kept = []
    filtered = 0
    for citer in citers:
        abstract_idx = citer.get("abstract_inverted_index")
        abstract = reconstruct_abstract(abstract_idx)
        if mentions_dataset(abstract, dataset_name):
            filtered += 1
            continue
        kept.append(process_paper_for_output(citer, abstract))

    append_checkpoint(dataset_name, first_id, kept)
    return (raw_count, filtered, len(kept), None)


# ===========================================================================
# Interrupt handling (checkpoint is per-paper; resume with --resume)
# ===========================================================================

_shutdown_requested = False


def _interrupt_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    raise KeyboardInterrupt()


# ===========================================================================
# Main processing
# ===========================================================================

_progress_lock = threading.Lock()


def process_dataset(dataset_name: str, resume: bool = False,
                    test: bool = False, max_first_degree: int = None):
    """Process one dataset: fetch second-degree citations with filtering."""
    global _shutdown_requested
    _shutdown_requested = False

    print(f"\n{'='*60}")
    print(f"Dataset: {dataset_name}")
    print(f"{'='*60}")

    # Load first-degree papers
    papers = load_first_degree_papers(dataset_name)
    print(f"  Total first-degree papers: {len(papers)}")

    # Filter to papers with citations, sort ascending by cited_by_count
    papers = [p for p in papers if p.get("cited_by_count", 0) > 0]
    papers.sort(key=lambda p: p.get("cited_by_count", 0))
    print(f"  With cited_by_count > 0: {len(papers)}")

    if test:
        papers = papers[:10]
        print(f"  TEST MODE: limited to {len(papers)} papers")

    if max_first_degree:
        papers = papers[:max_first_degree]
        print(f"  Limited to {len(papers)} first-degree papers")

    # Load checkpoint if resuming
    done_set = set()
    if resume:
        done_set = load_done_set(dataset_name)
        print(f"  Resuming: {len(done_set)} papers already processed")
    else:
        done_file = CHECKPOINT_DIR / f"{dataset_name}_done.txt"
        jsonl_file = CHECKPOINT_DIR / f"{dataset_name}_papers.jsonl"
        if done_file.exists():
            done_file.unlink()
        if jsonl_file.exists():
            jsonl_file.unlink()

    # Filter out already-done papers
    todo = [p for p in papers if p.get("id", "") not in done_set]
    total_first = len(papers)
    print(f"  To process: {len(todo)} papers ({WORKERS} threads, {TARGET_RPS} req/s)")

    t0 = time.monotonic()
    completed = len(papers) - len(todo)  # already done count
    total_raw = 0
    total_filtered = 0
    total_kept = 0
    failed_papers = []

    old_sigint = signal.signal(signal.SIGINT, _interrupt_handler)
    old_sigterm = signal.signal(signal.SIGTERM, _interrupt_handler)
    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            future_to_paper = {
                pool.submit(_process_one_paper, paper, dataset_name): paper
                for paper in todo
            }
            pbar = tqdm(
                total=total_first,
                initial=completed,
                unit="paper",
                desc=f"  {dataset_name}",
                dynamic_ncols=True,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            )
            try:
                while True:
                    try:
                        for future in as_completed(future_to_paper, timeout=2):
                            if _shutdown_requested:
                                for f in future_to_paper:
                                    f.cancel()
                                break
                            result = future.result()
                            if result is None:
                                completed += 1
                                pbar.update(1)
                                continue
                            raw, filt, kept, failed = result
                            if failed is not None:
                                failed_papers.append(failed)
                            else:
                                total_raw += raw
                                total_filtered += filt
                                total_kept += kept
                            completed += 1
                            pbar.update(1)
                            elapsed = time.monotonic() - t0
                            rps = total_raw / elapsed if elapsed > 0 else 0
                            pbar.set_postfix(raw=total_raw, filtered=total_filtered, kept=total_kept, rps=f"{rps:.0f}")
                        break  # normal completion
                    except TimeoutError:
                        if _shutdown_requested:
                            for f in future_to_paper:
                                f.cancel()
                            break
                    except KeyboardInterrupt:
                        _shutdown_requested = True
                        for f in future_to_paper:
                            f.cancel()
                        break
            finally:
                pbar.close()
    finally:
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)

    if _shutdown_requested:
        print("\n  *** Interrupted (Ctrl+C or SIGTERM). Progress checkpointed. ***")
        print("  Run with --resume to continue from where you left off.\n")
        finalize_dataset(dataset_name, total_first, total_raw, total_filtered)
        sys.exit(0)

    elapsed = time.monotonic() - t0
    print(f"\n  Done fetching in {elapsed:.0f}s. "
          f"Raw: {total_raw}, Filtered: {total_filtered}, Kept: {total_kept}")

    # Save failed IDs and retry at end
    if failed_papers:
        failed_file = CHECKPOINT_DIR / f"{dataset_name}_failed.txt"
        failed_file.write_text("\n".join(p.get("id", "") for p in failed_papers if p.get("id")), encoding="utf-8")
        print(f"  Saved {len(failed_papers)} failed paper IDs to {failed_file.name}; retrying...")
        still_failed = []
        for paper in failed_papers:
            try:
                result = _process_one_paper(paper, dataset_name)
                raw, filt, kept, failed = result
                if failed is not None:
                    still_failed.append(paper)
                else:
                    total_raw += raw
                    total_filtered += filt
                    total_kept += kept
            except Exception as e:
                print(f"    Retry ERROR for {paper.get('id', '')}: {e}")
                still_failed.append(paper)
        if still_failed:
            failed_file.write_text("\n".join(p.get("id", "") for p in still_failed if p.get("id")), encoding="utf-8")
            print(f"  After retry: {len(still_failed)} papers still failed (see {failed_file.name})")
        else:
            if failed_file.exists():
                failed_file.unlink()
            print("  All retried papers succeeded.")

    finalize_dataset(dataset_name, total_first, total_raw, total_filtered)


def finalize_dataset(dataset_name: str, total_first_queried: int,
                     total_raw: int, total_filtered: int):
    """Read JSONL checkpoint, deduplicate by ID, write final .json.gz."""
    jsonl_file = CHECKPOINT_DIR / f"{dataset_name}_papers.jsonl"

    papers = []
    seen_ids = set()

    if jsonl_file.exists():
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                p = json.loads(line)
                pid = p.get("id", "")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    papers.append(p)

    print(f"  After dedup: {len(papers)} unique second-degree papers")

    output = {
        "dataset": dataset_name,
        "fetched_at": datetime.now().isoformat(),
        "total_first_degree_queried": total_first_queried,
        "total_second_degree_raw": total_raw,
        "total_filtered_by_abstract": total_filtered,
        "total_papers": len(papers),
        "papers": papers,
    }

    out_path = SECOND_DIR / f"{dataset_name}.json.gz"
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"  Saved: {out_path} ({size_mb:.1f} MB)")


# ===========================================================================
# CLI
# ===========================================================================

def main():
    global _limiter
    _limiter = RateLimiter(TARGET_RPS)

    parser = argparse.ArgumentParser(
        description="Fetch second-degree citations (ripple effect)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dataset", "-d",
        type=str,
        help=f"Fetch specific dataset only. Options: {', '.join(DATASET_NAMES)}",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: process only 10 first-degree papers per dataset",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint (skip already-processed papers)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh (wipe checkpoints for datasets to be run)",
    )
    parser.add_argument(
        "--max-first-degree",
        type=int,
        default=None,
        help="Maximum number of first-degree papers to process per dataset",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if final output already exists (default: skip completed datasets)",
    )

    args = parser.parse_args()
    if args.resume and args.no_resume:
        print("Cannot use both --resume and --no-resume.")
        sys.exit(1)

    datasets = [args.dataset] if args.dataset else DATASET_NAMES
    to_run = []
    for ds in datasets:
        ds = ds.lower()
        if ds not in DATASET_TERMS:
            print(f"Unknown dataset: {ds}. Options: {', '.join(DATASET_NAMES)}")
            continue
        if not citing_papers_file_exists(ds):
            print(f"Skipping {ds}: no citing papers file in {CITING_DIR}")
            continue
        out_file = SECOND_DIR / f"{ds}.json.gz"
        if out_file.exists() and not args.force:
            print(f"Skipping {ds}: already completed ({out_file.name} exists). Use --force to re-run.")
            continue
        to_run.append(ds)

    # Resolve resume: explicit flag, or prompt when checkpoints exist
    resume = None
    if args.resume:
        resume = True
    elif args.no_resume:
        resume = False
    else:
        has_checkpoint = any(
            (CHECKPOINT_DIR / f"{ds}_done.txt").exists() for ds in to_run
        )
        if has_checkpoint:
            try:
                answer = input("Resume from existing checkpoint(s)? [Y/n] ").strip().lower()
                resume = answer != "n" and answer != "no"
            except (EOFError, KeyboardInterrupt):
                resume = True  # default to resume if non-interactive
        else:
            resume = False

    for ds in to_run:
        process_dataset(ds, resume=resume, test=args.test,
                        max_first_degree=args.max_first_degree)

    print(f"\n{'='*60}")
    print("All done!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
