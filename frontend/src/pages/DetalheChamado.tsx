import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { atualizarChamado, mensagemDeErro, obterChamado, type ChamadoDetalhe, type Status } from "../api";
import { BadgeFila, BadgePrioridade } from "../components/Badges";
import { BlocoJson } from "../components/BlocoJson";
import { ResultadoLaya } from "../components/ResultadoLaya";
import {
  FILA_REVISAO,
  NOMES_STATUS,
  STATUS,
  dataHora,
  decimal,
  milissegundos,
  nomeDaFila,
  porcentagem,
  useSetores,
} from "../formatos";

export default function DetalheChamado() {
  const { id } = useParams();
  const setores = useSetores();
  const [chamado, setChamado] = useState<ChamadoDetalhe | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [setorEscolhido, setSetorEscolhido] = useState("");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (!id) return;
    obterChamado(id)
      .then((dados) => {
        setChamado(dados);
        setSetorEscolhido(dados.setor);
      })
      .catch((e) => setErro(mensagemDeErro(e)));
  }, [id]);

  async function atualizar(dados: { status?: Status; fila?: string }) {
    if (!chamado) return;
    setSalvando(true);
    try {
      setChamado(await atualizarChamado(chamado.id, dados));
      setErro(null);
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setSalvando(false);
    }
  }

  if (!chamado) {
    return (
      <>
        <Link to="/fila" className="voltar">
          ← Voltar para a fila
        </Link>
        {erro ? <p className="aviso aviso-vermelho">{erro}</p> : <p className="vazio">Carregando...</p>}
      </>
    );
  }

  const emRevisao = chamado.fila === FILA_REVISAO;

  return (
    <>
      <Link to="/fila" className="voltar">
        ← Voltar para a fila
      </Link>

      <div className="cabecalho-detalhe">
        <h1>Chamado #{chamado.id}</h1>
        <BadgePrioridade prioridade={chamado.prioridade} pontos={chamado.pontos} />
        <BadgeFila nome={nomeDaFila(setores, chamado.fila)} revisao={emRevisao} />
        <label className="status-detalhe">
          Status
          <select
            value={chamado.status}
            disabled={salvando}
            onChange={(e) => atualizar({ status: e.target.value as Status })}
          >
            {STATUS.map((s) => (
              <option key={s} value={s}>
                {NOMES_STATUS[s]}
              </option>
            ))}
          </select>
        </label>
      </div>

      {erro && <p className="aviso aviso-vermelho">{erro}</p>}

      {emRevisao && (
        <section className="painel painel-revisao">
          <h2>Revisão humana</h2>
          <p>
            O Laya sugeriu <strong>{nomeDaFila(setores, chamado.setor)}</strong> com confiança de{" "}
            {porcentagem(chamado.confianca_setor)}, abaixo do limiar. Escolha o setor que vai atender:
          </p>
          <div className="linha-revisao">
            <select value={setorEscolhido} onChange={(e) => setSetorEscolhido(e.target.value)}>
              {setores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nome}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="botao"
              disabled={salvando || !setorEscolhido}
              onClick={() => atualizar({ fila: setorEscolhido })}
            >
              Encaminhar
            </button>
          </div>
        </section>
      )}

      <section className="painel">
        <h2>Dados do chamado</h2>
        <dl className="dados">
          <dt>Aluno</dt>
          <dd>{chamado.aluno ?? "Não informado"}</dd>
          <dt>Aberto em</dt>
          <dd>{dataHora(chamado.criado_em)}</dd>
          <dt>Descrição</dt>
          <dd className="texto-longo">{chamado.descricao}</dd>
          <dt>Setor sugerido pelo Laya</dt>
          <dd>
            {nomeDaFila(setores, chamado.setor)} ({porcentagem(chamado.confianca_setor)} de confiança)
          </dd>
          <dt>Fila atual</dt>
          <dd>{nomeDaFila(setores, chamado.fila)}</dd>
          <dt>Urgência</dt>
          <dd>{decimal(chamado.urgencia)} / 2</dd>
          <dt>Cita prazo</dt>
          <dd>{porcentagem(chamado.prob_prazo)}</dd>
          <dt>Pontos</dt>
          <dd>
            {chamado.pontos} / 100 (urgência × 40 + prazo × 20)
          </dd>
          <dt>Tempo do Laya</dt>
          <dd>{milissegundos(chamado.tempo_resposta_ms)}</dd>
          <dt>Checkpoint</dt>
          <dd>
            <code>{chamado.modelo_laya}</code>
          </dd>
        </dl>
      </section>

      <section className="painel">
        <h2>Resposta do Laya</h2>
        <ResultadoLaya chamado={chamado} setores={setores} />
        <BlocoJson titulo="O que foi enviado ao Laya" dados={chamado.payload_enviado} aberto />
        <BlocoJson titulo="Resposta bruta" dados={chamado.resposta_laya} aberto />
      </section>
    </>
  );
}
