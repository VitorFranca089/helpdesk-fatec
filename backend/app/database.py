"""Conexão com o SQLite: engine, sessão e classe base dos models."""
import json
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import config


def _criar_pasta_do_banco(url: str) -> None:
    """Cria a pasta do arquivo SQLite, se ainda não existir."""
    url_banco = make_url(url)
    if url_banco.get_backend_name() == "sqlite" and url_banco.database not in (None, "", ":memory:"):
        Path(url_banco.database).parent.mkdir(parents=True, exist_ok=True)


_criar_pasta_do_banco(config.DATABASE_URL)

engine = create_engine(
    config.DATABASE_URL,
    # O FastAPI atende as rotas em várias threads; o SQLite precisa liberar isso explicitamente.
    connect_args={"check_same_thread": False},
    # Grava acentos como texto legível nas colunas JSON, em vez de ç.
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """Dependência do FastAPI: abre uma sessão por requisição e fecha no fim."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
