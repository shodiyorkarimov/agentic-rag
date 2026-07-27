import os

# --- Kalitlar (Hugging Face Space'da "Secrets" bo'limidan keladi) ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY topilmadi. Hugging Face Space > Settings > Variables and secrets "
        "bo'limiga OPENAI_API_KEY qo'shing."
    )
if not TAVILY_API_KEY:
    raise RuntimeError(
        "TAVILY_API_KEY topilmadi. Hugging Face Space > Settings > Variables and secrets "
        "bo'limiga TAVILY_API_KEY qo'shing."
    )

# --- Modellar ---
CHAT_MODEL = "gpt-4o-mini"
VISION_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536  # text-embedding-3-small o'lchami

# --- Qdrant (embedded, server kerak emas) ---
QDRANT_PATH = os.environ.get("QDRANT_PATH", "qdrant_db")
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION", "my_docs")

# --- Agent sozlamalari ---
TOP_K = int(os.environ.get("TOP_K", "4"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))

# --- Konteyner ichida standart bo'lib ingest qilinadigan PDF ---
DEFAULT_PDF_PATH = os.environ.get("DEFAULT_PDF_PATH", "data/Principles_of_Economics.pdf")
