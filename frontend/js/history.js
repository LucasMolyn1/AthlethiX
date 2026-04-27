/**
 * history.js — Logique de la page historique.
 */

const TYPE_META = {
  run:      { icon: "🏃", label: "Course" },
  trail:    { icon: "⛰️",  label: "Trail" },
  cycling:  { icon: "🚴", label: "Vélo" },
  swimming: { icon: "🏊", label: "Natation" },
  strength: { icon: "🏋️", label: "Muscu" },
  other:    { icon: "🎯", label: "Autre" },
};

const PAGE_SIZE = 20;
let currentPage = 0;
let totalRows = 0;

function fmtDuration(s) {
  if (!s) return "–";
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h${String(m).padStart(2,"0")}` : `${m} min`;
}
function fmtDist(m) { return m ? (m >= 1000 ? (m/1000).toFixed(1)+" km" : Math.round(m)+" m") : "–"; }
function fmtDate(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleDateString("fr-FR", { weekday:"short", day:"numeric", month:"short", year:"numeric" });
}

function getFilters() {
  return {
    type:      document.getElementById("filter-type").value || null,
    date_from: document.getElementById("filter-from").value || null,
    date_to:   document.getElementById("filter-to").value || null,
    limit:     PAGE_SIZE,
    offset:    currentPage * PAGE_SIZE,
  };
}

async function load() {
  const tbody = document.getElementById("history-body");
  tbody.innerHTML = `<tr><td colspan="7" class="loading">Chargement...</td></tr>`;
  try {
    const rows = await API.getActivities(getFilters());
    totalRows = rows.length;

    document.getElementById("count-label").textContent =
      rows.length === PAGE_SIZE ? `${PAGE_SIZE}+ résultats` :
      rows.length === 0 ? "Aucun résultat" : `${rows.length} résultat(s)`;

    document.getElementById("btn-prev").disabled = currentPage === 0;
    document.getElementById("btn-next").disabled = rows.length < PAGE_SIZE;
    document.getElementById("page-info").textContent = `Page ${currentPage + 1}`;

    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">Aucune activité trouvée.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map(a => {
      const m = TYPE_META[a.type] || TYPE_META.other;
      return `<tr onclick="location.href='activity.html?id=${a.id}'" style="cursor:pointer">
        <td>${fmtDate(a.date)}</td>
        <td><span class="badge badge-${a.type}">${m.icon} ${m.label}</span></td>
        <td>${fmtDist(a.distance)}</td>
        <td>${fmtDuration(a.duration)}</td>
        <td>${a.elevation_gain ? "+"+Math.round(a.elevation_gain)+"m" : "–"}</td>
        <td>${a.avg_hr ? a.avg_hr+" bpm" : "–"}</td>
        <td>${a.calories ? a.calories+" kcal" : "–"}</td>
      </tr>`;
    }).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Erreur : ${e.message}</td></tr>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  load();
  document.getElementById("btn-filter").addEventListener("click", () => { currentPage = 0; load(); });
  document.getElementById("btn-reset").addEventListener("click", () => {
    document.getElementById("filter-type").value = "";
    document.getElementById("filter-from").value = "";
    document.getElementById("filter-to").value = "";
    currentPage = 0;
    load();
  });
  document.getElementById("btn-prev").addEventListener("click", () => { if (currentPage > 0) { currentPage--; load(); } });
  document.getElementById("btn-next").addEventListener("click", () => { if (totalRows >= PAGE_SIZE) { currentPage++; load(); } });
});
