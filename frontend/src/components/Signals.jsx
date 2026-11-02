// Rasgos del texto que se detectaron antes de clasificar: no son palabras, pero importan.
export default function Signals({ signals }) {
  const chips = [];
  if (signals.mayusculas) chips.push(["Escrito en mayúsculas, como un grito", "caps"]);
  signals.ofuscadas.forEach(({ original, normal }) =>
    chips.push([`Disfrazado: ${original.replace(/[^\p{L}\p{N}@*_]+$/u, "")} se leyó como ${normal.replace(/[^\p{L}\p{N}@*_]+$/u, "")}`, `obf-${original}`]));
  if (signals.emojis.length) chips.push([`Emojis: ${signals.emojis.join(" ")}`, "emoji"]);
  if (signals.risas) chips.push(["Contiene risas", "risas"]);

  if (chips.length === 0) return <p className="muted">No se detectaron mayúsculas, palabras disfrazadas, emojis ni risas.</p>;
  return (
    <ul className="chips">
      {chips.map(([text, key]) => (
        <li key={key} className="chip">{text}</li>
      ))}
    </ul>
  );
}
