from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base


_SESSION_FACTORY: sessionmaker | None = None


def init_database(database_url: str) -> sessionmaker:
    global _SESSION_FACTORY

    if _SESSION_FACTORY is None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        engine = create_engine(database_url, pool_pre_ping=True, future=True, connect_args=connect_args)
        Base.metadata.create_all(engine)
        _SESSION_FACTORY = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return _SESSION_FACTORY


def get_session_factory(database_url: str) -> sessionmaker:
    return init_database(database_url)
