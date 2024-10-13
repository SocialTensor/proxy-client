from enum import Enum

# UPDATE THIS WITH THE REQUIREMENT
API_RATE_LIMIT = "120/minute" # 120 requests per minute for the API. 
PRO_API_RATE_LIMIT = "1000/minute"

DB_NAME = "image_generation_service"

MODEL_CLASSIFICATION_URL = "https://superensembleclassifier-production.up.railway.app/classify"


STYLE_TO_MODEL_MAPPING = {
    "general": "OpenGeneral",
    "digital art": "OpenDigitalArt",
}

# Create enum for the models
class ModelName(Enum):
  JUGGERNAUT_XL = "JuggernautXL"
  ANIME_V3 = "AnimeV3"
  REALITIES_EDGE_XL = "RealitiesEdgeXL"
  DREAM_SHAPER_XL = "DreamShaperXL"
  GO_JOURNEY = "GoJourney"
  STICKER_MAKER = "StickerMaker"
  FACE_TO_MANY = "FaceToMany"

class CollectionName(Enum):
  VALIDATORS = "validators"
  AUTH_KEYS = "auth_keys"
  MODEL_CONFIG = "model_config"
  PRIVATE_KEY = "private_key"
  LOGS = "logs"
  
class LOGS_ACTION(Enum):
  SIGNUP = "User Sign Up"
  SIGNIN = "User Sign In"
  CHANGE_PASSWORD = "Change Password"
  APICALL = "API call"
  CREATE_API_KEY = "Create API key"
  DELETE_API_KEY = "Delete API key"