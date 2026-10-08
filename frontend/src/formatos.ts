// Nomes amigáveis e formatação de números e datas em pt-BR.
import { useEffect, useState } from "react";
import { listarSetores, type Prioridade, type Setor, type Status } from "./api";

export const FILA_REVISAO = "revisao_humana";

export const STATUS: Status[] = ["aberto", "em_atendimento", "resolvido"];

export const NOMES_STATUS: Record<Status, string> = {
  aberto: "Aberto",
  em_atendimento: "Em atendimento",
  resolvido: "Resolvido",
};

export const NOMES_PRIORIDADE: Record<Prioridade, string> = {
  alta: "Alta",
  media: "Média",
  baixa: "Baixa",
};

const NIVEIS_URGENCIA = ["baixa", "média", "alta"];

/** Nível mais próximo do score de urgência (0 a 2). */
export function nivelUrgencia(score: number): string {
  return NIVEIS_URGENCIA[Math.min(2, Math.max(0, Math.round(score)))];
}

/** Setores vindos de GET /api/setores (com cache). */
export function useSetores(): Setor[] {
  const [setores, setSetores] = useState<Setor[]>([]);
  useEffect(() => {
    listarSetores()
      .then(setSetores)
      .catch(() => setSetores([]));
  }, []);
  return setores;
}

export function nomeDaFila(setores: Setor[], id: string): string {
  if (id === FILA_REVISAO) return "Revisão humana";
  return setores.find((s) => s.id === id)?.nome ?? id;
}

export function porcentagem(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 0 });
}

export function decimal(valor: number, casas = 2): string {
  return valor.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

export function milissegundos(valor: number): string {
  return `${Math.round(valor).toLocaleString("pt-BR")} ms`;
}

export function dataHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}
