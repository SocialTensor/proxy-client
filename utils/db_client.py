from constants import DB_NAME, CollectionName
from bson.json_util import dumps
from typing import Dict
from threading import Thread
import time

from utils.db_base import DBBase
from utils.db_schemas import AuthKeySchema, ValidatorSchema

class MongoDBHandler(DBBase):
  def __init__(self, mongoDBConnectUri: str, dbname = DB_NAME) -> None:
    super().__init__(mongoDBConnectUri)
    if dbname not in self.client.list_database_names():
      print("Creating database", flush=True)
      self.client[dbname].create_collection(CollectionName.VALIDATORS.value)
      self.client[dbname].create_collection(CollectionName.AUTH_KEYS.value)
      self.client[dbname].create_collection(CollectionName.PRIVATE_KEY.value)
      self.client[dbname].create_collection(CollectionName.MODEL_CONFIG.value)

    self.db = self.client[dbname]
    self.validators_collection = self.db[CollectionName.VALIDATORS.value]
    self.auth_keys_collection = self.db[CollectionName.AUTH_KEYS.value]
    self.model_config = self.db[CollectionName.MODEL_CONFIG.value]
    self.private_key = self.db[CollectionName.PRIVATE_KEY.value]
    
    Thread(target=self.update_model_config, daemon=True).start()
    
  def update_model_config(self):
      while True:
        time.sleep(60 * 10)
        # Fetch new data from MongoDB and update self.model_config
        self.model_config = self.db[CollectionName.MODEL_CONFIG.value]
            
  def get_available_validators(self) -> Dict[str, ValidatorSchema]:
    return {doc["_id"]: doc for doc in self.validators_collection.find()}

  def get_auth_keys(self) -> Dict[str, AuthKeySchema]:
    return {doc["_id"]: doc for doc in self.auth_keys_collection.find()}

