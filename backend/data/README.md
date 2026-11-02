# Datos

## Origen: OffendES

| | |
|---|---|
| Nombre | OffendES: A New Corpus in Spanish for Offensive Language Research |
| Autores | Plaza-del-Arco, Montejo-Ráez, Ureña-López, Martín-Valdivia (SINAI, Universidad de Jaén) |
| Qué es | Comentarios en español de Twitter, Instagram y YouTube dirigidos a *influencers* jóvenes, etiquetados por anotadores humanos (Amazon Mechanical Turk). Es el corpus de la tarea MeOffendES de IberLEF 2021. |
| Dónde | https://huggingface.co/datasets/SINAI/OffendES |
| Artículo | https://aclanthology.org/2021.ranlp-1.123.pdf |
| Tamaño | 30.416 comentarios públicos: train 16.710, validation 100, test 13.606 |

### Clases

| Código | Nombre | Significado | En la vista binaria |
|---|---|---|---|
| `NO` | No ofensivo | Sin ofensas ni palabras fuertes | no ofensivo |
| `NOE` | No ofensivo con groserías | Palabras fuertes **sin** intención de ofender (suele ser positivo) | no ofensivo |
| `OFP` | Ofensivo a una persona | Ofensa a un individuo concreto | **ofensivo** |
| `OFG` | Ofensivo a un grupo | Ofensa a un colectivo (etnia, género, ideología, religión...) | **ofensivo** |

Conteo por partición (de la ficha del dataset):

| Clase | Train | Validation | Test |
|---|---|---|---|
| NO | 13.212 | 64 | 9.651 |
| NOE | 1.235 | 22 | 2.340 |
| OFP | 2.051 | 10 | 1.404 |
| OFG | 212 | 4 | 211 |

Dos cosas saltan a la vista y hay que tratarlas en con mucha atención: el **desbalance** (OFG es ~1 % del
entrenamiento) y que la **validación oficial tiene solo 100 filas**, así que no sirve para ajustar.
Por eso el proyecto ajusta con validación cruzada sobre el entrenamiento. Además, la distribución
del test oficial no es igual a la del train (por ejemplo, NO es 79 % en train y 71 % en test).

## Cómo conseguir los datos

El acceso está condicionado: hay que iniciar sesión en Hugging Face y aceptar compartir tu
información de contacto con los autores.

1. Crea una cuenta en https://huggingface.co e inicia sesión.
2. Abre https://huggingface.co/datasets/SINAI/OffendES y acepta las condiciones.
3. En la pestaña **Files and versions** descarga los archivos de train, validation y test.
4. Colócalos en `data/external/offendes/`. El nombre debe contener `train`, `val` o `test`
   (así se asigna la partición).
5. Convierte al formato del proyecto:

```bash
python -m src.data.ingest          # o: make ingest
```

Esto crea `data/raw/comentarios.csv`. Si tus archivos traen otros nombres de columna o un
separador raro, cámbialos en `params.yaml` → `data.source`.

> **Licencia: verifica antes de publicar.** La ficha del dataset muestra dos licencias que no
> coinciden (`cc-by-nc-sa-4.0` en los metadatos y Apache-2.0 en el texto). Hasta aclararlo, úsalo
> solo con fines académicos y no comerciales, **no subas los archivos al repositorio** (ya están en
> `.gitignore`) y cita a los autores.

## Formato del proyecto: `data/raw/comentarios.csv`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | texto | `<partición>-<comment_id>`; único aunque el id original se repita entre particiones |
| `texto` | texto | El comentario, tal como llegó |
| `etiqueta` | texto | `NO`, `NOE`, `OFP` u `OFG` |
| `plataforma` | texto | `twitter`, `instagram` o `youtube` |
| `influencer` | texto | A quién iba dirigido el comentario |
| `particion` | texto | `train`, `validation` o `test` (la original) |
| `fuente` | texto | `offendes` (real) o `sintetico` (demostración) |

El CSV **crudo** conserva textos vacíos y duplicados; la limpieza ocurre en el entrenamiento
(`src/data/prepare.py`) y queda registrada en `metrics.json → dataset.cleaning`.

## Privacidad y contenido

- El corpus contiene lenguaje **ofensivo real**, incluido contra personas y grupos. `metrics.json`
  (palabras frecuentes por clase, ejemplos de errores) lo reproduce: las apps deben mostrarlo tras
  un aviso.
- La API guarda en PostgreSQL los textos que le envían los usuarios (tabla `predicciones`). Si la
  app se usa con personas reales, avisa de ello y define cuánto tiempo se conservan.
