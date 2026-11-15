"""离线词项检索实验；英文空白词项，不代表中文向量检索质量。"""
import json
import math
import re
from collections import Counter


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def search(documents, query, k=3):
    if k < 1:
        raise ValueError("k must be positive")
    terms = {key: Counter(tokenize(text)) for key, text in documents.items()}
    vocabulary = set().union(*(set(row) for row in terms.values())) if terms else set()
    idf = {word: math.log((1 + len(terms)) / (1 + sum(word in row for row in terms.values()))) + 1 for word in vocabulary}
    query_counts = Counter(tokenize(query))
    query_vector = {word: count * idf[word] for word, count in query_counts.items() if word in idf}
    query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    ranked = []
    for key, counts in terms.items():
        vector = {word: count * idf[word] for word, count in counts.items()}
        norm = math.sqrt(sum(value * value for value in vector.values()))
        score = sum(value * vector.get(word, 0) for word, value in query_vector.items()) / (query_norm * norm) if query_norm and norm else 0.0
        if score > 0:
            ranked.append({"id": key, "score": score})
    return sorted(ranked, key=lambda row: (-row["score"], row["id"]))[:k]


def retrieval_metrics(ranked_ids, relevant_ids):
    relevant = set(relevant_ids)
    if not relevant:
        raise ValueError("No-answer questions need separate rejection evaluation")
    ids = list(dict.fromkeys(ranked_ids))
    hits = relevant.intersection(ids)
    return {"recall": len(hits) / len(relevant),
            "reciprocal_rank": next((1 / (i + 1) for i, key in enumerate(ids) if key in relevant), 0.0)}


def main():
    documents = {"network": "network timeout retry connection", "gpu": "gpu memory inference model", "database": "database transaction rollback commit"}
    rows = search(documents, "transaction rollback", 2)
    print(json.dumps({"scope": "synthetic_cpu_lexical_demo", "ranked": rows,
                      "metrics": retrieval_metrics([row["id"] for row in rows], ["database"]),
                      "unknown_query": search(documents, "payroll")}, indent=2))


if __name__ == "__main__":
    main()
