---
title: Agentic RAG Backend
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Agentic RAG — Backend (Hugging Face Spaces)

LangGraph asosidagi agentic RAG: retrieve → grade_documents → (web_search) →
generate → (hallucination/answer grading) → self-correct.

## Loyihaning tuzilishi

```
backend/
  app/
    __init__.py
    config.py     # kalitlar va sozlamalar
    ingest.py     # PDF -> matn+rasm -> chunk -> embedding -> Qdrant
    graders.py    # 3 ta grader (doc/hallucination/answer) + generatsiya zanjiri
    graph.py      # GraphState, 4 ta node, routing, LangGraph agent
    main.py       # FastAPI: /health, /chat, /ingest
  data/
    Principles_of_Economics.pdf   # standart hujjat — konteyner ishga tushganda avtomatik ingest bo'ladi
  requirements.txt
  Dockerfile
  .env.example
  README.md       # <- shu fayl (HF Space konfiguratsiyasi tepasidagi YAML orqali)
```

## 1) Hugging Face Space yaratish

1. https://huggingface.co/new-space ga o'ting.
2. **Space name** kiriting (masalan `agentic-rag-backend`).
3. **SDK**: **Docker** tanlang (shablon: "Blank" bo'lsa ham bo'ladi).
4. **Hardware**: Free (CPU basic) yetarli.
5. **Create Space** tugmasini bosing.

## 2) Kodni Space'ga yuklash

Ikki yo'l bor — birini tanlang:

**A) Git orqali (tavsiya etiladi):**
```bash
git clone https://huggingface.co/spaces/<username>/<space-name>
cd <space-name>
# shu backend/ papkadagi barcha fayllarni shu yerga ko'chiring (Dockerfile, app/, data/, requirements.txt, README.md)
git add .
git commit -m "Agentic RAG backend"
git push
```

**B) Veb interfeys orqali:**
Space sahifasida **Files** → **Add file** → **Upload files** orqali barcha
fayl va papkalarni (`app/`, `data/`, `Dockerfile`, `requirements.txt`, `README.md`)
yuklang. `data/Principles_of_Economics.pdf` ~14 MB bo'lgani uchun HF avtomatik
Git-LFS orqali saqlaydi — bu normal holat, kutib turing.

## 3) Kalitlarni sozlash (Secrets)

Space sahifasida: **Settings → Variables and secrets → New secret**

| Nomi | Qiymati |
|---|---|
| `OPENAI_API_KEY` | sizning OpenAI kalitingiz |
| `TAVILY_API_KEY` | sizning Tavily kalitingiz |

`.env` faylni Space'ga hech qachon yuklamang — kalitlar faqat shu Secrets orqali kiritiladi.

## 4) Build va birinchi ishga tushish

Secrets saqlangach, Space avtomatik qayta build bo'ladi (**Logs** bo'limidan kuzating).
Birinchi marta ishga tushganda `startup_ingest()` standart PDF'ni (Principles of
Economics) avtomatik o'qib, rasmlarni caption qilib, Qdrant'ga yozadi — bu bir
necha daqiqa vaqt olishi mumkin (rasm captioning uchun OpenAI so'rovlari ketadi).
Loglarda `[startup] Standart PDF ingest qilindi: N ta chunk` yozuvini kutib turing.

> **Eslatma:** HF Spaces bepul tarifida disk doimiy (persistent) emas — Space
> uyqudan uyg'onganda yoki qayta build bo'lganda konteyner qayta boshlanadi va
> `startup_ingest()` PDF'ni yana avtomatik ingest qiladi. Shu sababli qo'lda
> qayta ingest qilish shart emas.

## 5) Tekshirish

Space public URL'i (odatda `https://<username>-<space-name>.hf.space`) tayyor bo'lgach:

```bash
curl https://<username>-<space-name>.hf.space/health
# {"status":"ok","chunks":...}

curl -X POST https://<username>-<space-name>.hf.space/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is scarcity in economics?"}'
```

`/chat` javobida `answer`, `steps` (bosilgan node'lar) va `sources` (citation'lar) qaytadi.

## 6) Muammolarni bartaraf etish

| Belgi | Sabab / yechim |
|---|---|
| Build xatosi: kutubxona versiyasi topilmadi | `requirements.txt`dagi versiyani olib tashlang (`==x.y.z` o'chiring) — HF eng so'nggi mos versiyani o'rnatadi |
| `RuntimeError: OPENAI_API_KEY topilmadi` | Secrets bo'limiga kalitni qo'shmagansiz yoki nomi noto'g'ri yozilgan |
| `/health` chunks: 0 bo'lib qolyapti | Loglarni tekshiring — `startup_ingest()` xatolik bilan to'xtagan bo'lishi mumkin (odatda OpenAI kvota/kalit muammosi) |
| Space "sleeping" holatida | Bepul Space'lar faolsizlikdan keyin uxlaydi; birinchi so'rov uni uyg'otadi va ~30-60s kutish kerak bo'ladi |

## Keyingi bosqich

Bu backend tayyor bo'lgach, **frontend** (Next.js, Vercel) qurib, uning
`NEXT_PUBLIC_API_URL` qiymatini shu Space URL'iga yo'naltiramiz.
