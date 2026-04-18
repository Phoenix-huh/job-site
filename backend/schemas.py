from pydantic import BaseModel
from typing import List, Optional, Dict, Any

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
