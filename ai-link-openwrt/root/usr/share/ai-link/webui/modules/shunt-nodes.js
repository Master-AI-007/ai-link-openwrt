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

  // OPT-269-03: Sunk Pool Health Weight Breakdown Badge & Shunt Rule Hit KPI Formatter
  function renderPoolWeightBreakdownBadge(breakdown) {
    const bd = breakdown && typeof breakdown === 'object' ? breakdown : {};
    const grade = String(bd.grade || 'A');
    const total = Number(bd.total_score !== undefined ? bd.total_score : 95);
    const lat = Number(bd.latency_weighted !== undefined ? bd.latency_weighted : 38);
    const loss = Number(bd.loss_weighted !== undefined ? bd.loss_weighted : 30);
    const l7 = Number(bd.l7_weighted !== undefined ? bd.l7_weighted : 27);
    return '<span class="pool-weight-breakdown-badge" data-grade="' + grade + '">' +
      '综合 ' + total + '分 (' + grade + ') · 延迟40%:' + lat + ' + 丢包30%:' + loss + ' + L7 30%:' + l7 +
      '</span>';
  }

  function formatShuntRuleHitKpiText(hitCount, hitBytes) {
    const cnt = Math.max(0, Number(hitCount || 0));
    const bytes = Math.max(0, Number(hitBytes || 0));
    const mb = (bytes / (1024 * 1024)).toFixed(1);
    return '命中 ' + cnt.toLocaleString('en-US') + ' 次 · 累计 ' + mb + ' MB';
  }

  window.NexusModules = window.NexusModules || {};
  window.NexusModules.shuntNodes = Object.assign(window.NexusModules.shuntNodes || {}, {
    renderPoolWeightBreakdownBadge: renderPoolWeightBreakdownBadge,
    formatShuntRuleHitKpiText: formatShuntRuleHitKpiText
  });
  window.renderPoolWeightBreakdownBadge = renderPoolWeightBreakdownBadge;
  window.formatShuntRuleHitKpiText = formatShuntRuleHitKpiText;

  // OPT-270-03: Sunk Node Protocol Distribution Badge & Pool Failover RTO Summary Formatter
  function renderNodeProtocolDistributionHtml(protoSummary) {
    const ps = protoSummary && typeof protoSummary === 'object' ? protoSummary : {};
    const counts = ps.protocol_counts && typeof ps.protocol_counts === 'object' ? ps.protocol_counts : {};
    const total = Number(ps.total_nodes || 0);
    const v6Pct = Number(ps.ipv6_readiness_pct || 0).toFixed(1);
    const parts = Object.keys(counts).sort().map(k => k.toUpperCase() + ':' + counts[k]);
    const distTxt = parts.length ? parts.join(' / ') : '暂无节点';
    return '<div class="node-proto-dist-strip" data-total-nodes="' + total + '">' +
      '<span class="proto-dist-main">协议分布 (' + total + ')：' + distTxt + '</span>' +
      '<span class="proto-dist-v6">IPv6 就绪率 ' + v6Pct + '%</span>' +
      '</div>';
  }

  function formatPoolFailoverRtoBadgeText(rtoSummary) {
    const rs = rtoSummary && typeof rtoSummary === 'object' ? rtoSummary : {};
    const cnt = Number(rs.switch_event_count || 0);
    const avgRtt = Number(rs.avg_post_switch_rtt_ms || 0).toFixed(1);
    const minRtt = Number(rs.fastest_post_switch_rtt_ms || 0).toFixed(1);
    return '累计自愈切换 ' + cnt + ' 次 · 切换后最快 ' + minRtt + ' ms / 均值 ' + avgRtt + ' ms';
  }

  window.NexusModules = window.NexusModules || {};
  window.NexusModules.shuntNodes = Object.assign(window.NexusModules.shuntNodes || {}, {
    renderNodeProtocolDistributionHtml: renderNodeProtocolDistributionHtml,
    formatPoolFailoverRtoBadgeText: formatPoolFailoverRtoBadgeText
  });
  window.renderNodeProtocolDistributionHtml = renderNodeProtocolDistributionHtml;
  window.formatPoolFailoverRtoBadgeText = formatPoolFailoverRtoBadgeText;

  // OPT-271-03: HomeLink Security Audit Red-Dot & Remediation Guidance Banner Renderer
  function renderHomeLinkSecurityBannerHtml(postureObj) {
    const po = postureObj && typeof postureObj === 'object' ? postureObj : {};
    const ok = po.ok !== false && !(Array.isArray(po.port_conflicts) && po.port_conflicts.length) && !(Array.isArray(po.weak_credentials) && po.weak_credentials.length);
    if (ok) {
      return '<div class="homelink-sec-banner is-healthy" data-sec-ok="1"><span class="sec-dot is-ok"></span><span>回家隧道安全预检通过（端口无冲突 · 凭据强度合规）</span></div>';
    }
    const pCnt = Array.isArray(po.port_conflicts) ? po.port_conflicts.length : 0;
    const wCnt = Array.isArray(po.weak_credentials) ? po.weak_credentials.length : 0;
    return '<div class="homelink-sec-banner is-warning" data-sec-ok="0">' +
      '<span class="sec-dot is-red-dot" aria-label="安全告警红点"></span>' +
      '<span>发现安全隐患：端口冲突 ' + pCnt + ' 处 / 弱凭据 ' + wCnt + ' 处，建议更换为 >1024 独立端口并重新生成 16 位随机密钥</span>' +
      '</div>';
  }

  // OPT-271-04: Regional P50 / P95 Latency Percentile Visualization Pills Renderer
  function renderRegionLatencyPercentilePillsHtml(percentilesObj) {
    const po = percentilesObj && typeof percentilesObj === 'object' ? percentilesObj : {};
    const regs = po.regions && typeof po.regions === 'object' ? po.regions : {};
    const keys = Object.keys(regs).sort();
    if (!keys.length) {
      return '<div class="region-p50-p95-empty">暂无区域延迟分位数样本</div>';
    }
    const pills = keys.map(reg => {
      const item = regs[reg] || {};
      const cnt = Number(item.count || 0);
      const p50 = Number(item.p50_ms || 0);
      const p95 = Number(item.p95_ms || 0);
      return '<span class="region-lat-pill" data-region="' + reg + '">' +
        '<strong>' + reg + '</strong> (' + cnt + ') · P50 ' + p50 + 'ms / P95 ' + p95 + 'ms' +
        '</span>';
    });
    return '<div class="region-p50-p95-strip">' + pills.join(' ') + '</div>';
  }

  window.NexusModules = window.NexusModules || {};
  window.NexusModules.shuntNodes = Object.assign(window.NexusModules.shuntNodes || {}, {
    renderHomeLinkSecurityBannerHtml: renderHomeLinkSecurityBannerHtml,
    renderRegionLatencyPercentilePillsHtml: renderRegionLatencyPercentilePillsHtml
  });
  window.renderHomeLinkSecurityBannerHtml = renderHomeLinkSecurityBannerHtml;
  window.renderRegionLatencyPercentilePillsHtml = renderRegionLatencyPercentilePillsHtml;

