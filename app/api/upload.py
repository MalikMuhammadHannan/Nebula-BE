import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.core.jwt import get_current_user
from app.models.user import User
from app.services.cloudinary import upload_image


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

MAX_FILE_SIZE = 5 * 1024 * 1024  
CHUNK_SIZE = 64 * 1024

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _detect_image_type(header: bytes) -> str | None:
    """Identify the real image type from its magic bytes (don't trust the client)."""
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


async def _read_limited(file: UploadFile) -> bytes:
    """Read the upload in chunks, aborting as soon as it exceeds MAX_FILE_SIZE."""
    buffer = bytearray()
    while chunk := await file.read(CHUNK_SIZE):
        buffer.extend(chunk)
        if len(buffer) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB",
            )
    return bytes(buffer)


@router.post("/image")
async def upload_blog_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, WEBP and GIF images are allowed",
        )

    contents = await _read_limited(file)
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    if _detect_image_type(contents[:16]) is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content is not a valid image",
        )

    try:
        result = await run_in_threadpool(upload_image, io.BytesIO(contents))
    except Exception:
        logger.exception("Image upload failed for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image upload failed. Please try again later.",
        )
    finally:
        await file.close()

    return {
        "message": "Image uploaded successfully",
        "image_url": result["url"],
        "public_id": result["public_id"]
    }
