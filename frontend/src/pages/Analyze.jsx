import { useId, useState } from "react";
import { api } from "../api.js";
import Annotated from "../components/Annotated.jsx";
import ClassBars from "../components/ClassBars.jsx";
import Meter from "../components/Meter.jsx";
import Signals from "../components/Signals.jsx";
import Steps from "../components/Steps.jsx";
import { useApp } from "../context.js";
import { decimal, percent } from "../lib/format.js";

const MAX_CHARS = 1000;
const EXAMPLES = [
  "Me encantó tu canal, saludos desde Bolivia",
  "Eres un inútil, nadie te soporta 🤡",
  "Todos los políticos son unos corruptos",
  "Joder, qué buen video jajaja ❤",
];

function WeighedWords({ terms }) {
  if (terms.length === 0) return <p className="muted">Ninguna palabra empujó el resultado hacia «ofensivo».</p>;
  const strongest = Math.max(...terms.map((t) => t.peso));
  return (
    <ul className="weighed">
      {terms.map((term) => (
        <li key={term.termino}>
          <span className="word">{term.palabra}</span>
          <span className="bar" aria-hidden="true">
            <span style={{ width: `${(term.peso / strongest) * 100}%` }} />
          </span>
          <span className="class-value">{decimal(term.peso, 2)}</span>
        </li>
      ))}
    </ul>
  );
}

function Verdict({ data }) {
  const { labels, byCode } = useApp();
  const predicted = byCode[data.clase];
  const disagrees = predicted && predicted.ofensivo !== data.ofensivo;
  return (
    <>
      <h2 className={`verdict ${data.ofensivo ? "is-risk" : "is-clean"}`}>
        {data.ofensivo ? "Ofensivo" : "No ofensivo"}
      </h2>
      <p>
        Probabilidad de que sea ofensivo: <strong>{percent(data.probabilidad_ofensivo)}</strong>.
        {" "}Se considera ofensivo a partir de {percent(data.umbral, 0)}.
      </p>
      <Meter value={data.probabilidad_ofensivo} threshold={data.umbral} />

      <h3>Clase más probable: {data.nombre_clase}</h3>
      <p className="muted">{data.descripcion}</p>
      {disagrees && (
        <p className="note">
          La clase más probable es «{data.nombre_clase}», pero las dos clases ofensivas juntas
          {data.ofensivo ? " superan " : " no llegan a "}el umbral. El veredicto usa la suma.
        </p>
      )}
      <ClassBars values={data.probabilidades} labels={labels} highlight={data.clase} />
    </>
  );
}

export default function Analyze() {
  const fieldId = useId();
  const [text, setText] = useState("");
  const [result, setResult] = useState(null); // { text, data } del último análisis
  const [editing, setEditing] = useState(true);
  const [status, setStatus] = useState({ loading: false, error: null });

  async function analyze(value = text) {
    const comment = value.trim();
    if (!comment || status.loading) return;
    setStatus({ loading: true, error: null });
    try {
      const data = await api.predict(comment);
      setText(comment);
      setResult({ text: comment, data });
      setEditing(false);
      setStatus({ loading: false, error: null });
    } catch (error) {
      setStatus({ loading: false, error: error.message });
    }
  }

  const onKeyDown = (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) analyze();
  };

  const data = result?.data;
  return (
    <div className="analyze">
      <div className="analyze-main">
        <h1 className="visually-hidden">Analizar un comentario</h1>
        <div className="sheet" data-editing={editing}>
          {editing ? (
            <>
              <label htmlFor={fieldId} className="sheet-label">Comentario a revisar</label>
              <textarea
                id={fieldId}
                className="sheet-text"
                value={text}
                maxLength={MAX_CHARS}
                rows={6}
                placeholder="Escribe o pega un comentario en español."
                onChange={(event) => setText(event.target.value)}
                onKeyDown={onKeyDown}
              />
              <div className="sheet-foot">
                <span className="muted small">{text.length} de {MAX_CHARS} caracteres</span>
                <button type="button" className="button primary" disabled={!text.trim() || status.loading}
                        onClick={() => analyze()}>
                  {status.loading ? "Analizando…" : "Analizar"}
                </button>
              </div>
            </>
          ) : (
            <>
              <span className="sheet-label">Comentario analizado</span>
              <Annotated text={result.text} terms={data.explicacion.ofensivo}
                         obfuscated={data.preprocesamiento.senales.ofuscadas} />
              <div className="sheet-foot">
                <span className="muted small">Las palabras marcadas son las que más pesaron.</span>
                <button type="button" className="button secondary" onClick={() => setEditing(true)}>
                  Editar texto
                </button>
              </div>
            </>
          )}
        </div>

        {status.error && <p className="problem" role="alert">{status.error}</p>}

        <div className="examples">
          <span className="muted small">Probar con un ejemplo:</span>
          {EXAMPLES.map((example) => (
            <button key={example} type="button" className="button ghost"
                    onClick={() => { setText(example); analyze(example); }}>
              {example}
            </button>
          ))}
        </div>

        {data && (
          <section aria-labelledby="weighed-title" className="block">
            <h3 id="weighed-title">Palabras que empujaron hacia «ofensivo»</h3>
            <WeighedWords terms={data.explicacion.ofensivo} />
            <h3>Señales detectadas</h3>
            <Signals signals={data.preprocesamiento.senales} />
            <Steps steps={data.preprocesamiento} />
          </section>
        )}
      </div>

      <aside className="analyze-side" aria-live="polite" aria-label="Resultado del análisis">
        {data ? (
          <>
            <Verdict data={data} />
            <p className="muted small">
              Modelo: {data.modelo.nombre}, versión {data.modelo.version}. Respondió en {decimal(data.tiempo_ms, 0)} ms.
            </p>
          </>
        ) : (
          <div className="empty">
            <h2>Aquí aparecerá el resultado</h2>
            <p>
              Escribe un comentario y pulsa Analizar. Verás si es ofensivo, a qué clase se parece más
              y qué palabras pesaron en la decisión.
            </p>
            <p className="muted small">Atajo: Ctrl + Enter.</p>
          </div>
        )}
      </aside>
    </div>
  );
}
