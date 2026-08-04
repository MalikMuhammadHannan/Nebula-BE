from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.cloudinary import upload_image


router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

@router.post("/image")

async def upload_blog_image(file:UploadFile=File(...)):
    try:
        result = upload_image(file.file)
        return {
            "message": "Image uploaded successfully",
            "image_url": result["url"],
            "public_id": result["public_id"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=(str(e)))
        
        
