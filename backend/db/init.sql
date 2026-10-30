-- Se ejecuta la primera vez que el contenedor de PostgreSQL 
-- arranca con el volumen vacío.

-- Dataset crudo, (con textos vacíos y duplicados).
CREATE TABLE IF NOT EXISTS comentarios (
    id          TEXT PRIMARY KEY,
    texto       TEXT,
    etiqueta    TEXT NOT NULL CHECK (etiqueta IN ('NO', 'NOE', 'OFP', 'OFG')),
    plataforma  TEXT,
    influencer  TEXT,
    particion   TEXT,
    fuente      TEXT NOT NULL       -- 'offendes'
);

-- Guarda una fila por entrenamiento: qué se entrenó y qué tan bien le fue.
CREATE TABLE IF NOT EXISTS entrenamientos (
    id              SERIAL PRIMARY KEY,
    version         TEXT NOT NULL UNIQUE,
    fecha           TIMESTAMPTZ NOT NULL DEFAULT now(),
    modelo          TEXT NOT NULL,
    configuracion   JSONB NOT NULL,
    fuente_datos    TEXT NOT NULL,
    cv_f1_macro     DOUBLE PRECISION NOT NULL,
    test_f1_macro   DOUBLE PRECISION NOT NULL,
    test_accuracy   DOUBLE PRECISION NOT NULL,
    test_f1_ofensivo DOUBLE PRECISION NOT NULL,
    n_entrenamiento INTEGER NOT NULL,
    n_prueba        INTEGER NOT NULL
);

-- Guarda cada predicción que sirvió la API.
CREATE TABLE IF NOT EXISTS predicciones (
    id                  SERIAL PRIMARY KEY,
    fecha               TIMESTAMPTZ NOT NULL DEFAULT now(),
    texto               TEXT NOT NULL,
    clase               TEXT NOT NULL,
    ofensivo            BOOLEAN NOT NULL,
    probabilidad        DOUBLE PRECISION NOT NULL,
    probabilidad_ofensivo DOUBLE PRECISION NOT NULL,
    probabilidades      JSONB NOT NULL,
    version_modelo      TEXT NOT NULL,
    origen              TEXT NOT NULL CHECK (origen IN ('individual', 'lote'))
);

CREATE INDEX IF NOT EXISTS predicciones_fecha_idx ON predicciones (fecha DESC);
