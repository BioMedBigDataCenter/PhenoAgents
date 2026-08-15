# Simplified conceptual model of PhenoDE

This document defines the core objects in the PhenoDE information model and their relationships and cardinalities.

| Object | JSON representation | Conceptual definition | Relationship/cardinality | Notes |
| --- | --- | --- | --- | --- |
| PhenoDE | JSON root object | Complete standardized phenotype data-element record | 1 | Aggregates core metadata, linked variables, and the PhenoAM semantic representation. |
| Schema version | Schema version property | Version of the normative information-model schema applied to the record | 1 per PhenoDE | Initial formal release: 1.0.0. Distinct from the record-version suffix embedded in the PhenoDE ID. |
| Variable ID | Element of the Variable IDs array | Identifier of a concrete variable associated with a PhenoDE | 1..n per PhenoDE | One PhenoDE may be linked to one or more source variables; array elements must be unique. |
| Value domain | Value domain object | Data-element-level specification of permissible values for an enumerated variable | 0..1 per PhenoDE | Optional; distinct from the Feature-Qualifier semantic representation and populated when an authoritative coding specification is available. |
| Permissible value | Object in the Permissible values array | One permitted coded or textual category | 1..n per Value domain | Records code, label, definition, and ordinal position where applicable. Code uniqueness within a Value domain is a semantic-validation rule. |
| PhenoAM representation | Phenotype Assembly Method representation | Feature-Qualifier semantic decomposition object | 1 per PhenoDE | Contains one Feature object and a Qualifiers array. |
| Feature | Feature object | Core phenotype feature described by the PhenoDE | 1 per PhenoDE | Defined by Feature ID, Feature classification, Feature term, and External mappings. |
| Qualifier | Object in the Qualifiers array | Semantic component that constrains the measurement object, process, or result of the Feature | 1..n per PhenoDE | One ID per independent Qualifier; classifications may repeat. Overall cardinality is 1..n, and ex vivo records require at least one ST. |
| External mapping | Object in an External mappings array | Mapping between a Feature or Qualifier and an external terminology or ontology concept | 0..n per Feature/Qualifier | Mapping result is Exact, Partial, or Unique. [] means no mapping object is recorded; for MT, this may reflect exclusion from the present mapping evaluation. |
