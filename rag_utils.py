# rag_utils.py — RAG index helper (uses tmp_uploads/chroma_db)
import os
from typing import List, Tuple

# Document loading & splitting (langchain community loaders)
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# SentenceTransformers embeddings
from sentence_transformers import SentenceTransformer

# Chroma DB (persistent)
import chromadb
from chromadb.config import Settings

class RAGIndex:
    def __init__(self, persist_dir: str = "tmp_uploads/chroma_db", model_name: str = "all-MiniLM-L6-v2"):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)

        # Sentence transformer for embeddings
        self.model = SentenceTransformer(model_name)

        # Use persistent client so DB is stored on disk
        try:
            # When using persistent client, pass path
            self.client = chromadb.PersistentClient(path=self.persist_dir)
        except Exception:
            # fallback to regular client (some installations)
            self.client = chromadb.Client(Settings(path=self.persist_dir))

        # Create / get collection
        try:
            self.collection = self.client.get_or_create_collection(name="docs")
        except Exception:
            # Some chroma versions use create_collection
            try:
                self.collection = self.client.create_collection(name="docs")
            except Exception as e:
                raise

    def load_pdf(self, file_path: str):
        """
        Load a PDF, split into chunks, embed, and add to Chroma.
        """
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        if not docs:
            print("⚠️ No pages found in PDF:", file_path)
            return

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
        chunks = text_splitter.split_documents(docs)

        ids, texts = [], []
        for i, c in enumerate(chunks):
            ids.append(f"{os.path.basename(file_path)}_{i}")
            texts.append(c.page_content)

        if not texts:
            print("⚠️ No text chunks extracted:", file_path)
            return

        # compute embeddings in batch
        embeddings = self.model.encode(texts).tolist()
        # add to collection
        try:
            self.collection.add(ids=ids, embeddings=embeddings, documents=texts)
            print(f"✅ Indexed {len(texts)} chunks from {os.path.basename(file_path)}")
        except Exception as e:
            print("❌ Failed to add to chroma:", e)
            # try recreate collection and add
            try:
                self.collection = self.client.get_or_create_collection(name="docs")
                self.collection.add(ids=ids, embeddings=embeddings, documents=texts)
            except Exception as e2:
                raise

    def query(self, query_text: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Query vector DB for semantic matches. Returns list of (document_text, distance/score).
        """
        try:
            if not self.collection.count():
                return []
        except Exception:
            # If collection.count isn't implemented, attempt a query and catch empty
            pass

        q_emb = self.model.encode([query_text]).tolist()
        try:
            results = self.collection.query(query_embeddings=q_emb, n_results=top_k)
        except Exception as e:
            # Some versions return dict differently; try alternate call
            try:
                results = self.collection.query(query_embeddings=q_emb, top_k=top_k)
            except Exception:
                return []

        # results typically has "documents" and "distances"
        documents = results.get("documents", [[]])[0] if isinstance(results, dict) else (results["documents"][0] if "documents" in results else [])
        distances = results.get("distances", [[]])[0] if isinstance(results, dict) else (results["distances"][0] if "distances" in results else [])

        pairs = []
        for i, doc in enumerate(documents):
            try:
                dist = distances[i] if i < len(distances) else 0.0
            except Exception:
                dist = 0.0
            pairs.append((doc, float(dist)))
        # filter low-similarity (optional): if distance metric is large = dissimilar (depends on chroma settings)
        # keep as-is and let agent decide
        return pairs

    def count(self) -> int:
        try:
            return int(self.collection.count())
        except Exception:
            # if not available
            try:
                return len(self.collection.get())  # may be heavy
            except Exception:
                return 0

    def clear(self):
        try:
            self.collection.delete(where={})
        except Exception:
            # fallback: recreate
            try:
                self.client.delete_collection(name="docs")
            except Exception:
                pass
