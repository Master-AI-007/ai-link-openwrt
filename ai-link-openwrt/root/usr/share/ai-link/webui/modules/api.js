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

