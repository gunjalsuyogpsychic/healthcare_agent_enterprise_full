from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def init_kb(pdf_dir: str, faiss_dir: str, embedding_model: str):
    pdf_path = Path(pdf_dir)
    pdfs = sorted([p for p in pdf_path.glob("*.pdf")])
    docs = []
    for p in pdfs:
        loader = PyPDFLoader(str(p))
        docs.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    chunks = splitter.split_documents(docs) if docs else []

    embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
    if chunks:
        db = FAISS.from_documents(chunks, embeddings)
    else:
        db = FAISS.from_texts(["No PDFs indexed yet. Add PDFs to data/pdf_sources and rebuild KB."], embeddings)

    Path(faiss_dir).mkdir(parents=True, exist_ok=True)
    db.save_local(faiss_dir)
    return db

def load_kb(faiss_dir: str, embedding_model: str) -> FAISS:
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
    return FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)

def retrieve_medical_docs(db: FAISS, query: str, k: int=4):
    return db.similarity_search(query, k=k)
