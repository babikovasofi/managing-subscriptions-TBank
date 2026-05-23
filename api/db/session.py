from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "output" / "subscriptions.db"
_ENGINE = create_engine(
    f"sqlite:///{_DB_PATH}",
    connect_args={"check_same_thread": False},
)
_SessionLocal = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False)


def get_db():
    db: Session = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_engine() -> Engine:
    return _ENGINE
