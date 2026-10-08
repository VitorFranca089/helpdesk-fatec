// Cliente da API do TriaDesk. O endereço do backend vem de VITE_API_URL.

const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
export const API_URL = `${BASE_URL}/api`;
export const DOCS_URL = `${BASE_URL}/docs`;

export type Status = "aberto" | "em_atendimento" | "resolvido";
export type Prioridade = "alta" | "media" | "baixa";

export interface Setor {
  id: string;
  nome: string;
  descricao: string;
}

export interface Saude {
  status: "carregando" | "ok" | "erro";
  modelo_carregado: boolean;
  modelo: string;
  limiar_confianca: number;
  erro: string | null;
}

/** Resposta bruta do Laya 0.4.0, só com os campos que a interface usa. */
export interface RespostaLaya {
  answers: {
    setor: {
      choice: string;
      probabilities: Record<string, number>;
      confidence: number;
      answer_confidence: number;
    };
    urgencia: {
      score: number;
      probabilities: Record<string, number>;
      legend: Record<string, string>;
      answer_confidence: number;
    };
    tem_prazo: {
      noul: number;
      answer_confidence: number;
    };
  };
  routing: { model: string; repo?: string; reason?: string };
  usage?: { input_tokens?: number };
}

export interface Chamado {
  id: number;
  aluno: string | null;
  descricao: string;
  setor: string;
  fila: string;
  confianca_setor: number;
  urgencia: number;
  prob_prazo: number;
  prioridade: Prioridade;
  pontos: number;
  status: Status;
  tempo_resposta_ms: number;
  modelo_laya: string;
  criado_em: string;
}

export interface ChamadoDetalhe extends Chamado {
  payload_enviado: Record<string, unknown>;
  resposta_laya: RespostaLaya;
}

export interface Estatisticas {
  total: number;
  por_fila: Record<string, number>;
  por_prioridade: Record<Prioridade, number>;
  por_status: Record<Status, number>;
  tempo_medio_laya_ms: number | null;
}

export class ErroApi extends Error {
  status: number;

  constructor(mensagem: string, status: number) {
    super(mensagem);
    this.status = status;
  }
}

async function requisitar<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`${API_URL}${caminho}`, {
      ...opcoes,
      headers: { "Content-Type": "application/json", ...opcoes.headers },
    });
  } catch {
    throw new ErroApi("Não foi possível falar com a API. Confira se o backend está no ar.", 0);
  }
  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const detalhe = corpo?.detail;
    throw new ErroApi(
      typeof detalhe === "string" ? detalhe : `A API respondeu com erro ${resposta.status}.`,
      resposta.status,
    );
  }
  return corpo as T;
}

/** A rota responde 503 enquanto o modelo carrega, mas o corpo é útil nos dois casos. */
export async function obterSaude(): Promise<Saude> {
  const resposta = await fetch(`${API_URL}/health`);
  return (await resposta.json()) as Saude;
}

let setoresEmCache: Promise<Setor[]> | null = null;

export function listarSetores(): Promise<Setor[]> {
  setoresEmCache ??= requisitar<Setor[]>("/setores").catch((erro) => {
    setoresEmCache = null; // tenta de novo na próxima chamada
    throw erro;
  });
  return setoresEmCache;
}

export function criarChamado(dados: { aluno: string | null; descricao: string }) {
  return requisitar<ChamadoDetalhe>("/chamados", { method: "POST", body: JSON.stringify(dados) });
}

export function listarChamados(filtros: { fila?: string; status?: string } = {}) {
  const params = new URLSearchParams();
  if (filtros.fila) params.set("fila", filtros.fila);
  if (filtros.status) params.set("status", filtros.status);
  const query = params.toString();
  return requisitar<Chamado[]>(`/chamados${query ? `?${query}` : ""}`);
}

export function obterChamado(id: number | string) {
  return requisitar<ChamadoDetalhe>(`/chamados/${id}`);
}

export function atualizarChamado(id: number, dados: { status?: Status; fila?: string }) {
  return requisitar<ChamadoDetalhe>(`/chamados/${id}`, { method: "PATCH", body: JSON.stringify(dados) });
}

export function obterEstatisticas() {
  return requisitar<Estatisticas>("/estatisticas");
}

export function mensagemDeErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : "Erro inesperado.";
}
