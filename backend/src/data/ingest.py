"""Convierte los archivos originales de OffendES en el CSV que usa el proyecto.

    python -m src.data.ingest                       # lee data/external/offendes/
    python -m src.data.ingest --input otra/carpeta

Salida (data.raw_path): id, texto, etiqueta, plataforma, influencer, particion, fuente.
"""

import argparse
from pathlib import Path

import pandas as pd

from src.config import ROOT, labels, load_params

EXTENSIONS = {".csv", ".tsv", ".txt"}
OUTPUT_COLUMNS = ["id", "texto", "etiqueta", "plataforma", "influencer", "particion", "fuente"]


def partition_of(path: Path) -> str:
    name = path.stem.lower()
    if "test" in name:
        return "test"
    if "val" in name or "dev" in name:
        return "validation"
    if "train" in name:
        return "train"
    return "sin_particion"

def read_file(path: Path, separator: str | None) -> pd.DataFrame:
    """Lee un CSV/TSV. Con separator=None pandas detecta coma, tabulador o punto y coma."""
    return pd.read_csv(path, sep=separator, engine="python", dtype=str,
                       encoding="utf-8-sig", keep_default_na=False)

def ingest(files: list[Path], source: dict) -> tuple[pd.DataFrame, dict]:
    if not files:
        raise FileNotFoundError("No hay archivos .csv/.tsv para convertir.")
    columns = source["columns"]
    frames, report = [], {"archivos": {}, "sin_etiqueta": 0}
    for path in files:
        raw = read_file(path, source.get("separator"))
        missing = [c for c in (columns["id"], columns["texto"], columns["etiqueta"])
                   if c not in raw.columns]
        if missing:
            raise ValueError(
                f"{path.name}: faltan las columnas {missing}. Columnas encontradas: "
                f"{list(raw.columns)}. Ajusta data.source.columns en params.yaml.")
        part = partition_of(path)
        df = pd.DataFrame({
            "id": part + "-" + raw[columns["id"]].str.strip(),
            "texto": raw[columns["texto"]],
            "etiqueta": raw[columns["etiqueta"]].str.strip().str.upper(),
            "plataforma": raw[columns["plataforma"]].str.strip().str.lower()
                          if columns["plataforma"] in raw.columns else "desconocida",
            "influencer": raw[columns["influencer"]].str.strip()
                          if columns["influencer"] in raw.columns else "desconocido",
            "particion": part,
            "fuente": "offendes",
        })
        no_label = df["etiqueta"].eq("")
        report["sin_etiqueta"] += int(no_label.sum())
        df = df[~no_label]
        unknown = sorted(set(df["etiqueta"]) - set(labels()))
        if unknown:
            raise ValueError(f"{path.name}: etiquetas desconocidas {unknown}; "
                             f"se esperaban {labels()}.")
        report["archivos"][path.name] = {"particion": part, "filas": len(df)}
        frames.append(df)
    return pd.concat(frames, ignore_index=True)[OUTPUT_COLUMNS], report

def main() -> None:
    params = load_params()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=ROOT / params["data"]["external_dir"])
    parser.add_argument("--output", type=Path, default=ROOT / params["data"]["raw_path"])
    args = parser.parse_args()

    files = sorted(p for p in args.input.glob("*") if p.suffix.lower() in EXTENSIONS) \
        if args.input.is_dir() else [args.input]
    if not files:
        raise SystemExit(f"No encontré archivos en {args.input}.\n"
                         "Descarga OffendES (ver data/README.md) y colócalos ahí.")
    df, report = ingest(files, params["data"]["source"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    print(f"{len(df)} comentarios escritos en {args.output}")
    for name, info in report["archivos"].items():
        print(f"  {name:<28} {info['particion']:<13} {info['filas']:>6} filas")
    if report["sin_etiqueta"]:
        print(f"  {report['sin_etiqueta']} filas sin etiqueta se omitieron "
              "(p. ej. un test sin etiquetas públicas).")
    print("Distribución:", df["etiqueta"].value_counts().to_dict())

if __name__ == "__main__":
    main()
