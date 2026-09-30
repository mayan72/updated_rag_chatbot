import json

from google import genai

from app.models.query_plan import QueryPlan


class LLMQueryPlanner:

    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def plan(
        self,
        question: str,
        schema: dict,
    ) -> QueryPlan:

        prompt = f"""
You are a structured-data query planner.

Your job is to understand the user's question
and convert it into a structured QueryPlan.

You MUST NOT generate SQL.

You MUST NOT invent columns.

You MUST NOT invent values.

Available database schema:

{json.dumps(schema, indent=2)}

User question:

{question}

Rules:

1. Use only columns present in the schema.
2. Use only values that appear in the schema/value catalog.
3. For aggregation questions, identify the requested operation.
4. For "how many records", use operation "count".
5. COUNT does not require target_column.
6. For SUM, AVG, MIN and MAX, identify target_column.
7. Convert natural language filters into column/value filters.
8. Do not calculate the answer.
9. Do not generate SQL.
10. If the question cannot be safely represented using the available
    schema, return an empty/invalid plan rather than inventing data.

Return ONLY valid JSON matching this structure:

{{
    "operation": "sum|avg|count|min|max",
    "target_column": "column name or null",
    "filters": [
        {{
            "column": "column name",
            "operator": "=",
            "value": "value"
        }}
    ],
    "group_by": []
}}
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        raw = response.text.strip()

        return QueryPlan.model_validate_json(raw)