from fastapi import FastAPI, UploadFile, File
import shutil
import os

from app.config.settings import settings
from app.structured.executor import StructuredExecutor
from app.ingestion.excel_loader import load_excel
from app.ingestion.sheet_detector import detect_sheet_type
from fastapi.middleware.cors import CORSMiddleware
from app.embeddings.embedder import Embedder
from app.vectorstore.chroma_store import ChromaStore
from app.utils.logger import logger
from app.structured.database import StructuredDatabase
from pydantic import BaseModel
from app.rag.retriever import Retriever
from app.rag.chatbot import Chatbot
from app.rag.query_router import classify_query
from app.rag.prompt_builder import build_prompt
from app.structured.query_planner import StructuredQueryPlanner
from app.ingestion.ingestion_service import IngestionService
app = FastAPI(
    title="Dynamic RAG Chatbot"
)
from app.rag.query_understanding import QueryUnderstandingService
from app.structured.query_validator import QueryPlanValidator

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
embedder = Embedder(settings.embedding_model)
vector_store = ChromaStore(settings.chroma_path)
structured_db = StructuredDatabase(settings.structured_db)

retriever = Retriever(vector_store, embedder)
chatbot = Chatbot(settings.google_api_key, settings.llm_model)

ingestion_service = IngestionService(
    embedder=embedder,
    vector_store=vector_store,
    structured_db=structured_db,
)

structured_executor = StructuredExecutor(
    settings.structured_db
)

structured_planner = StructuredQueryPlanner(
    structured_db
)

query_understanding = QueryUnderstandingService(
    api_key=settings.google_api_key,
    model=settings.llm_model,
)

query_validator = QueryPlanValidator(
    structured_db
)

@app.get("/health")
def health():

    return {
        "status": "ok"
    }

@app.post("/upload")
async def upload(
    file: UploadFile = File(...)
):

    os.makedirs(
        "data/uploads",
        exist_ok=True,
    )

    file_path = (
        f"data/uploads/{file.filename}"
    )

    with open(file_path, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer,
        )

    ingestion_result = (
        ingestion_service.ingest(
            file_path
        )
    )

    return {
        "filename": file.filename,
        "ingestion": ingestion_result,
    }
class ChatRequest(BaseModel):
    question: str
 
 
@app.post("/chat")
def chat(request: ChatRequest):

    question = request.question.strip()

    if not question:
        return {
            "question": question,
            "error": "Question cannot be empty.",
        }

    logger.info(
        "Chat request received | question=%s",
        question,
    )

    # ---------------------------------------------------------
    # 1. Get actual database schema
    # ---------------------------------------------------------

    schema_context = structured_db.get_schema_context(
        "structured"
    )

    logger.debug(
        "Schema context:\n%s",
        schema_context,
    )

    # ---------------------------------------------------------
    # 2. Ask Gemini to understand the question
    # ---------------------------------------------------------

    understanding = query_understanding.understand(
        question=question,
        schema_context=schema_context,
    )

    logger.info(
        "Detected intent | %s",
        understanding.intent,
    )

    # ---------------------------------------------------------
    # 3. Validate structured plan
    # ---------------------------------------------------------

    understanding = query_validator.validate(
        understanding=understanding,
        table_name="structured",
    )

    # ---------------------------------------------------------
    # 4. Structured query
    # ---------------------------------------------------------

    if understanding.intent == "structured":

        plan = understanding.structured_plan

        result = structured_executor.aggregate(
            table_name="structured",
            operation=plan.operation,
            target_column=plan.target_column,
            filters={
                item.column: item.value
                for item in plan.filters
                if item.operator == "="
            },
        )

        return {
            "question": question,
            "type": "structured",
            "plan": plan.model_dump(),
            "answer": result,
        }

    # ---------------------------------------------------------
    # 5. Unstructured query
    # ---------------------------------------------------------

    if understanding.intent == "unstructured":

        search_query = (
            understanding.search_query
            or question
        )

        results = retriever.retrieve(
            search_query,
            settings.top_k,
        )

        context = "\n\n".join(
            item["text"]
            for item in results
        )

        prompt = build_prompt(
            question,
            context,
        )

        answer = chatbot.generate(prompt)

        return {
            "question": question,
            "type": "unstructured",
            "answer": answer,
            "sources": results,
        }

    # ---------------------------------------------------------
    # 6. Hybrid is not implemented yet
    # ---------------------------------------------------------

    if understanding.intent == "hybrid":

        return {
            "question": question,
            "type": "hybrid",
            "status": "not_implemented",
            "plan": (
                understanding.structured_plan.model_dump()
                if understanding.structured_plan
                else None
            ),
            "search_query": understanding.search_query,
        }

    # ---------------------------------------------------------
    # 7. Unknown
    # ---------------------------------------------------------

    return {
        "question": question,
        "type": "unknown",
        "answer": (
            "I could not determine how to answer this question "
            "from the available data."
        ),
    }