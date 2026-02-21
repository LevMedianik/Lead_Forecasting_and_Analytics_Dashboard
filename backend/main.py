from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import pandas as pd
import joblib
import os
from pathlib import Path
from backend.ml.features import recursive_forecast
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from backend.ml.anomalies import detect_hourly_anomalies

DATA_HOURLY = Path("backend/data/respond_hourly.csv")
DATA_MONTHLY = Path("backend/data/respond.csv")
MODEL_PATH = Path("backend/models/forecast.pkl")

# Инициализация приложения
app = FastAPI(title="RE:SPOND Dashboard API")

# --- Раздача фронтенда ---
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def root():
    """Главная страница — отдаём index.html"""
    return FileResponse(os.path.join(frontend_dir, "index.html"))

# Разрешаем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = joblib.load(MODEL_PATH)

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics(n: int = 12):
    """Возвращает последние n месяцев KPI"""
    df = pd.read_csv(DATA_MONTHLY)
    data = df.tail(n).to_dict(orient="records")
    return {"data": data}

@app.get("/forecast")

def forecast(horizon_hours: int = 168, history_hours: int = 24 * 14):
    """
    Forecast leads for the next horizon_hours using:
    - Prophet: direct predict on future timestamps
    - sklearn/boosting: correct recursive multi-step forecast (updates lags/rolling)
    
    Returns:
      - actual_hourly: last history_hours points
      - forecast_hourly: next horizon_hours points
      - forecast_monthly: monthly sum of the forecast (for compatibility with old UI)
    """
    if model is None:
        return JSONResponse(status_code=500, content={"error": "Модель не загружена"})

    df = pd.read_csv(DATA_HOURLY, parse_dates=["datetime"]).set_index("datetime").sort_index()

    # берём историю для recursive (нужно минимум max(window, lag) значений; у нас окна до 168)
    # поэтому для устойчивости берём хотя бы max(history_hours, 24*14)
    history_hours = max(history_hours, 24 * 14)
    df_hist = df.tail(history_hours).copy()

    # --------- PROPHET ----------
    if "prophet" in str(type(model)).lower():
        future = pd.date_range(
            df_hist.index.max() + pd.Timedelta(hours=1),
            periods=horizon_hours,
            freq="H",
        )
        future_df = pd.DataFrame({"ds": future})
        fcst = model.predict(future_df)[["ds", "yhat"]].rename(
            columns={"ds": "datetime", "yhat": "leads_forecast"}
        )
        forecast_hourly = fcst.copy()
        forecast_hourly["datetime"] = pd.to_datetime(forecast_hourly["datetime"])

    # --------- SKLEARN / BOOSTING ----------
    else:
        # recursive multi-step forecast (correct for lag/rolling models)
        fcst_df = recursive_forecast(
            model=model,
            df_hist=df_hist[["leads"]],
            horizon_hours=horizon_hours,
        )
        forecast_hourly = fcst_df.reset_index().rename(
            columns={"datetime": "datetime", "leads_pred": "leads_forecast"}
        )
        forecast_hourly["datetime"] = pd.to_datetime(forecast_hourly["datetime"])

    # --------- ACTUAL (for chart) ----------
    actual_hourly = df_hist.reset_index()[["datetime", "leads"]].copy()
    actual_hourly["datetime"] = pd.to_datetime(actual_hourly["datetime"])

    # align to "now" for demo purposes (optional)
    align_to_now = True
    if align_to_now:
        now = pd.Timestamp.now().floor("H")
        max_actual = actual_hourly["datetime"].max()
        delta = now - max_actual
        actual_hourly["datetime"] = actual_hourly["datetime"] + delta
        forecast_hourly["datetime"] = forecast_hourly["datetime"] + delta

    # --------- MONTHLY AGG (compatibility) ----------
    tmp = forecast_hourly.copy()
    tmp["month"] = tmp["datetime"].dt.to_period("M").astype(str)
    forecast_monthly = (
        tmp.groupby("month")["leads_forecast"]
        .sum()
        .reset_index()
        .to_dict(orient="records")
    )

    return {
        "actual_hourly": actual_hourly.to_dict(orient="records"),
        "forecast_hourly": forecast_hourly.to_dict(orient="records"),
        "forecast_monthly": forecast_monthly,
        "meta": {
            "model": type(model).__name__,
            "horizon_hours": horizon_hours,
            "history_hours": history_hours,
        },
    }

@app.get("/kpi")
def kpi(window_hours: int = 24):
    """
    KPI только по факту за последние window_hours.
    Без расчёта прогноза.
    """
    df = pd.read_csv(DATA_HOURLY, parse_dates=["datetime"]).set_index("datetime").sort_index()

    hist = df.tail(window_hours)

    return {
        "kpi": {
            "leads_24h": int(hist["leads"].sum()),
            "cpl_24h": round(float(hist["cpl"].mean()), 2),
            "roi_24h": round(float(hist["roi"].mean()), 3),
        }
    }

@app.get("/anomalies")
def anomalies(
    metric: str = "cpl",
    k: float = 2.5,
    window_hours: int = 24 * 7,
    lookback_hours: int = 24 * 14,
    align_to_now: bool = True,
):
    df = detect_hourly_anomalies(
        metric=metric,
        k=k,
        window_hours=window_hours,
        lookback_hours=lookback_hours,
    )

    # --- Сдвиг времени к текущему моменту ---
    if align_to_now and not df.empty:
        now = pd.Timestamp.now().floor("H")
        max_ts = df["datetime"].max()
        delta = now - max_ts
        df["datetime"] = df["datetime"] + delta

    return {
        "metric": metric,
        "k": k,
        "window_hours": window_hours,
        "lookback_hours": lookback_hours,
        "anomalies": df.to_dict(orient="records"),
    }