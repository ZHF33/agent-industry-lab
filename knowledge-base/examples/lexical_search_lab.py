"""Toy inverted index; no database, model, or network."""
import re

DOCS = {"A": "damaged mug return", "B": "damaged plate return", "C": "mug care"}

def terms(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def build_index(documents):
    index = {}
    for source, text in documents.items():
        for term in terms(text):
            index.setdefault(term, set()).add(source)
    return index

def search(index, query, allowed):
    query_terms = terms(query)
    candidates = set()
    for term in query_terms:
        candidates.update(index.get(term, set()))
    scores = [(source, sum(source in index.get(term, set()) for term in query_terms))
              for source in candidates & allowed]
    return sorted(scores, key=lambda item: (-item[1], item[0]))

if __name__ == "__main__":
    index = build_index(DOCS)
    print("mug:", ",".join(sorted(index["mug"])))
    print("all:", search(index, "damaged mug return", set(DOCS)))
    print("scoped:", search(index, "damaged mug return", {"A", "C"}))
    print("synonym:", search(index, "broken cup", set(DOCS)))
