import { createContext, useContext } from "react";

// Lo que casi todas las pantallas necesitan: las clases (nombre, descripción, si ofenden).
export const AppContext = createContext({ labels: [] });

export function useApp() {
  const { labels } = useContext(AppContext);
  const byCode = Object.fromEntries(labels.map((l) => [l.codigo, l]));
  return { labels, byCode };
}
