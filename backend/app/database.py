"""SQLAlchemy engine, session factory and the get_db dependency."""
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

_database_url = get_settings().database_url

engine = create_engine(
    _database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _database_url.startswith("sqlite") else {},
)

if _database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):
        # SQLite ignores foreign keys (and ON DELETE CASCADE) unless asked.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Yield a database session and always close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
