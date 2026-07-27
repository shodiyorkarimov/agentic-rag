from typing import Literal

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from . import config

llm = ChatOpenAI(model=config.CHAT_MODEL, temperature=0)


class GradeDocuments(BaseModel):
    """Retrieved hujjat savolga tegishlimi?"""
    binary_score: Literal["yes", "no"] = Field(
        description="Hujjat savolga tegishli bo'lsa 'yes', bo'lmasa 'no'"
    )


class GradeHallucination(BaseModel):
    """Javob berilgan hujjatlar bilan asoslanganmi (o'ylab topilmaganmi)?"""
    binary_score: Literal["yes", "no"] = Field(
        description="Javob hujjatlarga asoslangan bo'lsa 'yes', o'ylab topilgan bo'lsa 'no'"
    )


class GradeAnswer(BaseModel):
    """Javob savolga haqiqatan ham javob beradimi?"""
    binary_score: Literal["yes", "no"] = Field(
        description="Javob savolni hal qilsa 'yes', qilmasa 'no'"
    )


doc_grader = llm.with_structured_output(GradeDocuments)
hallucination_grader = llm.with_structured_output(GradeHallucination)
answer_grader = llm.with_structured_output(GradeAnswer)

# --- Hujjat grading uchun prompt ---
grade_prompt = ChatPromptTemplate.from_messages([
    ("system", "Siz retrieved hujjat foydalanuvchi savoliga tegishli yoki tegishli emasligini "
               "aniqlaydigan graderesiz. Agar hujjatda savolga oid kalit so'zlar yoki semantik "
               "aloqa bo'lsa, tegishli deb belgilang. Maqsad — aniq noto'g'ri natijalarni "
               "filtrlash, shuning uchun qattiq test shart emas."),
    ("human", "Retrieved hujjat:\n\n{document}\n\nFoydalanuvchi savoli: {question}"),
])
doc_grader_chain = grade_prompt | doc_grader

# --- Hallyutsinatsiya grading uchun prompt ---
hallucination_prompt = ChatPromptTemplate.from_messages([
    ("system", "Siz LLM javobi berilgan hujjatlar (faktlar) bilan asoslanganligini tekshiruvchi "
               "graderesiz. Javob hujjatlardagi ma'lumotlarga tayangan bo'lsa 'yes', o'ylab "
               "topilgan yoki hujjatlarda yo'q da'volar bo'lsa 'no' bering."),
    ("human", "Hujjatlar:\n\n{documents}\n\nLLM javobi:\n{generation}"),
])
hallucination_grader_chain = hallucination_prompt | hallucination_grader

# --- Javob relevantligi grading uchun prompt ---
answer_prompt = ChatPromptTemplate.from_messages([
    ("system", "Siz LLM javobi foydalanuvchi savoliga haqiqatan javob berayotganini "
               "tekshiruvchi graderesiz."),
    ("human", "Savol: {question}\n\nLLM javobi: {generation}"),
])
answer_grader_chain = answer_prompt | answer_grader

# --- Javob generatsiyasi uchun prompt ---
rag_prompt = ChatPromptTemplate.from_template(
    """Siz savolga faqat berilgan kontekst asosida javob beruvchi yordamchisiz.
Agar kontekstda javob yo'q bo'lsa, "Men bu savolga hujjatlar asosida javob bera olmayman" deb ayting.
Javob oxirida foydalanilgan manbalarni [sahifa N] shaklida ko'rsating.

Kontekst:
{context}

Savol: {question}

Javob:"""
)
rag_chain = rag_prompt | llm | StrOutputParser()


def format_docs(docs) -> str:
    return "\n\n".join(f"[sahifa {d.metadata.get('page', '?')}] {d.page_content}" for d in docs)
