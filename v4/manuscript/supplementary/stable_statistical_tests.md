# Statistical Analysis

All tests are Pearson's chi-square tests with Cramér's V for effect size.
Odds ratios (OR) with 95% confidence intervals are reported for 2×2 comparisons.
Pairwise comparisons use Bonferroni correction (n=3).
Significance level: α = 0.05.

## Overall Tests (All Datasets)

| Test | χ² | df | p-value | Cramér's V |
|------|---:|---:|--------:|-----------:|
| Overall LMIC distribution | 14435.18 | 3 | 0.00e+00 | 0.2465 |
| Overall gender distribution | 1583.92 | 3 | 0.00e+00 | 0.0763 |

## Pairwise Comparisons (MIMIC vs Others, Bonferroni-corrected)

| Comparison | Test | χ² | p-value (adj) | Cramér's V | OR (95% CI) |
|------------|------|---:|:-------------:|-----------:|:-----------:|
| MIMIC vs UK-Biobank | LMIC representation | 5527.75 | 0.00e+00 | 0.1857 | 2.341 (2.288–2.395) |
| MIMIC vs UK-Biobank | Gender distribution | 792.69 | 6.28e-174 | 0.066 | 0.74 (0.725–0.756) |
| MIMIC vs OpenSAFELY | LMIC representation | 8156.3 | 0.00e+00 | 0.2781 | 3.527 (3.43–3.628) |
| MIMIC vs OpenSAFELY | Gender distribution | 1317.82 | 4.54e-288 | 0.1023 | 0.651 (0.636–0.666) |
| MIMIC vs All-of-Us | LMIC representation | 9511.65 | 0.00e+00 | 0.378 | 17.714 (16.453–19.073) |
| MIMIC vs All-of-Us | Gender distribution | 884.25 | 7.83e-194 | 0.1063 | 0.614 (0.594–0.634) |

OR for LMIC: odds of LMIC authorship in MIMIC relative to comparator (OR > 1 = higher LMIC in MIMIC).
OR for gender: odds of female authorship in MIMIC relative to comparator (OR < 1 = lower female in MIMIC).

## Position Effects (First vs Last Author Within Each Dataset)

| Dataset | Test | χ² | p-value | Cramér's V | OR (95% CI) |
|---------|------|---:|--------:|-----------:|:-----------:|
| MIMIC | (gender) | 55.32 | 1.02e-13 | 0.0537 | 1.266 (1.19–1.347) |
| MIMIC | (LMIC) | 8.55 | 0.0035 | 0.0229 | 1.097 (1.031–1.168) |
| UK-Biobank | (gender) | 296.89 | 1.57e-66 | 0.1138 | 1.609 (1.524–1.698) |
| UK-Biobank | (LMIC) | 18.63 | 1.59e-05 | 0.03 | 1.144 (1.076–1.216) |
| OpenSAFELY | (gender) | 87.41 | 8.80e-21 | 0.0864 | 1.429 (1.326–1.539) |
| OpenSAFELY | (LMIC) | 0.01 | 0.9089 | 0.0011 | 1.007 (0.917–1.105) |
| All-of-Us | (gender) | 10.73 | 0.0011 | 0.052 | 1.239 (1.091–1.408) |
| All-of-Us | (LMIC) | 2.94 | 0.0866 | 0.029 | 1.396 (0.97–2.01) |

OR for position: odds of female (or LMIC) authorship in first author position relative to last author (OR > 1 = higher in first).