from typing import Literal

from .data_manager import DataManager
from .prompt_baseline import BASELINE_GUIDELINES
from .prompt_full import FULL_GUIDELINES
from .schemas import ExplainableDataProfile


TASK_TITLE = "DETERMINE THE SEMANTIC DESCRIPTIVE COMPONENTS OF THE PHENOTYPE"
SYSTEM_PROMPT = "You are an advanced biologist specializing in human phenotypes."


DEFINITIONS = """
## Definitions
- **Feature**: The mandatory minimal biologically meaningful measurable characteristic of a phenotype. It answers "what is measured?" and is classified into ex vivo, in vivo, or questionnaire measurement.
- **Qualifier**: Optional semantic constraints that further specify the Feature from the perspectives of measurement object, measurement process, measurement result, or applicable subject.
- **Boundary test**: If removing a word still preserves the core measurable object/property, put that word into a Qualifier. If removing it makes the Feature too vague, keep it in the Feature.

### Qualifier Subcategories
1. **Sample types (ST)**: Types of tissues, fluids, or cells used in ex vivo measurements. ST is treated as metadata and is not an output qualifier in this public schema.
2. **Human anatomical parts (HAP)**: Specific body regions or physiological structures only; do not include orientation or direction.
3. **Orientation and relative positions (ORP)**: Spatial relationships and anatomical positions only.
4. **Measurement methods (MM)**: Standardized measurement procedures, protocols, segmentation rules, or computational formulas; do not use instruments as MM.
5. **Measurement tools (MT)**: Instruments, devices, or standardized assessment tools used for measurement. MT is treated as metadata and is not an output qualifier in this public schema.
6. **Measurement conditions (MC)**: Factors influencing measurements, including timing, frequency, environment, subject state, task condition, zone, panel, region setting, and instrument settings.
7. **Measurement indicators (MID)**: Specific measured result dimensions, components, channels, sub-indicators, or questionnaire item categories.
8. **Statistical indicators (SI)**: Computed statistical metrics or summaries.
9. **Measurement units (MU)**: Standard units. MU is treated as metadata and is not an output qualifier in this public schema.
10. **Applicable Subjects (AS)**: Target populations or subject attributes.
11. **Others (OT)**: Use only when the information cannot be assigned to any other output qualifier category.

### Boundary Examples
- "left retinal nerve fiber layer thickness" -> Feature: "Retinal nerve fiber layer thickness"; HAP: "Retina;Retinal nerve fiber layer"; ORP: "Left".
- "average and maximum flow velocity" -> Feature: "Flow velocity"; SI: "Average;Maximum".
- "hearing threshold at 1 kHz" -> Feature: "Hearing threshold"; MC: "1 kHz".
- "sleep duration in the past seven days" -> Feature: "Sleep duration"; Feature_class: "Questionnaire"; MC: "In the past seven days".
- "Fridericia-corrected QT interval" -> Feature: "QT interval"; MM: "Fridericia formula".
- "36 equal part ring segmentation zone" -> MM: "36 Equal Part Of Ring"; MC: "Zone".
- "superior temporal retinal sector" -> ORP: "Superior;Temporal".
- "wine intake among drinkers" -> Feature: "Wine intake"; MID: "Wine"; AS: "Drinker".
- "normal range upper limit of body weight" -> Feature: "Body weight"; MID: "Upper Limit".
- "zone 05 retinal thickness" -> MC: "Zone".
- "principal component 12 score" -> MID: "Principal Component".
""".strip()


def guidelines_to_prompt(guidelines: list[str]) -> str:
    numbered = "\n".join(f"{index + 1}. {item}" for index, item in enumerate(guidelines))
    return f"## Requirements\n\n{numbered}\n\n{DEFINITIONS}"


def response_schema_prompt() -> str:
    return f"""## Response Format

Always answer with one JSON object defined by this Pydantic schema:

```json
{ExplainableDataProfile.model_json_schema()}
```
"""


def build_extraction_prompt(
    meta_info: dict[str, object],
    prompt_style: Literal["full", "baseline"] = "full",
) -> str:
    if prompt_style == "full":
        guidelines = FULL_GUIDELINES
    elif prompt_style == "baseline":
        guidelines = BASELINE_GUIDELINES
    else:
        raise ValueError("prompt_style must be either 'full' or 'baseline'.")

    data = DataManager(meta_info)
    return f"""# {TASK_TITLE}

{data.to_prompt()}

{response_schema_prompt()}

{guidelines_to_prompt(guidelines)}

## Data Profile Extraction

Use the metadata above to extract the phenotype semantic profile.
"""
