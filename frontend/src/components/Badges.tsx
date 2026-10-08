import type { Prioridade } from "../api";
import { NOMES_PRIORIDADE } from "../formatos";

export function BadgePrioridade({ prioridade, pontos }: { prioridade: Prioridade; pontos?: number }) {
  return (
    <span className={`badge badge-${prioridade}`}>
      {NOMES_PRIORIDADE[prioridade] ?? prioridade}
      {pontos !== undefined && <span className="badge-pontos">{pontos} pts</span>}
    </span>
  );
}

export function BadgeFila({ nome, revisao }: { nome: string; revisao: boolean }) {
  return <span className={`badge ${revisao ? "badge-revisao" : "badge-fila"}`}>{nome}</span>;
}
