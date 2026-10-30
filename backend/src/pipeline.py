"""Un comando, de los datos crudos a los modelos guardados.

    python -m src.pipeline                          # entrena con los datos reales
    python -m src.pipeline --reload-data            # vuelve a cargar el CSV en PostgreSQL

Etapas: elegir el CSV -> sincronizar la base (si hay) -> entrenar (src.models.train).
"""

import sys
import argparse

from pathlib import Path

import pandas as pd

from src import db
from src.models import train
from src.config import MODEL_PATH, ROOT, load_params

NO_DATA_MESSAGE = """\
No encuentro los datos reales: {path}

  1. Descarga OffendES (ver data/README.md) y déjalo en {external}/
  2. Ejecuta:  python -m src.data.ingest
  3. Vuelve a ejecutar:  python -m src.pipeline
"""

def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-if-trained", action="store_true",
                        help="termina sin hacer nada si ya existe artifacts/model.joblib")
    parser.add_argument("--reload-data", action="store_true",
                        help="reemplaza la tabla de comentarios con el CSV")
    return parser.parse_args(argv)

def choose_dataset(params: dict) -> Path:
    """Carga el CSV que se va a usar."""
    real = ROOT / params["data"]["raw_path"]
    if not real.exists():
        sys.exit(NO_DATA_MESSAGE.format(path=real, external=params["data"]["external_dir"]))
    print(f"[1/3] Datos crudos: {real}")
    return real

def sync_database(csv_path: Path, force: bool) -> None:
    """
    Carga el CSV en PostgreSQL si hace falta: base vacía, otro origen de datos o --reload-data.
    """
    repository = db.get_repository()
    if repository is None:
        print("[2/3] Sin DATABASE_URL: se entrena directamente desde el CSV")
        return
    frame = pd.read_csv(csv_path, dtype={"id": str})
    different_source = repository.comment_sources() != set(frame["fuente"].unique())
    if force or different_source or repository.comment_count() == 0:
        repository.replace_comments(frame)
        print(f"[2/3] {len(frame)} comentarios cargados en PostgreSQL")
    else:
        print(f"[2/3] PostgreSQL ya tiene {repository.comment_count()} comentarios")

def main() -> None:
    """Pipeline de entrenamiento del modelo ofensometro."""
    args = parse_args()
    params = load_params()
    if args.skip_if_trained and MODEL_PATH.exists():
        print(f"Ya existe {MODEL_PATH}; no se reentrena "
              "(fuerza el reentrenamiento con: python -m src.pipeline)")
        return
    csv_path = choose_dataset(params)
    sync_database(csv_path, args.reload_data)
    print("[3/3] Entrenando")
    train.main(csv_path)

if __name__ == "__main__":
    main()
