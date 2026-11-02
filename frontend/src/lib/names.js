// Nombres que entiende una persona para lo que en el modelo son identificadores.

export const NORMALIZERS = { stem: "Raíz (stemming)", lemma: "Lema (spaCy)", "-": "—" };
export const STOPWORD_LISTS = {
  spacy_full: "Lista completa de spaCy",
  adjusted: "Lista ajustada al dominio",
  "-": "—",
};
export const NGRAMS = { "1-1": "Palabras sueltas", "1-2": "Palabras y pares", "-": "—" };
export const STAGES = { cribado: "Cribado", ajuste: "Ajuste", "línea base": "Línea base" };
export const MODELS = {
  complement_nb: "Naive Bayes complementario",
  logistic_regression: "Regresión logística",
  baseline: "Línea base",
};
export const FACTORS = {
  normalizer: ["Raíz o lema", NORMALIZERS],
  stopword_list: ["Stop words", STOPWORD_LISTS],
  ngram_range: ["Palabras sueltas o pares", NGRAMS],
  model: ["Modelo", MODELS],
};

export function hyperparameters(object) {
  const entries = Object.entries(object ?? {});
  if (entries.length === 0) return "valores por defecto";
  return entries.map(([k, v]) => `${k} = ${v === null ? "ninguno" : v}`).join(", ");
}
