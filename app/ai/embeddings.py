from langchain_huggingface import HuggingFaceEmbeddings
from typing import List

class EmbeddingService:
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_model(self):
        if self._model is None:
            self._model = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        return self._model
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Use for document chunks (indexing time)."""
        return self.get_model().embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """Use for search queries (retrieval time)."""
        return self.get_model().embed_query(text)


embedding_service = EmbeddingService()
        