import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure environment variables are loaded
_backend_env = Path(__file__).resolve().parent.parent / ".env"
_root_env = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_backend_env)
load_dotenv(dotenv_path=_root_env)
load_dotenv()

def _sanitize_db_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    
    # Handle unencoded special characters in password (e.g. '@' in 'intervyn@ai123')
    if "://" in url and "@" in url:
        prefix, rest = url.split("://", 1)
        last_at_idx = rest.rfind("@")
        if last_at_idx != -1:
            auth_part = rest[:last_at_idx]
            host_part = rest[last_at_idx + 1:]
            if ":" in auth_part:
                user, pwd = auth_part.split(":", 1)
                unquoted_pwd = urllib.parse.unquote(pwd)
                encoded_pwd = urllib.parse.quote_plus(unquoted_pwd)
                url = f"{prefix}://{user}:{encoded_pwd}@{host_part}"
    
    cloud_hosts = ("supabase.com", "supabase.co", "render.com", "neon.tech", "cockroachlabs.cloud", "aivencloud.com")
    if any(h in url for h in cloud_hosts) and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url

_root_dir = Path(__file__).resolve().parent.parent.parent
_default_db_path = _root_dir / "intervyn.db"
_default_sqlite_url = f"sqlite:///{_default_db_path.as_posix()}"
DATABASE_URL = _sanitize_db_url(os.getenv("DATABASE_URL", _default_sqlite_url))

connect_args = {}
engine_kwargs = {
    "echo": False
}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Handle cloud PostgreSQL (Supabase / Render) connection drops and timeouts
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

# Enable foreign keys for SQLite
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def ensure_db_migrations(target_engine):
    """
    Safely apply schema additions to existing database tables across SQLite and PostgreSQL.
    Guarantees zero-downtime startup compatibility without requiring manual database migration scripts.
    """
    try:
        from sqlalchemy import inspect, text
        import uuid

        inspector = inspect(target_engine)
        table_names = inspector.get_table_names()

        if "users" in table_names:
            cols = [col["name"] for col in inspector.get_columns("users")]
            if "session_generation" not in cols:
                with target_engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN session_generation VARCHAR(64) DEFAULT 'initial_session'"))
                    rows = conn.execute(text("SELECT id FROM users")).fetchall()
                    for r in rows:
                        conn.execute(
                            text("UPDATE users SET session_generation = :gen WHERE id = :uid"),
                            {"gen": str(uuid.uuid4()), "uid": r[0]}
                        )
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").warning(f"[DB Migration] Automatic schema migration warning: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
