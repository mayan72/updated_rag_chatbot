from typing import Optional
import json

from google import genai

from app.models.query_plan import QueryUnderstanding
from app.utils.logger import logger


class QueryUnderstandingService:

    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def understand(
        self,
        question: str,
        schema_context: str,
    ) -> QueryUnderstanding:

        prompt = f"""
You are a query-understanding component for a production RAG system.

Your job is ONLY to understand the user's question and return a structured
query-understanding object.

You must NOT:
- calculate numerical results
- generate SQL
- invent columns
- invent filter values
- answer the user's question

Available dataset schema:

{schema_context}

User question:
{question}

Determine the intent:

1. structured
   Use this when the answer requires deterministic operations on structured
   tabular data such as:
   - sum
   - average
   - count
   - minimum
   - maximum
   - filtering
   - grouping

2. unstructured
   Use this when the answer requires textual/document evidence.

3. hybrid
   Use this when the question requires both structured data and textual
   evidence.

4. unknown
   Use this only when the intent genuinely cannot be determined.

For structured queries:
- operation must be one of:
  sum, avg, count, min, max
- target_column must be an actual schema column when required
- filters must reference actual schema columns
- group_by must reference actual schema columns
- do not invent values
- COUNT does not require target_column

For unstructured/hybrid queries:
- provide a concise search_query suitable for semantic retrieval.

Return ONLY valid JSON matching this structure:

{{
  "intent": "structured | unstructured | hybrid | unknown",
  "structured_plan": {{
    "operation": "sum | avg | count | min | max",
    "target_column": "column or null",
    "filters": [
      {{
        "column": "column",
        "operator": "= | != | > | >= | < | <=",
        "value": "value"
      }}
    ],
    "group_by": ["column"]
  }},
  "search_query": "retrieval query or null"
}}
"""

        logger.info(
            "Query understanding started | question=%s",
            question,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        raw_text = response.text.strip()

        logger.debug(
            "Query understanding raw response | %s",
            raw_text,
        )

        try:
            cleaned_text = self._clean_json_response(raw_text)

            logger.debug(
                "Query understanding cleaned response | %s",
                cleaned_text,
            )

            data = json.loads(cleaned_text)

            result = QueryUnderstanding.model_validate(data)

            logger.info(
                "Query understanding completed | intent=%s | plan=%s | search_query=%s",
                result.intent,
                result.structured_plan,
                result.search_query,
            )

            return result

        except Exception:
            logger.exception(
                "Failed to parse Gemini query-understanding response"
            )
            raise
        
    @staticmethod
    def _clean_json_response(raw_text: str) -> str:
        """
        Remove Markdown code fences if Gemini returns JSON inside
        ```json ... ```.

        The method does not modify the JSON content itself.
        """

        text = raw_text.strip()

        if text.startswith("```"):

            lines = text.splitlines()

            # Remove opening fence
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]

            # Remove closing fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        return text