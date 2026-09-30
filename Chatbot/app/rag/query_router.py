import re


STRUCTURED_KEYWORDS = [
    "total",
    "sum",
    "average",
    "avg",
    "maximum",
    "minimum",
    "highest",
    "lowest",
    "count",
    "how many",
    "quantity",
    "sales",
    "revenue",
    "price"
]


def classify_query(query: str) -> str:

    query_lower = query.lower()

    for keyword in STRUCTURED_KEYWORDS:

        if keyword in query_lower:
            return "structured"

    return "unstructured"