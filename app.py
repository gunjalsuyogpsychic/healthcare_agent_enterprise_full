import streamlit as st
import pandas as pd
from config import settings
from src.db import init_db, seed_demo_data, list_patients, list_appointments
from src.kb import init_kb
from src.orchestrator import build_graph, run_graph

st.set_page_config(page_title="Agentic Healthcare Assistant", layout="wide")
st.title("Agentic Healthcare Assistant — Medical Task Automation (Enterprise)")

st.sidebar.header("Settings")
provider = st.sidebar.selectbox("LLM Provider", ["groq", "ollama"], index=0 if settings.LLM_PROVIDER=="groq" else 1)
st.sidebar.caption("Groq needs GROQ_API_KEY. Ollama needs local model.")
st.sidebar.divider()
st.sidebar.code(f"DB: {settings.DB_PATH}\nKB: {settings.FAISS_DIR}\nSources: {settings.PDF_SOURCES_DIR}")

init_db(settings.DB_PATH)

with st.sidebar.expander("Demo data"):
    if st.button("Seed demo patients + appointments"):
        seed_demo_data(settings.DB_PATH, settings.PDF_SOURCES_DIR, settings.RECORDS_XLSX)
        st.success("Seeded demo data.")
    if st.button("Build / Refresh Knowledge Base (RAG)"):
        init_kb(settings.PDF_SOURCES_DIR, settings.FAISS_DIR, settings.EMBEDDING_MODEL)
        st.success("Knowledge base built.")

graph = build_graph(provider)

tab1, tab2, tab3 = st.tabs(["Assistant", "Patient & Appointment Dashboard", "Knowledge Base"])

with tab1:
    st.subheader("Chat with the Healthcare Assistant")
    st.caption("Book appointments, update records, retrieve history, or ask medical info questions.")
    msg = st.text_area(
        "User message",
        height=140,
        placeholder="Examples:\n- Book an appointment with Dr. Smith (Cardiology) next Monday morning for Anjali\n- Add record for patient Anjali: Diabetes diagnosed 2019, on Metformin\n- Show medical history for patient Ramesh\n- What are symptoms and treatment options for hypertension?"
    )

    if st.button("Send", type="primary") and msg.strip():
        result = run_graph(graph, msg, db_path=settings.DB_PATH, faiss_dir=settings.FAISS_DIR, embedding_model=settings.EMBEDDING_MODEL)
        st.markdown("### Intent / Task Classification")
        st.json(result.get("intent", {}))
        st.markdown("### Sentiment")
        st.json(result.get("sentiment", {}))
        if result.get("action"):
            st.markdown("### Action Output")
            st.json(result["action"])
        st.markdown("### Final Response")
        st.markdown(result.get("final_response",""))

with tab2:
    st.subheader("Patient & Appointment Dashboard")
    colA, colB = st.columns(2)
    with colA:
        st.markdown("#### Patients")
        st.dataframe(list_patients(settings.DB_PATH, limit=100))
    with colB:
        st.markdown("#### Appointments")
        st.dataframe(list_appointments(settings.DB_PATH, limit=100))

with tab3:
    st.subheader("Knowledge Base (RAG Sources)")
    st.write("Knowledge base is built from PDFs in `data/pdf_sources/` and used to answer medical info questions.")
    st.write("Tip: Click **Build / Refresh Knowledge Base (RAG)** from the sidebar after adding new PDFs.")
    import os
    try:
        pdfs = [p for p in os.listdir(settings.PDF_SOURCES_DIR) if p.lower().endswith(".pdf")]
        st.write(f"PDF sources found: {len(pdfs)}")
        st.code("\n".join(sorted(pdfs)[:80]))
    except Exception as e:
        st.warning(f"Could not list sources: {e}")
