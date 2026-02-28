#!/usr/bin/env Rscript
# Recreate Figure 1 and Figure 2 in R with publication-quality formatting

library(jsonlite)
library(dplyr)
library(ggplot2)
library(scales)
library(patchwork)

# ---- Paths ----
args <- commandArgs(trailingOnly = FALSE)
script_path <- sub("--file=", "", args[grep("--file=", args)])
if (length(script_path) > 0) {
  script_dir <- dirname(normalizePath(script_path))
} else {
  script_dir <- getwd()
}
base_dir <- normalizePath(file.path(script_dir, ".."))
authors_dir <- file.path(base_dir, "data", "authors")
figures_dir <- file.path(base_dir, "figures")
dir.create(figures_dir, showWarnings = FALSE, recursive = TRUE)

# ---- Dataset config ----
dataset_config <- tibble::tribble(
  ~dataset,      ~color,     ~launch_year, ~funding_m, ~shape,
  "MIMIC",       "#1f77b4",  1997,         14.4,       16,

  "UK-Biobank",  "#2ca02c",  2015,         525.5,      15,
  "OpenSAFELY",  "#ff7f0e",  2020,         53.7,       17,
  "All-of-Us",   "#d62728",  2018,         2160.0,     18
)

mimic_components <- c("mimic-i", "mimic-ii", "mimic-iii", "mimic-iv")

# ---- Load data ----
cat("Loading datasets...\n")

load_json <- function(name) {
  path_json <- file.path(authors_dir, paste0(name, "_with_gender.json"))
  path_gz   <- file.path(authors_dir, paste0(name, "_with_gender.json.gz"))
  if (file.exists(path_gz)) {
    fromJSON(path_gz, simplifyVector = FALSE)
  } else if (file.exists(path_json)) {
    fromJSON(path_json, simplifyVector = FALSE)
  } else {
    stop("File not found for: ", name)
  }
}

# Load MIMIC (combine I-IV)
mimic_papers <- list()
for (comp in mimic_components) {
  d <- load_json(comp)
  mimic_papers <- c(mimic_papers, d$papers)
}
cat("  MIMIC combined:", length(mimic_papers), "papers\n")

# Load others
ukb_data <- load_json("uk-biobank")
os_data  <- load_json("opensafely")
aou_data <- load_json("all-of-us")

cat("  UK-Biobank:", length(ukb_data$papers), "papers\n")
cat("  OpenSAFELY:", length(os_data$papers), "papers\n")
cat("  All-of-Us:", length(aou_data$papers), "papers\n")

all_datasets <- list(
  "MIMIC"      = mimic_papers,
  "UK-Biobank" = ukb_data$papers,
  "OpenSAFELY" = os_data$papers,
  "All-of-Us"  = aou_data$papers
)

# ---- Publication theme ----
theme_pub <- function(base_size = 11) {
  theme_classic(base_size = base_size) %+replace%
    theme(
      text = element_text(family = "sans", colour = "black"),
      axis.text = element_text(colour = "black", size = rel(0.9)),
      axis.title = element_text(size = rel(1.0), face = "plain"),
      axis.line = element_line(colour = "black", linewidth = 0.4),
      axis.ticks = element_line(colour = "black", linewidth = 0.3),
      legend.title = element_blank(),
      legend.text = element_text(size = rel(0.85)),
      legend.key.size = unit(0.9, "lines"),
      legend.background = element_rect(fill = "white", colour = NA),
      plot.title = element_text(size = rel(1.1), face = "bold", hjust = 0),
      plot.margin = margin(8, 12, 8, 8),
      panel.grid = element_blank()
    )
}

dataset_colors <- setNames(dataset_config$color, dataset_config$dataset)
dataset_shapes <- setNames(dataset_config$shape, dataset_config$dataset)

# ===========================================================================
# FIGURE 1: Cumulative Citations Over Time
# ===========================================================================
cat("Generating Figure 1...\n")

fig1_data <- bind_rows(lapply(names(all_datasets), function(ds_name) {
  papers <- all_datasets[[ds_name]]
  cfg <- dataset_config %>% filter(dataset == ds_name)
  launch <- cfg$launch_year

  # Extract years
  years <- sapply(papers, function(p) p$year)
  years <- years[!is.na(years) & !is.null(years)]
  years <- as.integer(unlist(years))

  year_counts <- table(factor(years, levels = seq(min(years), 2025)))
  cumsum_vals <- cumsum(as.numeric(year_counts))
  yr_seq <- as.integer(names(year_counts))

  # Start from launch year
  keep <- yr_seq >= launch
  tibble(
    year = yr_seq[keep],
    cumulative = cumsum_vals[keep],
    dataset = ds_name
  )
}))

# Factor to preserve legend order
fig1_data$dataset <- factor(fig1_data$dataset, levels = dataset_config$dataset)

# Legend labels with launch year
legend_labels <- setNames(
  paste0(dataset_config$dataset, " (", dataset_config$launch_year, ")"),
  dataset_config$dataset
)
legend_labels["MIMIC"] <- "MIMIC II-IV (2010)"

p1 <- ggplot(fig1_data, aes(x = year, y = cumulative,
                             colour = dataset, shape = dataset)) +
  geom_line(linewidth = 0.8) +
  geom_point(size = 2) +
  scale_colour_manual(values = dataset_colors, labels = legend_labels) +
  scale_shape_manual(values = dataset_shapes, labels = legend_labels) +
  scale_x_continuous(breaks = seq(2010, 2024, by = 2), limits = c(2010, 2026),
                     expand = c(0.01, 0)) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.05))) +
  labs(x = "Year", y = "Cumulative Citing Papers") +
  theme_pub(base_size = 12) +
  theme(
    legend.position = c(0.02, 0.98),
    legend.justification = c(0, 1),
    legend.key.width = unit(1.5, "lines")
  )

ggsave(file.path(figures_dir, "figure_1_new.png"), p1,
       width = 7.5, height = 5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_1_new.svg"), p1,
       width = 7.5, height = 5, bg = "white")
cat("  Saved: figures/figure_1_new.png & .svg\n")

# ===========================================================================
# FIGURE 1 MONTHLY: Cumulative citations with monthly granularity
# ===========================================================================
cat("Generating Figure 1 monthly...\n")

fig1m_data <- bind_rows(lapply(names(all_datasets), function(ds_name) {
  papers <- all_datasets[[ds_name]]

  # Extract publication_date, fall back to year-01-01
  dates <- sapply(papers, function(p) {
    d <- p$publication_date
    if (is.null(d) || is.na(d)) {
      yr <- p$year
      if (!is.null(yr) && !is.na(yr)) paste0(yr, "-01-01") else NA_character_
    } else {
      d
    }
  })
  dates <- as.Date(dates)
  dates <- dates[!is.na(dates)]

  # Truncate to first of month
  months <- as.Date(format(dates, "%Y-%m-01"))

  # Count per month
  month_counts <- as.data.frame(table(months), stringsAsFactors = FALSE)
  names(month_counts) <- c("month", "n")
  month_counts$month <- as.Date(month_counts$month)
  month_counts <- month_counts[order(month_counts$month), ]

  # Fill in missing months with 0 and compute cumulative
  full_seq <- seq(min(month_counts$month), max(month_counts$month), by = "month")
  full_df <- data.frame(month = full_seq)
  full_df <- merge(full_df, month_counts, by = "month", all.x = TRUE)
  full_df$n[is.na(full_df$n)] <- 0
  full_df$cumulative <- cumsum(full_df$n)
  full_df$dataset <- ds_name
  full_df
}))

fig1m_data$dataset <- factor(fig1m_data$dataset, levels = dataset_config$dataset)

# Filter to 2010+
fig1m_data <- fig1m_data[fig1m_data$month >= as.Date("2010-01-01"), ]

p1m <- ggplot(fig1m_data, aes(x = month, y = cumulative,
                               colour = dataset)) +
  geom_line(linewidth = 0.6) +
  scale_colour_manual(values = dataset_colors, labels = legend_labels) +
  scale_x_date(date_breaks = "1 year", date_labels = "%Y",
               limits = as.Date(c("2010-01-01", "2026-01-01")),
               expand = c(0.01, 0)) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.05))) +
  labs(x = "Year", y = "Cumulative Citing Papers") +
  theme_pub(base_size = 12) +
  theme(
    legend.position = c(0.02, 0.98),
    legend.justification = c(0, 1),
    legend.key.width = unit(1.5, "lines")
  )

ggsave(file.path(figures_dir, "figure_1_monthly_new.png"), p1m,
       width = 7.5, height = 5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_1_monthly_new.svg"), p1m,
       width = 7.5, height = 5, bg = "white")
cat("  Saved: figures/figure_1_monthly_new.png & .svg\n")

# ===========================================================================
# FIGURE 2: Citation Impact Distribution (Two Panels)
# ===========================================================================
cat("Generating Figure 2...\n")

fig2_data <- bind_rows(lapply(names(all_datasets), function(ds_name) {
  papers <- all_datasets[[ds_name]]
  cfg <- dataset_config %>% filter(dataset == ds_name)
  funding <- cfg$funding_m

  cites <- sapply(papers, function(p) {
    v <- p$cited_by_count
    if (is.null(v)) 0L else as.integer(v)
  })
  cites_sorted <- sort(cites, decreasing = TRUE)

  tibble(
    rank = seq_along(cites_sorted),
    citations = cites_sorted,
    citations_norm = cites_sorted / funding,
    dataset = ds_name
  )
}))

fig2_data$dataset <- factor(fig2_data$dataset, levels = dataset_config$dataset)

# Panel A: Raw citations
pA <- ggplot(fig2_data, aes(x = rank, y = citations, colour = dataset)) +
  geom_line(linewidth = 0.6, alpha = 0.85) +
  scale_x_log10(labels = comma) +
  scale_y_log10(labels = comma) +
  scale_colour_manual(values = dataset_colors) +
  labs(x = "Paper Rank (by citations)", y = "Citations", tag = "A") +
  theme_pub(base_size = 11)

# Panel B: Funding-normalized with readable y-axis labels
pB <- ggplot(fig2_data, aes(x = rank, y = citations_norm, colour = dataset)) +
  geom_line(linewidth = 0.6, alpha = 0.85) +
  scale_x_log10(labels = comma) +
  scale_y_log10(
    breaks = 10^seq(-3, 3),
    labels = function(x) {
      sapply(x, function(v) {
        if (v >= 1) format(v, big.mark = ",", scientific = FALSE)
        else if (v >= 0.1) "0.1"
        else if (v >= 0.01) "0.01"
        else "0.001"
      })
    }
  ) +
  scale_colour_manual(values = dataset_colors) +
  labs(x = "Paper Rank (by citations)", y = "Citations per $1M Funding", tag = "B") +
  theme_pub(base_size = 11)

p2 <- pA + pB + plot_layout(ncol = 2, guides = "collect") &
  theme(legend.position = "bottom",
        legend.margin = margin(t = -4),
        plot.tag = element_text(size = 14, face = "bold", hjust = 0, vjust = 1))

ggsave(file.path(figures_dir, "figure_2_new.png"), p2,
       width = 11, height = 5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_2_new.svg"), p2,
       width = 11, height = 5, bg = "white")
cat("  Saved: figures/figure_2_new.png & .svg\n")

# ===========================================================================
# FIGURE 3: Funding-normalized citation box plot (standalone)
# ===========================================================================
cat("Generating Figure 3...\n")

fig3_box <- bind_rows(lapply(names(all_datasets), function(ds_name) {
  papers <- all_datasets[[ds_name]]
  cfg <- dataset_config %>% filter(dataset == ds_name)
  funding <- cfg$funding_m

  cites <- sapply(papers, function(p) {
    v <- p$cited_by_count
    if (is.null(v)) 0L else as.integer(v)
  })
  # Citations per $1M funding = citations / funding_m
  cites_per_funding <- cites / funding
  tibble(dataset = ds_name, cites_per_funding = cites_per_funding) %>%
    filter(is.finite(cites_per_funding) & cites_per_funding > 0)
}))
fig3_box$dataset <- factor(fig3_box$dataset, levels = rev(dataset_config$dataset))

p3 <- ggplot(fig3_box, aes(x = dataset, y = cites_per_funding, fill = dataset)) +
  geom_boxplot(width = 0.55, outlier.size = 0.6, outlier.alpha = 0.25) +
  scale_fill_manual(values = dataset_colors) +
  scale_y_log10(
    breaks = c(0.001, 0.01, 0.1, 1, 10, 100, 1000),
    labels = c("0.001", "0.01", "0.1", "1", "10", "100", "1,000")
  ) +
  coord_flip() +
  labs(x = NULL, y = "Citations per $1M Funding") +
  theme_pub(base_size = 12) +
  theme(legend.position = "none")

p3_panel <- p3 + labs(tag = "B")

ggsave(file.path(figures_dir, "figure_3_new.png"), p3,
       width = 7.5, height = 4, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_3_new.svg"), p3,
       width = 7.5, height = 4, bg = "white")
cat("  Saved: figures/figure_3_new.png & .svg\n")

# ===========================================================================
# FIGURE 4: Citation distribution (citations per paper vs number of papers)
# ===========================================================================
cat("Generating Figure 4...\n")

fig4_data <- bind_rows(lapply(names(all_datasets), function(ds_name) {
  papers <- all_datasets[[ds_name]]

  cites <- sapply(papers, function(p) {
    v <- p$cited_by_count
    if (is.null(v)) 0L else as.integer(v)
  })
  # Keep only papers with >= 1 citation for log scale
  cites <- cites[cites >= 1]

  # Log-spaced bins
  max_cite <- max(cites)
  breaks <- 10^seq(0, log10(max_cite + 1), length.out = 40)
  h <- hist(cites, breaks = breaks, plot = FALSE)

  # Use bin midpoints (geometric mean of edges)
  bin_mid <- sqrt(h$breaks[-length(h$breaks)] * h$breaks[-1])
  keep <- h$counts > 0

  tibble(
    citations = bin_mid[keep],
    count = h$counts[keep],
    dataset = ds_name
  )
}))

fig4_data$dataset <- factor(fig4_data$dataset, levels = dataset_config$dataset)

p4 <- ggplot(fig4_data, aes(x = citations, y = count,
                              colour = dataset, shape = dataset)) +
  geom_line(linewidth = 0.7, alpha = 0.8) +
  geom_point(size = 1.8, alpha = 0.8) +
  scale_colour_manual(values = dataset_colors) +
  scale_shape_manual(values = dataset_shapes) +
  scale_x_log10(
    breaks = c(1, 5, 10, 50, 100, 500, 1000, 5000),
    labels = c("1", "5", "10", "50", "100", "500", "1,000", "5,000")
  ) +
  scale_y_log10(
    breaks = c(1, 5, 10, 50, 100, 500, 1000, 5000),
    labels = c("1", "5", "10", "50", "100", "500", "1,000", "5,000")
  ) +
  labs(x = "Citations per Paper", y = "Number of Papers") +
  theme_pub(base_size = 12) +
  theme(
    legend.position = c(0.98, 0.98),
    legend.justification = c(1, 1),
    legend.key.width = unit(1.5, "lines")
  )

p4_panel <- p4 + labs(tag = "A")

ggsave(file.path(figures_dir, "figure_4_new.png"), p4,
       width = 7.5, height = 5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_4_new.svg"), p4,
       width = 7.5, height = 5, bg = "white")
cat("  Saved: figures/figure_4_new.png & .svg\n")

# ===========================================================================
# FIGURE 3+4 Combined: Two-panel figure
# ===========================================================================
cat("Generating Figure 3+4 combined...\n")

p34 <- p4_panel + p3_panel +
  plot_layout(ncol = 2, widths = c(1.2, 1)) &
  theme(plot.tag = element_text(size = 14, face = "bold", hjust = 0, vjust = 1))

ggsave(file.path(figures_dir, "figure_3_4_combined.png"), p34,
       width = 14, height = 5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_3_4_combined.svg"), p34,
       width = 14, height = 5, bg = "white")
cat("  Saved: figures/figure_3_4_combined.png & .svg\n")

# ===========================================================================
# FIGURE 3+4 Alt: Panel A raw + Panel B funding-normalized distribution
# ===========================================================================
cat("Generating Figure 3+4 alt (funding-normalized distribution)...\n")

fig4_norm_data <- bind_rows(lapply(names(all_datasets), function(ds_name) {
  papers <- all_datasets[[ds_name]]
  cfg <- dataset_config %>% filter(dataset == ds_name)
  funding <- cfg$funding_m

  cites <- sapply(papers, function(p) {
    v <- p$cited_by_count
    if (is.null(v)) 0L else as.integer(v)
  })
  cites_norm <- cites / funding
  # Keep only positive values for log scale
  cites_norm <- cites_norm[cites_norm > 0]

  # Log-spaced bins
  max_val <- max(cites_norm)
  min_val <- min(cites_norm)
  breaks <- 10^seq(floor(log10(min_val)), ceiling(log10(max_val + 1)), length.out = 40)
  h <- hist(cites_norm, breaks = breaks, plot = FALSE)

  bin_mid <- sqrt(h$breaks[-length(h$breaks)] * h$breaks[-1])
  keep <- h$counts > 0

  tibble(
    cites_per_funding = bin_mid[keep],
    count = h$counts[keep],
    dataset = ds_name
  )
}))

fig4_norm_data$dataset <- factor(fig4_norm_data$dataset, levels = dataset_config$dataset)

p4_norm <- ggplot(fig4_norm_data, aes(x = cites_per_funding, y = count,
                                       colour = dataset, shape = dataset)) +
  geom_line(linewidth = 0.7, alpha = 0.8) +
  geom_point(size = 1.8, alpha = 0.8) +
  scale_colour_manual(values = dataset_colors) +
  scale_shape_manual(values = dataset_shapes) +
  scale_x_log10(
    breaks = c(0.001, 0.01, 0.1, 1, 10, 100, 1000),
    labels = c("0.001", "0.01", "0.1", "1", "10", "100", "1,000")
  ) +
  scale_y_log10(
    breaks = c(1, 5, 10, 50, 100, 500, 1000, 5000),
    labels = c("1", "5", "10", "50", "100", "500", "1,000", "5,000")
  ) +
  labs(x = "Citations per $1M Funding", y = "Number of Papers", tag = "B") +
  theme_pub(base_size = 12) +
  theme(
    legend.position = c(0.98, 0.98),
    legend.justification = c(1, 1),
    legend.key.width = unit(1.5, "lines")
  )

p34_alt <- p4_panel + p4_norm +
  plot_layout(ncol = 2, guides = "collect") &
  theme(legend.position = "bottom",
        legend.margin = margin(t = -4),
        plot.tag = element_text(size = 14, face = "bold", hjust = 0, vjust = 1))

ggsave(file.path(figures_dir, "figure_3_4_combined_alt.png"), p34_alt,
       width = 14, height = 5.5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_3_4_combined_alt.svg"), p34_alt,
       width = 14, height = 5.5, bg = "white")
cat("  Saved: figures/figure_3_4_combined_alt.png & .svg\n")

# ===========================================================================
# FIGURE 5: Second-Degree Citation Impact Distribution (Two Panels)
# ===========================================================================
cat("Generating Figure 5 (second-degree papers)...\n")

second_degree_dir <- file.path(base_dir, "data", "second_degree")

load_second_degree <- function(name) {
  path_gz <- file.path(second_degree_dir, paste0(name, ".json.gz"))
  if (file.exists(path_gz)) {
    fromJSON(path_gz, simplifyVector = FALSE)
  } else {
    stop("Second-degree file not found for: ", name)
  }
}

# Load second-degree papers (deduplicate MIMIC components)
mimic_2nd <- list()
mimic_2nd_ids <- character(0)
for (comp in mimic_components) {
  d <- load_second_degree(comp)
  for (p in d$papers) {
    if (!(p$id %in% mimic_2nd_ids)) {
      mimic_2nd <- c(mimic_2nd, list(p))
      mimic_2nd_ids <- c(mimic_2nd_ids, p$id)
    }
  }
}
cat("  MIMIC second-degree papers:", length(mimic_2nd), "\n")

ukb_2nd <- load_second_degree("uk-biobank")
os_2nd  <- load_second_degree("opensafely")
aou_2nd <- load_second_degree("all-of-us")

cat("  UK-Biobank second-degree papers:", length(ukb_2nd$papers), "\n")
cat("  OpenSAFELY second-degree papers:", length(os_2nd$papers), "\n")
cat("  All-of-Us second-degree papers:", length(aou_2nd$papers), "\n")

all_citing <- list(
  "MIMIC"      = mimic_2nd,
  "UK-Biobank" = ukb_2nd$papers,
  "OpenSAFELY" = os_2nd$papers,
  "All-of-Us"  = aou_2nd$papers
)

# ---- Panel A: Citations per Paper vs Number of Papers ----
fig5_raw_data <- bind_rows(lapply(names(all_citing), function(ds_name) {
  papers <- all_citing[[ds_name]]

  cites <- sapply(papers, function(p) {
    v <- p$cited_by_count
    if (is.null(v)) 0L else as.integer(v)
  })
  cites <- cites[cites >= 1]

  max_cite <- max(cites)
  breaks <- 10^seq(0, log10(max_cite + 1), length.out = 40)
  h <- hist(cites, breaks = breaks, plot = FALSE)

  bin_mid <- sqrt(h$breaks[-length(h$breaks)] * h$breaks[-1])
  keep <- h$counts > 0

  tibble(
    citations = bin_mid[keep],
    count = h$counts[keep],
    dataset = ds_name
  )
}))

fig5_raw_data$dataset <- factor(fig5_raw_data$dataset, levels = dataset_config$dataset)

p5A <- ggplot(fig5_raw_data, aes(x = citations, y = count,
                                   colour = dataset, shape = dataset)) +
  geom_line(linewidth = 0.7, alpha = 0.8) +
  geom_point(size = 1.8, alpha = 0.8) +
  scale_colour_manual(values = dataset_colors) +
  scale_shape_manual(values = dataset_shapes) +
  scale_x_log10(
    breaks = c(1, 5, 10, 50, 100, 500, 1000, 5000),
    labels = c("1", "5", "10", "50", "100", "500", "1,000", "5,000")
  ) +
  scale_y_log10(
    breaks = c(1, 5, 10, 50, 100, 500, 1000, 5000),
    labels = c("1", "5", "10", "50", "100", "500", "1,000", "5,000")
  ) +
  labs(x = "Citations per Paper", y = "Number of Papers", tag = "A") +
  theme_pub(base_size = 12)

# ---- Panel B: Funding-normalized ----
fig5_norm_data <- bind_rows(lapply(names(all_citing), function(ds_name) {
  papers <- all_citing[[ds_name]]
  cfg <- dataset_config %>% filter(dataset == ds_name)
  funding <- cfg$funding_m

  cites <- sapply(papers, function(p) {
    v <- p$cited_by_count
    if (is.null(v)) 0L else as.integer(v)
  })
  cites_norm <- cites / funding
  cites_norm <- cites_norm[cites_norm > 0]

  max_val <- max(cites_norm)
  min_val <- min(cites_norm)
  breaks <- 10^seq(floor(log10(min_val)), ceiling(log10(max_val + 1)), length.out = 40)
  h <- hist(cites_norm, breaks = breaks, plot = FALSE)

  bin_mid <- sqrt(h$breaks[-length(h$breaks)] * h$breaks[-1])
  keep <- h$counts > 0

  tibble(
    cites_per_funding = bin_mid[keep],
    count = h$counts[keep],
    dataset = ds_name
  )
}))

fig5_norm_data$dataset <- factor(fig5_norm_data$dataset, levels = dataset_config$dataset)

p5B <- ggplot(fig5_norm_data, aes(x = cites_per_funding, y = count,
                                    colour = dataset, shape = dataset)) +
  geom_line(linewidth = 0.7, alpha = 0.8) +
  geom_point(size = 1.8, alpha = 0.8) +
  scale_colour_manual(values = dataset_colors) +
  scale_shape_manual(values = dataset_shapes) +
  scale_x_log10(
    breaks = c(0.001, 0.01, 0.1, 1, 10, 100, 1000),
    labels = c("0.001", "0.01", "0.1", "1", "10", "100", "1,000")
  ) +
  scale_y_log10(
    breaks = c(1, 5, 10, 50, 100, 500, 1000, 5000),
    labels = c("1", "5", "10", "50", "100", "500", "1,000", "5,000")
  ) +
  labs(x = "Citations per $1M Funding", y = "Number of Papers", tag = "B") +
  theme_pub(base_size = 12)

p5 <- p5A + p5B +
  plot_layout(ncol = 2, guides = "collect") &
  theme(legend.position = "bottom",
        legend.margin = margin(t = -4),
        plot.tag = element_text(size = 14, face = "bold", hjust = 0, vjust = 1))

ggsave(file.path(figures_dir, "figure_5_second_degree.png"), p5,
       width = 14, height = 5.5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_5_second_degree.svg"), p5,
       width = 14, height = 5.5, bg = "white")
cat("  Saved: figures/figure_5_second_degree.png & .svg\n")

# ===========================================================================
# PRISMA Flow Diagram
# ===========================================================================
cat("Generating PRISMA diagram...\n")

library(DiagrammeR)
library(DiagrammeRsvg)
library(rsvg)

prisma_dot <- '
digraph PRISMA {
  graph [rankdir=TB, splines=ortho, nodesep=0.8, ranksep=0.6,
         bgcolor=white, fontname="Helvetica"]
  node [shape=box, style="filled,rounded", fontname="Helvetica", fontsize=11,
        fillcolor="#f0f4f8", color="#4a5568", penwidth=1.2,
        width=3.5, height=0.01, margin="0.18,0.1"]
  edge [color="#718096", penwidth=1.2, arrowsize=0.7]

  // Phase labels
  node [shape=plaintext, fillcolor=none, color=none, fontsize=13, fontcolor="#2d3748", width=0]
  L1 [label=<<B>Identification</B>>]
  L2 [label=<<B>1st Degree<BR/>Retrieval</B>>]
  L3 [label=<<B>Screening</B>>]
  L4 [label=<<B>2nd Degree<BR/>Retrieval</B>>]
  L5 [label=<<B>Included</B>>]

  // Main flow
  node [shape=box, style="filled,rounded", fillcolor="#f0f4f8", color="#4a5568", width=3.5]

  S1 [label=<<B>Source Publications Identified</B><BR/><BR/>MIMIC (I-IV): 4 papers<BR/>UK Biobank: 1 paper<BR/>OpenSAFELY: 1 paper<BR/>All of Us: 1 paper<BR/><BR/><B>Total: 7 source papers</B>>]

  S2 [label=<<B>First-Degree Citing Papers Retrieved</B><BR/>(via OpenAlex API)<BR/><BR/>MIMIC: 9,581  |  UK Biobank: 11,803<BR/>OpenSAFELY: 6,256  |  All of Us: 2,066<BR/><BR/><B>Total: 29,706 records</B>>]

  S3 [label=<<B>Unique First-Degree Papers</B><BR/><BR/>MIMIC: 9,581  |  UK Biobank: 11,803<BR/>OpenSAFELY: 6,256  |  All of Us: 2,066<BR/><BR/><B>Total: 29,291 unique papers</B>>]

  S4 [label=<<B>First-Degree Papers with Citations</B><BR/>(queried for 2nd-degree citers)<BR/><BR/>MIMIC: 7,100  |  UK Biobank: 9,075<BR/>OpenSAFELY: 5,052  |  All of Us: 1,478<BR/><BR/><B>Total: 22,705 papers</B>>]

  S5 [label=<<B>Second-Degree Citing Papers Retrieved</B><BR/><BR/>MIMIC: 133,861  |  UK Biobank: 215,809<BR/>OpenSAFELY: 124,311  |  All of Us: 29,890<BR/><BR/><B>Total: 466,932 unique papers</B>>,
      fillcolor="#f0fff4", color="#276749"]

  // Exclusion boxes
  node [width=2.8]

  E1 [label=<<B>Duplicates Removed</B><BR/><BR/>415 cross-component<BR/>duplicates (MIMIC I-IV)>,
      fillcolor="#fff5f5", color="#c53030"]

  E2 [label=<<B>Excluded: Uncited Papers</B><BR/>(no downstream citations)<BR/><BR/>MIMIC: 2,481  |  UK Biobank: 2,728<BR/>OpenSAFELY: 1,204  |  All of Us: 588<BR/><BR/><B>Total: 7,001 papers</B>>,
      fillcolor="#fff5f5", color="#c53030"]

  // Main vertical flow
  S1 -> S2 [weight=10]
  S2 -> S3 [weight=10]
  S3 -> S4 [weight=10]
  S4 -> S5 [weight=10]

  // Side arrows to exclusion boxes
  S2 -> E1 [constraint=false]
  S3 -> E2 [constraint=false]

  // Rank alignment
  { rank=same; L1; S1 }
  { rank=same; L2; S2; E1 }
  { rank=same; L3; S3; E2 }
  { rank=same; L4; S4 }
  { rank=same; L5; S5 }

  // Invisible edges to position labels
  edge [style=invis]
  L1 -> L2 -> L3 -> L4 -> L5
}
'

g <- grViz(prisma_dot)
svg_text <- export_svg(g)

# Save as SVG
svg_path <- file.path(figures_dir, "prisma_diagram.svg")
writeLines(svg_text, svg_path)

# Save as PNG
png_path <- file.path(figures_dir, "prisma_diagram.png")
rsvg_png(charToRaw(svg_text), file = png_path, width = 3600, height = 4800)

cat("  Saved: figures/prisma_diagram.png & .svg\n")

cat("Done.\n")
