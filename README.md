# EN: RE:SPOND Client Dashboard

A web-based analytics dashboard for visualizing and monitoring key business metrics of RE:SPOND.  
It enables tracking lead dynamics, forecasting future values, and detecting anomalies in CPL.

---

## 📊 Key Features

- KPI cards (Leads, CPL, ROI)
- Lead forecasting through the end of 2025
- Anomaly detection using Z-score
- Automated analytics and recommendation section

---

## 🧩 Tech Stack

### Frontend

- HTML5
- TailwindCSS
- JavaScript (Fetch API, Chart.js)

### Backend

- Python 3.12
- FastAPI
- Pandas
- Joblib
- Prophet / sklearn-compatible forecasting model

### Infrastructure

- Docker + Docker Compose
- Render (Web Service deployment)
- Git + GitHub (version control)

---

## ✅ Model Validation & Forecasting Logic
### Forecasting Approach  
The lead forecasting component is based on a supervised time-series modeling approach. Historical monthly lead data is transformed into a structured dataset with temporal features (trend components, seasonality indicators, and rolling statistics).  

The forecasting model (Prophet / sklearn-compatible regressor) captures:

- Long-term growth or decline trends
- Seasonal fluctuations
- Short-term variability

The trained model is serialized (forecast.pkl) and preloaded at application startup to ensure low-latency inference in production.

### Validation Strategy  

To ensure model reliability, the following validation steps were applied:

Train–validation split using time-aware separation (no random shuffling).  
Backtesting on historical periods to evaluate stability.  
Error metrics evaluation, including:  

- MAE (Mean Absolute Error)
- MAPE (Mean Absolute Percentage Error)
- RMSE (Root Mean Squared Error)

This prevents data leakage and provides realistic performance estimates for future projections.

### Anomaly Detection Logic

CPL anomaly detection is implemented using a statistical Z-score method:

𝑍 = 𝑥 − 𝜇 / 𝜎
​
Where:  

𝑥 – current metric value  
𝜇 – rolling mean  
𝜎 – rolling standard deviation  

A configurable threshold (default: 2.5) determines whether a data point is flagged as an anomaly.

This lightweight statistical approach ensures interpretability and transparency while remaining computationally efficient.

### Production Considerations
The forecasting model is loaded once at service startup to avoid repeated disk I/O.
Data preprocessing is deterministic and reproducible.
API endpoints are designed to separate computation from visualization logic.

The system allows future replacement of the forecasting model without frontend changes.

---

## ⚙️ Installation & Local Setup
1. Clone the repository
```
git clone https://github.com/LevMedianik/RESPOND_client_dashboard.git
cd RESPOND_client_dashboard
```
3. Configure environment variables
```
cp .env.example .env
```

(Add environment variables if needed.)

3. Run locally with Docker Compose
```
cd infra
docker-compose build
docker-compose up
```

After the build process, the application will be available at:
```
http://localhost:8000
```

---

## 🧠 API Endpoints
Endpoint	Method	Description
```
/	GET	Dashboard main page
/metrics?n=12	GET	KPI metrics for the last n months
/forecast	GET	Lead forecast until December 2025
/anomalies?metric=cpl&k=2.5	GET	Z-score anomaly detection
/health	GET	Server health check
```

---

## 🧱 Project Architecture
```
RESPOND_client_dashboard/
│
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── ml/
│   │   └── features.py         # Data preprocessing
│   ├── data/                   # CSV files with metrics
│   └── models/forecast.pkl     # Forecasting model
│
├── frontend/
│   ├── index.html              # Main dashboard page
│   ├── script.js               # API interaction logic
│   ├── styles.css              # Tailwind styling
│   └── static/                 # Images and favicon
│
├── infra/
│   ├── Dockerfile              # Application container image
│   ├── docker-compose.yml      # Container build & run config
│   └── .env.example            # Environment variables template
│
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## ☁️ Deployment

The application is deployed on Render.com as a Web Service.  
The container uses the Dockerfile from the infra directory.  
The frontend directory is mounted as /static to ensure proper resource loading.  
Static files are served directly via FastAPI StaticFiles.  

---

## 🧠 Implementation Details & Optimizations

CORS configuration implemented for proper frontend–backend communication.  
Fixed relative paths for Docker and Render environments.  
Optimized model and CSV loading to reduce response latency.  
Static resources are served directly from the container for improved performance.  
Forecasting model preloaded at application startup to minimize runtime overhead.  

---

## ✅ Result

The project is fully functional and production-ready for demonstration.  
Frontend and API align with technical requirements.  
Successfully deployed and accessible via public Render URL.  
Demonstrates practical ML integration into a business analytics workflow.  

---

## Note
The project is available in Russian only; English localization will be implemented in the future.  

# RU: RE:SPOND Client Dashboard

Веб-дашборд для аналитики и визуализации ключевых показателей компании **RE:SPOND**.  
Позволяет отслеживать динамику лидов, прогнозировать будущие значения и выявлять аномалии по CPL.

---

## 📊 Основные возможности

- Отображение KPI-карточек (Leads, CPL, ROI)  
- Прогнозирование количества лидов до конца 2025 года  
- Детекция аномалий по Z-score  
- Раздел с рекомендациями и автоматическим анализом данных  

---

## 🧩 Используемый стек

### Frontend
- HTML5  
- TailwindCSS  
- JavaScript (fetch API, Chart.js)

### Backend
- Python 3.12  
- FastAPI  
- Pandas  
- Joblib  
- Prophet / sklearn-совместимая модель

### Инфраструктура
- Docker + Docker Compose  
- Render (деплой Web Service)  
- Git + GitHub (версионирование)

---

## ✅ Логика валидации модели и прогнозирования
### Подход к прогнозированию

Модуль прогнозирования лидов основан на методе супервизируемого моделирования временных рядов. Исторические месячные данные преобразуются в структурированный датасет с временными признаками (тренд, сезонность, скользящие статистики).

Модель прогнозирования (Prophet / sklearn-совместимый регрессор) учитывает:

- Долгосрочный тренд роста или снижения
- Сезонные колебания
- Краткосрочную вариативность
Обученная модель сериализуется (forecast.pkl) и загружается при старте приложения для обеспечения низкой задержки в продакшене.

### Стратегия валидации

Для обеспечения надёжности прогноза применялись следующие подходы:

- Time-aware разделение train/validation (без случайного перемешивания данных)
- Backtesting на исторических периодах

### Оценка метрик качества:

- MAE (средняя абсолютная ошибка)
- MAPE (средняя абсолютная процентная ошибка)
- RMSE (среднеквадратичная ошибка)

Это исключает утечку данных и обеспечивает реалистичную оценку качества прогноза.

### Логика обнаружения аномалий

Обнаружение аномалий CPL реализовано на основе статистического метода Z-score:

𝑍 = 𝑥 − 𝜇 / 𝜎

Где:

𝑥 – текущее значение показателя
𝜇 – скользящее среднее
𝜎 – скользящее стандартное отклонение

Порог (по умолчанию 2.5) задаёт уровень чувствительности обнаружения аномалий.

Метод обеспечивает интерпретируемость, прозрачность и низкую вычислительную нагрузку.

### Продакшн-аспекты

Модель загружается один раз при запуске сервиса.  
Предобработка данных детерминирована и воспроизводима.  
Логика вычислений отделена от логики визуализации.  
Архитектура позволяет заменить модель без изменения frontend-части.

---

## ⚙️ Установка и запуск

1. Клонирование репозитория
```
git clone https://github.com/LevMedianik/RESPOND_client_dashboard.git
cd RESPOND_client_dashboard
```
2. Создание и настройка окружения
```
cp .env.example .env (при необходимости добавьте переменные окружения)
```
3. Запуск локально через Docker Compose
```
cd infra
docker-compose build
docker-compose up
```

После сборки приложение будет доступно по адресу:
```
http://localhost:8000
```

---

## 🧠 API-эндпоинты

| Endpoint | Метод | Описание |
|-----------|--------|----------|
| `/` | **GET** | Главная страница с дашбордом |
| `/metrics?n=12` | **GET** | KPI-метрики за последние *n* месяцев |
| `/forecast` | **GET** | Прогноз по лидам до декабря 2025 года |
| `/anomalies?metric=cpl&k=2.5` | **GET** | Детекция аномалий по Z-score |
| `/health` | **GET** | Проверка состояния сервера |

---

## 🧱 Архитектура проекта
```
RESPOND_client_dashboard/
│
├── backend/
│   ├── main.py                 # Точка входа FastAPI
│   ├── ml/
│   │   └── features.py         # Обработка данных
│   ├── data/                   # CSV-файлы с метриками
│   └── models/forecast.pkl     # Модель прогноза
│
├── frontend/
│   ├── index.html              # Главная страница
│   ├── script.js               # Логика взаимодействия с API
│   ├── styles.css              # Стили (Tailwind)
│   └── static/                 # Изображения и favicon
│
├── infra/
│   ├── Dockerfile              # Образ приложения
│   ├── docker-compose.yml      # Сборка и запуск контейнера
│   └── .env.example            # Пример переменных окружения
│
├── requirements.txt            # Python-зависимости
└── README.md                   # Описание проекта
```

---

## ☁️ Деплой

Приложение развёрнуто на Render.com как Web Service.
Контейнер использует Dockerfile из директории infra.
Путь к фронтенду (frontend/) монтируется как /static, что обеспечивает корректную загрузку всех ресурсов.

---

## 🧠 Особенности реализации и оптимизации

Реализована поддержка CORS для корректного взаимодействия фронтенда и API.
Исправлены относительные пути при работе в Docker и на Render.
Оптимизирована загрузка модели и CSV-файлов для минимизации времени отклика.
Все статические ресурсы раздаются напрямую из контейнера через StaticFiles.

---

## ✅ Результат

Проект полностью функционален и готов к демонстрации.
Интерфейс и API соответствуют техническому заданию.
Дашборд успешно задеплоен и доступен по публичному URL-адресу Render.

---

## Примечание
Язык проекта только русский, английская локализация будет внедрена в будущем

