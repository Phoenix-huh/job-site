from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True

class ScoreBase(BaseModel):
    final_score: float
    trust_tier: int
    flags: List[str]
    raw_threats: List[Dict[str, Any]]

class ScoreOut(ScoreBase):
    id: int
    job_id: int

    class Config:
        from_attributes = True

class JobBase(BaseModel):
    title: str
    company: str
    email: Optional[str] = None
    url: Optional[str] = None
    description: str
    role: Optional[str] = None
    location: Optional[str] = None

class JobCreate(JobBase):
    pass

class JobOut(JobBase):
    id: int
    created_at: str
    score: Optional[ScoreOut] = None

    class Config:
        from_attributes = True
