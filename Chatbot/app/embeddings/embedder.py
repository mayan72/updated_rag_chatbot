from sentence_transformers import SentenceTransformer


class Embedder:

    def __init__(self, model_name: str):

        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts):

        return self.model.encode(
            texts,
            normalize_embeddings=True
        ).tolist()

    def embed_query(self, query):

        return self.model.encode(
            query,
            normalize_embeddings=True
        ).tolist()