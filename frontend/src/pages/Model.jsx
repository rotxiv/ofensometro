import Bars from "../components/Bars.jsx";
import ConfusionMatrix from "../components/ConfusionMatrix.jsx";
import ContentGate from "../components/ContentGate.jsx";
import { Loading, Problem } from "../components/State.jsx";
import { useApp } from "../context.js";
import { useRequest } from "../hooks/useRequest.js";
import { api } from "../api.js";
import { dateTime, decimal, integer, percent } from "../lib/format.js";
import { FACTORS, MODELS, NGRAMS, NORMALIZERS, STAGES, STOPWORD_LISTS, hyperparameters } from "../lib/names.js";

function Comparison({ models, production }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <caption className="visually-hidden">Comparación de modelos</caption>
        <thead>
          <tr>
            <th scope="col">Modelo</th>
            <th scope="col" className="num">F1 macro en validación</th>
            <th scope="col" className="num">F1 macro en prueba</th>
            <th scope="col" className="num">Exactitud en prueba</th>
            <th scope="col" className="num">F1 de la clase ofensiva</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <tr key={m.name} className={m.name === production ? "is-chosen" : ""}>
              <th scope="row">{m.label}{m.name === production && <span className="tag">en producción</span>}</th>
              <td className="num">{decimal(m.cv_f1_macro)} ± {decimal(m.cv_f1_macro_std, 3)}</td>
              <td className="num">{decimal(m.test.f1_macro)}</td>
              <td className="num">{percent(m.test.accuracy)}</td>
              <td className="num">{decimal(m.test_binary.offensive.f1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PerClass({ perClass, labels }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <caption className="visually-hidden">Métricas por clase</caption>
        <thead>
          <tr>
            <th scope="col">Clase</th>
            <th scope="col" className="num">Precisión</th>
            <th scope="col" className="num">Recall</th>
            <th scope="col" className="num">F1</th>
            <th scope="col" className="num">Comentarios de prueba</th>
          </tr>
        </thead>
        <tbody>
          {labels.map((l) => {
            const c = perClass[l.codigo];
            return (
              <tr key={l.codigo}>
                <th scope="row">{l.nombre}</th>
                <td className="num">{decimal(c.precision)}</td>
                <td className="num">{decimal(c.recall)}</td>
                <td className="num">{decimal(c.f1)}</td>
                <td className="num">{integer(c.support)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Experiments({ rows }) {
  return (
    <div className="table-wrap">
      <table className="table dense">
        <caption className="visually-hidden">Configuraciones evaluadas con validación cruzada</caption>
        <thead>
          <tr>
            <th scope="col">Etapa</th>
            <th scope="col">Modelo</th>
            <th scope="col">Texto</th>
            <th scope="col">Stop words</th>
            <th scope="col">Términos</th>
            <th scope="col">Hiperparámetros</th>
            <th scope="col" className="num">F1 macro</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{STAGES[r.stage] ?? r.stage}</td>
              <td>{MODELS[r.model] ?? r.model}</td>
              <td>{NORMALIZERS[r.normalizer] ?? r.normalizer}</td>
              <td>{STOPWORD_LISTS[r.stopword_list] ?? r.stopword_list}</td>
              <td>{NGRAMS[r.ngram_range] ?? r.ngram_range}</td>
              <td>{hyperparameters(r.hyperparameters)}</td>
              <td className="num">{decimal(r.cv_f1_macro)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Model() {
  const { labels, byCode } = useApp();
  const { data: m, error, loading, reload } = useRequest(api.metrics);

  if (loading) return <div className="page"><h1>Modelo</h1><Loading what="las métricas" /></div>;
  if (error) return <div className="page"><h1>Modelo</h1><Problem error={error} onRetry={reload} /></div>;

  const production = m.models.find((x) => x.name === m.production.name);
  const names = labels.map((l) => l.nombre);
  const shownExperiments = m.experiments.slice(0, 12);

  return (
    <div className="page">
      <h1>Modelo</h1>
      <p className="lead">
        En producción: <strong>{m.production.label}</strong>, entrenado el {dateTime(m.trained_at)} con{" "}
        {integer(m.dataset.train_size)} comentarios y probado con {integer(m.dataset.test_size)}.
        Vocabulario de {integer(m.vocabulary_size)} términos; división {m.split === "official" ? "oficial" : "estratificada"}.
      </p>

      <section className="block">
        <h2>Comparación de modelos</h2>
        <p className="muted">
          El modelo se elige por su F1 macro en validación cruzada, no por la prueba. El F1 macro
          da el mismo peso a las cuatro clases, así que una clase pequeña como «Ofensivo a un grupo»
          cuenta igual que «No ofensivo».
        </p>
        <Comparison models={m.models} production={m.production.name} />
      </section>

      <section className="block">
        <h2>Dónde acierta y dónde se equivoca</h2>
        <div className="pair">
          <ConfusionMatrix matrix={production.test.confusion_matrix} names={names}
                           caption="Cuatro clases (conjunto de prueba)" />
          <ConfusionMatrix matrix={production.test_binary.confusion_matrix}
                           names={["No ofensivo", "Ofensivo"]}
                           caption={`Vista binaria, umbral ${percent(m.threshold, 0)}`} />
        </div>
        <p className="muted">
          Cada fila suma 100 %: muestra qué hizo el modelo con los comentarios de esa clase real.
          La diagonal son los aciertos.
        </p>
        <PerClass perClass={production.test.per_class} labels={labels} />
        {production.test_binary.roc_auc !== null && (
          <p className="muted">
            En la vista binaria, el área bajo la curva ROC es {decimal(production.test_binary.roc_auc)}:
            la probabilidad de que un comentario ofensivo reciba más puntaje que uno que no lo es.
          </p>
        )}
      </section>

      <section className="block">
        <h2>Qué decisiones importaron</h2>
        <p className="muted">
          Mejor F1 macro en validación cruzada con cada opción, en el cribado, donde todas se miden
          con los mismos hiperparámetros.
        </p>
        <div className="factors">
          {Object.entries(m.factor_effects).map(([factor, values]) => {
            const [title, names] = FACTORS[factor];
            return (
              <div key={factor}>
                <h3>{title}</h3>
                <Bars max={Math.max(...Object.values(values))}
                      items={Object.entries(values).map(([key, value]) => ({
                        key, label: names[key] ?? key, value, text: decimal(value),
                      }))} />
              </div>
            );
          })}
        </div>
      </section>

      <section className="block">
        <h2>Configuraciones probadas</h2>
        <Experiments rows={shownExperiments} />
        <p className="muted small">
          Se muestran las {shownExperiments.length} mejores de {m.experiments.length}. Todas están en
          <code> artifacts/experiments.csv</code>.
        </p>
      </section>

      <section className="block">
        <h2>Cuándo falla más</h2>
        <div className="pair">
          <div>
            <h3>Según cómo está escrito el comentario</h3>
            <Bars tone="ui" items={m.accuracy_by_phenomenon.map((p) => ({
              key: p.fenomeno, label: `${p.fenomeno} (${integer(p.n)})`, value: p.accuracy, text: percent(p.accuracy, 0),
            }))} />
          </div>
          <div>
            <h3>Según la plataforma</h3>
            <Bars tone="ui" items={m.accuracy_by_platform.map((p) => ({
              key: p.plataforma, label: `${p.plataforma} (${integer(p.n)})`, value: p.accuracy, text: percent(p.accuracy, 0),
            }))} />
          </div>
        </div>
        <p className="muted small">Exactitud en el conjunto de prueba; entre paréntesis, cuántos comentarios tenían ese rasgo.</p>
      </section>

      <ContentGate title="Términos que más empujan hacia cada clase">
        {labels.map((l) => (
          <div key={l.codigo} className="term-group">
            <h4>{l.nombre}</h4>
            <ul className="chips tight">
              {(m.top_terms[l.codigo] ?? []).map(([term, weight]) => (
                <li key={term} className="chip plain">{term} <span className="muted">{decimal(weight, 2)}</span></li>
              ))}
            </ul>
          </div>
        ))}
      </ContentGate>

      <ContentGate title="Errores con más seguridad">
        {m.error_examples.length === 0 ? <p className="muted">No hay errores para mostrar.</p> : (
          <div className="table-wrap">
            <table className="table dense">
              <caption className="visually-hidden">Errores del modelo</caption>
              <thead>
                <tr>
                  <th scope="col">Comentario</th>
                  <th scope="col">Era</th>
                  <th scope="col">Predijo</th>
                  <th scope="col" className="num">Seguridad</th>
                </tr>
              </thead>
              <tbody>
                {m.error_examples.map((e) => (
                  <tr key={e.id}>
                    <td>{e.texto}</td>
                    <td>{byCode[e.real]?.nombre ?? e.real}</td>
                    <td>{byCode[e.predicho]?.nombre ?? e.predicho}</td>
                    <td className="num">{percent(e.probabilidad, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </ContentGate>
    </div>
  );
}
