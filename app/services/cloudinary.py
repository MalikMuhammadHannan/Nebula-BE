import cloudinary
import cloudinary.uploader

from app.config import CLOUDINARY_API_KEY,CLOUDINARY_CLOUD_NAME,CLOUDINARY_API_SECRET


cloudinary.config(
    cloud_name = CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret = CLOUDINARY_API_SECRET
)

def upload_image(file):
    result = cloudinary.uploader.upload(
        file,
        folder="blogs"
    )
    
    return {
        "url":result["secure_url"],
        "public_id":result["public_id"]
    }