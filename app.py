import asyncio
import base64
import io
import os
import requests
import random
from datetime import date
from typing import Dict, List, Union
import time
import bittensor as bt
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException, Request
from PIL import Image
from threading import Thread
from constants import API_RATE_LIMIT, ModelName
from slowapi import Limiter
from slowapi.util import get_remote_address
from prometheus_fastapi_instrumentator import Instrumentator
from PIL import Image
from utils.data_types import Prompt, TextPrompt, TextToImage, ImageToImage, ValidatorInfo
from utils.db_client import MongoDBHandler

def get_api_key(request: Request):
    return request.headers.get("API_KEY", get_remote_address(request))

limiter = Limiter(key_func=get_api_key)

def pil_image_to_base64(image: Image.Image, format="JPEG") -> str:
    if format not in ["JPEG", "PNG"]:
        format = "JPEG"
    image_stream = io.BytesIO()
    image = image.convert("RGB")
    image.save(image_stream, format=format)
    base64_image = base64.b64encode(image_stream.getvalue()).decode("utf-8")
    return base64_image


MONGO_DB_USERNAME = os.getenv("MONGO_DB_USERNAME")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")

class ImageGenerationService:
    def __init__(self):
        self.subtensor = bt.subtensor("finney")
        self.metagraph = self.subtensor.metagraph(23)
        mongoDBConnectUri = f"mongodb://{MONGO_DB_USERNAME}:{MONGO_DB_PASSWORD}@localhost:27017"
        # mongoDBConnectUri = f"mongodb://localhost:27017"
        self.dbhandler = MongoDBHandler(mongoDBConnectUri, )
        # verify db connection
        print(self.dbhandler.client.server_info())

        self.available_validators = self.dbhandler.get_available_validators()
        self.filter_validators()
        self.app = FastAPI()
        self.auth_keys = self.dbhandler.get_auth_keys()
        self.private_key = self.load_private_key()
        self.public_key = self.private_key.public_key()
        self.public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        model_list_entry = self.dbhandler.model_config.find_one({"name": "model_list"})
        self.model_list = model_list_entry["data"] if model_list_entry else {}
        self.message = "image-generating-subnet"
        self.signature = base64.b64encode(
            self.private_key.sign(self.message.encode("utf-8"))
        )

        self.loop = asyncio.get_event_loop()

        Instrumentator().instrument(self.app).expose(self.app)
        Thread(target=self.sync_metagraph_periodically, daemon=True).start()
        Thread(target=self.recheck_validators, daemon=True).start()
        
    def sync_db(self):
        new_available_validators = self.dbhandler.get_available_validators()
        for key, value in new_available_validators.items():
            if key not in self.available_validators:
                self.available_validators[key] = value
        self.auth_keys = self.dbhandler.get_auth_keys()

    def filter_validators(self) -> None:
        for hotkey in list(self.available_validators.keys()):
            self.available_validators[hotkey]["is_active"] = False
            if hotkey not in self.metagraph.hotkeys:
                print(f"Removing validator {hotkey}", flush=True)
                self.dbhandler.validators_collection.delete_one({"_id": hotkey})
                self.available_validators.pop(hotkey)

    def load_private_key(self) -> Ed25519PrivateKey:
        # Load private key from MongoDB or generate a new one
        private_key_doc = self.dbhandler.private_key.find_one()
        if private_key_doc:
            return serialization.load_pem_private_key(
                private_key_doc["key"].encode("utf-8"), password=None
            )
        else:
            print("Generating private key", flush=True)
            private_key = Ed25519PrivateKey.generate()
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode("utf-8")
            self.dbhandler.private_key.insert_one({"key": private_key_pem})
            return private_key

    def sync_metagraph_periodically(self) -> None:
        while True:
            print("Syncing metagraph", flush=True)
            self.metagraph.sync(subtensor=self.subtensor, lite=True)
            time.sleep(60 * 10)

    def check_auth(self, key: str) -> None:
        if key not in self.dbhandler.get_auth_keys():
            raise HTTPException(status_code=401, detail="Invalid authorization key")

    async def get_credentials(
        self, request: Request, validator_info: ValidatorInfo
    ) -> Dict:
        client_ip = request.client.host
        uid = validator_info.uid
        hotkey = self.metagraph.hotkeys[uid]
        postfix = validator_info.postfix

        if not postfix:
            raise HTTPException(status_code=404, detail="Invalid postfix")

        new_validator = self.available_validators.setdefault(hotkey, {})
        new_validator.update(
            {
                "generate_endpoint": "http://" + client_ip + postfix,
                "is_active": True,
            }
        )

        print(
            f"Found validator\n- hotkey: {hotkey}, uid: {uid}, endpoint: {new_validator['generate_endpoint']}",
            flush=True,
        )
        self.dbhandler.validators_collection.update_one(
            {"_id": hotkey}, {"$set": new_validator}, upsert=True
        )

        return {
            "message": self.message,
            "signature": self.signature,
        }

    async def check_prompt(self, prompt: str):
        try:
            endpoint = "https://api.midjourneyapi.xyz/mj/v2/validation"
            data = {
                "prompt": prompt,
            }
            async with httpx.AsyncClient(timeout=4) as client:
                response = await client.post(endpoint, json=data)
            response = response.json()
            print(response, flush=True)
            if not response["ErrorMessage"]:
                return True, ""
            else:
                print(response["ErrorMessage"], flush=True)
                return False, response["ErrorMessage"]
        except Exception as e:
            print(e, flush=True)
            return True, ""

    async def generate(self, prompt: Union[Prompt, TextPrompt]):
        if prompt.model_name not in self.model_list:
            raise HTTPException(status_code=404, detail="Model not found")
        if self.auth_keys[prompt.key]["credit"] < self.model_list[prompt.model_name].get("credit_cost", 1):
            raise HTTPException(status_code=403, detail="Run out of credit")
                
        self.sync_db()
        self.check_auth(prompt.key)
        if isinstance(prompt, Prompt):
            is_safe_prompt, reason = await self.check_prompt(prompt.prompt)
            if not is_safe_prompt:
                return HTTPException(
                    status_code=406, detail=f"Prompt checking: {reason}"
                )
            if prompt.pipeline_params.get("use_expansion", False):
                try:
                    async with httpx.AsyncClient(timeout=4) as client:
                        response = await client.post(
                            "http://213.173.102.215:10354/api/prompt_expansion",
                            json={"prompt": prompt.prompt},
                        )
                    if response.status_code == 200:
                        prompt.prompt = response.json()
                except Exception as e:
                    print(e, flush=True)

        validatorItems = self.available_validators.items()
        hotkeys = [
            hotkey
            for hotkey, log in validatorItems
            if log["is_active"]
        ]
        hotkeys = [hotkey for hotkey in hotkeys if hotkey in self.metagraph.hotkeys]
        stakes = [
            self.metagraph.total_stake[self.metagraph.hotkeys.index(hotkey)]
            for hotkey in hotkeys
        ]

        validators = list(zip(hotkeys, stakes))

        request_dict = {
            "payload": dict(prompt),
            "authorization": base64.b64encode(self.public_key_bytes).decode("utf-8"),
        }
        output = None
        while len(validators) and not output:
            stakes = [stake for _, stake in validators]
            validator = random.choices(validators, weights=stakes, k=1)[0]
            hotkey, stake = validator
            validators.remove(validator)
            validator_counter = self.available_validators[hotkey].setdefault(
                "counter", {}
            )
            today_counter = validator_counter.setdefault(
                str(date.today()), {"success": 0, "failure": 0}
            )
            print(f"Selected validator: {hotkey}, stake: {stake}", flush=True)
            try:
                start_time = time.time()
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(connect=2, timeout=64)
                ) as client:
                    response = await client.post(
                        self.available_validators[hotkey]["generate_endpoint"],
                        json=request_dict,
                    )
                end_time = time.time()
                print(
                    f"Received response from validator {hotkey} in {end_time - start_time:.2f} seconds",
                    flush=True,
                )
            except Exception as e:
                print(f"Failed to send request to validator {hotkey}: {e}", flush=True)
                continue
            status_code = response.status_code
            try:
                response = response.json()
            except Exception as e:
                response = {"error": str(e)}

            if status_code == 200:
                print(f"Received response from validator {hotkey}", flush=True)
                output = response

            if output:
                today_counter["success"] += 1
            else:
                today_counter["failure"] += 1
            try:
                self.dbhandler.validators_collection.update_one(
                    {"_id": hotkey}, {"$set": self.available_validators[hotkey]}
                )
                self.auth_keys[prompt.key].setdefault("request_count", 0)
                self.auth_keys[prompt.key]["request_count"] += 1
                
                self.auth_keys[prompt.key]["credit"] -= self.model_list[prompt.model_name].get("credit_cost", 1)
                
                self.dbhandler.auth_keys_collection.update_one(
                    {"_id": prompt.key}, {"$set": self.auth_keys[prompt.key]}
                )
            except Exception as e:
                print(f"Failed to update validator - MongoDB: {e}", flush=True)
        if not output:
            if not len(self.available_validators):
                raise HTTPException(status_code=404, detail="No available validators")
            raise HTTPException(status_code=500, detail="All validators failed")
        return output

    def recheck_validators(self) -> None:
        request_dict = {
            "payload": {"recheck": True},
            "model_name": "proxy-service",
            "authorization": base64.b64encode(self.public_key_bytes).decode("utf-8"),
        }

        def check_validator(hotkey):
            with httpx.Client(timeout=httpx.Timeout(8)) as client:
                try:
                    response = client.post(
                        self.available_validators[hotkey]["generate_endpoint"],
                        json=request_dict,
                    )
                    response.raise_for_status()
                    print(f"Validator {hotkey} responded", flush=True)
                except Exception as e:
                    print(f"Validator {hotkey} failed to respond: {e}", flush=True)
                    # Set is_active to False if validator is not responding
                    self.available_validators[hotkey]["is_active"] = False

        while True:
            print("Rechecking validators", flush=True)
            threads = []
            hotkeys = list(self.available_validators.keys())
            for hotkey in hotkeys:
                thread = Thread(target=check_validator, args=(hotkey,))
                thread.start()
            for thread in threads:
                thread.join()
            print("Total validators:", len(self.available_validators), flush=True)
            # update validators to mongodb
            for hotkey in list(self.available_validators.keys()):
                self.dbhandler.validators_collection.update_one(
                    {"_id": hotkey}, {"$set": self.available_validators[hotkey]}
                )
            time.sleep(60 * 5)

    async def get_validators(self) -> List:
        return list(self.available_validators.keys())

    async def txt2img_api(self, request: Request, data: TextToImage):
        # Get API_KEY from header
        api_key = request.headers.get("API_KEY")
        self.check_auth(api_key)
        prompt = data.prompt
        model_name = data.model_name
        aspect_ratio = data.aspect_ratio
        negative_prompt = data.negative_prompt
        seed = data.seed
        if seed == 0:
            seed = random.randint(0, 1000000)
        advanced_params = data.advanced_params
        ratio_to_size = self.dbhandler.model_config.find_one({"name": "ratio-to-size"})["data"]
        if aspect_ratio not in ratio_to_size:
            raise HTTPException(status_code=400, detail="Aspect ratio not found")
        if model_name not in self.model_list:
            raise HTTPException(status_code=400, detail="Model not found")
        supporting_pipelines = self.model_list[model_name].get("supporting_pipelines", [])
        if "txt2img" not in supporting_pipelines:
            raise HTTPException(
                status_code=400, detail="Model does not support txt2img pipeline"
            )
        default_params = self.model_list[model_name].get("default_params", {})
        width, height = ratio_to_size[aspect_ratio]

        if model_name == ModelName.GO_JOURNEY.value:
            prompt = f"{prompt} --ar {aspect_ratio} --v 6"
            pipeline_type = "gojourney"
        else:
            pipeline_type = "txt2img"
        generate_data = {
            "key": api_key,
            "prompt": prompt,
            "model_name": model_name,
            "pipeline_type": pipeline_type,
            "seed": seed,
            "pipeline_params": {
                "width": width,
                "height": height,
                "negative_prompt": negative_prompt,
                **advanced_params,
            },
        }
        for key, value in default_params.items():
            generate_data["pipeline_params"][key] = value
        output = await self.generate(Prompt(**generate_data))
        if model_name == "DallE":
            image_url = output["response_dict"]["url"]
            image = Image.open(requests.get(image_url, stream=True).raw)
            base64_image = pil_image_to_base64(image)
            output["image"] = base64_image

        return output

    async def img2img_api(self, request: Request, data: ImageToImage):
        # Get API_KEY from header
        api_key = request.headers.get("API_KEY")
        self.check_auth(api_key)
        prompt = data.prompt
        model_name = data.model_name
        negative_prompt = data.negative_prompt
        seed = data.seed
        conditional_image = data.conditional_image

        if seed == 0:
            seed = random.randint(0, 1000000)
        advanced_params = data.advanced_params
        if model_name not in self.model_list:
            raise HTTPException(status_code=404, detail="Model not found")
        supporting_pipelines = self.model_list[model_name].get("supporting_pipelines", [])
        if "img2img" not in supporting_pipelines:
            raise HTTPException(
                status_code=404, detail="Model does not support img2img pipeline"
            )
        default_params = self.model_list[model_name].get("default_params", {})
        conditional_image: Image.Image = self.base64_to_pil_image(conditional_image)
        conditional_image = self.resize_divisible(conditional_image, 1024, 16)
        conditional_image = self.pil_image_to_base64(conditional_image)

        generate_data = {
            "key": api_key,
            "prompt": prompt,
            "model_name": model_name,
            "conditional_image": conditional_image,
            "pipeline_type": "img2img",
            "seed": seed,
            "pipeline_params": {
                "negative_prompt": negative_prompt,
                **advanced_params,
            },
        }

        for key, value in default_params.items():
            generate_data["pipeline_params"][key] = value

        return await self.generate(Prompt(**generate_data))

    async def instantid_api(self, request: Request, data: ImageToImage):
        # Get API_KEY from header
        api_key = request.headers.get("API_KEY")
        self.check_auth(api_key)
        prompt = data.prompt
        model_name = data.model_name
        negative_prompt = data.negative_prompt
        seed = data.seed
        conditional_image = data.conditional_image

        if seed == 0:
            seed = random.randint(0, 1000000)
        advanced_params = data.advanced_params
        if model_name not in self.model_list:
            raise HTTPException(status_code=404, detail="Model not found")
        supporting_pipelines = self.model_list[model_name].get("supporting_pipelines", [])
        if "instantid" not in supporting_pipelines:
            raise HTTPException(
                status_code=404, detail="Model does not support instantid pipeline"
            )
        default_params = self.model_list[model_name].get("default_params", {})

        conditional_image: Image.Image = self.base64_to_pil_image(conditional_image)
        conditional_image = self.resize_divisible(conditional_image, 1024, 16)
        conditional_image = self.pil_image_to_base64(conditional_image)

        generate_data = {
            "key": api_key,
            "prompt": prompt,
            "model_name": model_name,
            "conditional_image": conditional_image,
            "pipeline_type": "instantid",
            "seed": seed,
            "pipeline_params": {
                "negative_prompt": negative_prompt,
                **advanced_params,
            },
        }
        for key, value in default_params.items():
            generate_data["pipeline_params"][key] = value

        return await self.generate(Prompt(**generate_data))

    async def controlnet_api(self, request: Request, data: ImageToImage):
        # Get API_KEY from header
        api_key = request.headers.get("API_KEY")
        self.check_auth(api_key)
        prompt = data.prompt
        model_name = data.model_name
        negative_prompt = data.negative_prompt
        seed = data.seed
        conditional_image = data.conditional_image

        if seed == 0:
            seed = random.randint(0, 1000000)
        advanced_params = data.advanced_params
        model_list = self.dbhandler.model_config.find_one({"name": "model_list"})["data"]
        if model_name not in model_list:
            raise HTTPException(status_code=404, detail="Model not found")
        supporting_pipelines = model_list[model_name].get("supporting_pipelines", [])
        if "controlnet" not in supporting_pipelines:
            raise HTTPException(
                status_code=404, detail="Model does not support controlnet pipeline"
            )
        default_params = model_list[model_name].get("default_params", {})

        conditional_image: Image.Image = self.base64_to_pil_image(conditional_image)
        conditional_image = self.resize_divisible(conditional_image, 1024, 16)
        conditional_image = self.pil_image_to_base64(conditional_image)

        generate_data = {
            "key": api_key,
            "prompt": prompt,
            "model_name": model_name,
            "conditional_image": conditional_image,
            "pipeline_type": "controlnet",
            "seed": seed,
            "pipeline_params": {
                "negative_prompt": negative_prompt,
                **advanced_params,
            },
        }
        for key, value in default_params.items():
            generate_data["pipeline_params"][key] = value

        return await self.generate(Prompt(**generate_data))

    def base64_to_pil_image(self, base64_image):
        image = base64.b64decode(base64_image)
        image = io.BytesIO(image)
        image = Image.open(image)
        return image

    def pil_image_to_base64(self, image: Image.Image, format="JPEG") -> str:
        if format not in ["JPEG", "PNG"]:
            format = "JPEG"
        image_stream = io.BytesIO()
        image.save(image_stream, format=format)
        base64_image = base64.b64encode(image_stream.getvalue()).decode("utf-8")
        return base64_image

    def resize_divisible(self, image, max_size=1024, divisible=16):
        W, H = image.size
        if W > H:
            W, H = max_size, int(max_size * H / W)
        else:
            W, H = int(max_size * W / H), max_size
        W = W - W % divisible
        H = H - H % divisible
        image = image.resize((W, H))
        return image


app = ImageGenerationService()


@app.app.post("/api/v1/txt2img")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def txt2img_api2(request: Request, data: TextToImage):
    return await app.txt2img_api(request, data)

@app.app.post("/get_credentials")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def get_credentials(request: Request, validator_info: ValidatorInfo):
    return await app.get_credentials(request, validator_info)

@app.app.post("/generate")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def generate(request: Request, prompt: Union[Prompt, TextPrompt]):
    return await app.generate(prompt)

@app.app.get("/get_validators")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def get_validators(request: Request):
    return await app.get_validators(request)

@app.app.post("/api/v1/img2img")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def img2img_api(request: Request, data: ImageToImage):
    return await app.img2img_api(request, data)

@app.app.post("/api/v1/instantid")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def instantid_api(request: Request, data: ImageToImage):
    return await app.instantid_api(request, data)

@app.app.post("/api/v1/controlnet")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def controlnet_api(request: Request, data: ImageToImage):
    return await app.controlnet_api(request, data)