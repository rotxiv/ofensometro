import { describe, expect, it } from "vitest";
import { toCsv } from "./csv.js";
import { percent } from "./format.js";
import { fold, segment } from "./highlight.js";

const marked = (segments) => segments.filter((s) => s.level !== null).map((s) => s.text);

describe("segment", () => {
  const terms = [{ palabra: "idiota", peso: 0.8 }, { palabra: "nadie", peso: 0.4 }];

  it("marca las palabras influyentes sin perder ni cambiar el texto", () => {
    const text = "Eres un idiota, nadie te soporta";
    const parts = segment(text, terms);
    expect(parts.map((p) => p.text).join("")).toBe(text);
    expect(marked(parts)).toEqual(["idiota", "nadie"]);
  });

  it("escala la intensidad: 1 para la palabra que más pesó", () => {
    const parts = segment("idiota y nadie", terms);
    expect(parts.find((p) => p.text === "idiota").level).toBe(1);
    expect(parts.find((p) => p.text === "nadie").level).toBeCloseTo(0.5);
  });

  it("ignora mayúsculas y tildes", () => {
    expect(marked(segment("IDIÓTA", [{ palabra: "idiota", peso: 1 }]))).toEqual(["IDIÓTA"]);
  });

  it("encuentra palabras ofuscadas aunque la API anote la puntuación pegada", () => {
    const obfuscated = [{ original: "1di0ta,", normal: "idiota," }];
    expect(marked(segment("Qué 1di0ta, eres", terms, obfuscated))).toEqual(["1di0ta"]);
  });

  it("encuentra alargamientos y censura con asteriscos", () => {
    expect(marked(segment("idiotaaaa", terms))).toEqual(["idiotaaaa"]);
    expect(marked(segment("p*ta madre", [{ palabra: "pta", peso: 1 }]))).toEqual(["p*ta"]);
  });

  it("marca cada palabra de un par", () => {
    expect(marked(segment("eres idiota", [{ palabra: "eres idiota", peso: 1 }]))).toEqual(["eres", "idiota"]);
  });

  it("no intenta marcar señales como (mayúsculas) ni se rompe sin términos", () => {
    expect(marked(segment("HOLA", [{ palabra: "(mayúsculas)", peso: 1 }]))).toEqual([]);
    expect(segment("hola", []).every((s) => s.level === null)).toBe(true);
  });

  it("conserva emojis y saltos de línea", () => {
    const text = "idiota 🤡\nfin";
    expect(segment(text, terms).map((s) => s.text).join("")).toBe(text);
  });
});

describe("fold", () => {
  it("quita tildes y pasa a minúsculas", () => {
    expect(fold("INÚTIL")).toBe("inutil");
  });
});

describe("toCsv", () => {
  const columns = [{ title: "texto", value: (r) => r.t }, { title: "clase", value: (r) => r.c }];

  it("escapa comillas, comas y saltos de línea", () => {
    const csv = toCsv([{ t: 'dijo "hola", y se fue\nya', c: "NO" }], columns);
    expect(csv).toContain('"dijo ""hola"", y se fue\nya",NO');
  });

  it("empieza con BOM para que Excel lea UTF-8 y trae el encabezado", () => {
    expect(toCsv([], columns)).toBe("\uFEFFtexto,clase");
  });
});

describe("percent", () => {
  it("formatea en español", () => {
    expect(percent(0.935)).toMatch(/93,5\s%/);
    expect(percent(null)).toBe("—");
  });
});
