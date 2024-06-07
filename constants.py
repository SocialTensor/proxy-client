from enum import Enum

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