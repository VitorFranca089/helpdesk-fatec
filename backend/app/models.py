"""Tabelas do banco."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def agora_utc() -> datetime:
    """Data e hora atuais em UTC, sem fuso (o SQLite não guarda fuso)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Chamado(Base):
    __tablename__ = "chamados"

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno: Mapped[str | None] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(Text)

    # Resultado da triagem
    setor: Mapped[str] = mapped_column(String(40))
    fila: Mapped[str] = mapped_column(String(40), index=True)
    confianca_setor: Mapped[float]
    urgencia: Mapped[float]
    prob_prazo: Mapped[float]
    prioridade: Mapped[str] = mapped_column(String(10))
    pontos: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default="aberto", index=True)

    # Rastro da consulta ao Laya
    tempo_resposta_ms: Mapped[float]
    modelo_laya: Mapped[str] = mapped_column(String(60))
    payload_enviado: Mapped[dict[str, Any]] = mapped_column(JSON)
    resposta_laya: Mapped[dict[str, Any]] = mapped_column(JSON)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
