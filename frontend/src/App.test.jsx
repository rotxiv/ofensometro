// Pruebas de la aplicación completa contra respuestas REALES de la API (src/test/*.json,
// generadas por el backend), con fetch simulado. Verifican el contrato entre ambos lados.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";
import batch from "./test/batch.json";
import health from "./test/health.json";
import labels from "./test/labels.json";
import metrics from "./test/metrics.json";
import clean from "./test/predict-clean.json";
import offensive from "./test/predict-offensive.json";

const json = (body, status = 200) =>
  Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) });

// Cada prueba puede sobrescribir lo que responde una ruta.
let routes;
beforeEach(() => {
  routes = {
    "GET /api/health": () => json(health),
    "GET /api/labels": () => json(labels),
    "GET /api/metrics": () => json(metrics),
    "POST /api/predict": () => json(offensive),
    "POST /api/predict/batch": () => json(batch),
    "GET /api/history": () => json({ error: "La base de datos no está configurada (DATABASE_URL).", detalles: [] }, 503),
    "GET /api/trainings": () => json({ error: "La base de datos no está configurada (DATABASE_URL).", detalles: [] }, 503),
  };
  vi.stubGlobal("fetch", vi.fn((url, options = {}) => {
    const key = `${options.method ?? "GET"} ${String(url).split("?")[0]}`;
    if (!routes[key]) throw new Error(`Ruta sin simular: ${key}`);
    return routes[key](url, options);
  }));
  window.location.hash = "";
});

async function open(page) {
  window.location.hash = `#/${page}`;
  render(<App />);
  await screen.findByRole("navigation", { name: "Secciones" });
}

describe("estructura", () => {
  it("avisa que el modelo es de demostración y marca la página actual", async () => {
    await open("analizar");
    expect(await screen.findByText(/Modelo de demostración/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Analizar" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Modelo" })).not.toHaveAttribute("aria-current");
  });

  it("explica qué hacer si la API no responde", async () => {
    routes["GET /api/labels"] = () => Promise.reject(new TypeError("fetch failed"));
    routes["GET /api/health"] = () => Promise.reject(new TypeError("fetch failed"));
    await open("analizar");
    const alerts = await screen.findAllByRole("alert");
    expect(alerts[0]).toHaveTextContent("No se pudo conectar con el servidor");
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});

describe("Analizar", () => {
  it("muestra el veredicto, marca las palabras y explica las señales", async () => {
    const user = userEvent.setup();
    await open("analizar");
    const box = await screen.findByRole("textbox", { name: "Comentario a revisar" });
    expect(screen.getByRole("button", { name: "Analizar" })).toBeDisabled();

    await user.type(box, "ERES UN 1di0ta, nadie te soporta 🤡");
    await user.click(screen.getByRole("button", { name: "Analizar" }));

    expect(await screen.findByRole("heading", { name: "Ofensivo" })).toBeInTheDocument();
    expect(screen.getByRole("meter")).toBeInTheDocument();

    // la palabra ofuscada se marca en el texto original, tal como la escribió la persona
    const marked = Array.from(document.querySelectorAll("mark")).map((m) => m.textContent);
    expect(marked).toContain("1di0ta");
    expect(marked).toContain("nadie");

    expect(screen.getByText(/Disfrazado: 1di0ta se leyó como idiota/)).toBeInTheDocument();
    expect(screen.getByText(/Emojis: 🤡/)).toBeInTheDocument();
    expect(screen.getByText(/Clase más probable: Ofensivo a una persona/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Editar texto" })).toBeInTheDocument();
  });

  it("un comentario amable sale como no ofensivo", async () => {
    routes["POST /api/predict"] = () => json(clean);
    const user = userEvent.setup();
    await open("analizar");
    await user.type(await screen.findByRole("textbox"), "Me encantó el video, saludos desde Bolivia");
    await user.click(screen.getByRole("button", { name: "Analizar" }));
    expect(await screen.findByRole("heading", { name: "No ofensivo" })).toBeInTheDocument();
  });

  it("envía el texto recortado a la API", async () => {
    const user = userEvent.setup();
    await open("analizar");
    await user.type(await screen.findByRole("textbox"), "   hola mundo   ");
    await user.click(screen.getByRole("button", { name: "Analizar" }));
    await screen.findByRole("heading", { name: "Ofensivo" });
    const call = fetch.mock.calls.find(([url]) => url === "/api/predict");
    expect(JSON.parse(call[1].body)).toEqual({ texto: "hola mundo" });
  });

  it("muestra el mensaje de error de la API tal cual", async () => {
    routes["POST /api/predict"] = () => json({ error: "El texto no contiene palabras.", detalles: [] }, 422);
    const user = userEvent.setup();
    await open("analizar");
    await user.type(await screen.findByRole("textbox"), "1234");
    await user.click(screen.getByRole("button", { name: "Analizar" }));
    expect(await screen.findByText("El texto no contiene palabras.")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeInTheDocument(); // se puede corregir y reintentar
  });

  it("un ejemplo se analiza con un solo clic", async () => {
    const user = userEvent.setup();
    await open("analizar");
    await user.click(await screen.findByRole("button", { name: /Todos los políticos/ }));
    expect(await screen.findByRole("heading", { name: "Ofensivo" })).toBeInTheDocument();
  });
});

describe("Archivo", () => {
  it("resume el lote, filtra y descarga", async () => {
    const user = userEvent.setup();
    await open("archivo");
    const file = new File(["Qué buen video\nEres un payaso\n"], "comentarios.txt", { type: "text/plain" });
    await user.upload(await screen.findByLabelText(/Elige un archivo/), file);

    expect(await screen.findByText(/2 de 3 comentarios son ofensivos/)).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Resultados por comentario" });
    expect(within(table).getAllByRole("row")).toHaveLength(1 + batch.resultados.length);

    await user.click(screen.getByRole("button", { name: "No ofensivos" }));
    expect(within(table).getAllByRole("row")).toHaveLength(1 + batch.resultados.filter((r) => !r.ofensivo).length);
    expect(screen.getByRole("button", { name: /Descargar resultados/ })).toBeInTheDocument();

    await user.click(screen.getByText("1 filas omitidas"));
    expect(screen.getByText(/Fila 4: El texto no contiene palabras./)).toBeInTheDocument();
  });

  it("muestra el motivo si el archivo no sirve", async () => {
    routes["POST /api/predict/batch"] = () => json({ error: "El CSV debe tener una columna llamada 'texto'.", detalles: [] }, 422);
    const user = userEvent.setup();
    await open("archivo");
    await user.upload(await screen.findByLabelText(/Elige un archivo/), new File(["a\n1"], "x.csv", { type: "text/csv" }));
    expect(await screen.findByText(/columna llamada 'texto'/)).toBeInTheDocument();
  });
});

describe("Archivo grande", () => {
  it("traduce el 413 de nginx, que llega sin JSON", async () => {
    routes["POST /api/predict/batch"] = () =>
      Promise.resolve({ ok: false, status: 413, json: () => Promise.reject(new SyntaxError("no es JSON")) });
    const user = userEvent.setup();
    await open("archivo");
    await user.upload(await screen.findByLabelText(/Elige un archivo/), new File(["x"], "grande.txt", { type: "text/plain" }));
    expect(await screen.findByText("El archivo es demasiado grande. El máximo es 1 MB.")).toBeInTheDocument();
  });
});

describe("Modelo y Datos", () => {
  it("compara los modelos y marca el que está en producción", async () => {
    await open("modelo");
    const table = await screen.findByRole("table", { name: "Comparación de modelos" });
    expect(within(table).getByText("en producción")).toBeInTheDocument();
    expect(within(table).getByText(/Línea base/)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /Cuatro clases/ })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /Vista binaria/ })).toBeInTheDocument();
  });

  it("oculta el contenido ofensivo hasta que la persona lo pide", async () => {
    const user = userEvent.setup();
    await open("modelo");
    await screen.findByRole("table", { name: "Comparación de modelos" });
    expect(screen.queryByRole("table", { name: "Errores del modelo" })).not.toBeInTheDocument();
    const gate = screen.getByRole("heading", { name: "Errores con más seguridad" }).closest("section");
    await user.click(within(gate).getByRole("button", { name: "Mostrar contenido ofensivo" }));
    expect(screen.getByRole("table", { name: "Errores del modelo" })).toBeInTheDocument();
    await user.click(within(gate).getByRole("button", { name: "Ocultar contenido ofensivo" }));
    expect(screen.queryByRole("table", { name: "Errores del modelo" })).not.toBeInTheDocument();
  });

  it("Datos muestra las clases y lo que se limpió", async () => {
    await open("datos");
    expect(await screen.findByRole("heading", { name: "Cuántos hay de cada clase" })).toBeInTheDocument();
    expect(screen.getByText(/Textos duplicados/)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Comentarios por clase y conjunto" })).toBeInTheDocument();
  });
});

describe("Historial", () => {
  it("sin base de datos explica por qué y deja reintentar", async () => {
    await open("historial");
    await waitFor(() => expect(screen.getAllByText(/base de datos no está configurada/)).toHaveLength(2));
    expect(screen.getAllByRole("button", { name: "Reintentar" }).length).toBeGreaterThan(0);
  });

  it("lista las predicciones guardadas", async () => {
    routes["GET /api/history"] = () => json([
      { id: 1, fecha: "2026-10-30T12:00:00Z", texto: "Eres un payaso", clase: "OFP", ofensivo: true,
        probabilidad: 0.9, probabilidad_ofensivo: 0.95, version_modelo: "v1", origen: "individual" },
    ]);
    routes["GET /api/trainings"] = () => json([]);
    await open("historial");
    expect(await screen.findByText("Eres un payaso")).toBeInTheDocument();
    expect(screen.getByText("Todavía no hay entrenamientos registrados.")).toBeInTheDocument();
  });
});
