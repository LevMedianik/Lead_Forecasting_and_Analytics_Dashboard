# EN: Lead Forecasting and Analytics Dashboard

The project was inspired by an internal analytics panel prototype. The current version has been fully redesigned and extended as a standalone ML project.  
The demo version uses synthetic / anonymized data.  
This is a web dashboard for analysis and short-term forecasting of key marketing metrics (Leads, CPL, ROI).  
The project demonstrates a complete ML pipeline for time-series tasks, including training, validation, anomaly detection, and REST integration.

---

## 🎯 Project Goal

To implement a reproducible short-term lead forecasting system (hourly, 7-day horizon) including:

- proper time-series cross-validation without data leakage  
- visualization of actuals and forecast  
- CPL anomaly monitoring  
- production-oriented architecture with backend/frontend separation  

---

## 📊 ML Methodology and Model Selection

### Modeling Approach

The time series is transformed into a supervised learning format using:

- lag features  
- calendar features  
- rolling statistics  

**Time Series Cross-Validation (5 folds)** is applied:

- data is not shuffled  
- training is performed only on past data  
- validation is performed on the subsequent time segment  
- data leakage is fully prevented  

Metrics are averaged across folds (mean ± std).

---

### Evaluation Metrics

- **RMSE** — sensitive to large errors  
- **MAE** — mean absolute error  
- **R²** — proportion of explained variance  
- **sMAPE** — symmetric relative percentage error  

### Results obtained:
```
RMSE : 1.498 ± 0.028
MAE  : 1.198 ± 0.021
R²   : 0.733 ± 0.008
sMAPE: 0.381 ± 0.008
```
### Interpretation:

- Error ~1–1.5 leads per hour within a 0–12 range  
- The model explains ~73% of time-series variance  
- Stability confirmed by low std across folds  

---

### Why GradientBoosting Was Selected

Models compared:

Linear Regression, Ridge, Lasso, Decision Tree, Random Forest, ExtraTrees, GradientBoosting, LightGBM, XGBoost, Prophet.

Selection criteria:

- lowest RMSE  
- higher R² at comparable RMSE  
- stability under TSCV  

GradientBoosting demonstrated:

- lowest average RMSE  
- stable metrics across folds  
- strong bias/variance trade-off  
- no signs of overfitting  

---

## 🚨 Anomaly Detection

CPL anomalies are detected using a rolling Z-score:

```
Z = (x - μ) / σ
```


Where:

- x — current value  
- μ — rolling mean  
- σ — rolling standard deviation  

Default sensitivity threshold: |Z| > 2.5  

A 14-day lookback window and a 7-day baseline window are used.

---

## 🏗 Architecture and Production Approach

### Backend (FastAPI)

- model loading (`forecast.pkl`) at service startup  
- REST API:
  - `/forecast`
  - `/anomalies`
  - `/kpi`
  - `/health`
- separation of ML logic and UI  
- modular structure (`features.py`, `anomalies.py`)  

### ML Pipeline

1. Time-series loading and sorting  
2. Feature generation  
3. Time-series cross-validation  
4. Experiment logging  
5. Best model saving  
6. Inference mode  

### Frontend

- 14 days actuals + 7 days forecast chart  
- KPIs for the last 24 hours  
- automatic refresh  
- anomaly visualization  

### Production Principles

- model is loaded once  
- training is separated from inference  
- backend and frontend are fully decoupled  
- containerization via Docker  
- deployment on Render  

---

## ⚙️ Installation and Run

```bash
git clone https://github.com/LevMedianik/Lead_Forecasting_and_Analytics_Dashboard.git
cd Lead_Forecasting_and_Analytics_Dashboard
```

### Using Docker
```bash
cd infra
docker-compose build
docker-compose up
```

The application will be available at:

```
http://localhost:8000
```

### 📂 Project Structure

```
RESPOND_client_dashboard/
│
├── backend/
│   ├── main.py
│   ├── ml/
│   │   └── features.py
│   ├── data/
│   └── models/forecast.pkl
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   ├── styles.css
│
├── infra/
│   ├── Dockerfile
│   ├── docker-compose.yml
│
└── README.md
```
### ✅ Summary

The project demonstrates:

- proper time-series validation
- justified model selection
- metric interpretation
- anomaly detection
- production-ready architecture

The dashboard is fully functional and ready for demonstration.

---

# RU: Дашборд прогнозирования и аналитики лидов

Проект вдохновлён прототипом внутренней аналитической панели. Текущая версия была полностью переработана и расширена как самостоятельный ML-проект.
В демонстрационной версии используются синтетические / анонимизированные данные.
Это веб-дашборд для анализа и краткосрочного прогнозирования ключевых маркетинговых метрик (Leads, CPL, ROI).
Проект демонстрирует полный ML-pipeline для задач временных рядов, включая обучение, валидацию, детекцию аномалий и REST-интеграцию.

---

## 🎯 Цель проекта

Реализовать воспроизводимую систему краткосрочного прогнозирования лидов (hourly, горизонт 7 дней), включающую:

- корректную time-series cross-validation без утечки данных  
- визуализацию факта и прогноза  
- мониторинг аномалий CPL  
- production-подход с разделением backend и frontend  

---

## 📊 ML-методология и выбор модели

### Подход к моделированию

Временной ряд преобразуется в supervised-формат с использованием:

- лаговых признаков  
- календарных признаков  
- скользящих статистик  

Использована **Time Series Cross-Validation (5 фолдов)**:

- данные не перемешиваются  
- обучение происходит только на прошлом  
- валидация — на следующем временном сегменте  
- исключён data leakage  

Метрики усредняются по фолдам (mean ± std).

---

### Используемые метрики

- **RMSE** — чувствителен к крупным ошибкам  
- **MAE** — средняя абсолютная ошибка  
- **R²** — доля объяснённой дисперсии  
- **sMAPE** — относительная симметричная ошибка  

### Полученные результаты:

```
RMSE : 1.498 ± 0.028
MAE  : 1.198 ± 0.021
R²   : 0.733 ± 0.008
sMAPE: 0.381 ± 0.008
```

### Интерпретация:

- Ошибка ~1–1.5 лида в час при диапазоне 0–12  
- Модель объясняет ~73% вариации временного ряда  
- Устойчивость подтверждается низким std по фолдам  

---

### Почему выбрана GradientBoosting

Сравнивались:

Linear Regression, Ridge, Lasso, Decision Tree, Random Forest, ExtraTrees, GradientBoosting, LightGBM, XGBoost, Prophet.

Критерии выбора:

- минимальный RMSE  
- более высокий R² при равном RMSE  
- стабильность на TSCV  

GradientBoosting показал:

- наименьший средний RMSE  
- стабильные метрики по фолдам  
- хороший баланс bias/variance  
- отсутствие признаков переобучения  

---

## 🚨 Детекция аномалий

Аномалии CPL определяются через rolling Z-score:

```
Z = (x - μ) / σ
```

Где:

- x — текущее значение  
- μ — скользящее среднее  
- σ — скользящее стандартное отклонение  

Порог чувствительности по умолчанию: |Z| > 2.5  

Используется lookback-окно 14 дней и baseline-окно 7 дней.

---

## 🏗 Архитектура и продакшн-подход

### Backend (FastAPI)

- загрузка модели (`forecast.pkl`) при старте сервиса  
- REST API:
  - `/forecast`
  - `/anomalies`
  - `/kpi`
  - `/health`
- разделение логики ML и UI  
- модульная структура (`features.py`, `anomalies.py`)  

### ML-пайплайн

1. Загрузка и сортировка временного ряда  
2. Генерация признаков  
3. Time-series CV  
4. Логирование экспериментов  
5. Сохранение лучшей модели  
6. Inference-режим  

### Frontend

- график: 14 дней факт + 7 дней прогноз  
- KPI за последние 24 часа  
- автоматическое обновление  
- визуализация аномалий  

### Продакшн-принципы

- модель загружается один раз  
- обучение отделено от inference  
- backend и frontend полностью независимы  
- контейнеризация через Docker  
- деплой на Render  

---

## ⚙️ Установка и запуск

```bash
git clone https://github.com/LevMedianik/Lead_Forecasting_and_Analytics_Dashboard.git
cd Lead_Forecasting_and_Analytics_Dashboard
```

### Через Docker:

```bash
cd infra
docker-compose build
docker-compose up
```

Приложение доступно по адресу:

```
http://localhost:8000
```

---

## 📂 Структура проекта

```
RESPOND_client_dashboard/
│
├── backend/
│   ├── main.py
│   ├── ml/
│   │   └── features.py
│   ├── data/
│   └── models/forecast.pkl
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   ├── styles.css
│
├── infra/
│   ├── Dockerfile
│   ├── docker-compose.yml
│
└── README.md
```

---

## ✅ Итог

Проект демонстрирует:

- корректную time-series валидацию  
- обоснованный выбор модели  
- интерпретацию метрик  
- детекцию аномалий  
- production-ready архитектуру  

Дашборд полностью функционален и готов к демонстрации.