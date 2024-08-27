from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List
from hashlib import sha256
from uuid import uuid4

app = FastAPI()

# Databases (in-memory for simplicity)
users: Dict[str, str] = {}
sessions: Dict[str, str] = {}
active_referrals: Dict[str, List[str]] = {}
balance_of_user: Dict[str, float] = {}
referral_score_for_user: Dict[str, int] = {}

# Models
class UserAuth(BaseModel):
    username: str
    password: str

class Referral(BaseModel):
    referral_code: str

class WithdrawRequest(BaseModel):
    amount: float

# Helper Functions
def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()

def create_session_id(username: str, hashed_password: str) -> str:
    session_id = str(uuid4())
    sessions[f"{hashed_password}{username}"] = session_id
    return session_id

def get_session_id(username: str, hashed_password: str) -> str:
    return sessions.get(f"{hashed_password}{username}")

# Endpoints
@app.post("/register/")
def register(user: UserAuth):
    if user.username in users:
        raise HTTPException(status_code=400, detail="Username already exists.")
    
    hashed_password = hash_password(user.password)
    users[user.username] = hashed_password
    session_id = create_session_id(user.username, hashed_password)
    active_referrals[session_id] = []
    balance_of_user[session_id] = 0.0
    referral_score_for_user[session_id] = 0
    return {"session_id": session_id}

@app.post("/auth/")
def auth(user: UserAuth):
    hashed_password = hash_password(user.password)
    
    if user.username not in users:
        raise HTTPException(status_code=400, detail="User not found. Please register first.")
    
    if users[user.username] == hashed_password:
        session_id = get_session_id(user.username, hashed_password)
        if session_id:
            return {"session_id": session_id}
        else:
            session_id = create_session_id(user.username, hashed_password)
            return {"session_id": session_id}
    
    else:
        raise HTTPException(status_code=400, detail="Incorrect login.")

@app.post("/add-referral/")
def add_referral(session_id: str, referral: Referral):
    if session_id in active_referrals:
        active_referrals[session_id].append(referral.referral_code)
        return {"message": "Referral code added."}
    else:
        raise HTTPException(status_code=400, detail="Invalid session ID.")

@app.post("/redeem-referral/")
def redeem_referral(session_id: str, referral: Referral):
    for sid, referrals in active_referrals.items():
        if referral.referral_code in referrals:
            referrals.remove(referral.referral_code)
            referral_score_for_user[session_id] += 1
            return {"message": "Referral code redeemed."}
    
    raise HTTPException(status_code=400, detail="Referral code not found.")

@app.post("/withdraw/")
def withdraw(session_id: str, request: WithdrawRequest):
    if session_id in balance_of_user:
        if balance_of_user[session_id] >= request.amount:
            balance_of_user[session_id] -= request.amount
            return {"new_balance": balance_of_user[session_id]}
        else:
            raise HTTPException(status_code=400, detail="Insufficient balance.")
    else:
        raise HTTPException(status_code=400, detail="Invalid session ID.")

@app.post("/convert-referral-to-money/")
def convert_referral_to_money(session_id: str):
    if session_id in balance_of_user and session_id in referral_score_for_user:
        referral_amount = referral_score_for_user[session_id] * 100
        balance_of_user[session_id] += referral_amount
        referral_score_for_user[session_id] = 0
        return {"new_balance": balance_of_user[session_id]}
    else:
        raise HTTPException(status_code=400, detail="Invalid session ID or no referral score.")

# To run the application, use the command: `uvicorn filename:app --reload`
