from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Neon commonly supplies DATABASE_URL as `postgresql://...`, while this project
# intentionally uses psycopg v3 (`psycopg[binary]`). SQLAlchemy otherwise selects
# the legacy psycopg2 dialect and the Vercel function fails during import.
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = "postgresql+psycopg://" + database_url.removeprefix("postgres://")
elif database_url.startswith("postgresql://"):
    database_url = "postgresql+psycopg://" + database_url.removeprefix("postgresql://")

engine = create_engine(
    database_url,
    connect_args={"connect_timeout": 5},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
