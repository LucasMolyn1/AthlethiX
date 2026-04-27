/**
 * alerts.js — Bannière d'alertes partagée entre toutes les pages.
 * Inclure après api.js. Inject automatiquement la bannière si des alertes
 * non lues existent, juste après l'ouverture de <main class="main-content">.
 */

const ALERT_ICONS = {
  danger:  "🔴",
  warning: "🟠",
  info:    "🔵",
  success: "🟢",
};

const ALERT_COLORS = {
  danger:  { bg: "rgba(248,113,113,.12)", border: "#f87171" },
  warning: { bg: "rgba(251,146,60,.12)",  border: "#fb923c" },
  info:    { bg: "rgba(79,142,247,.12)",  border: "#4f8ef7" },
  success: { bg: "rgba(52,211,153,.12)",  border: "#34d399" },
};

async function loadAlertsBanner() {
  let alerts;
  try {
    alerts = await API.getAlerts(true);
  } catch (_) {
    return;
  }
  if (!alerts.length) return;

  const main = document.querySelector(".main-content");
  if (!main) return;

  const banner = document.createElement("div");
  banner.id = "alerts-banner";
  banner.style.cssText = "margin-bottom:20px";

  banner.innerHTML = alerts.map(a => {
    const col = ALERT_COLORS[a.level] || ALERT_COLORS.info;
    return `
      <div id="alert-${a.id}" style="
        display:flex;align-items:flex-start;gap:10px;
        background:${col.bg};border:1px solid ${col.border};
        border-radius:8px;padding:12px 14px;margin-bottom:8px;
      ">
        <span style="font-size:1rem;flex-shrink:0">${ALERT_ICONS[a.level] || "ℹ️"}</span>
        <span style="flex:1;font-size:.88rem;line-height:1.5">${escHtml(a.message)}</span>
        <button
          onclick="dismissAlert(${a.id})"
          style="background:none;border:none;color:var(--text-muted);cursor:pointer;
                 font-size:1rem;padding:0;line-height:1;flex-shrink:0"
          title="Marquer comme lue">✕</button>
      </div>
    `;
  }).join("");

  main.insertBefore(banner, main.firstChild);
}

async function dismissAlert(id) {
  try {
    await API.markAlertRead(id);
    const el = document.getElementById(`alert-${id}`);
    if (el) el.remove();
    const banner = document.getElementById("alerts-banner");
    if (banner && !banner.querySelector("[id^='alert-']")) banner.remove();
  } catch (_) {}
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

loadAlertsBanner();
