import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import {
  atualizarChamado,
  listarChamados,
  mensagemDeErro,
  obterEstatisticas,
  type Chamado,
  type Estatisticas,
  type Status,
} from "../api";
import { BadgeFila, BadgePrioridade } from "../components/Badges";
import { FILA_REVISAO, NOMES_STATUS, STATUS, dataHora, milissegundos, nomeDaFila, useSetores } from "../formatos";

export default function Fila() {
  const setores = useSetores();
  const [fila, setFila] = useState("");
  const [status, setStatus] = useState("");
  const [chamados, setChamados] = useState<Chamado[] | null>(null);
  const [estatisticas, setEstatisticas] = useState<Estatisticas | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      const [lista, resumo] = await Promise.all([listarChamados({ fila, status }), obterEstatisticas()]);
      setChamados(lista);
      setEstatisticas(resumo);
      setErro(null);
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }, [fila, status]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function mudarStatus(chamado: Chamado, novo: Status) {
    try {
      await atualizarChamado(chamado.id, { status: novo });
      await carregar();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  const filas = [...setores.map((s) => s.id), FILA_REVISAO];

  return (
    <>
      <h1>Fila de atendimento</h1>
      <p className="subtitulo">Ordenada por prioridade (pontos) e, no empate, pelo chamado mais antigo.</p>

      {estatisticas && (
        <section className="resumo">
          <div className="resumo-numeros">
            <Numero rotulo="Chamados" valor={estatisticas.total} />
            <Numero rotulo="Prioridade alta" valor={estatisticas.por_prioridade.alta} classe="alta" />
            <Numero rotulo="Prioridade média" valor={estatisticas.por_prioridade.media} classe="media" />
            <Numero rotulo="Prioridade baixa" valor={estatisticas.por_prioridade.baixa} classe="baixa" />
            <Numero
              rotulo="Tempo médio do Laya"
              valor={estatisticas.tempo_medio_laya_ms === null ? "—" : milissegundos(estatisticas.tempo_medio_laya_ms)}
            />
          </div>
          <div className="resumo-filas">
            {Object.entries(estatisticas.por_fila).map(([id, total]) => (
              <button
                key={id}
                type="button"
                className={`chip${fila === id ? " ativo" : ""}${id === FILA_REVISAO ? " chip-revisao" : ""}`}
                onClick={() => setFila(fila === id ? "" : id)}
              >
                {nomeDaFila(setores, id)} <strong>{total}</strong>
              </button>
            ))}
          </div>
        </section>
      )}

      <div className="filtros">
        <label>
          Fila
          <select value={fila} onChange={(e) => setFila(e.target.value)}>
            <option value="">Todas</option>
            {filas.map((id) => (
              <option key={id} value={id}>
                {nomeDaFila(setores, id)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos</option>
            {STATUS.map((s) => (
              <option key={s} value={s}>
                {NOMES_STATUS[s]}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="botao botao-secundario" onClick={carregar}>
          Atualizar
        </button>
      </div>

      {erro && <p className="aviso aviso-vermelho">{erro}</p>}

      {chamados && chamados.length === 0 && (
        <p className="vazio">
          Nenhum chamado encontrado. <Link to="/">Abrir um chamado</Link>
        </p>
      )}

      {chamados && chamados.length > 0 && (
        <div className="tabela-rolagem">
          <table className="tabela">
            <thead>
              <tr>
                <th>#</th>
                <th>Prioridade</th>
                <th>Descrição</th>
                <th>Fila</th>
                <th>Status</th>
                <th>Aberto em</th>
              </tr>
            </thead>
            <tbody>
              {chamados.map((c) => (
                <tr key={c.id}>
                  <td className="numero">{c.id}</td>
                  <td>
                    <BadgePrioridade prioridade={c.prioridade} pontos={c.pontos} />
                  </td>
                  <td className="descricao">
                    <Link to={`/chamados/${c.id}`}>{c.descricao}</Link>
                    <span className="aluno">{c.aluno ?? "Aluno não informado"}</span>
                  </td>
                  <td>
                    <BadgeFila nome={nomeDaFila(setores, c.fila)} revisao={c.fila === FILA_REVISAO} />
                  </td>
                  <td>
                    <select
                      value={c.status}
                      onChange={(e) => mudarStatus(c, e.target.value as Status)}
                      aria-label={`Status do chamado ${c.id}`}
                    >
                      {STATUS.map((s) => (
                        <option key={s} value={s}>
                          {NOMES_STATUS[s]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="data">{dataHora(c.criado_em)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Numero({ rotulo, valor, classe }: { rotulo: string; valor: number | string; classe?: string }) {
  return (
    <div className={`numero-resumo${classe ? ` numero-${classe}` : ""}`}>
      <span>{rotulo}</span>
      <strong>{valor}</strong>
    </div>
  );
}
