// Cliente de la API. Todas las rutas son relativas a /api: en desarrollo las reenvía Vite
// y en Docker las reenvía nginx, así que el navegador nunca habla con otro origen (sin CORS).

const BASE = "/api";

export class ApiProblem extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(BASE + path, options);
  } catch {
    throw new ApiProblem("No se pudo conectar con el servidor. Comprueba que la API esté en marcha.");
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    /* respuesta sin cuerpo JSON */
  }
  if (!response.ok) {
    // nginx corta los cuerpos demasiado grandes con su propia página (sin JSON): se traduce.
    const tooLarge = "El archivo es demasiado grande. El máximo es 1 MB.";
    const fallback = response.status === 413 ? tooLarge : `El servidor respondió con el error ${response.status}.`;
    throw new ApiProblem(body?.error ?? fallback, response.status);
  }
  return body;
}

export const api = {
  health: () => request("/health"),
  labels: () => request("/labels"),
  metrics: () => request("/metrics"),
  history: (limit = 30) => request(`/history?limit=${limit}`),
  trainings: () => request("/trainings"),
  predict: (texto) =>
    request("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto }),
    }),
  batch: (file) => {
    const form = new FormData();
    form.append("archivo", file);
    return request("/predict/batch", { method: "POST", body: form });
  },
};
