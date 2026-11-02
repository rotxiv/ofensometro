import { percent } from "../lib/format.js";

// Escala de 0 a 100 % con una marca en el umbral de decisión y otra en el valor obtenido.
export default function Meter({ value, threshold }) {
  const at = (x) => `${(x * 100).toFixed(2)}%`;
  return (
    <div
      className="meter"
      role="meter"
      aria-label="Probabilidad de que el comentario sea ofensivo"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(value * 100)}
      aria-valuetext={percent(value)}
    >
      <div className="meter-track">
        <span className="meter-clean" style={{ width: at(threshold) }} />
        <span className="meter-risk" style={{ left: at(threshold) }} />
        <span className="meter-cut" style={{ left: at(threshold) }} />
        <span className="meter-value" style={{ left: at(value) }} />
      </div>
      <div className="meter-scale" aria-hidden="true">
        <span>0 %</span>
        <span className="meter-cut-label" style={{ left: at(threshold) }}>
          umbral {percent(threshold, 0)}
        </span>
        <span>100 %</span>
      </div>
    </div>
  );
}
