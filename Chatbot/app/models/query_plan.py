from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class QueryFilter(BaseModel):
    column: str
    operator: Literal["=", "!=", ">", ">=", "<", "<="]
    value: str


class StructuredQueryPlan(BaseModel):
    operation: Literal[
        "sum",
        "avg",
        "count",
        "min",
        "max",
    ]

    target_column: Optional[str] = None

    filters: List[QueryFilter] = Field(default_factory=list)

    group_by: List[str] = Field(default_factory=list)


class QueryUnderstanding(BaseModel):
    intent: Literal[
        "structured",
        "unstructured",
        "hybrid",
        "unknown",
    ]

    structured_plan: Optional[StructuredQueryPlan] = None

    search_query: Optional[str] = None