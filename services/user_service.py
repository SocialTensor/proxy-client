import uuid
from fastapi import HTTPException, Request
from utils.common import check_password, hash_password
from utils.data_types import ChangePasswordDataType, EmailDataType, UserSigninInfo, APIKey
from constants import LOGS_ACTION
from datetime import datetime
from bson import ObjectId

class UserService:
    def __init__(self, dbhandler):
        self.dbhandler = dbhandler
        self.auth_keys = self.dbhandler.get_auth_keys()

    def signin(self, request: Request, data: UserSigninInfo):
        userInfo = self.dbhandler.auth_keys_collection.find_one({"email": data.email})
        if userInfo:
            if check_password(data.password, userInfo["password"]):
                userInfo["_id"] = str(userInfo["_id"])
                userInfo.pop("password", None)
                self.log_user_activity(userInfo["_id"], LOGS_ACTION.SIGNIN.value, "User logged in", 200, "", 0)
                return userInfo
            else:
                self.log_user_activity(userInfo["_id"], LOGS_ACTION.SIGNIN.value, "Tried to log in with incorrect password", 400, "", 0)
                raise HTTPException(
                    status_code=400, detail="User credentials are incorrect!"
                )
        else:
            raise HTTPException(status_code=400, detail="User does not exist!")

    def signup(self, request: Request, data: UserSigninInfo):
        userInfo = self.dbhandler.auth_keys_collection.find_one({"email": data.email})
        if userInfo:
            raise HTTPException(
                status_code=400, detail="User with the same email already exists!"
            )

        user_id = str(uuid.uuid4())
        userInfo = self.dbhandler.auth_keys_collection.insert_one(
            {
                "_id": user_id,
                "email": data.email,
                "request_count": 0,
                "password": hash_password(data.password),
                "credit": 5,
                "created_date": datetime.utcnow(),
                "api_keys": [{"key": str(uuid.uuid4()), "created": datetime.utcnow()}],
                "usage": [],
                "balance_history": []
            }
        )
        created_user = self.dbhandler.auth_keys_collection.find_one(
            {"_id": user_id}, {"password": 0}
        )
        if created_user:
            created_user["_id"] = str(created_user["_id"])
            self.log_user_activity(created_user["_id"], LOGS_ACTION.SIGNUP.value, "Registered", 200, "", 0)
        return created_user

    def reset_password(self, request: Request, data: EmailDataType):
        userInfo = self.dbhandler.auth_keys_collection.find_one({"email": data.email})
        new_password = str(uuid.uuid4())
        if userInfo:
            self.dbhandler.auth_keys_collection.update_one({"email": data.email}, {"$set": {"password": hash_password(new_password)}})
            return {"message": "Password reset successfully"}
        else:
            raise HTTPException(status_code=400, detail="User does not exist!")

    def change_password(self, request: Request, data: ChangePasswordDataType):
        userInfo = self.dbhandler.auth_keys_collection.find_one({"email": data.email})
        if userInfo:
            if check_password(data.oldPassword, userInfo["password"]):
                self.dbhandler.auth_keys_collection.update_one({"email": data.email}, {"$set": {"password": hash_password(data.newPassword)}})
                self.auth_keys = self.dbhandler.get_auth_keys()
                api_key = request.headers.get("API_KEY")
                user_info = self.auth_keys[api_key]
                if user_info:
                    user_info.pop("password", None)
                    user_info.pop("temp_id", None)
                    self.log_user_activity(api_key, LOGS_ACTION.CHANGE_PASSWORD.value, "Password changed", 200, "", 0)
                    return {"message": "Password changed successfully", "user": user_info}
            else:
                raise HTTPException(status_code=400, detail="Old password is incorrect!")
        else:
            raise HTTPException(status_code=400, detail="User does not exist!")

    def get_user_info(self, request: Request):
        try:
            api_key = request.headers.get("API_KEY")
            self.auth_keys = self.dbhandler.get_auth_keys()
            user_info = self.auth_keys[api_key]
            if user_info:
                user_info.pop("password", None)
                user_info.pop("temp_id", None)
                return {
                    k: str(v) if isinstance(v, ObjectId) else v
                    for k, v in user_info.items()
                }
            else:
                raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="An error occurred while fetching user data"
            )

    def add_api_key(self, request: Request):
        try:
            api_key = request.headers.get("API_KEY")
            self.auth_keys = self.dbhandler.get_auth_keys()
            key_id = self.auth_keys[api_key]["temp_id"]
            new_api_key = {"key": str(uuid.uuid4()), "created": datetime.utcnow()}
            self.dbhandler.auth_keys_collection.update_one(
                {"_id": key_id}, {"$push": {"api_keys": new_api_key}}
            )
            self.auth_keys = self.dbhandler.get_auth_keys()
            user_info = self.auth_keys[api_key]
            if user_info:
                user_info.pop("password", None)
                self.log_user_activity(api_key, LOGS_ACTION.CREATE_API_KEY.value, "Added a new API key", 200, "", 0)
                return {
                    k: str(v) if isinstance(v, ObjectId) else v
                    for k, v in user_info.items()
                }
            else:
                self.log_user_activity(api_key, LOGS_ACTION.CREATE_API_KEY.value, "API key invalid", 404, "", 0)
                raise HTTPException(status_code=404, detail="API key invalid")
        except Exception as e:
            self.log_user_activity(api_key, LOGS_ACTION.CREATE_API_KEY.value, str(e), 500, "", 0)
            raise HTTPException(
                status_code=500, detail="An error occurred while adding api key"
            )

    def delete_api_key(self, request: Request, api_key_data: str):
        try:
            api_key = request.headers.get("API_KEY")
            self.auth_keys = self.dbhandler.get_auth_keys()
            key_id = self.auth_keys[api_key]["temp_id"]
            result = self.dbhandler.auth_keys_collection.update_one(
                {"_id": key_id}, {"$pull": {"api_keys": {"key": api_key_data}}}
            )
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=404, detail="API key not found or no modification made"
                )
            self.auth_keys = self.dbhandler.get_auth_keys()
            user_info = self.auth_keys[api_key]
            if user_info:
                user_info.pop("password", None)
                self.log_user_activity(api_key, LOGS_ACTION.DELETE_API_KEY.value, "Deleted API key", 200, "", 0)
                return {
                    k: str(v) if isinstance(v, ObjectId) else v
                    for k, v in user_info.items()
                }
            else:
                self.log_user_activity(api_key, LOGS_ACTION.DELETE_API_KEY.value, "User not found", 404, "", 0)
                raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            self.log_user_activity(api_key, LOGS_ACTION.DELETE_API_KEY.value, str(e), 500, "", 0)
            raise HTTPException(
                status_code=500, detail="An error occurred while deleting api key"
            )

    def get_logs(self, request: Request):
        try:
            api_key = request.headers.get("API_KEY")
            self.auth_keys = self.dbhandler.get_auth_keys()
            userInfo = self.auth_keys[api_key]
            keys = [api_key] + [key["key"] for key in userInfo["api_keys"]]
            logs = self.dbhandler.logs_collection.find({"api_key": {"$in": keys}})
            logs_list = list(logs)
            return [{**log, "_id": str(log["_id"])} for log in logs_list]
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="An error occurred while getting logs"
            )

    def log_user_activity(self, api_key, action, details, status, model, cost):
        self.dbhandler.logs_collection.insert_one(
            {
                "action": action,
                "details": details,
                "api_key": api_key,
                "status": status,
                "model": model,
                "cost": cost,
                "timestamp": datetime.utcnow(),
            }
        )
    def add_balance(self, email, amount):
        userInfo = self.dbhandler.auth_keys_collection.find_one({"email": email})
        if userInfo:
            # Update the credit
            new_credit = userInfo.get("credit", 0) + amount
            self.dbhandler.auth_keys_collection.update_one(
                {"email": email},
                {"$set": {"credit": new_credit}}
            )

            # Prepare balance history entry
            balance_entry = {
                "amount": amount,
                "timestamp": datetime.utcnow()
            }

            # Update balance_history
            if "balance_history" not in userInfo:
                self.dbhandler.auth_keys_collection.update_one(
                    {"email": email},
                    {"$set": {"balance_history": [balance_entry]}}
                )
            else:
                self.dbhandler.auth_keys_collection.update_one(
                    {"email": email},
                    {"$push": {"balance_history": balance_entry}}
                )

            # Log the balance addition
            self.log_user_activity(userInfo["_id"], LOGS_ACTION.ADD_BALANCE.value, f"Added balance: {amount}", 200, "", 0)
        else:
            raise HTTPException(status_code=400, detail="User does not exist!")

    async def handle_webhooks(self, request: Request):
        try:
            json_data = await request.json()

            # Check if the event type is charge.succeeded
            if json_data.get("type") == "charge.succeeded":
                email = json_data.get("data", {}).get("object", {}).get("billing_details", {}).get("email")
                amount = json_data.get("data", {}).get("object", {}).get("amount")
                self.add_balance(email, amount / 100)
                print(f"Charge succeeded event received. Email: {email}, Amount: {amount}")
                return {"message": "charge succeeded"}
            else:
                return {"message": "Stripe webhook called"}
        
        except Exception as e:
            print(f"Error processing webhook: {e}", flush=True)
            raise HTTPException(status_code=400, detail="Invalid webhook data")