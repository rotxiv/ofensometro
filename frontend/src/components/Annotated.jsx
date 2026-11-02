import { useMemo } from "react";
import { segment } from "../lib/highlight.js";

// El comentario con las palabras influyentes marcadas, como con un marcador de editor.
export default function Annotated({ text, terms, obfuscated }) {
  const parts = useMemo(() => segment(text, terms, obfuscated), [text, terms, obfuscated]);
  let order = 0;
  return (
    <p className="annotated sheet-text" lang="es">
      {parts.map((part, index) =>
        part.level === null ? (
          <span key={index}>{part.text}</span>
        ) : (
          <mark key={index} style={{ "--level": part.level.toFixed(2), "--order": order++ }}
                title="Pesó en la decisión">
            {part.text}
          </mark>
        ),
      )}
    </p>
  );
}
