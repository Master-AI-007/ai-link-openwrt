(function () {
  'use strict';

  var STORAGE_KEY = 'ailink_galaxy_device_view';
  var LEGACY_KEY = 'deviceView';

  function normalizeDeviceView(val) {
    if (val === 'top3' || val === 'TOP3' || val === 'top' || val === 'TOP 3' || val === false || val === 'false') {
      return 'top3';
    }
    return 'all';
  }

  function getDeviceView() {
    var raw = '';
    try {
      if (window.NexusStorage && typeof window.NexusStorage.get === 'function') {
        raw = window.NexusStorage.get(STORAGE_KEY) || window.NexusStorage.get(LEGACY_KEY) || '';
      }
      if (!raw) {
        raw = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_KEY) || '';
      }
    } catch (_) {}
    var mode = normalizeDeviceView(raw || 'all');
    try {
      if (window.NexusStorage && typeof window.NexusStorage.set === 'function') {
        window.NexusStorage.set(STORAGE_KEY, mode);
        window.NexusStorage.set(LEGACY_KEY, mode);
      }
      localStorage.setItem(STORAGE_KEY, mode);
      localStorage.setItem(LEGACY_KEY, mode);
    } catch (_) {}
    return mode;
  }

  function setDeviceView(nextMode, stateObj) {
    var mode = normalizeDeviceView(nextMode);
    try {
      if (window.NexusStorage && typeof window.NexusStorage.set === 'function') {
        window.NexusStorage.set(STORAGE_KEY, mode);
        window.NexusStorage.set(LEGACY_KEY, mode);
      }
      localStorage.setItem(STORAGE_KEY, mode);
      localStorage.setItem(LEGACY_KEY, mode);
    } catch (_) {}
    if (stateObj && typeof stateObj === 'object') {
      stateObj.galaxyDeviceView = mode;
      stateObj.deviceView = mode;
      stateObj.listView = mode;
      stateObj.viewMode = mode;
      stateObj.showAll = (mode === 'all');
      stateObj._lastSyncedDeviceView = mode;
    }
    return mode;
  }

  function syncStateDeviceView(stateObj) {
    if (!stateObj || typeof stateObj !== 'object') {
      return getDeviceView();
    }
    var last = stateObj._lastSyncedDeviceView;
    var candidate = null;
    if (stateObj.galaxyDeviceView && stateObj.galaxyDeviceView !== last) {
      candidate = stateObj.galaxyDeviceView;
    } else if (stateObj.deviceView && stateObj.deviceView !== last) {
      candidate = stateObj.deviceView;
    } else if (stateObj.listView && stateObj.listView !== last) {
      candidate = stateObj.listView;
    } else if (stateObj.viewMode && stateObj.viewMode !== last) {
      candidate = stateObj.viewMode;
    } else if (typeof stateObj.showAll === 'boolean' && ((stateObj.showAll ? 'all' : 'top3') !== last)) {
      candidate = stateObj.showAll ? 'all' : 'top3';
    }
    if (candidate !== null) {
      return setDeviceView(candidate, stateObj);
    }
    var persisted = getDeviceView();
    stateObj.galaxyDeviceView = persisted;
    stateObj.deviceView = persisted;
    stateObj.listView = persisted;
    stateObj.viewMode = persisted;
    stateObj.showAll = (persisted === 'all');
    stateObj._lastSyncedDeviceView = persisted;
    return persisted;
  }

  function mergeLanDevices(primaryLan, insightDevices, fallbackPrevLan) {
    var byKey = {};
    var order = [];
    function addEntry(d, isPrimary) {
      if (!d || typeof d !== 'object') return;
      var ip = String(d.ip || '').trim();
      var name = String(d.name || ip || '局域网终端').trim();
      var key = ip || ('name:' + name);
      if (!byKey[key]) {
        byKey[key] = {
          ip: ip,
          name: name,
          down_rate: Number(d.down_rate || 0),
          up_rate: Number(d.up_rate || 0),
          conns: Number(d.conns || 0),
          totalMb: Number(d.totalMb || 0),
          is_remote: Boolean(d.is_remote),
          state: d.state || 'ok'
        };
        order.push(key);
      } else {
        var cur = byKey[key];
        if (isPrimary || (Number(d.down_rate || 0) + Number(d.up_rate || 0)) > (cur.down_rate + cur.up_rate)) {
          cur.down_rate = Number(d.down_rate || 0);
          cur.up_rate = Number(d.up_rate || 0);
        }
        if (Number(d.conns || 0) > cur.conns) {
          cur.conns = Number(d.conns || 0);
        }
        if (Number(d.totalMb || 0) > cur.totalMb) {
          cur.totalMb = Number(d.totalMb || 0);
        }
        if (d.name && (!cur.name || cur.name === cur.ip || cur.name === '局域网终端')) {
          cur.name = String(d.name).trim();
        }
        if (d.is_remote) {
          cur.is_remote = true;
        }
      }
    }
    if (Array.isArray(primaryLan) && primaryLan.length) {
      primaryLan.forEach(function (d) { addEntry(d, true); });
    } else if (Array.isArray(fallbackPrevLan) && fallbackPrevLan.length) {
      fallbackPrevLan.forEach(function (d) { addEntry(d, true); });
    }
    if (Array.isArray(insightDevices) && insightDevices.length) {
      insightDevices.forEach(function (d) { addEntry(d, false); });
    }
    var list = order.map(function (k) { return byKey[k]; });
    list.sort(function (a, b) {
      var ra = Number(a.down_rate || 0) + Number(a.up_rate || 0);
      var rb = Number(b.down_rate || 0) + Number(b.up_rate || 0);
      if (rb !== ra) return rb - ra;
      var ca = Number(a.conns || 0);
      var cb = Number(b.conns || 0);
      if (cb !== ca) return cb - ca;
      var ma = Number(a.totalMb || 0);
      var mb = Number(b.totalMb || 0);
      if (mb !== ma) return mb - ma;
      return String(a.ip || a.name || '').localeCompare(String(b.ip || b.name || ''));
    });
    return list;
  }

  function syncBypassBanner(isBypassActive, modeName) {
    var banners = [
      document.getElementById('global-bypass-alert-banner'),
      document.getElementById('galaxy-bypass-alert-banner')
    ];
    banners.forEach(function (el) {
      if (!el) return;
      el.classList.toggle('hidden', !isBypassActive);
      var lbl = el.querySelector('[data-bypass-mode-label]');
      if (lbl && modeName) {
        lbl.textContent = '应急直连旁路生效中（已覆盖「' + modeName + '」）· 全屋流量当前直连上网';
      }
    });
  }

  // Initialize localStorage persistence immediately on module load
  getDeviceView();

  window.NexusGalaxyHud = {
    STORAGE_KEY: STORAGE_KEY,
    normalizeDeviceView: normalizeDeviceView,
    getDeviceView: getDeviceView,
    setDeviceView: setDeviceView,
    syncStateDeviceView: syncStateDeviceView,
    mergeLanDevices: mergeLanDevices,
    syncBypassBanner: syncBypassBanner
  };
})();
