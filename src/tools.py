import json
from typing import Dict, Any
from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate

INTENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a healthcare task router. Classify the user's intent into ONE of:\n"
     "1) book_appointment\n"
     "2) update_records\n"
     "3) retrieve_history\n"
     "4) medical_info\n"
     "5) general\n"
     "Return STRICT JSON: intent, confidence (0-1), extracted (object with patient_name, doctor, specialty, date_hint, time_hint, symptoms/topic)."),
    ("human", "{message}")
])

SENTIMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Return STRICT JSON: sentiment (positive|neutral|negative), intensity (0-1), emotions (list), notes (short)."),
    ("human", "{message}")
])

RESPONSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are an Agentic Healthcare Assistant.\n"
     "Safety rules:\n"
     "- Do NOT diagnose. Provide general educational info only.\n"
     "- If emergency symptoms appear (chest pain, severe breathlessness, fainting), advise emergency services.\n"
     "Use context and action outputs; personalize tone based on sentiment."),
    ("human",
     "User message: {message}\n\n"
     "Intent: {intent}\n"
     "Sentiment: {sentiment}\n"
     "Action output: {action}\n"
     "Retrieved context: {context}\n")
])

def _safe_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}

def detect_intent(llm, message: str) -> Dict[str, Any]:
    resp = llm.invoke(INTENT_PROMPT.format_messages(message=message))
    return _safe_json(resp.content if hasattr(resp, "content") else str(resp))

def analyze_sentiment(llm, message: str) -> Dict[str, Any]:
    resp = llm.invoke(SENTIMENT_PROMPT.format_messages(message=message))
    return _safe_json(resp.content if hasattr(resp, "content") else str(resp))

def craft_final_response(llm, message: str, intent: Dict[str, Any], sentiment: Dict[str, Any], action: Dict[str, Any], context: str) -> str:
    resp = llm.invoke(RESPONSE_PROMPT.format_messages(
        message=message,
        intent=json.dumps(intent, indent=2),
        sentiment=json.dumps(sentiment, indent=2),
        action=json.dumps(action, indent=2),
        context=context
    ))
    return resp.content if hasattr(resp, "content") else str(resp)

def parse_date_hint(date_hint: str) -> str:
    base = datetime.utcnow().date()
    if not date_hint:
        return (base + timedelta(days=1)).isoformat()
    dh = date_hint.strip().lower()
    if dh == "today":
        return base.isoformat()
    if dh == "tomorrow":
        return (base + timedelta(days=1)).isoformat()
    weekdays = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    for i, wd in enumerate(weekdays):
        if wd in dh:
            days_ahead = (i - base.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (base + timedelta(days=days_ahead)).isoformat()
    try:
        return datetime.fromisoformat(date_hint).date().isoformat()
    except Exception:
        return (base + timedelta(days=1)).isoformat()

def pick_time_window(time_hint: str):
    if not time_hint:
        return (9, 17)
    th = time_hint.lower()
    if "morning" in th:
        return (9, 12)
    if "afternoon" in th:
        return (12, 17)
    if "evening" in th:
        return (17, 20)
    return (9, 17)
