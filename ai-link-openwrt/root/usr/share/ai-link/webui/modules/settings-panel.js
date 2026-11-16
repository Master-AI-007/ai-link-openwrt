(function () {
  'use strict';
  function consumeLuciBridgeTokenHash(storage) {
    try {
      const h = String(window.location.hash || '');
      const m = h.match(/(?:^|[#&])bridge_token=([^&]+)/);
      if (m && m[1]) {
        const tok = decodeURIComponent(m[1]).trim();
        if (tok && storage) {
          storage.set('ailink_panel_token', tok);
        }
        if (window.history && typeof window.history.replaceState === 'function') {
          window.history.replaceState(null, document.title, window.location.pathname + window.location.search);
        }
      }
    } catch (_) {}
  }
  window.NexusSettingsPanel = {
    consumeLuciBridgeTokenHash: consumeLuciBridgeTokenHash
  };
})();
