import pandas as pd
import numpy as np
from pathlib import Path
from typing import Iterable, Tuple

DATA_PATH = Path("backend/data/respond_hourly.csv")


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляем календарные признаки (hour, dow, month + sin/cos кодировки)."""
    df = df.copy()
    df["hour"] = df.index.hour
    df["dayofweek"] = df.index.dayofweek
    df["month"] = df.index.month

    # sin/cos для циклических признаков
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    df["dow_sin"] = np.sin(2 * np.pi * df["dayofweek"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dayofweek"] / 7)

    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    return df


def add_lag_features(
    df: pd.DataFrame,
    target: str = "leads",
    lags: Iterable[int] = (1, 2, 6, 12, 24),
) -> pd.DataFrame:
    """Добавляем лаги по целевой переменной (leads)."""
    df = df.copy()
    for lag in lags:
        df[f"{target}_lag{lag}"] = df[target].shift(lag)
    return df


def add_rolling_features(
    df: pd.DataFrame,
    target: str = "leads",
    windows: Iterable[int] = (24, 168),
) -> pd.DataFrame:
    """Добавляем скользящие средние по часам (сутки и неделя)."""
    df = df.copy()
    for w in windows:
        df[f"{target}_rollmean{w}"] = df[target].shift(1).rolling(window=w).mean()
    return df


def make_features(
    df: pd.DataFrame,
    horizon: int = 24,
    lags: Tuple[int, ...] = (1, 2, 6, 12, 24),
    windows: Tuple[int, ...] = (24, 168),
):
    """
    Генерация признаков для обучения + baseline future features.

    ВАЖНО:
    X_future, который строится ниже, НЕ является корректным multi-step прогнозом для boosting,
    потому что лаги/rolling "замораживаются" (не обновляются на основе предсказаний).
    Для корректного multi-step используйте make_features_single_step + recursive_forecast().
    """
    df = df.copy()

    # --- базовые фичи ---
    df = add_time_features(df)

    # --- лаги и скользящие ---
    df = add_lag_features(df, target="leads", lags=lags)
    df = add_rolling_features(df, target="leads", windows=windows)

    # --- выбрасываем NA после лагов ---
    df = df.dropna()

    # --- разделение ---
    X = df.drop(columns=["cpl", "roi", "leads"], errors="ignore")
    y = df["leads"]

    # --- baseline future X (НЕ recursive) ---
    last_index = df.index[-1]
    future_index = pd.date_range(last_index + pd.Timedelta(hours=1), periods=horizon, freq="H")
    df_future = pd.DataFrame(index=future_index)

    # временные признаки
    df_future = add_time_features(df_future)

    # лаги: берём последние значения из df (baseline подход)
    for lag in lags:
        df_future[f"leads_lag{lag}"] = df["leads"].iloc[-lag]

    # скользящие средние: baseline (одно значение на весь горизонт)
    for w in windows:
        tail = df["leads"].iloc[-w:] if len(df) >= w else df["leads"]
        df_future[f"leads_rollmean{w}"] = tail.mean()

    X_future = df_future

    return X, y, X_future


def make_features_single_step(
    df_hist: pd.DataFrame,
    next_ts: pd.Timestamp,
    target: str = "leads",
    lags: Tuple[int, ...] = (1, 2, 6, 12, 24),
    windows: Tuple[int, ...] = (24, 168),
) -> pd.DataFrame:
    """
    Фичи для ОДНОГО будущего шага (t -> t+1), чтобы делать корректный recursive forecast.

    df_hist:
      - index: datetime (freq=H)
      - column: 'leads' (и можно иметь cpl/roi, но здесь они не используются)
    next_ts:
      - timestamp следующего шага (обычно last_ts + 1 hour)

    Возвращает DataFrame с 1 строкой X (index=[next_ts]).
    """
    if target not in df_hist.columns:
        raise ValueError(f"df_hist must contain column '{target}'")

    df_hist = df_hist.sort_index()

    row = pd.DataFrame(index=[next_ts])

    # time features для next_ts
    row = add_time_features(row)

    # lag features из истории
    n = len(df_hist)
    for lag in lags:
        if n >= lag:
            row[f"{target}_lag{lag}"] = df_hist[target].iloc[-lag]
        else:
            # fallback: если истории мало — берём первое доступное
            row[f"{target}_lag{lag}"] = df_hist[target].iloc[0]

    # rolling mean features из истории (как в add_rolling_features: shift(1).rolling(w).mean())
    # то есть для next_ts считаем mean по последним w значениям истории (без будущего значения)
    for w in windows:
        tail = df_hist[target].iloc[-w:] if n >= w else df_hist[target]
        row[f"{target}_rollmean{w}"] = float(tail.mean())

    return row


def recursive_forecast(
    model,
    df_hist: pd.DataFrame,
    horizon_hours: int = 168,
    target: str = "leads",
    lags: Tuple[int, ...] = (1, 2, 6, 12, 24),
    windows: Tuple[int, ...] = (24, 168),
) -> pd.DataFrame:
    """
    Корректный multi-step прогноз для sklearn/boosting:
    - предсказываем следующий шаг
    - добавляем предсказание в историю
    - пересчитываем лаги/rolling
    - повторяем horizon_hours раз

    Возвращает DataFrame:
      index: datetime (будущие timestamps)
      columns: ['leads_pred']
    """
    df_sim = df_hist[[target]].copy().sort_index()
    preds = []

    for _ in range(horizon_hours):
        last_ts = df_sim.index[-1]
        next_ts = last_ts + pd.Timedelta(hours=1)

        X_next = make_features_single_step(
            df_hist=df_sim,
            next_ts=next_ts,
            target=target,
            lags=lags,
            windows=windows,
        )

        y_next = float(model.predict(X_next)[0])
        y_next = max(0.0, y_next)          # запрет отрицательных
        y_next = round(y_next)             # лиды целые числа

        preds.append({"datetime": next_ts, f"{target}_pred": y_next})

        # добавляем предсказание в "историю" (для следующих лагов/rolling)
        df_sim.loc[next_ts, target] = y_next

    out = pd.DataFrame(preds).set_index("datetime")
    return out


if __name__ == "__main__":
    df = pd.read_csv(DATA_PATH, parse_dates=["datetime"]).set_index("datetime").sort_index()

    X, y, X_future = make_features(df, horizon=24)
    print("Признаки готовы")
    print("X:", X.shape, "y:", y.shape, "X_future:", X_future.shape)