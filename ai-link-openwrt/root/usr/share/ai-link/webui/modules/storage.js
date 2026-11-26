(function () {
  'use strict';
  var _mem = {};
  function safeStorageGet(key, fallbackVal) {
    try {
      var v = window.localStorage.getItem(key);
      if (v !== null && v !== undefined) {
        _mem[key] = String(v);
        return v;
      }
    } catch (_) {}
    if (Object.prototype.hasOwnProperty.call(_mem, key)) {
      return _mem[key];
    }
    return fallbackVal !== undefined ? fallbackVal : '';
  }
  function safeStorageSet(key, val) {
    var s = String(val);
    _mem[key] = s;
    try {
      window.localStorage.setItem(key, s);
      return true;
    } catch (_) {
      return true;
    }
  }
  function safeStorageRemove(key) {
    delete _mem[key];
    try {
      window.localStorage.removeItem(key);
      return true;
    } catch (_) {
      return true;
    }
  }
  function safeStorageKeys() {
    var ks = Object.keys(_mem);
    try {
      var lks = Object.keys(window.localStorage);
      for (var i = 0; i < lks.length; i++) {
        if (ks.indexOf(lks[i]) === -1) ks.push(lks[i]);
      }
    } catch (_) {}
    return ks;
  }
  window.NexusStorage = {
    get: safeStorageGet,
    set: safeStorageSet,
    remove: safeStorageRemove,
    keys: safeStorageKeys
  };
})();

// OPT-289-01 & OPT-289-08: Quota-safe storage helpers & bounded RingBuffer
function safeGetStorage(key, fallback) {
  try {
    if (typeof localStorage === 'undefined') return fallback;
    var v = localStorage.getItem(String(key));
    return v === null ? fallback : v;
  } catch (_) { return fallback; }
}
function safeSetStorage(key, val) {
  try {
    if (typeof localStorage !== 'undefined') localStorage.setItem(String(key), String(val));
    return true;
  } catch (_) { return false; }
}
function createRingBuffer(maxLen) {
  var cap = Math.max(8, Number(maxLen) || 200);
  var buf = [];
  return {
    push: function (item) { buf.push(item); if (buf.length > cap) buf.shift(); },
    items: function () { return buf.slice(); },
    size: function () { return buf.length; }
  };
}
if (typeof window !== 'undefined') {
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.storage = Object.assign(window.NexusModules.storage || {}, {
    safeGetStorage: safeGetStorage, safeSetStorage: safeSetStorage, createRingBuffer: createRingBuffer
  });
}

// OPT-290-01: Unified HTML entity escaping & safeSetHtml helper
function escapeHtmlStr(val) {
  return String(val == null ? '' : val)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
function safeSetHtml(el, htmlStr) {
  if (!el) return false;
  el.innerHTML = String(htmlStr == null ? '' : htmlStr);
  return true;
}
if (typeof window !== 'undefined') {
  window.escapeHtmlStr = escapeHtmlStr;
  window.safeSetHtml = safeSetHtml;
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.storage = Object.assign(window.NexusModules.storage || {}, {
    escapeHtmlStr: escapeHtmlStr, safeSetHtml: safeSetHtml
  });
}

// OPT-291-03: Exception-safe JSON.parse helper
function safeJsonParse(raw, fallback) {
  try {
    if (raw === null || raw === undefined || raw === '') return fallback;
    return JSON.parse(String(raw));
  } catch (_) { return fallback; }
}
if (typeof window !== 'undefined') {
  window.safeJsonParse = safeJsonParse;
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.storage = Object.assign(window.NexusModules.storage || {}, {
    safeJsonParse: safeJsonParse
  });
}

// OPT-292-05: HTTP non-secure context fallback clipboard copy
function safeCopyText(text) {
  var s = String(text == null ? '' : text);
  if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(s).then(function () { return true; }).catch(function () { return false; });
  }
  try {
    if (typeof document !== 'undefined') {
      var ta = document.createElement('textarea');
      ta.value = s; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      var ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return Promise.resolve(!!ok);
    }
  } catch (_) {}
  return Promise.resolve(false);
}
if (typeof window !== 'undefined') {
  window.safeCopyText = safeCopyText;
  window.NexusModules = window.NexusModules || {};
  window.NexusModules.storage = Object.assign(window.NexusModules.storage || {}, {
    safeCopyText: safeCopyText
  });
}
