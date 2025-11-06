import json, os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings

SCHEMA_PATH = "db/schema_metadata.json"
CHROMA_DIR = "db/chroma_store"

with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    schema = json.load(f)

documents = [f"Table {t} has columns: {', '.join(cols)}." for t, cols in schema.items()]

embedding_model = OllamaEmbeddings(model="llama3")

vector_store = Chroma.from_texts(
    documents,
    embedding=embedding_model,
    persist_directory=CHROMA_DIR
)
vector_store.persist()
print(f"Local embeddings created via Ollama and stored in {CHROMA_DIR}")
