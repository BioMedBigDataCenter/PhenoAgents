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

qq_theme <- function(use_light = TRUE) {
  base_theme <- if (use_light) theme_light() else theme()
  base_theme +
    theme(
      plot.margin = margin(10, 10, 10, 10),
      plot.title = element_text(hjust = 0.5, size = 14, family = "sans"),
      axis.title = element_text(size = 12, family = "sans"),
      axis.text = element_text(size = 12, family = "sans"),
      plot.background = element_blank(),
      panel.background = element_blank(),
      panel.border = element_rect(color = "black", fill = NA)
    )
}

fit_distribution <- function(hpdata, dist_name, method = "mle") {
  tryCatch({
    list(success = TRUE, fit = fitdist(hpdata, dist_name, method = method), error = "")
  }, error = function(e) {
    list(success = FALSE, fit = NULL, error = e$message)
  })
}

save_continuous_distribution_plot <- function(hpdata, name, filename, title, density_fun, density_args, quantile_fun, quantile_args, use_light_qq = TRUE, show_empirical_density = TRUE) {
  sample_quantiles <- sort(hpdata)
  theoretical_quantiles <- do.call(quantile_fun, c(list(p = ppoints(hpdata)), quantile_args))

  p1 <- ggplot(data.frame(hpdata = hpdata), aes(x = hpdata)) +
    geom_histogram(aes(y = ..density..), bins = 100, fill = "lightblue", color = "#2f87bd", size = 0.1)

  if (show_empirical_density) {
    p1 <- p1 + stat_density(aes(color = "Empirical"), lwd = 0.7, geom = "line")
  }

  p1 <- p1 +
    profile_theme() +
    labs(y = "Density", x = name) +
    stat_function(fun = density_fun, args = density_args, aes(color = "Theoretical"), lwd = 0.7) +
    scale_color_manual(values = c("Empirical" = "black", "Theoretical" = "red")) +
    theme(legend.position = c(0.83, 0.93)) +
    guides(color = guide_legend(title = NULL, override.aes = list(fill = NA, linetype = 1, shape = 15)))

  if (title == "Exponential Distribution") {
    p1 <- p1 + theme(legend.position = c(0.83, 1.2))
  }

  p2 <- ggplot(data.frame(Theoretical = theoretical_quantiles, Sample = sample_quantiles), aes(x = Theoretical, y = Sample)) +
    geom_point(color = "black", size = 0.7, shape = 1) +
    geom_abline(slope = 1, intercept = 0, color = "red", lwd = 0.7) +
    labs(x = "Theoretical Quantiles", y = "Sample Quantiles") +
    qq_theme(use_light = use_light_qq)

  combined_plot <- ggarrange(p1, p2, ncol = 2, nrow = 1, legend = "top", common.legend = TRUE)
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
  hpdata <- hpdata_raw[!is.na(hpdata_raw) & is.finite(hpdata_raw)]

  if (non_finite_count > 0) {
    record_status(name, "Data cleaning", "Non-finite values removed", paste0("Removed ", non_finite_count, " Inf/-Inf/NaN values"))
  }

  if (length(hpdata) < 2) {
    warning(paste("Row", i, "has fewer than 2 valid data points. Skipping this row. Name:", name))
    record_status(name, "Data check", "Insufficient data points", "Fewer than 2 finite non-missing values")
    next
  }

  if (length(unique(hpdata)) == 1) {
    record_status(name, "Data check", "Values are the same", "Distribution plots skipped")
    next
  }

  s <- tryCatch({
    shapiro.test(hpdata)
  }, error = function(e) {
    return(list(p.value = NA))
  })

  if (is.list(s) && !is.na(s$p.value)) {
    formatted_pvalue <- sprintf("%.3e", s$p.value)
  } else {
    formatted_pvalue <- "Normality test not applicable"
  }

  bb <- data.frame(hpdata = hpdata)
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

  x <- median(hpdata)
  x1 <- sprintf("%.2f", x)

  p <- ggplot(data = data.frame(hpdata), aes(x = hpdata)) +
    geom_histogram(aes(y = ..density..), bins = 100, fill = "lightblue", color = "#2f87bd", size = 0.1) +
    geom_density(color = "black", lwd = 0.7) +
    theme_light() +
    theme(
      plot.margin = margin(10, 10, 10, 10),
      panel.border = element_rect(color = "black", fill = NA),
      text = element_text(family = "sans", size = 0.8),
      plot.title = element_text(hjust = 0.5, size = 14, family = "sans"),
      axis.title = element_text(size = 12, family = "sans"),
      axis.text = element_text(size = 12, family = "sans"),
      legend.text = element_text(size = 10, family = "sans"),
      legend.key.size = unit(0.7, "lines"),
      legend.background = element_rect(fill = "transparent", color = NA)
    ) +
    geom_vline(xintercept = x, linetype = 2, color = 'black') +
    geom_text(aes(x = x + 0.3, y = -0.0002, label = paste('Median=', x1)), color = 'black', size = 3.5, family = "sans") +
    theme(plot.title = element_text(hjust = 0.5), plot.subtitle = element_text(hjust = 0.5)) +
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
    record_status(name, "Box and histogram", "Failed", e$message)
  })

  if (all(hpdata > 0)) {
    exp_fit <- fit_distribution(hpdata, "exp", method = "mle")
    if (exp_fit$success) {
      rate <- exp_fit$fit$estimate["rate"]
      filename2 <- file.path(output_dir, paste0(name, "_exp.svg"))
      tryCatch({
        save_continuous_distribution_plot(
          hpdata = hpdata,
          name = name,
          filename = filename2,
          title = "Exponential Distribution",
          density_fun = dexp,
          density_args = list(rate = rate),
          quantile_fun = qexp,
          quantile_args = list(rate = rate),
          use_light_qq = TRUE
        )
        record_status(name, "Exponential", "Fit completed", filename2)
      }, error = function(e) {
        close_all_devices()
        record_status(name, "Exponential", "Plot failed", e$message)
      })
    } else {
      record_status(name, "Exponential", "Fit failed", exp_fit$error)
    }

    lnorm_fit <- fit_distribution(hpdata, "lnorm", method = "mle")
    if (lnorm_fit$success) {
      meanlog <- lnorm_fit$fit$estimate["meanlog"]
      sdlog <- lnorm_fit$fit$estimate["sdlog"]
      filename3 <- file.path(output_dir, paste0(name, "_lnorm.svg"))
      tryCatch({
        save_continuous_distribution_plot(
          hpdata = hpdata,
          name = name,
          filename = filename3,
          title = "Log-Normal Distribution",
          density_fun = dlnorm,
          density_args = list(meanlog = meanlog, sdlog = sdlog),
          quantile_fun = qlnorm,
          quantile_args = list(meanlog = meanlog, sdlog = sdlog),
          use_light_qq = TRUE
        )
        record_status(name, "Log-Normal", "Fit completed", filename3)
      }, error = function(e) {
        close_all_devices()
        record_status(name, "Log-Normal", "Plot failed", e$message)
      })
    } else {
      record_status(name, "Log-Normal", "Fit failed", lnorm_fit$error)
    }
  } else {
    cauchy_fit <- fit_distribution(hpdata, "cauchy", method = "mle")
    if (cauchy_fit$success) {
      location <- cauchy_fit$fit$estimate["location"]
      scale <- cauchy_fit$fit$estimate["scale"]
      filename4 <- file.path(output_dir, paste0(name, "_cauchy.svg"))
      tryCatch({
        save_continuous_distribution_plot(
          hpdata = hpdata,
          name = name,
          filename = filename4,
          title = "Cauchy Distribution",
          density_fun = dcauchy,
          density_args = list(location = location, scale = scale),
          quantile_fun = qcauchy,
          quantile_args = list(location = location, scale = scale),
          use_light_qq = FALSE,
          show_empirical_density = FALSE
        )
        record_status(name, "Cauchy", "Fit completed", filename4)
      }, error = function(e) {
        close_all_devices()
        record_status(name, "Cauchy", "Plot failed", e$message)
      })
    } else {
      record_status(name, "Cauchy", "Fit failed", cauchy_fit$error)
    }
  }

  close_all_devices()
}

write.csv(result, file.path(output_dir, "processing_results.csv"), row.names = FALSE, fileEncoding = "UTF-8")
