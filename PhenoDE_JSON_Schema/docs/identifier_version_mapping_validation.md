# Identifier, minimal version, external-mapping, and machine-validation rules

This document summarizes identifier formats, the minimal record-version mechanism, component identifier stability, external mapping semantics, and the boundary between schema validation and semantic validation.

| Rule category | Rule name | Specification | Status |
| --- | --- | --- | --- |
| Identifier | PhenoDE ID | Format: PDE + numeric body + "." + integer record-version suffix; e.g., PDE057024733.1. | Format is schema-enforced. |
| Identifier | Variable ID | Format: PDV + numeric body + "." + version + "_" + variable sequence number. | Format is schema-enforced. |
| Identifier | Feature ID | Controlled Feature identifier with category-related prefix; e.g., FI0597, FE004362, or FQ0387. | Format is schema-enforced by the current schema. |
| Identifier | Qualifier ID | Uppercase classification prefix plus digits; e.g., HAP166 or MT062. | Format is schema-enforced. |
| Information-model version | Schema version | A required root Schema version field identifies the version of the normative JSON Schema used to validate or exchange a record. Initial release: 1.0.0. | Format is schema-enforced; release policy is documented. |
| Minimal version mechanism | Stable identity and record revision | The integer suffix denotes the PhenoDE record version. A correction or refinement that preserves the measurement concept retains the stable identifier body and increments the suffix, e.g., .1 to .2. | Policy documented; identifier format is schema-enforced. |
| Minimal version mechanism | New concept and historical record | A change that creates a different measurement concept receives a new PhenoDE ID. Historical versions are retained for traceability, while the portal displays the latest version by default. | Policy documented. |
| Component identifiers | Feature/Qualifier stability | Feature and Qualifier IDs do not receive per-entry version suffixes. Textual revisions that preserve meaning retain the ID; a new or substantially changed concept receives a new ID; retired IDs are not reused. | Policy documented. |
| External mapping | Exact | The PhenoAM component is semantically equivalent to the external concept; Source Name, Source Type, and External Link or ID are required. | Field completeness is schema-validatable. |
| External mapping | Partial | The PhenoAM component corresponds to only part of the external concept; Source Name, Source Type, and External Link or ID are required. | Field completeness is schema-validatable. |
| External mapping | Unique | No suitable external counterpart was identified and the expression is retained as PhenoAM-specific; external source fields are prohibited. | Field exclusion is schema-validatable. |
| External mapping | Unmapped | External mappings is [] when no mapping object is recorded. For MT, [] may reflect exclusion from the present mapping evaluation; this is distinct from Unique. | Schema and examples implement this distinction; mapping scope is documented. |
| Machine validation | Schema standard and validated constraints | JSON Schema Draft 2020-12 validates required fields, field types, ID patterns, array cardinalities, unique Variable IDs, duplicate full-object exclusion, conditional mapping fields, Value domain restriction to Enum type, and undefined fields. | Schema-validatable. |
| Machine validation | Semantic validation boundary | The schema does not determine biomedical correctness, mapping quality, all domain-specific Qualifier combinations, or uniqueness of nested Qualifier IDs and permissible-value Codes. | Expert review or future domain rules are required. |
