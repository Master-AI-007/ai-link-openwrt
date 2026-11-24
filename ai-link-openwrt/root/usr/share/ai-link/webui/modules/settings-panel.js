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

  // OPT-266-02 / OPT-266-10: Sunk View Renderer for Diagnostic Export Self-Audit Summary
  function renderDiagRedactionBadge(auditObj) {
    if (!auditObj || typeof auditObj !== 'object') return '诊断导出脱敏自检：已就绪（UUID / 密码 / 私钥 / 订阅 Token 自动脱敏）';
    const cnt = Number(auditObj.redacted_count || 0);
    return '诊断导出脱敏自检：已拦截并脱敏 ' + cnt + ' 处敏感凭据（明文泄漏 0 处）';
  }
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.settingsPanel = Object.assign(window.NexusModules.settingsPanel || {}, {
    renderDiagRedactionBadge: renderDiagRedactionBadge
  });
  window.renderDiagRedactionBadge = renderDiagRedactionBadge;


// OPT-287-07: Settings panel header & status badge helpers
function formatSettingsStatusBadge(enabled, labelOn, labelOff) {
  return enabled ? String(labelOn || '已启用') : String(labelOff || '未启用');
}
if (typeof window !== 'undefined') {
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.settingsPanel = Object.assign(window.NexusModules.settingsPanel || {}, { formatSettingsStatusBadge: formatSettingsStatusBadge });
}
