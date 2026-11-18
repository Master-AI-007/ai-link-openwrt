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

  // OPT-267-07: Sunk Node Table & Shunt Matrix Independent Renderers
  function renderNodeTableFragment(rowsHtmlArray) {
    const frag = document.createDocumentFragment();
    const temp = document.createElement('tbody');
    temp.innerHTML = Array.isArray(rowsHtmlArray) ? rowsHtmlArray.join('') : String(rowsHtmlArray || '');
    while (temp.firstChild) {
      frag.appendChild(temp.firstChild);
    }
    return frag;
  }
  function renderShuntMatrixSummaryBadge(groups) {
    const list = Array.isArray(groups) ? groups : [];
    const activeCnt = list.filter(g => g && g.mode && g.mode !== 'direct').length;
    return { totalGroups: list.length, activeProxyGroups: activeCnt, labelZh: '共 ' + list.length + ' 个分流组 · 代理接管 ' + activeCnt + ' 组' };
  }
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.shuntNodes = Object.assign(window.NexusModules.shuntNodes || {}, {
    renderNodeTableFragment: renderNodeTableFragment,
    renderShuntMatrixSummaryBadge: renderShuntMatrixSummaryBadge
  });
  window.renderNodeTableFragment = renderNodeTableFragment;
  window.renderShuntMatrixSummaryBadge = renderShuntMatrixSummaryBadge;

  // OPT-268-03: Sunk Batch Speed-Test Control State & Subscription Card Meta Renderers
  function buildBatchProbeControlState(nodes, isProbing, probeProgress) {
    const list = Array.isArray(nodes) ? nodes : [];
    const total = list.length;
    const selectable = list.filter(n => n && !n.disabled && n.selectable !== false).length;
    const probed = list.filter(n => n && Number(n.delay_ms || n.delay || 0) > 0).length;
    const done = probeProgress && typeof probeProgress.done === 'number' ? probeProgress.done : probed;
    const target = probeProgress && typeof probeProgress.total === 'number' && probeProgress.total > 0 ? probeProgress.total : Math.max(1, selectable);
    const pct = isProbing ? Math.min(99, Math.max(1, Math.round((done / target) * 100))) : (probed > 0 ? 100 : 0);
    return {
      totalNodes: total,
      selectableNodes: selectable,
      probedNodes: probed,
      isProbing: Boolean(isProbing),
      progressPct: pct,
      buttonDisabled: Boolean(isProbing || selectable === 0),
      buttonLabelZh: isProbing ? ('并发测速中 (' + pct + '%)') : ('批量测速 (' + selectable + ' 节点)'),
      summaryZh: '可用测速 ' + probed + ' / ' + selectable + ' 节点'
    };
  }

  function renderSubscriptionCardMetaHtml(subItem) {
    if (!subItem || typeof subItem !== 'object') return '';
    const name = String(subItem.name || '机场订阅');
    const usedPct = Number(subItem.used_pct || 0);
    const grade = String(subItem.health_grade || 'A');
    const score = Number(subItem.health_score || 92);
    const expireStr = String(subItem.expire_str || '长期有效');
    const nodeCnt = Number(subItem.node_count || 0);
    return '<div class="sub-card-meta-summary" data-sub-grade="' + grade + '">' +
      '<span class="sub-card-title">' + name + ' (' + nodeCnt + ' 节点)</span>' +
      '<span class="sub-card-health-badge">健康度 ' + grade + ' · ' + score + '分 (延迟40%/丢包30%/L7 30%)</span>' +
      '<span class="sub-card-quota">已用 ' + usedPct + '% · 到期 ' + expireStr + '</span>' +
      '</div>';
  }

  window.NexusModules = window.NexusModules || {};
  window.NexusModules.shuntNodes = Object.assign(window.NexusModules.shuntNodes || {}, {
    buildBatchProbeControlState: buildBatchProbeControlState,
    renderSubscriptionCardMetaHtml: renderSubscriptionCardMetaHtml
  });
  window.buildBatchProbeControlState = buildBatchProbeControlState;
  window.renderSubscriptionCardMetaHtml = renderSubscriptionCardMetaHtml;

