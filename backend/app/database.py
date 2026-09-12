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
        url = url.replace("postgres://", "postgresql://", 1)
    
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
    
    if ("supabase.com" in url or "supabase.co" in url) and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url

DATABASE_URL = _sanitize_db_url(os.getenv("DATABASE_URL", "sqlite:///./intervyn.db"))

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
