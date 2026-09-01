from typing import List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.jwt import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.blogs import Blog
from app.schema.blogs import BlogResponse
from app.schema.document import DocumentUploadResponse, DocumentQueryRequest
from app.services.document_extractor import extract_text, get_file_extension
from app.ai.chunking import chunking_service
from app.ai.embeddings import embedding_service

TOP_K_BLOGS = 6

router = APIRouter(
    prefix="/document",
    tags=["Document"]
)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        file_type = get_file_extension(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    file_bytes = await file.read()

    document = Document(
        filename=file.filename,
        file_type=file_type,
        status="processing",
        owner_id=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        text = extract_text(file.filename, file_bytes)
        chunks = chunking_service.split_text(text)
        if not chunks:
            raise ValueError("No extractable text found in document")

        chunk_embeddings = embedding_service.embed_texts(chunks)
        for index, (chunk_text, chunk_embedding) in enumerate(zip(chunks, chunk_embeddings)):
            db.add(DocumentChunk(
                document_id=document.id,
                chunk_text=chunk_text,
                chunk_index=index,
                embedding=chunk_embedding,
            ))

        document.status = "processed"
        db.commit()
    except Exception as e:
        document.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    return DocumentUploadResponse(
        session_id=str(document.id),
        filename=document.filename,
        file_type=document.file_type,
        status=document.status,
    )
    
    
@router.delete("/{session_id}", response_model=DocumentUploadResponse)
def delete_document(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        document_id = int(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    db.delete(document)
    db.commit()

    return DocumentUploadResponse(
        session_id=str(document.id),
        filename=document.filename,
        file_type=document.file_type,
        status="deleted",
    )


@router.get("/all", response_model=List[DocumentUploadResponse])
def get_all_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    documents = db.query(Document).filter(Document.owner_id == current_user.id).all()
    return [
        DocumentUploadResponse(
            session_id=str(doc.id),
            filename=doc.filename,
            file_type=doc.file_type,
            status=doc.status,
        )
        for doc in documents
    ]


@router.post("/query", response_model=List[BlogResponse])
def query_document(
    payload: DocumentQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        document_id = int(payload.session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    query_embedding = embedding_service.embed_query(payload.query)

    blogs = (
        db.query(Blog)
        .filter(Blog.embedding.isnot(None))
        .order_by(Blog.embedding.cosine_distance(query_embedding))
        .limit(TOP_K_BLOGS)
        .all()
    )

    return blogs
