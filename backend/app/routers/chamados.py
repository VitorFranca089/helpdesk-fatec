"""Rotas da API, todas com o prefixo /api."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.laya_service import MODELO, NOMES_SETORES, SETORES, ServicoLaya
from app.models import Chamado
from app.schemas import (
    FILAS_VALIDAS,
    STATUS_VALIDOS,
    ChamadoAtualizar,
    ChamadoCriar,
    ChamadoDetalhe,
    ChamadoResumo,
    Estatisticas,
    Saude,
    Setor,
)
from app.triagem import PRIORIDADES, ordenar_fila, triar

logger = logging.getLogger("triadesk.api")

router = APIRouter(prefix="/api")


def obter_laya(request: Request) -> ServicoLaya:
    return request.app.state.laya


def exigir_modelo_pronto(laya: ServicoLaya) -> None:
    if laya.status == "erro":
        raise HTTPException(503, f"O modelo Laya não pôde ser carregado: {laya.erro}")
    if not laya.carregado:
        raise HTTPException(503, "O modelo Laya ainda está carregando. Tente de novo em instantes.")


def buscar_chamado(db: Session, chamado_id: int) -> Chamado:
    chamado = db.get(Chamado, chamado_id)
    if chamado is None:
        raise HTTPException(404, f"Chamado {chamado_id} não encontrado.")
    return chamado


@router.get("/health", response_model=Saude, summary="Situação da API e do modelo")
def saude(request: Request, response: Response):
    laya = obter_laya(request)
    # 503 enquanto o modelo carrega, para o healthcheck do Docker só aprovar com o Laya pronto.
    if not laya.carregado:
        response.status_code = 503
    return Saude(
        status=laya.status,
        modelo_carregado=laya.carregado,
        modelo=MODELO,
        limiar_confianca=config.LIMIAR_CONFIANCA,
        erro=laya.erro,
    )


@router.get("/setores", response_model=list[Setor], summary="Setores do suporte de TI")
def listar_setores():
    return [Setor(id=id_, nome=NOMES_SETORES[id_], descricao=descricao) for id_, descricao in SETORES.items()]


@router.post("/chamados", response_model=ChamadoDetalhe, status_code=201, summary="Abre e classifica um chamado")
def criar_chamado(dados: ChamadoCriar, request: Request, db: Session = Depends(get_db)):
    # Rota `def` (e não `async def`): o FastAPI a roda num threadpool, então a inferência
    # do Laya, que é síncrona e pesada, não trava o event loop.
    laya = obter_laya(request)
    exigir_modelo_pronto(laya)
    try:
        consulta = laya.classificar(dados.aluno, dados.descricao)
    except Exception as exc:
        logger.exception("Falha ao consultar o Laya.")
        raise HTTPException(500, "Falha ao consultar o Laya. Veja os logs do backend.") from exc

    resultado = triar(consulta.resposta["answers"], config.LIMIAR_CONFIANCA)
    chamado = Chamado(
        aluno=dados.aluno,
        descricao=dados.descricao,
        setor=resultado.setor,
        fila=resultado.fila,
        confianca_setor=resultado.confianca_setor,
        urgencia=resultado.urgencia,
        prob_prazo=resultado.prob_prazo,
        prioridade=resultado.prioridade,
        pontos=resultado.pontos,
        tempo_resposta_ms=consulta.tempo_ms,
        modelo_laya=consulta.resposta["routing"]["model"],
        payload_enviado=consulta.payload,
        resposta_laya=consulta.resposta,
    )
    db.add(chamado)
    db.commit()
    db.refresh(chamado)
    return chamado


@router.get("/chamados", response_model=list[ChamadoResumo], summary="Fila de atendimento")
def listar_chamados(fila: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    consulta = select(Chamado)
    if fila:
        consulta = consulta.where(Chamado.fila == fila)
    if status:
        consulta = consulta.where(Chamado.status == status)
    return ordenar_fila(db.scalars(consulta).all())


@router.get("/chamados/{chamado_id}", response_model=ChamadoDetalhe, summary="Detalhe de um chamado")
def obter_chamado(chamado_id: int, db: Session = Depends(get_db)):
    return buscar_chamado(db, chamado_id)


@router.patch("/chamados/{chamado_id}", response_model=ChamadoDetalhe, summary="Muda o status ou a fila")
def atualizar_chamado(chamado_id: int, dados: ChamadoAtualizar, db: Session = Depends(get_db)):
    chamado = buscar_chamado(db, chamado_id)
    if dados.status is not None:
        chamado.status = dados.status
    if dados.fila is not None:
        # O `setor` continua sendo o que o Laya sugeriu; só a fila muda (decisão humana).
        chamado.fila = dados.fila
    db.commit()
    db.refresh(chamado)
    return chamado


@router.get("/estatisticas", response_model=Estatisticas, summary="Resumo da fila")
def estatisticas(db: Session = Depends(get_db)):
    def contar_por(coluna, chaves) -> dict[str, int]:
        contagem = dict.fromkeys(chaves, 0)
        for valor, total in db.execute(select(coluna, func.count()).group_by(coluna)):
            contagem[valor] = total
        return contagem

    tempo_medio = db.scalar(select(func.avg(Chamado.tempo_resposta_ms)))
    return Estatisticas(
        total=db.scalar(select(func.count()).select_from(Chamado)) or 0,
        por_fila=contar_por(Chamado.fila, FILAS_VALIDAS),
        por_prioridade=contar_por(Chamado.prioridade, PRIORIDADES),
        por_status=contar_por(Chamado.status, STATUS_VALIDOS),
        tempo_medio_laya_ms=round(tempo_medio, 1) if tempo_medio is not None else None,
    )
