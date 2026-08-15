# PhenoDE formal and machine-verifiable information model

This directory provides the formal conceptual model, field specifications, Feature-Qualifier rules, identifier and minimal record-version mechanism, optional value-domain representation for enumerated variables, the normative JSON Schema, and representative JSON instances for PhenoDE.

## Contents

### Documentation

- `docs/conceptual_model.md`: core PhenoDE objects, relationships, and cardinalities.
- `docs/field_specifications.md`: JSON field definitions, types, required status, and cardinalities.
- `docs/feature_qualifier_rules.md`: Feature-Qualifier relationship, combination, and cardinality rules.
- `docs/value_domain_rules.md`: representation rules for permissible values of enumerated variables.
- `docs/identifier_version_mapping_validation.md`: identifier formats, minimal record-version mechanism, external mapping semantics, and machine-validation scope.

### Machine-readable schema

- `schema/phenode.schema.json`: normative PhenoDE JSON Schema using JSON Schema Draft 2020-12.

The schema requires a `Schema version` field, at least one Qualifier per PhenoDE, at least one Sample Type (`ST`) Qualifier for ex vivo records, and permits a `Value domain` object only for records with `Data type` set to `Enum type`.

### Representative instances

- `examples/PDE057024733.1.json`: in vivo ophthalmic OCT example.
- `examples/PDE047007571.1.json`: ex vivo IFN-γ example.
- `examples/PDE026002951.1.json`: questionnaire enumerated-variable example with a Value domain.

The examples conform to `schema/phenode.schema.json`. Empty `External mappings` arrays for MT Qualifiers indicate that no external mapping object is recorded duplicate objects are disallowed. They do not indicate the absence of the MT Qualifier.

## Validation scope

The JSON Schema validates structural constraints including required fields, field types, identifier patterns, cardinalities, duplicate full-object exclusion where specified, conditional mapping fields, the ex vivo ST requirement, the Enum-type condition for Value domain, and undeclared properties are disallowed.

Biomedical semantic correctness, mapping quality, all domain-specific Qualifier combinations, uniqueness of nested Qualifier IDs, and uniqueness of permissible-value Codes require semantic validation beyond JSON Schema.
