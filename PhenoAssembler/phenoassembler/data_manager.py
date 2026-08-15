from collections.abc import Mapping

import pandas as pd


def normalize_value(value) -> str:
    if pd.isna(value):
        return "<NA>"
    text = str(value).strip()
    return text if text else "<NA>"


class DataManager:
    def __init__(self, meta_info: Mapping[str, object]):
        self.meta_info = {str(k): normalize_value(v) for k, v in meta_info.items()}

    @property
    def meta_info_markdown(self) -> str:
        return "\n".join(f"- **{key}**: {value}" for key, value in self.meta_info.items())

    def to_prompt(self) -> str:
        return f"""## Metadata of the Column

{self.meta_info_markdown}
"""
