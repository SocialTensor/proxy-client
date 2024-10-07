import os
from typing import Union
from fastapi import HTTPException, Depends, Request
from constants import API_RATE_LIMIT
from slowapi import Limiter
from slowapi.util import get_remote_address
from services.image_generation_service import ImageGenerationService
from services.user_service import UserService
from services.stripe_service import StripeService
from utils.data_types import APIKey, ChangePasswordDataType, EmailDataType, Prompt, TextPrompt, TextToImage, ImageToImage, UserSigninInfo, ValidatorInfo, ChatCompletion, StripePay
from utils.db_client import MongoDBHandler
from dotenv import load_dotenv

load_dotenv()
def get_api_key(request: Request):
    return request.headers.get("API_KEY", get_remote_address(request))

limiter = Limiter(key_func=get_api_key)
def dynamic_rate_limit(request: Request):  # Add request parameter
    # check if the user's role is pro or standard
    # user_role = request.headers.get("User-Role", "default")  # Example header
    # if user_role == "pro":
    #     return PRO_API_RATE_LIMIT  # Premium users get a higher limit
    # else:
    return API_RATE_LIMIT  # Default limit for regular users

MONGOUSER = os.getenv("MONGOUSER")
MONGOPASSWORD = os.getenv("MONGOPASSWORD")
MONGOHOST = os.getenv("MONGOHOST", "localhost")
MONGOPORT = os.getenv("MONGOPORT", 27017)

# mongoDBConnectUri = f"mongodb://localhost:27017"
mongoDBConnectUri = f"mongodb://{MONGOUSER}:{MONGOPASSWORD}@{MONGOHOST}:{MONGOPORT}"
print(mongoDBConnectUri)
dbhandler = MongoDBHandler(mongoDBConnectUri, )
# verify db connection
print(dbhandler.client.server_info())

# Initialize AuthService with the dbhandler
user_service = UserService(dbhandler)  

app = ImageGenerationService(dbhandler, user_service)

async def api_key_checker(request: Request = None):
    client_host = request.client.host
    print(client_host, flush=True)
    try:
        json_data = await request.json()
    except Exception as e:
        print(e, flush=True)
        json_data = {}
    api_key = request.headers.get("API_KEY") or json_data.get("key") or request.headers.get("Authorization").replace("Bearer ", "")
    if not api_key or api_key not in app.dbhandler.get_auth_keys():
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

admin_keys = ["82aa2404-5774-468a-98f7-694f33f965c6", "66fad9cbdf55d190f6d8693f"]
async def is_admin(request: Request):
    api_key = request.headers.get("API_KEY")
    if not api_key or api_key not in admin_keys:
        raise HTTPException(status_code=403, detail="Not an admin")

@app.app.post("/api/v1/txt2img", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def txt2img_api2(request: Request, data: TextToImage):
    return await app.txt2img_api(request, data)

@app.app.post("/get_credentials")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def get_credentials(request: Request, validator_info: ValidatorInfo):
    return await app.get_credentials(request, validator_info)

@app.app.post("/generate", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def generate(request: Request, prompt: Union[Prompt, TextPrompt]):
    return await app.generate(prompt)

@app.app.get("/get_validators", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def get_validators(request: Request):
    return await app.get_validators(request)

@app.app.post("/api/v1/img2img", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def img2img_api(request: Request, data: ImageToImage):
    return await app.img2img_api(request, data)

@app.app.post("/api/v1/instantid", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def instantid_api(request: Request, data: ImageToImage):
    return await app.instantid_api(request, data)

@app.app.post("/api/v1/controlnet", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def controlnet_api(request: Request, data: ImageToImage):
    return await app.controlnet_api(request, data)

@app.app.post("/api/v1/upscale", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def upscale_api(request: Request, data: ImageToImage):
    return await app.upscale_api(request, data)

@app.app.post("/api/v1/chat/completions", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def chat_completions_api(request: Request, data: ChatCompletion):
    return await app.chat_completions(request, data)

@app.app.post("/api/v1/signin")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
def signin(request: Request, data: UserSigninInfo):
    user = user_service.signin(request, data)
    return {"message": "User signed in successfully", "user": user}

@app.app.post("/api/v1/signup")
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
def signup(request: Request, data: UserSigninInfo):
    insert_result = user_service.signup(request, data)
    if insert_result:
        return {"message": "User created successfully", "user": insert_result}
    else:
        raise HTTPException(status_code=500, detail="Failed to create user")

@app.app.get("/api/v1/get_user_info", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
async def get_user_info(request: Request):
    userInfo = user_service.get_user_info(request)
    if userInfo:
        return {"message": "User data fetched successfully", "user": userInfo}
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch user data")

@app.app.get("/api/v1/add_api_key", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
def add_api_key(request: Request):
    apiKey = user_service.add_api_key(request)
    if apiKey:
        return {"message": "New api key generated", "user": apiKey}
    else:
        raise HTTPException(status_code=500, detail="Failed to add API key")

@app.app.post("/api/v1/delete_api_key", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
def delete_api_key(request: Request, data: APIKey):
    apiKey = user_service.delete_api_key(request, data.key)
    if apiKey:
        return {"message": "API key deleted", "user": apiKey}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete API key")
    
@app.app.get("/api/v1/get_logs", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
def get_logs(request: Request):
    logs = user_service.get_logs(request)
    if logs:
        return {"message": "Retrieved Logs", "logs": logs}
    else:
        raise HTTPException(status_code=500, detail="Failed to get logs")

@app.app.post("/api/v1/reset_password", dependencies=[Depends(is_admin)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
def reset_password(request: Request, data: EmailDataType):
    return user_service.reset_password(request, data)

@app.app.post("/api/v1/change_password", dependencies=[Depends(api_key_checker)])
@limiter.limit(API_RATE_LIMIT) # Update the rate limit
def change_password(request: Request, data: ChangePasswordDataType):
    return user_service.change_password(request, data)

@app.app.post("/api/v1/create-payment-intent")
async def create_payment_intent(data: StripePay):
    return await StripeService.create_payment_intent(data)