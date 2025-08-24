from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()

class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    original_solution = Column(Text, nullable=False)  # JSON string
    user_rating = Column(Integer, nullable=False)  # 1-5 scale
    user_comment = Column(Text, nullable=True)
    corrected_answer = Column(String(500), nullable=True)
    corrected_steps = Column(Text, nullable=True)  # JSON string
    is_helpful = Column(Boolean, default=True)
    route_used = Column(String(50), nullable=False)  # kb/web_search
    confidence_score = Column(Float, nullable=False)
    topic = Column(String(100), nullable=True)
    difficulty = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # New fields for educational tracking
    educational_quality_rating = Column(Integer, nullable=True)  # 1-5 scale for step quality
    step_clarity_feedback = Column(Text, nullable=True)
    
class LearningMetrics(Base):
    __tablename__ = "learning_metrics"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow)
    avg_rating = Column(Float, nullable=False)
    total_feedback_count = Column(Integer, nullable=False)
    kb_accuracy = Column(Float, nullable=False)
    web_accuracy = Column(Float, nullable=False)
    prompt_version = Column(String(50), nullable=True)  # For DSPy tracking
    
    # New educational metrics
    avg_educational_quality = Column(Float, nullable=True)
    professor_mode_usage = Column(Integer, default=0)
    step_clarity_score = Column(Float, nullable=True)

# Database setup
DATABASE_URL = "sqlite:///feedback.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_database():
    """Initialize feedback database with educational enhancements"""
    Base.metadata.create_all(bind=engine)
    print("✅ Enhanced feedback database initialized with educational tracking")
