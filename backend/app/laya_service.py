"""Integração com o Laya: carrega o Router e define as perguntas enviadas a cada chamado.

O pacote `laya` (e o PyTorch) só é importado dentro de `ServicoLaya.carregar`, para que o resto
do sistema, e os testes, funcionem sem carregar o modelo.
"""
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("triadesk.laya")

# Checkpoint multilíngue do Laya (mmBERT, 100+ idiomas), adequado para texto em português.
MODELO = "multilingual"

# Enviado em toda chamada. Sem ele, o Router detecta o idioma pelo texto, e uma frase curta ou com
# poucas palavras típicas do português poderia ser lida como inglês e ir para o checkpoint inglês,
# o que, com max_loaded=1, descarregaria o multilíngue e baixaria outro modelo.
IDIOMA = "pt"

# As perguntas abaixo são a variante "misto_original", escolhida com scripts/avaliar_perguntas.py
# sobre os chamados rotulados de scripts/chamados_rotulados.json (veja a seção "Ajuste das
# perguntas" do README): o setor continua com a pergunta original, e a urgência e o prazo usam a
# versão descritiva, que cita entre crases o campo do estado que o modelo lê (como nos presets
# do Laya). O Laya responde cada pergunta de forma independente, então dá para combiná-las.
SETORES = {
    "rede_wifi": "internet, Wi-Fi do campus, conexão caindo, rede lenta",
    "sistema_academico": "portal do aluno, notas, faltas, matrícula, envio de atividades no sistema",
    "laboratorio": "computadores do laboratório, software instalado, impressora, projetor da sala",
    "conta_senha": "login, senha esquecida, e-mail institucional, conta bloqueada",
    "outros": "qualquer assunto que não se encaixe nos anteriores",
}

NOMES_SETORES = {
    "rede_wifi": "Rede / Wi-Fi",
    "sistema_academico": "Sistema Acadêmico",
    "laboratorio": "Laboratório",
    "conta_senha": "Conta / Senha",
    "outros": "Outros",
}

PERGUNTAS = {
    "setor": {
        "type": "choice",
        "instructions": "Qual setor do suporte de TI da faculdade deve atender este chamado?",
        "criteria": SETORES,
    },
    "urgencia": {
        "type": "score",
        "instructions": "Qual é a urgência do problema descrito em `mensagem`?",
        "criteria": [
            "baixa: dúvida, sugestão ou problema que pode esperar alguns dias",
            "média: atrapalha, mas há alternativa ou o prazo não é hoje",
            "alta: impede agora uma aula, prova ou entrega de hoje",
        ],
    },
    "tem_prazo": {
        "type": "noul",
        "instructions": "A `mensagem` cita um prazo ou compromisso próximo, como entrega, prova ou aula hoje ou amanhã?",
        "criteria": {"false": "não cita prazo, data nem horário", "true": "cita prazo, data ou horário próximo"},
    },
}

# Chamado fictício usado só no aquecimento do modelo; não é gravado no banco.
ESTADO_AQUECIMENTO = {"aluno": "aquecimento", "mensagem": "Esqueci a senha do portal do aluno."}


def montar_estado(aluno: str | None, descricao: str) -> dict[str, str]:
    """O "estado" que o Laya lê: quem abriu o chamado e o que escreveu."""
    return {"aluno": aluno or "não informado", "mensagem": descricao}


@dataclass(frozen=True)
class ConsultaLaya:
    payload: dict[str, Any]   # o que foi enviado: estado, perguntas e idioma
    resposta: dict[str, Any]  # resposta bruta do Laya, em tipos JSON puros
    tempo_ms: float           # duração da chamada router.predict


class ServicoLaya:
    """Guarda o único Router do Laya da aplicação e acompanha o carregamento do modelo."""

    def __init__(self, threads: int | None = None):
        self.threads = threads
        self.router = None
        self.status = "carregando"  # carregando | ok | erro
        self.erro: str | None = None

    @property
    def carregado(self) -> bool:
        return self.status == "ok"

    def carregar(self) -> None:
        """Cria o Router, baixa o checkpoint (só na primeira vez) e faz o aquecimento.

        É lento (download + carga na memória), por isso roda numa thread separada, iniciada no
        lifespan do FastAPI. Enquanto isso, a API responde 503 nas rotas que precisam do modelo.
        """
        try:
            inicio = time.perf_counter()
            if self.threads:
                import torch

                torch.set_num_threads(self.threads)
            from laya import Router

            self.router = Router(default=MODELO, max_loaded=1)
            logger.info("Carregando o checkpoint '%s' do Laya (a primeira vez inclui o download)...", MODELO)
            self.router.predict(ESTADO_AQUECIMENTO, PERGUNTAS, lang=IDIOMA)
            self.status = "ok"
            logger.info("Laya pronto em %.1f s.", time.perf_counter() - inicio)
        except Exception as exc:
            self.erro = str(exc)
            self.status = "erro"
            logger.exception("Não foi possível carregar o Laya.")

    def classificar(self, aluno: str | None, descricao: str) -> ConsultaLaya:
        """Envia o chamado ao Laya e devolve o payload, a resposta bruta e o tempo gasto.

        A inferência é síncrona e pesada: chame esta função fora do event loop (rota `def`).
        """
        estado = montar_estado(aluno, descricao)
        inicio = time.perf_counter()
        resultado = self.router.predict(estado, PERGUNTAS, lang=IDIOMA)
        tempo_ms = (time.perf_counter() - inicio) * 1000

        payload = {"estado": estado, "perguntas": PERGUNTAS, "lang": IDIOMA}
        # A resposta traz subclasses de dict (RouteDecision); a ida e volta pelo JSON
        # deixa tudo em tipos puros, prontos para gravar no banco e devolver na API.
        resposta = json.loads(json.dumps(resultado, ensure_ascii=False, default=str))
        return ConsultaLaya(payload=payload, resposta=resposta, tempo_ms=round(tempo_ms, 1))
