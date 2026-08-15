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
if (is.null(input_file) || is.null(output_dir) || is.null(output_csv)) stop("Required args: --input --output-dir --output-csv")
if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)

MIN_SAMPLE_SIZE <- 3
MIN_EXPECTED_COUNT <- 5
GOF_THRESHOLD <- 0.05

df <- read.csv(input_file, check.names = FALSE)
if (colnames(df)[1] == "X" || colnames(df)[1] == "") df <- df[, -1]

chisq_gof <- function(observed_values, fitted_dist, fit_params) {
  obs_table <- table(observed_values)
  obs_values <- as.numeric(names(obs_table))
  obs_freq <- as.integer(obs_table)
  max_val <- max(obs_values)

  if (fitted_dist == "pois") {
    lambda <- fit_params$lambda
    expected_probs <- dpois(0:max_val, lambda = lambda)
    tail_prob <- 1 - ppois(max_val, lambda = lambda)
    n_params <- 1
  } else if (fitted_dist == "nbinom") {
    size <- fit_params$size
    if ("prob" %in% names(fit_params)) {
      prob <- fit_params$prob
    } else if ("mu" %in% names(fit_params)) {
      mu <- fit_params$mu
      prob <- size / (size + mu)
    } else {
      return(list(applicable=FALSE, statistic=NA, p.value=NA, df=NA, reason="nbinom requires prob or mu"))
    }
    expected_probs <- dnbinom(0:max_val, size = size, prob = prob)
    tail_prob <- 1 - pnbinom(max_val, size = size, prob = prob)
    n_params <- 2
  } else {
    return(list(applicable=FALSE, statistic=NA, p.value=NA, df=NA, reason="unknown distribution"))
  }

  full_obs <- rep(0, max_val + 1); names(full_obs) <- as.character(0:max_val)
  for (j in seq_along(obs_values)) full_obs[as.character(obs_values[j])] <- obs_freq[j]
  n <- sum(obs_freq)
  full_exp <- c(expected_probs * n, tail_prob * n)
  full_obs <- c(full_obs, 0)

  merged_obs <- c(); merged_exp <- c(); temp_obs <- 0; temp_exp <- 0
  for (j in seq_along(full_exp)) {
    temp_obs <- temp_obs + full_obs[j]; temp_exp <- temp_exp + full_exp[j]
    if (temp_exp >= MIN_EXPECTED_COUNT) {
      merged_obs <- c(merged_obs, temp_obs); merged_exp <- c(merged_exp, temp_exp)
      temp_obs <- 0; temp_exp <- 0
    }
  }
  if (temp_exp > 0) {
    if (length(merged_obs) > 0) {
      merged_obs[length(merged_obs)] <- merged_obs[length(merged_obs)] + temp_obs
      merged_exp[length(merged_exp)] <- merged_exp[length(merged_exp)] + temp_exp
    } else {
      return(list(applicable=FALSE, statistic=NA, p.value=NA, df=NA, reason="insufficient expected counts after merging"))
    }
  }
  if (length(merged_obs) < 2) return(list(applicable=FALSE, statistic=NA, p.value=NA, df=NA, reason="fewer than 2 bins after merging"))
  chi_stat <- sum((merged_obs - merged_exp)^2 / merged_exp)
  df_val <- length(merged_obs) - 1 - n_params
  if (df_val < 1) return(list(applicable=FALSE, statistic=chi_stat, p.value=NA, df=df_val, reason="degrees of freedom < 1"))
  list(applicable=TRUE, statistic=chi_stat, p.value=1 - pchisq(chi_stat, df=df_val), df=df_val, reason=NA)
}

empty_result <- function(name, n, status) {
  data.frame(
    variable_id=name, n_nonmissing=n, shapiro_wilk_statistic=NA, shapiro_wilk_pvalue=NA,
    pois_AIC=NA, pois_BIC=NA, pois_lambda=NA, pois_chisq_stat=NA, pois_chisq_pvalue=NA, pois_chisq_df=NA, pois_chisq_applicable=NA, pois_error=NA,
    nbinom_AIC=NA, nbinom_BIC=NA, nbinom_size=NA, nbinom_mu=NA, nbinom_chisq_stat=NA, nbinom_chisq_pvalue=NA, nbinom_chisq_df=NA, nbinom_chisq_applicable=NA, nbinom_error=NA,
    selected_distribution=NA, selected_AIC=NA, selected_BIC=NA, selected_GOF_stat=NA, selected_GOF_pvalue=NA, selected_GOF_pass=NA,
    final_status=status,
    stringsAsFactors=FALSE
  )
}

results <- data.frame()
for (i in 1:nrow(df)) {
  if (i %% 20 == 0 || i == nrow(df)) cat(sprintf("Processing %d / %d\n", i, nrow(df)))
  raw_data <- suppressWarnings(as.numeric(unlist(df[i, -1])))
  hpdata <- raw_data[!is.na(raw_data) & is.finite(raw_data)]
  name <- as.character(df[i, 1])

  if (length(hpdata) < MIN_SAMPLE_SIZE) { results <- rbind(results, empty_result(name, length(hpdata), "insufficient data")); next }
  if (!all(hpdata == floor(hpdata))) { results <- rbind(results, empty_result(name, length(hpdata), "non-integer values detected")); next }
  if (any(hpdata < 0)) { results <- rbind(results, empty_result(name, length(hpdata), "contains negative values")); next }
  if (length(unique(hpdata)) == 1) { results <- rbind(results, empty_result(name, length(hpdata), "constant values")); next }

  sw_stat <- NA; sw_pval <- NA
  tryCatch({ sw <- shapiro.test(hpdata); sw_stat <- as.numeric(sw$statistic); sw_pval <- sw$p.value }, error=function(e) {})

  pois_AIC <- pois_BIC <- pois_lambda <- pois_chisq_stat <- pois_chisq_pval <- pois_chisq_df <- NA
  pois_chisq_app <- NA; pois_error <- ""
  tryCatch({
    pois_fit <- fitdist(hpdata, distr="pois", discrete=TRUE)
    pois_AIC <- AIC(pois_fit); pois_BIC <- BIC(pois_fit); pois_lambda <- pois_fit$estimate["lambda"]
    g <- chisq_gof(hpdata, "pois", list(lambda=pois_lambda))
    pois_chisq_app <- ifelse(g$applicable, "yes", paste("no:", g$reason))
    if (g$applicable) { pois_chisq_stat <- g$statistic; pois_chisq_pval <- g$p.value; pois_chisq_df <- g$df }
  }, error=function(e) { pois_error <<- e$message; pois_chisq_app <<- paste("fit failed:", e$message) })

  nbinom_AIC <- nbinom_BIC <- nbinom_size <- nbinom_mu <- nbinom_chisq_stat <- nbinom_chisq_pval <- nbinom_chisq_df <- NA
  nbinom_chisq_app <- NA; nbinom_error <- ""
  tryCatch({
    nbinom_fit <- fitdist(hpdata, distr="nbinom", discrete=TRUE)
    nbinom_AIC <- AIC(nbinom_fit); nbinom_BIC <- BIC(nbinom_fit); nbinom_size <- nbinom_fit$estimate["size"]
    if ("mu" %in% names(nbinom_fit$estimate)) nbinom_mu <- nbinom_fit$estimate["mu"] else if ("prob" %in% names(nbinom_fit$estimate)) nbinom_mu <- nbinom_size * (1 - nbinom_fit$estimate["prob"]) / nbinom_fit$estimate["prob"]
    g <- chisq_gof(hpdata, "nbinom", list(size=nbinom_size, mu=nbinom_mu))
    nbinom_chisq_app <- ifelse(g$applicable, "yes", paste("no:", g$reason))
    if (g$applicable) { nbinom_chisq_stat <- g$statistic; nbinom_chisq_pval <- g$p.value; nbinom_chisq_df <- g$df }
  }, error=function(e) { nbinom_error <<- e$message; nbinom_chisq_app <<- paste("fit failed:", e$message) })

  passed <- c()
  if (!is.na(pois_chisq_pval) && pois_chisq_pval > GOF_THRESHOLD) passed <- c(passed, "Poisson")
  if (!is.na(nbinom_chisq_pval) && nbinom_chisq_pval > GOF_THRESHOLD) passed <- c(passed, "Negative Binomial")
  all_aic <- c(); if (!is.na(pois_AIC)) all_aic <- c(all_aic, Poisson=pois_AIC); if (!is.na(nbinom_AIC)) all_aic <- c(all_aic, `Negative Binomial`=nbinom_AIC)

  if (length(passed) > 0) {
    a <- all_aic[passed]; selected <- names(which.min(a)); selected_pass <- "yes"; final_status <- "accepted"
  } else if (length(all_aic) > 0) {
    selected <- names(which.min(all_aic)); selected_pass <- "no"
    final_status <- ifelse(!is.na(pois_chisq_pval) || !is.na(nbinom_chisq_pval), "no adequate parametric fit", "GOF test not applicable")
  } else {
    selected <- NA; selected_pass <- NA; final_status <- "all distributions failed to fit"
  }
  if (!is.na(selected) && selected == "Poisson") { selected_AIC <- pois_AIC; selected_BIC <- pois_BIC; selected_GOF_stat <- pois_chisq_stat; selected_GOF_pvalue <- pois_chisq_pval } else if (!is.na(selected)) { selected_AIC <- nbinom_AIC; selected_BIC <- nbinom_BIC; selected_GOF_stat <- nbinom_chisq_stat; selected_GOF_pvalue <- nbinom_chisq_pval } else { selected_AIC <- selected_BIC <- selected_GOF_stat <- selected_GOF_pvalue <- NA }

  results <- rbind(results, data.frame(
    variable_id=name, n_nonmissing=length(hpdata), shapiro_wilk_statistic=sw_stat, shapiro_wilk_pvalue=sw_pval,
    pois_AIC=pois_AIC, pois_BIC=pois_BIC, pois_lambda=pois_lambda, pois_chisq_stat=pois_chisq_stat, pois_chisq_pvalue=pois_chisq_pval, pois_chisq_df=pois_chisq_df, pois_chisq_applicable=pois_chisq_app, pois_error=pois_error,
    nbinom_AIC=nbinom_AIC, nbinom_BIC=nbinom_BIC, nbinom_size=nbinom_size, nbinom_mu=nbinom_mu, nbinom_chisq_stat=nbinom_chisq_stat, nbinom_chisq_pvalue=nbinom_chisq_pval, nbinom_chisq_df=nbinom_chisq_df, nbinom_chisq_applicable=nbinom_chisq_app, nbinom_error=nbinom_error,
    selected_distribution=selected, selected_AIC=selected_AIC, selected_BIC=selected_BIC, selected_GOF_stat=selected_GOF_stat, selected_GOF_pvalue=selected_GOF_pvalue, selected_GOF_pass=selected_pass,
    final_status=final_status,
    stringsAsFactors=FALSE
  ))
}

write.csv(results, output_csv, row.names=FALSE, fileEncoding="UTF-8")
cat("Done:", output_csv, "\n")
