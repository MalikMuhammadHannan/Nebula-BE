from app.services.image_generator import image_generator
image = image_generator.generate(
    "hello"
)
image.save("test.png")
print(image, "image generated!")