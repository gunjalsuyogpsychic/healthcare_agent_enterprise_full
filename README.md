# Agentic Healthcare Assistant for Medical Task Automation (Enterprise)

## Features
- LangGraph multi-agent orchestration: intent router + specialized task agents
- Appointment booking: slot discovery + booking into SQLite DB
- Medical record updates: add unstructured notes & imported reports
- Medical history retrieval: summarizes stored records
- Medical info RAG: FAISS index built from trusted PDFs in `data/pdf_sources/`

## Run locally (Groq)
```bash
pip install -r requirements.txt
export GROQ_API_KEY="YOUR_KEY"
export LLM_PROVIDER="groq"
streamlit run app.py
```

## Demo steps
1) Click **Seed demo patients + appointments**
2) Click **Build / Refresh Knowledge Base (RAG)**
3) Ask:
- Book an appointment with Cardiology next Monday morning for Anjali
- Add record for patient Anjali: Diabetes diagnosed 2019, on Metformin
- Show medical history for patient Ramesh
- What are symptoms and treatment options for hypertension?

## Streamlit Cloud
Deploy with main file `app.py` and add secrets:
- GROQ_API_KEY
- LLM_PROVIDER=groq
