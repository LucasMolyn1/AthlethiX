/**
 * api.js — Couche d'appels vers le backend FastAPI.
 * Toutes les requêtes HTTP passent par ici.
 * BASE_URL pointe vers /api (proxyfié par Apache2 vers FastAPI).
 */

const API = (() => {
  const BASE = "/api";

  async function request(path, options = {}) {
    const res = await fetch(BASE + path, options);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const err = new Error(body.detail || `HTTP ${res.status}`);
      err.status = res.status;
      throw err;
    }
    return res.json();
  }

  return {
    // --- Dashboard ---
    getWeekSummary:      () => request("/dashboard/week"),
    getFitnessCurve:     () => request("/dashboard/fitness"),
    getRecentActivities: () => request("/dashboard/recent"),
    getSyncStatus:       () => request("/dashboard/sync-status"),
    getDashboardExtras:  () => request("/dashboard/extras"),

    // --- Activités ---
    getActivities: (params = {}) => {
      const q = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
      );
      return request("/activities" + (q.toString() ? "?" + q : ""));
    },
    getActivity: (id) => request(`/activities/${id}`),

    // --- Journal ---
    getJournal:    (activityId) => request(`/journal/${activityId}`),
    createJournal: (activityId, data) => request(`/journal/${activityId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
    updateJournal: (activityId, data) => request(`/journal/${activityId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

    // --- Strava ---
    stravaStatus: () => request("/strava/status"),
    syncStrava: (days = 30) => request("/strava/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ days }),
    }),

    // --- Musculation ---
    getSessions: (params = {}) => {
      const q = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
      );
      return request("/strength/sessions" + (q.toString() ? "?" + q : ""));
    },
    getSession:    (id) => request(`/strength/sessions/${id}`),
    createSession: (data) => request("/strength/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
    updateSession: (id, data) => request(`/strength/sessions/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
    deleteSession: (id) => request(`/strength/sessions/${id}`, { method: "DELETE" }),
    getExercises:  (category) => request("/strength/exercises" + (category ? "?category=" + category : "")),
    createExercise: (data) => request("/strength/exercises", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
    getExerciseProgress: (id) => request(`/strength/exercises/${id}/progress`),

    // --- Nutrition ---
    getNutritionLogs: (params = {}) => {
      const q = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
      );
      return request("/nutrition/logs" + (q.toString() ? "?" + q : ""));
    },
    getNutritionLog:    (date) => request(`/nutrition/logs/${date}`),
    createNutritionLog: (data) => request("/nutrition/logs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
    updateNutritionLog: (date, data) => request(`/nutrition/logs/${date}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
    deleteNutritionLog: (date) => request(`/nutrition/logs/${date}`, { method: "DELETE" }),

    // --- Alertes ---
    getAlerts:    (unreadOnly = true) => request(`/alerts?unread_only=${unreadOnly}`),
    markAlertRead: (id) => request(`/alerts/${id}/read`, { method: "PUT" }),
    deleteAlert:   (id) => request(`/alerts/${id}`,      { method: "DELETE" }),
    clearReadAlerts: ()  => request("/alerts",            { method: "DELETE" }),

    // --- Comparaison ---
    comparePeriods: (aFrom, aTo, bFrom, bTo) =>
      request(`/compare/periods?a_from=${aFrom}&a_to=${aTo}&b_from=${bFrom}&b_to=${bTo}`),
    compareExercises: (exAId, exBId) =>
      request(`/compare/exercises?exercise_a_id=${exAId}&exercise_b_id=${exBId}`),
  };
})();
