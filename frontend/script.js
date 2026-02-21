const API_BASE = "";
let chart;

// Универсальный fetch с таймаутом
async function fetchJSON(url, timeoutMs = 8000) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error(`Ошибка загрузки ${url}: ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(t);
  }
}

let isRefreshing = false;

async function refreshAll() {
  if (isRefreshing) return;        // не допускаем перекрытия
  isRefreshing = true;

  try {
    await loadForecast();
    await loadAnomalies();
    await loadKPI();
  } catch (err) {
    console.error("Ошибка refreshAll:", err);
  } finally {
    isRefreshing = false;
  }
}

// === KPI ===
async function loadMetrics() {
  try {
    const metrics = await fetchJSON(`${API_BASE}/metrics?n=12`);
    const last = metrics.data[metrics.data.length - 1];

    document.getElementById("leadsValue").textContent = last.leads;
    document.getElementById("cplValue").textContent = last.cpl.toFixed(2);
    document.getElementById("roiValue").textContent = last.roi.toFixed(3);

    return metrics;
  } catch (err) {
    console.error("Ошибка загрузки KPI:", err);
  }
}

// === График факт + прогноз (hourly: 14 days actual + 7 days forecast) ===
async function loadForecast() {
  try {
    // 14 дней истории = 336 часов, 7 дней прогноза = 168 часов
    const horizonHours = 168;
    const historyHours = 24 * 14;

    const forecast = await fetchJSON(
      `${API_BASE}/forecast?horizon_hours=${horizonHours}&history_hours=${historyHours}`
    );

    const actual = forecast.actual_hourly || [];
    const pred = forecast.forecast_hourly || [];

    // labels: datetime строки
    const labelsActual = actual.map(d => formatTs(d.datetime));
    const labelsPred = pred.map(d => formatTs(d.datetime));
    const labels = [...labelsActual, ...labelsPred];

    const yActual = actual.map(d => Number(d.leads));
    const yPred = pred.map(d => Number(d.leads_forecast));

    // прогнозная линия: null до последней фактической точки, затем "стык" и прогноз
    const forecastSeries = [
      ...Array(Math.max(0, yActual.length - 1)).fill(null),
      yActual.length ? yActual[yActual.length - 1] : null,
      ...yPred
    ];

    // --- KPI подпись: прогноз на 24ч (берём первые 24 часа прогноза) ---
    const forecast24 = yPred.slice(0, 24).reduce((a, b) => a + b, 0);
    const leadsEl = document.getElementById("leadsValue");
    if (leadsEl) {
      const leadsCard = leadsEl.closest(".kpi-card");
      if (leadsCard) {
        const note = leadsCard.querySelector(".kpi-note");
        if (note) note.textContent = `Факт за 24ч / Прогноз на 24ч: ${Math.round(forecast24)}`;
      }
    }

    const canvas = document.getElementById("leadsChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (!chart) {
      chart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Фактический Leads (час)",
              data: [...yActual, ...Array(yPred.length).fill(null)],
              borderColor: "blue",
              fill: false,
              pointRadius: 0,
              tension: 0.2
            },
            {
              label: "Прогноз Leads (7 дней)",
              data: forecastSeries,
              borderColor: "red",
              borderDash: [5, 5],
              fill: false,
              pointRadius: 0,
              tension: 0.2
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: { tooltip: { enabled: true } },
          scales: {
            x: {
              ticks: {
                maxRotation: 0,
                autoSkip: true,
                // метка раз в 12 часов (можно 24)
                callback: function (value, index) {
                  return index % 12 === 0 ? labels[index] : "";
                }
              }
            },
            y: {
              beginAtZero: true,
              grace: "5%"
            }
          }
        }
      });
    } else {
      chart.data.labels = labels;
      chart.data.datasets[0].data = [...yActual, ...Array(yPred.length).fill(null)];
      chart.data.datasets[1].data = forecastSeries;
      chart.update();
    }
  } catch (err) {
    console.error("Ошибка загрузки прогноза:", err);
  }
}

async function loadKPI() {
  try {
    // KPI только по факту за последние 24 часа (без прогноза)
    const data = await fetchJSON(`${API_BASE}/kpi?window_hours=24`);
    const k = data.kpi;

    // Эти элементы реально существуют в твоём index.html
    const leadsEl = document.getElementById("leadsValue");
    const cplEl = document.getElementById("cplValue");
    const roiEl = document.getElementById("roiValue");

    if (!leadsEl || !cplEl || !roiEl) {
      console.warn("KPI elements not found in DOM");
      return;
    }

    // Факт за 24 часа
    leadsEl.textContent = k.leads_24h;
    cplEl.textContent = Number(k.cpl_24h).toFixed(2);
    roiEl.textContent = Number(k.roi_24h).toFixed(3);

    // Прогноз на 24 часа теперь проставляется в loadForecast()
    // (через note.textContent = `Факт за 24ч / Прогноз на 24ч: ...`)
  } catch (err) {
    console.error("Ошибка загрузки KPI:", err);
  }
}

// helper: формат времени для подписей графика
function formatTs(dt) {
  // FastAPI обычно отдаёт ISO: "2025-01-01T12:00:00"
  // Сделаем "MM-DD HH:00"
  if (!dt) return "";
  const s = String(dt).replace("T", " ");
  // "YYYY-MM-DD HH:MM:SS" -> "MM-DD HH:MM"
  const mmdd = s.slice(5, 10);
  const hhmm = s.slice(11, 16);
  return `${mmdd} ${hhmm}`;
}


// === Аномалии ===
async function loadAnomalies() {
  try {
    const data = await fetchJSON(`${API_BASE}/anomalies?metric=cpl&k=2.5`);

    const monthEl = document.getElementById("anomalyMonth");
    const valueEl = document.getElementById("anomalyValue");
    const zEl = document.getElementById("anomalyZscore");
    const notesEl = document.getElementById("anomaliesNotes");

    if (!monthEl || !valueEl || !zEl || !notesEl) {
      console.warn("Anomaly elements not found in DOM");
      return;
    }

    // Если аномалий нет
    if (!data.anomalies || data.anomalies.length === 0) {
      monthEl.textContent = "—";
      valueEl.textContent = "—";
      zEl.textContent = "—";
      notesEl.innerHTML = `<span class="text-green-700 font-semibold">Аномалий не найдено ✅</span><br>
                           Рекомендации: продолжать текущую стратегию.`;
      return;
    }

    // Берём самую "сильную" аномалию (первую)
    const a = data.anomalies[0];
    const z = Number(a.z_score);

    monthEl.textContent = a.datetime ? formatTs(a.datetime) : "—";
    valueEl.textContent = (a.cpl !== undefined && a.cpl !== null) ? Number(a.cpl).toFixed(2) : "—";
    zEl.textContent = Number.isFinite(z) ? z.toFixed(2) : "—";

    if (Number.isFinite(z)) {
      if (z > 0) {
        notesEl.innerHTML = `<span class="text-red-700 font-semibold">⚠ CPL выше нормы (Z = ${z.toFixed(2)}).</span><br>
                             Рекомендации: оптимизировать расходы и снизить стоимость заявок.`;
      } else {
        notesEl.innerHTML = `<span class="text-red-700 font-semibold">⚠ CPL ниже нормы (Z = ${z.toFixed(2)}).</span><br>
                             Рекомендации: проверить качество лидов и корректность данных.`;
      }
    } else {
      notesEl.innerHTML = `<span class="text-yellow-700 font-semibold">⚠ Не удалось интерпретировать Z-score.</span><br>
                           Рекомендации: проверить данные и расчёт аномалий.`;
    }
  } catch (err) {
    console.error("Ошибка загрузки аномалий:", err);
  }
}

// === Init ===
async function init() {
  await refreshAll();
  setInterval(refreshAll, 30000);
}

init();