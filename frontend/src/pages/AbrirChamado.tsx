import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { criarChamado, mensagemDeErro, type ChamadoDetalhe, type Saude, type Setor } from "../api";
import { BlocoJson } from "../components/BlocoJson";
import { ResultadoLaya } from "../components/ResultadoLaya";
import { FILA_REVISAO, NOMES_PRIORIDADE, nomeDaFila, porcentagem, useSetores } from "../formatos";

const DESCRICAO_MIN = 10;
const DESCRICAO_MAX = 2000;

// As mesmas mensagens do smoke test, para preencher o formulário rápido nos prints.
const EXEMPLOS = [
  {
    rotulo: "Portal do aluno",
    texto:
      "Não consigo enviar a atividade no portal do aluno, dá erro ao anexar o PDF e o prazo acaba hoje às 23h59.",
  },
  {
    rotulo: "Wi-Fi lento",
    texto: "O Wi-Fi do bloco B fica lento à noite, dá pra usar mas demora pra carregar as páginas.",
  },
  {
    rotulo: "Laboratório",
    texto: "O computador 12 do laboratório 3 não tem o VS Code instalado e a aula prática é amanhã.",
  },
  {
    rotulo: "Senha do e-mail",
    texto: "Esqueci a senha do e-mail institucional e o link de recuperação não chega.",
  },
];

export default function AbrirChamado({ saude }: { saude: Saude | null }) {
  const setores = useSetores();
  const [aluno, setAluno] = useState("");
  const [descricao, setDescricao] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [chamado, setChamado] = useState<ChamadoDetalhe | null>(null);

  const tamanho = descricao.trim().length;
  const descricaoValida = tamanho >= DESCRICAO_MIN && tamanho <= DESCRICAO_MAX;
  const modeloPronto = saude?.modelo_carregado ?? false;

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setErro(null);
    setChamado(null);
    try {
      setChamado(await criarChamado({ aluno: aluno.trim() || null, descricao: descricao.trim() }));
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <h1>Abrir chamado</h1>
      <p className="subtitulo">
        Descreva o problema. O Laya classifica o chamado e o TriaDesk encaminha para a fila certa.
      </p>

      <form className="painel formulario" onSubmit={enviar}>
        <label>
          Nome do aluno <span className="opcional">(opcional)</span>
          <input value={aluno} onChange={(e) => setAluno(e.target.value)} maxLength={120} placeholder="Ex.: Maria Souza" />
        </label>

        <label>
          Descrição do problema
          <textarea
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            rows={5}
            maxLength={DESCRICAO_MAX}
            placeholder="O que aconteceu, onde e se há algum prazo envolvido."
            required
          />
          <span className={`contador${tamanho > 0 && !descricaoValida ? " invalido" : ""}`}>
            {tamanho}/{DESCRICAO_MAX} {tamanho > 0 && tamanho < DESCRICAO_MIN && `· mínimo de ${DESCRICAO_MIN} caracteres`}
          </span>
        </label>

        <div className="exemplos">
          <span>Exemplos:</span>
          {EXEMPLOS.map((exemplo) => (
            <button key={exemplo.rotulo} type="button" className="chip" onClick={() => setDescricao(exemplo.texto)}>
              {exemplo.rotulo}
            </button>
          ))}
        </div>

        {!modeloPronto && (
          <p className="aviso aviso-amarelo">
            {!saude
              ? "Conectando à API..."
              : saude.status === "erro"
                ? `O Laya não carregou: ${saude.erro}`
                : "O Laya ainda está carregando. Na primeira subida o modelo é baixado, o que leva alguns minutos."}
          </p>
        )}

        <button type="submit" className="botao" disabled={enviando || !descricaoValida || !modeloPronto}>
          {enviando ? (
            <>
              <span className="spinner" aria-hidden="true" /> Consultando o Laya...
            </>
          ) : (
            "Classificar chamado"
          )}
        </button>

        {erro && <p className="aviso aviso-vermelho">{erro}</p>}
      </form>

      {chamado && (
        <section className="painel">
          <Encaminhamento chamado={chamado} setores={setores} limiar={saude?.limiar_confianca} />
          <ResultadoLaya chamado={chamado} setores={setores} />
          <BlocoJson titulo="O que foi enviado ao Laya" dados={chamado.payload_enviado} />
          <BlocoJson titulo="Resposta bruta" dados={chamado.resposta_laya} />
        </section>
      )}
    </>
  );
}

function Encaminhamento({ chamado, setores, limiar }: { chamado: ChamadoDetalhe; setores: Setor[]; limiar?: number }) {
  const prioridade = `${NOMES_PRIORIDADE[chamado.prioridade].toLowerCase()} (${chamado.pontos} pontos)`;
  const link = (
    <Link to={`/chamados/${chamado.id}`} className="link-detalhe">
      Ver o chamado #{chamado.id} →
    </Link>
  );

  if (chamado.fila === FILA_REVISAO) {
    return (
      <div className="encaminhamento encaminhamento-revisao">
        <p>
          <strong>Enviado para revisão humana.</strong> A confiança no setor sugerido (
          {nomeDaFila(setores, chamado.setor)}) foi de {porcentagem(chamado.confianca_setor)}
          {limiar !== undefined && <>, abaixo do limiar de {porcentagem(limiar)}</>}. Prioridade {prioridade}.
        </p>
        {link}
      </div>
    );
  }

  return (
    <div className="encaminhamento encaminhamento-ok">
      <p>
        <strong>Encaminhado para a fila {nomeDaFila(setores, chamado.fila)}</strong> com prioridade {prioridade}.
      </p>
      {link}
    </div>
  );
}
