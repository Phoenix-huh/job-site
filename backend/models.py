from sqlalchemy import Column, Integer, String, Text, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    company = Column(String, index=True)
    email = Column(String, nullable=True)
    url = Column(String, unique=True, index=True, nullable=True)
    description = Column(Text)
    role = Column(String, index=True, nullable=True)  # e.g. "Data Analyst", "Software Engineer"
    location = Column(String, index=True, nullable=True)  # e.g. "Mumbai", "Remote", "Bangalore"
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

    score = relationship("Score", back_populates="job", uselist=False)

class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    final_score = Column(Float)
    trust_tier = Column(Integer)  # 1, 2, or 3
    flags = Column(JSON)          # List of strings (e.g. "CRIT: Request upfront fee")
    raw_threats = Column(JSON)    # Detailed json breakdown
    
    job = relationship("Job", back_populates="score")
