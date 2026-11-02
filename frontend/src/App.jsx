import { useEffect, useState } from "react";
import { api } from "./api.js";
import { AppContext } from "./context.js";
import { useRequest } from "./hooks/useRequest.js";
import Analyze from "./pages/Analyze.jsx";
import Batch from "./pages/Batch.jsx";
import Data from "./pages/Data.jsx";
import History from "./pages/History.jsx";
import Model from "./pages/Model.jsx";

const PAGES = [
  { id: "analizar", label: "Analizar", Page: Analyze },
  { id: "archivo", label: "Archivo", Page: Batch },
  { id: "modelo", label: "Modelo", Page: Model },
  { id: "datos", label: "Datos", Page: Data },
  { id: "historial", label: "Historial", Page: History },
];

// La página actual vive en la parte # de la URL (#/modelo): se puede compartir y recargar.
function pageFromHash() {
  const id = window.location.hash.replace(/^#\/?/, "");
  return PAGES.find((page) => page.id === id) ?? PAGES[0];
}

function useCurrentPage() {
  const [page, setPage] = useState(pageFromHash);
  useEffect(() => {
    const update = () => setPage(pageFromHash());
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  useEffect(() => {
    document.title = `${page.label} - Ofensómetro`;
  }, [page]);
  return page;
}

function Notices({ health }) {
  if (health.error) {
    return <p className="notice is-risk" role="alert">{health.error.message}</p>;
  }
  if (!health.data) return null;
  return (
    <>
      {!health.data.modelo_cargado && (
        <p className="notice is-risk" role="alert">
          El modelo todavía no está entrenado. En el backend ejecuta <code>python -m src.pipeline</code> y reinicia la API.
        </p>
      )}
      {health.data.modo_demo && (
        <p className="notice" role="status">
          <strong>Modelo de demostración.</strong> Se entrenó con datos sintéticos: sirve para probar la
          aplicación, pero sus resultados no reflejan el lenguaje real.
        </p>
      )}
    </>
  );
}

export default function App() {
  const page = useCurrentPage();
  const health = useRequest(api.health);
  const labels = useRequest(api.labels);
  const { Page } = page;

  return (
    <AppContext.Provider value={{ labels: labels.data ?? [] }}>
      <header className="masthead">
        <div className="shell masthead-row">
          <a className="wordmark" href="#/analizar">Ofensómetro</a>
          <nav aria-label="Secciones">
            <ul>
              {PAGES.map(({ id, label }) => (
                <li key={id}>
                  <a href={`#/${id}`} aria-current={id === page.id ? "page" : undefined}>{label}</a>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>

      <main className="shell">
        <Notices health={health} />
        {labels.loading ? (
          <p className="muted" role="status">Conectando con la API…</p>
        ) : labels.error ? (
          <div className="problem" role="alert">
            <p>{labels.error.message}</p>
            <button type="button" className="button secondary" onClick={() => { labels.reload(); health.reload(); }}>
              Reintentar
            </button>
          </div>
        ) : (
          <Page key={page.id} />
        )}
      </main>

      <footer className="shell footer">
        {health.data?.modelo_cargado ? (
          <p className="muted small">
            Modelo en uso: {health.data.modelo}, versión {health.data.version}.
            Datos de entrenamiento: {health.data.datos === "sintetico" ? "sintéticos" : health.data.datos}.
          </p>
        ) : (
          <p className="muted small">Proyecto de Tópicos de Programación Avanzada.</p>
        )}
      </footer>
    </AppContext.Provider>
  );
}
