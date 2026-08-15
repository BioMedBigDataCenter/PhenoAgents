# Full prompt variant

## Classification prompt

You are an expert in phenotype term classification. Classify the following term.

Term: "{term}"

Primary category (choose exactly one):
- molecular: molecular entities, including genes, proteins, metabolites, microbes, and cell-related terms.
- non_molecular: non-molecular phenotype terms and non-molecular phenotype measurement-related terms.

Molecular branch - subtype (required only if category=molecular; otherwise use N/A):
- gene: gene symbols, gene names, gene IDs, or gene products.
- protein: protein names or protein markers.
- metabolite: metabolites or chemical compounds.
- microbe: microbes or taxonomy terms.
- cell: cell types, immune cell populations, or cell phenotype terms.

Non-molecular branch - semantic route (required only if category=non_molecular; otherwise use N/A):
- anatomical_sites
- measurement_unit
- measurement_method
- measurement_indicators
- statistical_metric
- orientation
- sample_type
- measurement_condition
- applicable_subjects
- questionnaire
- other

Return exactly three lines and no extra text:
category: <molecular|non_molecular>
molecular_type: <gene|protein|metabolite|microbe|cell|N/A>
route: <anatomical_sites|measurement_unit|measurement_method|measurement_indicators|statistical_metric|orientation|sample_type|measurement_condition|applicable_subjects|questionnaire|other|N/A>

## Re-ranking prompt

You are an ontology matching expert. Re-rank the following BioPortal search results for the query term.

Query term: "{term}"
Semantic route: {route}
Preferred ontologies for this route: {preferred_ontologies}

Search results:
{candidates}

Ranking rules:
1. Rank candidates from preferred ontologies first when their label or synonym is an exact, close, or clearly related semantic match to the query term.
2. Rank semantically matching candidates from non-preferred ontologies after preferred-ontology semantic matches.
3. A candidate from a preferred ontology but with poor semantic match should be excluded or placed last.
4. Prefer exact label or synonym matches over broader/narrower concepts within the same ontology-priority tier.

Return only the ranked result numbers as a comma-separated list.
