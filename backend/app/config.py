"""Configurações do TriaDesk, lidas de variáveis de ambiente."""
import os


def _inteiro_opcional(nome: str) -> int | None:
    valor = os.getenv(nome, "").strip()
    if not valor:
        return None
    numero = int(valor)
    return numero if numero > 0 else None


# Banco SQLite. No Docker, aponte para um arquivo dentro do volume (ex.: sqlite:////data/triadesk.db).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dados/triadesk.db")

# Abaixo desta confiança no setor, o chamado vai para a fila de revisão humana.
LIMIAR_CONFIANCA = float(os.getenv("LIMIAR_CONFIANCA", "0.60"))

# Limita as threads do PyTorch na CPU. Vazio = deixa o PyTorch decidir.
LAYA_THREADS = _inteiro_opcional("LAYA_THREADS")

# Origens liberadas no CORS, separadas por vírgula. "*" libera todas (uso em desenvolvimento).
CORS_ORIGENS = [o.strip() for o in os.getenv("CORS_ORIGENS", "*").split(",") if o.strip()]
