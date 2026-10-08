"""Testes das regras de triagem com respostas do Laya mockadas (o modelo não é carregado)."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.triagem import (
    FILA_REVISAO_HUMANA,
    calcular_pontos,
    classificar_prioridade,
    encaminhar,
    ordenar_fila,
    triar,
)

LIMIAR = 0.60


def respostas_laya(setor: str, confianca: float, urgencia: float, prazo: float) -> dict:
    """Monta um `resultado["answers"]` no formato do Laya 0.4.0, só com os campos usados."""
    return {
        "setor": {"type": "choice", "choice": setor, "answer_confidence": confianca},
        "urgencia": {"type": "score", "score": urgencia},
        "tem_prazo": {"type": "noul", "noul": prazo},
    }


def test_prioridade_alta_vai_para_o_setor_escolhido():
    resultado = triar(respostas_laya("sistema_academico", 0.92, urgencia=1.8, prazo=0.9), LIMIAR)

    assert resultado.setor == "sistema_academico"
    assert resultado.fila == "sistema_academico"
    assert resultado.pontos == 90  # 1,8 × 40 + 0,9 × 20
    assert resultado.prioridade == "alta"


def test_prioridade_media():
    resultado = triar(respostas_laya("laboratorio", 0.80, urgencia=1.0, prazo=0.2), LIMIAR)

    assert resultado.fila == "laboratorio"
    assert resultado.pontos == 44  # 1,0 × 40 + 0,2 × 20
    assert resultado.prioridade == "media"


def test_prioridade_baixa():
    resultado = triar(respostas_laya("rede_wifi", 0.75, urgencia=0.3, prazo=0.1), LIMIAR)

    assert resultado.fila == "rede_wifi"
    assert resultado.pontos == 14  # 0,3 × 40 + 0,1 × 20
    assert resultado.prioridade == "baixa"


def test_confianca_baixa_vai_para_revisao_humana_mas_guarda_o_setor_sugerido():
    resultado = triar(respostas_laya("conta_senha", 0.45, urgencia=1.2, prazo=0.3), LIMIAR)

    assert resultado.fila == FILA_REVISAO_HUMANA
    assert resultado.setor == "conta_senha"
    assert resultado.confianca_setor == 0.45
    assert resultado.prioridade == "media"  # a prioridade é calculada mesmo em revisão


def test_confianca_igual_ao_limiar_nao_vai_para_revisao():
    assert encaminhar({"choice": "outros", "answer_confidence": 0.60}, LIMIAR) == "outros"
    assert encaminhar({"choice": "outros", "answer_confidence": 0.5999}, LIMIAR) == FILA_REVISAO_HUMANA


def test_limiar_configuravel():
    setor = {"choice": "laboratorio", "answer_confidence": 0.70}
    assert encaminhar(setor, limiar=0.60) == "laboratorio"
    assert encaminhar(setor, limiar=0.80) == FILA_REVISAO_HUMANA


@pytest.mark.parametrize(
    ("pontos", "prioridade"),
    [(100, "alta"), (60, "alta"), (59, "media"), (30, "media"), (29, "baixa"), (0, "baixa")],
)
def test_faixas_de_prioridade(pontos, prioridade):
    assert classificar_prioridade(pontos) == prioridade


def test_pontos_ficam_entre_0_e_100():
    assert calcular_pontos(0.0, 0.0) == 0
    assert calcular_pontos(2.0, 1.0) == 100


def test_fila_ordena_por_pontos_e_depois_pelo_mais_antigo():
    def chamado(id_, pontos, hora):
        return SimpleNamespace(id=id_, pontos=pontos, criado_em=datetime(2026, 10, 8, hora))

    antigo_medio = chamado(1, 44, hora=8)
    novo_alto = chamado(2, 90, hora=10)
    novo_medio = chamado(3, 44, hora=9)
    baixo = chamado(4, 14, hora=7)

    ordem = ordenar_fila([baixo, novo_medio, novo_alto, antigo_medio])

    assert [c.id for c in ordem] == [2, 1, 3, 4]
