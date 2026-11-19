(function () {
  'use strict';
  window.NexusModals = {
    createStackManager: function () {
      return [];
    }
  };
})();

  // OPT-272-04/05: Debounced Health Audit Snapshot Download Guard & Empty-Pool Fallback Notice Formatter
  var _lastSnapshotDlTs = 0;
  function createSnapshotDownloadDebouncer(cooldownMs) {
    var cd = Math.max(500, Number(cooldownMs || 2000));
    return function canTriggerSnapshotDownload(nowMs) {
      var ts = Number(nowMs || Date.now());
      if (ts - _lastSnapshotDlTs < cd) {
        return false;
      }
      _lastSnapshotDlTs = ts;
      return true;
    };
  }

  function formatEmptyPoolFallbackNoticeHtml(diagObj) {
    var d = diagObj && typeof diagObj === 'object' ? diagObj : {};
    var emptyGroups = Array.isArray(d.empty_groups) ? d.empty_groups : [];
    if (!emptyGroups.length) {
      return '<div class="pool-fallback-ok" data-empty-groups="0">全部多线策略组均有可用健康节点</div>';
    }
    var items = emptyGroups.map(function(g) {
      var nm = String((g && g.group_id) || '未命名分组');
      var fb = String((g && g.fallback_outbound) || 'direct');
      return '<li><strong>' + nm + '</strong>：可用节点为 0，已安全降级至 <code>' + fb + '</code></li>';
    }).join('');
    return '<div class="pool-fallback-warn" data-empty-groups="' + emptyGroups.length + '"><ul>' + items + '</ul></div>';
  }

  function formatWatchdogCircuitNoticeHtml(noticeObj) {
    var n = noticeObj && typeof noticeObj === 'object' ? noticeObj : {};
    if (!n.circuit_open) {
      return '<div class="wd-cb-ok" data-cb-open="0">看门狗运行正常</div>';
    }
    return '<div class="wd-cb-open" data-cb-open="1">看门狗已触发熔断保护（连续失败 ' +
      Number(n.failure_count || 0) + ' 次）：' + String(n.recovery_hint_zh || '请检查内核日志并点击一键恢复') + '</div>';
  }


  function createAbortableEventGroup() {
    var ctrl = (typeof AbortController === 'function') ? new AbortController() : null;
    var bound = [];
    return {
      signal: ctrl ? ctrl.signal : undefined,
      on: function (el, type, fn, opts) {
        if (!el || typeof el.addEventListener !== 'function' || typeof fn !== 'function') return;
        var o = Object.assign({}, opts && typeof opts === 'object' ? opts : {});
        if (ctrl && ctrl.signal) o.signal = ctrl.signal;
        el.addEventListener(type, fn, o);
        bound.push([el, type, fn, o]);
      },
      abortAll: function () {
        if (ctrl && typeof ctrl.abort === 'function') {
          try { ctrl.abort(); } catch (_e) {}
        }
        bound.forEach(function (item) {
          try { item[0].removeEventListener(item[1], item[2], item[3]); } catch (_e) {}
        });
        bound.length = 0;
      },
      size: function () { return bound.length; }
    };
  }

  window.NexusModules = window.NexusModules || {};
  window.NexusModules.modals = Object.assign(window.NexusModules.modals || {}, {
    createSnapshotDownloadDebouncer: createSnapshotDownloadDebouncer,
    formatEmptyPoolFallbackNoticeHtml: formatEmptyPoolFallbackNoticeHtml,
    formatWatchdogCircuitNoticeHtml: formatWatchdogCircuitNoticeHtml,
    createAbortableEventGroup: createAbortableEventGroup
  });
  window.createSnapshotDownloadDebouncer = createSnapshotDownloadDebouncer;
  window.formatEmptyPoolFallbackNoticeHtml = formatEmptyPoolFallbackNoticeHtml;
  window.formatWatchdogCircuitNoticeHtml = formatWatchdogCircuitNoticeHtml;
  window.createAbortableEventGroup = createAbortableEventGroup;

