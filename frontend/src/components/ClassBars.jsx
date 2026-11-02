import { percent } from "../lib/format.js";

// Una barra por clase. `values` es { codigo: número }; por defecto se muestran como porcentaje.
export default function ClassBars({ values, labels, highlight, scale = 1, show = percent }) {
  return (
    <ul className="class-bars">
      {labels.map((label) => {
        const value = values[label.codigo] ?? 0;
        return (
          <li key={label.codigo} className={label.ofensivo ? "is-risk" : "is-clean"}
              data-current={label.codigo === highlight}>
            <span className="class-name">{label.nombre}</span>
            <span className="bar" aria-hidden="true">
              <span style={{ width: `${Math.min(100, (value / scale) * 100)}%` }} />
            </span>
            <span className="class-value">{show(value)}</span>
          </li>
        );
      })}
    </ul>
  );
}
