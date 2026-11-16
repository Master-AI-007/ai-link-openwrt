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
