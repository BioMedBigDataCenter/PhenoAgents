# PhenoCurator

PhenoCurator is a large language model-based agent for phenotype data quality control. It examines phenotype metadata and observed values, identifies candidate missing and anomalous values, infers variable types, and supports downstream statistical characterization and visualization.

## Repository contents

This repository provides:

- the PhenoCurator agent implementation for OpenAI-compatible chat-completion endpoints;
- the two prompts evaluated in the simulation experiments;
- three synthetic phenotype datasets and their reference annotations;
- examples of the three supported metadata input levels;
- continuous and discrete distribution fitting;
- continuous, discrete, and qualitative visualization; and
- the NHANES variable list and participant identifiers used to define the study subset.

Model outputs, evaluation scripts, parallel launchers, repeated-run scripts, complete phenotype metadata, and NHANES measurement data are not included.

## Benchmark parameters

| Parameter | Manuscript description |
| --- | --- |
| `name_only` | Name only |
| `basic_metadata` | Basic metadata |
| `enhanced_metadata` | Enhanced metadata |
| `explicit` | Dataset 1: Explicit Anomaly Dataset |
| `format_coding` | Dataset 2: Format and Coding Anomaly Dataset |
| `semantic_context` | Dataset 3: Semantic-Context-Dependent Anomaly Dataset |

## Data and annotations

Each phenotype matrix contains one variable per row. The first column is the phenotype variable name, and columns `P1` through `P1000` contain participant-level values. Values are read as strings before unique values are extracted for agent analysis.

The synthetic matrices and their reference annotations are located together in `data/simulation_dataset/`:

- `dataset_1_explicit.csv` and `dataset_1_explicit.xlsx`
- `dataset_2_format_coding.csv` and `dataset_2_format_coding.xlsx`
- `dataset_3_semantic_context.csv` and `dataset_3_semantic_context.xlsx`

The CSV files are the matrices read by the agent in the reported experiments. Their values are unchanged from the experiment files; only the text encoding was converted from GB18030 to UTF-8 for repository portability. The XLSX files are also provided because they preserve the source spreadsheet representation of missing-value markers. In Dataset 1, exporting the source workbook to CSV converted several marker strings, including `NA`, `N/A`, `n/a`, `NaN`, `null`, and `None`, to empty fields. The distributed CSV files have not been altered to restore those strings.

Two complementary annotation files are provided for each dataset in the same directory:

- `dataset_*_anomaly_summary.xlsx` is a byte-identical copy of the corresponding `answer_*.xlsx` file supplied with the synthetic dataset. It records anomaly counts and a display summary of anomalous values for each phenotype variable. Some display summaries list the first 20 unique values followed by the total number of unique values; these summaries should not be treated as complete value-level annotations.
- `dataset_*_cell_labels.xlsx` mirrors the 200 by 1,000 phenotype matrix and labels each participant-level cell as `normal` or `anomaly`. It supports point-level evaluation.

The cell-level label files are byte-identical copies of the supplied `ground_truth_*.xlsx` files and are the complete reference annotations. They can be joined to either matrix representation by `Term` and participant column (`P1` through `P1000`).

The metadata files in `data/metadata_examples/` demonstrate the expected columns for each input-information level. Each file contains three representative phenotype variables.

The files in `data/nhanes_information/` contain the 114 phenotype variable names and 1,000 participant identifiers used to define the NHANES study subset. Measurement data can be obtained from the official NHANES source.

## Software

Python 3.10 or later is required with `pandas`, `requests`, and `openpyxl`. Distribution fitting and plotting were developed with R 4.3.1 and use `fitdistrplus`, `ggplot2`, `ggpubr`, `ggrepel`, `gridExtra`, `RColorBrewer`, and `scales`.

## Model configuration

PhenoCurator communicates with an OpenAI-compatible chat-completion endpoint. Credentials are read from environment variables and are not stored in the source code.

```powershell
$env:PHENOCURATOR_API_URL = "https://example.org/v1/chat/completions"
$env:PHENOCURATOR_API_KEY = Read-Host "API key"
$env:PHENOCURATOR_MODEL = "model-name"
```

The default temperature is `0.2`, consistent with the manuscript experiments.

## Running the agent

Name-only analysis does not require a metadata file:

```powershell
python agent/run_qc.py `
  --dataset explicit `
  --input-level name_only `
  --prompt prompt2 `
  --output output/qc_result.csv
```

Basic or enhanced metadata analysis additionally requires `--metadata path/to/metadata.xlsx`.

The complete sequence, from agent-based quality control through statistical analysis and plotting, can be selected with `agent/run_pipeline.py` using `--start-step` and `--end-step`. Valid steps are `qc`, `profile`, and `plots`.

## Statistical characterization

After agent-based quality control, distribution fitting and plots can be generated with:

```powershell
python agent/run_profile.py `
  --input data/simulation_dataset/dataset_1_explicit.csv `
  --qc-result output/qc_result.csv `
  --profile-mode raw `
  --run-distribution `
  --run-plots `
  --output-dir output/profile
```

Use `candidate_filtered` instead of `raw` to replace values identified by the agent as candidate missing or anomalous values before statistical characterization.

Continuous variables are evaluated against normal, log-normal, exponential, and Cauchy distributions, while discrete count variables are evaluated against Poisson and negative binomial distributions. Candidate models passing the goodness-of-fit criterion (`p > 0.05`) are compared by AIC; if none passes, the fitted model with the lowest AIC is retained and marked as an inadequate fit. The output includes AIC, BIC, goodness-of-fit statistics and p-values, selected-model indicators, and fitting status.

Qualitative variables are summarized using observed category frequencies and proportions. Plots are saved as SVG files.

## Use

Copyright is retained by the authors. No software license is granted unless separate permission is provided.
