// Estados comunes de una pantalla que pide datos: cargando y con error.
export function Loading({ what = "los datos" }) {
  return <p className="muted" role="status">Cargando {what}…</p>;
}

export function Problem({ error, onRetry }) {
  return (
    <div className="problem" role="alert">
      <p>{error.message}</p>
      {onRetry && (
        <button type="button" className="button secondary" onClick={onRetry}>Reintentar</button>
      )}
    </div>
  );
}
