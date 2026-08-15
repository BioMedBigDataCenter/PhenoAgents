from enum import Enum

from pydantic import BaseModel, Field, field_validator


NOT_APPLICABLE = "not applicable"


class FeatureClass(str, Enum):
    Ex_vivo = "Ex_vivo"
    In_vivo = "In_vivo"
    Questionnaire = "Questionnaire"


class DataProfile(BaseModel):
    Feature_class: FeatureClass
    Feature: str
    qualifier_HAP: str = NOT_APPLICABLE
    qualifier_ORP: str = NOT_APPLICABLE
    qualifier_MM: str = NOT_APPLICABLE
    qualifier_MC: str = NOT_APPLICABLE
    qualifier_MID: str = NOT_APPLICABLE
    qualifier_SI: str = NOT_APPLICABLE
    qualifier_AS: str = NOT_APPLICABLE
    qualifier_OT: str = NOT_APPLICABLE

    @field_validator("*", mode="before")
    @classmethod
    def normalize_empty_text(cls, value):
        if value is None:
            return NOT_APPLICABLE
        if isinstance(value, str) and not value.strip():
            return NOT_APPLICABLE
        return value


class ExplainableDataProfile(BaseModel):
    result: DataProfile
    explanation: dict[str, str] = Field(
        description=(
            "Concise explanations for each field in result. "
            "The keys must match the result field names."
        )
    )

    @field_validator("explanation", mode="after")
    @classmethod
    def explanation_keys_match_result(cls, value: dict[str, str]) -> dict[str, str]:
        expected = set(DataProfile.model_fields.keys())
        actual = set(value.keys())
        if actual != expected:
            raise ValueError(
                f"explanation keys must match result fields. Expected {expected}, got {actual}."
            )
        return value


class Critics(BaseModel):
    needed: bool
    message: str | None = Field(
        default=None,
        description="Required only when the previous answer needs revision.",
    )


RESULT_FIELDS = list(DataProfile.model_fields.keys())
QUALIFIER_FIELDS = [
    "qualifier_HAP",
    "qualifier_ORP",
    "qualifier_MM",
    "qualifier_MC",
    "qualifier_MID",
    "qualifier_SI",
    "qualifier_AS",
    "qualifier_OT",
]
