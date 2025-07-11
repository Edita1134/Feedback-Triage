"""
Database models for feedback history storage
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class FeedbackHistory(Base):
    __tablename__ = "feedback_history"
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_text = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    urgency_score = Column(Integer, nullable=False)
    confidence_score = Column(Float, nullable=True)
    processing_time = Column(Float, nullable=True)  # in seconds
    llm_provider = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_ip = Column(String(45), nullable=True)  # For basic tracking
    
    def to_dict(self):
        return {
            "id": self.id,
            "feedback_text": self.feedback_text,
            "category": self.category,
            "urgency_score": self.urgency_score,
            "confidence_score": self.confidence_score,
            "processing_time": self.processing_time,
            "llm_provider": self.llm_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_ip": self.user_ip
        }

# Database configuration with SQLite fallback
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./feedback_triage.db")

# Create engine with appropriate configuration
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)
