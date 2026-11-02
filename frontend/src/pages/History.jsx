import { api } from "../api.js";
import { Loading, Problem } from "../components/State.jsx";
import { useApp } from "../context.js";
import { useRequest } from "../hooks/useRequest.js";
import { dateTime, decimal, percent, shorten } from "../lib/format.js";

export default function History() {
  const { byCode } = useApp();
  const predictions = useRequest(() => api.history(30));
  const trainings = useRequest(api.trainings);

  const reloadAll = () => { predictions.reload(); trainings.reload(); };

  return (
    <div className="page">
      <h1>Historial</h1>
      <p className="lead">
        Lo que guardó la base de datos: las últimas predicciones y cada entrenamiento del modelo.
        Las predicciones incluyen los textos que enviaron las personas que usan la aplicación.
      </p>

      <section className="block">
        <h2>Últimas predicciones</h2>
        {predictions.loading && <Loading what="el historial" />}
        {predictions.error && <Problem error={predictions.error} onRetry={reloadAll} />}
        {predictions.data && predictions.data.length === 0 && (
          <p className="muted">Todavía no hay predicciones. Analiza un comentario y aparecerá aquí.</p>
        )}
        {predictions.data && predictions.data.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <caption className="visually-hidden">Últimas predicciones</caption>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Comentario</th>
                  <th scope="col">Veredicto</th>
                  <th scope="col" className="num">Prob. ofensivo</th>
                  <th scope="col">Clase</th>
                  <th scope="col">Origen</th>
                </tr>
              </thead>
              <tbody>
                {predictions.data.map((p) => (
                  <tr key={p.id}>
                    <td>{dateTime(p.fecha)}</td>
                    <td title={p.texto}>{shorten(p.texto, 90)}</td>
                    <td><span className={`badge ${p.ofensivo ? "is-risk" : "is-clean"}`}>
                      {p.ofensivo ? "Ofensivo" : "No ofensivo"}</span></td>
                    <td className="num">{percent(p.probabilidad_ofensivo)}</td>
                    <td>{byCode[p.clase]?.nombre ?? p.clase}</td>
                    <td>{p.origen === "lote" ? "Archivo" : "Individual"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="block">
        <h2>Entrenamientos</h2>
        {trainings.loading && <Loading what="los entrenamientos" />}
        {trainings.error && <Problem error={trainings.error} onRetry={reloadAll} />}
        {trainings.data && trainings.data.length === 0 && <p className="muted">Todavía no hay entrenamientos registrados.</p>}
        {trainings.data && trainings.data.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <caption className="visually-hidden">Entrenamientos registrados</caption>
              <thead>
                <tr>
                  <th scope="col">Versión</th>
                  <th scope="col">Fecha</th>
                  <th scope="col">Modelo</th>
                  <th scope="col">Datos</th>
                  <th scope="col" className="num">F1 macro en prueba</th>
                  <th scope="col" className="num">F1 ofensivo</th>
                </tr>
              </thead>
              <tbody>
                {trainings.data.map((t) => (
                  <tr key={t.version}>
                    <td><code>{t.version}</code></td>
                    <td>{dateTime(t.fecha)}</td>
                    <td>{t.modelo === "complement_nb" ? "Naive Bayes complementario" : "Regresión logística"}</td>
                    <td>{t.fuente_datos === "sintetico" ? "Sintéticos (demostración)" : t.fuente_datos}</td>
                    <td className="num">{decimal(t.test_f1_macro)}</td>
                    <td className="num">{decimal(t.test_f1_ofensivo)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
