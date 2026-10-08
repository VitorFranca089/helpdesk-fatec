"""Regras de negócio da triagem, aplicadas sobre as respostas do Laya.

Todas as funções são puras: recebem as respostas (o dict `resultado["answers"]` do Laya) e
devolvem o resultado, sem acessar banco nem modelo. Por isso são testadas com respostas mockadas.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, TypeVar

FILA_REVISAO_HUMANA = "revisao_humana"

# Pesos da pontuação de prioridade: urgência vai de 0 a 2 e P(prazo) de 0 a 1, então o máximo é 100.
PESO_URGENCIA = 40
PESO_PRAZO = 20

# Pontuação mínima de cada prioridade, da maior para a menor.
FAIXAS_PRIORIDADE = (("alta", 60), ("media", 30), ("baixa", 0))
PRIORIDADES = tuple(nome for nome, _ in FAIXAS_PRIORIDADE)


@dataclass(frozen=True)
class ResultadoTriagem:
    setor: str
    fila: str
    confianca_setor: float
    urgencia: float
    prob_prazo: float
    pontos: int
    prioridade: str


def encaminhar(resposta_setor: dict[str, Any], limiar: float) -> str:
    """Regras 1 e 2: a fila é o setor escolhido (Choice), ou revisão humana se a confiança for baixa."""
    if resposta_setor["answer_confidence"] < limiar:
        return FILA_REVISAO_HUMANA
    return resposta_setor["choice"]


def calcular_pontos(urgencia: float, prob_prazo: float) -> int:
    """Regra 3: pontos = urgência × 40 + P(prazo) × 20, de 0 a 100."""
    pontos = round(urgencia * PESO_URGENCIA + prob_prazo * PESO_PRAZO)
    return max(0, min(100, pontos))


def classificar_prioridade(pontos: int) -> str:
    """Regra 3: >= 60 é alta, >= 30 é média, abaixo disso é baixa."""
    for prioridade, minimo in FAIXAS_PRIORIDADE:
        if pontos >= minimo:
            return prioridade
    return "baixa"


def triar(respostas: dict[str, Any], limiar: float) -> ResultadoTriagem:
    """Aplica as regras 1 a 3 sobre as respostas do Laya (`resultado["answers"]`)."""
    setor = respostas["setor"]
    urgencia = float(respostas["urgencia"]["score"])
    prob_prazo = float(respostas["tem_prazo"]["noul"])
    pontos = calcular_pontos(urgencia, prob_prazo)
    return ResultadoTriagem(
        setor=setor["choice"],
        fila=encaminhar(setor, limiar),
        confianca_setor=float(setor["answer_confidence"]),
        urgencia=urgencia,
        prob_prazo=prob_prazo,
        pontos=pontos,
        prioridade=classificar_prioridade(pontos),
    )


T = TypeVar("T")


def ordenar_fila(chamados: Iterable[T]) -> list[T]:
    """Regra 4: mais pontos primeiro; no empate, o chamado mais antigo primeiro.

    Aceita qualquer objeto com os atributos `pontos`, `criado_em` e `id`.
    """
    return sorted(chamados, key=lambda c: (-c.pontos, c.criado_em, c.id))
