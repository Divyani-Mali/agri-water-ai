from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    """Tiny migration: add columns introduced after the table was first created."""
    insp = inspect(engine)
    if "alerts" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("alerts")]
        if "alert_type" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE alerts ADD COLUMN alert_type VARCHAR DEFAULT 'general'")
                )