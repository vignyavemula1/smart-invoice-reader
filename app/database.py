"""Database setup with SQLAlchemy (works with SQLite by default, or MySQL)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import config

# check_same_thread is only needed for SQLite with FastAPI
connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: opens a database session per request and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()