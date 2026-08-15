suppressPackageStartupMessages({
  library(ggplot2)
  library(ggrepel)
  library(RColorBrewer)
  library(scales)
  library(grid)
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
qual_data <- read.csv(input_file, check.names = FALSE, stringsAsFactors = FALSE, fileEncoding = "UTF-8-BOM")
colnames(qual_data)[1] <- "name"
sample_cols <- 2:ncol(qual_data)


qual_data[] <- lapply(qual_data, function(x) ifelse(x == "", NA, x))

sample_count <- length(sample_cols)
na_count <- rowSums(is.na(qual_data[, sample_cols, drop = FALSE]))

summary_data <- data.frame(
  dataCode = qual_data$name,
  na.count = na_count,
  na.ratio = "",
  no.na = sample_count - na_count,
  no.na.ratio = "",
  stringsAsFactors = FALSE
)

summary_data[is.na(summary_data)] <- 0

for (i in 1:nrow(summary_data)) {
  summary_data$na.ratio[i] <- paste0(round(as.numeric(summary_data$na.count[i]) / sample_count, 4) * 100, "%")
  summary_data$no.na.ratio[i] <- paste0(round(as.numeric(summary_data$no.na[i]) / sample_count, 4) * 100, "%")
}

plotdata <- list()
for (i in 1:nrow(qual_data)) {
  plotdata[[i]] <- table(unlist(unname(qual_data[i, sample_cols])))
}
names(plotdata) <- summary_data$dataCode
summary_data$index <- ""
summary_data$index.num <- ""
for (i in 1:nrow(summary_data)) {
  summary_data$index.num[i] <- as.numeric(length(plotdata[[i]]))
  if (summary_data$index.num[i] == 0) {
    summary_data$index[i] <- ""
  } else {
    summary_data$index[i] <- paste(unlist(names(plotdata[[i]])), collapse = "|")
  }
}

write.csv(summary_data, file.path(output_dir, "qualitative_plot_summary.csv"), row.names = FALSE, fileEncoding = "UTF-8")

qual_col_pals <- brewer.pal.info[brewer.pal.info$category == 'qual', ]
col_vector <- unlist(mapply(brewer.pal, qual_col_pals$maxcolors, rownames(qual_col_pals)))

Dir <- output_dir
if (!dir.exists(Dir)) {
  dir.create(Dir, recursive = TRUE)
}
if (!dir.exists(file.path(Dir, "svg"))) {
  dir.create(file.path(Dir, "svg"), recursive = TRUE)
}

save_qual_plot <- function(plot_obj, file_name) {
  filename <- file.path(Dir, "svg", paste0(file_name, ".svg"))
  grDevices::svg(filename = filename, width = 8, height = 4)
  print(plot_obj)
  grDevices::dev.off()
}

make_small_category_plot <- function(data_plot, variable_name, title_text, colour_count) {
  ggplot(data_plot, aes(x = name, fill = variable)) +
    geom_bar(width = 0.5, position = "fill") +
    coord_flip() +
    scale_fill_manual(values = col_vector[1:colour_count]) +
    guides(fill = guide_legend(reverse = FALSE)) +
    scale_y_continuous(labels = percent) +
    theme(axis.title.x = element_blank()) +
    guides(fill = guide_legend(title = "Variables Name")) +
    labs(title = title_text, x = "", y = "Percent") +
    theme_minimal(base_family = "Arial") +
    theme(
      axis.text.y = element_blank(),
      axis.text.x = element_text(size = 15, hjust = 1, family = "sans"),
      panel.background = element_rect(fill = "white"),
      axis.title.x = element_text(size = 20),
      legend.title = element_text(size = 18),
      legend.text = element_text(size = 10),
      plot.title = element_text(size = 20, hjust = 0.5, family = "sans"),
      legend.key.size = unit(0.6, "lines")
    ) +
    geom_label_repel(
      aes(label = scales::percent(..count.. / sum(..count..))),
      stat = "count",
      position = position_fill(vjust = 0.5),
      size = 3,
      max.overlaps = 50,
      show.legend = FALSE
    )
}

make_large_category_plot <- function(category_data, title_text, colour_count, axis_text_size, legend_key_size) {
  ggplot(category_data, aes(x = index_replace, y = num, fill = index_replace)) +
    geom_bar(stat = "identity") +
    geom_text(aes(label = num), vjust = -0.3, size = 4) +
    guides(fill = guide_legend(title = "Variables Name")) +
    labs(title = title_text, x = "", y = "Number") +
    theme_minimal(base_family = "Arial") +
    theme(
      axis.text.x = element_text(size = axis_text_size, angle = 70, hjust = 1, family = "sans"),
      axis.text.y = element_text(size = 15),
      axis.title.x = element_text(size = 15),
      axis.title.y = element_text(size = 15),
      legend.title = element_text(size = 18),
      legend.text = element_text(size = 10),
      plot.title = element_text(size = 20, hjust = 0.5, family = "sans"),
      panel.background = element_rect(fill = "white"),
      legend.key.size = unit(legend_key_size, "lines")
    ) +
    scale_fill_manual(values = col_vector[1:colour_count])
}

for (i in 1:nrow(qual_data)) {
  cat(i, "\n")
  category_data <- as.data.frame(plotdata[i])


  if (nrow(category_data) > 0) {
    colnames(category_data) <- c("index", "num")
    category_data <- category_data[!is.na(category_data$index) & as.character(category_data$index) != "", , drop = FALSE]

    if (nrow(category_data) != 0) {
      category_data <- category_data[order(category_data$num, decreasing = TRUE), ]
      category_data$index_replace <- paste0("Variable.", 1:nrow(category_data))

      data_index <- as.character(category_data$index_replace)
      data_num <- as.integer(category_data$num)
      repeated_vars <- rep(data_index, times = data_num)
      data_plot <- data.frame(variable = repeated_vars, name = names(plotdata[i]))
      colourCount <- length(data_index)
      level <- data_index
      data_plot$variable <- factor(data_plot$variable, levels = level)
      title_text <- paste0(summary_data$dataCode[i], "(", summary_data$no.na.ratio[i], ")")

      if ((as.numeric(summary_data$index.num[i]) > 0) & (as.numeric(summary_data$index.num[i]) <= 15)) {
        plot <- make_small_category_plot(data_plot, names(plotdata[i]), title_text, colourCount)
        save_qual_plot(plot, names(plotdata[i]))
      } else if (as.numeric((as.numeric(summary_data$index.num[i]) > 15) & (as.numeric(summary_data$index.num[i]) < 25))) {
        category_data$index_replace <- factor(category_data$index_replace, levels = level)
        plot <- make_large_category_plot(category_data, title_text, colourCount, axis_text_size = 10, legend_key_size = 0.6)
        save_qual_plot(plot, names(plotdata[i]))
      } else if (as.numeric(summary_data$index.num[i]) >= 25) {
        category_data$index_replace <- factor(category_data$index_replace, levels = level)
        plot <- make_large_category_plot(category_data, title_text, colourCount, axis_text_size = 6, legend_key_size = 0.3)
        save_qual_plot(plot, names(plotdata[i]))
      }
    }
  }
}
