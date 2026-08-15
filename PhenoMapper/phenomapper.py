#!/usr/bin/env python3
"""Core workflow of the PhenoMapper LLM-based phenotype-mapping agent."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
VALID_TYPES = {"gene", "protein", "metabolite", "microbe", "cell"}
VALID_ROUTES = {
    "anatomical_sites", "measurement_unit", "measurement_method",
    "measurement_indicators", "statistical_metric", "orientation", "sample_type",
    "measurement_condition", "applicable_subjects", "questionnaire", "other",
}
ONTOLOGY_PRIORITY = {
    "anatomical_sites": ["UBERON", "FMA"],
    "measurement_unit": ["UO", "NCIT"],
    "measurement_method": ["OBI", "NCIT"],
    "measurement_indicators": ["NCIT", "EFO"],
    "sample_type": ["OBI", "UBERON"],
    "cell": ["CL", "CYTO"],
}


def load_prompt(variant: str, section: str) -> str:
    text = (ROOT / "prompts" / f"{variant}.md").read_text(encoding="utf-8")
    marker = f"## {section}"
    if marker not in text:
        raise ValueError(f"Prompt section not found: {section}")
    section_text = text.split(marker, 1)[1]
    return section_text.split("\n## ", 1)[0].strip()


def call_llm(prompt: str, temperature: float) -> str:
    key = os.getenv("LLM_API_KEY")
    if not key:
        raise RuntimeError("LLM_API_KEY is required and must be supplied via the environment.")
    url = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("LLM_MODEL", "")
    if not model:
        raise RuntimeError("LLM_MODEL is required and must be supplied via the environment.")
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
    response = requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_classification(response: str) -> dict[str, str]:
    fields = {"category": "", "molecular_type": "", "route": ""}
    for line in response.splitlines():
        if ":" not in line:
            continue
        key, value = (part.strip().lower() for part in line.split(":", 1))
        if key in fields:
            fields[key] = value.replace(" ", "_")
    if fields["category"] not in {"molecular", "non_molecular"}:
        fields = {"category": "non_molecular", "molecular_type": "", "route": "other"}
    if fields["molecular_type"] not in VALID_TYPES:
        fields["molecular_type"] = ""
    if fields["route"] not in VALID_ROUTES:
        fields["route"] = "other" if fields["category"] == "non_molecular" else ""
    if fields["category"] == "molecular":
        fields["route"] = ""
    else:
        fields["molecular_type"] = ""
    return fields


def classify_term(term: str, variant: str, temperature: float) -> dict[str, str]:
    template = load_prompt(variant, "Classification prompt")
    return parse_classification(call_llm(template.format(term=term), temperature))


def hit(identifier: str, label: str, source: str, ontology: str = "", description: str = "", synonyms: str = "", iri: str = "") -> dict[str, str]:
    return {"id": identifier, "label": label, "source": source, "ontology": ontology,
            "description": description, "synonyms": synonyms, "iri": iri}


def query_bioportal(term: str, limit: int) -> list[dict[str, str]]:
    key = os.getenv("BIOPORTAL_API_KEY")
    if not key:
        return []
    response = requests.get("https://data.bioontology.org/search", params={"q": term, "pagesize": limit * 2, "apikey": key}, timeout=30)
    response.raise_for_status()
    candidates = []
    for item in response.json().get("collection", []):
        ontology = item.get("links", {}).get("ontology", "").rsplit("/", 1)[-1]
        candidates.append(hit(item.get("@id", ""), item.get("prefLabel", ""), "BioPortal", ontology,
                              item.get("definition", "") or "", "; ".join(item.get("synonym", []) or []), item.get("@id", "")))
    return candidates


def query_molecular(term: str, subtype: str, limit: int) -> list[dict[str, str]]:
    if subtype == "gene":
        data = requests.get("https://mygene.info/v3/query", params={"q": term, "species": "human", "size": limit}, timeout=30).json()
        return [hit(str(x.get("_id", "")), x.get("symbol", ""), "MyGene", "NCBI Gene", x.get("name", "")) for x in data.get("hits", [])]
    if subtype == "protein":
        data = requests.get("https://rest.uniprot.org/uniprotkb/search", params={"query": term, "size": limit, "format": "json"}, timeout=30).json()
        return [hit(x.get("primaryAccession", ""), x.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""), "UniProt", "UniProt", iri=f"https://www.uniprot.org/uniprotkb/{x.get('primaryAccession', '')}") for x in data.get("results", [])]
    if subtype == "metabolite":
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(term, safe='')}/property/IUPACName/JSON"
        data = requests.get(url, timeout=30).json()
        return [hit(str(x.get("CID", "")), x.get("IUPACName", term), "PubChem", "PubChem") for x in data.get("PropertyTable", {}).get("Properties", [])[:limit]]
    if subtype == "microbe":
        data = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={"db": "taxonomy", "term": term, "retmode": "json", "retmax": limit}, timeout=30).json()
        return [hit(taxid, term, "NCBI Taxonomy", "NCBI Taxonomy") for taxid in data.get("esearchresult", {}).get("idlist", [])]
    return query_bioportal(term, limit)


def fallback_sort(candidates: list[dict[str, str]], term: str, preferred: list[str]) -> list[dict[str, str]]:
    normalized = term.casefold()
    def score(item: dict[str, str]) -> tuple[int, int]:
        label = item.get("label", "").casefold()
        exact = int(label == normalized)
        ontology = item.get("ontology", "").upper()
        priority = int(ontology in {x.upper() for x in preferred})
        return exact, priority
    return sorted(candidates, key=score, reverse=True)


def rerank_bioportal(term: str, route: str, candidates: list[dict[str, str]], variant: str, temperature: float, limit: int) -> list[dict[str, str]]:
    preferred = ONTOLOGY_PRIORITY.get(route, ["NCIT"])
    if len(candidates) < 2:
        return candidates[:limit]
    listing = "\n".join(f"{i}. id={c['id']}, label={c['label']}, ontology={c['ontology']}, synonyms={c['synonyms'][:100]}" for i, c in enumerate(candidates, 1))
    prompt = load_prompt(variant, "Re-ranking prompt").format(term=term, route=route, preferred_ontologies=", ".join(preferred), candidates=listing)
    try:
        numbers = [int(x) - 1 for x in re.findall(r"\d+", call_llm(prompt, temperature))]
        ordered, seen = [], set()
        for index in numbers:
            if 0 <= index < len(candidates) and index not in seen:
                ordered.append(candidates[index]); seen.add(index)
        ordered.extend(c for i, c in enumerate(fallback_sort(candidates, term, preferred)) if c not in ordered)
        return ordered[:limit]
    except Exception:
        return fallback_sort(candidates, term, preferred)[:limit]


def query_pubmed(term: str, limit: int) -> list[dict[str, str]]:
    data = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={"db": "pubmed", "term": term, "retmode": "json", "retmax": limit}, timeout=30).json()
    return [hit(pmid, f"PubMed:{pmid}", "PubMed", "PubMed", iri=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/") for pmid in data.get("esearchresult", {}).get("idlist", [])]


def map_term(term: str, variant: str, temperature: float, limit: int) -> dict[str, Any]:
    classification = classify_term(term, variant, temperature)
    try:
        if classification["category"] == "molecular":
            candidates = query_molecular(term, classification["molecular_type"], limit)
        else:
            candidates = rerank_bioportal(term, classification["route"], query_bioportal(term, limit), variant, temperature, limit)
        literature = query_pubmed(term, limit) if not candidates else []
        status = "ok"
    except requests.RequestException as error:
        candidates, literature, status = [], [], f"resource_error: {error.__class__.__name__}"
    return {"term": term, **classification, "candidates": candidates, "pubmed_fallback": literature, "status": status}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV file with a term column")
    parser.add_argument("--prompt", choices=("full", "brief"), default="full")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--output", default="results.json")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8", newline="") as handle:
        terms = [row["term"].strip() for row in csv.DictReader(handle) if row.get("term", "").strip()]
    results = [map_term(term, args.prompt, args.temperature, args.top_k) for term in terms]
    Path(args.output).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
