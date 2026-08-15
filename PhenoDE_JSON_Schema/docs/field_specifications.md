# JSON field specifications

This document specifies the fields, JSON types, required status, cardinalities, and representative examples used in PhenoDE records.

| Level | Field name | JSON type | Required | Cardinality | Definition/example |
| --- | --- | --- | --- | --- | --- |
| PhenoDE | ID | string | Yes | 1 | Stable identifier body plus record-version suffix; e.g., PDE057024733.1. No separate PhenoDE version field is required. |
| PhenoDE | Schema version | string | Yes | 1 | Semantic version of the normative JSON Schema used to validate or exchange the record; initial release: 1.0.0. |
| PhenoDE | Platform | string | Yes | 1 | Measurement platform; e.g., Sensory. |
| PhenoDE | Detection item | string | Yes | 1 | Detection item, device category, or measurement item. |
| PhenoDE | Term | string | Yes | 1 | Complete PhenoDE term. |
| PhenoDE | Description | string | Yes | 1 | Definition or measurement description of the data element. |
| PhenoDE | Data type | string | Yes | 1 | Data type; e.g., Numeric type or Enum type. If Value domain is present, Data type must be Enum type. |
| PhenoDE | Value domain | object | No | 0..1 | Optional data-element-level specification of permissible values; permitted only when Data type is Enum type. |
| Value domain | Value domain type | string enum | Yes, if Value domain is present | 1 | Value-domain type; currently Enumerated. |
| Value domain | Permissible values | array[object] | Yes, if Value domain is present | 1..n | Array of permitted coded or textual categories. |
| Permissible value | Code | string | Yes | 1 | Code or textual category value; Codes must be unique within a Value domain through semantic validation. |
| Permissible value | Label | string | Yes | 1 | Human-readable category label. |
| Permissible value | Definition | string or null | No | 0..1 | Optional category definition. |
| Permissible value | Ordinal position | integer or null | No | 0..1 | Ordinal position for ordered categories; null for non-ordered values such as Unknown. |
| Value domain | Coding information | string or null | No | 0..1 | Notes on coding direction, interpretation, official coding, or non-ordered categories. |
| Value domain | Source/provenance | string or null | No | 0..1 | Source or provenance of the value-domain specification. |
| PhenoDE | Abbreviation | string or null | No | 0..1 | Abbreviation; may be null or omitted when unavailable. |
| PhenoDE | Variable IDs | array[string] | Yes | 1..n | Array of linked variable IDs; elements must be unique; e.g., PDV057024733.1_00100. |
| PhenoDE | Phenotype Assembly Method representation | object | Yes | 1 | Container for the Feature-Qualifier semantic decomposition. |
| PhenoAM representation | Feature | object | Yes | 1 | The single core Feature object. |
| Feature | Feature ID | string | Yes | 1 | Feature identifier; e.g., FI0597, FE004362, or FQ0387. |
| Feature | Feature classification | string | Yes | 1 | Feature class; e.g., In vivo measurement. |
| Feature | Feature term | string | Yes | 1 | Feature term; e.g., Optic disc layer thickness. |
| Feature | External mappings | array[object] | Yes | 0..n | External mappings for the Feature; use [] when none is available. |
| PhenoAM representation | Qualifiers | array[object] | Yes | 1..n | Array of Qualifier objects; at least one is required. Ex vivo records must include at least one ST Qualifier. |
| Qualifier | Qualifier ID | string | Yes | 1 | Qualifier identifier; e.g., HAP166, MT062, or ORP05. |
| Qualifier | Qualifier classification | string | Yes | 1 | Qualifier class; e.g., HAP, MT, MU, ORP, or MM. |
| Qualifier | Qualifier term | string | Yes | 1 | Qualifier term; MT062: Optical coherence tomography for ophthalmology. |
| Qualifier | External mappings | array[object] | Yes | 0..n | Independent Qualifier mappings; use [] when none is recorded. For MT, [] may indicate exclusion from the present mapping evaluation. |
| External mapping | Mapping result | enum | Yes | 1 | Allowed values: Exact, Partial, or Unique. |
| External mapping | Source Name | string | Conditional | 0..1 | Required for Exact/Partial; prohibited for Unique. |
| External mapping | Source Type | string | Conditional | 0..1 | Required for Exact/Partial; prohibited for Unique. |
| External mapping | External Link or ID | string | Conditional | 0..1 | Required for Exact/Partial; stores an external concept URI, code, DOI, or other stable identifier. |
| External mapping | UI links | string or null | No | 0..1 | Optional human-facing link; prohibited for Unique. |
