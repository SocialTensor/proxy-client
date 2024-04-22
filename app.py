import argparse
import asyncio
import base64
import io
import json
import os
import random
from datetime import date
from typing import Dict, List, Optional, Tuple
import time
import bittensor as bt
import httpx
import numpy as np
import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException, Request
from PIL import Image
from pydantic import BaseModel
from tqdm import tqdm
from starlette.concurrency import run_in_threadpool
from threading import Thread


class Prompt(BaseModel):
    key: str
    prompt: str
    model_name: str
    pipeline_type: str = "txt2img"
    conditional_image: str = ""
    seed: int = -1
    miner_uid: int = -1
    pipeline_params: dict = {}


class ValidatorInfo(BaseModel):
    postfix: str
    uid: int
    all_uid_info: dict = {}
    sha: str = ""


class ImageGenerationService:
    def __init__(self, args):
        self.args = args
        self.subtensor = bt.subtensor("test")
        self.metagraph = self.subtensor.metagraph(119)
        self.available_validators: Dict[str, Dict] = self.load_json(
            "validator_logs.json", {}
        )
        self.filter_validators()
        self.app = FastAPI()
        self.auth_keys: Dict[str, Dict] = self.load_json("auth_keys.json", {})
        self.private_key = self.load_private_key()
        self.public_key = self.private_key.public_key()
        self.public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        self.message = "image-generating-subnet"
        self.signature = base64.b64encode(
            self.private_key.sign(self.message.encode("utf-8"))
        )

        self.loop = asyncio.get_event_loop()

        self.app.add_api_route(
            "/get_credentials", self.get_credentials, methods=["POST"]
        )
        self.app.add_api_route("/generate", self.generate, methods=["POST"])
        Thread(target=self.sync_metagraph_periodically, daemon=True).start()
        Thread(target=self.recheck_validators, daemon=True).start()

    def filter_validators(self) -> None:
        for hotkey in list(self.available_validators.keys()):
            self.available_validators[hotkey]["is_active"] = False
            if hotkey not in self.metagraph.hotkeys:
                print(f"Removing validator {hotkey}", flush=True)
                self.available_validators.pop(hotkey)

    def load_json(self, filename: str, default: Dict) -> Dict:
        filepath = os.path.join(self.args.save_log_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
        return default

    def save_json(self, data: Dict, filename: str) -> None:
        filepath = os.path.join(self.args.save_log_dir, filename)
        with open(filepath, "w") as f:
            json.dump(data, f)

    def load_private_key(self) -> Ed25519PrivateKey:
        filepath = os.path.join(self.args.save_log_dir, "private_key.pem")
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return serialization.load_pem_private_key(f.read(), password=None)
        else:
            print("Generating private key", flush=True)
            private_key = Ed25519PrivateKey.generate()
            with open(filepath, "wb") as f:
                f.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )
            return private_key

    def sync_metagraph_periodically(self) -> None:
        while True:
            print("Syncing metagraph", flush=True)
            self.metagraph.sync(subtensor=self.subtensor, lite=True)
            time.sleep(60 * 5)

    def check_auth(self, key: str) -> None:
        if key not in self.auth_keys:
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
        self.save_json(self.available_validators, "validator_logs.json")

        return {
            "message": self.message,
            "signature": self.signature,
        }

    async def generate(self, prompt: Prompt) -> Dict:
        self.check_auth(prompt.key)

        hotkeys = [
            hotkey
            for hotkey, log in self.available_validators.items()
            if log["is_active"]
        ]
        stakes = [
            self.metagraph.total_stake[self.metagraph.hotkeys.index(hotkey)].item() + 1
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
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=2, timeout=64)
            ) as client:
                response = await client.post(
                    self.available_validators[hotkey]["generate_endpoint"],
                    json=request_dict,
                )
            status_code = response.status_code
            response = response.json()

            if status_code != 200:
                today_counter["failure"] += 1
            else:
                output = response
                today_counter["success"] += 1

            self.save_json(self.available_validators, "validator_logs.json")
            self.auth_keys[prompt.key].setdefault("request_count", 0)
            self.auth_keys[prompt.key]["request_count"] += 1
            self.save_json(self.auth_keys, "auth_keys.json")
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
            time.sleep(60 * 5)

    def run(self) -> None:
        uvicorn.run(self.app, host="0.0.0.0", port=self.args.port)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=10003)
    parser.add_argument("--save_log_dir", type=str, default="./")
    args, _ = parser.parse_known_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    service = ImageGenerationService(args)
    service.run()
