# The Power of Data Communities

Data and code for the study analyzing the scholarly impact and research equity of four major open health data repositories: MIMIC, UK Biobank, OpenSAFELY, and All of Us.

**Preprint:** [The power of data communities: an analysis of open-access health data repositories](https://www.medrxiv.org/content/10.64898/2026.03.20.26348933v1)

## Overview

This repository contains the complete data and analysis pipeline for a cross-sectional bibliometric study examining:

1. **Funding-normalized scholarly output** at first-degree (direct citations) and second-degree (citations of citations) levels
2. **Research community demographics**, including gender representation, geographic diversity, and authorship position
3. **Equity patterns** across repositories serving different research communities

Citation data was collected from [OpenAlex](https://openalex.org/) through December 31, 2025. Author gender was inferred using [Genderize.io](https://genderize.io/). Country income classifications follow [World Bank](https://datahelpdesk.worldbank.org/knowledgebase/articles/906519) groupings.

## Repository Structure

```
.
├── data/
│   ├── citing_papers/          # First-degree citation data per repository
│   ├── authors/                # Gender-annotated author data per repository
│   ├── second_degree/          # Second-degree citation data (gzipped)
│   ├── world_bank_income.json  # Country income classifications
│   └── fetch_summary.json      # Data collection summary
├── scripts/
│   ├── 01_fetch_citing_papers.py      # Collect citing papers from OpenAlex
│   ├── 01b_fetch_second_degree.py     # Collect second-degree citations
│   ├── 02_infer_gender.py             # Infer author gender via Genderize.io
│   ├── 03_analysis.py                 # Main analysis and statistical tests
│   ├── 04_supplementary_analysis.py   # Supplementary tables
│   └── generate_figures.R             # Publication-quality figures
├── figures/                    # Generated figures (PNG + SVG)
├── DATA_DICTIONARY.md          # Variable descriptions for all data files
└── README.md
```

## Data

All datasets are provided as JSON files (or gzip-compressed `.json.gz` for larger files). See [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) for complete variable descriptions.

### Citing Papers (`data/citing_papers/`)

First-degree citations for each repository's primary publication(s), collected from OpenAlex. Each file contains full metadata including authors, affiliations, topics, keywords, MeSH terms, funders, and open access status.

| File | Repository |
|------|-----------|
| `mimic-i.json` | MIMIC-I |
| `mimic-ii.json` | MIMIC-II |
| `mimic-iii.json` | MIMIC-III |
| `mimic-iv.json` | MIMIC-IV |
| `all-of-us.json` | All of Us |
| `opensafely.json.gz` | OpenSAFELY |
| `uk-biobank.json.gz` | UK Biobank |

### Author Data (`data/authors/`)

Gender-annotated versions of the citing paper files, with probabilistic gender assignments from Genderize.io added to each author record.

### Second-Degree Citations (`data/second_degree/`)

Papers that cite the first-degree citing papers (i.e., citations of citations), filtered to exclude papers whose abstracts mention the original dataset. These capture the "invisible" downstream influence of each repository.

### Reference Data

- `data/world_bank_income.json` — World Bank country income classifications (HIC, UMC, LMC, LIC)
- `data/fetch_summary.json` — Summary statistics from data collection

## Scripts

Scripts are numbered in the order they should be run.

### Prerequisites

**Python** (3.9+):
```bash
pip install requests pandas tqdm matplotlib numpy scipy
```

**R** (4.0+):
```R
install.packages(c("jsonlite", "dplyr", "tidyr", "ggplot2", "scales", "patchwork", "DiagrammeR", "DiagrammeRsvg", "rsvg"))
```

### Pipeline

| Step | Script | Description |
|------|--------|-------------|
| 1 | `01_fetch_citing_papers.py` | Fetch first-degree citing papers from OpenAlex |
| 2 | `01b_fetch_second_degree.py` | Fetch second-degree citations (requires OpenAlex API key) |
| 3 | `02_infer_gender.py` | Infer author gender using Genderize.io |
| 4 | `03_analysis.py` | Run main analysis, generate tables and statistical tests |
| 5 | `04_supplementary_analysis.py` | Generate supplementary tables |
| 6 | `generate_figures.R` | Generate all publication figures |

## License

This repository is made available under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) license.

## Citation

If you use this data or code, please cite:

> Gorijavolu, R., et al. The Power of Open Health Data: Impact, Representation, and Knowledge Diffusion. *medRxiv* (2026). https://doi.org/10.64898/2026.03.20.26348933
