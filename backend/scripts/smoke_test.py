"""Smoke test: com o sistema no ar, envia as 4 mensagens de teste e imprime o que o Laya decidiu.

Uso (dentro do container do backend):
    python scripts/smoke_test.py

A URL da API vem de API_URL (padrão: http://localhost:8000/api). Só usa a biblioteca padrão.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = os.getenv("API_URL", "http://localhost:8000/api").rstrip("/")
ESPERA_MAXIMA_S = 600

CASOS = [
    (
        "Não consigo enviar a atividade no portal do aluno, dá erro ao anexar o PDF e o prazo acaba hoje às 23h59.",
        "Sistema Acadêmico, urgência alta, cita prazo",
    ),
    (
        "O Wi-Fi do bloco B fica lento à noite, dá pra usar mas demora pra carregar as páginas.",
        "Rede/Wi-Fi, urgência baixa/média",
    ),
    (
        "O computador 12 do laboratório 3 não tem o VS Code instalado e a aula prática é amanhã.",
        "Laboratório, urgência média/alta",
    ),
    (
        "Esqueci a senha do e-mail institucional e o link de recuperação não chega.",
        "Conta/Senha",
    ),
]


def requisitar(metodo: str, caminho: str, corpo: dict | None = None) -> tuple[int, dict]:
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(
        API_URL + caminho, data=dados, method=metodo, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as erro:
        return erro.code, json.load(erro)


def esperar_modelo() -> None:
    inicio = time.monotonic()
    while True:
        try:
            status, saude = requisitar("GET", "/health")
            if status == 200:
                return
            if saude.get("status") == "erro":
                sys.exit(f"O Laya não carregou: {saude.get('erro')}")
        except (urllib.error.URLError, ConnectionError):
            pass
        if time.monotonic() - inicio > ESPERA_MAXIMA_S:
            sys.exit(f"A API não ficou pronta em {ESPERA_MAXIMA_S} s ({API_URL}/health).")
        print("Aguardando o Laya carregar...")
        time.sleep(5)


def main() -> None:
    print(f"API: {API_URL}")
    esperar_modelo()
    _, setores = requisitar("GET", "/setores")
    nomes = {s["id"]: s["nome"] for s in setores} | {"revisao_humana": "Revisão humana"}

    for numero, (mensagem, esperado) in enumerate(CASOS, start=1):
        status, chamado = requisitar("POST", "/chamados", {"aluno": "Smoke test", "descricao": mensagem})
        print(f"\n[{numero}] {mensagem}")
        print(f"    Esperado:   {esperado}")
        if status != 201:
            print(f"    ERRO {status}: {chamado.get('detail')}")
            continue
        print(
            f"    Setor:      {nomes[chamado['setor']]} (confiança {chamado['confianca_setor']:.0%})"
            f" -> fila {nomes[chamado['fila']]}"
        )
        print(f"    Urgência:   {chamado['urgencia']:.2f} / 2")
        print(f"    Cita prazo: {chamado['prob_prazo']:.0%}")
        print(f"    Prioridade: {chamado['prioridade']} ({chamado['pontos']} pontos)")
        print(f"    Tempo:      {chamado['tempo_resposta_ms']:.0f} ms ({chamado['modelo_laya']})")


if __name__ == "__main__":
    main()
