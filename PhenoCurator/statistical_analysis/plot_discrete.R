suppressPackageStartupMessages({
  library(ggplot2)
  library(ggpubr)
  library(fitdistrplus)
})

parse_args <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  out <- list()
  i <- 1
  while (i <= length(args)) {
    if (args[[i]] %in% c("--input", "--output-dir") && i < length(args)) {
      out[[substring(args[[i]], 3)]] <- args[[i + 1]]
      i <- i + 2
    } else {
      i <- i + 1
    }
  }
  out
}

args <- parse_args()
input_file <- args$input
output_dir <- args[["output-dir"]]
if (is.null(input_file) || is.null(output_dir)) stop("Required args: --input --output-dir")
if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
df <- read.csv(input_file, check.names = FALSE, stringsAsFactors = FALSE)


result <- data.frame(
  Name = character(),
  Step = character(),
  Status = character(),
  Detail = character(),
  stringsAsFactors = FALSE
)

record_status <- function(name, step, status, detail = "") {
  result <<- rbind(result, data.frame(
    Name = name,
    Step = step,
    Status = status,
    Detail = detail,
    stringsAsFactors = FALSE
  ))
}

close_all_devices <- function() {
  while (dev.cur() > 1) {
    dev.off()
  }
}

profile_theme <- function() {
  theme_light() +
    theme(
      plot.margin = margin(10, 10, 10, 10),
      panel.border = element_rect(color = "black", fill = NA),
      text = element_text(family = "sans", size = 12),
      plot.title = element_text(hjust = 0.5, size = 14, family = "sans"),
      axis.title = element_text(size = 12, family = "sans"),
      axis.text = element_text(size = 12, family = "sans"),
      legend.text = element_text(size = 10, family = "sans"),
      legend.key.size = unit(0.7, "lines"),
      legend.background = element_rect(fill = "transparent", color = NA)
    )
}

qq_theme <- function() {
  theme_light() +
    theme(
      plot.margin = margin(10, 10, 10, 10),
      plot.title = element_text(hjust = 0.5, size = 14, family = "sans"),
      axis.title = element_text(size = 12, family = "sans"),
      axis.text = element_text(size = 12, family = "sans"),
      legend.key.size = unit(0.7, "lines"),
      legend.background = element_rect(fill = "transparent", color = NA),
      plot.background = element_blank(),
      panel.background = element_blank(),
      panel.border = element_rect(color = "black", fill = NA, linewidth = 0.5)
    )
}

fit_distribution <- function(hpdata, dist_name) {
  tryCatch({
    list(success = TRUE, fit = fitdist(hpdata, distr = dist_name, discrete = TRUE), error = "")
  }, error = function(e) {
    list(success = FALSE, fit = NULL, error = e$message)
  })
}

get_nbinom_simulation <- function(fit, n = 1000) {
  size <- fit$estimate["size"]
  if ("prob" %in% names(fit$estimate)) {
    return(rnbinom(n, size = size, prob = fit$estimate["prob"]))
  }
  if ("mu" %in% names(fit$estimate)) {
    return(rnbinom(n, size = size, mu = fit$estimate["mu"]))
  }
  stop("Negative Binomial fit did not return prob or mu")
}

save_discrete_distribution_plot <- function(hpdata, expected_data, name, filename, title) {
  expected_data <- expected_data[!is.na(expected_data) & is.finite(expected_data)]
  if (length(expected_data) == 0) {
    stop("No finite theoretical values generated")
  }

  density_plot <- ggplot(data = data.frame(hpdata = hpdata), aes(x = hpdata)) +
    geom_histogram(aes(y = ..density..), bins = 20, fill = "lightblue", color = "#2f87bd", size = 0.1) +
    profile_theme() +
    labs(y = "Density", x = name) +
    geom_density(aes(color = "Empirical"), lwd = 0.7) +
    geom_density(data = data.frame(value = expected_data), aes(x = value, color = "Theoretical"), lwd = 0.7) +
    scale_color_manual(values = c("Empirical" = "black", "Theoretical" = "red")) +
    theme(legend.position = c(0.83, 0.93)) +
    guides(color = guide_legend(title = NULL), override.aes = list(fill = NA, linetype = 1, shape = 15))

  qq_plot <- ggplot() +
    geom_point(aes(
      x = quantile(hpdata, probs = seq(0, 1, by = 0.01), na.rm = TRUE),
      y = quantile(expected_data, probs = seq(0, 1, by = 0.01), na.rm = TRUE)
    ), color = "black", size = 0.7, shape = 1) +
    geom_abline(intercept = 0, slope = 1, color = "red", lwd = 0.7) +
    labs(x = "Theoretical Quantiles", y = "Sample Quantiles") +
    qq_theme()

  combined_plot <- ggarrange(density_plot, qq_plot, ncol = 2, heights = c(1, 1), legend = "top", common.legend = TRUE)
  combined_plot <- annotate_figure(combined_plot, top = text_grob(title, size = 14, family = "sans"))

  svg(file = filename, width = 8, height = 4)
  on.exit({
    if (dev.cur() > 1) {
      dev.off()
    }
  }, add = TRUE)
  print(combined_plot)
}

for (i in 1:nrow(df)) {
  hpdata_raw <- as.numeric(df[i, -1])
  name <- as.character(df[i, 1])
  non_finite_count <- sum(!is.na(hpdata_raw) & !is.finite(hpdata_raw))
  hpdata_clean <- hpdata_raw[!is.na(hpdata_raw) & is.finite(hpdata_raw)]

  if (non_finite_count > 0) {
    record_status(name, "Data cleaning", "Non-finite values removed", paste0("Removed ", non_finite_count, " Inf/-Inf/NaN values"))
  }

  s <- tryCatch({
    shapiro.test(hpdata_clean)
  }, error = function(e) {
    return(list(p.value = NA))
  })

  if (is.list(s) && !is.na(s$p.value)) {
    formatted_pvalue <- sprintf("%.3e", s$p.value)
  } else {
    formatted_pvalue <- "Normality test not applicable"
  }

  if (length(hpdata_clean) < 3 || length(hpdata_clean) > 5000) {
    record_status(name, "Data check", "Sample Size Out of Range", paste0("n=", length(hpdata_clean)))
    next
  }

  bb <- data.frame(hpdata = hpdata_clean)
  filename1 <- file.path(output_dir, paste0(name, ".svg"))

  box <- ggplot(bb, aes(x = "", y = hpdata)) +
    geom_boxplot(fill = "lightblue", color = "black") +
    theme_light() +
    theme(
      plot.margin = margin(10, 10, 10, 10),
      panel.border = element_rect(color = "black", fill = NA),
      text = element_text(family = "sans", size = 12),
      plot.title = element_text(hjust = 0.5, size = 14, family = "sans"),
      axis.title = element_text(size = 12, family = "sans"),
      axis.text = element_text(size = 12, family = "sans")
    ) +
    labs(y = "Value", x = "")

  x <- median(hpdata_clean)
  x1 <- sprintf("%.2f", x)

  p <- ggplot(data = data.frame(hpdata = hpdata_clean), aes(x = hpdata)) +
    geom_histogram(aes(y = ..density..), bins = 20, fill = "lightblue", color = "#2f87bd", size = 0.1) +
    geom_density(color = "black", lwd = 0.7) +
    theme_light() +
    theme(
      plot.margin = margin(10, 10, 10, 10),
      panel.border = element_rect(color = "black", fill = NA),
      text = element_text(family = "sans", size = 12),
      plot.title = element_text(hjust = 0.5, size = 14, family = "sans"),
      axis.title = element_text(size = 12, family = "sans"),
      axis.text = element_text(size = 12, family = "sans")
    ) +
    geom_vline(xintercept = x, linetype = 2, color = 'darkblue') +
    geom_text(aes(x = x + 0.3, y = -0.0002, label = paste('Median=', x1)), color = 'darkblue', size = 3.5, family = "sans") +
    labs(y = "Density", x = "")

  cp <- ggarrange(box, p, ncol = 2, heights = c(1, 1))
  title_grob <- text_grob(name, size = 14, family = "sans")
  pvalue_grob <- text_grob(paste('shapiro.test: p-value = ', formatted_pvalue), size = 10, family = "sans")
  combined_title <- gridExtra::arrangeGrob(
    title_grob,
    pvalue_grob,
    ncol = 1,
    heights = unit(c(1, 1), "lines")
  )
  final_plot <- annotate_figure(cp, top = combined_title)

  tryCatch({
    grDevices::svg(filename = filename1, width = 8, height = 4)
    print(final_plot)
    grDevices::dev.off()
    record_status(name, "Box and histogram", "Saved", filename1)
  }, error = function(e) {
    record_status(name, "Box and histogram", "Plot Saving Failed", e$message)
  })

  if (all(hpdata_clean == floor(hpdata_clean))) {
    if (all(hpdata_clean >= 0)) {
      if (all(hpdata_clean > 0)) {
        filename3 <- file.path(output_dir, paste0(name, "_nbinom.svg"))
        nbinom_fit <- fit_distribution(hpdata_clean, "nbinom")
        if (nbinom_fit$success) {
          tryCatch({
            set.seed(2025 + i)
            nbinom_expected_hpdata <- get_nbinom_simulation(nbinom_fit$fit, n = 1000)
            save_discrete_distribution_plot(
              hpdata = hpdata_clean,
              expected_data = nbinom_expected_hpdata,
              name = name,
              filename = filename3,
              title = "Negative Binomial Distribution"
            )
            record_status(name, "Negative Binomial", "Fit completed", filename3)
          }, error = function(e) {
            close_all_devices()
            record_status(name, "Negative Binomial", "Plot failed", e$message)
          })
        } else {
          record_status(name, "Negative Binomial", "Fit failed", nbinom_fit$error)
        }
      } else {
        filename2 <- file.path(output_dir, paste0(name, "_pois.svg"))
        tryCatch({
          set.seed(2025 + i)
          lambda_hpdata <- mean(hpdata_clean)
          expected_hpdata1 <- rpois(1000, lambda = lambda_hpdata)
          save_discrete_distribution_plot(
            hpdata = hpdata_clean,
            expected_data = expected_hpdata1,
            name = name,
            filename = filename2,
            title = "Poisson Distribution"
          )
          record_status(name, "Poisson", "Fit completed", filename2)
        }, error = function(e) {
          close_all_devices()
          record_status(name, "Poisson", "Plot failed", e$message)
        })
      }
    } else {
      record_status(name, "Data check", "Contains Negative Values", "Discrete distribution plot skipped")
      message("Data for ", name, " contains negative values, skipping...")
    }
  } else {
    record_status(name, "Data check", "Contains Non-Integer Values", "Discrete distribution plot skipped")
    message("Data for ", name, " contains non-integer values, skipping...")
  }

  close_all_devices()
}

write.csv(result, file.path(output_dir, "processing_results.csv"), row.names = FALSE, fileEncoding = "UTF-8")
