# Feature-Qualifier relationship, combination, and cardinality rules

This document defines the structural and interpretive rules governing Feature and Qualifier representation in PhenoDE.

| Rule | Specification | JSON/Schema expression | Validation status or scope |
| --- | --- | --- | --- |
| C1 | Each PhenoDE must contain one Phenotype Assembly Method representation object. | The object is required and has cardinality 1. | Schema-validatable. |
| C2 | Each PhenoDE must contain exactly one Feature. | Feature is a single object rather than an array. | Schema-validatable. |
| C3 | Each PhenoDE must contain one or more Qualifiers. | Qualifiers is an array with minItems = 1; cardinality 1..n. | Schema-validatable. |
| C4 | Each Qualifier object contains one Qualifier ID. Within a PhenoDE, Qualifier IDs are intended to be unique. | Qualifiers has uniqueItems = true; duplicate Qualifier ID detection requires semantic validation. | Duplicate full-object exclusion is schema-validatable; nested-ID uniqueness requires semantic validation. |
| C5 | The same Qualifier classification may occur more than once. | For example, multiple HAP Qualifiers are represented as separate array elements. | Allowed; classification repetition is not restricted. |
| C6 | All Qualifiers in one PhenoDE jointly constrain the single Feature. | Feature and Qualifiers are colocated within one PhenoAM representation. | Conceptual rule; biomedical semantics are not schema-validated. |
| C7 | The order of the Qualifiers array does not indicate semantic priority or dependency. | The array provides set-like organization. | Interpretive rule. |
| C8 | The current schema does not encode direct modifier or hierarchical relations between Qualifiers. | No qualifier-to-qualifier relation field is defined. | Current model boundary. |
| C9 | The Feature and each Qualifier maintain their own External mappings. | The same field name is used within distinct nested objects. | Schema-validatable. |
| C10 | Each External mappings array may contain zero or more mapping objects. | An empty array denotes no current external mapping. | Schema-validatable. |
| C11 | Variable IDs must contain at least one unique element. | minItems = 1 and uniqueItems = true. | Schema-validatable. |
| C12 | Each ex vivo PhenoDE must contain at least one Sample Type (ST) Qualifier. | If Feature classification is Ex vivo measurement, Qualifiers uses contains with classification = ST and minContains = 1. | Schema-validatable conditional requirement. |
| C13 | The schema primarily validates structural constraints and does not encode every domain-specific exclusion, dependency, conditional combination, or nested-field uniqueness rule. | For example, biomedical plausibility across specific Qualifier classes and duplicate Qualifier IDs. | Requires expert review or future domain rules. |
