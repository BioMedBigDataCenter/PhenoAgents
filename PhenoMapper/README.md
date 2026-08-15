# PhenoMapper

PhenoMapper is an LLM-based agent for phenotype-term mapping, released with the accompanying manuscript. The agent performs semantic routing, selects and queries public biomedical resources, re-ranks ontology candidates, and invokes a literature fallback when no structured candidate is returned.

This repository contains the core agent workflow and the two prompt variants examined in the study. Study data, generated outputs, and evaluation utilities are outside the scope of this release.

## Contents

- `phenomapper.py` — the core agent workflow.
- `prompts/full.md` and `prompts/brief.md` — the two prompt variants examined in the study.
- `example_input.csv` — a schema-only example input.

## Configuration

The agent reads credentials only from environment variables; no credentials are included in this repository.

| Variable | Purpose |
| --- | --- |
| `LLM_API_KEY` | API key for an OpenAI-compatible chat-completions endpoint. |
| `LLM_API_URL` | Endpoint URL. |
| `LLM_MODEL` | Model identifier. |
| `BIOPORTAL_API_KEY` | Optional key for BioPortal ontology search. |

## Main parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `--input` | required | CSV file containing a `term` column. |
| `--prompt` | `full` | Prompt variant: `full` or `brief`. |
| `--top-k` | `10` | Maximum ontology candidates returned per term. |
| `--output` | `results.json` | JSON path for generated results. |
| `--temperature` | `0.2` | LLM sampling temperature. |

The agent queries BioPortal for non-molecular terms, selected public gene, protein, metabolite, and taxonomy resources for molecular terms, and PubMed when no structured candidate is returned.
