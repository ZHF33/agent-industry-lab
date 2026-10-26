"""Scoped lexical retrieval over synthetic approved support passages."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

REQUESTS = {"REQUEST-DEMO-01": {"source": "support-request-demo-01", "request_id": "REQUEST-DEMO-01",
    "product": "DEMO-MUG", "region": "DEMO-US", "query": "damaged mug return",
    "observed_at": "2026-10-26T12:00:00+00:00"}}
DOCUMENTS = [
    {"source": "KB-DEMO-RETURN-v2", "product": "DEMO-MUG", "region": "DEMO-US", "status": "published",
     "effective_from": "2026-10-01T00:00:00+00:00", "effective_until": None,
     "text": "Damaged mug return requests require order date and damage evidence for human review. Do not promise a refund."},
    {"source": "KB-DEMO-RETURN-v1", "product": "DEMO-MUG", "region": "DEMO-US", "status": "published",
     "effective_from": "2026-01-01T00:00:00+00:00", "effective_until": "2026-10-01T00:00:00+00:00",
     "text": "Damaged mug return requests follow the old synthetic process."},
    {"source": "KB-DEMO-OTHER-v1", "product": "DEMO-PLATE", "region": "DEMO-US", "status": "published",
     "effective_from": "2026-10-01T00:00:00+00:00", "effective_until": None,
     "text": "Damaged mug return damaged mug return: unrelated product fixture."},
    {"source": "KB-DEMO-DRAFT-v3", "product": "DEMO-MUG", "region": "DEMO-US", "status": "draft",
     "effective_from": "2026-10-01T00:00:00+00:00", "effective_until": None,
     "text": "Damaged mug return: unapproved draft."}
]
POLICY = {"source": "retrieval-policy-demo-01", "max_age_seconds": 60, "top_k": 3,
          "scope": "Synthetic product/region scope is not authentication or tenant authorization."}


def instant(value):
    if not isinstance(value, str): raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None: raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def terms(text):
    if not isinstance(text, str): raise ValueError("Query text required")
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve(request, documents, as_of):
    reference, observed = instant(as_of), instant(request["observed_at"])
    if observed > reference: raise ValueError("Future request observation")
    query = terms(request["query"])
    if not query: raise ValueError("Non-empty English/alphanumeric query required")
    ids = [doc["source"] for doc in documents]
    if len(set(ids)) != len(ids): raise ValueError("Duplicate source identity")
    fresh = (reference - observed).total_seconds() <= POLICY["max_age_seconds"]
    hits = []
    for doc in documents:
        if doc["product"] != request["product"] or doc["region"] != request["region"] or doc["status"] != "published":
            continue
        start = instant(doc["effective_from"])
        end = instant(doc["effective_until"]) if doc["effective_until"] is not None else None
        if end is not None and end <= start: raise ValueError("Invalid effective interval")
        if not start <= reference or (end is not None and reference >= end): continue
        overlap = sorted(query & terms(doc["text"]))
        if overlap and fresh:
            hits.append({**doc, "matched_terms": overlap, "overlap_score": len(overlap)})
    hits.sort(key=lambda item: (-item["overlap_score"], item["source"]))
    return {"source": "retrieval-result-demo-01", "request_source": request["source"],
            "query_terms": sorted(query), "request_fresh": fresh,
            "hits": hits[:POLICY["top_k"]], "method": "unique_term_overlap_not_bm25"}


def assess(request, documents, as_of):
    result = retrieve(request, documents, as_of)
    return {"source": "retrieval-assessment-demo-01", "inputs": [request["source"], result["source"], POLICY["source"]],
            "candidate_source_ids": [x["source"] for x in result["hits"]],
            "status": "candidate_evidence_requires_review" if result["hits"] else "insufficient_evidence",
            "missing_business_facts": ["order_date", "damage_evidence", "order_product_and_region_confirmation"],
            "eligibility_verified": False, "answer_entailment_verified": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_request": "Read synthetic request scope and fixed search query",
                    "search_knowledge": "Retrieve published, effective product/region-matching synthetic passages by unique term overlap",
                    "assess_retrieval": "Report candidate citations and missing business facts; never approve a refund"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"request_id": {"type": "string"}},
                            "required": ["request_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, request_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments, dict)
            or set(arguments) != {"request_id"} or arguments["request_id"] != request_id):
        raise ValueError("Invalid tool or request scope")
    request = REQUESTS.get(request_id)
    if request is None: raise ValueError("Unknown synthetic request")
    if name == "lookup_request": return [request]
    if name == "assess_retrieval": return [assess(request, DOCUMENTS, as_of)]
    result = retrieve(request, DOCUMENTS, as_of)
    return [result, POLICY] + result["hits"]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                    data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
