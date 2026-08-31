from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"}
)
texts = ["Hello world", "How are you?", "This is a test sentence."]

vectors = embeddings.embed_documents(texts)

print(f"Number of vectors: {len(vectors)}")
print(f"Dimension of each vector: {len(vectors[0])}")
print(vectors[0][:5])