"""Compara variantes das perguntas enviadas ao Laya num conjunto de chamados rotulados à mão.

Uso (dentro do container do backend; carrega o próprio modelo, então leva alguns segundos):
    python scripts/avaliar_perguntas.py              # tabela-resumo
    python scripts/avaliar_perguntas.py --detalhes   # e a resposta para cada chamado

Os rótulos estão em scripts/chamados_rotulados.json. As regras de triagem (pontos e prioridade)
são as mesmas do sistema; só as perguntas mudam de uma variante para outra.
"""
import argparse
import json
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # para importar o pacote `app`

from app import config  # noqa: E402
from app.laya_service import IDIOMA, MODELO, PERGUNTAS, montar_estado  # noqa: E402
from app.triagem import calcular_pontos, classificar_prioridade, triar  # noqa: E402

ARQUIVO_ROTULOS = Path(__file__).with_name("chamados_rotulados.json")

# --- Variantes -------------------------------------------------------------------------------

# As perguntas como vieram no PROMPT_CLAUDE_CODE.md (ponto de partida).
ORIGINAL = {
    "setor": {
        "type": "choice",
        "instructions": "Qual setor do suporte de TI da faculdade deve atender este chamado?",
        "criteria": {
            "rede_wifi": "internet, Wi-Fi do campus, conexão caindo, rede lenta",
            "sistema_academico": "portal do aluno, notas, faltas, matrícula, envio de atividades no sistema",
            "laboratorio": "computadores do laboratório, software instalado, impressora, projetor da sala",
            "conta_senha": "login, senha esquecida, e-mail institucional, conta bloqueada",
            "outros": "qualquer assunto que não se encaixe nos anteriores",
        },
    },
    "urgencia": {
        "type": "score",
        "instructions": "Qual é a urgência deste chamado para o aluno?",
        "criteria": [
            "baixa: pode esperar alguns dias",
            "média: atrapalha, mas o aluno tem alternativa",
            "alta: impede uma aula, prova ou entrega hoje",
        ],
    },
    "tem_prazo": {
        "type": "noul",
        "instructions": "O aluno menciona um prazo, entrega ou prova próxima?",
    },
}

SETORES_PT = {
    "rede_wifi": "internet ou Wi-Fi do campus: sem conexão, conexão caindo, rede lenta ou sinal fraco",
    "sistema_academico": "portal do aluno e sistema acadêmico: notas, faltas, matrícula, histórico, "
    "envio de atividades e provas online",
    "laboratorio": "equipamentos das salas e laboratórios: computador ou PC quebrado, software não instalado, "
    "impressora, projetor, mouse e teclado",
    "conta_senha": "acesso à conta institucional: login, senha esquecida, e-mail institucional, conta bloqueada",
    "outros": "dúvidas gerais, sugestões e qualquer assunto que não se encaixe nos anteriores",
}

SETORES_EN = {
    "rede_wifi": "campus internet or Wi-Fi: no connection, dropping connection, slow network or weak signal",
    "sistema_academico": "student portal and academic system: grades, absences, enrollment, transcripts, "
    "submitting assignments and online exams",
    "laboratorio": "classroom and lab equipment: broken computer or PC, missing software, printer, projector, "
    "mouse and keyboard",
    "conta_senha": "access to the institutional account: login, forgotten password, institutional e-mail, "
    "locked account",
    "outros": "general questions, suggestions and anything that does not fit the other options",
}

PRAZO_PT = {
    "type": "noul",
    "instructions": "A `mensagem` cita um prazo ou compromisso próximo, como entrega, prova ou aula hoje ou amanhã?",
    "criteria": {"false": "não cita prazo, data nem horário", "true": "cita prazo, data ou horário próximo"},
}

PRAZO_EN = {
    "type": "noul",
    "instructions": "Does `mensagem` mention a deadline or an upcoming commitment, such as a delivery, exam or "
    "class today or tomorrow?",
    "criteria": {"false": "no deadline, date or time mentioned", "true": "mentions a close deadline, date or time"},
}


def perguntas(instr_setor, setores, instr_urgencia, niveis, prazo):
    return {
        "setor": {"type": "choice", "instructions": instr_setor, "criteria": setores},
        "urgencia": {"type": "score", "instructions": instr_urgencia, "criteria": niveis},
        "tem_prazo": prazo,
    }


SETOR_PT = "Qual setor do suporte de TI da faculdade deve atender o problema descrito em `mensagem`?"
URGENCIA_PT = "Qual é a urgência do problema descrito em `mensagem`?"
SETOR_EN = "Which IT support team of the college should handle the problem described in `mensagem`?"
URGENCIA_EN = "How urgent is the problem described in `mensagem`?"

VARIANTES = {
    "original": ORIGINAL,
    "pt_descritiva": perguntas(SETOR_PT, SETORES_PT, URGENCIA_PT, [
        "baixa: dúvida, sugestão ou problema que pode esperar alguns dias",
        "média: atrapalha, mas há alternativa ou o prazo não é hoje",
        "alta: impede agora uma aula, prova ou entrega de hoje",
    ], PRAZO_PT),
    "en_descritiva": perguntas(SETOR_EN, SETORES_EN, URGENCIA_EN, [
        "low: a question, suggestion or problem that can wait a few days",
        "medium: it gets in the way, but there is a workaround or the deadline is not today",
        "high: it blocks a class, exam or delivery happening now or today",
    ], PRAZO_EN),
    "pt_5_niveis": perguntas(SETOR_PT, SETORES_PT, URGENCIA_PT, [
        "nenhuma: dúvida ou sugestão, sem problema a resolver",
        "baixa: incomoda, mas pode esperar alguns dias",
        "média: atrapalha, mas há alternativa ou o prazo não é hoje",
        "alta: precisa ser resolvido ainda hoje",
        "crítica: impede agora uma aula, prova ou entrega em andamento",
    ], PRAZO_PT),
    "en_5_niveis": perguntas(SETOR_EN, SETORES_EN, URGENCIA_EN, [
        "none: a question or suggestion, nothing to fix",
        "low: annoying, but it can wait a few days",
        "medium: it gets in the way, but there is a workaround or the deadline is not today",
        "high: it must be solved today",
        "critical: it blocks a class, exam or delivery happening right now",
    ], PRAZO_EN),
}

# Segunda rodada: combinações das melhores partes da primeira (setor de uma, urgência e prazo de outra).
VARIANTES["misto_original"] = {**VARIANTES["pt_descritiva"], "setor": ORIGINAL["setor"]}
VARIANTES["misto_en"] = {**VARIANTES["pt_descritiva"], "setor": VARIANTES["en_descritiva"]["setor"]}
VARIANTES["pt_descritiva_v2"] = perguntas(SETOR_PT, ORIGINAL["setor"]["criteria"], URGENCIA_PT, [
    "baixa: dúvida, sugestão, pedido para o futuro ou defeito pequeno que pode esperar alguns dias",
    "média: atrapalha, mas há alternativa ou o prazo não é hoje",
    "alta: impede agora uma aula, prova ou entrega de hoje",
], PRAZO_PT)

# Se as perguntas em produção forem diferentes de todas as variantes, avalia também.
if all(PERGUNTAS != v for v in VARIANTES.values()):
    VARIANTES["atual"] = PERGUNTAS


# --- Métricas --------------------------------------------------------------------------------

def nivel(urgencia: float) -> int:
    """Nível (0, 1 ou 2) mais próximo de uma urgência na escala de 0 a 2."""
    return 0 if urgencia < 0.5 else 1 if urgencia < 1.5 else 2


def concordancia(previstos, esperados) -> float:
    """Fração dos pares com rótulos diferentes que o previsto põe na ordem certa (empate vale meio)."""
    acertos = total = 0.0
    for (p1, e1), (p2, e2) in combinations(zip(previstos, esperados), 2):
        if e1 == e2:
            continue
        total += 1
        acertos += 0.5 if p1 == p2 else float((p1 > p2) == (e1 > e2))
    return acertos / total


def avaliar(router, nome: str, perguntas_variante: dict, chamados: list[dict]) -> dict:
    niveis = len(perguntas_variante["urgencia"]["criteria"])
    linhas = []
    inicio = time.perf_counter()
    for chamado in chamados:
        resposta = router.predict(montar_estado(None, chamado["texto"]), perguntas_variante, lang=IDIOMA)
        answers = resposta["answers"]
        # Leva a urgência para a escala de 0 a 2 do sistema, qualquer que seja o número de níveis.
        urgencia = answers["urgencia"]["score"] * 2 / (niveis - 1)
        answers = {**answers, "urgencia": {**answers["urgencia"], "score": urgencia}}
        resultado = triar(answers, config.LIMIAR_CONFIANCA)
        pontos_esperados = calcular_pontos(chamado["urgencia"], chamado["prazo"])
        linhas.append({
            "chamado": chamado,
            "resultado": resultado,
            "pontos_esperados": pontos_esperados,
            "prioridade_esperada": classificar_prioridade(pontos_esperados),
        })
    tempo_ms = (time.perf_counter() - inicio) * 1000 / len(chamados)

    def media(valores):
        return sum(valores) / len(valores) if valores else float("nan")

    r = [linha["resultado"] for linha in linhas]
    c = [linha["chamado"] for linha in linhas]
    return {
        "nome": nome,
        "linhas": linhas,
        "setor": media([x.setor == y["setor"] for x, y in zip(r, c)]),
        "revisao": sum(x.fila == "revisao_humana" for x in r),
        "urg_nivel": media([nivel(x.urgencia) == y["urgencia"] for x, y in zip(r, c)]),
        "urg_ordem": concordancia([x.urgencia for x in r], [y["urgencia"] for y in c]),
        "urg_medias": [media([x.urgencia for x, y in zip(r, c) if y["urgencia"] == n]) for n in (0, 1, 2)],
        "prazo": media([(x.prob_prazo >= 0.5) == bool(y["prazo"]) for x, y in zip(r, c)]),
        "prioridade": media([x.prioridade == linha["prioridade_esperada"] for x, linha in zip(r, linhas)]),
        "pontos_ordem": concordancia([x.pontos for x in r], [linha["pontos_esperados"] for linha in linhas]),
        "tempo_ms": tempo_ms,
    }


def imprimir_resumo(resultados: list[dict], conjunto: str, total: int) -> None:
    print(
        f"\nConjunto '{conjunto}': {total} chamados rotulados · checkpoint {MODELO} · lang={IDIOMA} "
        f"· limiar {config.LIMIAR_CONFIANCA}\n"
    )
    cabecalho = (
        f"{'variante':<14} {'setor':>6} {'revisão':>7} {'urg.nível':>9} {'urg.ordem':>9} "
        f"{'urg. média b/m/a':>17} {'prazo':>6} {'priorid.':>8} {'ordem pts':>9} {'ms':>5}"
    )
    print(cabecalho)
    print("-" * len(cabecalho))
    for r in resultados:
        b, m, a = r["urg_medias"]
        print(
            f"{r['nome']:<14} {r['setor']:>6.0%} {r['revisao']:>7} {r['urg_nivel']:>9.0%} {r['urg_ordem']:>9.0%} "
            f"{f'{b:.2f}/{m:.2f}/{a:.2f}':>17} {r['prazo']:>6.0%} {r['prioridade']:>8.0%} "
            f"{r['pontos_ordem']:>9.0%} {r['tempo_ms']:>5.0f}"
        )
    print(
        "\nsetor/prazo/priorid.: acertos · urg.nível: nível mais próximo igual ao rótulo · "
        "urg.ordem e ordem pts: pares com rótulos diferentes postos na ordem certa · "
        "urg. média: urgência média dos chamados rotulados baixa/média/alta (ideal 0/1/2)"
    )


def imprimir_detalhes(resultados: list[dict]) -> None:
    for r in resultados:
        print(f"\n=== {r['nome']}")
        for linha in r["linhas"]:
            x, ch = linha["resultado"], linha["chamado"]
            marca = "ok" if x.prioridade == linha["prioridade_esperada"] else "XX"
            setor = x.setor if x.setor == ch["setor"] else f"{x.setor} (esperado {ch['setor']})"
            print(
                f"  {marca} {x.pontos:>3} pts {x.prioridade:<5} (esperado {linha['prioridade_esperada']:<5}) "
                f"urg {x.urgencia:.2f}/{ch['urgencia']} prazo {x.prob_prazo:.0%}/{ch['prazo']} "
                f"conf {x.confianca_setor:.0%} {setor} · {ch['texto'][:70]}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--detalhes", action="store_true", help="mostra a resposta para cada chamado")
    parser.add_argument("--variantes", nargs="+", choices=list(VARIANTES), help="avalia só estas variantes")
    args = parser.parse_args()

    rotulos = json.loads(ARQUIVO_ROTULOS.read_text(encoding="utf-8"))
    conjuntos = {"desenvolvimento": rotulos["chamados"], "validacao": rotulos.get("validacao", [])}
    variantes = {nome: VARIANTES[nome] for nome in (args.variantes or VARIANTES)}
    if config.LAYA_THREADS:
        import torch

        torch.set_num_threads(config.LAYA_THREADS)
    from laya import Router

    router = Router(default=MODELO, max_loaded=1)
    print("Carregando o modelo...")
    router.predict(montar_estado(None, "aquecimento do modelo"), ORIGINAL, lang=IDIOMA)

    for conjunto, chamados in conjuntos.items():
        if not chamados:
            continue
        resultados = [avaliar(router, nome, p, chamados) for nome, p in variantes.items()]
        imprimir_resumo(resultados, conjunto, len(chamados))
        if args.detalhes:
            imprimir_detalhes(resultados)


if __name__ == "__main__":
    main()
