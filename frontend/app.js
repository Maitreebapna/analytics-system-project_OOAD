const PAGE_SIZE = 10;
const PERFORMANCE_ORDER = ["Viral Hit", "High Engagement", "Steady Growth"];
const VIEW_COPY = {
  overview: ["CHANNEL PERFORMANCE", "Overview"],
  videos: ["CONTENT LIBRARY", "Video library"],
  learning: ["PERSONALIZED PLAYLISTS", "Learning paths"],
};

const state = {
  hasSnapshot: false,
  dashboard: null,
  videos: [],
  videoTotal: 0,
  page: 0,
  activeView: "overview",
  recommendationTopic: "",
};

const $ = (selector) => document.querySelector(selector);
const numberFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
const dateFormat = new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" });

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function formatNumber(value) {
  return numberFormat.format(Number(value) || 0);
}

function formatCompact(value) {
  const numeric = Number(value) || 0;
  if (numeric >= 1_000_000_000) return `${(numeric / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
  if (numeric >= 1_000_000) return `${(numeric / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (numeric >= 1_000) return `${(numeric / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  return formatNumber(numeric);
}

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dateFormat.format(date);
}

function formatDuration(minutes) {
  const value = Math.max(0, Math.round(Number(minutes) || 0));
  const hours = Math.floor(value / 60);
  const remaining = value % 60;
  return hours ? `${hours}h${remaining ? ` ${remaining}m` : ""}` : `${remaining} min`;
}

function performanceClass(category) {
  if (category === "Viral Hit") return "pill-viral";
  if (category === "High Engagement") return "pill-high";
  return "pill-steady";
}

function performanceBadge(category) {
  return `<span class="performance-pill ${performanceClass(category)}">${escapeHtml(category || "Uncategorized")}</span>`;
}

function videoCell(video) {
  const videoId = String(video.video_id || "");
  const link = !videoId.startsWith("mock-")
    ? `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`
    : "";
  const title = escapeHtml(video.title);
  const titleMarkup = link
    ? `<a class="video-title" href="${link}" target="_blank" rel="noopener noreferrer">${title}</a>`
    : `<span class="video-title">${title}</span>`;
  return `<div class="video-cell"><span class="video-thumb"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3V9Z"/></svg></span><span>${titleMarkup}<span class="video-subtitle">${escapeHtml(formatDate(video.published_at))}</span></span></div>`;
}

async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new Error("Unable to reach the analytics API. Check that the server is running and try again.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : `Request failed (${response.status}).`;
    throw new Error(detail);
  }
  return body;
}

function showToast(message, type = "success", title = type === "success" ? "All set" : "Something went wrong") {
  const toast = document.createElement("div");
  toast.className = `toast${type === "error" ? " is-error" : ""}`;
  toast.setAttribute("role", type === "error" ? "alert" : "status");
  toast.innerHTML = `<span class="toast-mark">${type === "error" ? "!" : "✓"}</span><span class="toast-copy"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(message)}</span></span>`;
  $("#toast-region").append(toast);
  window.setTimeout(() => toast.remove(), 5200);
}

function setView(view) {
  if (!VIEW_COPY[view]) return;
  state.activeView = view;
  document.querySelectorAll(".nav-link").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === view);
  });
  document.querySelectorAll(".view-panel").forEach((panel) => {
    panel.classList.toggle("is-visible", panel.id === `view-${view}`);
  });
  $("#page-eyebrow").textContent = VIEW_COPY[view][0];
  $("#page-title").textContent = VIEW_COPY[view][1];
  $("#empty-state").classList.toggle("is-hidden", state.hasSnapshot);
  if (view === "videos" && state.hasSnapshot) loadVideoPage();
}

function setHasSnapshot(value) {
  state.hasSnapshot = value;
  document.querySelectorAll(".view-panel").forEach((panel) => {
    panel.classList.toggle("is-hidden", !value);
  });
  $("#empty-state").classList.toggle("is-hidden", value);
  document.querySelectorAll(".nav-link").forEach((button) => {
    button.disabled = !value;
    button.setAttribute("aria-disabled", String(!value));
  });
  if (!value) {
    $("#channel-name").textContent = "Your channel analytics";
    $("#channel-id").textContent = "Connect your first data snapshot";
    $("#data-source").textContent = "Waiting for data";
  }
}

async function getAllVideos() {
  const all = [];
  let offset = 0;
  let total = 0;
  do {
    const page = await apiRequest(`/api/videos?limit=200&offset=${offset}`);
    all.push(...page.items);
    total = page.total;
    offset += page.items.length;
    if (!page.items.length) break;
  } while (offset < total);
  return all;
}

async function loadInitialData() {
  try {
    const health = await apiRequest("/api/health");
    if (!health.has_snapshot) {
      setHasSnapshot(false);
      return;
    }
    await loadSnapshot();
  } catch (error) {
    showToast(error.message, "error", "Could not load analytics");
    setHasSnapshot(false);
  }
}

async function loadSnapshot() {
  const [dashboard, videos] = await Promise.all([
    apiRequest("/api/dashboard"),
    getAllVideos(),
  ]);
  state.dashboard = dashboard;
  state.videos = videos;
  state.videoTotal = videos.length;
  setHasSnapshot(true);
  renderDashboard();
  populateTopicOptions();
  await loadVideoPage();
  $("#updated-label").innerHTML = `<span class="live-dot"></span> Updated ${escapeHtml(formatDate(dashboard.captured_at))}`;
}

function renderDashboard() {
  const dashboard = state.dashboard;
  if (!dashboard) return;
  const { channel, metrics } = dashboard;
  $("#channel-name").textContent = channel.channel_name;
  $("#channel-id").textContent = channel.channel_id;
  $("#channel-avatar").textContent = (channel.channel_name || "S").trim().charAt(0).toUpperCase();
  $("#data-source").textContent = dashboard.data_source === "live" ? "Live YouTube data" : "Illustrative sample data";
  $("#snapshot-number").textContent = `#${dashboard.snapshot_id}`;
  $("#metric-subscribers").textContent = formatCompact(channel.subscribers);
  $("#metric-views").textContent = formatCompact(metrics.total_views);
  $("#metric-engagement").textContent = `${(Number(metrics.average_engagement_rate) || 0).toFixed(2)}%`;
  $("#metric-videos").textContent = formatNumber(metrics.videos_analyzed);
  $("#video-nav-count").textContent = formatNumber(metrics.videos_analyzed);
  $("#video-result-count").textContent = `${formatNumber(metrics.videos_analyzed)} ${metrics.videos_analyzed === 1 ? "video" : "videos"}`;
  renderPerformanceMix();
  renderTopVideos();
  renderRecentVideos();
}

function renderPerformanceMix() {
  const counts = Object.fromEntries(PERFORMANCE_ORDER.map((category) => [category, 0]));
  state.videos.forEach((video) => {
    if (Object.hasOwn(counts, video.performance_category)) counts[video.performance_category] += 1;
  });
  const total = state.videos.length;
  const classes = { "Viral Hit": "bar-viral", "High Engagement": "bar-high", "Steady Growth": "bar-steady" };
  $("#performance-chart").innerHTML = PERFORMANCE_ORDER.map((category) => {
    const count = counts[category];
    const percent = total ? (count / total) * 100 : 0;
    return `<div class="distribution-row"><span>${escapeHtml(category)}</span><span class="distribution-track"><span class="distribution-bar ${classes[category]}" style="display:block;width:${percent}%"></span></span><span class="distribution-count">${count}</span></div>`;
  }).join("");
}

function renderTopVideos() {
  const leaders = [...state.videos].sort((a, b) => Number(b.views) - Number(a.views)).slice(0, 4);
  $("#top-videos").innerHTML = leaders.length
    ? leaders.map((video, index) => `<div class="leader-row"><span class="leader-rank">${String(index + 1).padStart(2, "0")}</span><div><div class="leader-title" title="${escapeHtml(video.title)}">${escapeHtml(video.title)}</div><div class="leader-topic">${escapeHtml(video.topic)}</div></div><span class="leader-views">${formatCompact(video.views)} views</span></div>`).join("")
    : `<div class="empty-table">No videos are available in this snapshot.</div>`;
}

function renderRecentVideos() {
  const latest = [...state.videos]
    .sort((a, b) => new Date(b.published_at) - new Date(a.published_at))
    .slice(0, 5);
  $("#recent-videos").innerHTML = latest.length
    ? latest.map((video) => `<tr><td>${videoCell(video)}</td><td><span class="topic-chip">${escapeHtml(video.topic)}</span></td><td>${formatCompact(video.views)}</td><td><span class="engagement-value">${(Number(video.engagement_rate) || 0).toFixed(2)}%</span></td><td>${performanceBadge(video.performance_category)}</td></tr>`).join("")
    : `<tr><td class="empty-table" colspan="5">No videos are available in this snapshot.</td></tr>`;
}

function populateTopicOptions() {
  const topics = [...new Set(state.videos.map((video) => video.topic).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b));
  const topicFilter = $("#topic-filter");
  const recommendationTopic = $("#recommendation-topic");
  const selectedFilter = topicFilter.value;
  const selectedRecommendation = recommendationTopic.value || state.recommendationTopic;
  topicFilter.innerHTML = `<option value="">All topics</option>${topics.map((topic) => `<option value="${escapeHtml(topic)}">${escapeHtml(topic)}</option>`).join("")}`;
  recommendationTopic.innerHTML = `<option value="">Choose a topic</option>${topics.map((topic) => `<option value="${escapeHtml(topic)}">${escapeHtml(topic)}</option>`).join("")}`;
  if (topics.includes(selectedFilter)) topicFilter.value = selectedFilter;
  if (topics.includes(selectedRecommendation)) recommendationTopic.value = selectedRecommendation;
}

function currentPageUrl() {
  const params = new URLSearchParams();
  const search = $("#video-search").value.trim();
  const topic = $("#topic-filter").value;
  const performance = $("#performance-filter").value;
  if (search) params.set("search", search);
  if (topic) params.set("topic", topic);
  if (performance) params.set("performance_category", performance);
  params.set("sort_by", $("#sort-filter").value);
  params.set("sort_order", "desc");
  params.set("limit", String(PAGE_SIZE));
  params.set("offset", String(state.page * PAGE_SIZE));
  return `/api/videos?${params.toString()}`;
}

async function loadVideoPage() {
  if (!state.hasSnapshot) return;
  try {
    const result = await apiRequest(currentPageUrl());
    state.videoTotal = result.total;
    $("#library-videos").innerHTML = result.items.length
      ? result.items.map((video) => `<tr><td>${videoCell(video)}</td><td><span class="topic-chip">${escapeHtml(video.topic)}</span></td><td>${formatCompact(video.views)}</td><td>${formatCompact(video.likes)}</td><td><span class="engagement-value">${(Number(video.engagement_rate) || 0).toFixed(2)}%</span></td><td>${escapeHtml(formatDate(video.published_at))}</td><td>${performanceBadge(video.performance_category)}</td></tr>`).join("")
      : `<tr><td class="empty-table" colspan="7">No videos match those filters. Try a different search or topic.</td></tr>`;
    const start = result.total ? result.offset + 1 : 0;
    const end = Math.min(result.offset + result.items.length, result.total);
    $("#pagination-summary").textContent = result.total ? `Showing ${start}–${end} of ${formatNumber(result.total)} videos` : "No matching videos";
    $("#page-number").textContent = result.total ? `${state.page + 1} / ${Math.ceil(result.total / PAGE_SIZE)}` : "0 / 0";
    $("#previous-page").disabled = state.page === 0;
    $("#next-page").disabled = result.offset + result.items.length >= result.total;
    const dashboardCount = state.dashboard?.metrics?.videos_analyzed ?? result.total;
    $("#video-result-count").textContent = `${formatNumber(result.total)} ${result.total === 1 ? "video" : "videos"} found · ${formatNumber(dashboardCount)} total`;
  } catch (error) {
    showToast(error.message, "error", "Could not load videos");
  }
}

async function buildRecommendation(event) {
  event.preventDefault();
  const topic = $("#recommendation-topic").value;
  const maxDuration = $("#duration-filter").value;
  if (!topic) {
    $("#recommendation-topic").focus();
    return;
  }
  const submit = event.currentTarget.querySelector("button[type='submit']");
  submit.disabled = true;
  try {
    const params = new URLSearchParams({ topic, max_duration_mins: maxDuration });
    const result = await apiRequest(`/api/recommendations?${params.toString()}`);
    state.recommendationTopic = result.topic;
    $("#pathway-title").textContent = `${result.topic} learning path`;
    $("#pathway-count").textContent = `${result.items.length} ${result.items.length === 1 ? "video" : "videos"} · up to ${formatDuration(maxDuration)}`;
    $("#recommendation-list").innerHTML = result.items.length
      ? result.items.map((item) => `<article class="recommendation-item"><span class="step-number">${String(item.step).padStart(2, "0")}</span><div><h3>${escapeHtml(item.title)}</h3><div class="recommendation-meta"><span>${escapeHtml(item.topic)}</span><span>${formatDuration(item.duration_mins)}</span><span>${formatCompact(item.views)} views</span></div></div><div class="recommendation-score">${(Number(item.engagement_rate) || 0).toFixed(2)}%<span>engagement</span></div></article>`).join("")
      : `<div class="empty-inline"><div class="empty-icon">↗</div><strong>No videos fit that path yet</strong><span>Try a longer duration or choose another topic.</span></div>`;
  } catch (error) {
    showToast(error.message, "error", "Could not build learning path");
  } finally {
    submit.disabled = false;
  }
}

function openRefreshDialog() {
  const dialog = $("#refresh-dialog");
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  $("#channel-input").focus();
}

async function refreshSnapshot(event) {
  event.preventDefault();
  const submit = $("#submit-refresh");
  const label = submit.querySelector("span");
  const previousLabel = label.textContent;
  const channelId = $("#channel-input").value.trim();
  submit.disabled = true;
  label.textContent = "Fetching data…";
  try {
    const result = await apiRequest("/api/refresh", {
      method: "POST",
      body: JSON.stringify(channelId ? { channel_id: channelId } : {}),
    });
    $("#refresh-dialog").close();
    $("#channel-input").value = "";
    await loadSnapshot();
    const sourceMessage = result.data_source === "live"
      ? `${result.channel_name} is up to date · ${formatNumber(result.videos_analyzed)} videos analyzed.`
      : `Sample analytics loaded for ${result.channel_name}${result.fallback_reason ? ` · ${result.fallback_reason}` : ""}.`;
    showToast(sourceMessage, "success", "Snapshot refreshed");
  } catch (error) {
    showToast(error.message, "error", "Refresh failed");
  } finally {
    submit.disabled = false;
    label.textContent = previousLabel;
  }
}

function bindEvents() {
  document.querySelectorAll(".nav-link").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
  document.querySelectorAll("[data-go]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.go));
  });
  $("#open-refresh").addEventListener("click", openRefreshDialog);
  $("#empty-refresh").addEventListener("click", openRefreshDialog);
  $("#close-refresh").addEventListener("click", () => $("#refresh-dialog").close());
  $("#cancel-refresh").addEventListener("click", () => $("#refresh-dialog").close());
  $("#refresh-form").addEventListener("submit", refreshSnapshot);
  $("#recommendation-form").addEventListener("submit", buildRecommendation);

  let searchTimer;
  $("#video-search").addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    state.page = 0;
    searchTimer = window.setTimeout(loadVideoPage, 220);
  });
  [$("#topic-filter"), $("#performance-filter"), $("#sort-filter")].forEach((control) => {
    control.addEventListener("change", () => {
      state.page = 0;
      loadVideoPage();
    });
  });
  $("#previous-page").addEventListener("click", () => {
    if (state.page > 0) {
      state.page -= 1;
      loadVideoPage();
    }
  });
  $("#next-page").addEventListener("click", () => {
    if ((state.page + 1) * PAGE_SIZE < state.videoTotal) {
      state.page += 1;
      loadVideoPage();
    }
  });
}

bindEvents();
loadInitialData();
