# Value-domain representation rules

This document defines the optional value-domain representation for enumerated variables.

| Rule | Specification | JSON/Schema expression | Validation status or scope |
| --- | --- | --- | --- |
| V1 | Value domain is an optional component of the PhenoDE root object. | Value domain is not listed in the root required array. | Schema-validatable. |
| V2 | Value domain is distinct from Feature and Qualifiers. | Value domain is a root-level property rather than a property of Feature or Qualifier. | Schema-validatable structural boundary. |
| V3 | An enumerated Value domain must contain one or more permissible values and excludes duplicate full permissible-value objects. | Permissible values has minItems = 1 and uniqueItems = true. | Schema-validatable for array cardinality and duplicate full objects. |
| V4 | Each permissible value must contain a Code and Label; Code uniqueness within a Value domain is required semantically. | Code and Label are required in PermissibleValue; duplicate-Code detection requires semantic validation. | Required fields are schema-validatable; Code uniqueness requires semantic validation. |
| V5 | Ordinal variables may record Ordinal position; nominal or non-ordered response options may use null. | Ordinal position is integer or null. | Schema-validatable type constraint; ordinal semantics require expert review. |
| V6 | Observed categories summarized by PhenoCurator do not automatically define normative permissible values. | No rule promotes observed categories to Value domain. | Conceptual rule; requires coding-specification review. |
| V7 | When an authoritative value domain is unavailable or not publicly disclosed, Value domain may be omitted. | Value domain is optional. | Policy documented. |
| V8 | A Value domain may be present only when Data type is Enum type. | If Value domain is present, Data type has const = Enum type. | Schema-validatable conditional requirement. |
