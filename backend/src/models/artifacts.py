"""Escribe en disco lo que produce un entrenamiento."""

import json
from pathlib import Path

import joblib
import pandas as pd

def save_artifacts(directory: Path, *, production, report: dict, experiments: pd.DataFrame,
                   error_table: pd.DataFrame) -> None:
    directory.mkdir(parents=True, exist_ok=True)

    joblib.dump({
        "pipeline": production.pipeline,
        "version": report["version"],
        "model": production.name,
        "label": production.label,
        "config": production.config,
        "threshold": report["threshold"],
        "demo_mode": report["demo_mode"],
    }, directory / "model.joblib")

    (directory / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    readable = experiments.assign(hyperparameters=experiments["hyperparameters"].map(json.dumps))
    readable.to_csv(directory / "experiments.csv", index=False)

    mistakes = error_table.loc[~error_table["correcto"]].drop(columns="correcto")
    mistakes.assign(fenomenos=mistakes["fenomenos"].map(" | ".join)) \
            .to_csv(directory / "errors.csv", index=False)
