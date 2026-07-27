from typing import TypedDict

from langchain_core.documents import Document
from langchain_tavily import TavilySearch
from langgraph.graph import END, StateGraph

from . import config
from .graders import (
    answer_grader_chain,
    doc_grader_chain,
    format_docs,
    hallucination_grader_chain,
    rag_chain,
)
from .ingest import get_retriever

tavily_search = TavilySearch(max_results=3)


class GraphState(TypedDict):
    question: str
    documents: list
    generation: str
    steps: list       # bajarilgan qadamlar (frontend'da ko'rsatish uchun)
    sources: list      # javob uchun ishlatilgan manbalar (citation)
    retries: int        # qayta urinishlar soni (cheksiz aylanmaslik uchun)


# ============ NODE 1: retrieve ============
def retrieve(state: GraphState):
    documents = get_retriever().invoke(state["question"])
    return {"documents": documents, "steps": state.get("steps", []) + ["retrieve"]}


# ============ NODE 2: grade_documents ============
def grade_documents(state: GraphState):
    question = state["question"]
    filtered = []
    for d in state["documents"]:
        result = doc_grader_chain.invoke({"document": d.page_content, "question": question})
        if result.binary_score == "yes":
            filtered.append(d)
    return {"documents": filtered, "steps": state.get("steps", []) + ["grade_documents"]}


# ============ NODE 3: web_search ============
def web_search(state: GraphState):
    question = state["question"]
    result = tavily_search.invoke({"query": question})
    raw_results = result.get("results", result) if isinstance(result, dict) else result
    web_docs = [
        Document(page_content=r["content"], metadata={"source": r.get("url", "web"), "type": "web"})
        for r in raw_results if isinstance(r, dict) and "content" in r
    ]
    documents = state.get("documents", []) + web_docs
    return {"documents": documents, "steps": state.get("steps", []) + ["web_search"]}


# ============ NODE 4: generate ============
def generate(state: GraphState):
    context = format_docs(state["documents"])
    answer = rag_chain.invoke({"context": context, "question": state["question"]})
    sources = [
        {"page": d.metadata.get("page"), "type": d.metadata.get("type"), "source": d.metadata.get("source")}
        for d in state["documents"]
    ]
    return {
        "generation": answer,
        "sources": sources,
        "steps": state.get("steps", []) + ["generate"],
        "retries": state.get("retries", 0) + 1,
    }


# ============ Routing funksiyalar ============
def route_after_grade(state: GraphState):
    return "web_search" if len(state["documents"]) == 0 else "generate"


def route_after_generate(state: GraphState):
    if state.get("retries", 0) >= config.MAX_RETRIES:
        return "useful"   # retry cap — cheksiz tsiklga yo'l qo'ymaymiz

    docs_text = format_docs(state["documents"])
    h = hallucination_grader_chain.invoke({"documents": docs_text, "generation": state["generation"]})
    if h.binary_score == "no":
        return "not_grounded"

    a = answer_grader_chain.invoke({"question": state["question"], "generation": state["generation"]})
    return "useful" if a.binary_score == "yes" else "not_useful"


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("retrieve", retrieve)
    g.add_node("grade_documents", grade_documents)
    g.add_node("web_search", web_search)
    g.add_node("generate", generate)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "grade_documents")
    g.add_conditional_edges("grade_documents", route_after_grade,
                             {"web_search": "web_search", "generate": "generate"})
    g.add_edge("web_search", "generate")
    g.add_conditional_edges("generate", route_after_generate,
                             {"useful": END, "not_grounded": "generate", "not_useful": "web_search"})
    return g.compile()


_compiled_app = None


def get_agent():
    """LangGraph agentni bir marta compile qiladi va keyingi chaqiruvlarda qayta ishlatadi."""
    global _compiled_app
    if _compiled_app is None:
        _compiled_app = build_graph()
    return _compiled_app
