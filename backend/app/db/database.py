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
    """Tiny migration: add columns introduced after a table was first created,
    so existing data is kept. (New tables are created by create_all.)"""
    insp = inspect(engine)
    tables = insp.get_table_names()
    statements = []

    if "alerts" in tables:
        cols = {c["name"] for c in insp.get_columns("alerts")}
        if "alert_type" not in cols:
            statements.append(
                "ALTER TABLE alerts ADD COLUMN alert_type VARCHAR DEFAULT 'general'"
            )
        if "params" not in cols:
            statements.append("ALTER TABLE alerts ADD COLUMN params TEXT")

    if "users" in tables:
        cols = {c["name"] for c in insp.get_columns("users")}
        if "preferred_language" not in cols:
            statements.append(
                "ALTER TABLE users ADD COLUMN preferred_language VARCHAR NOT NULL DEFAULT 'en'"
            )

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))