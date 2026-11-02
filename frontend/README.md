# Ofensómetro: (frontend)

Aplicación web del detector de lenguaje ofensivo. Es un proyecto independiente: React 19 + Vite, en
JavaScript, sin librerías de componentes ni de gráficos (solo React y las fuentes). Se comunica con
la API del backend únicamente por HTTP, a través de la ruta `/api`.

| Pantalla | Qué hace | Endpoint que usa |
|---|---|---|
| Analizar | Clasifica un comentario y marca las palabras que pesaron | `POST /api/predict` |
| Archivo | Clasifica un `.txt` o `.csv` y descarga los resultados | `POST /api/predict/batch` |
| Modelo | Comparación de modelos, matrices de confusión, errores | `GET /api/metrics` |
| Datos | Clases, limpieza, longitudes, palabras frecuentes | `GET /api/metrics` |
| Historial | Predicciones y entrenamientos guardados | `GET /api/history`, `GET /api/trainings` |

Además, en todas las pantallas: `GET /api/health` (aviso de modelo de demostración) y
`GET /api/labels` (nombres de las clases).

## Cómo se conecta con la API

El navegador **siempre** llama a rutas relativas (`/api/...`), nunca a la dirección de la API. Quién
atiende esa ruta depende de cómo lo ejecutes:

```text
npm run dev / preview   navegador -> Vite  -> API   (la dirección sale de VITE_API_TARGET)
Docker                  navegador -> nginx -> API   (la dirección sale de API_UPSTREAM)
```

Así el navegador habla con un solo origen y **no hace falta CORS**.

| Variable | Se usa en | Por defecto | Para qué |
|---|---|---|---|
| `VITE_API_TARGET` | `npm run dev`, `npm run preview` | `http://127.0.0.1:8000` | Dónde está la API |
| `API_UPSTREAM` | Docker (nginx) | `http://host.docker.internal:8000` | Dónde está la API, vista desde el contenedor. **Sin barra final** |
| `WEB_PORT` | Docker Compose | `8080` | Puerto donde se publica la web |

Se pueden definir en el entorno o en un archivo `.env` (copia `.env.example`). Una variable del
entorno gana sobre el `.env`.

## Requisitos

- Node.js **22.22 o superior** (`.nvmrc` incluido) y npm. Las herramientas de pruebas (`vitest`,
  `jsdom`) piden esa versión; con Node más viejo `npm install` avisa y las pruebas pueden fallar.
- Una API del backend en marcha (para usar la aplicación; no hace falta para las pruebas ni el build).
- Docker es opcional.

## Sin Docker

```bash
npm install
npm run dev          # http://localhost:5173  (recarga al guardar)
```

La API debe estar en `http://127.0.0.1:8000`. Si está en otro lugar:

```bash
VITE_API_TARGET=http://otro-host:8000 npm run dev
# o escribe VITE_API_TARGET en un archivo .env
```

Para comprobar el build de producción:

```bash
npm run build        # genera dist/
npm run preview      # http://localhost:4173, con la misma conexión a la API
```

`npm run preview` sirve para revisar el build, no para producción. Para publicar sin Docker, sirve
`dist/` con cualquier servidor web que **reenvíe `/api` a la API** (la configuración de
`nginx.conf.template` es un ejemplo).

```bash
npm test             # 27 pruebas, no necesitan la API
```

## Con Docker

Solo el frontend (necesita una API accesible):

```bash
docker compose up --build        # http://localhost:8080
```

Por defecto busca la API en el equipo anfitrión, en el puerto 8000 (`host.docker.internal`; en Linux
el compose ya lo configura con `extra_hosts`). Para otra dirección:

```bash
API_UPSTREAM=http://192.168.1.20:8000 docker compose up --build
```

Sin Compose:

```bash
docker build -t ofensometro-web .
docker run --rm -p 8080:80 -e API_UPSTREAM=http://host.docker.internal:8000 ofensometro-web
```

`API_UPSTREAM` se lee **al arrancar el contenedor**, no al construir la imagen: la misma imagen sirve
para cualquier entorno. nginx la aplica a la plantilla `nginx.conf.template`.

### Con el backend en un mismo compose

Cuando uses un `docker-compose.yml` que tenga la API y la web juntas, añade este servicio (ajusta el
nombre `api` al del servicio de tu backend y la ruta de `build`):

```yaml
  web:
    build: ./frontend
    environment:
      API_UPSTREAM: http://api:8000      # nombre del servicio de la API, sin barra final
    ports:
      - "8080:80"
    depends_on:
      api:
        condition: service_healthy       # nginx necesita que el nombre `api` exista al arrancar
```

### Si algo falla en Docker

| Síntoma | Causa y solución |
|---|---|
| El contenedor se detiene con `host not found in upstream "..."` | El nombre de `API_UPSTREAM` no existe en esa red. Revisa el nombre del servicio, o usa `host.docker.internal` |
| La web carga pero todo da 404 en `/api` | `API_UPSTREAM` termina en `/`. Quita la barra final |
| La web carga pero todo da 502 | La API no está en marcha o no es alcanzable desde el contenedor. Con la API en el equipo, que escuche en `0.0.0.0` o esté publicada por Docker |
| Un archivo grande da error 413 | nginx corta lo que supera 2 MB; la API acepta hasta 1 MB. Es lo esperado |

## Qué espera de la API

Los campos que usa la interfaz, tal como los devuelve el backend:

- `POST /api/predict`: `ofensivo`, `probabilidad_ofensivo`, `umbral`, `clase`, `nombre_clase`,
  `descripcion`, `probabilidades`, `explicacion.ofensivo[].{palabra, peso}`,
  `preprocesamiento.{...}`, `preprocesamiento.senales.{mayusculas, ofuscadas, emojis, risas}`,
  `modelo`, `tiempo_ms`.
- Errores: JSON `{"error": "mensaje"}`; el mensaje se muestra tal cual.
- `GET /api/health`: `modelo_cargado`, `modo_demo`, `modelo`, `version`, `datos`.

Las pruebas usan respuestas reales de la API guardadas en `src/test/*.json`. Si el backend cambia
sus respuestas, esas copias deben actualizarse (y las pruebas avisarán si el contrato se rompió).

## Estructura

```text
frontend/
├── package.json · package-lock.json · .nvmrc
├── vite.config.js            # proxy de /api en desarrollo y en preview
├── nginx.conf.template       # proxy de /api en Docker (usa API_UPSTREAM)
├── Dockerfile · docker-compose.yml · .env.example
└── src/
    ├── api.js                # cliente de la API y manejo de errores
    ├── App.jsx               # cabecera, avisos y navegación por # (#/modelo)
    ├── pages/                # Analizar · Archivo · Modelo · Datos · Historial
    ├── components/           # Annotated (texto marcado), Meter, ClassBars, ConfusionMatrix...
    ├── lib/                  # funciones puras: highlight, csv, format, names
    ├── hooks/useRequest.js
    ├── test/                 # respuestas reales de la API (fixtures)
    └── styles.css
```

## Scripts

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo con recarga (puerto 5173) |
| `npm run build` | Compila a `dist/` |
| `npm run preview` | Sirve `dist/` para revisarlo (puerto 4173) |
| `npm test` | Pruebas (Vitest + Testing Library) |

## Problemas habituales

| Situación | Qué hacer |
|---|---|
| La web dice «No se pudo conectar con el servidor» | La API no está en marcha, o todavía arranca (carga spaCy y tarda unos segundos): espera y pulsa Reintentar |
| `npm run dev` abre, pero `/api` da error | Revisa `VITE_API_TARGET` y que la API responda en esa dirección |
| El puerto 5173 está ocupado | Vite elige el siguiente (5174...) y lo muestra en la terminal |
| `npm install` advierte `EBADENGINE` | Tu Node es anterior a 22.22: actualízalo (`nvm use` lee `.nvmrc`) |
