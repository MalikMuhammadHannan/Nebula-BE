import torch
from diffusers import StableDiffusionPipeline


class ImageGenerator:
    def __init__(self):
        model_id = "diffusers/tiny-stable-diffusion-torch"
        self.pipe=StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            safety_checker=None,
        )
        self.pipe = self.pipe.to("cpu")

        
    def generate(self,prompt:str):
        image = self.pipe(
            prompt,
            num_inference_steps=20,
            height=256,
            width=256
        ).images[0]
        return image
    
    
image_generator = ImageGenerator()
