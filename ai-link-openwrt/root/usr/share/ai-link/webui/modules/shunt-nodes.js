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
