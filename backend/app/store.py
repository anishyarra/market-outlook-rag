import os
from chromadb import PersistentClient

# backend/app -> backend/
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(DATA_DIR, "docs")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

def get_collection():
    client = PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(name="reports")

def get_paths():
    return {"docs_dir": DOCS_DIR, "chroma_dir": CHROMA_DIR}