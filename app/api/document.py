from io import BytesIO
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.jwt import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.chat_turn import DocumentChatTurn
from app.schema.document import DocumentUploadResponse, DocumentQueryRequest
from app.services.document_extractor import extract_text, get_file_extension
from app.services.cloudinary import upload_image
from app.services.image_generator import image_generator
from app.ai.chunking import chunking_service
from app.ai.embeddings import embedding_service
from app.ai.llm import LLMService
from app.ai.token_usage import usage_tokens

TOP_K_CHUNKS = 5
HISTORY_LIMIT = 5
RELEVANCE_THRESHOLD = 0.9
# Small models over-use a special keyword like "NOT_FOUND" when it's offered,
# so the prompt asks for a natural sentence and we detect how it starts.
NOT_FOUND_PREFIXES = ("the document does not mention", "the document doesn't mention", "not_found")

QUERY_PROMPT = """You are a document question-answering assistant.

Previous questions in this session (most recent last):
{history}

Relevant document excerpts:
{context}

User question:
{query}

Questions that say "he", "she", "they" or "the name" refer to the person or subject the document is about. The excerpt marked [Start of document] usually begins with that name or title.

Write a concise answer to the question in 2-3 sentences, using only the information in the excerpts and previous answers above. Do not use outside knowledge, and do not guess or invent information. Keep numbers and names exactly as written in the excerpts.
If the excerpts do not cover the question, reply only: The document does not mention this.
"""


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
    db.query(DocumentChatTurn).filter(DocumentChatTurn.document_id == document.id).delete()
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



@router.post("/query")
def query_document(
    payload: DocumentQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty"
        )
    if current_user.token_balance <= 0:
            raise HTTPException(
                status_code=402,
                detail="You have no AI tokens left. Please purchase more tokens to continue.",
            )    

    try:
        document_id = int(payload.session_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    # Only answered turns go into the history: a run of "not found" turns
    # makes the model keep answering NOT_FOUND even when the answer is in the excerpts.
    previous_turns = (
        db.query(DocumentChatTurn)
        .filter(
            DocumentChatTurn.document_id == document.id,
            DocumentChatTurn.found.is_(True),
        )
        .order_by(DocumentChatTurn.created_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    previous_turns.reverse()

    if previous_turns:
        history = "\n".join(
            f"Q: {turn.query}\nA: {turn.title} - {turn.description}"
            for turn in previous_turns
        )
    else:
        history = "(no previous questions in this session)"

    query_embedding = embedding_service.embed_query(
        payload.query
    )

    distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)
    rows = (
        db.query(DocumentChunk, distance_expr.label("distance"))
        .filter(
            DocumentChunk.document_id == document.id,
            DocumentChunk.embedding.isnot(None),
        )
        .order_by(distance_expr)
        .limit(TOP_K_CHUNKS)
        .all()
    )

    chunks = [chunk for chunk, distance in rows if distance <= RELEVANCE_THRESHOLD]

    # The start of a document (name, title, contact details, summary) rarely
    # matches short questions like "what's the name?" semantically, so always
    # include it in the context.
    if not any(chunk.chunk_index == 0 for chunk in chunks):
        first_chunk = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id, DocumentChunk.chunk_index == 0)
            .first()
        )
        if first_chunk:
            chunks.append(first_chunk)

    if not chunks:
        db.add(DocumentChatTurn(document_id=document.id, query=payload.query, found=False))
        db.commit()
        return []

    chunks.sort(key=lambda chunk: chunk.chunk_index)
    context = "\n\n".join(
        ("[Start of document]\n" if chunk.chunk_index == 0 else "[Excerpt]\n") + chunk.chunk_text
        for chunk in chunks
    )

    prompt = LLMService.get_prompt(QUERY_PROMPT)
    chain = prompt | LLMService.get_model()
    raw = chain.invoke({
        "history": history,
        "context": context,
        "query": payload.query,
    })

    tokens_used = usage_tokens(raw)
    current_user.token_balance = max(0, current_user.token_balance - tokens_used)

    answer = (raw.content or "").strip()

    if not answer or answer.lower().startswith(NOT_FOUND_PREFIXES):
        db.add(DocumentChatTurn(document_id=document.id, query=payload.query, found=False))
        db.commit()
        return []

    sentences = [s.strip() for s in answer.replace("\n", " ").split(". ") if s.strip()]
    description = sentences[0] if sentences else answer[:140]
    if not description.endswith("."):
        description += "."
    words = answer.split()
    title = " ".join(words[:8]) + ("..." if len(words) > 8 else "")
    content = answer

    # image_url = None
    # try:
    #     image = image_generator.generate(title)
    #     buffer = BytesIO()
    #     image.save(buffer, format="PNG")
    #     buffer.seek(0)
    #     image_url = upload_image(buffer)["url"]
    # except Exception:
    #     image_url = None

    db.add(DocumentChatTurn(
        document_id=document.id,
        query=payload.query,
        found=True,
        title=title,
        description=description,
        content=content,
        image_url=None,
    ))
    db.commit()

    return [
        {
            "id": 0,
            "title": title,
            "description": description,
            "image_url": None,
            "author_id": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "content": content,
        }
    ]


@router.get("/{session_id}/history")
def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        document_id = int(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Session not found")

    turns = (
        db.query(DocumentChatTurn)
        .filter(DocumentChatTurn.document_id == document.id)
        .order_by(DocumentChatTurn.created_at.asc())
        .all()
    )

    return [
        {
            "id": turn.id,
            "query": turn.query,
            "blogs": [
                {
                    "id": 0,
                    "title": turn.title,
                    "description": turn.description,
                    "image_url": turn.image_url,
                    "author_id": current_user.id,
                    "created_at": turn.created_at.isoformat(),
                    "content": turn.content,
                }
            ] if turn.found else [],
        }
        for turn in turns
    ]
