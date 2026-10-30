"""
Entrena, compara y guarda los modelos.
    python -m src.models.train
Lee los comentarios de PostgreSQL si hay DATABASE_URL; si no, del CSV. Escribe en artifacts/:
model.joblib, metrics.json, experiments.csv y errors.csv (ver artifacts.py).
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src import db
from src.config import ARTIFACTS_DIR, ROOT, labels, load_params
from src.data.prepare import clean, describe, split
from src.models.artifacts import save_artifacts
from src.models.evaluate import (binary_metrics, classification_metrics, error_table,
                                 probabilities_by_label)
from src.models.experiments import (MODEL_LABELS, build_pipeline, make_model, row_to_config,
                                    run_experiments)
from src.models.report import ModelResult, build_report


def load_raw(params: dict, csv_path: Path | None = None) -> tuple[pd.DataFrame, str]:
    repository = db.get_repository()
    if repository is not None:
        return repository.load_comments(), "postgresql"
    return pd.read_csv(csv_path or ROOT / params["data"]["raw_path"]), "csv"

def fit_and_test(name: str, experiments: pd.DataFrame, train_df: pd.DataFrame,
                 test_df: pd.DataFrame, params: dict) -> ModelResult:
    """Entrena el modelo con su mejor fila de experimentos y lo prueba con el conjunto apartado."""
    best = experiments[experiments["model"] == name].iloc[0]
    if name == "baseline":
        config = {"model": "baseline", "hyperparameters": best["hyperparameters"]}
        pipeline = make_model("baseline", params["seed"])
    else:
        config = row_to_config(best)
        pipeline = build_pipeline(config, params)
    pipeline.fit(train_df["texto"], train_df["etiqueta"])

    proba = probabilities_by_label(pipeline, test_df["texto"])
    predicted = [labels()[i] for i in proba.argmax(axis=1)]
    return ModelResult(
        name=name, label=MODEL_LABELS[name], config=config,
        cv_f1_macro=float(best["cv_f1_macro"]), cv_f1_macro_std=float(best["cv_f1_macro_std"]),
        test=classification_metrics(test_df["etiqueta"], predicted),
        test_binary=binary_metrics(test_df["etiqueta"], proba,
                                   params["decision"]["umbral_ofensivo"]),
        pipeline=pipeline,
    )

def choose_production(results: list[ModelResult]) -> ModelResult:
    """El de mayor F1 de validación cruzada. Se decide con la validación cruzada, no con la
    prueba, para no ajustar el modelo mirando el examen final."""
    contenders = [r for r in results if r.name != "baseline"]
    return max(contenders, key=lambda r: r.cv_f1_macro)

def train(raw: pd.DataFrame, params: dict, artifacts_dir: Path | None = None) -> dict:
    clean_df, cleaning = clean(raw)
    eda = describe(clean_df, tuple(params["nlp"]["keep_words"]),
                   tuple(params["nlp"]["extra_stopwords"]))
    train_df, test_df = split(clean_df, params)
    print(f"Entrenamiento: {len(train_df)} | prueba: {len(test_df)}")

    print("Validación cruzada de las configuraciones...")
    experiments = run_experiments(train_df["texto"], train_df["etiqueta"], params)

    # Recién ahora se abre el conjunto de prueba, una sola vez.
    model_names = [*params["experiments"]["models"], "baseline"]
    results = [fit_and_test(name, experiments, train_df, test_df, params)
               for name in model_names]
    production = choose_production(results)

    mistakes_table = error_table(production.pipeline, test_df,
                                 params["decision"]["umbral_ofensivo"])
    now = datetime.now(timezone.utc)
    report = build_report(
        version=now.strftime("%Y%m%d-%H%M%S"), trained_at=now.isoformat(timespec="seconds"),
        params=params, raw=raw, cleaning=cleaning, eda=eda, train_df=train_df, test_df=test_df,
        results=results, production=production, experiments=experiments,
        error_table=mistakes_table,
    )
    save_artifacts(artifacts_dir or ARTIFACTS_DIR, production=production, report=report,
                   experiments=experiments, error_table=mistakes_table)
    _print_summary(experiments, results, production, report["demo_mode"])
    return report

def _print_summary(experiments: pd.DataFrame, results: list[ModelResult],
                   production: ModelResult, demo: bool) -> None:
    if demo:
        print("\n*** DATOS SINTÉTICOS: modelo de demostración, no reportar estos resultados ***")
    print("\nMejores configuraciones (validación cruzada, F1 macro):")
    shown = ["stage", "model", "normalizer", "stopword_list", "ngram_range",
             "cv_f1_macro", "cv_f1_macro_std"]
    print(experiments.head(8)[shown].to_string(index=False))
    print("\nConjunto de prueba (4 clases | vista binaria ofensivo):")
    for r in results:
        print(f"  {r.label:<46} acc={r.test['accuracy']:.3f}  F1macro={r.test['f1_macro']:.3f}"
              f" | F1 ofensivo={r.test_binary['offensive']['f1']:.3f}")
    print(f"\nEn producción: {production.label} {production.config}")


def main(csv_path: Path | None = None) -> None:
    params = load_params()
    raw, source = load_raw(params, csv_path)
    print(f"{len(raw)} comentarios leídos desde {source}")
    report = train(raw, params)

    repository = db.get_repository()
    if repository is None:
        return
    winner = next(m for m in report["models"] if m["name"] == report["production"]["name"])
    repository.add_training({
        "version": report["version"],
        "modelo": winner["name"],
        "configuracion": winner["config"],
        "fuente_datos": report["data_source"],
        "cv_f1_macro": winner["cv_f1_macro"],
        "test_f1_macro": winner["test"]["f1_macro"],
        "test_accuracy": winner["test"]["accuracy"],
        "test_f1_ofensivo": winner["test_binary"]["offensive"]["f1"],
        "n_entrenamiento": report["dataset"]["train_size"],
        "n_prueba": report["dataset"]["test_size"],
    })
    print("Entrenamiento registrado en la tabla entrenamientos")

if __name__ == "__main__":
    main()
