/**
 * dashboard.js — Logique de la page d'accueil (index.html).
 */

// Icônes et labels par type d'activité
const TYPE_META = {
  run:      { icon: "🏃", label: "Course",    cls: "run" },
  trail:    { icon: "⛰️",  label: "Trail",     cls: "trail" },
  cycling:  { icon: "🚴", label: "Vélo",      cls: "cycling" },
  swimming: { icon: "🏊", label: "Natation",  cls: "swimming" },
  strength: { icon: "🏋️", label: "Muscu",     cls: "strength" },
  other:    { icon: "🎯", label: "Autre",     cls: "other" },
};

function typeMeta(t) { return TYPE_META[t] || TYPE_META.other; }

// Formatters
function fmtDuration(secs) {
  if (!secs) return "--";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return h > 0 ? `${h}h${String(m).padStart(2,"0")}` : `${m}min`;
}
function fmtDist(m) {
  if (!m) return "--";
  return m >= 1000 ? (m / 1000).toFixed(1) + " km" : Math.round(m) + " m";
}
function fmtDate(iso) {
  if (!iso) return "--";
  return new Date(iso).toLocaleDateString("fr-FR", { weekday:"short", day:"numeric", month:"short" });
}
function toast(msg, type = "ok") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = "show " + type;
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = ""; }, 3500);
}

// ---- Sync status ----
async function loadSyncStatus() {
  try {
    const s = await API.getSyncStatus();
    const dot = s.status === "ok" ? "ok" : s.status === "never" ? "never" : "error";
    const label = s.last_sync
      ? "Sync " + new Date(s.last_sync).toLocaleString("fr-FR", { day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" })
      : "Jamais synchronisé";
    document.getElementById("sync-status").innerHTML =
      `<span class="sync-dot ${dot}"></span>${label}`;
  } catch (_) {}
}

// ---- Semaine courante ----
async function loadWeekSummary() {
  const container = document.getElementById("week-stats");
  try {
    const rows = await API.getWeekSummary();
    if (!rows.length) {
      container.innerHTML = '<p class="empty">Aucune activité cette semaine.</p>';
      return;
    }
    container.innerHTML = rows.map(r => {
      const m = typeMeta(r.type);
      return `
        <div class="stat-card">
          <div class="label">${m.icon} ${m.label}</div>
          <div class="value">${r.sessions}</div>
          <div class="unit">séance${r.sessions > 1 ? "s" : ""} · ${fmtDist(r.total_distance)}${r.total_elevation ? " · +"+Math.round(r.total_elevation)+"m" : ""}</div>
        </div>`;
    }).join("");
  } catch (e) {
    container.innerHTML = `<p class="empty">Erreur : ${e.message}</p>`;
  }
}

// ---- Courbe de forme ----
async function loadFitnessChart() {
  const ctx = document.getElementById("fitness-chart").getContext("2d");
  try {
    const data = await API.getFitnessCurve();
    if (!data.length) return;
    new Chart(ctx, {
      type: "line",
      data: {
        labels: data.map(d => d.day.slice(5)),  // MM-DD
        datasets: [{
          label: "Charge d'entraînement",
          data: data.map(d => Math.round(d.load)),
          borderColor: "#E8501A",
          backgroundColor: "rgba(232,80,26,.08)",
          fill: true,
          tension: .4,
          pointRadius: 3,
          pointHoverRadius: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: "#EEEDE8" }, ticks: { color: "#999999", maxTicksLimit: 8 } },
          y: { grid: { color: "#EEEDE8" }, ticks: { color: "#999999" }, beginAtZero: true },
        },
      },
    });
  } catch (_) {}
}

// ---- Dernières activités ----
async function loadRecent() {
  const el = document.getElementById("recent-list");
  try {
    const acts = await API.getRecentActivities();
    if (!acts.length) { el.innerHTML = '<li class="empty">Aucune activité. Lance une synchronisation.</li>'; return; }
    el.innerHTML = acts.map(a => {
      const m = typeMeta(a.type);
      return `
        <li class="activity-item" onclick="location.href='activity.html?id=${a.id}'">
          <div class="activity-icon icon-${m.cls}">${m.icon}</div>
          <div class="activity-info">
            <div class="name">${m.label} — ${fmtDate(a.date)}</div>
            <div class="meta">${a.avg_hr ? "FC moy. "+a.avg_hr+" bpm" : ""}</div>
          </div>
          <div class="activity-stats">
            <div class="primary">${fmtDist(a.distance)}</div>
            <div class="secondary">${fmtDuration(a.duration)}</div>
          </div>
        </li>`;
    }).join("");
  } catch (e) {
    el.innerHTML = `<li class="empty">Erreur : ${e.message}</li>`;
  }
}

// ---- Sync manuelle ----
async function triggerSync() {
  const btn = document.getElementById("btn-sync");
  btn.disabled = true;
  btn.textContent = "Synchronisation...";
  try {
    const r = await API.syncStrava(30);
    if (r.error) { toast("Erreur : " + r.error, "err"); }
    else { toast(`+${r.added} activité(s) ajoutée(s)`, "ok"); await loadAll(); }
  } catch (e) {
    toast("Erreur réseau : " + e.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "Synchroniser";
  }
}

// ---- Initialisation bouton sync (état connecté / non connecté) ----
async function initSyncButton() {
  const btn = document.getElementById("btn-sync");
  if (!btn) return;
  try {
    const { connected } = await API.stravaStatus();
    if (connected) {
      btn.addEventListener("click", triggerSync);
    } else {
      btn.textContent = "Connecter Strava";
      btn.style.background = "#111111";
      btn.onclick = () => { window.location.href = "/api/strava/auth"; };
    }
  } catch (_) {
    btn.addEventListener("click", triggerSync);
  }
}

// ---- Widget nutrition + musculation semaine ----
async function loadExtras() {
  try {
    const d = await API.getDashboardExtras();
    renderNutritionWidget(d.nutrition);
    renderStrengthWidget(d.strength);
  } catch (_) {}
}

function renderNutritionWidget(n) {
  const el = document.getElementById("widget-nutrition");
  if (!el) return;
  const hydStr   = n.avg_hydration != null ? n.avg_hydration + " L" : "—";
  const scoreStr = n.avg_score     != null ? n.avg_score + " / 10"  : "—";
  const logged   = n.days_logged;
  el.innerHTML = `
    <div class="stat-card">
      <div class="label">💧 Hydratation moy.</div>
      <div class="value">${hydStr}</div>
      <div class="unit">${logged} jour${logged !== 1 ? "s" : ""} loggé${logged !== 1 ? "s" : ""}</div>
    </div>
    <div class="stat-card">
      <div class="label">🥗 Score nutrition moy.</div>
      <div class="value">${scoreStr}</div>
      <div class="unit">sur la semaine</div>
    </div>`;
}

function renderStrengthWidget(s) {
  const el = document.getElementById("widget-strength");
  if (!el) return;
  const vol = s.total_volume;
  const volStr = vol > 0
    ? (vol >= 1000 ? (vol / 1000).toFixed(1) + " t" : vol + " kg")
    : "—";
  el.innerHTML = `
    <div class="stat-card">
      <div class="label">💪 Séances muscu</div>
      <div class="value">${s.sessions_count}</div>
      <div class="unit">${s.total_sets} série${s.total_sets !== 1 ? "s" : ""} au total</div>
    </div>
    <div class="stat-card">
      <div class="label">🏋️ Volume soulevé</div>
      <div class="value">${volStr}</div>
      <div class="unit">cette semaine</div>
    </div>`;
}

async function loadAll() {
  await Promise.all([loadSyncStatus(), loadWeekSummary(), loadRecent()]);
}

document.addEventListener("DOMContentLoaded", () => {
  loadAll();
  loadFitnessChart();
  loadExtras();
  initSyncButton();

  // Retour depuis le flow OAuth Strava
  const params = new URLSearchParams(location.search);
  if (params.get("strava") === "connected") {
    toast("Strava connecté — tu peux synchroniser !", "ok");
    history.replaceState({}, "", "/");
    initSyncButton();
  } else if (params.get("strava") === "error") {
    toast("Connexion Strava échouée, réessaie.", "err");
    history.replaceState({}, "", "/");
  }
});
