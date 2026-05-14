let exercises    = [];
let periodChart  = null;
let exerciseChart = null;

const CAT_COLORS = {
  push: "#E8501A", pull: "#22c55e", legs: "#f59e0b", core: "#8b5cf6", cardio: "#ef4444",
};

async function init() {
  setDefaultDates();
  try {
    exercises = await API.getExercises();
    populateExerciseSelects();
  } catch (e) {
    console.warn("Exercices non chargés :", e.message);
  }
  showTab("periods");
}

function setDefaultDates() {
  const today = new Date();
  const fmt = d => d.toISOString().slice(0, 10);
  const sub = (n) => { const d = new Date(today); d.setDate(d.getDate() - n); return d; };

  document.getElementById("a-from").value = fmt(sub(6));
  document.getElementById("a-to").value   = fmt(today);
  document.getElementById("b-from").value = fmt(sub(13));
  document.getElementById("b-to").value   = fmt(sub(7));
}

function populateExerciseSelects() {
  const opts = exercises
    .map(e => `<option value="${e.id}">${e.name}</option>`)
    .join("");
  ["ex-a", "ex-b"].forEach(id => {
    document.getElementById(id).innerHTML =
      `<option value="">— Choisir —</option>` + opts;
  });
  if (exercises.length >= 1) document.getElementById("ex-a").value = exercises[0].id;
  if (exercises.length >= 2) document.getElementById("ex-b").value = exercises[1].id;
}

function showTab(tab) {
  ["periods", "exercises"].forEach(t => {
    const panel = document.getElementById(`tab-${t}`);
    const btn   = document.getElementById(`btn-tab-${t}`);
    const active = t === tab;
    panel.style.display    = active ? "block" : "none";
    btn.style.background   = active ? "var(--accent)"  : "var(--surface2)";
    btn.style.color        = active ? "#fff"            : "var(--text-muted)";
    btn.style.borderColor  = active ? "var(--accent)"  : "var(--border)";
  });
}

// ── Comparaison de périodes ───────────────────────────────────────────────────

async function comparePeriods() {
  const aFrom = document.getElementById("a-from").value;
  const aTo   = document.getElementById("a-to").value;
  const bFrom = document.getElementById("b-from").value;
  const bTo   = document.getElementById("b-to").value;
  if (!aFrom || !aTo || !bFrom || !bTo) {
    showToast("Toutes les dates sont requises", "err");
    return;
  }
  const el = document.getElementById("periods-results");
  el.innerHTML = `<p class="loading">Chargement...</p>`;
  try {
    const { period_a, period_b } = await API.comparePeriods(aFrom, aTo, bFrom, bTo);
    renderPeriodResults(period_a, period_b);
  } catch (e) {
    el.innerHTML = `<p class="empty">Erreur : ${e.message}</p>`;
  }
}

function renderPeriodResults(a, b) {
  const durA = Math.round((a.activities.total_duration_s || 0) / 60);
  const durB = Math.round((b.activities.total_duration_s || 0) / 60);

  const row = (label, vA, vB, unit = "") => {
    const numA = typeof vA === "number" ? vA : parseFloat(vA) || 0;
    const numB = typeof vB === "number" ? vB : parseFloat(vB) || 0;
    const cA = numA > numB ? "var(--green)" : numA < numB ? "var(--text-muted)" : "var(--text)";
    const cB = numB > numA ? "var(--green)" : numB < numA ? "var(--text-muted)" : "var(--text)";
    return `<tr>
      <td style="color:var(--text-muted);font-size:.85rem;padding:9px 12px">${label}</td>
      <td style="text-align:center;font-weight:700;color:${cA};padding:9px 12px">${vA}${unit}</td>
      <td style="text-align:center;font-weight:700;color:${cB};padding:9px 12px">${vB}${unit}</td>
    </tr>`;
  };

  document.getElementById("periods-results").innerHTML = `
    <div class="card" style="margin-bottom:20px">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th style="width:40%"></th>
              <th style="text-align:center;color:#E8501A">
                Période A<br>
                <span style="font-weight:400;text-transform:none;font-size:.78rem">${a.from} → ${a.to}</span>
              </th>
              <th style="text-align:center;color:#34d399">
                Période B<br>
                <span style="font-weight:400;text-transform:none;font-size:.78rem">${b.from} → ${b.to}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            ${row("Jours actifs",             a.active_days,                      b.active_days)}
            ${row("Activités (cardio)",        a.activities.total_count,           b.activities.total_count)}
            ${row("Durée totale",              fmtDur(a.activities.total_duration_s), fmtDur(b.activities.total_duration_s))}
            ${row("Distance",                  a.activities.total_distance_km,     b.activities.total_distance_km, " km")}
            ${row("Séances musculation",       a.strength.sessions_count,          b.strength.sessions_count)}
            ${row("Séries totales (muscu)",    a.strength.total_sets,              b.strength.total_sets)}
          </tbody>
        </table>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Visualisation — comparaison directe</div>
      <div class="chart-container" style="height:260px">
        <canvas id="period-chart"></canvas>
      </div>
    </div>
  `;

  renderPeriodChart(a, b, durA, durB);
}

function renderPeriodChart(a, b, durA, durB) {
  if (periodChart) periodChart.destroy();
  const ctx = document.getElementById("period-chart").getContext("2d");
  periodChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Jours actifs", "Activités", "Durée (min)", "Séances muscu"],
      datasets: [
        {
          label: `A · ${a.from} → ${a.to}`,
          data: [a.active_days, a.activities.total_count, durA, a.strength.sessions_count],
          backgroundColor: "rgba(232,80,26,.75)",
          borderColor: "#E8501A",
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: `B · ${b.from} → ${b.to}`,
          data: [b.active_days, b.activities.total_count, durB, b.strength.sessions_count],
          backgroundColor: "rgba(52,211,153,.75)",
          borderColor: "#34d399",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#999999" } } },
      scales: {
        x: { ticks: { color: "#999999" }, grid: { color: "#EEEDE8" } },
        y: { ticks: { color: "#999999" }, grid: { color: "#EEEDE8" }, beginAtZero: true },
      },
    },
  });
}

// ── Comparaison d'exercices ───────────────────────────────────────────────────

async function compareExercises() {
  const idA = document.getElementById("ex-a").value;
  const idB = document.getElementById("ex-b").value;
  if (!idA || !idB) { showToast("Sélectionne deux exercices", "err"); return; }

  const el = document.getElementById("exercises-results");
  el.innerHTML = `<p class="loading">Chargement...</p>`;
  try {
    const { exercise_a, exercise_b } = await API.compareExercises(parseInt(idA), parseInt(idB));
    renderExerciseResults(exercise_a, exercise_b);
  } catch (e) {
    el.innerHTML = `<p class="empty">Erreur : ${e.message}</p>`;
  }
}

function renderExerciseResults(exA, exB) {
  const card = (ex, color) => {
    const catColor = CAT_COLORS[ex.exercise.category] || "#999999";
    const pr = ex.pr;
    return `
      <div class="card">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
          <div style="width:4px;height:36px;background:${color};border-radius:2px;flex-shrink:0"></div>
          <div>
            <div style="font-size:1rem;font-weight:600">${ex.exercise.name}</div>
            <span style="display:inline-block;margin-top:3px;font-size:.72rem;font-weight:700;
                         text-transform:uppercase;letter-spacing:.04em;
                         background:${catColor}22;color:${catColor};
                         padding:2px 8px;border-radius:4px">${ex.exercise.category}</span>
          </div>
        </div>
        ${pr ? `
          <div class="detail-grid">
            <div class="detail-stat">
              <div class="label">Meilleur 1RM</div>
              <div class="value" style="color:var(--green)">${pr.best_1rm} kg</div>
            </div>
            <div class="detail-stat">
              <div class="label">Date PR</div>
              <div class="value" style="font-size:1.05rem">${pr.date}</div>
            </div>
            <div class="detail-stat">
              <div class="label">Poids max</div>
              <div class="value">${pr.max_weight} kg</div>
            </div>
            <div class="detail-stat">
              <div class="label">Séances</div>
              <div class="value">${ex.history.length}</div>
            </div>
          </div>
        ` : `<p class="empty" style="padding:12px 0;text-align:left">Aucune donnée enregistrée</p>`}
      </div>
    `;
  };

  document.getElementById("exercises-results").innerHTML = `
    <div class="grid-2" style="margin-bottom:20px">
      ${card(exA, "#E8501A")}
      ${card(exB, "#22c55e")}
    </div>
    <div class="card">
      <div class="card-title">Progression 1RM comparée (formule Epley)</div>
      <div class="chart-container" style="height:280px">
        <canvas id="exercise-chart"></canvas>
      </div>
    </div>
  `;

  if (exA.history.length || exB.history.length) {
    renderExerciseChart(exA, exB);
  } else {
    document.querySelector("#exercise-chart").closest(".card").innerHTML +=
      `<p class="empty">Aucune donnée pour tracer le graphique</p>`;
  }
}

function renderExerciseChart(exA, exB) {
  if (exerciseChart) exerciseChart.destroy();

  // Union des dates, triées chronologiquement
  const allDates = [...new Set([
    ...exA.history.map(h => h.date),
    ...exB.history.map(h => h.date),
  ])].sort();

  const mapA = Object.fromEntries(exA.history.map(h => [h.date, h.best_1rm]));
  const mapB = Object.fromEntries(exB.history.map(h => [h.date, h.best_1rm]));

  const ctx = document.getElementById("exercise-chart").getContext("2d");
  exerciseChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: allDates,
      datasets: [
        {
          label: exA.exercise.name,
          data: allDates.map(d => mapA[d] ?? null),
          borderColor: "#E8501A",
          backgroundColor: "rgba(232,80,26,.07)",
          tension: 0.3,
          spanGaps: true,
          pointRadius: 4,
          pointBackgroundColor: "#E8501A",
          fill: true,
        },
        {
          label: exB.exercise.name,
          data: allDates.map(d => mapB[d] ?? null),
          borderColor: "#22c55e",
          backgroundColor: "rgba(34,197,94,.07)",
          tension: 0.3,
          spanGaps: true,
          pointRadius: 4,
          pointBackgroundColor: "#22c55e",
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#999999" } } },
      scales: {
        x: {
          ticks: { color: "#999999", maxTicksLimit: 10 },
          grid:  { color: "#EEEDE8" },
        },
        y: {
          ticks: { color: "#999999", callback: v => v + " kg" },
          grid:  { color: "#EEEDE8" },
          beginAtZero: false,
        },
      },
    },
  });
}

// ── Utilitaires ───────────────────────────────────────────────────────────────

function fmtDur(secs) {
  if (!secs) return "0 min";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return h > 0 ? `${h}h ${String(m).padStart(2, "0")}` : `${m} min`;
}

function showToast(msg, type = "ok") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `show ${type}`;
  setTimeout(() => (t.className = ""), 3000);
}

init();
