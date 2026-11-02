// Marca, dentro del texto ORIGINAL del usuario, las palabras que el modelo consideró influyentes.
//
// La API devuelve las palabras ya normalizadas (minúsculas, ofuscación revertida...), así que
// hay que volver a emparejarlas con lo que la persona escribió: "1di0ta," -> "idiota".

const WORD = /[\p{L}\p{N}@*_]+/gu;
const EDGES = /^[^\p{L}\p{N}@*_]+|[^\p{L}\p{N}@*_]+$/gu;

export function fold(text) {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

// Las variantes con las que una palabra escrita puede coincidir con la del modelo:
// tal cual, sin alargamientos ("idiotaaaa") y sin asteriscos de censura ("p*ta").
function variants(word) {
  const base = fold(word);
  const stretched = base.replace(/(.)\1{2,}/gu, "$1");
  return [...new Set([base, stretched, base.replace(/\*+/g, ""), stretched.replace(/\*+/g, "")])];
}

function weightsByWord(terms) {
  const weights = new Map();
  for (const { palabra, peso } of terms) {
    if (palabra.startsWith("(")) continue; // señales como "(mayúsculas)": no son palabras del texto
    for (const part of palabra.split(" ")) {
      const key = fold(part);
      weights.set(key, Math.max(weights.get(key) ?? 0, peso));
    }
  }
  return weights;
}

function restoredWords(obfuscated) {
  // La API anota «1di0ta,» con su puntuación pegada; se limpian ambos lados.
  const map = new Map();
  for (const { original, normal } of obfuscated) {
    map.set(fold(original.replace(EDGES, "")), fold(normal.replace(EDGES, "")));
  }
  return map;
}

/**
 * Parte el texto en tramos: [{ text, level }].
 * level es null en el texto normal, y un valor en (0, 1] en las palabras marcadas
 * (1 = la palabra que más pesó).
 */
export function segment(text, terms, obfuscated = []) {
  const weights = weightsByWord(terms);
  const restored = restoredWords(obfuscated);
  const strongest = Math.max(0, ...weights.values());
  const segments = [];
  let cursor = 0;

  for (const match of text.matchAll(WORD)) {
    const [word] = match;
    if (match.index > cursor) segments.push({ text: text.slice(cursor, match.index), level: null });

    const keys = variants(word).map((v) => restored.get(v) ?? v);
    const found = keys.map((k) => weights.get(k)).find((w) => w !== undefined);
    segments.push({ text: word, level: found !== undefined && strongest > 0 ? found / strongest : null });
    cursor = match.index + word.length;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), level: null });
  return segments;
}
