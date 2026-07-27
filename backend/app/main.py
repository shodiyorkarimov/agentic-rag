import os
import shutil
import tempfile

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config
from .graph import get_agent
from .ingest import collection_count, ingest_pdf

api = FastAPI(title="Agentic RAG API")

# Frontend (Vercel) boshqa domendan so'rov yuboradi — CORS ochamiz.
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.on_event("startup")
def startup_ingest():
    """Konteyner ishga tushganda: agar Qdrant bo'sh bo'lsa, standart PDF'ni avtomatik ingest qiladi.
    Bu HF Spaces qayta ishga tushganda (restart/redeploy) qo'lda ingest qilishni talab qilmaydi."""
    if collection_count() == 0 and os.path.exists(config.DEFAULT_PDF_PATH):
        n = ingest_pdf(config.DEFAULT_PDF_PATH)
        print(f"[startup] Standart PDF ingest qilindi: {n} ta chunk")
    else:
        print(f"[startup] Qdrant'da {collection_count()} ta chunk allaqachon mavjud, ingest o'tkazib yuborildi")


class ChatIn(BaseModel):
    question: str


@api.get("/health")
def health():
    return {"status": "ok", "chunks": collection_count()}


@api.post("/chat")
def chat(body: ChatIn):
    r = get_agent().invoke({
        "question": body.question,
        "documents": [], "generation": "", "steps": [], "sources": [], "retries": 0,
    })
    return {"answer": r["generation"], "steps": r["steps"], "sources": r["sources"]}


@api.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """Yangi PDF yuklab, Qdrant'ga qo'shish uchun endpoint (ixtiyoriy — demo standart PDF bilan ishlaydi)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        n = ingest_pdf(tmp_path)
    finally:
        os.remove(tmp_path)
    return {"filename": file.filename, "chunks_added": n}
