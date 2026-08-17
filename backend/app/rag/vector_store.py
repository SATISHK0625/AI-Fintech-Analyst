import os
import chromadb
from chromadb.utils import embedding_functions
from app.config import settings

class VectorStoreManager:
    def __init__(self):
        os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
        
        # Local Sentence Transformers embedding model
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL_NAME
        )
        
        self.collection = self.client.get_or_create_collection(
            name="financial_knowledge_base",
            embedding_function=self.embedding_fn
        )

    def seed_initial_knowledge(self):
        """Indexes initial company financial policy documents into vector store tagged by company_id."""
        if self.collection.count() > 0:
            return

        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.abspath(os.path.join(current_dir, "..", "data", "policies"))

        policies = [
            (1, "ApexTech_Financial_Control_Policies.md", "ApexTech Solutions Inc."),
            (2, "BioHealth_Financial_Control_Policies.md", "BioHealth Dynamics Inc."),
            (3, "Nexus_Financial_Control_Policies.md", "Nexus Logistics Global")
        ]

        documents = []
        metadatas = []
        ids = []

        counter = 1
        for comp_id, filename, comp_name in policies:
            path = os.path.join(data_dir, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                sections = content.split("## ")
                for sec in sections:
                    sec_text = sec.strip()
                    if not sec_text:
                        continue

                    full_text = f"{comp_name} Policy Section: {sec_text}"
                    documents.append(full_text)
                    metadatas.append({
                        "category": "enterprise_policy",
                        "source": filename,
                        "company_id": comp_id
                    })
                    ids.append(f"policy_doc_{counter}")
                    counter += 1

        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

    def add_custom_documents(self, text_chunks: list[str], source_name: str, company_id: int = 1) -> int:
        """Dynamically indexes user uploaded document text chunks into the RAG vector store tagged by company_id."""
        if not text_chunks:
            return 0
        
        start_id = self.collection.count() + 1
        ids = [f"doc_{start_id + i}" for i in range(len(text_chunks))]
        metadatas = [{"category": "uploaded_document", "source": source_name, "company_id": company_id} for _ in text_chunks]

        self.collection.add(
            documents=text_chunks,
            metadatas=metadatas,
            ids=ids
        )
        return len(text_chunks)

    def search_knowledge_base(self, query: str, n_results: int = 4, company_id: int = None) -> list[dict]:
        """Searches vector store and returns top semantic matches filtered by company_id."""
        kwargs = {
            "query_texts": [query],
            "n_results": n_results
        }
        if company_id is not None:
            kwargs["where"] = {"company_id": company_id}

        try:
            results = self.collection.query(**kwargs)
        except Exception:
            # Fallback if where filter fails on older collection
            kwargs.pop("where", None)
            results = self.collection.query(**kwargs)
        
        output = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            for doc, meta in zip(docs, metas):
                output.append({
                    "content": doc,
                    "metadata": meta
                })
        return output

# Singleton instance
vector_store = VectorStoreManager()
