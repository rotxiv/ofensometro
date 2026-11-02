import { useMemo, useState } from "react";
import { api } from "../api.js";
import ClassBars from "../components/ClassBars.jsx";
import { useApp } from "../context.js";
import { downloadText, toCsv } from "../lib/csv.js";
import { decimal, integer, percent, shorten } from "../lib/format.js";

const PAGE = 50;
const FILTERS = [
  ["todos", "Todos"],
  ["ofensivos", "Ofensivos"],
  ["limpios", "No ofensivos"],
];

export default function Batch() {
  const { labels, byCode } = useApp();
  const [file, setFile] = useState(null);
  const [state, setState] = useState({ loading: false, error: null, result: null });
  const [filter, setFilter] = useState("todos");
  const [shown, setShown] = useState(PAGE);
  const [dragging, setDragging] = useState(false);

  async function send(chosen) {
    if (!chosen) return;
    setFile(chosen);
    setState({ loading: true, error: null, result: null });
    setShown(PAGE);
    setFilter("todos");
    try {
      setState({ loading: false, error: null, result: await api.batch(chosen) });
    } catch (error) {
      setState({ loading: false, error: error.message, result: null });
    }
  }

  const { result } = state;
  const rows = useMemo(() => {
    if (!result) return [];
    if (filter === "ofensivos") return result.resultados.filter((r) => r.ofensivo);
    if (filter === "limpios") return result.resultados.filter((r) => !r.ofensivo);
    return result.resultados;
  }, [result, filter]);

  function download() {
    const columns = [
      { title: "fila", value: (r) => r.fila },
      { title: "texto", value: (r) => r.texto },
      { title: "ofensivo", value: (r) => (r.ofensivo ? "sí" : "no") },
      { title: "probabilidad_ofensivo", value: (r) => r.probabilidad_ofensivo },
      { title: "clase", value: (r) => r.clase },
      { title: "probabilidad_clase", value: (r) => r.probabilidad },
    ];
    downloadText("resultados-ofensometro.csv", toCsv(result.resultados, columns));
  }

  return (
    <div className="page">
      <h1>Analizar un archivo</h1>
      <p className="lead">
        Sube un archivo <code>.txt</code> con un comentario por línea, o un <code>.csv</code> con una
        columna llamada <code>texto</code>. Máximo 500 comentarios y 1 MB, en UTF-8.
      </p>

      <label className={`drop ${dragging ? "is-over" : ""}`}
             onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
             onDragLeave={() => setDragging(false)}
             onDrop={(e) => { e.preventDefault(); setDragging(false); send(e.dataTransfer.files[0]); }}>
        <input type="file" accept=".txt,.csv,text/plain,text/csv"
               onChange={(e) => { send(e.target.files[0]); e.target.value = ""; }} />
        <strong>{file ? file.name : "Elige un archivo o suéltalo aquí"}</strong>
        <span className="muted small">{state.loading ? "Analizando…" : "Formatos admitidos: .txt y .csv"}</span>
      </label>

      {state.error && <p className="problem" role="alert">{state.error}</p>}

      {result && (
        <section className="block" aria-label="Resultados del archivo">
          <h2>
            {integer(result.ofensivos)} de {integer(result.total)} comentarios son ofensivos
            {" "}({percent(result.ofensivos / result.total, 0)})
          </h2>
          <ClassBars values={result.resumen} labels={labels} scale={result.total}
                     show={(count) => integer(count)} />

          {result.omitidas.length > 0 && (
            <details className="disclosure">
              <summary>{result.omitidas.length} filas omitidas</summary>
              <ul className="plain-list">
                {result.omitidas.map((row) => (
                  <li key={row.fila}>Fila {row.fila}: {row.motivo}</li>
                ))}
              </ul>
            </details>
          )}

          <div className="toolbar">
            <div role="group" aria-label="Filtrar resultados" className="segmented">
              {FILTERS.map(([id, label]) => (
                <button key={id} type="button" aria-pressed={filter === id}
                        onClick={() => { setFilter(id); setShown(PAGE); }}>
                  {label}
                </button>
              ))}
            </div>
            <button type="button" className="button secondary" onClick={download}>
              Descargar resultados (CSV)
            </button>
          </div>

          <div className="table-wrap">
            <table className="table">
              <caption className="visually-hidden">Resultados por comentario</caption>
              <thead>
                <tr>
                  <th scope="col">Fila</th>
                  <th scope="col">Comentario</th>
                  <th scope="col">Veredicto</th>
                  <th scope="col" className="num">Prob. ofensivo</th>
                  <th scope="col">Clase</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, shown).map((row) => (
                  <tr key={row.fila}>
                    <td className="num">{row.fila}</td>
                    <td title={row.texto}>{shorten(row.texto, 140)}</td>
                    <td><span className={`badge ${row.ofensivo ? "is-risk" : "is-clean"}`}>
                      {row.ofensivo ? "Ofensivo" : "No ofensivo"}</span></td>
                    <td className="num">{percent(row.probabilidad_ofensivo)}</td>
                    <td>{byCode[row.clase]?.nombre ?? row.clase} ({decimal(row.probabilidad, 2)})</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length === 0 && <p className="muted">Ningún comentario coincide con este filtro.</p>}
          {rows.length > shown && (
            <button type="button" className="button secondary" onClick={() => setShown(shown + PAGE)}>
              Mostrar {Math.min(PAGE, rows.length - shown)} más ({integer(rows.length - shown)} restantes)
            </button>
          )}
        </section>
      )}
    </div>
  );
}
