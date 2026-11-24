(function () {
  'use strict';
  async function fetchWithAbort(url, opts, timeoutMs) {
    const ms = Number(timeoutMs || 15000);
    if (typeof AbortController === 'function') {
      const ctrl = new AbortController();
      const timer = setTimeout(() => { try { ctrl.abort(); } catch (_) {} }, ms);
      try {
        return await fetch(url, Object.assign({}, opts || {}, { signal: ctrl.signal }));
      } finally {
        clearTimeout(timer);
      }
    }
    return await fetch(url, opts || {});
  }
  window.NexusApi = {
    fetchWithAbort: fetchWithAbort
  };
})();

  // OPT-266-02 / OPT-266-09: Adaptive Heartbeat & Long-Poll Helper
  function computeAdaptivePollIntervalMs(isHidden, consecutiveIdleTicks) {
    if (isHidden) return 15000;
    const ticks = Math.max(0, Number(consecutiveIdleTicks) || 0);
    if (ticks >= 10) return 8000;
    if (ticks >= 4) return 5000;
    return 3000;
  }
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.api = Object.assign(window.NexusModules.api || {}, {
    computeAdaptivePollIntervalMs: computeAdaptivePollIntervalMs
  });
  window.computeAdaptivePollIntervalMs = computeAdaptivePollIntervalMs;


// OPT-287-07: API URL & error normalization helpers
function buildApiUrl(path, queryObj) {
  var base = String(path || '/api/status');
  if (!queryObj || typeof queryObj !== 'object') return base;
  var pairs = Object.keys(queryObj).filter(function (k) { return queryObj[k] !== undefined && queryObj[k] !== null; })
    .map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(String(queryObj[k])); });
  return pairs.length ? (base + (base.indexOf('?') >= 0 ? '&' : '?') + pairs.join('&')) : base;
}
function parseApiError(payload, fallback) {
  if (payload && typeof payload === 'object') return String(payload.error || payload.message || fallback || '请求失败');
  return String(fallback || '请求失败');
}
if (typeof window !== 'undefined') {
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.api = Object.assign(window.NexusModules.api || {}, { buildApiUrl: buildApiUrl, parseApiError: parseApiError });
}
