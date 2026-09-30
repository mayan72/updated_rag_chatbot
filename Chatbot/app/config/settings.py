from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    google_api_key: str

    llm_model: str = "gemini-2.5-flash"

    embedding_model: str = "BAAI/bge-small-en-v1.5"

    chroma_path: str = "./data/chroma"

    structured_db: str = "./storage/structured.db"

    top_k: int = 5

    chunk_size: int = 700

    chunk_overlap: int = 100

    class Config:
        env_file = ".env"


settings = Settings()