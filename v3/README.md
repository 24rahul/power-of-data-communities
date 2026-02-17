# Power of Data Communities v3

Clean, well-organized analysis addressing PLOS Digital Health editor feedback.
The original Jupyter notebook has been broken into modular Python scripts.

## Structure

```
v3/
├── data/
│   ├── citations.csv              # Citation data (from data_definitions.py)
│   └── funding.csv                # Funding data with sources
├── scripts/
│   ├── data_definitions.py        # Source data: citations & funding (base module)
│   ├── 02_scrape_google_scholar.py    # Google Scholar scraper (data collection)
│   ├── 03_plot_growth.py          # Longevity-adjusted growth plots
│   ├── 04_plot_funding_normalized.py  # Funding-normalized plots
│   └── 05_h_index_analysis.py     # H-index paper-level analysis
├── figures/                       # Generated figures
└── output/                        # Summary tables
```

## Quick Start

```bash
cd v3/scripts

# 1. View data definitions (source of truth)
python data_definitions.py

# 2. Scrape Google Scholar for new data (use with caution)
python 02_scrape_google_scholar.py --list
python 02_scrape_google_scholar.py --dataset MIMIC-III --test

# 3. Generate longevity-adjusted growth plots
python 03_plot_growth.py

# 4. Generate funding-normalized plots
python 04_plot_funding_normalized.py

# 5. H-index analysis (requires scraped paper-level data)
python 05_h_index_analysis.py
```

## Scripts

### data_definitions.py (Base Module)
Source of truth for all data:
- Citation counts by year (from Google Scholar)
- Funding amounts with sources
- Helper functions for data access

### 02_scrape_google_scholar.py (Data Collection)
Google Scholar citation scraper:
- Supports all configured datasets
- Rate-limited to avoid blocking
- Saves results to CSV

### 03_plot_growth.py (Visualization)
Generates longevity-adjusted citation growth plots:
- Cumulative citations aligned by years since publication
- MIMIC vs closed datasets comparison
- Citation ratio analysis

### 04_plot_funding_normalized.py (Visualization)
Generates funding-normalized plots:
- Citations per $1M funding (log scale)
- Addresses reviewer concern about funding attribution

### 05_h_index_analysis.py (Advanced Analysis)
H-index and paper-level analysis:
- Requires individual paper citation data from scraping
- Multiple visualization options
- Funding-adjusted h-index

## Data Sources

### Citations (from data_definitions.py)
| Dataset | DOI | Start Year |
|---------|-----|------------|
| MIMIC-I | 10.1109/CIC.1996.542622 | 1997 |
| MIMIC-II | 10.1109/CIC.2002.1166854 | 2003 |
| MIMIC-III | 10.1038/sdata.2016.35 | 2016 |
| MIMIC-IV | 10.1038/s41597-022-01899-x | 2022 |
| UK Biobank | 10.1371/journal.pmed.1001779 | 2015 |
| OpenSAFELY | 10.1038/s41586-020-2521-4 | 2019 |
| All of Us | 10.1056/NEJMsr1809937 | 2018 |

### Funding
| Dataset | Funding | Source |
|---------|---------|--------|
| All MIMIC | $14.4M | NIH Reporter |
| UK Biobank | $525.5M | Wellcome Trust/MRC |
| OpenSAFELY | $53.7M | Multiple grants |
| All of Us | $2.16B | NIH |

## Editor Feedback Addressed

1. **Longevity Adjustment**: `02_plot_growth.py` - normalizes for dataset age
2. **Funding Attribution**: `03_plot_funding_normalized.py` - citations per $1M
3. **Consent & Reidentifiability**: To be added in future iteration

## Generated Figures

| Script | Output |
|--------|--------|
| 03_plot_growth.py | `growth_adjusted_MIMIC-together.png`, `citation_ratios_growth.png` |
| 04_plot_funding_normalized.py | `funding_normalized_MIMIC-together_log.png`, `funding_normalized_ratios.png` |
| 05_h_index_analysis.py | `h_index_*.png` (multiple variants) |

## Citation Summary

From `data_definitions.py`:

| Dataset | Total Citations | Funding | Citations/$1M |
|---------|-----------------|---------|---------------|
| All MIMIC | 9,695 | $14.4M | **672.2** |
| UK Biobank | 9,582 | $525.5M | 18.2 |
| OpenSAFELY | 6,253 | $53.7M | 116.4 |
| All of Us | 1,306 | $2,160M | 0.6 |
