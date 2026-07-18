# Data Dictionary

This document describes all variables in the datasets provided in `data/`.

## Citing Papers (`data/citing_papers/*.json[.gz]`)

Each file is a JSON object with the following structure:

### Envelope (top-level fields)

| Field | Type | Description |
|-------|------|-------------|
| `dataset` | string | Repository name (e.g., "MIMIC-III") |
| `source_doi` | string | DOI of the repository's primary publication |
| `source_openalex_id` | string | OpenAlex work ID for the primary publication |
| `launch_year` | integer | Year the repository first released data |
| `fetched_at` | string | ISO 8601 datetime of data collection |
| `total_papers` | integer | Total number of citing papers |
| `total_author_records` | integer | Total author records across all papers |
| `papers` | array | Array of paper objects (see below) |

### Paper Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | OpenAlex work ID |
| `doi` | string | Digital Object Identifier (URL format) |
| `title` | string | Paper title |
| `year` | integer | Publication year |
| `publication_date` | string | ISO 8601 date |
| `cited_by_count` | integer | Number of citations received |
| `type` | string | Publication type (e.g., "article") |
| `language` | string | ISO 639-1 language code |
| `is_retracted` | boolean | Whether the paper has been retracted |
| `fwci` | float | Field-Weighted Citation Impact |
| `journal` | string | Journal or source name |
| `journal_id` | string | OpenAlex source ID |
| `open_access` | object | Open access status (see below) |
| `topics` | array | Topic classifications (see below) |
| `keywords` | array | Author keywords (see below) |
| `mesh` | array | MeSH descriptors (see below) |
| `funders` | array | Funding sources |
| `authors` | array | Author records (see below) |

### Open Access Object

| Field | Type | Description |
|-------|------|-------------|
| `is_oa` | boolean | Whether the paper is open access |
| `oa_status` | string | OA type: "gold", "green", "hybrid", "bronze", or "closed" |

### Topic Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | OpenAlex topic ID |
| `name` | string | Topic name |
| `score` | float | Classification confidence (0-1) |
| `subfield` | string | Subfield name |
| `field` | string | Field name |
| `domain` | string | Domain name |

### Keyword Object

| Field | Type | Description |
|-------|------|-------------|
| `keyword` | string | Keyword text |
| `score` | float | Relevance score (0-1) |

### MeSH Object

| Field | Type | Description |
|-------|------|-------------|
| `descriptor_ui` | string | MeSH descriptor unique identifier |
| `descriptor_name` | string | MeSH descriptor name |
| `qualifier_ui` | string | MeSH qualifier unique identifier |
| `qualifier_name` | string | MeSH qualifier name |
| `is_major_topic` | boolean | Whether this is a major topic |

### Author Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | OpenAlex author ID |
| `name` | string | Author display name |
| `raw_name` | string | Name as it appears on the paper |
| `orcid` | string or null | ORCID identifier |
| `position` | integer | 1-indexed position in author list |
| `position_type` | string | "first", "middle", or "last" |
| `is_corresponding` | boolean | Whether this is the corresponding author |
| `countries` | array of strings | ISO 3166-1 alpha-2 country codes from affiliations |
| `raw_affiliation_strings` | array of strings | Raw affiliation text |
| `institutions` | array | Institutional affiliations |

---

## Author Data (`data/authors/*_with_gender.json[.gz]`)

Same structure as citing papers, with the following additions:

### Additional Envelope Field

| Field | Type | Description |
|-------|------|-------------|
| `gender_inference` | object | Gender inference metadata |

#### Gender Inference Object

| Field | Type | Description |
|-------|------|-------------|
| `inferred_at` | string | ISO 8601 datetime of inference |
| `cache_size` | integer | Number of names in the gender cache |
| `gender_distribution` | object | Counts: `{male, female, unknown}` |

### Additional Author Fields

| Field | Type | Description |
|-------|------|-------------|
| `gender` | string | Inferred gender: "male", "female", or "unknown" |
| `gender_probability` | float | Confidence of gender assignment (0-1) |
| `first_name` | string | Lowercased first name used for inference |

---

## Second-Degree Citations (`data/second_degree/*.json.gz`)

Gzip-compressed JSON files containing papers that cite the first-degree papers.

### Envelope

| Field | Type | Description |
|-------|------|-------------|
| `dataset` | string | Repository name |
| `fetched_at` | string | ISO 8601 datetime of data collection |
| `total_first_degree_queried` | integer | Number of first-degree papers queried |
| `total_second_degree_raw` | integer | Total second-degree papers before filtering |
| `total_filtered_by_abstract` | integer | Papers removed (abstract mentions dataset) |
| `total_papers` | integer | Final count after filtering |
| `papers` | array | Array of paper objects (see below) |

### Second-Degree Paper Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | OpenAlex work ID |
| `doi` | string | Digital Object Identifier |
| `title` | string | Paper title |
| `abstract` | string | Paper abstract text |
| `cited_by_count` | integer | Number of citations received |
| `year` | integer | Publication year |
| `type` | string | Publication type |
| `language` | string | ISO 639-1 language code |
| `journal` | string | Journal or source name |

---

## World Bank Income Classifications (`data/world_bank_income.json`)

JSON object keyed by ISO 3166-1 alpha-2 country code.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Country or region name |
| `income_level` | string | World Bank code: "HIC", "UMC", "LMC", "LIC", or "NA" |
| `income_name` | string | Human-readable label (e.g., "High income") |

Income level codes:
- **HIC** — High-income country
- **UMC** — Upper-middle-income country
- **LMC** — Lower-middle-income country
- **LIC** — Low-income country

---

## Fetch Summary (`data/fetch_summary.json`)

JSON array summarizing the data collection for each dataset.

| Field | Type | Description |
|-------|------|-------------|
| `dataset` | string | Repository name |
| `papers` | integer | Number of citing papers collected |
| `author_records` | integer | Total author records across all papers |
| `countries` | integer | Number of distinct countries represented |
| `fetch_time` | string | ISO 8601 datetime of collection |

---

## Gender Cache (`data/authors/gender_cache.json`)

JSON object mapping lowercase first names to Genderize.io results. Used to avoid redundant API calls.

| Field | Type | Description |
|-------|------|-------------|
| *(key)* | string | Lowercase first name |
| *(value)*.`gender` | string or null | Inferred gender |
| *(value)*.`probability` | float | Confidence (0-1) |
| *(value)*.`count` | integer | Number of records in Genderize.io database |
