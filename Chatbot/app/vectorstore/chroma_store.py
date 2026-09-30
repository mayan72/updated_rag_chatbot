import chromadb


class ChromaStore:

    def __init__(self, path: str):

        self.client = chromadb.PersistentClient(
            path=path
        )

        self.collection = self.client.get_or_create_collection(
            name="rag_documents"
        )

    def add_documents(
        self,
        documents,
        embeddings,
        metadatas,
        ids
    ):

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def search(
        self,
        embedding,
        top_k=5
    ):

        return self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k
        )