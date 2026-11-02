import { integer, percent } from "../lib/format.js";

// Filas = lo que era en realidad; columnas = lo que predijo el modelo.
// El color de cada celda indica qué parte de su fila cae ahí (la diagonal son los aciertos).
export default function ConfusionMatrix({ matrix, names, caption }) {
  return (
    <div className="table-wrap">
      <table className="confusion">
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th scope="col" className="corner">Real \ Predicho</th>
            {names.map((name) => (
              <th key={name} scope="col">{name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => {
            const total = row.reduce((a, b) => a + b, 0);
            return (
              <tr key={names[i]}>
                <th scope="row">{names[i]}</th>
                {row.map((count, j) => (
                  <td key={j} className={i === j ? "hit" : "miss"}
                      style={{ "--share": total ? count / total : 0 }}>
                    <strong>{integer(count)}</strong>
                    <span>{percent(total ? count / total : 0, 0)}</span>
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
