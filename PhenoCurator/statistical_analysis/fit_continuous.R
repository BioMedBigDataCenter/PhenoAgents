library(fitdistrplus)

parse_args <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  out <- list()
  flags <- c("--input", "--output-dir", "--output-csv")
  i <- 1
  while (i <= length(args)) {
    key <- args[[i]]
    if (key %in% flags && i < length(args)) {
      out[[substring(key, 3)]] <- args[[i + 1]]
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
output_csv <- args[["output-csv"]]
if (is.null(input_file) || is.null(output_dir) || is.null(output_csv)) {
  stop("Required args: --input --output-dir --output-csv")
}
if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)

MIN_SAMPLE_SIZE <- 2
GOF_THRESHOLD <- 0.05

df <- read.csv(input_file, check.names = FALSE)
if (colnames(df)[1] == "X" || colnames(df)[1] == "") df <- df[, -1]

fit_and_metrics <- function(data, dist_name, method = "mle") {
  tryCatch({
    fit <- fitdist(data, distr = dist_name, method = method)
    if (dist_name == "norm") {
      ks_result <- ks.test(data, "pnorm", mean = fit$estimate["mean"], sd = fit$estimate["sd"])
    } else if (dist_name == "lnorm") {
      ks_result <- ks.test(data, "plnorm", meanlog = fit$estimate["meanlog"], sdlog = fit$estimate["sdlog"])
    } else if (dist_name == "exp") {
      ks_result <- ks.test(data, "pexp", rate = fit$estimate["rate"])
    } else if (dist_name == "cauchy") {
      ks_result <- ks.test(data, "pcauchy", location = fit$estimate["location"], scale = fit$estimate["scale"])
    } else {
      ks_result <- list(statistic = NA, p.value = NA)
    }
    list(success = TRUE, AIC = AIC(fit), BIC = BIC(fit), ks_stat = as.numeric(ks_result$statistic), ks_pvalue = ks_result$p.value, error_msg = "")
  }, error = function(e) {
    list(success = FALSE, AIC = NA, BIC = NA, ks_stat = NA, ks_pvalue = NA, error_msg = e$message)
  })
}

empty_result <- function(name, n, status) {
  data.frame(
    variable_id = name, n_nonmissing = n,
    shapiro_wilk_statistic = NA, shapiro_wilk_pvalue = NA,
    normal_AIC = NA, normal_BIC = NA, normal_KS_stat = NA, normal_KS_pvalue = NA, normal_error = NA,
    lnorm_AIC = NA, lnorm_BIC = NA, lnorm_KS_stat = NA, lnorm_KS_pvalue = NA, lnorm_applicable = NA, lnorm_error = NA,
    exp_AIC = NA, exp_BIC = NA, exp_KS_stat = NA, exp_KS_pvalue = NA, exp_applicable = NA, exp_error = NA,
    cauchy_AIC = NA, cauchy_BIC = NA, cauchy_KS_stat = NA, cauchy_KS_pvalue = NA, cauchy_error = NA,
    selected_distribution = NA, selected_AIC = NA, selected_BIC = NA,
    selected_KS_stat = NA, selected_KS_pvalue = NA, selected_KS_pass = NA,
    final_status = status,
    stringsAsFactors = FALSE
  )
}

results <- data.frame()
for (i in 1:nrow(df)) {
  if (i %% 500 == 0 || i == nrow(df)) cat(sprintf("Processing %d / %d\n", i, nrow(df)))
  raw_data <- suppressWarnings(as.numeric(unlist(df[i, -1])))
  hpdata <- raw_data[!is.na(raw_data) & is.finite(raw_data)]
  name <- as.character(df[i, 1])

  if (length(hpdata) < MIN_SAMPLE_SIZE) {
    results <- rbind(results, empty_result(name, length(hpdata), "insufficient data")); next
  }
  if (length(unique(hpdata)) == 1) {
    results <- rbind(results, empty_result(name, length(hpdata), "constant values")); next
  }

  sw_stat <- NA; sw_pval <- NA
  tryCatch({
    if (length(hpdata) >= 3 && length(hpdata) <= 5000) {
      sw <- shapiro.test(hpdata); sw_stat <- as.numeric(sw$statistic); sw_pval <- sw$p.value
    }
  }, error = function(e) {})

  has_negative <- any(hpdata < 0)
  has_zero_or_negative <- any(hpdata <= 0)
  res_norm <- fit_and_metrics(hpdata, "norm")
  if (!has_zero_or_negative) { res_lnorm <- fit_and_metrics(hpdata, "lnorm"); lnorm_applicable <- "yes" } else { res_lnorm <- list(success=FALSE,AIC=NA,BIC=NA,ks_stat=NA,ks_pvalue=NA,error_msg="not applicable"); lnorm_applicable <- "no: contains zero or negative values" }
  if (!has_negative) { res_exp <- fit_and_metrics(hpdata, "exp"); exp_applicable <- "yes" } else { res_exp <- list(success=FALSE,AIC=NA,BIC=NA,ks_stat=NA,ks_pvalue=NA,error_msg="not applicable"); exp_applicable <- "no: contains negative values" }
  res_cauchy <- fit_and_metrics(hpdata, "cauchy")

  candidates <- list(Normal=res_norm, `Log-normal`=res_lnorm, Exponential=res_exp, Cauchy=res_cauchy)
  passed_names <- names(candidates)[sapply(candidates, function(x) isTRUE(x$success) && !is.na(x$ks_pvalue) && x$ks_pvalue > GOF_THRESHOLD)]
  all_success <- names(candidates)[sapply(candidates, function(x) isTRUE(x$success) && !is.na(x$AIC))]

  if (length(passed_names) > 0) {
    selected <- passed_names[which.min(sapply(candidates[passed_names], function(x) x$AIC))]
    selected_pass <- "yes"; final_status <- "accepted"
  } else if (length(all_success) > 0) {
    selected <- all_success[which.min(sapply(candidates[all_success], function(x) x$AIC))]
    selected_pass <- "no"; final_status <- "no adequate parametric fit"
  } else {
    selected <- NA; selected_pass <- NA; final_status <- "all distributions failed to fit"
  }
  sel <- if (!is.na(selected)) candidates[[selected]] else list(AIC=NA,BIC=NA,ks_stat=NA,ks_pvalue=NA)

  results <- rbind(results, data.frame(
    variable_id = name, n_nonmissing = length(hpdata),
    shapiro_wilk_statistic = sw_stat, shapiro_wilk_pvalue = sw_pval,
    normal_AIC = res_norm$AIC, normal_BIC = res_norm$BIC, normal_KS_stat = res_norm$ks_stat, normal_KS_pvalue = res_norm$ks_pvalue, normal_error = res_norm$error_msg,
    lnorm_AIC = res_lnorm$AIC, lnorm_BIC = res_lnorm$BIC, lnorm_KS_stat = res_lnorm$ks_stat, lnorm_KS_pvalue = res_lnorm$ks_pvalue, lnorm_applicable = lnorm_applicable, lnorm_error = res_lnorm$error_msg,
    exp_AIC = res_exp$AIC, exp_BIC = res_exp$BIC, exp_KS_stat = res_exp$ks_stat, exp_KS_pvalue = res_exp$ks_pvalue, exp_applicable = exp_applicable, exp_error = res_exp$error_msg,
    cauchy_AIC = res_cauchy$AIC, cauchy_BIC = res_cauchy$BIC, cauchy_KS_stat = res_cauchy$ks_stat, cauchy_KS_pvalue = res_cauchy$ks_pvalue, cauchy_error = res_cauchy$error_msg,
    selected_distribution = selected, selected_AIC = sel$AIC, selected_BIC = sel$BIC,
    selected_KS_stat = sel$ks_stat, selected_KS_pvalue = sel$ks_pvalue, selected_KS_pass = selected_pass,
    final_status = final_status,
    stringsAsFactors = FALSE
  ))
}

write.csv(results, output_csv, row.names = FALSE, fileEncoding = "UTF-8")
cat("Done:", output_csv, "\n")
