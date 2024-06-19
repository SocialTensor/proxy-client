from pymongo import MongoClient
from typing import Dict

class DBBase:
  def __init__(self, mongoDBConnectUri: str) -> None:
    self.client = MongoClient(mongoDBConnectUri)

  def get_collection(self, collection_name: str):
    return self.db[collection_name]

  def insert_one(self, collection_name: str, document: Dict):
    collection = self.get_collection(collection_name)
    return collection.insert_one(document)

  def update_one(self, collection_name: str, query: Dict, new_values: Dict):
    collection = self.get_collection(collection_name)
    return collection.update_one(query, {"$set": new_values})

  def find(self, collection_name: str, query: Dict):
    collection = self.get_collection(collection_name)
    return collection.find(query)
  
  def delete_one(self, collection_name: str, query: Dict):
    collection = self.get_collection(collection_name)
    return collection.delete_one(query)