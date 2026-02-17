# Publication-Ready Tables and Statistical Analysis

---

## Table 2. Author Demographics of Publications Citing Open Health Data Repositories

| Repository | Publications (n) | Authors (n) | Female (%)† | Countries (n) | LMIC (%)‡ | HIC-LMIC Collab (%)§ |
|:-----------|:----------------:|:-----------:|:-----------:|:-------------:|:---------:|:--------------------:|
| MIMIC | 9,924 | 57,713 | 31.8 | 105 | **41.8** | 11.8 |
| UK Biobank | 11,803 | 126,115 | 38.6 | 134 | 22.9 | 16.4 |
| OpenSAFELY | 6,256 | 70,043 | 41.7 | 148 | 17.4 | 12.1 |
| All of Us | 2,066 | 21,483 | 43.2 | 91 | 4.3 | 8.4 |
| **χ² (df=3)** | | | **1,583.9** | | **14,435.2** | |
| **p-value** | | | **<0.001** | | **<0.001** | |

† Percentage of authors with identifiable gender (identification rate >98% for all repositories).
‡ Low- and middle-income countries as classified by World Bank 2024.
§ Percentage of publications with authors from both high-income and low/middle-income countries.

---

## Table 3. Author Position Analysis by Gender and Income Classification

| Repository | First Author Female (%) | First Author LMIC (%) | Last Author Female (%) | Last Author LMIC (%) | Gender p‖ |
|:-----------|:-----------------------:|:---------------------:|:----------------------:|:--------------------:|:---------:|
| MIMIC | 32.3 | **43.8** | 27.4 | **41.5** | <0.001 |
| UK Biobank | 42.2 | 29.4 | 31.3 | 26.7 | <0.001 |
| OpenSAFELY | 43.0 | 22.0 | 34.6 | 21.9 | <0.001 |
| All of Us | 42.7 | 4.1 | 37.6 | 3.0 | 0.001 |

First author = primary researcher; last author = senior/supervising investigator.
‖ Chi-square test comparing gender distribution between first and last author positions.

---

## Supplementary Table S1. Gender Distribution by Author Position

| Repository | Position | Male (n) | Female (n) | Female (%) |
|:-----------|:---------|---------:|-----------:|-----------:|
| **MIMIC** | First | 6,604 | 3,156 | 32.3 |
| | Middle | 25,414 | 12,371 | 32.7 |
| | Last | 6,849 | 2,586 | 27.4 |
| **UK Biobank** | First | 6,735 | 4,927 | 42.2 |
| | Middle | 62,322 | 39,914 | 39.0 |
| | Last | 7,743 | 3,521 | 31.3 |
| **OpenSAFELY** | First | 3,449 | 2,603 | 43.0 |
| | Middle | 33,025 | 24,209 | 42.3 |
| | Last | 3,710 | 1,960 | 34.6 |
| **All of Us** | First | 1,172 | 874 | 42.7 |
| | Middle | 9,746 | 7,609 | 43.8 |
| | Last | 1,200 | 722 | 37.6 |

Gender inferred using Genderize.io API based on author first names.

---

## Supplementary Table S2. Geographic Distribution by Author Position

| Repository | Position | HIC (n) | LMIC (n) | LMIC (%) |
|:-----------|:---------|---------:|---------:|---------:|
| **MIMIC** | First | 4,710 | 3,666 | 43.8 |
| | Middle | 17,665 | 13,395 | 43.1 |
| | Last | 4,681 | 3,320 | 41.5 |
| **UK Biobank** | First | 7,529 | 3,139 | 29.4 |
| | Middle | 70,542 | 21,672 | 23.5 |
| | Last | 7,301 | 2,661 | 26.7 |
| **OpenSAFELY** | First | 4,222 | 1,192 | 22.0 |
| | Middle | 39,736 | 7,936 | 16.6 |
| | Last | 3,879 | 1,088 | 21.9 |
| **All of Us** | First | 1,738 | 75 | 4.1 |
| | Middle | 15,010 | 656 | 4.2 |
| | Last | 1,618 | 50 | 3.0 |

HIC = high-income country; LMIC = low- and middle-income country (World Bank 2024).

---

## Supplementary Table S3. Pairwise Statistical Comparisons (MIMIC vs Other Repositories)

| Comparison | Measure | χ² | p-value (adj)¶ | Cramér's V | OR (95% CI) |
|:-----------|:--------|---:|:--------------:|:----------:|:-----------:|
| MIMIC vs UK Biobank | LMIC representation | 5,527.8 | <0.001 | 0.186 | 2.34 (2.29–2.40) |
| MIMIC vs UK Biobank | Gender distribution | 792.7 | <0.001 | 0.066 | 0.74 (0.73–0.76) |
| MIMIC vs OpenSAFELY | LMIC representation | 8,156.3 | <0.001 | 0.278 | 3.53 (3.43–3.63) |
| MIMIC vs OpenSAFELY | Gender distribution | 1,317.8 | <0.001 | 0.102 | 0.65 (0.64–0.67) |
| MIMIC vs All of Us | LMIC representation | 9,511.7 | <0.001 | 0.378 | 17.71 (16.45–19.07) |
| MIMIC vs All of Us | Gender distribution | 884.3 | <0.001 | 0.106 | 0.61 (0.59–0.63) |

¶ Bonferroni-corrected (n=3). All comparisons significant at α = 0.05.
OR for LMIC: odds of LMIC authorship in MIMIC relative to comparator (OR >1 = higher in MIMIC).
OR for gender: odds of female authorship in MIMIC relative to comparator (OR <1 = lower in MIMIC).

---

## Supplementary Table S4. Intersectional Analysis: Authorship Position by Gender and Income

| Repository | Position | HIC Male (n) | HIC Female (n) | HIC Female (%) | LMIC Male (n) | LMIC Female (n) | LMIC Female (%) |
|:-----------|:---------|:------------:|:--------------:|:--------------:|:-------------:|:---------------:|:---------------:|
| **MIMIC** | First | 3,261 | 1,400 | 30.0 | 2,287 | 1,310 | 36.4 |
| | Middle | 12,423 | 5,089 | 29.1 | 8,160 | 5,081 | 38.4 |
| | Last | 3,526 | 1,109 | 23.9 | 2,233 | 1,044 | 31.9 |
| **UK Biobank** | First | 4,424 | 3,048 | 40.8 | 1,709 | 1,384 | 44.7 |
| | Middle | 43,885 | 26,271 | 37.4 | 11,842 | 9,582 | 44.7 |
| | Last | 5,130 | 2,145 | 29.5 | 1,700 | 926 | 35.3 |
| **OpenSAFELY** | First | 2,392 | 1,777 | 42.6 | 630 | 542 | 46.2 |
| | Middle | 22,768 | 16,606 | 42.2 | 4,160 | 3,653 | 46.8 |
| | Last | 2,507 | 1,325 | 34.6 | 667 | 400 | 37.5 |
| **All of Us** | First | 983 | 745 | 43.1 | 45 | 30 | 40.0 |
| | Middle | 8,402 | 6,500 | 43.6 | 366 | 281 | 43.4 |
| | Last | 1,001 | 611 | 37.9 | 26 | 24 | 48.0 |

Female % calculated within each income group. Authors with unknown gender or unclassified income excluded.

---

## Supplementary Table S5a. Unique Author Demographics by Gender and Income Classification

Authors deduplicated by OpenAlex author ID within each dataset.

| Repository | Unique Authors (n) | Male (n) | Female (n) | Female (%)† | HIC (n) | LMIC (n) | LMIC (%)‡ |
|:-----------|:------------------:|---------:|-----------:|:-----------:|--------:|---------:|:---------:|
| MIMIC | 33,573 | 22,063 | 11,096 | 33.5 | 15,149 | 13,599 | **47.3** |
| UK Biobank | 51,783 | 30,080 | 21,204 | 41.3 | 32,047 | 13,838 | 30.2 |
| OpenSAFELY | 44,441 | 24,629 | 19,152 | 43.7 | 29,073 | 8,124 | 21.8 |
| All of Us | 13,238 | 7,310 | 5,828 | 44.4 | 11,110 | 615 | 5.2 |

† Of unique authors with identified gender. ‡ Of unique authors with classified country income.

---

## Supplementary Table S5b. Unique Authors: Gender x Income Cross-Tabulation

| Repository | HIC Male (n) | HIC Female (n) | LMIC Male (n) | LMIC Female (n) |
|:-----------|:------------:|:--------------:|:-------------:|:---------------:|
| MIMIC | 10,555 | 4,445 | 8,353 | **5,062** |
| UK Biobank | 18,937 | 12,846 | 7,682 | 6,000 |
| OpenSAFELY | 16,327 | 12,392 | 4,359 | 3,634 |
| All of Us | 6,156 | 4,875 | 340 | 269 |

Authors with unknown gender or unclassified country income excluded.

---

## Supplementary Table S5c. Unique Authors Who Held First or Last Author Position

| Repository | Ever First Author (n) | First Female (%) | First LMIC (%) | Ever Last Author (n) | Last Female (%) | Last LMIC (%) |
|:-----------|:---------------------:|:----------------:|:--------------:|:--------------------:|:---------------:|:-------------:|
| MIMIC | 6,921 | 32.8 | **39.2** | 5,853 | 28.3 | **40.7** |
| UK Biobank | 7,278 | 42.7 | 31.3 | 5,071 | 32.8 | 27.0 |
| OpenSAFELY | 4,810 | 43.0 | 21.3 | 4,289 | 35.5 | 21.5 |
| All of Us | 1,517 | 43.8 | 3.8 | 1,271 | 39.4 | 3.3 |

"Ever First" = unique authors who appeared as first author on at least one publication citing the repository.

---

## Supplementary Table S6. Position Effect Statistics (First vs Last Author)

| Repository | Measure | χ² | p-value | Cramér's V | OR (95% CI) |
|:-----------|:--------|---:|--------:|:----------:|:-----------:|
| MIMIC | Gender | 55.3 | <0.001 | 0.054 | 1.27 (1.19–1.35) |
| MIMIC | LMIC | 8.6 | 0.004 | 0.023 | 1.10 (1.03–1.17) |
| UK Biobank | Gender | 296.9 | <0.001 | 0.114 | 1.61 (1.52–1.70) |
| UK Biobank | LMIC | 18.6 | <0.001 | 0.030 | 1.14 (1.08–1.22) |
| OpenSAFELY | Gender | 87.4 | <0.001 | 0.086 | 1.43 (1.33–1.54) |
| OpenSAFELY | LMIC | 0.01 | 0.909 | 0.001 | 1.01 (0.92–1.11) |
| All of Us | Gender | 10.7 | 0.001 | 0.052 | 1.24 (1.09–1.41) |
| All of Us | LMIC | 2.9 | 0.087 | 0.029 | 1.40 (0.97–2.01) |

OR: odds of female (or LMIC) authorship in first author position relative to last author position (OR >1 = higher in first).

---

## Methods

**Citation data**: Citing publications identified via OpenAlex API for each repository's primary publication(s). MIMIC combines versions I–IV.

**Gender inference**: Author gender inferred using Genderize.io API based on first names. Identification rate exceeded 98% for all repositories. Gender percentages calculated from identified authors only.

**Income classification**: Countries classified as HIC or LMIC using World Bank 2024 income classifications. Country determined from institutional affiliations in OpenAlex. LMIC percentages calculated from authors with classified country income only.

**Statistical analysis**: Pearson's chi-square tests with Cramér's V for effect size. Odds ratios with 95% confidence intervals reported for all 2×2 comparisons. Pairwise comparisons Bonferroni-corrected (n=3). Significance level α = 0.05.
