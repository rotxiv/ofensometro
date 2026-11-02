import { useState } from "react";

// El contenido ofensivo real (palabras frecuentes, ejemplos de errores) no se muestra
// hasta que la persona decide verlo.
export default function ContentGate({ title, children }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="gate">
      <h3>{title}</h3>
      {open ? (
        <>
          {children}
          <button type="button" className="button quiet" onClick={() => setOpen(false)}>
            Ocultar contenido ofensivo
          </button>
        </>
      ) : (
        <div className="gate-closed">
          <p>
            Esta sección reproduce lenguaje ofensivo real tomado de los datos, incluso contra personas
            y grupos.
          </p>
          <button type="button" className="button secondary" onClick={() => setOpen(true)}>
            Mostrar contenido ofensivo
          </button>
        </div>
      )}
    </section>
  );
}
