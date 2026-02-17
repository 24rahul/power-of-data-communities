# Power of Data Communities - v2 Analysis

Revised analysis addressing PLOS Digital Health editor feedback.

## Key Improvements over v1

1. **Reproducible citation data** - OpenAlex API instead of manual Google Scholar
2. **Enhanced longevity adjustment** - Citations per year, growth rate analysis
3. **Documented funding attribution** - Currency standardization, source documentation
4. **Consent & reidentifiability analysis** - New section comparing dataset governance
5. **Statistical rigor** - Confidence intervals, significance tests

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Fetch Citation Data

```bash
cd scripts
python fetch_citations.py
```

This will:
- Query OpenAlex API for each dataset's primary publication
- Save citation counts by year to `data/citations/`
- Create a summary file and detailed logs

### 2. Run Analysis

Open `analysis_v2.ipynb` in Jupyter and run all cells.

## Project Structure

```
v2/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── analysis_v2.ipynb           # Main analysis notebook
├── data/
│   ├── datasets_metadata.csv   # Dataset properties (funding, consent, etc.)
│   ├── citations/              # OpenAlex citation data
│   │   ├── mimic-i_citations.csv
│   │   ├── mimic-ii_citations.csv
│   │   └── ...
│   ├── all_citations_combined.csv
│   └── citation_fetch_summary.csv
├── scripts/
│   └── fetch_citations.py      # OpenAlex data fetcher
├── figures/                    # Generated figures
└── logs/                       # API query logs for reproducibility
```

## Data Sources

### Citation Data
- **Source**: OpenAlex API (https://openalex.org/)
- **Method**: Query by DOI, extract `counts_by_year`
- **Reproducibility**: All API queries logged with timestamps

### Funding Data
- **MIMIC**: NIH Reporter (https://reporter.nih.gov/)
- **UK Biobank**: Official funding summary PDF
- **OpenSAFELY**: Wellcome Trust / MRC / NIHR grants
- **All of Us**: NIH program funding

### Consent & Access Models
- Documented from official dataset documentation
- See `data/datasets_metadata.csv` for details

## Addressing Editor Feedback

| Concern | How Addressed |
|---------|---------------|
| Longevity adjustment | Citations/year metric, growth rate normalization, maturity grouping |
| Funding attribution | Documented sources, original currency preserved, conversion methodology |
| Consent & reidentifiability | New comparison table with consent models, access controls, risk levels |

## Citation

If you use this analysis, please cite:
- The original manuscript (DOI pending)
- OpenAlex: Priem, J., Piwowar, H., & Orr, R. (2022). OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts. arXiv:2205.01833.
