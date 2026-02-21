import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import mlflow.sklearn
import numpy as np
import pandas as pd
import xgboost as xgb
from prophet import Prophet
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.tree import DecisionTreeRegressor
import shutil

MLFLOW_EXPERIMENT_NAME = "respond_client_dashboard_forecasting"
MLRUNS_PATH = Path("mlruns")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.ml.features import make_features  # noqa: E402

DATA_PATH = Path("backend/data/respond_hourly.csv")
MODEL_PATH = Path("backend/models/forecast.pkl")


def smape(y_true, y_pred, eps: float = 1e-8) -> float:
    """
    Symmetric MAPE: устойчивее обычного MAPE при малых значениях.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true) + np.abs(y_pred) + eps
    return float(np.mean(2.0 * np.abs(y_pred - y_true) / denom))


def evaluate_model(y_true, y_pred):
    """
    Метрики: RMSE, MAE, R², sMAPE
    """
    rmse = float(root_mean_squared_error(y_true, y_pred))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    sm = float(smape(y_true, y_pred))
    return rmse, mae, r2, sm


def _fit_predict_prophet(train_df: pd.DataFrame, val_df: pd.DataFrame) -> np.ndarray:
    """
    train_df, val_df: DataFrame with columns ['ds', 'y']
    Возвращает yhat для val_df.ds
    """
    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=True,  # hourly данные — это уместно
    )
    m.fit(train_df)
    future = val_df[["ds"]].copy()
    fcst = m.predict(future)
    return fcst["yhat"].values

def cleanup_mlruns_trash() -> None:
    """
    Safely removes mlruns/.trash if it exists.
    Works whether .trash is a folder or file.
    """
    trash_path = MLRUNS_PATH / ".trash"

    if not MLRUNS_PATH.exists():
        return

    if trash_path.exists():
        try:
            if trash_path.is_dir():
                shutil.rmtree(trash_path)
            else:
                trash_path.unlink()
            print("Cleaned mlruns/.trash")
        except Exception as e:
            print(f"Could not clean mlruns/.trash: {e}")

def train_forecast(horizon: int = 24):
    # гарантируем локальное хранилище MLflow
    MLRUNS_PATH.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"file:{MLRUNS_PATH.resolve()}")

    # чистим только мусор (если есть)
    cleanup_mlruns_trash()

    # отдельный эксперимент (чтобы не плодить experiment 0)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    # Загружаем данные
    df = pd.read_csv(DATA_PATH, parse_dates=["datetime"]).set_index("datetime").sort_index()

    if "leads" not in df.columns:
        raise ValueError("В respond_hourly.csv должна быть колонка 'leads'.")

    # Генерируем фичи для sklearn/boosting
    X, y, _ = make_features(df, horizon=horizon)

    # Time-series CV
    tscv = TimeSeriesSplit(n_splits=5)

    # Модели
    models = {
        "LinearRegression": LinearRegression(),
        "Ridge": Ridge(alpha=1.0),
        "Lasso": Lasso(alpha=0.01),
        "DecisionTree": DecisionTreeRegressor(max_depth=6),
        "RandomForest": RandomForestRegressor(n_estimators=200, random_state=42),
        "ExtraTrees": ExtraTreesRegressor(n_estimators=200, random_state=42),
        "GradientBoosting": GradientBoostingRegressor(random_state=42),
        "LightGBM": lgb.LGBMRegressor(random_state=42),
        "XGBoost": xgb.XGBRegressor(
            random_state=42,
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
        ),
        "Prophet": None,  # special case
    }

    best_rmse, best_r2 = float("inf"), -float("inf")
    best_model, best_name = None, None
    all_results = {}

    # Prophet данные строим из y (важно: same index length, что и X/y после лагов)
    prophet_df_full = (
        y.reset_index()
        .rename(columns={"datetime": "ds", "leads": "y"})
        .sort_values("ds")
        .reset_index(drop=True)
    )
    
    for name, model in models.items():
        with mlflow.start_run(run_name=name):
            mlflow.log_param("model", name)
            mlflow.log_param("cv_splits", 5)

            fold_metrics = []

            if name == "Prophet":
                # Честный out-of-sample TSCV на тех же индексах, что и y
                for fold, (train_idx, val_idx) in enumerate(tscv.split(prophet_df_full), start=1):
                    train_df = prophet_df_full.iloc[train_idx][["ds", "y"]].copy()
                    val_df = prophet_df_full.iloc[val_idx][["ds", "y"]].copy()

                    y_pred = _fit_predict_prophet(train_df, val_df)
                    y_true = val_df["y"].values

                    rmse_f, mae_f, r2_f, sm_f = evaluate_model(y_true, y_pred)
                    fold_metrics.append((rmse_f, mae_f, r2_f, sm_f))

                    mlflow.log_metric(f"rmse_fold_{fold}", rmse_f)
                    mlflow.log_metric(f"mae_fold_{fold}", mae_f)
                    mlflow.log_metric(f"r2_fold_{fold}", r2_f)
                    mlflow.log_metric(f"smape_fold_{fold}", sm_f)

                # mean metrics for selection/logging
                rmse = float(np.mean([m[0] for m in fold_metrics]))
                mae = float(np.mean([m[1] for m in fold_metrics]))
                r2 = float(np.mean([m[2] for m in fold_metrics]))
                sm = float(np.mean([m[3] for m in fold_metrics]))

                # Перетренируем Prophet на всех данных (для сохранения в прод)
                model_to_save = Prophet(
                    yearly_seasonality=True,
                    weekly_seasonality=True,
                    daily_seasonality=True,
                )
                model_to_save.fit(prophet_df_full)

            else:
                # sklearn / boosting: CV на X/y
                for fold, (train_idx, val_idx) in enumerate(tscv.split(X), start=1):
                    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_val)

                    rmse_f, mae_f, r2_f, sm_f = evaluate_model(y_val, y_pred)
                    fold_metrics.append((rmse_f, mae_f, r2_f, sm_f))

                    mlflow.log_metric(f"rmse_fold_{fold}", rmse_f)
                    mlflow.log_metric(f"mae_fold_{fold}", mae_f)
                    mlflow.log_metric(f"r2_fold_{fold}", r2_f)
                    mlflow.log_metric(f"smape_fold_{fold}", sm_f)

                rmse = float(np.mean([m[0] for m in fold_metrics]))
                mae = float(np.mean([m[1] for m in fold_metrics]))
                r2 = float(np.mean([m[2] for m in fold_metrics]))
                sm = float(np.mean([m[3] for m in fold_metrics]))

                # (опционально) лог-модель в MLflow
                mlflow.sklearn.log_model(model, artifact_path="model")
                model_to_save = model

            # Сохраняем результаты модели в память ДЛЯ ВСЕХ моделей
            rmses = [m[0] for m in fold_metrics]
            maes = [m[1] for m in fold_metrics]
            r2s = [m[2] for m in fold_metrics]
            smapes = [m[3] for m in fold_metrics]

            all_results[name] = {
                "folds": fold_metrics,
                "mean": {
                    "rmse": float(np.mean(rmses)),
                    "mae": float(np.mean(maes)),
                    "r2": float(np.mean(r2s)),
                    "smape": float(np.mean(smapes)),
                },
                "std": {
                    "rmse": float(np.std(rmses, ddof=1)) if len(rmses) > 1 else 0.0,
                    "mae": float(np.std(maes, ddof=1)) if len(maes) > 1 else 0.0,
                    "r2": float(np.std(r2s, ddof=1)) if len(r2s) > 1 else 0.0,
                    "smape": float(np.std(smapes, ddof=1)) if len(smapes) > 1 else 0.0,
                },
            }

            # Логируем итоговые метрики в MLflow
            mlflow.log_metric("rmse_mean", rmse)
            mlflow.log_metric("mae_mean", mae)
            mlflow.log_metric("r2_mean", r2)
            mlflow.log_metric("smape_mean", sm)

            # Выбор лучшей модели: по RMSE, tie-breaker по R²
            if (rmse < best_rmse) or (rmse == best_rmse and r2 > best_r2):
                best_rmse, best_r2 = rmse, r2
                best_model, best_name = model_to_save, name
            
    # Сохраняем лучшую модель
    MODEL_PATH.parent.mkdir(exist_ok=True, parents=True)
    joblib.dump(best_model, MODEL_PATH)

    print("\n" + "=" * 70)
    print(f"BEST MODEL: {best_name}")
    print(f"Saved to: {MODEL_PATH}")

    # Подробные метрики best model
    best = all_results.get(best_name)
    if best:
        m = best["mean"]
        s = best["std"]
        print("\nMetrics (mean ± std over folds):")
        print(f"  RMSE : {m['rmse']:.4f} ± {s['rmse']:.4f}")
        print(f"  MAE  : {m['mae']:.4f} ± {s['mae']:.4f}")
        print(f"  sMAPE: {m['smape']:.4f} ± {s['smape']:.4f}")
        print(f"  R²   : {m['r2']:.4f} ± {s['r2']:.4f}")

        print("\nFold metrics:")
        print("  fold |   RMSE   |   MAE    |  sMAPE   |   R²")
        print("  -----+----------+----------+----------+--------")
        for i, (rmse_f, mae_f, r2_f, sm_f) in enumerate(best["folds"], start=1):
            print(f"  {i:>4} | {rmse_f:>8.4f} | {mae_f:>8.4f} | {sm_f:>8.4f} | {r2_f:>6.4f}")
    else:
        print("\nNo in-memory metrics found for best model (unexpected).")

    # Топ моделей по RMSE
    print("\nTop models by RMSE (lower is better):")
    ranking = []
    for name, res in all_results.items():
        ranking.append((res["mean"]["rmse"], res["mean"]["r2"], name))
    ranking.sort(key=lambda x: (x[0], -x[1]))

    for k, (rmse_m, r2_m, name) in enumerate(ranking[:5], start=1):
        print(f"  {k}. {name:>16}  RMSE={rmse_m:.4f}  R²={r2_m:.4f}")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    train_forecast(horizon=24)