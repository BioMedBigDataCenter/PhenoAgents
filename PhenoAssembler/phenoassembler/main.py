import time
from pathlib import Path
from typing import Literal

import pandas as pd

from .llm_client import LLMClient
from .prompts import build_extraction_prompt


COMMON_METADATA_COLUMNS = [
    "ID",
    "Term",
    "Top class",
    "Subclass",
    "qualifier_ST",
    "qualifier_MT",
    "qualifier_MU",
]


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".tsv", ".txt"}:
        return pd.read_csv(path, sep="\t")
    raise ValueError(f"Unsupported input format: {path.suffix}")


def write_table(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df.to_excel(path, index=False)
    elif suffix == ".csv":
        df.to_csv(path, index=False)
    elif suffix in {".tsv", ".txt"}:
        df.to_csv(path, sep="\t", index=False)
    else:
        raise ValueError(f"Unsupported output format: {path.suffix}")


def row_to_metadata(row: pd.Series) -> dict[str, object]:
    return {str(key): ("<NA>" if pd.isna(value) else value) for key, value in row.to_dict().items()}


def run(
    input_path: str | Path,
    output_path: str | Path,
    prompt_style: Literal["full", "baseline"] = "full",
    max_retries: int = 3,
    max_critics: int = 1,
    temperature: float = 0.2,
    sleep_seconds: float = 0.0,
    limit: int | None = None,
) -> pd.DataFrame:
    input_df = read_table(input_path)
    if limit is not None:
        input_df = input_df.head(limit)

    client = LLMClient.from_env(temperature=temperature)
    output_records: list[dict[str, object]] = []

    for index, row in input_df.iterrows():
        metadata = row_to_metadata(row)
        record = {
            column: metadata.get(column)
            for column in COMMON_METADATA_COLUMNS
            if column in metadata
        }
        record["source_row_index"] = index

        try:
            prompt = build_extraction_prompt(metadata, prompt_style=prompt_style)
            extraction = client.extract_profile(
                prompt,
                max_retries=max_retries,
                max_critics=max_critics,
            )
            record.update(extraction.result.model_dump(mode="json"))
            record.update(
                {
                    f"explanation_{key}": value
                    for key, value in extraction.explanation.items()
                }
            )
            record["error"] = ""
        except Exception as exc:
            record["error"] = str(exc)

        output_records.append(record)

        if sleep_seconds and len(output_records) < len(input_df):
            time.sleep(sleep_seconds)

    output_df = pd.DataFrame(output_records)
    write_table(output_df, output_path)
    return output_df
