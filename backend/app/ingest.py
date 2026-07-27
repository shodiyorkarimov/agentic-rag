import base64
import io
import os
from typing import List

import fitz  # PyMuPDF
from PIL import Image
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from . import config

_vision_llm = ChatOpenAI(model=config.VISION_MODEL, temperature=0)
_embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)

_client: QdrantClient | None = None
_vectorstore: QdrantVectorStore | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(path=config.QDRANT_PATH)
    return _client


def get_vectorstore() -> QdrantVectorStore:
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    client = get_client()
    if not client.collection_exists(config.COLLECTION_NAME):
        client.create_collection(
            collection_name=config.COLLECTION_NAME,
            vectors_config=VectorParams(size=config.EMBEDDING_DIM, distance=Distance.COSINE),
        )
    _vectorstore = QdrantVectorStore(
        client=client,
        collection_name=config.COLLECTION_NAME,
        embedding=_embeddings,
    )
    return _vectorstore


def get_retriever(k: int | None = None):
    return get_vectorstore().as_retriever(search_kwargs={"k": k or config.TOP_K})


def collection_count() -> int:
    client = get_client()
    if not client.collection_exists(config.COLLECTION_NAME):
        return 0
    return client.get_collection(config.COLLECTION_NAME).points_count


def _normalize_image(image_bytes: bytes) -> bytes:
    """Har qanday formatdagi rasmni PNG'ga aylantiradi (OpenAI faqat PNG/JPEG/GIF/WEBP qabul qiladi)."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _caption_image(img_bytes: bytes) -> str:
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    msg = HumanMessage(content=[
        {"type": "text", "text": "Rasmda nima tasvirlangan? Qisqa va aniq tasvirlab ber (1-2 gap). "
                                  "Agar diagramma, grafik yoki jadval bo'lsa, mazmunini yoz."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ])
    response = _vision_llm.invoke([msg])
    return response.content


def load_pdf_as_documents(pdf_path: str) -> List[Document]:
    """PDF'dan matn va rasm (caption) hujjatlarini chiqaradi — multimodal ingest."""
    docs: List[Document] = []
    pdf = fitz.open(pdf_path)
    source_name = os.path.basename(pdf_path)

    for page_num, page in enumerate(pdf):
        text = page.get_text()
        if text.strip():
            docs.append(Document(
                page_content=text,
                metadata={"source": source_name, "page": page_num + 1, "type": "text"},
            ))

        for img in page.get_images(full=True):
            xref = img[0]
            base_image = pdf.extract_image(xref)
            image_bytes = base_image["image"]
            try:
                png_bytes = _normalize_image(image_bytes)
                check = Image.open(io.BytesIO(png_bytes))
                if check.width < 40 or check.height < 40:
                    continue  # ikonka/chiziqcha kabi foydasiz rasmlarni o'tkazib yuboramiz
                caption = _caption_image(png_bytes)
                docs.append(Document(
                    page_content=f"[Rasm tavsifi] {caption}",
                    metadata={"source": source_name, "page": page_num + 1, "type": "image"},
                ))
            except Exception:
                continue

    pdf.close()
    return docs


def ingest_pdf(pdf_path: str) -> int:
    """PDF'ni to'liq ingest qiladi: yukla -> chunk -> embed -> Qdrant'ga saqla.
    Qo'shilgan chunk sonini qaytaradi."""
    docs = load_pdf_as_documents(pdf_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)
    get_vectorstore().add_documents(chunks)
    return len(chunks)
