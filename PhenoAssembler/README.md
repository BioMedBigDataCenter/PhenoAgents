# PhenoAssembler

PhenoAssembler is an LLM-based agent for assembling structured phenotype semantics from heterogeneous phenotype metadata. For each metadata record, it identifies the feature class and core feature term, assigns eight types of semantic qualifiers, validates the structured response, and can perform an iterative self-review before producing the final output.

This repository contains the core PhenoAssembler implementation. Evaluation scripts, held-out data, model comparison outputs, and manual review files are not included.

## Output Schema

Each record is converted into one JSON-compatible result:

- `Feature_class`: `Ex_vivo`, `In_vivo`, or `Questionnaire`
- `Feature`: the core measurable phenotype concept
- `qualifier_HAP`: human anatomical part
- `qualifier_ORP`: orientation or relative position
- `qualifier_MM`: measurement method
- `qualifier_MC`: measurement condition
- `qualifier_MID`: measurement indicator
- `qualifier_SI`: statistical indicator
- `qualifier_AS`: applicable subject
- `qualifier_OT`: other qualifier

Empty qualifier fields should use the exact string `not applicable`.

## Agent Configurations

Two extraction configurations are provided in separate files:

- `full` (`phenoassembler/prompt_full.py`): the detailed configuration used by the complete agent.
- `baseline` (`phenoassembler/prompt_baseline.py`): the simplified configuration used in comparison experiments.

## Setup

```bash
pip install -r requirements.txt
```

Set an OpenAI-compatible chat-completion endpoint:

```bash
set OPENAI_API_KEY=your_api_key
set OPENAI_BASE_URL=https://api.openai.com/v1/chat/completions
set OPENAI_MODEL=your_model_name
```

On macOS/Linux, use `export` instead of `set`.

## Minimal Run

```bash
python scripts/run_phenoassembler.py ^
  --input examples/example_input.csv ^
  --output examples/example_output.xlsx ^
  --prompt-style full
```

Use `--prompt-style baseline` to run the simplified configuration.

## Notes

- The agent accepts tabular metadata in `.xlsx`, `.csv`, or `.tsv` format.
- All available columns in each row are passed to the model as metadata.
- The script uses an OpenAI-compatible `/chat/completions` API and validates responses with Pydantic.
- No API keys, private paths, experimental outputs, or evaluation scripts are included in this public package.
