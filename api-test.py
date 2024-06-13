import requests
from PIL import Image
import io
import base64
import time
from PIL import Image
from datetime import datetime
import sys
from constants import ModelName

# endpoint = "http://nicheimage.nichetensor.com/api/v1"
endpoint = "http://localhost:8000/api/v1"

headers = {
    "API_KEY": "api-key",
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
    
def fetch_GoJourney(task_id):
    endpoint = "https://api.midjourneyapi.xyz/mj/v2/fetch"
    data = {"task_id": task_id}
    response = requests.post(endpoint, json=data)
    return response.json()

def txt2img(headers=headers):
    try:
        data = {
            "prompt": "photo, man",
            "model_name": ModelName.JUGGERNAUT_XL.value,
            "seed": 0,
            "aspect_ratio": "19:13",
        }
        if data["model_name"] == ModelName.FACE_TO_MANY.value:
            print(f'===> {ModelName.FACE_TO_MANY.value} model does not support txt2img. Use img2img instead.')
            return
        route_str = "/txt2img"
        response = requests.post(endpoint + route_str, json=data, headers=headers)
            
        response.raise_for_status()
        response = response.json()
        print('===> response', response)
        if data["model_name"] == ModelName.GO_JOURNEY.value:
            task_response = response["response_dict"]
            task_status = task_response["status"]
            task_id = task_response["task_id"]
            img_url = ''
            if task_status == "failed":
                return
            while True:
                task_response = fetch_GoJourney(task_id)
                if task_response["status"] == "finished":
                    img_url = task_response["task_result"]["image_url"]
                    print("===> Done")
                    break
                else:
                    print("===> Waiting for the image to be ready...")
                time.sleep(2)
            if img_url and img_url != '':
                image = Image.open(requests.get(img_url, stream=True).raw)
                save_img_to_disk(image)
        else:
            base64_image = response["image"]
            image = base64_to_pil_image(base64_image)
            save_img_to_disk(image)
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except requests.exceptions.RequestException as err:
        print(f"Error occurred: {err}")
    
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
    # Receiving API_KEY as an argument
    if (len(sys.argv) > 1):
        txt2img(headers={
            "API_KEY": sys.argv[1],
        })
    else:
        txt2img()
    # img2img()