from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END

from src.llm import get_llm
from src.kb import load_kb, retrieve_medical_docs
from src.tools import detect_intent, analyze_sentiment, craft_final_response
from src.agents import appointment_agent, records_agent, history_agent

class HCState(TypedDict, total=False):
    user_message: str
    db_path: str
    faiss_dir: str
    embedding_model: str
    intent: Dict[str, Any]
    sentiment: Dict[str, Any]
    action: Dict[str, Any]
    retrieved_context: str
    final_response: str

def node_intent(state: HCState, llm):
    return {"intent": detect_intent(llm, state["user_message"])}

def node_sentiment(state: HCState, llm):
    return {"sentiment": analyze_sentiment(llm, state["user_message"])}

def node_action(state: HCState):
    intent = state.get("intent", {})
    extracted = intent.get("extracted", {}) if isinstance(intent, dict) else {}
    label = intent.get("intent", "general") if isinstance(intent, dict) else "general"

    if label == "book_appointment":
        return {"action": appointment_agent(state["db_path"], extracted)}
    if label == "update_records":
        return {"action": records_agent(state["db_path"], extracted, state["user_message"])}
    if label == "retrieve_history":
        return {"action": history_agent(state["db_path"], extracted)}
    if label == "medical_info":
        return {"action": {"ok": True, "action": "medical_info", "topic": extracted.get("symptoms/topic") or extracted.get("topic") or "medical question"}}
    return {"action": {"ok": True, "action": "general"}}

def node_retrieve(state: HCState):
    intent = state.get("intent", {})
    label = intent.get("intent", "general") if isinstance(intent, dict) else "general"
    extracted = intent.get("extracted", {}) if isinstance(intent, dict) else {}
    if label != "medical_info":
        return {"retrieved_context": "(not needed)"}
    topic = extracted.get("symptoms/topic") or extracted.get("topic") or state["user_message"]
    try:
        db = load_kb(state["faiss_dir"], state["embedding_model"])
        docs = retrieve_medical_docs(db, topic, k=4)
        ctx = "\n\n".join([f"[{i+1}] {d.page_content[:900]}" for i, d in enumerate(docs)])
        return {"retrieved_context": ctx or "(no relevant context found)"}
    except Exception:
        return {"retrieved_context": "(knowledge base not built yet — click Build/Refresh Knowledge Base)"}

def node_respond(state: HCState, llm):
    return {"final_response": craft_final_response(
        llm,
        message=state["user_message"],
        intent=state.get("intent", {}),
        sentiment=state.get("sentiment", {}),
        action=state.get("action", {}),
        context=state.get("retrieved_context","")
    )}

def build_graph(provider: str):
    llm = get_llm(provider)
    g = StateGraph(HCState)
    g.add_node("intent", lambda s: node_intent(s, llm))
    g.add_node("sentiment", lambda s: node_sentiment(s, llm))
    g.add_node("action", node_action)
    g.add_node("retrieve", node_retrieve)
    g.add_node("respond", lambda s: node_respond(s, llm))
    g.set_entry_point("intent")
    g.add_edge("intent", "sentiment")
    g.add_edge("sentiment", "action")
    g.add_edge("action", "retrieve")
    g.add_edge("retrieve", "respond")
    g.add_edge("respond", END)
    return g.compile()

def run_graph(graph, user_message: str, db_path: str, faiss_dir: str, embedding_model: str):
    state: HCState = {"user_message": user_message, "db_path": db_path, "faiss_dir": faiss_dir, "embedding_model": embedding_model}
    return graph.invoke(state)
