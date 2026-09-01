from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List


class ChunkingService:
    def __init__(self, chunk_size:int=500, chunk_overlap:int=50):
        self.chunk_size=chunk_size
        self.chunk_overlap=chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
                 chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        
        
    def split_text(self,text:str)->list[str]:
        
        if not text or not text.strip():
            return []
        
        chunks = self.splitter.split_text(text)
        return [chunk.strip() for chunk in chunks if chunk.strip()]

        

chunking_service = ChunkingService()