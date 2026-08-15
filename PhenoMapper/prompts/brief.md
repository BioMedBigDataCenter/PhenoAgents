# Brief prompt variant

## Classification prompt

Classify the phenotype mapping query.

Term: "{term}"

Primary category:
- molecular: genes, proteins, metabolites, microbes, or cell-related terms.
- non_molecular: non-molecular phenotype terms and non-molecular phenotype measurement-related terms.

If category=molecular, choose one molecular subtype:
gene | protein | metabolite | microbe | cell

If category=non_molecular, choose exactly one semantic route:
anatomical_sites | measurement_unit | measurement_method | measurement_indicators | statistical_metric | orientation | sample_type | measurement_condition | applicable_subjects | questionnaire | other

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
1. Semantic match to the query term is required.
2. Prefer listed ontologies when semantically plausible.
3. Prefer exact label or synonym matches.

Return only the ranked result numbers as a comma-separated list.
