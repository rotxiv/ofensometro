// Barras horizontales genéricas: [{ key, label, value, text }], con el valor en 0..max.
export default function Bars({ items, max = 1, tone = "ui" }) {
  return (
    <ul className={`class-bars tone-${tone}`}>
      {items.map((item) => (
        <li key={item.key ?? item.label}>
          <span className="class-name">{item.label}</span>
          <span className="bar" aria-hidden="true">
            <span style={{ width: `${Math.min(100, (item.value / max) * 100)}%` }} />
          </span>
          <span className="class-value">{item.text}</span>
        </li>
      ))}
    </ul>
  );
}
