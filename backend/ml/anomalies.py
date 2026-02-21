import pandas as pd
import numpy as np
from pathlib import Path

DATA_HOURLY = Path("backend/data/respond_hourly.csv")


def detect_hourly_anomalies(
    metric: str = "cpl",
    k: float = 2.5,
    window_hours: int = 24 * 7,
    lookback_hours: int = 24 * 14,
):
    """
    Почасовая детекция аномалий через rolling z-score:
      z(t) = (x(t) - mean_{window}(t-1)) / std_{window}(t-1)
    Где mean/std считаются по предыдущим значениям (shift(1)), чтобы не "подглядывать".

    Возвращает таблицу аномалий за lookback_hours (последние 14 дней по умолчанию).
    """
    if metric not in {"cpl", "roi", "leads"}:
        raise ValueError("metric must be one of: 'cpl', 'roi', 'leads'")

    df = pd.read_csv(DATA_HOURLY, parse_dates=["datetime"]).set_index("datetime").sort_index()
    s = df[metric].astype(float)

    # rolling baseline без подглядывания в текущую точку
    mu = s.shift(1).rolling(window_hours).mean()
    sigma = s.shift(1).rolling(window_hours).std(ddof=0)

    z = (s - mu) / sigma.replace(0, np.nan)

    out = pd.DataFrame(
        {
            "datetime": s.index,
            metric: s.values,
            "z_score": z.values,
        }
    ).dropna()
    
    # фильтр по порогу
    out = out[np.abs(out["z_score"]) > k]

    # последние N часов
    cutoff = df.index.max() - pd.Timedelta(hours=lookback_hours)
    out = out[out["datetime"] >= cutoff]

    # сортировка: самые "сильные" аномалии сверху
    out = out.sort_values("z_score", key=lambda x: np.abs(x), ascending=False)

    return out

if __name__ == "__main__":
    # Пример использования
    anomalies_cpl = detect_hourly_anomalies(metric="cpl", k=2.5)
    anomalies_roi = detect_hourly_anomalies(metric="roi", k=2.5)

    print("Аномалии CPL:")
    print(anomalies_cpl if not anomalies_cpl.empty else "Не найдено")

    print("\nАномалии ROI:")
    print(anomalies_roi if not anomalies_roi.empty else "Не найдено")
