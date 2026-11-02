import { api } from "../api.js";
import Bars from "../components/Bars.jsx";
import ClassBars from "../components/ClassBars.jsx";
import ContentGate from "../components/ContentGate.jsx";
import { Loading, Problem } from "../components/State.jsx";
import { useApp } from "../context.js";
import { useRequest } from "../hooks/useRequest.js";
import { decimal, integer, percent } from "../lib/format.js";

const SOURCES = { offendes: "OffendES (datos reales)", sintetico: "datos sintéticos de demostración", mixta: "mezcla de orígenes" };

export default function Data() {
  const { labels } = useApp();
  const { data: m, error, loading, reload } = useRequest(api.metrics);

  if (loading) return <div className="page"><h1>Datos</h1><Loading what="los datos" /></div>;
  if (error) return <div className="page"><h1>Datos</h1><Problem error={error} onRetry={reload} /></div>;

  const { cleaning, eda, train_counts, test_counts } = m.dataset;
  const platforms = Object.entries(eda.by_platform ?? {});
  const largest = Math.max(...eda.length_histogram.map((b) => b.count));
  const cleaned = [
    ["Textos vacíos", cleaning.empty_texts_removed],
    ["Etiquetas desconocidas", cleaning.unknown_labels_removed],
    ["Textos duplicados", cleaning.duplicates_removed],
  ];

  return (
    <div className="page">
      <h1>Datos</h1>
      <p className="lead">
        Origen: {SOURCES[m.data_source] ?? m.data_source}. De {integer(cleaning.raw_rows)} comentarios,
        quedaron {integer(cleaning.clean_rows)} tras la limpieza.
      </p>

      <section className="block">
        <h2>Cuántos hay de cada clase</h2>
        <ClassBars values={eda.class_share} labels={labels} scale={Math.max(...Object.values(eda.class_share))} />
        <p className="muted">
          La clase más grande tiene {decimal(eda.imbalance_ratio, 0)} veces más comentarios que la más
          pequeña. Por eso se mide con F1 macro y no solo con la exactitud: responder siempre
          «No ofensivo» ya acertaría {percent(Math.max(...Object.values(eda.class_share)), 0)} de las veces.
        </p>
        <div className="table-wrap">
          <table className="table">
            <caption className="visually-hidden">Comentarios por clase y conjunto</caption>
            <thead>
              <tr>
                <th scope="col">Clase</th>
                <th scope="col" className="num">Entrenamiento</th>
                <th scope="col" className="num">Prueba</th>
              </tr>
            </thead>
            <tbody>
              {labels.map((l) => (
                <tr key={l.codigo}>
                  <th scope="row">{l.nombre}</th>
                  <td className="num">{integer(train_counts[l.codigo])}</td>
                  <td className="num">{integer(test_counts[l.codigo])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="block">
        <h2>Qué se limpió</h2>
        <ul className="plain-list">
          {cleaned.map(([name, count]) => (
            <li key={name}>{name}: <strong>{integer(count)}</strong> eliminados</li>
          ))}
          <li>
            Mismo texto con etiquetas distintas: <strong>{integer(cleaning.duplicates_with_conflicting_label)}</strong>
            {" "}casos (el dato es ambiguo; se conservó solo el primero).
          </li>
        </ul>
      </section>

      <section className="block">
        <h2>Qué tan largos son</h2>
        <Bars tone="ui" max={largest} items={eda.length_histogram.map((b) => ({
          key: b.from, label: `${b.from} a ${b.to} palabras`, value: b.count, text: integer(b.count),
        }))} />
      </section>

      {platforms.length > 0 && (
        <section className="block">
          <h2>Por plataforma</h2>
          <div className="table-wrap">
            <table className="table">
              <caption className="visually-hidden">Comentarios por plataforma y clase</caption>
              <thead>
                <tr>
                  <th scope="col">Plataforma</th>
                  {labels.map((l) => <th key={l.codigo} scope="col" className="num">{l.nombre}</th>)}
                </tr>
              </thead>
              <tbody>
                {platforms.map(([name, counts]) => (
                  <tr key={name}>
                    <th scope="row">{name}</th>
                    {labels.map((l) => <td key={l.codigo} className="num">{integer(counts[l.codigo] ?? 0)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <ContentGate title="Palabras más frecuentes en cada clase">
        {labels.map((l) => (
          <div key={l.codigo} className="term-group">
            <h4>{l.nombre}</h4>
            <ul className="chips tight">
              {(eda.top_words[l.codigo] ?? []).map(([word, count]) => (
                <li key={word} className="chip plain">{word} <span className="muted">{integer(count)}</span></li>
              ))}
            </ul>
          </div>
        ))}
      </ContentGate>
    </div>
  );
}
