"""Schemas Pydantic: o que a API recebe e devolve."""
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.laya_service import SETORES
from app.triagem import FILA_REVISAO_HUMANA

STATUS_VALIDOS = ("aberto", "em_atendimento", "resolvido")
FILAS_VALIDAS = (*SETORES, FILA_REVISAO_HUMANA)

DESCRICAO_MIN = 10
DESCRICAO_MAX = 2000
ALUNO_MAX = 120


class ChamadoCriar(BaseModel):
    aluno: str | None = None
    descricao: str

    @field_validator("aluno")
    @classmethod
    def validar_aluno(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip()
        if len(valor) > ALUNO_MAX:
            raise ValueError(f"O nome do aluno pode ter no máximo {ALUNO_MAX} caracteres.")
        return valor or None

    @field_validator("descricao")
    @classmethod
    def validar_descricao(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < DESCRICAO_MIN:
            raise ValueError(f"A descrição precisa ter pelo menos {DESCRICAO_MIN} caracteres.")
        if len(valor) > DESCRICAO_MAX:
            raise ValueError(f"A descrição pode ter no máximo {DESCRICAO_MAX} caracteres.")
        return valor


class ChamadoAtualizar(BaseModel):
    status: str | None = None
    fila: str | None = None

    @field_validator("status")
    @classmethod
    def validar_status(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in STATUS_VALIDOS:
            raise ValueError(f"Status inválido. Use um destes: {', '.join(STATUS_VALIDOS)}.")
        return valor

    @field_validator("fila")
    @classmethod
    def validar_fila(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in FILAS_VALIDAS:
            raise ValueError(f"Fila inválida. Use uma destas: {', '.join(FILAS_VALIDAS)}.")
        return valor

    @model_validator(mode="after")
    def exigir_algum_campo(self) -> "ChamadoAtualizar":
        if self.status is None and self.fila is None:
            raise ValueError("Informe o novo status ou a nova fila do chamado.")
        return self


class ChamadoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno: str | None
    descricao: str
    setor: str
    fila: str
    confianca_setor: float
    urgencia: float
    prob_prazo: float
    prioridade: str
    pontos: int
    status: str
    tempo_resposta_ms: float
    modelo_laya: str
    criado_em: datetime

    @field_validator("criado_em")
    @classmethod
    def marcar_utc(cls, valor: datetime) -> datetime:
        # O banco guarda UTC sem fuso; marcar o fuso faz o navegador converter para a hora local.
        return valor.replace(tzinfo=timezone.utc) if valor.tzinfo is None else valor


class ChamadoDetalhe(ChamadoResumo):
    payload_enviado: dict[str, Any]
    resposta_laya: dict[str, Any]


class Setor(BaseModel):
    id: str
    nome: str
    descricao: str


class Saude(BaseModel):
    status: str
    modelo_carregado: bool
    modelo: str
    limiar_confianca: float
    erro: str | None = None


class Estatisticas(BaseModel):
    total: int
    por_fila: dict[str, int]
    por_prioridade: dict[str, int]
    por_status: dict[str, int]
    tempo_medio_laya_ms: float | None
