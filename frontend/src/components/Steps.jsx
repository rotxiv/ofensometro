// El recorrido del texto por el preprocesamiento, paso a paso.
const method = { stem: "Raíces (stemming)", lemma: "Lemas" };

function Words({ items }) {
  if (!items.length) return <span className="muted">ninguna</span>;
  return (
    <ul className="chips tight">
      {items.map((word, index) => (
        <li key={index} className="chip plain">{word}</li>
      ))}
    </ul>
  );
}

export default function Steps({ steps }) {
  const rows = [
    ["Texto normalizado", <code key="n">{steps.normalizado || "(vacío)"}</code>],
    ["Palabras", <Words key="t" items={steps.tokens} />],
    ["Stop words eliminadas", <Words key="s" items={steps.stopwords_eliminadas} />],
    [method[steps.metodo] ?? "Raíces", <Words key="r" items={steps.raices} />],
    ["Lo que recibe el modelo", <Words key="f" items={steps.final} />],
  ];
  return (
    <details className="disclosure">
      <summary>Cómo se procesó el texto</summary>
      <dl className="steps">
        {rows.map(([name, value]) => (
          <div key={name}>
            <dt>{name}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="muted small">
        Las groserías, la negación, los pronombres, los emojis y las mayúsculas se conservan a
        propósito: en este problema son la señal.
      </p>
    </details>
  );
}
