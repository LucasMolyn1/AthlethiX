/**
 * journal.js — Vue journal : liste les activités récentes.
 * Pour chaque activité, tente de charger son journal et affiche un indicateur.
 */

const TYPE_META = {
  run:      { icon: "🏃", label: "Course" },
  trail:    { icon: "⛰️",  label: "Trail" },
  cycling:  { icon: "🚴", label: "Vélo" },
  swimming: { icon: "🏊", label: "Natation" },
  strength: { icon: "🏋️", label: "Muscu" },
  other:    { icon: "🎯", label: "Autre" },
};

function fmtDate(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleDateString("fr-FR", { weekday:"short", day:"numeric", month:"short" });
}
function fmtDuration(s) {
  if (!s) return "–";
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h${String(m).padStart(2,"0")}` : `${m} min`;
}
function fmtDist(m) { return m ? (m >= 1000 ? (m/1000).toFixed(1)+" km" : Math.round(m)+" m") : "–"; }

async function loadJournalList() {
  const el = document.getElementById("journal-list");
  try {
    const acts = await API.getActivities({ limit: 20 });
    if (!acts.length) { el.innerHTML = '<li class="empty">Aucune activité synchronisée.</li>'; return; }

    // Charge les journaux en parallèle (ignore les 404)
    const journals = await Promise.all(
      acts.map(a => API.getJournal(a.id).catch(() => null))
    );

    el.innerHTML = acts.map((a, i) => {
      const m = TYPE_META[a.type] || TYPE_META.other;
      const hasJ = journals[i] !== null;
      return `
        <li class="activity-item" onclick="location.href='activity.html?id=${a.id}'">
          <div class="activity-icon icon-${a.type}">${m.icon}</div>
          <div class="activity-info">
            <div class="name">${m.label} — ${fmtDate(a.date)}</div>
            <div class="meta">${fmtDist(a.distance)} · ${fmtDuration(a.duration)}</div>
          </div>
          <div style="flex-shrink:0">
            ${hasJ
              ? `<span style="color:var(--green);font-size:.8rem">✓ Journal rempli</span>`
              : `<span style="color:var(--text-muted);font-size:.8rem">Ajouter un journal</span>`
            }
          </div>
        </li>`;
    }).join("");
  } catch (e) {
    el.innerHTML = `<li class="empty">Erreur : ${e.message}</li>`;
  }
}

document.addEventListener("DOMContentLoaded", loadJournalList);
