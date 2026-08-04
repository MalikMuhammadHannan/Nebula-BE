import cloudinary
import cloudinary.uploader
import os 
from urllib.parse import urlparse
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
    
def delete_upload_image(image_url: str):
    path = urlparse(image_url).path

    # /dwgbi4yy6/image/upload/v1785848450/blogs/rvvgrmzbf3jh03rek5mx.webp
    public_id = path.split("/upload/")[-1]

    # Remove version
    # v1785848450/blogs/abc.webp -> blogs/abc.webp
    public_id = "/".join(public_id.split("/")[1:])

    # Remove extension
    public_id = os.path.splitext(public_id)[0]

    return cloudinary.uploader.destroy(public_id)