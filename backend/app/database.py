# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Retrieve database URL from environment variables with a sensible fallback for local development
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/mockwright"
)

# Initialize SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create configured "SessionLocal" class
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# Base class for declarative models
Base = declarative_base()

def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy database session,
    ensuring it is properly closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()