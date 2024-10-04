from pydantic import BaseModel

class Prompt(BaseModel):
    key: str
    prompt: str
    model_name: str
    pipeline_type: str = "txt2img"
    conditional_image: str = ""
    seed: int = -1
    miner_uid: int = -1
    pipeline_params: dict = {}


class TextPrompt(BaseModel):
    key: str = ""
    prompt_input: str = ""
    model_name: str = ""
    pipeline_params: dict = {}
    seed: int = 0


class TextToImage(BaseModel):
    prompt: str
    model_name: str
    aspect_ratio: str = "1:1"
    negative_prompt: str = ""
    seed: int = 0
    advanced_params: dict = {}


class ImageToImage(BaseModel):
    prompt: str
    model_name: str
    conditional_image: str
    negative_prompt: str = ""
    seed: int = 0
    advanced_params: dict = {}


class ValidatorInfo(BaseModel):
    postfix: str
    uid: int
    all_uid_info: dict = {}
    sha: str = ""

class UserSigninInfo(BaseModel):
    email: str
    password: str

class ChatCompletion(BaseModel):
    model: str
    messages: list[dict]
    temperature: float = 1
    top_p: float = 1
    max_tokens: int = 128
    
class APIKey(BaseModel):
    key: str

class StripePay(BaseModel):
    price: int