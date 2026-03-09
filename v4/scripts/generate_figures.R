#!/usr/bin/env Rscript
# Recreate Figure 1 and Figure 2 in R with publication-quality formatting

library(jsonlite)
library(dplyr)
library(tidyr)
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
# Second-degree analyses use only data/second_degree/*.json.gz as ground truth
# (all-of-us, mimic-i/ii/iii/iv, opensafely, uk-biobank). No other sources.
# ===========================================================================
cat("Generating Figure 5 (second-degree papers)...\n")

second_degree_dir <- file.path(base_dir, "data", "second_degree")

load_second_degree_df <- function(name) {
  path_gz <- file.path(second_degree_dir, paste0(name, ".json.gz"))
  if (!file.exists(path_gz)) stop("Second-degree file not found for: ", name)
  d <- fromJSON(path_gz, simplifyVector = TRUE, flatten = TRUE)
  papers <- d$papers
  if (!is.data.frame(papers)) stop("Expected data.frame for papers in: ", name)
  papers$cited_by_count <- as.integer(ifelse(is.na(papers$cited_by_count), 0L, papers$cited_by_count))
  papers$year <- as.integer(papers$year)
  papers
}

# Load second-degree papers as data.frames (fast)
cat("  Loading second-degree data (as data.frames)...\n")
mimic_2nd_dfs <- list()
for (comp in mimic_components) {
  cat("    Loading ", comp, "...\n")
  mimic_2nd_dfs[[comp]] <- load_second_degree_df(comp)
}
mimic_2nd_all <- bind_rows(mimic_2nd_dfs)
mimic_2nd_all <- mimic_2nd_all[!duplicated(mimic_2nd_all$id), ]
cat("  MIMIC second-degree papers:", nrow(mimic_2nd_all), "\n")

cat("    Loading uk-biobank...\n")
ukb_2nd_df <- load_second_degree_df("uk-biobank")
cat("    Loading opensafely...\n")
os_2nd_df  <- load_second_degree_df("opensafely")
cat("    Loading all-of-us...\n")
aou_2nd_df <- load_second_degree_df("all-of-us")

cat("  UK-Biobank second-degree papers:", nrow(ukb_2nd_df), "\n")
cat("  OpenSAFELY second-degree papers:", nrow(os_2nd_df), "\n")
cat("  All-of-Us second-degree papers:", nrow(aou_2nd_df), "\n")

# all_citing is now a named list of data.frames
all_citing <- list(
  "MIMIC"      = mimic_2nd_all,
  "UK-Biobank" = ukb_2nd_df,
  "OpenSAFELY" = os_2nd_df,
  "All-of-Us"  = aou_2nd_df
)

# ---- Panel A: Citations per Paper vs Number of Papers ----
fig5_raw_data <- bind_rows(lapply(names(all_citing), function(ds_name) {
  df <- all_citing[[ds_name]]
  cites <- df$cited_by_count
  cites <- cites[!is.na(cites) & cites >= 1]

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
  df <- all_citing[[ds_name]]
  cfg <- dataset_config %>% filter(dataset == ds_name)
  funding <- cfg$funding_m

  cites <- df$cited_by_count
  cites_norm <- cites / funding
  cites_norm <- cites_norm[!is.na(cites_norm) & cites_norm > 0]

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
# RIPPLE ANALYSIS: Shared data preparation for Figures 6-9
# ===========================================================================
cat("Preparing ripple analysis data...\n")

# Compute total citation mass per dataset for each layer
ripple_summary <- bind_rows(lapply(names(all_datasets), function(ds_name) {
  cfg <- dataset_config %>% filter(dataset == ds_name)
  funding <- cfg$funding_m

  fd_papers <- all_datasets[[ds_name]]
  sd_df <- all_citing[[ds_name]]

  fd_cites <- sum(sapply(fd_papers, function(p) {
    v <- p$cited_by_count; if (is.null(v)) 0L else as.integer(v)
  }))
  sd_cites <- sum(sd_df$cited_by_count, na.rm = TRUE)

  tibble(
    dataset = ds_name,
    fd_papers = length(fd_papers),
    sd_papers = nrow(sd_df),
    fd_cites = fd_cites,
    sd_cites = sd_cites,
    funding_m = funding,
    fd_per_m = fd_cites / funding,
    sd_per_m = sd_cites / funding,
    ripple_ratio = if (fd_cites > 0) sd_cites / fd_cites else NA_real_
  )
}))
ripple_summary$dataset <- factor(ripple_summary$dataset, levels = dataset_config$dataset)

cat("  Ripple summary:\n")
for (i in seq_len(nrow(ripple_summary))) {
  r <- ripple_summary[i, ]
  cat(sprintf("    %s: 1st=%s cites, 2nd=%s cites, ratio=%.1fx, per $1M: %s / %s\n",
              r$dataset, format(r$fd_cites, big.mark = ","),
              format(r$sd_cites, big.mark = ","), r$ripple_ratio,
              format(round(r$fd_per_m), big.mark = ","),
              format(round(r$sd_per_m), big.mark = ",")))
}

# Per-year cumulative data for both layers
ripple_time <- bind_rows(lapply(names(all_datasets), function(ds_name) {
  cfg <- dataset_config %>% filter(dataset == ds_name)
  funding <- cfg$funding_m
  launch <- cfg$launch_year

  # First-degree: list-of-lists -> extract year + cited_by_count
  build_cumulative_list <- function(papers, layer_name) {
    years <- as.integer(vapply(papers, function(p) {
      v <- p$year; if (is.null(v)) NA_integer_ else as.integer(v)
    }, integer(1)))
    cites <- as.integer(vapply(papers, function(p) {
      v <- p$cited_by_count; if (is.null(v)) 0L else as.integer(v)
    }, integer(1)))
    keep <- !is.na(years)
    years <- years[keep]; cites <- cites[keep]
    if (length(years) == 0) return(tibble())

    df <- tibble(year = years, cites = cites) %>%
      group_by(year) %>% summarise(mass = sum(cites), .groups = "drop") %>%
      arrange(year)

    all_years <- tibble(year = seq(max(launch, min(df$year)), 2025))
    df <- left_join(all_years, df, by = "year") %>%
      mutate(mass = replace(mass, is.na(mass), 0),
             cumulative = cumsum(mass),
             dataset = ds_name, layer = layer_name,
             funding_m = funding, cum_per_m = cumulative / funding)
    df
  }

  # Second-degree: data.frame -> vectorised
  build_cumulative_df <- function(sd_df, layer_name) {
    sd_df <- sd_df[!is.na(sd_df$year), ]
    if (nrow(sd_df) == 0) return(tibble())

    df <- sd_df %>%
      group_by(year) %>% summarise(mass = sum(cited_by_count, na.rm = TRUE), .groups = "drop") %>%
      arrange(year)

    all_years <- tibble(year = seq(max(launch, min(df$year)), 2025))
    df <- left_join(all_years, df, by = "year") %>%
      mutate(mass = replace(mass, is.na(mass), 0),
             cumulative = cumsum(mass),
             dataset = ds_name, layer = layer_name,
             funding_m = funding, cum_per_m = cumulative / funding)
    df
  }

  bind_rows(
    build_cumulative_list(all_datasets[[ds_name]], "1st-degree"),
    build_cumulative_df(all_citing[[ds_name]], "2nd-degree")
  )
}))
ripple_time$dataset <- factor(ripple_time$dataset, levels = dataset_config$dataset)
ripple_time$layer <- factor(ripple_time$layer, levels = c("2nd-degree", "1st-degree"))

# ===========================================================================
# FIGURE 6: Two-panel grouped bars (absolute + per $1M)
# ===========================================================================
cat("Generating Figure 6 (ripple bars)...\n")

fig6_data <- ripple_summary %>%
  tidyr::pivot_longer(cols = c(fd_cites, sd_cites),
                      names_to = "layer", values_to = "cites") %>%
  mutate(
    layer = factor(ifelse(layer == "fd_cites", "1st-degree", "2nd-degree"),
                   levels = c("1st-degree", "2nd-degree")),
    cites_m = cites / 1e6,
    cites_per_m = cites / funding_m
  )

layer_fills <- c("1st-degree" = "#5a9bd5", "2nd-degree" = "#ed7d31")

p6A <- ggplot(fig6_data, aes(x = dataset, y = cites_m, fill = layer)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  scale_fill_manual(values = layer_fills) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.08))) +
  labs(x = NULL, y = "Total Citations (millions)", tag = "A") +
  theme_pub(base_size = 11) +
  theme(legend.position = "none",
        axis.text.x = element_text(size = rel(0.85)))

p6B <- ggplot(fig6_data, aes(x = dataset, y = cites_per_m, fill = layer)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  scale_fill_manual(values = layer_fills) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.08))) +
  labs(x = NULL, y = "Citations per $1M Funding", tag = "B") +
  theme_pub(base_size = 11) +
  theme(axis.text.x = element_text(size = rel(0.85)))

p6 <- p6A + p6B +
  plot_layout(ncol = 2, guides = "collect") &
  theme(legend.position = "bottom",
        legend.margin = margin(t = -4),
        plot.tag = element_text(size = 14, face = "bold", hjust = 0, vjust = 1))

ggsave(file.path(figures_dir, "figure_6_ripple_bars.png"), p6,
       width = 12, height = 5.5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_6_ripple_bars.svg"), p6,
       width = 12, height = 5.5, bg = "white")
cat("  Saved: figures/figure_6_ripple_bars.png & .svg\n")

# ===========================================================================
# FIGURE 7: Cumulative ripple over time per $1M (line chart)
# ===========================================================================
cat("Generating Figure 7 (ripple over time)...\n")

fig7_data <- ripple_time %>% filter(year >= 2010)

p7 <- ggplot(fig7_data, aes(x = year, y = cum_per_m,
                              colour = dataset, linetype = layer)) +
  geom_line(linewidth = 0.8) +
  scale_colour_manual(values = dataset_colors, labels = legend_labels) +
  scale_linetype_manual(values = c("1st-degree" = "dashed", "2nd-degree" = "solid"),
                        labels = c("1st-degree" = "1st-degree (direct)", "2nd-degree" = "2nd-degree (ripple)")) +
  scale_x_continuous(breaks = seq(2010, 2024, by = 2), limits = c(2010, 2026),
                     expand = c(0.01, 0)) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.05))) +
  labs(x = "Year", y = "Cumulative Citations per $1M Funding") +
  guides(colour = guide_legend(order = 1), linetype = guide_legend(order = 2)) +
  theme_pub(base_size = 12) +
  theme(
    legend.position = c(0.02, 0.98),
    legend.justification = c(0, 1),
    legend.key.width = unit(2, "lines"),
    legend.spacing.y = unit(0.2, "lines")
  )

ggsave(file.path(figures_dir, "figure_7_ripple_over_time.png"), p7,
       width = 8.5, height = 5.5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_7_ripple_over_time.svg"), p7,
       width = 8.5, height = 5.5, bg = "white")
cat("  Saved: figures/figure_7_ripple_over_time.png & .svg\n")

# ===========================================================================
# FIGURE 8: Stacked iceberg bars per $1M
# ===========================================================================
cat("Generating Figure 8 (iceberg bars)...\n")

fig8_data <- ripple_summary %>%
  tidyr::pivot_longer(cols = c(fd_per_m, sd_per_m),
                      names_to = "layer", values_to = "per_m") %>%
  mutate(
    layer = factor(ifelse(layer == "fd_per_m", "1st-degree", "2nd-degree"),
                   levels = c("2nd-degree", "1st-degree")),
    dataset = factor(dataset, levels = rev(levels(dataset)))
  )

# Lighter shades for 2nd-degree
iceberg_fills <- c("1st-degree" = "#2c3e50", "2nd-degree" = "#85c1e9")

# Multiplier labels positioned at the end of the full bar
fig8_labels <- ripple_summary %>%
  mutate(
    total_per_m = fd_per_m + sd_per_m,
    label = sprintf("%.0fx", ripple_ratio),
    dataset = factor(dataset, levels = rev(levels(dataset)))
  )

p8 <- ggplot(fig8_data, aes(x = dataset, y = per_m, fill = layer)) +
  geom_col(width = 0.6) +
  geom_text(data = fig8_labels,
            aes(x = dataset, y = total_per_m, label = label, fill = NULL),
            hjust = -0.2, size = 3.5, fontface = "bold") +
  scale_fill_manual(values = iceberg_fills,
                    labels = c("2nd-degree" = "2nd-degree (ripple)",
                               "1st-degree" = "1st-degree (direct)")) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.12))) +
  coord_flip() +
  labs(x = NULL, y = "Citations per $1M Funding") +
  theme_pub(base_size = 12) +
  theme(legend.position = "bottom",
        legend.margin = margin(t = -2))

ggsave(file.path(figures_dir, "figure_8_iceberg_bars.png"), p8,
       width = 8, height = 4.5, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_8_iceberg_bars.svg"), p8,
       width = 8, height = 4.5, bg = "white")
cat("  Saved: figures/figure_8_iceberg_bars.png & .svg\n")

# ===========================================================================
# FIGURE 9: True iceberg chart -- 1st-degree above waterline, 2nd-degree below
# ===========================================================================
cat("Generating Figure 9 (iceberg over time)...\n")

fig9_data <- ripple_time %>%
  filter(year >= 2010) %>%
  select(year, dataset, layer, cum_per_m)

fig9_above <- fig9_data %>% filter(layer == "1st-degree")
fig9_below <- fig9_data %>% filter(layer == "2nd-degree")

# Top row: 1st-degree (direct) -- own y-axis, area grows upward
p9_top <- ggplot(fig9_above, aes(x = year, y = cum_per_m)) +
  geom_area(fill = "#2471a3", alpha = 0.9) +
  geom_line(colour = "#1a5276", linewidth = 0.3) +
  facet_wrap(~dataset, ncol = 4) +
  scale_x_continuous(breaks = seq(2012, 2024, by = 4), expand = c(0.02, 0)) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.05)),
                     position = "left") +
  labs(x = NULL, y = "Direct (per $1M)") +
  theme_pub(base_size = 10) +
  theme(
    strip.text = element_text(face = "bold", size = rel(1.0)),
    strip.background = element_blank(),
    panel.spacing = unit(0.8, "lines"),
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank(),
    plot.margin = margin(8, 12, 0, 8)
  )

# Bottom row: 2nd-degree (ripple) -- own y-axis, area grows downward
p9_bottom <- ggplot(fig9_below, aes(x = year, y = -cum_per_m)) +
  geom_area(aes(y = -cum_per_m), fill = "#aed6f1", alpha = 0.8) +
  geom_line(aes(y = -cum_per_m), colour = "#1a5276", linewidth = 0.3) +
  facet_wrap(~dataset, ncol = 4) +
  scale_x_continuous(breaks = seq(2012, 2024, by = 4), expand = c(0.02, 0)) +
  scale_y_continuous(labels = function(x) comma(abs(x)),
                     expand = expansion(mult = c(0.05, 0)),
                     position = "left") +
  labs(x = "Year", y = "Ripple (per $1M)") +
  theme_pub(base_size = 10) +
  theme(
    strip.text = element_blank(),
    panel.spacing = unit(0.8, "lines"),
    plot.margin = margin(0, 12, 8, 8)
  )

max_direct <- max(fig9_above$cum_per_m, na.rm = TRUE)
max_ripple <- max(fig9_below$cum_per_m, na.rm = TRUE)
p9 <- p9_top / p9_bottom + plot_layout(heights = c(max_direct, max_ripple))

total_h <- 3 + 3 * (max_ripple / max_direct)
total_h <- min(max(total_h, 5), 12)

ggsave(file.path(figures_dir, "figure_9_iceberg_over_time.png"), p9,
       width = 14, height = total_h, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_9_iceberg_over_time.svg"), p9,
       width = 14, height = total_h, bg = "white")
cat("  Saved: figures/figure_9_iceberg_over_time.png & .svg\n")

# ===========================================================================
# Figure 10 — Disciplinary Diffusion
# ===========================================================================
cat("Generating Figure 10 (disciplinary diffusion)...\n")

extract_topics <- function(ds_name, papers) {
  rows <- list()
  for (p in papers) {
    yr <- p$year
    if (is.null(yr) || is.na(yr)) next
    topics <- p$topics
    if (is.null(topics) || length(topics) == 0) next
    top_topic <- topics[[1]]
    field <- top_topic$field
    domain <- top_topic$domain
    if (is.null(field) || is.na(field)) next
    rows[[length(rows) + 1]] <- data.frame(
      dataset = ds_name, year = as.integer(yr),
      field = field, domain = if (is.null(domain)) NA_character_ else domain,
      stringsAsFactors = FALSE
    )
  }
  bind_rows(rows)
}

topic_data <- bind_rows(lapply(names(all_datasets), function(ds_name) {
  extract_topics(ds_name, all_datasets[[ds_name]])
}))

topic_data <- topic_data %>%
  filter(year >= 2010, !is.na(field))

top_fields <- topic_data %>%
  count(field, sort = TRUE) %>%
  head(8) %>%
  pull(field)

topic_data <- topic_data %>%
  mutate(field_group = ifelse(field %in% top_fields, field, "Other"))

field_year_raw <- topic_data %>%
  count(dataset, year, field_group)

year_totals <- field_year_raw %>%
  group_by(dataset, year) %>%
  summarise(total = sum(n), .groups = "drop")

field_year <- field_year_raw %>%
  inner_join(year_totals, by = c("dataset", "year")) %>%
  filter(total >= 10) %>%
  mutate(pct = n / total) %>%
  select(-total)

ds_order <- c("MIMIC", "UK-Biobank", "OpenSAFELY", "All-of-Us")
field_year$dataset <- factor(field_year$dataset, levels = ds_order)

palette_fields <- c(
  "#2471a3", "#1abc9c", "#e74c3c", "#f39c12",
  "#9b59b6", "#3498db", "#e67e22", "#27ae60",
  "#bdc3c7"
)
n_groups <- length(unique(field_year$field_group))
names(palette_fields) <- c(
  sort(setdiff(unique(field_year$field_group), "Other")),
  "Other"
)[1:n_groups]

p10 <- ggplot(field_year, aes(x = year, y = pct, fill = field_group)) +
  geom_area(alpha = 0.85, colour = "white", linewidth = 0.2) +
  facet_wrap(~dataset, ncol = 4) +
  scale_x_continuous(breaks = seq(2012, 2024, by = 4), expand = c(0.02, 0)) +
  scale_y_continuous(labels = percent_format(accuracy = 1),
                     limits = c(0, 1),
                     expand = expansion(mult = c(0, 0.02))) +
  scale_fill_manual(values = palette_fields, name = "Field") +
  labs(x = "Year",
       y = "Share of Papers by Primary Research Field") +
  theme_pub(base_size = 10) +
  theme(
    strip.text = element_text(face = "bold", size = rel(1.0)),
    strip.background = element_blank(),
    panel.spacing = unit(0.8, "lines"),
    legend.position = "bottom",
    legend.text = element_text(size = rel(0.7)),
    legend.key.size = unit(0.4, "cm"),
    legend.margin = margin(t = -4)
  ) +
  guides(fill = guide_legend(nrow = 2))

ggsave(file.path(figures_dir, "figure_10_disciplinary_diffusion.png"), p10,
       width = 14, height = 6, dpi = 600, bg = "white")
ggsave(file.path(figures_dir, "figure_10_disciplinary_diffusion.svg"), p10,
       width = 14, height = 6, bg = "white")
cat("  Saved: figures/figure_10_disciplinary_diffusion.png & .svg\n")

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
