(function () {
  'use strict';
  function buildSubFailInlineActions() {
    return '<span class="inline-fallback-actions" style="display:inline-flex;gap:6px;margin-left:8px;vertical-align:middle">' +
      '<button type="button" class="button secondary compact" data-action="import">手动粘贴节点原文</button>' +
      '<button type="button" class="button ghost compact" data-action="binding">切换镜像重试</button>' +
      '</span>';
  }
  window.NexusShuntNodes = {
    buildSubFailInlineActions: buildSubFailInlineActions
  };
})();

  // OPT-266-02 / OPT-266-07: Sunk View Renderer for SRS Rule Fallback Degraded Notice
  function formatSrsDegradedBannerHtml(srsStatus) {
    if (!srsStatus || typeof srsStatus !== 'object' || !srsStatus.using_cached_srs) return '';
    const reason = String(srsStatus.last_error_reason || '云端镜像连接超时');
    const lastTs = String(srsStatus.last_success_str || '本地预置基线');
    return '<div class="srs-degraded-banner">规则集自愈降级提示：云端镜像暂不可达（' + reason + '），已自动启用本地缓存规则集（最后成功缓存时间：' + lastTs + '）。</div>';
  }
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.shuntNodes = Object.assign(window.NexusModules.shuntNodes || {}, {
    formatSrsDegradedBannerHtml: formatSrsDegradedBannerHtml
  });
  window.formatSrsDegradedBannerHtml = formatSrsDegradedBannerHtml;

