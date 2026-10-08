"""Aplicação FastAPI do TriaDesk."""
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.database import Base, engine
from app.laya_service import ServicoLaya
from app.routers import chamados

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    # Um único Router do Laya para a aplicação inteira, guardado em app.state.
    # O carregamento (download + aquecimento) roda em segundo plano para a API já subir
    # e responder /api/health (503) enquanto isso.
    app.state.laya = ServicoLaya(threads=config.LAYA_THREADS)
    threading.Thread(target=app.state.laya.carregar, name="carregar-laya", daemon=True).start()
    yield


app = FastAPI(
    title="TriaDesk API",
    description="Help desk de TI da faculdade com triagem automática pelo Laya.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGENS,
    allow_methods=["*"],
    allow_headers=["*"],
)

MENSAGENS_VALIDACAO = {
    "missing": "Campo obrigatório.",
    "string_type": "Deve ser um texto.",
    "int_parsing": "Deve ser um número inteiro.",
    "json_invalid": "O corpo da requisição não é um JSON válido.",
    "model_attributes_type": "O corpo da requisição deve ser um objeto JSON.",
    "dict_type": "O corpo da requisição deve ser um objeto JSON.",
}


@app.exception_handler(RequestValidationError)
async def erro_de_validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Devolve os erros de validação (422) em português."""
    erros = []
    for erro in exc.errors():
        campo = ".".join(str(p) for p in erro["loc"] if p not in ("body", "query", "path")) or "corpo"
        if erro["type"] == "value_error":
            mensagem = str(erro.get("ctx", {}).get("error", erro["msg"]))  # dos nossos validadores
        else:
            mensagem = MENSAGENS_VALIDACAO.get(erro["type"], "Valor inválido.")
        erros.append({"campo": campo, "mensagem": mensagem})
    resumo = " ".join(e["mensagem"] for e in erros)
    return JSONResponse(status_code=422, content={"detail": resumo, "erros": erros})


app.include_router(chamados.router)
