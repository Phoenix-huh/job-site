from sqlalchemy import Column, Integer, String, Text, Float, JSON, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    company = Column(String, index=True)
    email = Column(String, nullable=True)
    url = Column(String, unique=True, index=True, nullable=True)
    description = Column(Text)
    role = Column(String, index=True, nullable=True)
    location = Column(String, index=True, nullable=True)
    country = Column(String, index=True, nullable=True)
    platform = Column(String, index=True, nullable=True)
    job_type = Column(String, index=True, nullable=True)
    workplace_type = Column(String, index=True, nullable=True)
    posted_date = Column(Date, nullable=True)
    salary = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

    score = relationship("Score", back_populates="job", uselist=False)

class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    final_score = Column(Float)
    trust_tier = Column(Integer)
    flags = Column(JSON)
    raw_threats = Column(JSON)
    
    job = relationship("Job", back_populates="score")

class UserJobInteraction(Base):
    __tablename__ = "user_job_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True, nullable=False)
    applied = Column(Boolean, default=False)
    rejected = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
