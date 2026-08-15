from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATASET_FILES = {
    "explicit": ROOT / "data" / "simulation_dataset" / "dataset_1_explicit.csv",
    "format_coding": ROOT / "data" / "simulation_dataset" / "dataset_2_format_coding.csv",
    "semantic_context": ROOT / "data" / "simulation_dataset" / "dataset_3_semantic_context.csv",
}
INPUT_LEVELS = {"name_only", "basic_metadata", "enhanced_metadata"}
VARIABLE_TYPES = {
    "Continuous variable",
    "Discrete variable",
    "Ordinal variable",
    "Nominal variable",
    "NA variable",
    "ZERO variable",
    "Duplicate variable",
}
RESULT_FIELDS = (
    "variable_type",
    "specified_minimal_value",
    "specified_maximal_value",
    "na_values",
    "anomalous_values",
)


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"Cannot decode CSV: {path}")


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=object)
    return read_csv(path, dtype=object, keep_default_na=False)


def normalize_identifier(value: Any) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def parse_metadata_json(value: Any) -> dict[str, Any]:
    if value is None or (not isinstance(value, (dict, list)) and pd.isna(value)):
        return {}
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


class MetadataIndex:
    def __init__(self, path: Path | None) -> None:
        self.by_id: dict[str, dict[str, Any]] = {}
        self.by_term: dict[str, dict[str, Any]] = {}
        if path is None:
            return
        frame = read_table(path)
        for _, row in frame.iterrows():
            record = {str(key): value for key, value in row.to_dict().items()}
            data_id = normalize_identifier(record.get("Dataid", ""))
            term = str(record.get("Term", "")).strip()
            if data_id:
                self.by_id[data_id] = record
            if term:
                self.by_term[term] = record

    def find(self, key: str) -> dict[str, Any] | None:
        return self.by_id.get(normalize_identifier(key)) or self.by_term.get(key)


def clean_metadata_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value is None or pd.isna(value):
        return "<NA>"
    return value


def metadata_payload(
    input_level: str,
    variable_key: str,
    record: dict[str, Any] | None,
) -> tuple[str, str, dict[str, Any]]:
    if record is None:
        if input_level != "name_only":
            raise KeyError(f"No metadata row found for variable: {variable_key}")
        return variable_key, variable_key, {"name": variable_key}

    data_id = normalize_identifier(record.get("Dataid", variable_key))
    term = str(record.get("Term", variable_key)).strip() or variable_key
    if input_level == "name_only":
        return data_id, term, {"name": term}

    payload = {
        key: clean_metadata_value(record.get(key))
        for key in ("Term", "Class", "Description", "DataType")
        if key in record
    }
    if input_level == "basic_metadata":
        payload.update(parse_metadata_json(record.get("JSON")))
    else:
        payload.update(parse_metadata_json(record.get("JSON_new")))
        for key in ("ID", "Detection item"):
            if key in record:
                payload[key] = clean_metadata_value(record.get(key))
    return data_id, term, payload


def metadata_guidance(input_level: str) -> str:
    if input_level == "name_only":
        return (
            "Only the variable name is provided. Use the variable name and observed values "
            "to infer what this variable measures. Do not assume unavailable metadata."
        )
    if input_level == "basic_metadata":
        return (
            "Use the provided basic metadata, including the name, variable class, description, "
            "data type, unit or valid range, and available enumerations when present."
        )
    return (
        "Use the provided enhanced metadata. In addition to the basic fields, feature describes "
        "the core measurable phenotype, feature_class describes the measurement category, and "
        "Q_ fields provide structured qualifiers such as anatomy, orientation, tools, units, "
        "conditions, indicators, and applicable subjects."
    )


def response_schema() -> dict[str, Any]:
    result_properties = {
        "variable_type": {"type": "string", "enum": sorted(VARIABLE_TYPES)},
        "specified_minimal_value": {"anyOf": [{"type": "number"}, {"const": "(not applicable)"}]},
        "specified_maximal_value": {"anyOf": [{"type": "number"}, {"const": "(not applicable)"}]},
        "na_values": {"type": "array", "items": {"type": "string"}},
        "anomalous_values": {"type": "array", "items": {"type": "string"}},
    }
    return {
        "type": "object",
        "required": ["result", "explanation"],
        "properties": {
            "result": {
                "type": "object",
                "required": list(RESULT_FIELDS),
                "properties": result_properties,
                "additionalProperties": False,
            },
            "explanation": {
                "type": "object",
                "required": list(RESULT_FIELDS),
                "additionalProperties": {"type": "string"},
            },
        },
        "additionalProperties": False,
    }


def load_prompt(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    marker = "[SUBSEQUENT_BATCH]"
    if "[FIRST_BATCH]" not in text or marker not in text:
        raise ValueError(f"Prompt file must contain [FIRST_BATCH] and {marker}: {path}")
    first, subsequent = text.split(marker, 1)
    return first.replace("[FIRST_BATCH]", "", 1).strip(), subsequent.strip()


def unique_values(series: pd.Series) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for value in series.tolist():
        text = "<NA>" if pd.isna(value) else str(value)
        if text not in seen:
            seen.add(text)
            values.append(text)
    return values


def balanced_batches(values: list[str], maximum: int = 100) -> list[list[str]]:
    if not values:
        return [[]]
    count = math.ceil(len(values) / maximum)
    size = math.ceil(len(values) / count)
    return [values[start : start + size] for start in range(0, len(values), size)]


def strip_control_characters(text: str) -> str:
    return "".join(char for char in text if char in "\n\r\t" or ord(char) >= 32)


def extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidate = match.group(1) if match else text.strip()
    parsed = json.loads(strip_control_characters(candidate))
    if not isinstance(parsed, dict):
        raise ValueError("The model response is not a JSON object")
    return parsed


def normalize_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return list(dict.fromkeys(str(item) for item in value))


def validate_profile(payload: dict[str, Any], observed: set[str]) -> dict[str, Any]:
    if set(payload) != {"result", "explanation"}:
        raise ValueError("Response must contain only result and explanation")
    result = payload["result"]
    explanation = payload["explanation"]
    if not isinstance(result, dict) or set(result) != set(RESULT_FIELDS):
        raise ValueError("Result fields do not match the required schema")
    if not isinstance(explanation, dict) or set(explanation) != set(RESULT_FIELDS):
        raise ValueError("Explanation keys do not match result fields")
    if result["variable_type"] not in VARIABLE_TYPES:
        raise ValueError("Unknown variable_type")
    for field in ("specified_minimal_value", "specified_maximal_value"):
        value = result[field]
        if value != "(not applicable)" and not isinstance(value, (int, float)):
            raise ValueError(f"{field} must be numeric or '(not applicable)'")
    result["na_values"] = normalize_string_list(result["na_values"], "na_values")
    result["anomalous_values"] = normalize_string_list(result["anomalous_values"], "anomalous_values")
    overlap = set(result["na_values"]) & set(result["anomalous_values"])
    if overlap:
        raise ValueError(f"na_values and anomalous_values overlap: {sorted(overlap)}")
    flagged = set(result["na_values"]) | set(result["anomalous_values"])
    unseen = flagged - observed
    if unseen:
        raise ValueError(f"Flagged values were not observed: {sorted(unseen)}")
    if not all(isinstance(explanation[field], str) for field in RESULT_FIELDS):
        raise ValueError("Every explanation value must be a string")
    return payload


class ModelRequestError(RuntimeError):
    pass


class ChatClient:
    def __init__(self, api_url: str, model: str, api_key: str, timeout: int, temperature: float) -> None:
        self.api_url = api_url
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature

    def ask(self, messages: list[dict[str, str]]) -> str:
        try:
            import requests
        except ImportError as exc:
            raise ModelRequestError(
                "The 'requests' package is required to call the model API"
            ) from exc

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "stream": False,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except Exception as exc:
            raise ModelRequestError(f"Model API request failed: {exc}") from exc


def extract_validated(
    client: ChatClient,
    messages: list[dict[str, str]],
    observed: set[str],
    max_retries: int,
) -> dict[str, Any]:
    working = list(messages)
    last_error: Exception | None = None
    for _ in range(max_retries + 1):
        answer = client.ask(working)
        try:
            return validate_profile(extract_json(answer), observed)
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            working.extend(
                [
                    {"role": "assistant", "content": answer},
                    {
                        "role": "user",
                        "content": (
                            f"Validation failed: {exc}. Revise the response. Return only one JSON object "
                            "that matches the required schema."
                        ),
                    },
                ]
            )
    raise RuntimeError(f"Model output validation failed: {last_error}")


def apply_self_critique(
    client: ChatClient,
    messages: list[dict[str, str]],
    profile: dict[str, Any],
    observed: set[str],
    max_retries: int,
    max_critics: int,
) -> dict[str, Any]:
    current = profile
    for _ in range(max_critics):
        critic_messages = messages + [
            {"role": "assistant", "content": json.dumps(current, ensure_ascii=False)},
            {
                "role": "user",
                "content": (
                    "Review the answer against every instruction. Check the variable type, candidate missing "
                    "values, candidate anomalous values, mutual exclusivity, specified range, observed-value "
                    "constraint, and explanation keys. Return only JSON with fields needed (boolean) and "
                    "message (string or null)."
                ),
            },
        ]
        critic = extract_json(client.ask(critic_messages))
        if set(critic) != {"needed", "message"} or not isinstance(critic["needed"], bool):
            continue
        if not critic["needed"]:
            break
        revision_messages = messages + [
            {"role": "assistant", "content": json.dumps(current, ensure_ascii=False)},
            {
                "role": "user",
                "content": (
                    f"Revise the answer for this reason: {critic.get('message')}. Return only one JSON object "
                    "that matches the required schema."
                ),
            },
        ]
        current = extract_validated(client, revision_messages, observed, max_retries)
    return current


def build_messages(
    metadata: dict[str, Any],
    examples: list[str],
    batch: list[str],
    input_level: str,
    rules: str,
    previous: dict[str, Any] | None,
) -> list[dict[str, str]]:
    sections = [
        "# DETERMINE THE DATA PROFILE OF A COLUMN",
        "## Metadata of the column",
        json.dumps(metadata, ensure_ascii=False, indent=2),
        "## Metadata guidance",
        metadata_guidance(input_level),
        "## Example data points",
        json.dumps(examples, ensure_ascii=False),
        "## Response format",
        json.dumps(response_schema(), ensure_ascii=False, indent=2),
    ]
    if previous is not None:
        sections.extend(["## Previous answer", json.dumps(previous, ensure_ascii=False, indent=2)])
    sections.extend(
        [
            "## Values in the current batch",
            json.dumps(batch, ensure_ascii=False),
            "## Requirements",
            rules,
        ]
    )
    return [
        {
            "role": "system",
            "content": "You are an advanced data scientist performing phenotype data quality control.",
        },
        {"role": "user", "content": "\n\n".join(sections)},
    ]


def special_profile(values: list[str]) -> dict[str, Any] | None:
    if values and all(value == "0" for value in values):
        variable_type = "ZERO variable"
    elif len(values) == 1:
        variable_type = "Duplicate variable"
    else:
        return None
    result = {
        "variable_type": variable_type,
        "specified_minimal_value": "(not applicable)",
        "specified_maximal_value": "(not applicable)",
        "na_values": [],
        "anomalous_values": [],
    }
    explanation = {field: "Assigned deterministically from the observed column values." for field in RESULT_FIELDS}
    return {"result": result, "explanation": explanation}


def run_variable(
    client: ChatClient,
    values: list[str],
    metadata: dict[str, Any],
    input_level: str,
    first_rules: str,
    subsequent_rules: str,
    max_retries: int,
    max_critics: int,
) -> dict[str, Any]:
    deterministic = special_profile(values)
    if deterministic is not None:
        return deterministic
    observed = set(values)
    examples = values[:10]
    current: dict[str, Any] | None = None
    for index, batch in enumerate(balanced_batches(values)):
        rules = first_rules if index == 0 else subsequent_rules
        messages = build_messages(metadata, examples, batch, input_level, rules, current)
        current = extract_validated(client, messages, observed, max_retries)
        current = apply_self_critique(
            client, messages, current, observed, max_retries, max_critics
        )
    if current is None:
        raise RuntimeError("No profile was produced")
    return current


def write_results(records: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output, index=False, encoding="utf-8-sig")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the PhenoCurator agent with an OpenAI-compatible model"
    )
    parser.add_argument("--dataset", choices=[*DATASET_FILES, "nhanes", "custom"], required=True)
    parser.add_argument("--input", type=Path, help="Input matrix CSV; required for nhanes or custom")
    parser.add_argument("--metadata", type=Path, help="Metadata CSV/XLSX; required except for name_only")
    parser.add_argument("--input-level", choices=sorted(INPUT_LEVELS), required=True)
    parser.add_argument("--prompt", choices=["prompt1", "prompt2"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-url", default=os.getenv("PHENOCURATOR_API_URL", ""))
    parser.add_argument("--model", default=os.getenv("PHENOCURATOR_MODEL", ""))
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=130)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-critics", type=int, default=3)
    parser.add_argument("--row-retries", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_path = args.input or DATASET_FILES.get(args.dataset)
    if input_path is None:
        raise ValueError("--input is required for nhanes or custom datasets")
    if args.input_level != "name_only" and args.metadata is None:
        raise ValueError("--metadata is required for basic_metadata and enhanced_metadata")
    if not args.api_url or not args.model:
        raise ValueError("Set --api-url and --model, or the corresponding PHENOCURATOR environment variables")

    prompt_path = ROOT / "prompts" / f"{args.prompt}.txt"
    first_rules, subsequent_rules = load_prompt(prompt_path)
    matrix = read_csv(input_path, dtype=str, keep_default_na=False)
    metadata_index = MetadataIndex(args.metadata)
    id_column = matrix.columns[0]
    client = ChatClient(
        args.api_url,
        args.model,
        os.getenv("PHENOCURATOR_API_KEY", ""),
        args.timeout,
        args.temperature,
    )

    records: list[dict[str, Any]] = []
    completed: set[str] = set()
    if args.resume and args.output.exists():
        existing = read_csv(args.output, dtype=object, keep_default_na=False)
        records = existing.to_dict("records")
        completed = set(existing.loc[existing["status"] == "success", "variable_key"].astype(str))

    for _, row in matrix.iterrows():
        variable_key = str(row[id_column]).strip()
        if variable_key in completed:
            continue
        metadata_record = metadata_index.find(variable_key)
        data_id, term, metadata = metadata_payload(args.input_level, variable_key, metadata_record)
        values = unique_values(row.iloc[1:])
        profile: dict[str, Any] | None = None
        error = ""
        for attempt in range(args.row_retries):
            try:
                profile = run_variable(
                    client,
                    values,
                    metadata,
                    args.input_level,
                    first_rules,
                    subsequent_rules,
                    args.max_retries,
                    args.max_critics,
                )
                break
            except (ModelRequestError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
                error = str(exc)
                if attempt + 1 < args.row_retries:
                    time.sleep(min(2 ** attempt, 10))

        if profile is None:
            record = {
                "variable_key": variable_key,
                "Dataid": data_id,
                "Term": term,
                "status": "error",
                "error": error,
            }
        else:
            result = profile["result"]
            record = {
                "variable_key": variable_key,
                "Dataid": data_id,
                "Term": term,
                "variable_type": result["variable_type"],
                "specified_minimal_value": result["specified_minimal_value"],
                "specified_maximal_value": result["specified_maximal_value"],
                "na_values_json": json.dumps(result["na_values"], ensure_ascii=False),
                "anomalous_values_json": json.dumps(result["anomalous_values"], ensure_ascii=False),
                "explanation_json": json.dumps(profile["explanation"], ensure_ascii=False),
                "model": args.model,
                "prompt": args.prompt,
                "input_level": args.input_level,
                "dataset": args.dataset,
                "status": "success",
                "error": "",
            }
        records.append(record)
        write_results(records, args.output)

    print(f"QC results written to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
