FROM python:3.11-slim

WORKDIR /code

# PyMuPDF va Pillow uchun kerakli tizim kutubxonalari
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces (Docker SDK) har doim 7860-portni kutadi
EXPOSE 7860

# Yozish huquqi kerak bo'lgan joylar (Qdrant embedded bazasi shu yerga yoziladi)
RUN mkdir -p /code/qdrant_db && chmod -R 777 /code

CMD ["uvicorn", "app.main:api", "--host", "0.0.0.0", "--port", "7860"]
