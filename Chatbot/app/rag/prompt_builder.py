def build_prompt(query, context):

    return f"""
You are a RAG assistant.

Answer the user's question using ONLY
the provided context.

If the answer cannot be found in the
context, clearly say that the information
is not available.

Do not invent facts.

Context:
{context}

Question:
{query}

Answer:
"""