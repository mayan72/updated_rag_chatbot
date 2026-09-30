class Retriever:

    def __init__(self, vector_store, embedder):

        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query, top_k=5):

        query_embedding = self.embedder.embed_query(
            query
        )

        result = self.vector_store.search(
            query_embedding,
            top_k
        )

        documents = result.get("documents", [[]])[0]

        metadatas = result.get("metadatas", [[]])[0]

        return [
            {
                "text": document,
                "metadata": metadata
            }
            for document, metadata
            in zip(documents, metadatas)
        ]