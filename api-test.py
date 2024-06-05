import requests
from tqdm import tqdm
import random
from PIL import Image
import io
import base64
import time
from PIL import Image
from datetime import datetime

# endpoint = "http://nicheimage.nichetensor.com/api/v1"
endpoint = "http://localhost:8000/api/v1"

headers = {
    "API_KEY": "capricorn_feb",
}
    
def base64_to_pil_image(base64_image):
        image = base64.b64decode(base64_image)
        image = io.BytesIO(image)
        image = Image.open(image)
        return image

def image_grid(imgs, rows, cols):
    assert len(imgs) == rows*cols

    w, h = imgs[0].size
    grid = Image.new('RGB', size=(cols*w, rows*h))
    grid_w, grid_h = grid.size

    for i, img in enumerate(imgs):
        grid.paste(img, box=(i%cols*w, i//cols*h))
    return grid

def pil_image_to_base64(image: Image.Image, format="JPEG") -> str:
    if format not in ["JPEG", "PNG"]:
        format = "JPEG"
    image_stream = io.BytesIO()
    image.save(image_stream, format=format)
    base64_image = base64.b64encode(image_stream.getvalue()).decode("utf-8")
    return base64_image

def save_img_to_disk(image):
    # Get current date and time
    now = datetime.now()

    # Format as a string
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")

    # Use as part of filename
    filename = f"output_{timestamp_str}.png"

    image.save(filename)
    
def txt2img():
    data = {
        "prompt": "photo, man",
        "model_name": "JuggernautXL",
        "seed": 0,
        "aspect_ratio": "19:13",
    }
    response = requests.post(endpoint + "/txt2img", json=data, headers=headers)
    response.raise_for_status()
    response = response.json()
    base64_image = response["image"]
    image = base64_to_pil_image(base64_image)
    save_img_to_disk(image)
    
def resize_divisible(image, max_size=1024, divisible=16):
    W, H = image.size
    if W > H:
        W, H = max_size, int(max_size * H / W)
    else:
        W, H = int(max_size * W / H), max_size
    W = W - W % divisible
    H = H - H % divisible
    image = image.resize((W, H))
    return image

def img2img():
    face_image_url = "https://parrotprint.com/media/wordpress/7630543941b44634748ddea65e5a417c.webp"
    face_image = Image.open(requests.get(face_image_url, stream=True).raw)
    face_image = resize_divisible(face_image, 1024, 16)
    print(face_image.size)
    
    base64_face_image = pil_image_to_base64(face_image)
    data = {
        "prompt": "anime colors, ghibi studio, girl, surrounded by magical glow,floating ice shards, snow crystals, cold, windy background",
        "model_name": "DreamShaperXL",
        "conditional_image": base64_face_image,
        "seed": 0,
    }
    response = requests.post(endpoint + "/instantid", json=data, headers=headers)
    response = response.json()
    base64_image = response["image"]
    image = base64_to_pil_image(base64_image)
    save_img_to_disk(image)
    
if __name__ == "__main__":
    # txt2img()
    img2img()