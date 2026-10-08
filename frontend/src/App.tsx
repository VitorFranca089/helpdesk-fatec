import { useEffect, useState } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router";
import { DOCS_URL, obterSaude, type Saude } from "./api";
import AbrirChamado from "./pages/AbrirChamado";
import DetalheChamado from "./pages/DetalheChamado";
import Fila from "./pages/Fila";

const INTERVALO_SAUDE_MS = 5000;

/** Consulta /api/health a cada 5 s até o modelo ficar pronto (ou falhar). */
function useSaude() {
  const [saude, setSaude] = useState<Saude | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let ativo = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function consultar() {
      try {
        const atual = await obterSaude();
        if (!ativo) return;
        setSaude(atual);
        setOffline(false);
        if (atual.status !== "carregando") return;
      } catch {
        if (!ativo) return;
        setOffline(true);
      }
      timer = setTimeout(consultar, INTERVALO_SAUDE_MS);
    }

    consultar();
    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, []);

  return { saude, offline };
}

function StatusModelo({ saude, offline }: { saude: Saude | null; offline: boolean }) {
  let classe = "carregando";
  let texto = "Conectando à API...";
  if (offline) {
    classe = "erro";
    texto = "API fora do ar";
  } else if (saude?.status === "ok") {
    classe = "ok";
    texto = `Laya pronto · ${saude.modelo}`;
  } else if (saude?.status === "erro") {
    classe = "erro";
    texto = "Erro ao carregar o Laya";
  } else if (saude) {
    texto = "Carregando o Laya...";
  }
  return (
    <span className={`status-modelo status-${classe}`}>
      <span className="ponto" aria-hidden="true" />
      {texto}
    </span>
  );
}

export default function App() {
  const { saude, offline } = useSaude();

  return (
    <BrowserRouter>
      <header className="topo">
        <div className="topo-conteudo">
          <Link to="/" className="marca">
            Tria<span>Desk</span>
          </Link>
          <nav>
            <NavLink to="/" end>
              Abrir chamado
            </NavLink>
            <NavLink to="/fila">Fila de atendimento</NavLink>
          </nav>
          <StatusModelo saude={saude} offline={offline} />
        </div>
      </header>

      <main className="conteudo">
        <Routes>
          <Route path="/" element={<AbrirChamado saude={saude} />} />
          <Route path="/fila" element={<Fila />} />
          <Route path="/chamados/:id" element={<DetalheChamado />} />
          <Route
            path="*"
            element={
              <p className="vazio">
                Página não encontrada. <Link to="/">Voltar ao início</Link>
              </p>
            }
          />
        </Routes>
      </main>

      <footer className="rodape">
        TriaDesk · help desk de TI da faculdade com triagem pelo Laya ·{" "}
        <a href={DOCS_URL} target="_blank" rel="noreferrer">
          documentação da API
        </a>
      </footer>
    </BrowserRouter>
  );
}
