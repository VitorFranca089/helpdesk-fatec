// Cards com as três respostas do Laya, o gráfico de probabilidades por setor e os metadados.
import type { ChamadoDetalhe, Setor } from "../api";
import { decimal, milissegundos, nivelUrgencia, nomeDaFila, porcentagem } from "../formatos";

export function ResultadoLaya({ chamado, setores }: { chamado: ChamadoDetalhe; setores: Setor[] }) {
  const respostas = chamado.resposta_laya.answers;
  const citaPrazo = chamado.prob_prazo >= 0.5;
  const tokens = chamado.resposta_laya.usage?.input_tokens;

  return (
    <div className="resultado-laya">
      <div className="cards">
        <div className="card-resposta">
          <span className="card-tipo">Setor · Choice</span>
          <strong className="card-valor">{nomeDaFila(setores, chamado.setor)}</strong>
          <span className="card-legenda">confiança de {porcentagem(chamado.confianca_setor)}</span>
        </div>
        <div className="card-resposta">
          <span className="card-tipo">Urgência · Score</span>
          <strong className="card-valor">
            {decimal(chamado.urgencia)} <small>/ 2</small>
          </strong>
          <div className="medidor" aria-hidden="true">
            <div className="medidor-preenchido" style={{ width: `${(chamado.urgencia / 2) * 100}%` }} />
          </div>
          <span className="card-legenda">nível mais próximo: {nivelUrgencia(chamado.urgencia)}</span>
        </div>
        <div className="card-resposta">
          <span className="card-tipo">Cita prazo? · Noul</span>
          <strong className="card-valor">{porcentagem(chamado.prob_prazo)}</strong>
          <span className="card-legenda">{citaPrazo ? "sim, menciona prazo ou prova" : "não menciona prazo"}</span>
        </div>
      </div>

      <GraficoSetores
        probabilidades={respostas.setor.probabilities}
        escolhido={respostas.setor.choice}
        setores={setores}
      />

      <p className="meta">
        O Laya respondeu em <strong>{milissegundos(chamado.tempo_resposta_ms)}</strong> · checkpoint{" "}
        <code>{chamado.modelo_laya}</code>
        {tokens !== undefined && <> · {tokens} tokens de entrada</>}
      </p>
    </div>
  );
}

function GraficoSetores({
  probabilidades,
  escolhido,
  setores,
}: {
  probabilidades: Record<string, number>;
  escolhido: string;
  setores: Setor[];
}) {
  const linhas = Object.entries(probabilidades).sort(([, a], [, b]) => b - a);
  return (
    <figure className="grafico">
      <figcaption>Probabilidade de cada setor</figcaption>
      {linhas.map(([id, p]) => (
        <div key={id} className={`barra-linha${id === escolhido ? " escolhido" : ""}`}>
          <span className="barra-rotulo">{nomeDaFila(setores, id)}</span>
          <div className="barra-trilho">
            <div className="barra" style={{ width: `${p * 100}%` }} />
          </div>
          <span className="barra-valor">{porcentagem(p)}</span>
        </div>
      ))}
    </figure>
  );
}
