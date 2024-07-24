from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple, Union

class AuthKeySchema(BaseModel):
  _id: str
  request_count: int
  credit: int
  
class ValidatorCounterSchema(BaseModel):
  success: int
  failure: int

class ValidatorSchema(BaseModel):
  _id: str
  generate_endpoint: str
  is_active: bool
  counter: Dict[str, ValidatorCounterSchema]

class ID(BaseModel):
  oid: str = Field(alias='$oid')

class ModelDefaultParams(BaseModel):
  num_inference_steps: Optional[int]
  clip_skip: Optional[int]
  guidance_scale: Optional[int]

class ModelData(BaseModel):
  supporting_pipelines: List[str]
  default_params: Optional[ModelDefaultParams]
  credit_cost: float

class Resolution(BaseModel):
  values: Tuple[int, int]
    
class ModelConfigSchema(BaseModel):
  _id: ID
  name: str
  data: Dict[str, Union[ModelData, Resolution]]

class PrivateKeySchema(BaseModel):
  _id: ID
  key: str