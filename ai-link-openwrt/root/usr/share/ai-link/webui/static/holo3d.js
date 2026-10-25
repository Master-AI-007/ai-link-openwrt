/* ============================================================
   AI-LINK 四维全息星系与深空黑洞拓扑 · holo3d.js (Interstellar Gargantua & 4-Galaxy Drawer Edition)
   依赖：static/three.min.js（r128）
   用法：Holo3D.mount(document.getElementById('holo-3d-stage'))
        Holo3D.setLive({conn, down, up, exit, mem})
        Holo3D.setGalaxy(snap)   // 接入 3 大星系 + 4th 净网引力黑洞 (snap.blackhole)
   ============================================================ */
(function () {
  'use strict';
  const CSS = `
.h3-root{position:absolute;inset:0;overflow:hidden;border-radius:inherit;background:#04020d;user-select:none;font-family:"Inter",-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}
.h3-root .holo-overlay-card{display:none !important}
.h3-root #h3-canvas{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab}
.h3-root #h3-canvas:active{cursor:grabbing}
.h3-vignette{position:absolute;inset:0;pointer-events:none;z-index:2;
background:radial-gradient(ellipse at 50% 44%,transparent 52%,rgba(4,2,14,.50) 84%,rgba(2,1,8,.88) 100%),
linear-gradient(180deg,rgba(6,4,18,.55) 0%,transparent 14%,transparent 82%,rgba(4,2,14,.78) 100%)}
.h3-leaders{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:9}
.h3-top{position:absolute;top:14px;left:14px;display:flex;flex-wrap:wrap;gap:11px;align-items:center;
background:rgba(9,11,24,.88);
border:1px solid rgba(148,163,184,.22);border-radius:13px;
padding:8px 14px;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
box-shadow:0 14px 34px -8px rgba(0,0,0,.80),inset 0 1px 0 rgba(255,255,255,.12);
font-size:11.5px;z-index:15}
.h3-top .k{color:#94a3b8;font-weight:500;margin-right:4px}
.h3-top .v{color:#f8fafc;font-variant-numeric:tabular-nums;font-weight:700;font-family:'Inter',system-ui,sans-serif;font-size:12px}
.h3-top .v.bh-v{color:#fb923c;cursor:pointer;border-bottom:1px dashed rgba(251,146,60,.55)}
.h3-top .sep{width:1px;height:14px;background:rgba(148,163,184,.2)}
.h3-nav-dock{position:absolute;top:14px;right:14px;display:flex;gap:6px;align-items:center;
background:rgba(9,11,24,.88);
border:1px solid rgba(148,163,184,.22);border-radius:13px;padding:5px 7px;
backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
box-shadow:0 14px 34px -8px rgba(0,0,0,.80);z-index:16}
.h3-nav-btn{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);color:#cbd5e1;
border-radius:9px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer;
transition:all .16s ease;display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.h3-nav-btn:hover{background:rgba(139,92,246,.22);border-color:rgba(196,181,253,.5);color:#fff}
.h3-nav-btn.active{background:linear-gradient(135deg,rgba(124,58,237,.68) 0%,rgba(14,165,233,.42) 100%);
border-color:rgba(221,214,254,.75);color:#fff;box-shadow:0 0 14px rgba(139,92,246,.38)}
.h3-nav-btn.bh-btn{border-color:rgba(249,115,22,.4);color:#fed7aa;background:rgba(154,52,18,.20)}
.h3-nav-btn.bh-btn:hover,.h3-nav-btn.bh-btn.active{background:linear-gradient(135deg,rgba(234,88,12,.78) 0%,rgba(168,85,247,.55) 100%);
border-color:#fdba74;color:#fff;box-shadow:0 0 18px rgba(249,115,22,.45)}
.h3-hint{position:absolute;top:54px;left:16px;font-size:11px;color:#64748b;line-height:1.5;z-index:12;
text-shadow:0 1px 3px rgba(0,0,0,.9);pointer-events:none;font-weight:500}
.h3-hud{position:absolute;pointer-events:none;min-width:248px;max-width:320px;
background:rgba(8,10,22,.94);
border:1px solid rgba(168,85,247,.45);border-radius:14px;
padding:11px 14px;backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);
box-shadow:0 20px 44px -10px rgba(0,0,0,.9),inset 0 1px 0 rgba(255,255,255,.16);
opacity:0;transform:translateY(4px) scale(.98);
transition:opacity .14s ease,transform .14s ease;z-index:32}
.h3-hud.show{opacity:1;transform:translateY(0) scale(1)}
.h3-hud .cat{display:flex;justify-content:space-between;align-items:center;font-size:10px;
letter-spacing:.06em;color:#c4b5fd;font-weight:700;border-bottom:1px solid rgba(148,163,184,.18);
padding-bottom:5px;margin-bottom:6px}
.h3-hud h3{font-size:13px;font-weight:700;color:#fff;margin-bottom:2px;word-break:break-all}
.h3-hud .sub{font-size:11px;color:#94a3b8;line-height:1.4;margin-bottom:7px}
.h3-hud .rows{display:grid;grid-template-columns:auto 1fr;gap:3.5px 12px;font-size:11px}
.h3-hud .rows b{color:#f8fafc;font-weight:600;text-align:right;font-variant-numeric:tabular-nums}
.h3-hud .rows span{color:#94a3b8}
.h3-toasts{position:absolute;top:60px;right:14px;width:330px;max-width:calc(100vw - 28px);display:flex;flex-direction:column;gap:8px;z-index:40;pointer-events:none}
.h3-toast{position:relative;overflow:hidden;background:rgba(6,24,16,.92);border:1px solid rgba(52,211,153,.45);
border-left:3px solid #10b981;border-radius:11px;padding:9px 12px;backdrop-filter:blur(16px);
box-shadow:0 12px 28px rgba(0,0,0,.75);animation:h3slide .2s ease-out}
.h3-toast.warn{background:rgba(28,16,4,.92);border-color:rgba(245,158,11,.45);border-left-color:#f59e0b}
.h3-toast.warn .t{color:#fcd34d}.h3-toast.warn .m{color:#fef3c7}
.h3-toast.crit{background:rgba(32,8,12,.92);border-color:rgba(239,68,68,.48);border-left-color:#ef4444}
.h3-toast.crit .t{color:#fca5a5}.h3-toast.crit .m{color:#fee2e2}
.h3-toast .t{font-size:9.5px;letter-spacing:.08em;color:#6ee7b7;font-weight:700;margin-bottom:2px}
.h3-toast .m{font-size:11.5px;color:#ecfdf5;line-height:1.45;font-weight:500}
.h3-toast .scan{position:absolute;top:0;left:-40%;width:40%;height:100%;
background:linear-gradient(90deg,transparent,rgba(255,255,255,.18),transparent);animation:h3scan 1.1s ease-out .1s 1}
@keyframes h3slide{from{opacity:0;transform:translateX(16px)}to{opacity:1;transform:none}}
@keyframes h3scan{to{left:110%}}
.h3-legend{position:absolute;left:14px;bottom:14px;
background:rgba(9,11,24,.86);
border:1px solid rgba(148,163,184,.2);border-radius:12px;padding:8px 12px;
backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
box-shadow:0 12px 28px -8px rgba(0,0,0,.75);
font-size:10.5px;z-index:12;pointer-events:none}
.h3-legend .row{display:flex;align-items:center;gap:6px;margin:3px 0;color:#cbd5e1}
.h3-legend .sw{width:7.5px;height:7.5px;border-radius:50%;box-shadow:0 0 6px currentColor;flex-shrink:0}
.h3-legend .hr{height:1px;background:rgba(148,163,184,.16);margin:5px 0}
.h3-ctrl{position:absolute;right:14px;bottom:14px;display:flex;flex-wrap:wrap;gap:6px;z-index:14}
.h3-ctrl button{background:rgba(12,15,32,.88);
border:1px solid rgba(148,163,184,.25);color:#e2e8f0;
border-radius:10px;padding:6px 11px;font-size:11px;font-weight:600;cursor:pointer;
backdrop-filter:blur(14px);transition:all .15s ease;
box-shadow:0 8px 20px -6px rgba(0,0,0,.7)}
.h3-ctrl button:hover{background:rgba(124,58,237,.35);border-color:rgba(196,181,253,.6);color:#fff}
.h3-ctrl button.on{background:linear-gradient(135deg,rgba(124,58,237,.72) 0%,rgba(14,165,233,.45) 100%);
border-color:#ddd6fe;color:#fff}
.h3-ctrl button.bh-open{background:linear-gradient(135deg,rgba(234,88,12,.78) 0%,rgba(147,51,234,.62) 100%);
border-color:#fdba74;color:#fff}
.h3-health{position:absolute;inset:0;pointer-events:none;z-index:11;overflow:hidden}
.h3-health .hc{position:absolute;transform:translate(-50%,-50%);display:flex;align-items:center;gap:5px;
background:rgba(8,10,22,.88);
border:1px solid rgba(148,163,184,.24);border-radius:999px;
padding:3.5px 9.5px;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
white-space:nowrap;box-shadow:0 6px 16px -4px rgba(0,0,0,.78);
transition:opacity .18s ease}
.h3-health .hc.hc-dom{border-color:rgba(244,114,182,.34)}
.h3-health .hc.hc-fore{border-color:rgba(34,211,238,.34)}
.h3-health .hc.hc-bh{border-color:rgba(251,146,60,.42)}
.h3-health .hc .dot{width:5.5px;height:5.5px;border-radius:50%;background:#94a3b8;flex:0 0 auto}
.h3-health .hc .nm{font-size:10.5px;color:#cbd5e1;font-weight:500;line-height:1.1}
.h3-health .hc .ms{font-size:10.5px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1.1;color:#34d399}
.h3-health .hc .ms.v{color:#ddd6fe}
.h3-health .hc .ms.o{color:#fdba74}
.h3-health .hc .ms.g{color:#34d399}.h3-health .hc .ms.y{color:#fbbf24}.h3-health .hc .ms.r{color:#f87171}
.h3-health .h3-star-badge{position:absolute;transform:translate(-50%,-50%);display:flex;align-items:center;gap:6px;
padding:4.5px 11px;border-radius:999px;background:rgba(8,10,22,.92);border:1px solid rgba(255,255,255,.22);
backdrop-filter:blur(14px);box-shadow:0 8px 22px rgba(0,0,0,.82);white-space:nowrap;pointer-events:auto;cursor:pointer;
transition:all .15s ease}
.h3-health .h3-star-badge:hover{border-color:rgba(255,255,255,.65);box-shadow:0 0 18px rgba(139,92,246,.45)}
.h3-health .h3-star-badge.bh-badge{background:rgba(20,10,24,.94);border-color:rgba(251,146,60,.55)}
.h3-health .h3-star-badge .s-dot{width:7px;height:7px;border-radius:50%;flex:0 0 auto}
.h3-health .h3-star-badge .s-nm{font-size:11px;font-weight:700;color:#f8fafc}
.h3-health .h3-star-badge .s-sub{font-size:10px;color:#94a3b8;font-weight:500;font-variant-numeric:tabular-nums}
/* ===== 四星系通用全息展开详情抽屉 (支持 🧠内核中枢 / 🇨🇳国内直连 / 🌍海外代理 / 🕳️深空黑洞) ===== */
.h3-bh-drawer{position:absolute;top:56px;right:14px;bottom:84px;width:392px;max-width:calc(100vw - 28px);
background:linear-gradient(165deg,rgba(10,12,26,.96) 0%,rgba(6,7,18,.98) 100%);
border:1px solid rgba(168,85,247,.42);border-radius:16px;
padding:14px 15px;backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);
box-shadow:0 24px 56px rgba(0,0,0,.92),inset 0 1px 0 rgba(255,255,255,.16);
display:flex;flex-direction:column;gap:10px;z-index:35;overflow-y:auto;
transform:translateX(425px);opacity:0;pointer-events:none;transition:transform .22s cubic-bezier(.22,1,.36,1),opacity .18s ease}
.h3-bh-drawer.open{transform:translateX(0);opacity:1;pointer-events:auto}
.h3-drawer-tabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;background:rgba(255,255,255,.04);padding:3.5px;border-radius:10px;border:1px solid rgba(255,255,255,.08)}
.h3-dtab{padding:5px 4px;border-radius:7px;font-size:10.5px;font-weight:600;color:#94a3b8;text-align:center;cursor:pointer;transition:all .14s ease;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.h3-dtab:hover{color:#f1f5f9;background:rgba(255,255,255,.05)}
.h3-dtab.active{background:rgba(139,92,246,.32);color:#fff;border:1px solid rgba(196,181,253,.45)}
.h3-dtab.active[data-dtab="blackhole"]{background:rgba(234,88,12,.34);border-color:rgba(251,146,60,.55)}
.h3-dtab.active[data-dtab="domestic"]{background:rgba(236,72,153,.28);border-color:rgba(244,114,182,.5)}
.h3-dtab.active[data-dtab="foreign"]{background:rgba(6,182,212,.28);border-color:rgba(34,211,238,.5)}
.h3-bh-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;border-bottom:1px solid rgba(148,163,184,.16);padding-bottom:9px}
.h3-bh-title{font-size:13.5px;font-weight:700;color:#fff;display:flex;align-items:center;gap:6px}
.h3-bh-sub{font-size:11px;color:#94a3b8;margin-top:2px;font-weight:500}
.h3-bh-close{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);color:#cbd5e1;
border-radius:8px;padding:3px 8px;font-size:11px;font-weight:600;cursor:pointer}
.h3-bh-close:hover{background:rgba(239,68,68,.3);color:#fff;border-color:#fca5a5}
.h3-bh-kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.h3-bh-kpi{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.08);border-radius:11px;padding:8.5px 10px}
.h3-bh-kpi .kl{font-size:10.5px;color:#94a3b8;font-weight:500}
.h3-bh-kpi .kv{font-size:16px;font-weight:700;font-variant-numeric:tabular-nums;margin-top:2px;color:#f8fafc;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.h3-bh-kpi .ks{font-size:10px;color:#64748b;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.h3-bh-sec{background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.07);border-radius:11px;padding:9.5px 11px}
.h3-bh-sec-h{display:flex;align-items:center;justify-content:space-between;font-size:11px;font-weight:600;color:#e2e8f0;margin-bottom:6px}
.h3-bh-cat-row{margin:5px 0}
.h3-bh-cat-top{display:flex;justify-content:space-between;font-size:10.5px;color:#cbd5e1;font-weight:500;margin-bottom:3px}
.h3-bh-bar-bg{height:5px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden}
.h3-bh-bar-fg{height:100%;border-radius:999px;background:linear-gradient(90deg,#f97316,#a855f7)}
.h3-bh-dom-list{display:flex;flex-direction:column;gap:4px;max-height:195px;overflow-y:auto;padding-right:2px}
.h3-bh-dom-item{display:flex;align-items:center;justify-content:space-between;gap:6px;padding:5px 8px;
border-radius:8px;background:rgba(0,0,0,.32);border:1px solid rgba(255,255,255,.06);font-size:11px}
.h3-bh-dom-name{color:#f1f5f9;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:190px}
.h3-bh-dom-meta{display:flex;align-items:center;gap:5px;flex-shrink:0}
.h3-bh-tag{padding:1px 6px;border-radius:5px;font-size:9.5px;font-weight:600;background:rgba(148,163,184,.15);color:#cbd5e1;border:1px solid rgba(148,163,184,.28)}
.h3-bh-cnt{font-variant-numeric:tabular-nums;font-weight:600;color:#34d399;font-size:10.5px}
.h3-bh-actions{display:flex;gap:7px;align-items:center}
.h3-bh-btn-act{flex:1;padding:7.5px 10px;border-radius:9px;font-size:11px;font-weight:600;cursor:pointer;text-align:center;
border:1px solid rgba(251,146,60,.5);background:linear-gradient(135deg,rgba(234,88,12,.80) 0%,rgba(147,51,234,.70) 100%);color:#fff;
transition:all .15s ease}
.h3-bh-btn-act:hover{filter:brightness(1.1)}
.h3-bh-btn-sub{padding:7.5px 11px;border-radius:9px;font-size:11px;font-weight:600;cursor:pointer;
border:1px solid rgba(148,163,184,.3);background:rgba(255,255,255,.06);color:#e2e8f0}
.h3-bh-btn-sub:hover{background:rgba(139,92,246,.3);color:#fff}
@media (max-width:1160px){
.h3-nav-dock{top:52px;right:14px;max-width:calc(100vw - 28px);overflow-x:auto}
.h3-hint{top:92px}
.h3-bh-drawer{top:94px;bottom:78px}
}
@media (max-width:960px){
.h3-legend{display:none !important}
.h3-ctrl{left:14px;right:14px;bottom:72px !important;justify-content:center}
}
@media (max-width:768px){
.h3-legend,.h3-hint{display:none !important}
.h3-top{top:8px;left:8px;right:8px;padding:5px 10px;font-size:10px;justify-content:space-between;gap:6px;flex-wrap:nowrap !important;white-space:nowrap;overflow-x:auto}
.h3-nav-dock{display:flex !important;top:44px;left:8px;right:8px;padding:4px 6px;gap:4px;overflow-x:auto;justify-content:flex-start}
.h3-nav-btn{padding:4px 8px;font-size:10px;flex-shrink:0}
.h3-ctrl{right:8px;left:8px;bottom:66px !important;justify-content:center;gap:4px}
.h3-ctrl button{padding:4.5px 7.5px;font-size:10px}
.h3-health .hc{padding:2.5px 7px !important}
.h3-health .hc .nm{font-size:9.5px !important}
.h3-health .hc .ms{font-size:10px !important}
.h3-bh-drawer{top:84px;left:8px;right:8px;width:auto;max-width:calc(100vw - 16px);bottom:70px;padding:11px 12px}
}
.h3-2d-fallback{position:absolute;inset:0;z-index:25;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:24px 16px 96px;background:radial-gradient(ellipse at 50% 40%,rgba(88,28,135,.32),rgba(6,3,18,.96) 75%);color:#e2e8f0;overflow-y:auto}
`;
  const HTML = `
<canvas id="h3-canvas"></canvas>
<div class="h3-vignette"></div>
<svg class="h3-leaders" id="h3-leaders-svg"></svg>
<div class="h3-top">
<span><span class="k">总连接</span> <span class="v" id="h3-t-conn">0</span></span>
<span class="sep"></span>
<span><span class="k">下行</span> <span class="v" id="h3-t-down">0 B/s</span></span>
<span class="sep"></span>
<span><span class="k">上行</span> <span class="v" id="h3-t-up">0 B/s</span></span>
<span class="sep"></span>
<span><span class="k">黑洞吞噬</span> <span class="v bh-v" id="h3-t-bh" title="点击展开深空黑洞广告拦截中枢">64 次 · 50,000+ 规则</span></span>
<span class="sep"></span>
<span><span class="k">粒子</span> <span class="v" id="h3-t-tier">4颗 · 待命</span></span>
</div>
<div class="h3-nav-dock" id="h3-nav-dock">
<button type="button" class="h3-nav-btn active" data-focus="all">🌌 全景星图</button>
<button type="button" class="h3-nav-btn" data-focus="lan">🧠 内核中枢</button>
<button type="button" class="h3-nav-btn" data-focus="domestic">🇨🇳 国内直连</button>
<button type="button" class="h3-nav-btn" data-focus="foreign">🌍 海外代理</button>
<button type="button" class="h3-nav-btn bh-btn" data-focus="blackhole">🕳️ 黑洞净网中枢</button>
</div>
<div class="h3-hint">拖拽旋转 · 滚轮缩放 · 点击任一星系母星或黑洞展开专属详情单 · Esc 复位全景</div>
<div class="h3-health" id="h3-health-layer"></div>
<div class="h3-legend">
<div class="row"><span class="sw" style="background:#10b981;color:#10b981"></span>正常 · <span class="sw" style="background:#f59e0b;color:#f59e0b"></span>高延迟 · <span class="sw" style="background:#ef4444;color:#ef4444"></span>异常 · <span class="sw" style="background:#fb923c;color:#fb923c"></span>黑洞净网拦截</div>
<div class="hr"></div>
<div class="row">点击任一母星（内核 / 直连 / 代理 / 黑洞）展开对应星系实时详情抽屉</div>
</div>
<div class="h3-ctrl">
<button id="h3-btn-bh" type="button" class="bh-open">📊 星系与黑洞详情</button>
<button id="h3-btn-orbit" type="button">自动环绕</button>
<button id="h3-btn-all" type="button">显示全部标签</button>
<button id="h3-btn-notify" type="button">模拟通知</button>
<button id="h3-btn-reset" type="button">复位视角</button>
</div>
<div class="h3-bh-drawer" id="h3-bh-drawer">
  <div class="h3-drawer-tabs" id="h3-drawer-tabs">
    <button type="button" class="h3-dtab" data-dtab="lan">🧠 内核中枢</button>
    <button type="button" class="h3-dtab" data-dtab="domestic">🇨🇳 国内直连</button>
    <button type="button" class="h3-dtab" data-dtab="foreign">🌍 海外代理</button>
    <button type="button" class="h3-dtab active" data-dtab="blackhole">🕳️ 黑洞拦截</button>
  </div>
  <div class="h3-bh-head">
    <div>
      <div class="h3-bh-title"><span id="h3-bhd-icon">🕳️</span><span id="h3-bhd-title">深空引力黑洞 · 净网广告拦截中枢</span></div>
      <div class="h3-bh-sub" id="h3-bhd-sub">AdGuardHome 级双擎护盾 (DNS Sinkhole + 路由层 .srs 规则集)</div>
    </div>
    <button type="button" class="h3-bh-close" id="h3-bhd-close">✕ 收起</button>
  </div>
  <div class="h3-bh-kpis" id="h3-bhd-kpis">
    <div class="h3-bh-kpi">
      <div class="kl" id="h3-kpi1-l">已吞噬广告/追踪请求</div>
      <div class="kv" style="color:#fb923c" id="h3-bhd-blocked">64</div>
      <div class="ks" id="h3-kpi1-s">拦截率 <b style="color:#fde68a" id="h3-bhd-rate">15.2%</b> · 实时引力捕获</div>
    </div>
    <div class="h3-bh-kpi">
      <div class="kl" id="h3-kpi2-l">挂载有效黑名单规则</div>
      <div class="kv" style="color:#34d399" id="h3-bhd-rules">50,085</div>
      <div class="ks" id="h3-bhd-srs-meta">二进制 .srs + DNS 双层生效</div>
    </div>
    <div class="h3-bh-kpi">
      <div class="kl" id="h3-kpi3-l">DNS 层前置阻断 (0.0.0.0)</div>
      <div class="kv" style="color:#38bdf8" id="h3-bhd-dns-blk">25</div>
      <div class="ks" id="h3-kpi3-s">毫秒级零连接开销拒绝</div>
    </div>
    <div class="h3-bh-kpi">
      <div class="kl" id="h3-kpi4-l">路由层 REJECT 掐断</div>
      <div class="kv" style="color:#c084fc" id="h3-bhd-route-blk">39</div>
      <div class="ks" id="h3-kpi4-s">防 DoH/硬编码绕过兜底</div>
    </div>
  </div>
  <div class="h3-bh-actions" id="h3-bhd-actions">
    <button type="button" class="h3-bh-btn-act" id="h3-bhd-test-btn">🧪 实测广告吞噬 (8大高频广告源)</button>
    <button type="button" class="h3-bh-btn-sub" id="h3-bhd-cfg-btn">⚙️ 规则设置</button>
  </div>
  <div class="h3-bh-sec" id="h3-bhd-sec1">
    <div class="h3-bh-sec-h"><span id="h3-sec1-title">📊 吞噬威胁分类占比</span><span id="h3-bhd-last-hit" style="color:#94a3b8;font-weight:500">最近吞噬: cpro.baidu.com</span></div>
    <div id="h3-bhd-cats"></div>
  </div>
  <div class="h3-bh-sec" style="flex:1;min-height:145px;display:flex;flex-direction:column">
    <div class="h3-bh-sec-h"><span id="h3-sec2-title">🔥 黑洞吞噬高频域名 TOP 榜</span><span id="h3-sec2-sub" style="color:#fb923c">实时统计</span></div>
    <div class="h3-bh-dom-list" id="h3-bhd-top-list"></div>
  </div>
</div>
<div class="h3-toasts" id="h3-toasts"></div>
<div class="h3-hud" id="h3-hud">
<div class="cat"><span id="h3-hud-cat">TELEMETRY</span><span id="h3-hud-state">● 在线</span></div>
<h3 id="h3-hud-title">—</h3>
<div class="sub" id="h3-hud-sub">—</div>
<div class="rows" id="h3-hud-rows"></div>
</div>
`;
  let mounted = false;
  let styleInjected = false;
  let _notifyFn = null;
  const LIVE = { on: false, conn: 0, down: 0, up: 0, exit: '', mem: 0 };
  function injectStyle() {
    if (styleInjected) return;
    const st = document.createElement('style');
    st.id = 'h3-style';
    st.textContent = CSS;
    document.head.appendChild(st);
    styleInjected = true;
  }
  function render2DFallback(root, reason) {
    injectStyle();
    root.classList.add('h3-root');
    const oldCanvas = root.querySelector('#canvas-3d-topology');
    if (oldCanvas) oldCanvas.style.display = 'none';
    if (!root.querySelector('#h3-t-conn')) {
      root.insertAdjacentHTML('beforeend', HTML);
    }
    const cv = root.querySelector('#h3-canvas');
    if (cv) cv.style.display = 'none';
    let fb = root.querySelector('#h3-2d-fallback');
    if (!fb) {
      fb = document.createElement('div');
      fb.id = 'h3-2d-fallback';
      fb.className = 'h3-2d-fallback';
      fb.innerHTML = `
        <div style="max-width:860px;width:100%;background:rgba(10,14,32,.92);border:1.5px solid rgba(168,85,247,.45);border-radius:20px;padding:18px 20px;box-shadow:0 20px 50px rgba(0,0,0,.85);">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:14px;border-bottom:1px solid rgba(255,255,255,.12);padding-bottom:10px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="font-size:18px;">🌌</span>
              <div>
                <div style="font-size:14px;font-weight:700;color:#f8fafc;">全息星系与深空黑洞拓扑视图 (2D 兼容模式)</div>
                <div style="font-size:11px;color:#cbd5e1;">当前环境未启用 WebGL (${reason || 'WebGL context unavailable'})，已切换为 2D 四维拓扑总览</div>
              </div>
            </div>
            <span style="padding:3px 10px;border-radius:999px;background:rgba(16,185,129,.18);border:1px solid rgba(16,185,129,.4);color:#6ee7b7;font-size:11px;font-weight:600;">● 实时遥测在线</span>
          </div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:12px;">
            <div style="background:rgba(30,27,75,.65);border:1px solid rgba(139,92,246,.45);border-radius:14px;padding:12px;">
              <div style="font-size:11.5px;color:#ddd6fe;font-weight:700;">🧠 内核中枢 · sing-box</div>
              <div style="font-size:12px;color:#e2e8f0;margin-top:4px;">状态: <b style="color:#34d399;">运行中</b></div>
              <div style="font-size:11px;color:#cbd5e1;margin-top:2px;">TProxy :7893 · Mixed :7890</div>
            </div>
            <div style="background:rgba(50,18,45,.65);border:1px solid rgba(244,114,182,.45);border-radius:14px;padding:12px;">
              <div style="font-size:11.5px;color:#fbcfe8;font-weight:700;">🇨🇳 直连出口 · 国内 WAN</div>
              <div style="font-size:12px;color:#e2e8f0;margin-top:4px;">路径: <b style="color:#f472b6;">宽带直连 (WAN)</b></div>
              <div style="font-size:11px;color:#cbd5e1;margin-top:2px;">百度 / B站 / 淘宝 / 抖音</div>
            </div>
            <div style="background:rgba(8,47,73,.65);border:1px solid rgba(34,211,238,.45);border-radius:14px;padding:12px;">
              <div style="font-size:11.5px;color:#a5f3fc;font-weight:700;">🌍 代理出口 · 海外节点</div>
              <div style="font-size:12px;color:#e2e8f0;margin-top:4px;">策略: <b style="color:#22d3ee;" id="h3-2d-exit">AI_Best_Auto</b></div>
              <div style="font-size:11px;color:#cbd5e1;margin-top:2px;">Gemini / ChatGPT / YouTube / GitHub</div>
            </div>
            <div style="background:rgba(45,16,12,.72);border:1px solid rgba(251,146,60,.55);border-radius:14px;padding:12px;">
              <div style="font-size:11.5px;color:#fed7aa;font-weight:700;">🕳️ 深空引力黑洞 · 净网中枢</div>
              <div style="font-size:12px;color:#e2e8f0;margin-top:4px;">已吞噬: <b style="color:#fb923c;" id="h3-2d-bh">64 次</b></div>
              <div style="font-size:11px;color:#cbd5e1;margin-top:2px;">AdGuard 双擎 · 50,000+ 规则</div>
            </div>
          </div>
        </div>`;
      root.appendChild(fb);
    }
    window.__h3SetLive = function (d) {
      if (!d) return;
      const elConn = document.getElementById('h3-t-conn');
      if (elConn && typeof d.conn === 'number') elConn.textContent = d.conn | 0;
      const elExit = document.getElementById('h3-2d-exit');
      if (elExit && d.exit) elExit.textContent = d.exit;
    };
    window.__h3SetActive = function () {};
  }

  function mount(root) {
    if (!root) return;
    if (mounted) { window.__h3Resize && window.__h3Resize(); return; }
    injectStyle();
    window.__h3Root = root;
    root.classList.add('h3-root');
    const oldCanvas = root.querySelector('#canvas-3d-topology');
    if (oldCanvas) oldCanvas.style.display = 'none';
    root.insertAdjacentHTML('beforeend', HTML);
    mounted = true;
    if (typeof THREE === 'undefined') {
      render2DFallback(root, 'THREE.js 未加载');
      return;
    }
    try {
      const testCv = document.createElement('canvas');
      const gl = testCv.getContext('webgl') || testCv.getContext('experimental-webgl');
      if (!gl) {
        render2DFallback(root, 'WebGL 已禁用或无 GPU 上下文');
        return;
      }
      start();
    } catch (e) {
      console.warn('[holo3d] WebGL fallback triggered:', e);
      render2DFallback(root, (e && e.message) || 'WebGL 初始化异常');
    }
    window.__holoInit = () => { window.__h3Resize && window.__h3Resize(); };
    window.__holoResize = window.__h3Resize;
    if (window.ResizeObserver) {
      new ResizeObserver(() => window.__h3Resize && window.__h3Resize()).observe(root);
    }
  }

  function start() {
    const C = {
      ok: 0x10b981, pending: 0x94a3b8, suspect: 0xf59e0b, dead: 0xef4444,
      kernel: 0x8b5cf6, direct: 0xf472b6, proxy: 0x06b6d4, blackhole: 0xf97316,
    };
    const CSS_COL = {
      ok: '#10b981', pending: '#94a3b8', suspect: '#f59e0b', dead: '#ef4444',
      kernel: '#a78bfa', direct: '#f472b6', proxy: '#22d3ee', blackhole: '#fb923c',
    };
    const GALAXY = {
      lan:       { center: new THREE.Vector3(-9.5, 0.05, 0.4),   r: 4.1, color: C.kernel,    css: CSS_COL.kernel,    name: '内核中枢',     sub: 'sing-box 分流' },
      domestic:  { center: new THREE.Vector3(7.4, 3.85, -1.5),   r: 3.5, color: C.direct,    css: CSS_COL.direct,    name: '国内直连星系', sub: '走 WAN 宽带' },
      foreign:   { center: new THREE.Vector3(7.4, -3.85, 1.8),   r: 3.5, color: C.proxy,     css: CSS_COL.proxy,     name: '海外代理星系', sub: '走优选节点' },
      blackhole: { center: new THREE.Vector3(-0.8, 4.95, -6.6),  r: 4.8, color: C.blackhole, css: CSS_COL.blackhole, name: '深空引力黑洞', sub: '净网拦截中枢' },
    };
    const HEALTH_TARGETS = {
      domestic: ['百度', 'B站', '抖音', '淘宝'],
      foreign:  ['Gemini', 'ChatGPT', 'YouTube', 'GitHub'],
    };
    const SAT_PALETTE = [
      0x7dd3fc, 0xc4b5fd, 0xfbbf24, 0x34d399, 0xf472b6,
      0x60a5fa, 0x22d3ee, 0xe879f9, 0xa3e635, 0xfb923c,
    ];
    function satColor(i) { return SAT_PALETTE[i % SAT_PALETTE.length]; }
    const DEVICE_RADII = [3.15, 3.62, 4.10, 4.58, 5.06];
    const SITE_RADII   = [3.05, 3.32, 3.58, 3.84, 4.10, 4.36, 4.62, 4.88, 5.14, 5.40];
    const HEALTH_RING_R = 6.35;
    const STATE_COLOR = { ok: C.ok, pending: C.pending, suspect: C.suspect, dead: C.dead };

    /* 智能精简标签名称（防止超长域名或 IPv6 撑满屏幕） */
    function compactDisplayLabel(rawStr) {
      let s = String(rawStr || '—').trim();
      s = s.replace(/\s*\(局域网终端\)\s*$/, '').replace(/\s*\(局域网设备\)\s*$/, '');
      if (s.length > 22) {
        if (s.includes('.') && !s.includes(' ')) {
          const parts = s.split('.');
          if (parts.length >= 3 && s.length > 23) {
            const tail = parts.slice(-2).join('.');
            const head = parts[0].slice(0, Math.max(6, 20 - tail.length));
            return head + '….' + tail;
          }
        }
        return s.slice(0, 20) + '…';
      }
      return s;
    }

    /* ---------------- 渲染器与场景 ---------------- */
    const canvas = document.getElementById('h3-canvas');
    const ROOT = window.__h3Root;
    let W = ROOT.clientWidth || 960, H = ROOT.clientHeight || 600;
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(W, H);
    renderer.setClearColor(0x04020d, 1);
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050312, 0.0082);
    const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 260);
    const camRig = { dist: 23.4, yaw: 0, pitch: 0.54, target: new THREE.Vector3(-0.2, 0.35, -0.6) };
    function applyCam() {
      const { dist, yaw, pitch, target } = camRig;
      camera.position.set(
        target.x + dist * Math.cos(pitch) * Math.sin(yaw),
        target.y + dist * Math.sin(pitch),
        target.z + dist * Math.cos(pitch) * Math.cos(yaw)
      );
      camera.lookAt(target);
      camera.updateMatrixWorld();
    }
    applyCam();

    /* ---------------- 程序化高精度贴图生成 ---------------- */
    function nebulaTexture(size, palette, blobs) {
      const cv = document.createElement('canvas');
      cv.width = cv.height = size;
      const ctx = cv.getContext('2d');
      ctx.fillStyle = '#04020d';
      ctx.fillRect(0, 0, size, size);
      for (let i = 0; i < blobs; i++) {
        const x = ((i * 73 + 19) % 100) / 100 * size + (Math.sin(i * 2.1) * size * 0.08);
        const y = ((i * 41 + 37) % 100) / 100 * size + (Math.cos(i * 1.7) * size * 0.08);
        const r = size * (0.08 + (i % 5) * 0.042);
        const c = palette[i % palette.length];
        const g = ctx.createRadialGradient(x, y, 0, x, y, r);
        g.addColorStop(0, c.replace('A', '0.45'));
        g.addColorStop(0.42, c.replace('A', '0.16'));
        g.addColorStop(1, c.replace('A', '0'));
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
      }
      return new THREE.CanvasTexture(cv);
    }
    const NEBULA_PALETTE = [
      'rgba(124,58,237,A)',
      'rgba(14,165,233,A)',
      'rgba(234,88,12,A)',
      'rgba(217,70,239,A)',
      'rgba(16,185,129,A)'
    ];
    (function dome() {
      const tex = nebulaTexture(1024, NEBULA_PALETTE, 52);
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(105, 32, 24),
        new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, transparent: true, opacity: 0.90, depthWrite: false })
      );
      mesh.rotation.y = 0.6;
      mesh.frustumCulled = false;
      scene.add(mesh);
      window.__nebulaDome = mesh;
    })();
    const nebulaLayers = [];
    [[-46, 0.30, 0.005], [-66, 0.22, -0.0035]].forEach(([z, op, spin], i) => {
      const tex = nebulaTexture(768, NEBULA_PALETTE.slice(i, i + 4), 26);
      const mesh = new THREE.Mesh(
        new THREE.PlaneGeometry(168, 112),
        new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: op, depthWrite: false, blending: THREE.AdditiveBlending })
      );
      mesh.position.set(0, 0, z);
      mesh.userData.spin = spin;
      mesh.frustumCulled = false;
      scene.add(mesh);
      nebulaLayers.push(mesh);
    });

    function makeStarPointTexture() {
      const s = 64, cv = document.createElement('canvas');
      cv.width = cv.height = s;
      const ctx = cv.getContext('2d');
      const g = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
      g.addColorStop(0, 'rgba(255,255,255,1)');
      g.addColorStop(0.25, 'rgba(230,225,255,0.78)');
      g.addColorStop(0.6, 'rgba(168,150,255,0.18)');
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, s, s);
      return new THREE.CanvasTexture(cv);
    }
    const STAR_PT_TEX = makeStarPointTexture();
    const starLayers = [];
    (function buildStars() {
      const g1 = new THREE.BufferGeometry();
      const n1 = 1400, pos1 = new Float32Array(n1 * 3);
      for (let i = 0; i < n1; i++) {
        const r = 44 + ((i * 37) % 58);
        const th = (i * 2.39996) % (Math.PI * 2);
        const u = ((i * 0.6180339) % 1) * 2 - 1;
        const ph = Math.acos(u);
        pos1[i * 3] = r * Math.sin(ph) * Math.cos(th);
        pos1[i * 3 + 1] = r * Math.cos(ph);
        pos1[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
      }
      g1.setAttribute('position', new THREE.BufferAttribute(pos1, 3));
      const pts1 = new THREE.Points(g1, new THREE.PointsMaterial({
        map: STAR_PT_TEX, color: 0xc4b5fd, size: 0.62, transparent: true, opacity: 0.68,
        depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true
      }));
      scene.add(pts1);
      starLayers.push(pts1);
      const g2 = new THREE.BufferGeometry();
      const n2 = 240, pos2 = new Float32Array(n2 * 3), col2 = new Float32Array(n2 * 3);
      const starCols = [new THREE.Color(0x93c5fd), new THREE.Color(0xfde68a), new THREE.Color(0xd8b4fe), new THREE.Color(0x67e8f9)];
      for (let i = 0; i < n2; i++) {
        const r = 34 + ((i * 29) % 45);
        const th = (i * 1.7548) % (Math.PI * 2);
        const ph = Math.acos((((i * 0.754877) % 1) * 2) - 1);
        pos2[i * 3] = r * Math.sin(ph) * Math.cos(th);
        pos2[i * 3 + 1] = r * Math.cos(ph);
        pos2[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
        const sc = starCols[i % starCols.length];
        col2[i * 3] = sc.r; col2[i * 3 + 1] = sc.g; col2[i * 3 + 2] = sc.b;
      }
      g2.setAttribute('position', new THREE.BufferAttribute(pos2, 3));
      g2.setAttribute('color', new THREE.BufferAttribute(col2, 3));
      const pts2 = new THREE.Points(g2, new THREE.PointsMaterial({
        map: STAR_PT_TEX, vertexColors: true, size: 1.02, transparent: true, opacity: 0.80,
        depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true
      }));
      scene.add(pts2);
      starLayers.push(pts2);
    })();

    function glowTexture() {
      const s = 128, cv = document.createElement('canvas');
      cv.width = cv.height = s;
      const ctx = cv.getContext('2d');
      const g = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
      g.addColorStop(0, 'rgba(255,255,255,.92)');
      g.addColorStop(0.24, 'rgba(255,255,255,.45)');
      g.addColorStop(0.58, 'rgba(255,255,255,.12)');
      g.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, s, s);
      return new THREE.CanvasTexture(cv);
    }
    const GLOW_TEX = glowTexture();

    /* 生成卡冈都亚 (Gargantua) 多层对数螺旋吸积盘高清纹理 */
    function makeAccretionDiskTexture() {
      const s = 512, cv = document.createElement('canvas');
      cv.width = cv.height = s;
      const ctx = cv.getContext('2d');
      const cx = s / 2, cy = s / 2;
      // 1. 中心绝对黑暗空洞 + 贴近视界的高亮光子内环 + 炽橙至紫红吸积渐变
      const g = ctx.createRadialGradient(cx, cy, s * 0.145, cx, cy, s * 0.495);
      g.addColorStop(0.0, 'rgba(0,0,0,1)');
      g.addColorStop(0.03, 'rgba(0,0,0,1)');
      g.addColorStop(0.065, 'rgba(255,255,255,1)');
      g.addColorStop(0.13, 'rgba(254,240,138,0.96)');
      g.addColorStop(0.26, 'rgba(251,146,60,0.92)');
      g.addColorStop(0.46, 'rgba(234,88,12,0.78)');
      g.addColorStop(0.68, 'rgba(168,85,247,0.46)');
      g.addColorStop(0.88, 'rgba(88,28,135,0.18)');
      g.addColorStop(1.0, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, s, s);

      // 2. 同心暗环间隙（塑造多普勒分层感）
      [0.22, 0.31, 0.39].forEach((rf, idx) => {
        ctx.beginPath();
        ctx.arc(cx, cy, s * rf, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(6, 3, 18, ${0.42 - idx * 0.08})`;
        ctx.lineWidth = s * 0.012;
        ctx.stroke();
      });

      // 3. 密集等离子体对数螺旋流线
      ctx.save();
      ctx.translate(cx, cy);
      for (let i = 0; i < 64; i++) {
        const a0 = (i / 64) * Math.PI * 2;
        const isBright = (i % 3 === 0);
        ctx.strokeStyle = isBright ? 'rgba(255,247,237,0.34)' : 'rgba(251,146,60,0.20)';
        ctx.lineWidth = isBright ? 2.4 : 1.4;
        ctx.beginPath();
        for (let r = s * 0.165; r <= s * 0.47; r += 5) {
          const th = a0 - ((r - s * 0.165) / s) * 5.6;
          const x = Math.cos(th) * r, y = Math.sin(th) * r;
          if (r === s * 0.165) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
      ctx.restore();
      return new THREE.CanvasTexture(cv);
    }

    function makeStarSurfaceTexture(hexColor) {
      const w = 256, h = 128, cv = document.createElement('canvas');
      cv.width = w; cv.height = h;
      const ctx = cv.getContext('2d');
      const base = new THREE.Color(hexColor);
      const bright = base.clone().lerp(new THREE.Color(0xffffff), 0.62);
      const deep = base.clone().lerp(new THREE.Color(0x090518), 0.45);
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, '#' + bright.getHexString());
      grad.addColorStop(0.25, '#' + base.getHexString());
      grad.addColorStop(0.5, '#' + bright.getHexString());
      grad.addColorStop(0.75, '#' + base.getHexString());
      grad.addColorStop(1, '#' + deep.getHexString());
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = 'rgba(255,255,255,0.24)';
      ctx.lineWidth = 1.5;
      [0.32, 0.5, 0.68].forEach(yf => {
        ctx.beginPath(); ctx.moveTo(0, h * yf); ctx.lineTo(w, h * yf); ctx.stroke();
      });
      return new THREE.CanvasTexture(cv);
    }

    function makeGlow(color, size, opacity = 0.72) {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({
        map: GLOW_TEX, color, transparent: true, opacity,
        blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false
      }));
      sp.frustumCulled = false;
      sp.renderOrder = -10;
      sp.scale.set(size, size, 1);
      return sp;
    }

    /* 深度优化的纤巧抗锯齿 3D 卫星标签 (清爽、精致、不遮挡画面) */
    const labelCache = new Map();
    function makeLabel(text, color = '#f8fafc', opts = {}) {
      const safeTxt = compactDisplayLabel(text);
      const key = safeTxt + '|' + color + '|' + (opts.borderColor || '');
      if (labelCache.has(key)) return labelCache.get(key).clone();
      const padX = 16, padY = 8, fs = 24;
      const cv = document.createElement('canvas');
      const ctx = cv.getContext('2d');
      const fontMain = `600 ${fs}px "Inter",-apple-system,"PingFang SC","Microsoft YaHei",sans-serif`;
      ctx.font = fontMain;
      const tw = Math.ceil(ctx.measureText(safeTxt).width);
      const w = tw + padX * 2;
      const h = fs + padY * 2;
      cv.width = w; cv.height = h;
      const c2 = cv.getContext('2d');
      c2.fillStyle = 'rgba(8, 10, 22, 0.88)';
      c2.strokeStyle = opts.borderColor || 'rgba(148, 163, 184, 0.38)';
      c2.lineWidth = 2;
      const r = h / 2;
      c2.beginPath();
      c2.moveTo(r, 1); c2.lineTo(w - r, 1);
      c2.quadraticCurveTo(w - 1, 1, w - 1, r);
      c2.quadraticCurveTo(w - 1, h - 1, w - r, h - 1);
      c2.lineTo(r, h - 1);
      c2.quadraticCurveTo(1, h - 1, 1, r);
      c2.quadraticCurveTo(1, 1, r, 1);
      c2.closePath();
      c2.fill();
      c2.stroke();
      c2.textAlign = 'center';
      c2.textBaseline = 'middle';
      c2.font = fontMain;
      c2.fillStyle = '#f8fafc';
      c2.fillText(safeTxt, w / 2, h / 2 + 1);
      const tex = new THREE.CanvasTexture(cv);
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({
        map: tex, transparent: true, depthTest: false, depthWrite: false, opacity: 0.92
      }));
      sp.frustumCulled = false;
      sp.renderOrder = 22;
      const scale = 0.0128;
      sp.scale.set(w * scale, h * scale, 1);
      sp.userData = { baseW: w * scale, baseH: h * scale };
      labelCache.set(key, sp);
      const cloned = sp.clone();
      cloned.userData = { baseW: w * scale, baseH: h * scale };
      return cloned;
    }

    /* ---------------- 三大星系 + 第四天体「深空引力黑洞」构建 ---------------- */
    const pickables = [];
    const allLabels = [];
    const galaxyGroup = {};
    const GAL = {};

    function buildGalaxy(key) {
      const cfg = GALAXY[key];
      const g = new THREE.Group();
      g.position.copy(cfg.center);
      scene.add(g);
      galaxyGroup[key] = g;
      const starTex = makeStarSurfaceTexture(cfg.color);
      const star = new THREE.Mesh(
        new THREE.SphereGeometry(0.75, 36, 36),
        new THREE.MeshBasicMaterial({ map: starTex })
      );
      star.userData = { kind: 'star', galaxy: key, baseR: 0.75 };
      g.add(star);
      pickables.push(star);

      const gyro1 = new THREE.Mesh(
        new THREE.RingGeometry(1.05, 1.11, 64),
        new THREE.MeshBasicMaterial({ color: cfg.color, side: THREE.DoubleSide, transparent: true, opacity: 0.46, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      gyro1.rotation.x = Math.PI / 2.3;
      gyro1.frustumCulled = false;
      g.add(gyro1);
      star.userData.gyro1 = gyro1;

      const gyro2 = new THREE.Mesh(
        new THREE.RingGeometry(1.26, 1.30, 64),
        new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide, transparent: true, opacity: 0.24, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      gyro2.rotation.x = Math.PI / 1.7;
      gyro2.rotation.y = 0.45;
      gyro2.frustumCulled = false;
      g.add(gyro2);
      star.userData.gyro2 = gyro2;

      const alertRing = new THREE.Mesh(
        new THREE.TorusGeometry(2.05, 0.08, 12, 72),
        new THREE.MeshBasicMaterial({ color: 0xff3b30, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      alertRing.rotation.x = Math.PI / 2;
      alertRing.visible = false;
      alertRing.frustumCulled = false;
      g.add(alertRing);
      star.userData.alertRing = alertRing;

      const glowColor = new THREE.Color(cfg.color).lerp(new THREE.Color(0xffffff), 0.42);
      const glow = makeGlow(glowColor.getHex(), 4.2, 0.50);
      g.add(glow);
      star.userData.glow = glow;

      const halo = new THREE.Mesh(
        new THREE.SphereGeometry(1.0, 28, 28),
        new THREE.MeshBasicMaterial({ color: cfg.color, transparent: true, opacity: 0.14, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      halo.frustumCulled = false;
      g.add(halo);
      star.userData.halo = halo;

      const ringPts = [];
      for (let i = 0; i <= 128; i++) {
        const a = i / 128 * Math.PI * 2;
        ringPts.push(new THREE.Vector3(Math.cos(a) * 2.95, 0, Math.sin(a) * 2.95));
      }
      const ring = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(ringPts),
        new THREE.LineBasicMaterial({ color: cfg.color, transparent: true, opacity: 0.22, depthWrite: false })
      );
      ring.frustumCulled = false;
      g.add(ring);

      (function dust() {
        const N = 110, g2 = new THREE.BufferGeometry(), pos = new Float32Array(N * 3);
        for (let i = 0; i < N; i++) {
          const r = 1.25 + ((i * 19) % 100) / 100 * 2.1;
          const th = (i * 2.39996) % (Math.PI * 2);
          const ph = (((i * 0.618) % 1) - 0.5) * 0.9;
          pos[i * 3] = Math.cos(th) * r * Math.cos(ph);
          pos[i * 3 + 1] = Math.sin(ph) * r * 0.55;
          pos[i * 3 + 2] = Math.sin(th) * r * Math.cos(ph);
        }
        g2.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        const pts = new THREE.Points(g2, new THREE.PointsMaterial({
          map: STAR_PT_TEX, color: cfg.color, size: 0.16, transparent: true, opacity: 0.56,
          blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true
        }));
        pts.userData.spin = 0.055 + (key === 'lan' ? 0.025 : 0.01);
        pts.frustumCulled = false;
        g.add(pts);
        galaxyGroup[key].dust = pts;
      })();

      const kMetrics = key === 'lan' ? [
        { name: '下行速率', angle: Math.PI * 0.68, kind: 'down' },
        { name: '上行速率', angle: Math.PI * 1.00, kind: 'up' },
        { name: '内存占用', angle: Math.PI * 1.32, kind: 'mem' },
      ] : [];
      const health = [];
      const angles = key === 'domestic'
        ? [-0.35, -1.15, -1.95, -2.75]
        : [0.35, 1.15, 1.95, 2.75];
      (HEALTH_TARGETS[key] || []).forEach((name, i) => {
        health.push({ name, angle: angles[i], ms: -1, state: 'pending' });
      });
      if (health.length || kMetrics.length) {
        const pts3 = [];
        for (let i = 0; i < 160; i++) {
          const a = i / 160 * Math.PI * 2;
          pts3.push(new THREE.Vector3(Math.cos(a) * HEALTH_RING_R, 0, Math.sin(a) * HEALTH_RING_R));
        }
        [0, 0.22].forEach(off => {
          const pts = pts3.map(v => v.clone().multiplyScalar((HEALTH_RING_R + off) / HEALTH_RING_R));
          const hr = new THREE.LineLoop(
            new THREE.BufferGeometry().setFromPoints(pts),
            new THREE.LineDashedMaterial({ color: cfg.color, transparent: true, opacity: off ? 0.12 : 0.32, dashSize: 0.18, gapSize: 0.16, depthWrite: false })
          );
          hr.computeLineDistances();
          hr.frustumCulled = false;
          g.add(hr);
        });
      }
      return { group: g, star, health, kMetrics, ring, satellites: [], slots: new Array(10).fill(null) };
    }

    /* ---------------- 构建深空引力黑洞 (Interstellar Gargantua 造型：正常视角下呈现饱满宽阔吸积盘 + 引力透镜拱环 + 纯黑视界) ---------------- */
    function buildBlackHole() {
      const cfg = GALAXY.blackhole;
      const g = new THREE.Group();
      g.position.copy(cfg.center);
      scene.add(g);
      galaxyGroup.blackhole = g;

      // 1. 纯黑事件视界奇点核心 (Event Horizon Shadow — renderOrder 最高以确保在吸积盘中心抠出深邃纯黑球体)
      const horizon = new THREE.Mesh(
        new THREE.SphereGeometry(1.12, 48, 48),
        new THREE.MeshBasicMaterial({ color: 0x000000, depthWrite: true })
      );
      horizon.renderOrder = 5;
      horizon.userData = { kind: 'star', galaxy: 'blackhole', baseR: 1.12 };
      g.add(horizon);
      pickables.push(horizon);

      // 2. 紧贴事件视界边缘的炽白光子环 (Einstein Photon Ring — 始终正对或微倾于相机)
      const photonRing = new THREE.Mesh(
        new THREE.RingGeometry(1.13, 1.24, 96),
        new THREE.MeshBasicMaterial({ color: 0xfff7ed, side: THREE.DoubleSide, transparent: true, opacity: 0.96, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      photonRing.rotation.x = 0.35;
      photonRing.renderOrder = 6;
      g.add(photonRing);
      horizon.userData.gyro1 = photonRing;

      // 3. 主吸积盘 (Main Relativistic Accretion Disk) —— 针对默认俯角 pitch=0.54rad 定制倾角：
      //    rotation.x = -Math.PI * 0.30 (-54°)，与视线形成约 42° 黄金夹角，呈现宽阔饱满的椭圆螺旋星盘，绝不变成一条细线！
      const diskTex = makeAccretionDiskTexture();
      const accDisk = new THREE.Mesh(
        new THREE.PlaneGeometry(8.8, 8.8),
        new THREE.MeshBasicMaterial({ map: diskTex, side: THREE.DoubleSide, transparent: true, opacity: 0.96, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      accDisk.rotation.x = -Math.PI * 0.30;
      accDisk.rotation.y = 0.08;
      accDisk.renderOrder = 4;
      g.add(accDisk);
      horizon.userData.accDisk = accDisk;

      // 4. 卡冈都亚引力透镜上下弯曲光环 (Gravitational Lensing Bent Upper/Lower Halo Disk)
      //    与主吸积盘近似正交（rotation.x = Math.PI * 0.14），围绕纯黑球体形成《星际穿越》标志性的上下立体弯曲光晕拱桥
      const lensDisk = new THREE.Mesh(
        new THREE.RingGeometry(1.16, 2.38, 96),
        new THREE.MeshBasicMaterial({ color: 0xfb923c, side: THREE.DoubleSide, transparent: true, opacity: 0.44, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      lensDisk.rotation.x = Math.PI * 0.14;
      lensDisk.rotation.y = -0.10;
      lensDisk.renderOrder = 3;
      g.add(lensDisk);
      horizon.userData.gyro2 = lensDisk;

      // 外围柔光晕（降低浓度避免把黑洞中心染成实心橙球）
      const glow = makeGlow(0xea580c, 5.4, 0.32);
      glow.renderOrder = 1;
      g.add(glow);
      horizon.userData.glow = glow;

      // 5. 螺旋坠入事件视界的广告/追踪碎片粒子流 (Infalling Ad/Tracker Debris Stream — 与主吸积盘共面)
      const DEBRIS_N = 96;
      const dGeo = new THREE.BufferGeometry();
      const dPos = new Float32Array(DEBRIS_N * 3);
      const dCol = new Float32Array(DEBRIS_N * 3);
      const dMeta = [];
      const debrisPalette = [new THREE.Color(0xfef08a), new THREE.Color(0xfb923c), new THREE.Color(0xf43f5e), new THREE.Color(0xc084fc)];
      for (let i = 0; i < DEBRIS_N; i++) {
        const r = 1.28 + ((i * 23) % 100) / 100 * 3.1;
        const a = (i * 2.39996) % (Math.PI * 2);
        const zOff = (((i * 0.618) % 1) - 0.5) * 0.35;
        dMeta.push({ r, a, zOff, speed: 0.72 + (i % 7) * 0.14 });
        dPos[i * 3] = Math.cos(a) * r;
        dPos[i * 3 + 1] = Math.sin(a) * r;
        dPos[i * 3 + 2] = zOff;
        const dc = debrisPalette[i % debrisPalette.length];
        dCol[i * 3] = dc.r; dCol[i * 3 + 1] = dc.g; dCol[i * 3 + 2] = dc.b;
      }
      dGeo.setAttribute('position', new THREE.BufferAttribute(dPos, 3));
      dGeo.setAttribute('color', new THREE.BufferAttribute(dCol, 3));
      const debrisPts = new THREE.Points(dGeo, new THREE.PointsMaterial({
        map: STAR_PT_TEX, vertexColors: true, size: 0.24, transparent: true, opacity: 0.90,
        blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true
      }));
      debrisPts.rotation.x = -Math.PI * 0.30;
      debrisPts.rotation.y = 0.08;
      debrisPts.renderOrder = 6;
      g.add(debrisPts);

      const ringPts = [];
      for (let i = 0; i <= 128; i++) {
        const a = i / 128 * Math.PI * 2;
        ringPts.push(new THREE.Vector3(Math.cos(a) * 4.25, Math.sin(a) * 4.25, 0));
      }
      const ring = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(ringPts),
        new THREE.LineDashedMaterial({ color: 0xf97316, transparent: true, opacity: 0.26, dashSize: 0.22, gapSize: 0.18, depthWrite: false })
      );
      ring.computeLineDistances();
      ring.rotation.x = -Math.PI * 0.30;
      ring.rotation.y = 0.08;
      g.add(ring);

      return { group: g, star: horizon, health: [], kMetrics: [], ring, debrisPts, debrisMeta: dMeta, satellites: [] };
    }

    ['lan', 'domestic', 'foreign'].forEach(k => { GAL[k] = buildGalaxy(k); });
    GAL.blackhole = buildBlackHole();

    /* ---------------- 覆盖层：母星铭牌 + 探测胶囊 (精简克制，无杂乱引线) ---------------- */
    const healthEls = {};
    const starBadgeEls = {};
    const healthRects = {};

    function buildHealthLayer() {
      const layer = document.getElementById('h3-health-layer');
      if (!layer) return;
      layer.innerHTML = '';
      ['lan', 'domestic', 'foreign', 'blackhole'].forEach(k => {
        const cfg = GALAXY[k];
        const b = document.createElement('div');
        b.className = 'h3-star-badge' + (k === 'blackhole' ? ' bh-badge' : '');
        b.title = '点击展开该星系实时详情单';
        b.innerHTML = `<span class="s-dot" style="background:${cfg.css};box-shadow:0 0 8px ${cfg.css}"></span><span class="s-nm">${k === 'blackhole' ? '🕳️ ' + cfg.name : cfg.name}</span><span class="s-sub">· ${cfg.sub}</span>`;
        b.onclick = (ev) => {
          ev.stopPropagation();
          openGalaxyDrawer(k);
          focusGalaxyCamera(k);
        };
        layer.appendChild(b);
        starBadgeEls[k] = b;
      });
      const kChips = [];
      (GAL.lan.kMetrics || []).forEach(m => {
        const c = document.createElement('div');
        c.className = 'hc';
        c.innerHTML = `<i class="dot" style="background:#a78bfa;color:#a78bfa"></i><span class="nm">${m.name}</span><span class="ms v">—</span>`;
        layer.appendChild(c);
        kChips.push(c);
      });
      healthEls.lan = kChips;

      ['domestic', 'foreign'].forEach(k => {
        const chips = [];
        (HEALTH_TARGETS[k] || []).forEach(name => {
          const c = document.createElement('div');
          c.className = 'hc ' + (k === 'domestic' ? 'hc-dom' : 'hc-fore');
          c.innerHTML = `<i class="dot"></i><span class="nm">${name}</span><span class="ms">—</span>`;
          layer.appendChild(c);
          chips.push(c);
        });
        healthEls[k] = chips;
      });
    }

    const _hp = new THREE.Vector3();
    function clampToSafeViewport(x, y, chipW, chipH) {
      if (W < 640) {
        const padX = Math.max(42, chipW * 0.42);
        const cx = Math.max(padX, Math.min(W - padX, x));
        const cy = Math.max(52, Math.min(H - 180, y));
        return { x: Math.round(cx), y: Math.round(cy) };
      }
      const padX = Math.max(58, chipW * 0.52);
      let cx = Math.max(padX, Math.min(W - padX, x));
      let cy = Math.max(56, Math.min(H - 96, y));
      if (cx < 460 && cy < 98) cy = 100;
      if (cx < 320 && cy > H - 220) cy = H - 224;
      if (cx > W - 380 && cy > H - 140) cy = H - 142;
      return { x: Math.round(cx), y: Math.round(cy) };
    }

    function updateHealthLayer() {
      const zoomScale = Math.max(0.84, Math.min(1.04, 23.4 / Math.max(12, camRig.dist)));
      const placedBoxes = [];
      ['lan', 'domestic', 'foreign', 'blackhole'].forEach(k => {
        const g = GAL[k];
        const b = starBadgeEls[k];
        if (!g || !b) return;
        _hp.set(0, k === 'blackhole' ? -2.35 : -1.15, 0);
        g.group.localToWorld(_hp);
        const v = _hp.clone().project(camera);
        if (v.z > 1) { b.style.display = 'none'; return; }
        b.style.display = 'flex';
        const rawX = (v.x * 0.5 + 0.5) * W;
        const rawY = (-v.y * 0.5 + 0.5) * H;
        const cl = clampToSafeViewport(rawX, rawY, 170, 26);
        b.style.left = cl.x + 'px';
        b.style.top = cl.y + 'px';
        b.style.transform = `translate(-50%,-50%) scale(${zoomScale.toFixed(3)})`;
        const subEl = b.querySelector('.s-sub');
        if (subEl) {
          if (k === 'foreign' && state.exitNode) {
            subEl.textContent = `· ${state.exitNode.slice(0, 14)}`;
          } else if (k === 'blackhole') {
            subEl.textContent = `· 已吞噬 ${state.bh.blocked_queries || 0} 次 · ${((state.bh.active_rules || 50000) / 1000).toFixed(1)}k 规则`;
          } else if (k === 'lan') {
            subEl.textContent = `· ${state.devices.length} 台终端在线`;
          }
        }
        placedBoxes.push({ x: cl.x, y: cl.y, w: 175 * zoomScale, h: 28 * zoomScale, fixed: true });
      });

      const pendingChips = [];
      if (healthEls.lan && GAL.lan) {
        const g = GAL.lan;
        const vals = {
          down: fmt(state.totalDown),
          up: fmt(state.totalUp),
          mem: ((state.memMib || LIVE.mem) > 0 ? (state.memMib || LIVE.mem).toFixed(1) : '—') + ' MiB',
        };
        healthRects.lan = [];
        (g.kMetrics || []).forEach((m, i) => {
          const c = healthEls.lan[i];
          if (!c) return;
          _hp.set(Math.cos(m.angle) * HEALTH_RING_R, 0, Math.sin(m.angle) * HEALTH_RING_R);
          g.group.localToWorld(_hp);
          const v = _hp.clone().project(camera);
          if (v.z > 1) { c.style.display = 'none'; return; }
          c.style.display = 'flex';
          const msEl = c.querySelector('.ms');
          if (msEl) msEl.textContent = vals[m.kind] || '—';
          const cl = clampToSafeViewport((v.x * 0.5 + 0.5) * W, (-v.y * 0.5 + 0.5) * H, 128, 24);
          pendingChips.push({ el: c, gal: 'lan', x: cl.x, y: cl.y, w: 128 * zoomScale, h: 25 * zoomScale });
        });
      }

      ['domestic', 'foreign'].forEach(k => {
        const chips = healthEls[k];
        const g = GAL[k];
        if (!chips || !g) return;
        healthRects[k] = [];
        g.health.forEach((h, i) => {
          const c = chips[i];
          if (!c) return;
          _hp.set(Math.cos(h.angle) * HEALTH_RING_R, 0, Math.sin(h.angle) * HEALTH_RING_R);
          g.group.localToWorld(_hp);
          const v = _hp.clone().project(camera);
          if (v.z > 1) { c.style.display = 'none'; return; }
          c.style.display = 'flex';
          const isProxySide = (k === 'foreign');
          const okLim = isProxySide ? 1500 : 400;
          const susLim = isProxySide ? 3500 : 2000;
          const isPend = (h.state === 'pending' && h.ms < 0);
          const cls = isPend ? 'v' : (h.ms < 0 ? 'r' : (h.ms < okLim ? 'g' : (h.ms < susLim ? 'y' : 'r')));
          const dotColor = isPend ? '#94a3b8' : (h.ms < 0 ? '#f87171' : (h.ms < okLim ? '#34d399' : (h.ms < susLim ? '#fbbf24' : '#f87171')));
          const msEl = c.querySelector('.ms');
          const dotEl = c.querySelector('.dot');
          if (msEl) { msEl.className = 'ms ' + cls; msEl.textContent = isPend ? '待测' : (h.ms > 0 ? h.ms + 'ms' : '超时'); }
          if (dotEl) { dotEl.style.background = dotColor; dotEl.style.color = dotColor; }
          const cl = clampToSafeViewport((v.x * 0.5 + 0.5) * W, (-v.y * 0.5 + 0.5) * H, 116, 24);
          pendingChips.push({ el: c, gal: k, x: cl.x, y: cl.y, w: 116 * zoomScale, h: 25 * zoomScale });
        });
      });

      for (let iter = 0; iter < 6; iter++) {
        for (let i = 0; i < pendingChips.length; i++) {
          const a = pendingChips[i];
          for (let j = 0; j < placedBoxes.length; j++) {
            const b = placedBoxes[j];
            const minDx = (a.w + b.w) * 0.54;
            const minDy = (a.h + b.h) * 0.64;
            const dx = a.x - b.x, dy = a.y - b.y;
            if (Math.abs(dx) < minDx && Math.abs(dy) < minDy) {
              a.y += (dy >= 0 ? (minDy - dy + 4) : -(minDy + dy + 4));
            }
          }
          for (let j = i + 1; j < pendingChips.length; j++) {
            const b = pendingChips[j];
            const minDx = (a.w + b.w) * 0.54;
            const minDy = (a.h + b.h) * 0.64;
            const dx = a.x - b.x, dy = a.y - b.y;
            if (Math.abs(dx) < minDx && Math.abs(dy) < minDy) {
              const overlapY = (minDy - Math.abs(dy)) * 0.58 + 3;
              if (dy >= 0) { a.y += overlapY; b.y -= overlapY; }
              else { a.y -= overlapY; b.y += overlapY; }
            }
          }
          const cl = clampToSafeViewport(a.x, a.y, a.w, a.h);
          a.x = cl.x; a.y = cl.y;
        }
      }

      if (W < 640) {
        const mobChips = [];
        pendingChips.forEach(item => {
          if (item.gal === 'lan') {
            item.el.style.display = 'none';
          } else {
            mobChips.push(item);
          }
        });
        const cols = 4;
        const colW = Math.floor((W - 16) / cols);
        mobChips.forEach((item, idx) => {
          const r = Math.floor(idx / cols);
          const c = idx % cols;
          const gx = 8 + colW * c + Math.floor(colW * 0.5);
          const gy = H - 152 + r * 28;
          item.el.style.left = gx + 'px';
          item.el.style.top = gy + 'px';
          item.el.style.transform = 'translate(-50%,-50%) scale(0.88)';
          if (!healthRects[item.gal]) healthRects[item.gal] = [];
          healthRects[item.gal].push({ x: gx, y: gy });
        });
      } else {
        pendingChips.forEach(item => {
          item.el.style.left = item.x + 'px';
          item.el.style.top = item.y + 'px';
          item.el.style.transform = `translate(-50%,-50%) scale(${zoomScale.toFixed(3)})`;
          if (!healthRects[item.gal]) healthRects[item.gal] = [];
          healthRects[item.gal].push({ x: item.x, y: item.y });
        });
      }
      const svgEl = document.getElementById('h3-leaders-svg');
      if (svgEl) svgEl.innerHTML = '';
    }

    buildHealthLayer();
    ['domestic', 'foreign'].forEach(k => {
      GAL[k].health.forEach(h => { h.ms = -1; h.state = 'pending'; });
    });

    /* ---------------- 3D 弧线能量导管 + 彗星光子流 ---------------- */
    const links = [];
    const _curveTmpMid = new THREE.Vector3();
    const _sharedPhotonGeo = new THREE.SphereGeometry(1, 10, 10);
    function computeArcPoints(a, b, isTrunk, segments) {
      _curveTmpMid.copy(a).add(b).multiplyScalar(0.5);
      const dist = a.distanceTo(b);
      _curveTmpMid.y += isTrunk ? Math.min(1.5, dist * 0.09) : Math.min(0.42, dist * 0.055);
      const curve = new THREE.QuadraticBezierCurve3(a.clone(), _curveTmpMid.clone(), b.clone());
      return { curve, pts: curve.getPoints(segments) };
    }
    function makeLink(a, b, color, opts = {}) {
      const isTrunk = (opts.kind || 'trunk') === 'trunk' || opts.kind === 'blackhole_pull';
      const segs = isTrunk ? 38 : 20;
      const { curve, pts } = computeArcPoints(a, b, isTrunk, segs);
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const mat = new THREE.LineBasicMaterial({
        color, transparent: true, opacity: opts.opacity ?? 0.42,
        blending: THREE.AdditiveBlending, depthWrite: false
      });
      const line = new THREE.Line(geo, mat);
      line.frustumCulled = false;
      scene.add(line);
      const parts = [];
      const maxN = 6;
      const dotR = opts.dotR ?? 0.06;
      for (let i = 0; i < maxN; i++) {
        const pMat = new THREE.MeshBasicMaterial({
          color, transparent: true, opacity: 0.94,
          blending: THREE.AdditiveBlending, depthWrite: false
        });
        const p = new THREE.Mesh(_sharedPhotonGeo, pMat);
        p.scale.setScalar(dotR);
        const haloSp = makeGlow(color, dotR * 5.6, 0.52);
        p.add(haloSp);
        p.visible = false;
        p.frustumCulled = false;
        scene.add(p);
        parts.push({ mesh: p, halo: haloSp, t: i / maxN });
      }
      const L = { a: a.clone(), b: b.clone(), curve, segs, isTrunk, line, mat, parts, color, rate: 0, active: true, kind: opts.kind || 'trunk', owner: opts.owner || null };
      links.push(L);
      return L;
    }

    const trunkDomestic  = makeLink(GALAXY.lan.center, GALAXY.domestic.center,  C.direct,    { opacity: 0.50, dotR: 0.08, kind: 'trunk' });
    const trunkForeign   = makeLink(GALAXY.lan.center, GALAXY.foreign.center,   C.proxy,     { opacity: 0.50, dotR: 0.08, kind: 'trunk' });
    const trunkBlackHole = makeLink(GALAXY.lan.center, GALAXY.blackhole.center, C.blackhole, { opacity: 0.44, dotR: 0.075, kind: 'blackhole_pull' });

    /* ---------------- 速率分档与状态模型 ---------------- */
    const TIER_SPEED = [0.08, 0.14, 0.32, 0.65];
    const TIER_COUNT = [1, 2, 4, 6];
    const TIER_NAME = ['待命 (慢速巡航)', '慢速 (1x)', '中速 (3x)', '高速 (6x)'];
    function speedTier(rate) {
      if (!rate || rate <= 0) return 0;
      if (rate < 200 * 1024) return 1;
      if (rate < 2 * 1024 * 1024) return 2;
      return 3;
    }
    const fmt = b => b > 1048576 ? (b / 1048576).toFixed(1) + ' MB/s'
      : b > 1024 ? (b / 1024).toFixed(0) + ' KB/s' : Math.max(0, Number(b) || 0).toFixed(0) + ' B/s';

    const state = {
      devices: [], domestic: [], foreign: [],
      locked: null, hovered: null, showAll: false, autoOrbit: false,
      drawerTab: 'blackhole',
      totalConn: 0, totalDown: 0, totalUp: 0, memMib: 0, uptime: '', sysUptime: '', proxyOk: true,
      exitNode: '', exitDelay: 0, exitState: '', directExitLabel: '宽带直连 (WAN)',
      particleCount: 4, particleTier: '待命 (慢速巡航)',
      bh: {
        enabled: true, active_rules: 50085, blocked_queries: 64, total_queries: 420,
        dns_layer_blocks: 25, route_reject_blocks: 39, block_rate_pct: 15.2,
        srs_compiled: true, srs_size_kb: 404.3, last_block_domain: 'cpro.baidu.com',
        categories: [
          { name: '商业广告联盟与弹窗', count: 36, pct: 56.3 },
          { name: '开屏广告与终端SDK', count: 18, pct: 28.1 },
          { name: '隐私遥测与追踪探针', count: 6, pct: 9.4 },
          { name: 'PCDN盗刷与后台上传', count: 4, pct: 6.2 },
        ],
        top_blocked: [
          { domain: 'cpro.baidu.com', count: 14, category: '商业广告联盟与弹窗', layer: '路由层REJECT' },
          { domain: 'pangolin-sdk-toutiao.com', count: 11, category: '开屏广告与终端SDK', layer: '路由层REJECT' },
          { domain: 'log.snssdk.com', count: 9, category: '隐私遥测与追踪探针', layer: 'DNS层REFUSED' },
          { domain: 'googleads.g.doubleclick.net', count: 8, category: '商业广告联盟与弹窗', layer: '路由层REJECT' },
          { domain: 'adsmind.ugdtimg.com', count: 7, category: '开屏广告与终端SDK', layer: 'DNS层REFUSED' },
          { domain: 'tanx.com', count: 6, category: '商业广告联盟与弹窗', layer: '路由层REJECT' },
        ]
      },
      active: true,
    };

    /* ---------------- 四星系通用全息展开详情抽屉渲染器 ---------------- */
    function renderGalaxyDrawer() {
      const tab = state.drawerTab || 'blackhole';
      const bh = state.bh || {};
      const elTopBh = document.getElementById('h3-t-bh');
      if (elTopBh) {
        elTopBh.textContent = `${bh.blocked_queries || 0} 次 · ${(bh.active_rules || 50000).toLocaleString()} 规则`;
      }
      document.querySelectorAll('#h3-drawer-tabs .h3-dtab').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-dtab') === tab);
      });

      const elIcon = document.getElementById('h3-bhd-icon');
      const elTitle = document.getElementById('h3-bhd-title');
      const elSub = document.getElementById('h3-bhd-sub');
      const k1L = document.getElementById('h3-kpi1-l'), k1V = document.getElementById('h3-bhd-blocked'), k1S = document.getElementById('h3-kpi1-s');
      const k2L = document.getElementById('h3-kpi2-l'), k2V = document.getElementById('h3-bhd-rules'), k2S = document.getElementById('h3-bhd-srs-meta');
      const k3L = document.getElementById('h3-kpi3-l'), k3V = document.getElementById('h3-bhd-dns-blk'), k3S = document.getElementById('h3-kpi3-s');
      const k4L = document.getElementById('h3-kpi4-l'), k4V = document.getElementById('h3-bhd-route-blk'), k4S = document.getElementById('h3-kpi4-s');
      const actBox = document.getElementById('h3-bhd-actions');
      const s1Title = document.getElementById('h3-sec1-title'), s1Sub = document.getElementById('h3-bhd-last-hit'), catsBox = document.getElementById('h3-bhd-cats');
      const s2Title = document.getElementById('h3-sec2-title'), s2Sub = document.getElementById('h3-sec2-sub'), topBox = document.getElementById('h3-bhd-top-list');

      if (tab === 'blackhole') {
        if (elIcon) elIcon.textContent = '🕳️';
        if (elTitle) elTitle.textContent = '深空引力黑洞 · 净网广告拦截中枢';
        if (elSub) elSub.textContent = 'AdGuardHome 级双擎护盾 (DNS Sinkhole + 路由层 .srs 规则集)';
        if (k1L) k1L.textContent = '已吞噬广告/追踪请求';
        if (k1V) { k1V.style.color = '#fb923c'; k1V.textContent = (bh.blocked_queries || 0).toLocaleString(); }
        if (k1S) k1S.innerHTML = `拦截率 <b style="color:#fde68a" id="h3-bhd-rate">${bh.block_rate_pct || 0}%</b> · 实时引力捕获`;
        if (k2L) k2L.textContent = '挂载有效黑名单规则';
        if (k2V) { k2V.style.color = '#34d399'; k2V.textContent = (bh.active_rules || 0).toLocaleString(); }
        if (k2S) k2S.textContent = bh.srs_compiled ? `已编译 .srs (${bh.srs_size_kb || 404} KB) + DNS 0.0.0.0 双保险` : `已加载 ${bh.active_rules || 0} 条规则 · 双层阻断生效`;
        if (k3L) k3L.textContent = 'DNS 层前置阻断 (0.0.0.0)';
        if (k3V) { k3V.style.color = '#38bdf8'; k3V.textContent = (bh.dns_layer_blocks || 0).toLocaleString(); }
        if (k3S) k3S.textContent = '毫秒级零连接开销拒绝';
        if (k4L) k4L.textContent = '路由层 REJECT 掐断';
        if (k4V) { k4V.style.color = '#c084fc'; k4V.textContent = (bh.route_reject_blocks || 0).toLocaleString(); }
        if (k4S) k4S.textContent = '防 DoH/硬编码绕过兜底';
        if (actBox) actBox.style.display = 'flex';
        if (s1Title) s1Title.textContent = '📊 吞噬威胁分类占比';
        if (s1Sub) s1Sub.textContent = `最近吞噬: ${bh.last_block_domain || 'cpro.baidu.com'}`;
        if (catsBox && Array.isArray(bh.categories)) {
          catsBox.innerHTML = bh.categories.map(c => `
            <div class="h3-bh-cat-row">
              <div class="h3-bh-cat-top"><span>${c.name}</span><span style="color:#fde68a">${c.count} 次 (${c.pct}%)</span></div>
              <div class="h3-bh-bar-bg"><div class="h3-bh-bar-fg" style="width:${Math.max(4, Math.min(100, c.pct || 0))}%"></div></div>
            </div>
          `).join('');
        }
        if (s2Title) s2Title.textContent = '🔥 黑洞吞噬高频域名 TOP 榜';
        if (s2Sub) s2Sub.textContent = '实时统计';
        if (topBox && Array.isArray(bh.top_blocked)) {
          topBox.innerHTML = bh.top_blocked.map(item => `
            <div class="h3-bh-dom-item">
              <span class="h3-bh-dom-name" title="${item.domain}">${item.domain}</span>
              <div class="h3-bh-dom-meta">
                <span class="h3-bh-tag">${item.layer || '路由REJECT'}</span>
                <span class="h3-bh-cnt">${item.count}次</span>
              </div>
            </div>
          `).join('');
        }
      } else if (tab === 'lan') {
        const lanDevs = state.devices.filter(d => !d.isRemote);
        const remDevs = state.devices.filter(d => d.isRemote);
        if (elIcon) elIcon.textContent = '🧠';
        if (elTitle) elTitle.textContent = '内核中枢 · sing-box 与终端星系';
        if (elSub) elSub.textContent = 'TProxy :7893 + Mixed :7890 全透明网关与内网终端实时吞吐';
        if (k1L) k1L.textContent = '活跃并发总连接';
        if (k1V) { k1V.style.color = '#a78bfa'; k1V.textContent = state.totalConn + ' 条'; }
        if (k1S) k1S.textContent = `内核运行: ${state.uptime || '运行中'}`;
        if (k2L) k2L.textContent = '实时总吞吐 (下/上行)';
        if (k2V) { k2V.style.color = '#34d399'; k2V.textContent = fmt(state.totalDown); }
        if (k2S) k2S.textContent = `上行速率: ${fmt(state.totalUp)}`;
        if (k3L) k3L.textContent = '局域网在线终端';
        if (k3V) { k3V.style.color = '#38bdf8'; k3V.textContent = lanDevs.length + ' 台'; }
        if (k3S) k3S.textContent = `含 IPv4 与 SLAAC/ULA IPv6 终端`;
        if (k4L) k4L.textContent = '内核内存占用 (RSS)';
        if (k4V) { k4V.style.color = '#f472b6'; k4V.textContent = (Number(state.memMib) || 0).toFixed(1) + ' MiB'; }
        if (k4S) k4S.textContent = remDevs.length > 0 ? `🏠 回家远程接入: ${remDevs.length} 台` : '🏠 回家远程接入: 0 台';
        if (actBox) actBox.style.display = 'none';
        if (s1Title) s1Title.textContent = '📡 内核网关工作状态';
        if (s1Sub) s1Sub.textContent = state.proxyOk ? '● 代理链路健康' : '● 降级保护中';
        if (catsBox) {
          const dPct = Math.min(100, Math.round((state.totalDown / (10 * 1048576)) * 100));
          const mPct = Math.min(100, Math.round(((state.memMib || 45) / 256) * 100));
          catsBox.innerHTML = `
            <div class="h3-bh-cat-row">
              <div class="h3-bh-cat-top"><span>实时下行负载 (${fmt(state.totalDown)})</span><span style="color:#a78bfa">当前出口: ${state.exitNode || '直连'}</span></div>
              <div class="h3-bh-bar-bg"><div class="h3-bh-bar-fg" style="width:${Math.max(6, dPct)}%;background:linear-gradient(90deg,#8b5cf6,#38bdf8)"></div></div>
            </div>
            <div class="h3-bh-cat-row">
              <div class="h3-bh-cat-top"><span>内核内存水位 (${(Number(state.memMib) || 0).toFixed(1)} MiB)</span><span style="color:#34d399">安全阈值 &lt; 210 MiB</span></div>
              <div class="h3-bh-bar-bg"><div class="h3-bh-bar-fg" style="width:${Math.max(8, mPct)}%;background:linear-gradient(90deg,#10b981,#38bdf8)"></div></div>
            </div>
          `;
        }
        if (s2Title) s2Title.textContent = `💻 活跃内网与回家终端列表 (${state.devices.length})`;
        if (s2Sub) s2Sub.textContent = '按实时速率排序';
        if (topBox) {
          if (!state.devices.length) {
            topBox.innerHTML = `<div class="h3-bh-dom-item"><span class="h3-bh-dom-name">暂无活跃终端流量</span></div>`;
          } else {
            topBox.innerHTML = [...state.devices].sort((a, b) => (b.rate || 0) - (a.rate || 0)).map(d => `
              <div class="h3-bh-dom-item">
                <span class="h3-bh-dom-name" title="${d.name} (${d.ip || ''})">${d.name}</span>
                <div class="h3-bh-dom-meta">
                  <span class="h3-bh-tag">${d.isRemote ? '🏠 回家隧道' : '🖧 局域网'}</span>
                  <span class="h3-bh-cnt">↓${fmt(d.downRate || 0)} · ${d.conn || 0}连</span>
                </div>
              </div>
            `).join('');
          }
        }
      } else if (tab === 'domestic') {
        const domRate = state.domestic.reduce((a, s) => a + (s.downRate || 0), 0);
        const domUp = state.domestic.reduce((a, s) => a + (s.upRate || 0), 0);
        const domConns = state.domestic.reduce((a, s) => a + (s.conn || 0), 0);
        const hList = (GAL.domestic && GAL.domestic.health) || [];
        if (elIcon) elIcon.textContent = '🇨🇳';
        if (elTitle) elTitle.textContent = '国内直连星系 · WAN 宽带直通';
        if (elSub) elSub.textContent = '大陆域名与 CN IP 绕过代理内核，零损耗直走主路由 WAN 出网';
        if (k1L) k1L.textContent = '活跃国内站点';
        if (k1V) { k1V.style.color = '#f472b6'; k1V.textContent = state.domestic.length + ' 个'; }
        if (k1S) k1S.textContent = `并发直连: ${domConns} 条连接`;
        if (k2L) k2L.textContent = '直连下行速率';
        if (k2V) { k2V.style.color = '#34d399'; k2V.textContent = fmt(domRate); }
        if (k2S) k2S.textContent = `直连上行: ${fmt(domUp)}`;
        if (k3L) k3L.textContent = '出网通道';
        if (k3V) { k3V.style.color = '#f8fafc'; k3V.textContent = 'WAN 直连'; }
        if (k3S) k3S.textContent = state.directExitLabel || '宽带直连 (WAN)';
        if (k4L) k4L.textContent = '国内 DNS 解析';
        if (k4V) { k4V.style.color = '#38bdf8'; k4V.textContent = '223.5.5.5'; }
        if (k4S) k4S.textContent = '阿里公共 DNS · 真实大陆 IP';
        if (actBox) actBox.style.display = 'none';
        if (s1Title) s1Title.textContent = '🩺 国内四大核心服务探测延迟';
        if (s1Sub) s1Sub.textContent = '直连健康环';
        if (catsBox) {
          catsBox.innerHTML = hList.map(h => {
            const msTxt = h.ms > 0 ? `${h.ms} ms` : (h.state === 'pending' ? '待测' : '超时');
            const pct = h.ms > 0 ? Math.max(8, Math.min(100, Math.round((1 - Math.min(h.ms, 400) / 450) * 100))) : 10;
            return `
              <div class="h3-bh-cat-row">
                <div class="h3-bh-cat-top"><span>${h.name}</span><span style="color:${h.ms > 0 ? '#34d399' : '#94a3b8'}">${msTxt}</span></div>
                <div class="h3-bh-bar-bg"><div class="h3-bh-bar-fg" style="width:${pct}%;background:linear-gradient(90deg,#ec4899,#34d399)"></div></div>
              </div>
            `;
          }).join('');
        }
        if (s2Title) s2Title.textContent = `🏠 实时国内直连站点 TOP 榜 (${state.domestic.length})`;
        if (s2Sub) s2Sub.textContent = 'Shunt_Domestic_CN';
        if (topBox) {
          if (!state.domestic.length) {
            topBox.innerHTML = `<div class="h3-bh-dom-item"><span class="h3-bh-dom-name">暂无活跃国内直连站点</span></div>`;
          } else {
            topBox.innerHTML = [...state.domestic].sort((a, b) => (b.rate || 0) - (a.rate || 0)).map(s => `
              <div class="h3-bh-dom-item">
                <span class="h3-bh-dom-name" title="${s.domain || s.name}">${s.name || s.domain}</span>
                <div class="h3-bh-dom-meta">
                  <span class="h3-bh-tag">直连 WAN</span>
                  <span class="h3-bh-cnt">↓${fmt(s.downRate || 0)} · ${s.conn || 0}连</span>
                </div>
              </div>
            `).join('');
          }
        }
      } else if (tab === 'foreign') {
        const forRate = state.foreign.reduce((a, s) => a + (s.downRate || 0), 0);
        const forUp = state.foreign.reduce((a, s) => a + (s.upRate || 0), 0);
        const forConns = state.foreign.reduce((a, s) => a + (s.conn || 0), 0);
        const hList = (GAL.foreign && GAL.foreign.health) || [];
        if (elIcon) elIcon.textContent = '🌍';
        if (elTitle) elTitle.textContent = '海外代理星系 · 全球智能分流出口';
        if (elSub) elSub.textContent = '按 AI / YouTube / TikTok / Google / Netflix 分流策略优选专线出站';
        if (k1L) k1L.textContent = '当前主出口节点';
        if (k1V) { k1V.style.color = '#22d3ee'; k1V.textContent = state.exitNode || '自动优选'; }
        if (k1S) k1S.textContent = `节点延迟: ${state.exitDelay > 0 ? state.exitDelay + ' ms' : '正常'} · ${state.proxyOk ? '在线' : '异常'}`;
        if (k2L) k2L.textContent = '代理下行速率';
        if (k2V) { k2V.style.color = '#34d399'; k2V.textContent = fmt(forRate); }
        if (k2S) k2S.textContent = `代理上行: ${fmt(forUp)}`;
        if (k3L) k3L.textContent = '活跃海外站点';
        if (k3V) { k3V.style.color = '#a78bfa'; k3V.textContent = state.foreign.length + ' 个'; }
        if (k3S) k3S.textContent = `并发代理连接: ${forConns} 条`;
        if (k4L) k4L.textContent = '防污染 FakeIP';
        if (k4V) { k4V.style.color = '#fde68a'; k4V.textContent = '198.18.0.0/15'; }
        if (k4S) k4S.textContent = '远程 DoH + FakeIP 零泄露';
        if (actBox) actBox.style.display = 'none';
        if (s1Title) s1Title.textContent = '🚀 国际四大核心服务探测延迟';
        if (s1Sub) s1Sub.textContent = '代理健康环';
        if (catsBox) {
          catsBox.innerHTML = hList.map(h => {
            const msTxt = h.ms > 0 ? `${h.ms} ms` : (h.state === 'pending' ? '待测' : '超时');
            const pct = h.ms > 0 ? Math.max(8, Math.min(100, Math.round((1 - Math.min(h.ms, 1200) / 1300) * 100))) : 10;
            return `
              <div class="h3-bh-cat-row">
                <div class="h3-bh-cat-top"><span>${h.name}</span><span style="color:${h.ms > 0 ? '#22d3ee' : '#94a3b8'}">${msTxt}</span></div>
                <div class="h3-bh-bar-bg"><div class="h3-bh-bar-fg" style="width:${pct}%;background:linear-gradient(90deg,#06b6d4,#8b5cf6)"></div></div>
              </div>
            `;
          }).join('');
        }
        if (s2Title) s2Title.textContent = `🌐 实时海外代理站点 TOP 榜 (${state.foreign.length})`;
        if (s2Sub) s2Sub.textContent = '显示分流组与出口';
        if (topBox) {
          if (!state.foreign.length) {
            topBox.innerHTML = `<div class="h3-bh-dom-item"><span class="h3-bh-dom-name">暂无活跃海外代理站点</span></div>`;
          } else {
            topBox.innerHTML = [...state.foreign].sort((a, b) => (b.rate || 0) - (a.rate || 0)).map(s => `
              <div class="h3-bh-dom-item">
                <span class="h3-bh-dom-name" title="${s.domain} (${s.exitNode || state.exitNode || ''})">${s.domain}</span>
                <div class="h3-bh-dom-meta">
                  <span class="h3-bh-tag">${(s.group || 'Shunt').replace(/^Shunt_/, '')}</span>
                  <span class="h3-bh-cnt">↓${fmt(s.downRate || 0)} · ${s.conn || 0}连</span>
                </div>
              </div>
            `).join('');
          }
        }
      }
    }

    function openGalaxyDrawer(tabKey) {
      if (tabKey && ['lan', 'domestic', 'foreign', 'blackhole'].includes(tabKey)) {
        state.drawerTab = tabKey;
      }
      const dr = document.getElementById('h3-bh-drawer');
      if (!dr) return;
      dr.classList.add('open');
      renderGalaxyDrawer();
    }

    function toggleBlackHoleDrawer(forceOpen) {
      const dr = document.getElementById('h3-bh-drawer');
      if (!dr) return;
      const next = typeof forceOpen === 'boolean' ? forceOpen : !dr.classList.contains('open');
      dr.classList.toggle('open', next);
      if (next) renderGalaxyDrawer();
    }

    window.__h3StarGlow = () => {
      const out = {};
      Object.keys(GAL).forEach(k => {
        const g = GAL[k];
        const gl = g && g.star && g.star.userData && g.star.userData.glow;
        out[k] = gl ? { visible: gl.visible, sx: +gl.scale.x.toFixed(2), op: +gl.material.opacity.toFixed(2),
          col: '#' + gl.material.color.getHexString(), posY: +gl.position.y.toFixed(2) } : null;
      });
      return out;
    };
    window.__h3Debug = () => ({
      auto: state.autoOrbit,
      domA: (state.domestic[0] || {}).orbitA || 0,
      devA: (state.devices[0] || {}).orbitA || 0,
      mem: state.memMib || LIVE.mem, liveOn: LIVE.on, down: state.totalDown, up: state.totalUp,
      dev: state.devices.length, dom: state.domestic.length, fore: state.foreign.length,
      bhBlocked: state.bh.blocked_queries,
    });
    window.__h3SetActive = function (v) {
      state.active = !!v;
      if (state.active) { clock.getDelta(); }
    };
    window.__h3SetLive = function (d) {
      if (!d) return;
      if (typeof d.conn === 'number') state.totalConn = d.conn | 0;
      if (typeof d.down === 'number') state.totalDown = d.down;
      if (typeof d.up === 'number') state.totalUp = d.up;
      if (typeof d.mem === 'number' && d.mem > 0) state.memMib = d.mem;
      const elConn = document.getElementById('h3-t-conn');
      const elDown = document.getElementById('h3-t-down');
      const elUp = document.getElementById('h3-t-up');
      if (elConn) elConn.textContent = state.totalConn;
      if (elDown) elDown.textContent = fmt(state.totalDown);
      if (elUp) elUp.textContent = fmt(state.totalUp);
    };

    function orbitSpeed(r, dir) {
      return dir * 0.20 / Math.pow(r, 1.5);
    }
    function hashStr(str) {
      let h = 0;
      for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0;
      return Math.abs(h);
    }
    function freeSlot(arr, slotCount) {
      const used = new Set(arr.map(o => o.slot));
      for (let i = 0; i < slotCount; i++) if (!used.has(i)) return i;
      return -1;
    }
    function createSatellite(kind, row) {
      const arr = kind === 'device' ? state.devices
        : (kind === 'domestic' ? state.domestic : state.foreign);
      const parent = kind === 'device' ? 'lan' : kind;
      const slotCount = kind === 'device' ? DEVICE_RADII.length : SITE_RADII.length;
      const slot = freeSlot(arr, slotCount);
      if (slot < 0) return null;
      const r = kind === 'device' ? DEVICE_RADII[slot] : SITE_RADII[slot];
      const key = row.ip || row.domain || ('x' + slot);
      const obj = {
        kind: kind === 'device' ? 'device' : 'site',
        side: kind === 'device' ? '' : kind,
        id: key, ip: row.ip, domain: row.domain,
        name: row.name || key, short: compactDisplayLabel(row.name || key),
        slot, orbitR: r,
        orbitA: kind === 'device'
          ? slot * (Math.PI * 2 / slotCount) + 0.42
          : -Math.PI / 2 + Math.PI / 10 + slot * (Math.PI * 2 / slotCount),
        orbitW: orbitSpeed(r, slot % 2 ? -1 : 1),
        yOff: (slot % 2 ? 0.09 : -0.06),
        color: satColor(hashStr(key)),
        rate: 0, downRate: 0, upRate: 0, conn: 0, state: 'ok', isRemote: !!row.is_remote, link: null,
      };
      obj.pos = orbitWorld(parent, obj);
      arr.push(obj);
      ensureSatellite(obj);
      return obj;
    }
    function applyGalaxyRows(kind, rows) {
      const arr = kind === 'device' ? state.devices
        : (kind === 'domestic' ? state.domestic : state.foreign);
      const seen = new Set();
      (rows || []).forEach(row => {
        const key = row.ip || row.domain;
        if (!key) return;
        seen.add(key);
        let o = arr.find(x => (x.ip || x.domain) === key);
        if (!o) o = createSatellite(kind, row);
        if (!o) return;
        o.downRate = Number(row.down_rate) || 0;
        o.upRate = Number(row.up_rate) || 0;
        o.rate = o.downRate + o.upRate;
        o.conn = Number(row.conns) || 0;
        o.state = row.state || 'ok';
        o.group = row.group || o.group;
        o.exitNode = row.exit_node || o.exitNode;
        o.isRemote = !!row.is_remote;
        if (row.name) { o.name = row.name; o.short = compactDisplayLabel(row.name); }
      });
      for (let i = arr.length - 1; i >= 0; i--) {
        const o = arr[i];
        if (!seen.has(o.ip || o.domain)) removeSatellite(o);
      }
      // 默认每个星系最多只展示前 3 个最高速率的卫星标签（悬停或开启「显示全部标签」时才展开其余标签），让画面干净清爽！
      const topLimit = kind === 'device' ? 3 : 3;
      [...arr].sort((a, b) => (b.rate || 0) - (a.rate || 0)).forEach((o, i) => { o.top = i < topLimit; });
    }

    window.__h3SetGalaxy = function (snap) {
      if (!snap || !snap.ok) return;
      const k = snap.kernel || {};
      state.totalConn = Number(k.conn) || 0;
      state.totalDown = Number(k.in_rate) || 0;
      state.totalUp = Number(k.out_rate) || 0;
      state.memMib = Number(k.mem_mib) || 0;
      state.uptime = k.kernel_uptime || k.uptime || '';
      state.sysUptime = k.sys_uptime || '';
      const px = (snap.exits && snap.exits.proxy) || {};
      const dx = (snap.exits && snap.exits.direct) || {};
      state.proxyOk = !!px.ok;
      state.exitNode = px.node || '';
      state.exitDelay = Number(px.delay_ms) || 0;
      state.exitState = px.state || '';
      state.directExitLabel = dx.node || dx.label || '宽带直连 (WAN)';
      state.particleCount = (snap.counts && Number(snap.counts.particles)) || (Array.isArray(snap.particles) ? snap.particles.length : 4);
      state.particleTier = snap.particle_tier || (snap.counts && snap.counts.tier) || TIER_NAME[speedTier(state.totalDown + state.totalUp)];
      if (snap.blackhole && typeof snap.blackhole === 'object') {
        state.bh = Object.assign({}, state.bh, snap.blackhole);
      }
      const elConn = document.getElementById('h3-t-conn');
      const elDown = document.getElementById('h3-t-down');
      const elUp = document.getElementById('h3-t-up');
      const elTier = document.getElementById('h3-t-tier');
      if (elConn) elConn.textContent = state.totalConn;
      if (elDown) elDown.textContent = fmt(state.totalDown);
      if (elUp) elUp.textContent = fmt(state.totalUp);
      if (elTier) elTier.textContent = `${state.particleCount}颗 · ${state.particleTier}`;
      applyGalaxyRows('device', snap.lan);
      applyGalaxyRows('domestic', snap.domestic);
      applyGalaxyRows('foreign', snap.foreign);
      const dr = document.getElementById('h3-bh-drawer');
      if (dr && dr.classList.contains('open')) {
        renderGalaxyDrawer();
      } else {
        const elTopBh = document.getElementById('h3-t-bh');
        if (elTopBh && state.bh) {
          elTopBh.textContent = `${state.bh.blocked_queries || 0} 次 · ${(state.bh.active_rules || 50000).toLocaleString()} 规则`;
        }
      }
    };

    window.__h3SetHealth = function (list) {
      if (!Array.isArray(list)) return;
      ['domestic', 'foreign'].forEach(k => {
        const g = GAL[k];
        if (!g) return;
        const isProxySide = (k === 'foreign');
        const okLim = isProxySide ? 1500 : 400;
        const susLim = isProxySide ? 3500 : 2000;
        g.health.forEach(h => {
          const t = list.find(x => x && x.name === h.name);
          if (!t) return;
          h.ms = (typeof t.ms === 'number') ? t.ms : -1;
          h.state = t.state || (h.ms < 0 ? 'dead' : (h.ms < okLim ? 'ok' : (h.ms < susLim ? 'suspect' : 'dead')));
        });
      });
      const dr = document.getElementById('h3-bh-drawer');
      if (dr && dr.classList.contains('open')) renderGalaxyDrawer();
    };

    function orbitWorld(parentKey, o) {
      const a = o.orbitA, r = o.orbitR;
      return new THREE.Vector3(
        Math.cos(a) * r,
        Math.sin(a) * r * 0.055 + (o.yOff || 0),
        Math.sin(a) * r
      ).add(GALAXY[parentKey].center);
    }
    function setLinkEnds(L, a, b) {
      if (L.a.distanceToSquared(a) < 1e-6 && L.b.distanceToSquared(b) < 1e-6) return;
      L.a.copy(a); L.b.copy(b);
      const { curve, pts } = computeArcPoints(a, b, L.isTrunk, L.segs);
      L.curve = curve;
      L.line.geometry.setFromPoints(pts);
    }

    const _sharedSatGeo = new THREE.SphereGeometry(0.245, 22, 22);
    function ensureSatellite(obj) {
      const parent = obj.kind === 'device' ? 'lan' : obj.side;
      const g = GAL[parent].group;
      const selfColor = obj.color || satColor(0);
      const stateColor = STATE_COLOR[obj.state] || C.ok;
      const mesh = new THREE.Mesh(
        _sharedSatGeo,
        new THREE.MeshBasicMaterial({ color: selfColor })
      );
      mesh.position.copy(obj.pos).sub(GALAXY[parent].center);
      mesh.userData = { kind: obj.kind === 'device' ? 'device' : 'site', ref: obj, baseR: 0.245 };
      g.add(mesh);
      pickables.push(mesh);
      obj.mesh = mesh;
      const glow = makeGlow(selfColor, 1.08, 0.52);
      glow.position.copy(mesh.position);
      g.add(glow);
      obj.glow = glow;
      const borderCol = parent === 'domestic' ? 'rgba(244,114,182,0.48)' : (parent === 'foreign' ? 'rgba(34,211,238,0.48)' : 'rgba(167,139,250,0.48)');
      const lab = makeLabel(obj.kind === 'device' ? (obj.short || obj.name) : obj.domain, '#f8fafc', { borderColor: borderCol });
      const dir = new THREE.Vector3(mesh.position.x, 0, mesh.position.z);
      if (dir.lengthSq() < 1e-4) dir.set(0, 0, 1);
      dir.normalize();
      lab.position.copy(mesh.position).add(dir.multiplyScalar(1.18)).add(new THREE.Vector3(0, (obj.slot % 2 ? 0.26 : -0.04), 0));
      lab.visible = false;
      lab.userData = Object.assign(lab.userData || {}, { prio: obj.kind === 'device' ? 30 : 50, ref: obj });
      g.add(lab);
      obj.label = lab;
      allLabels.push(lab);
      const orbPts = [];
      for (let i = 0; i < 96; i++) {
        const a = i / 96 * Math.PI * 2;
        orbPts.push(new THREE.Vector3(Math.cos(a) * obj.orbitR, Math.sin(a) * obj.orbitR * 0.055 + (obj.yOff || 0), Math.sin(a) * obj.orbitR));
      }
      const orbRing = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(orbPts),
        new THREE.LineBasicMaterial({ color: GALAXY[parent].color, transparent: true, opacity: 0.09, depthWrite: false })
      );
      orbRing.frustumCulled = false;
      g.add(orbRing);
      obj.orbitRing = orbRing;
      const from = obj.kind === 'device' ? GALAXY.lan.center : GALAXY[parent].center;
      obj.link = makeLink(from, obj.pos, stateColor, {
        opacity: 0.48, dotR: 0.052, kind: obj.kind, owner: obj
      });
      obj._lastState = obj.state;
      return obj;
    }

    function removeSatellite(obj) {
      const parent = obj.kind === 'device' ? 'lan' : obj.side;
      const g = GAL[parent].group;
      if (obj.mesh) {
        g.remove(obj.mesh);
        if (obj.mesh.material) obj.mesh.material.dispose();
        const i = pickables.indexOf(obj.mesh); if (i >= 0) pickables.splice(i, 1);
      }
      if (obj.glow) {
        g.remove(obj.glow);
        if (obj.glow.material) obj.glow.material.dispose();
      }
      if (obj.orbitRing) {
        g.remove(obj.orbitRing);
        obj.orbitRing.geometry.dispose();
        obj.orbitRing.material.dispose();
      }
      if (obj.label) {
        g.remove(obj.label);
        const i = allLabels.indexOf(obj.label); if (i >= 0) allLabels.splice(i, 1);
      }
      if (obj.link) {
        scene.remove(obj.link.line);
        obj.link.line.geometry.dispose();
        obj.link.mat.dispose();
        obj.link.parts.forEach(p => {
          scene.remove(p.mesh);
          if (p.mesh.material) p.mesh.material.dispose();
          if (p.halo && p.halo.material) p.halo.material.dispose();
        });
        const i = links.indexOf(obj.link); if (i >= 0) links.splice(i, 1);
      }
      const arr = obj.kind === 'device' ? state.devices : (obj.side === 'domestic' ? state.domestic : state.foreign);
      const idx = arr.indexOf(obj); if (idx >= 0) arr.splice(idx, 1);
    }

    /* ---------------- 交互、相机聚焦与手势 ---------------- */
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2(-10, -10);
    let pointerXY = { x: 0, y: 0 };
    const hud = document.getElementById('h3-hud');
    let dragging = false, lastX = 0, lastY = 0, moved = 0;

    canvas.addEventListener('pointerdown', e => {
      dragging = true; lastX = e.clientX; lastY = e.clientY; moved = 0;
    });
    window.addEventListener('pointerup', () => {
      if (!dragging) return;
      dragging = false;
      if (moved < 6) handleClick();
    });
    canvas.addEventListener('pointerleave', () => {
      if (!state.locked && hud) hud.classList.remove('show');
      state.hovered = null;
    });
    canvas.addEventListener('pointermove', e => {
      const _rc = canvas.getBoundingClientRect();
      pointerXY = { x: e.clientX - _rc.left, y: e.clientY - _rc.top };
      pointer.x = ((e.clientX - _rc.left) / Math.max(1, W)) * 2 - 1;
      pointer.y = -((e.clientY - _rc.top) / Math.max(1, H)) * 2 + 1;
      if (dragging) {
        const dx = e.clientX - lastX, dy = e.clientY - lastY;
        moved += Math.abs(dx) + Math.abs(dy);
        camRig.yaw -= dx * 0.0052;
        camRig.pitch = Math.max(-0.88, Math.min(0.94, camRig.pitch + dy * 0.0042));
        lastX = e.clientX; lastY = e.clientY;
        applyCam();
      }
    });
    canvas.addEventListener('wheel', e => {
      e.preventDefault();
      camRig.dist = Math.max(10.5, Math.min(52, camRig.dist + e.deltaY * 0.018));
      applyCam();
    }, { passive: false });
    canvas.addEventListener('dblclick', () => {
      const hit = pickAt();
      if (hit) flyTo(hit.point, 12.0);
      else focusGalaxyCamera('all');
    });
    window.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        state.locked = null;
        toggleBlackHoleDrawer(false);
        focusGalaxyCamera('all');
      }
    });

    function pickAt() {
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(pickables, false);
      return hits.length ? { obj: hits[0].object, point: hits[0].object.getWorldPosition(new THREE.Vector3()) } : null;
    }

    let fly = null;
    function flyTo(target, customDist) {
      const to = target
        ? { target: target.clone(), dist: customDist || 12.4 }
        : { target: new THREE.Vector3(-0.2, 0.35, -0.6), dist: 23.4 };
      fly = { t: 0, fromT: camRig.target.clone(), toT: to.target, fromD: camRig.dist, toD: to.dist };
    }

    function focusGalaxyCamera(key) {
      const dockBtns = document.querySelectorAll('#h3-nav-dock .h3-nav-btn');
      dockBtns.forEach(b => b.classList.toggle('active', b.getAttribute('data-focus') === key));
      if (!key || key === 'all') {
        state.locked = null;
        flyTo(null);
        return;
      }
      const g = GALAXY[key];
      if (!g) return;
      flyTo(g.center, key === 'blackhole' ? 11.4 : 12.6);
      if (GAL[key] && GAL[key].star) {
        state.locked = GAL[key].star.userData;
      }
    }

    function handleClick() {
      const hit = pickAt();
      if (!hit) { state.locked = null; return; }
      const ud = hit.obj.userData;
      if (ud.kind === 'star' && ud.galaxy) {
        state.locked = ud;
        openGalaxyDrawer(ud.galaxy);
        focusGalaxyCamera(ud.galaxy);
        return;
      }
      if (ud.kind === 'device' || ud.kind === 'site') {
        state.locked = (state.locked === ud) ? null : ud;
      }
    }

    /* ---------------- HUD 真实数据卡片 ---------------- */
    function hudData(ud) {
      if (!ud) return null;
      if (ud.kind === 'star') {
        const key = ud.galaxy;
        if (key === 'blackhole') {
          const bh = state.bh || {};
          const top0 = (bh.top_blocked && bh.top_blocked[0]) ? `${bh.top_blocked[0].domain} (${bh.top_blocked[0].count}次)` : 'cpro.baidu.com';
          return {
            cat: 'GRAVITY BLACK HOLE · ADGUARD ENGINE',
            state: bh.enabled !== false ? '● 引力护盾激活' : '● 已暂停',
            title: '🕳️ 深空引力黑洞 · 净网拦截中枢',
            sub: '点击展开黑洞拦截详情抽屉与 TOP 榜',
            rows: [
              ['已吞噬请求', (bh.blocked_queries || 0) + ' 次'],
              ['净网拦截率', (bh.block_rate_pct || 0) + ' %'],
              ['生效黑名单', (bh.active_rules || 50000).toLocaleString() + ' 条'],
              ['DNS 层前置阻断', (bh.dns_layer_blocks || 0) + ' 次'],
              ['路由层 REJECT', (bh.route_reject_blocks || 0) + ' 次'],
              ['榜首拦截域名', top0],
            ]
          };
        }
        if (key === 'lan') {
          return {
            cat: 'KERNEL', state: state.proxyOk ? '● 运行中' : '● 出口异常', title: 'sing-box 内核中枢',
            sub: '点击展开内核与在线终端详情单',
            rows: [['总连接', state.totalConn + ' 条'], ['下行', fmt(state.totalDown)],
                   ['上行', fmt(state.totalUp)],
                   ['在线终端', state.devices.length + ' 台'],
                   ['内核内存 (RSS)', (Number(state.memMib) || 0).toFixed(1) + ' MiB'],
                   ['内核运行', state.uptime || '—'],
                   ['当前节点', state.exitNode || '—'],
                   ['节点延迟', state.exitDelay > 0 ? state.exitDelay + ' ms' : '—']]
          };
        }
        const isDom = key === 'domestic';
        const g = GAL[key];
        const list = (g.health || []).map(x => [x.name, x.ms < 0 ? '超时' : x.ms + ' ms']);
        return {
          cat: isDom ? 'DIRECT EXIT' : 'PROXY EXIT',
          state: isDom ? '● 在线' : (state.proxyOk ? '● 在线' : '● 异常'),
          title: isDom ? '国内直连星系 (WAN)' : '海外代理星系',
          sub: isDom ? '点击展开国内直连站点详情单' : '点击展开海外代理站点与分流详情单',
          rows: isDom
            ? [['当前通道', state.directExitLabel || '宽带直连 (WAN)'], ['活跃站点', state.domestic.length + ' 个'], ...list]
            : [['当前节点', state.exitNode || '—'],
               ['出口延迟', state.exitDelay > 0 ? state.exitDelay + ' ms' : '—'],
               ['活跃站点', state.foreign.length + ' 个'],
               ...list]
        };
      }
      if (ud.kind === 'device') {
        const o = ud.ref;
        return {
          cat: o.isRemote ? 'HOMELINK REMOTE' : 'LAN DEVICE', state: '● 活跃', title: o.name,
          sub: o.isRemote ? `${o.ip || '—'} · 🏠 回家隧道接入` : `${o.ip || '—'} · 局域网终端`,
          rows: [['IP 地址', o.ip || '—'],
                 ['接入类型', o.isRemote ? '🏠 回家节点远程客户端' : '🖧 局域网内网设备'],
                 ['下行速率', fmt(o.downRate || 0)], ['上行速率', fmt(o.upRate || 0)],
                 ['并发连接', (o.conn || 0) + ' 条'], ['状态', o.state || 'ok']]
        };
      }
      if (ud.kind === 'site') {
        const o = ud.ref;
        return {
          cat: o.side === 'domestic' ? 'DOMESTIC SITE' : 'FOREIGN SITE',
          state: o.state === 'ok' ? '● 活跃' : '● 异常', title: o.domain,
          sub: o.side === 'domestic' ? '经直连出口 (WAN)' : `经代理出口 (${o.exitNode || state.exitNode || 'Proxy'})`,
          rows: [['下行速率', fmt(o.downRate != null ? o.downRate : o.rate)],
                 ['上行速率', fmt(o.upRate != null ? o.upRate : 0)],
                 ['并发连接', (o.conn || 0) + ' 条'],
                 ['命中分流组', o.group || (o.side === 'domestic' ? 'Shunt_Domestic_CN' : 'Shunt_Out')]]
        };
      }
      return null;
    }

    /* ---------------- 3D 标签屏幕去重叠与远近自适应缩放 ---------------- */
    const _v3 = new THREE.Vector3();
    function declutterLabels() {
      const placed = [];
      const cand = [];
      const zoomMul = Math.max(0.76, Math.min(1.06, 23.4 / Math.max(12, camRig.dist)));
      allLabels.forEach(l => {
        if (!l.visible) return;
        if (l.userData && l.userData.baseW) {
          l.scale.set(l.userData.baseW * zoomMul, l.userData.baseH * zoomMul, 1);
        }
        l.getWorldPosition(_v3);
        const p = _v3.clone().project(camera);
        if (p.z > 1) { l.visible = false; return; }
        const ref = l.userData && l.userData.ref;
        const isFocus = ref && ((state.hovered && state.hovered.ref === ref) || (state.locked && state.locked.ref === ref));
        cand.push({
          l,
          x: (p.x * 0.5 + 0.5) * W,
          y: (-p.y * 0.5 + 0.5) * H,
          prio: isFocus ? 120 : ((l.userData && l.userData.prio) || 10) + (ref && ref.top ? 25 : 0),
        });
      });
      const stars = [];
      ['lan', 'domestic', 'foreign', 'blackhole'].forEach(k => {
        const g = GAL[k]; if (!g) return;
        const v = g.star.getWorldPosition(new THREE.Vector3()).project(camera);
        if (v.z > 1) return;
        stars.push({ x: (v.x * 0.5 + 0.5) * W, y: (-v.y * 0.5 + 0.5) * H });
      });
      cand.sort((a, b) => b.prio - a.prio);
      const chipRects = [];
      Object.values(healthRects).forEach(arr => (arr || []).forEach(r => chipRects.push(r)));
      cand.forEach(c => {
        const w = 132 * zoomMul, h = 26 * zoomMul;
        const clash = placed.some(q => Math.abs(q.x - c.x) < w && Math.abs(q.y - c.y) < h);
        const nearStar = stars.some(st => Math.abs(st.x - c.x) < 76 && Math.abs(st.y - c.y) < 44)
          || chipRects.some(r => Math.abs(r.x - c.x) < 104 && Math.abs(r.y - c.y) < 24);
        if ((clash || nearStar) && c.prio < 100) {
          c.l.visible = false;
        } else {
          placed.push(c);
          c.l.material.opacity = c.prio >= 100 ? 1.0 : 0.90;
        }
      });
    }

    function updateHUD() {
      const hit = pickAt();
      const hoverUd = hit ? hit.obj.userData : null;
      state.hovered = hoverUd;
      canvas.style.cursor = hoverUd ? 'pointer' : (dragging ? 'grabbing' : 'grab');
      const activeUd = hoverUd || state.locked;
      if (!activeUd) { hud.classList.remove('show'); return; }
      const d = hudData(activeUd);
      if (!d) { hud.classList.remove('show'); return; }
      document.getElementById('h3-hud-cat').textContent = d.cat;
      document.getElementById('h3-hud-state').textContent = d.state;
      document.getElementById('h3-hud-title').textContent = d.title;
      document.getElementById('h3-hud-sub').textContent = d.sub;
      document.getElementById('h3-hud-rows').innerHTML =
        d.rows.map(([k, v]) => `<span>${k}</span><b>${v}</b>`).join('');
      hud.classList.add('show');
      const hudW = 280, hudH = 210;
      let hx = pointerXY.x + 18;
      let hy = pointerXY.y + 18;
      if (hx + hudW > W - 16) hx = Math.max(16, pointerXY.x - hudW - 18);
      if (hy + hudH > H - 96) hy = Math.max(60, H - 96 - hudH);
      hud.style.left = Math.round(hx) + 'px';
      hud.style.top = Math.round(hy) + 'px';
    }

    function notify(msg, level = 'info') {
      const box = document.getElementById('h3-toasts');
      if (!box) return;
      const el = document.createElement('div');
      el.className = 'h3-toast' + (level === 'warn' ? ' warn' : level === 'crit' ? ' crit' : '');
      el.innerHTML = `<div class="scan"></div><div class="t">星际指令 · INCOMING</div><div class="m"></div>`;
      box.appendChild(el);
      const m = el.querySelector('.m');
      let i = 0;
      const timer = setInterval(() => {
        m.textContent = msg.slice(0, ++i);
        if (i >= msg.length) clearInterval(timer);
      }, 16);
      setTimeout(() => { el.style.transition = 'opacity .4s'; el.style.opacity = 0;
        setTimeout(() => el.remove(), 420); }, 5200);
      while (box.children.length > 3) box.firstChild.remove();
    }
    _notifyFn = notify;

    let simTimer = 0;
    function simulate(dt) {
      simTimer += dt;
      if (simTimer < 0.8) return;
      simTimer = 0;
      document.getElementById('h3-t-conn').textContent = state.totalConn;
      document.getElementById('h3-t-down').textContent = fmt(state.totalDown);
      document.getElementById('h3-t-up').textContent = fmt(state.totalUp);
      const pCnt = state.particleCount || (state.totalConn > 0 ? Math.min(24, state.totalConn * 2) : 4);
      const tName = state.particleTier || TIER_NAME[speedTier(state.totalDown + state.totalUp)];
      document.getElementById('h3-t-tier').textContent = `${pCnt}颗 · ${tName}`;
    }

    /* ---------------- 渲染主循环 ---------------- */
    const clock = new THREE.Clock();
    let orbitT = 0;
    function animate() {
      requestAnimationFrame(animate);
      if (!state.active || document.hidden) { clock.getDelta(); return; }
      const dt = Math.min(clock.getDelta(), 0.05);
      const t = clock.elapsedTime;
      simulate(dt);
      if (window.__nebulaDome) window.__nebulaDome.rotation.y += dt * 0.005;
      nebulaLayers.forEach((m, i) => {
        m.rotation.z += dt * m.userData.spin;
        m.position.x = Math.sin(t * 0.05 + i) * 3.6;
        m.position.y = Math.cos(t * 0.04 + i) * 2.4;
      });
      if (starLayers[0]) starLayers[0].rotation.y += dt * 0.0025;
      if (starLayers[1]) starLayers[1].rotation.y -= dt * 0.004;

      ['lan', 'domestic', 'foreign'].forEach(k => {
        const g = GAL[k];
        if (!g) return;
        const hz = k === 'lan' ? 0.82 : 0.48;
        const p = 1 + Math.sin(t * Math.PI * 2 * hz) * 0.045;
        g.star.scale.setScalar(p);
        g.star.rotation.y += dt * (k === 'lan' ? 0.26 : 0.18);
        if (g.star.userData.gyro1) g.star.userData.gyro1.rotation.z += dt * 0.42;
        if (g.star.userData.gyro2) g.star.userData.gyro2.rotation.z -= dt * 0.31;
        const ar = g.star.userData.alertRing;
        if (ar) {
          const bad = (k !== 'domestic') && !state.proxyOk;
          ar.visible = bad;
          if (bad) {
            ar.rotation.z += dt * 1.1;
            ar.scale.setScalar(1 + Math.sin(t * 6) * 0.06);
            ar.material.opacity = 0.55 + Math.sin(t * 6) * 0.3;
          }
        }
        if (g.star.userData.glow) g.star.userData.glow.scale.setScalar(4.2 * p);
        if (g.star.userData.halo) g.star.userData.halo.scale.setScalar(p);
        g.ring.rotation.y += dt * (k === 'lan' ? 0.08 : 0.05);
        if (g.dust) g.dust.rotation.y -= dt * g.dust.userData.spin;
      });

      // 驱动深空引力黑洞旋转与广告碎片螺旋坍缩动画
      if (GAL.blackhole) {
        const bhG = GAL.blackhole;
        const bhStar = bhG.star;
        if (bhStar.userData.accDisk) {
          bhStar.userData.accDisk.rotation.z -= dt * 0.62;
        }
        if (bhStar.userData.gyro1) {
          bhStar.userData.gyro1.rotation.z += dt * 0.85;
        }
        if (bhStar.userData.gyro2) {
          bhStar.userData.gyro2.rotation.z -= dt * 0.42;
        }
        if (bhStar.userData.glow) {
          const pulse = 1 + Math.sin(t * 3.0) * 0.06;
          bhStar.userData.glow.scale.setScalar(5.4 * pulse);
        }
        bhG.ring.rotation.z -= dt * 0.16;
        if (bhG.debrisPts && bhG.debrisMeta) {
          const posAttr = bhG.debrisPts.geometry.attributes.position;
          const arr = posAttr.array;
          for (let i = 0; i < bhG.debrisMeta.length; i++) {
            const m = bhG.debrisMeta[i];
            m.a -= dt * (2.0 / Math.max(0.85, m.r)) * m.speed;
            m.r -= dt * 0.55 * m.speed;
            if (m.r < 1.16) {
              m.r = 4.15 + (i % 5) * 0.18;
            }
            arr[i * 3] = Math.cos(m.a) * m.r;
            arr[i * 3 + 1] = Math.sin(m.a) * m.r;
            arr[i * 3 + 2] = m.zOff * ((m.r - 1.1) / 3.2);
          }
          posAttr.needsUpdate = true;
        }
      }

      const domRate = state.domestic.reduce((a, s) => a + s.rate, 0) || (state.totalDown * 0.35);
      const forRate = state.foreign.reduce((a, s) => a + s.rate, 0) || (state.proxyOk ? state.totalDown * 0.65 : 0);
      trunkDomestic.rate = domRate;
      trunkForeign.rate = forRate;
      trunkForeign.mat.color.setHex(state.proxyOk ? C.proxy : C.dead);
      trunkBlackHole.rate = (state.bh && state.bh.enabled !== false) ? (250 * 1024) : 0;

      const _lp = new THREE.Vector3();
      const stepSat = (o, parentKey) => {
        if (state.autoOrbit) o.orbitA += o.orbitW * dt;
        const world = orbitWorld(parentKey, o);
        o.pos.copy(world);
        if (o.mesh) {
          o.mesh.position.copy(world).sub(GALAXY[parentKey].center);
          if (o.glow) o.glow.position.copy(o.mesh.position);
          if (o.label) {
            _lp.set(o.mesh.position.x, 0, o.mesh.position.z);
            if (_lp.lengthSq() < 1e-5) _lp.set(0, 0, 1);
            _lp.normalize().multiplyScalar(1.06);
            o.label.position.set(
              o.mesh.position.x + _lp.x,
              o.mesh.position.y + 0.26,
              o.mesh.position.z + _lp.z
            );
          }
        }
        if (o.link) setLinkEnds(o.link, GALAXY[parentKey].center, world);
      };
      state.devices.forEach(d => stepSat(d, 'lan'));
      state.domestic.forEach(s => stepSat(s, 'domestic'));
      state.foreign.forEach(s => stepSat(s, 'foreign'));
      state.devices.forEach(d => { if (d.link) d.link.rate = d.rate; });
      [...state.domestic, ...state.foreign].forEach(s => { if (s.link) s.link.rate = s.rate; });

      const lockedRef = state.locked ? state.locked.ref : null;
      const lockedGal = (state.locked && state.locked.kind === 'star') ? state.locked.galaxy : null;
      links.forEach(L => {
        const rate = L.rate || 0;
        const tier = speedTier(rate);
        const speed = TIER_SPEED[tier];
        const n = TIER_COUNT[tier];
        const isLinkHighlighted = !state.locked
          || (lockedRef && L.owner === lockedRef)
          || (lockedGal && (L.kind === 'trunk' || (lockedGal === 'blackhole' && L.kind === 'blackhole_pull') || (L.owner && (L.owner.side === lockedGal || (lockedGal === 'lan' && L.owner.kind === 'device')))));
        L.parts.forEach((p, i) => {
          p.mesh.visible = (i < n) && isLinkHighlighted;
          if (!p.mesh.visible) return;
          p.t += speed * dt;
          if (p.t > 1) p.t -= 1;
          if (L.curve) {
            L.curve.getPoint(p.t, p.mesh.position);
          } else {
            p.mesh.position.lerpVectors(L.a, L.b, p.t);
          }
          const env = Math.sin(p.t * Math.PI);
          p.mesh.material.opacity = 0.94 * env;
          if (p.halo) p.halo.material.opacity = 0.54 * env;
        });
        const baseOp = rate > 0 ? 0.50 : 0.20;
        L.mat.opacity = state.locked ? (isLinkHighlighted ? 0.85 : 0.10) : baseOp;
      });

      const hoveredUd = state.hovered;
      pickables.forEach(m => {
        const ud = m.userData;
        const isHover = hoveredUd === ud;
        const isLock = state.locked === ud;
        const o = ud.ref;
        const rateScale = o ? Math.max(0.88, Math.min(1.50, 0.90 + Math.log10(1 + (o.rate || 0) / 8192) * 0.20)) : 1.0;
        const hoverMul = (isHover || isLock) ? 1.26 : 1.0;
        const target = rateScale * hoverMul;
        if (ud.kind !== 'star') {
          m.scale.lerp(new THREE.Vector3(target, target, target), 0.18);
        }
        if (o) {
          if (o._lastState !== o.state && o.link) {
            o._lastState = o.state;
            const sc = STATE_COLOR[o.state] || C.ok;
            o.link.mat.color.setHex(sc);
            o.link.parts.forEach(p => {
              p.mesh.material.color.setHex(sc);
              if (p.halo) p.halo.material.color.setHex(sc);
            });
          }
          const deg = o.side === 'foreign' && !state.proxyOk;
          const dimmedByLock = state.locked && !isLock && !(lockedGal && (o.side === lockedGal || (lockedGal === 'lan' && o.kind === 'device')));
          m.material.color.setHex(deg ? 0x64748b : (o.color || 0x8b5cf6));
          if (o.glow) {
            o.glow.material.color.setHex(deg ? 0x64748b : (o.color || 0x8b5cf6));
            o.glow.material.opacity = (isHover || isLock) ? 0.85 : (dimmedByLock ? 0.16 : (deg ? 0.28 : 0.50));
            o.glow.scale.setScalar(1.08 * rateScale * hoverMul);
          }
          if (o.label) {
            // 默认只展示每个星系前 3 个核心标签；悬停、锁定或打开「显示全部标签」时展示其余标签
            const topN = o.top === true;
            o.label.visible = topN || isHover || isLock || state.showAll;
          }
        }
      });
      allLabels.forEach(l => { l.material.opacity = 0.90; });
      if (state.autoOrbit) {
        orbitT += dt;
        camRig.yaw = Math.sin(orbitT * 0.10) * 0.24;
        applyCam();
      }
      if (fly) {
        fly.t = Math.min(1, fly.t + dt * 1.8);
        const e = 1 - Math.pow(1 - fly.t, 3);
        camRig.target.lerpVectors(fly.fromT, fly.toT, e);
        camRig.dist = fly.fromD + (fly.toD - fly.fromD) * e;
        applyCam();
        if (fly.t >= 1) fly = null;
      }
      updateHUD();
      updateHealthLayer();
      declutterLabels();
      renderer.render(scene, camera);
    }

    /* ---------------- 绑定顶部导航与四星系详情抽屉事件 ---------------- */
    const btnOrbit = document.getElementById('h3-btn-orbit');
    const btnAll = document.getElementById('h3-btn-all');
    const btnBh = document.getElementById('h3-btn-bh');
    const topBh = document.getElementById('h3-t-bh');
    const closeBh = document.getElementById('h3-bhd-close');
    const testBhBtn = document.getElementById('h3-bhd-test-btn');
    const cfgBhBtn = document.getElementById('h3-bhd-cfg-btn');

    if (btnOrbit) btnOrbit.onclick = () => { state.autoOrbit = !state.autoOrbit; btnOrbit.classList.toggle('on', state.autoOrbit); };
    if (btnAll) btnAll.onclick = () => { state.showAll = !state.showAll; btnAll.classList.toggle('on', state.showAll); };
    if (btnBh) btnBh.onclick = () => { toggleBlackHoleDrawer(); };
    if (topBh) topBh.onclick = () => { openGalaxyDrawer('blackhole'); focusGalaxyCamera('blackhole'); };
    if (closeBh) closeBh.onclick = () => { toggleBlackHoleDrawer(false); };

    document.querySelectorAll('#h3-drawer-tabs .h3-dtab').forEach(tabBtn => {
      tabBtn.onclick = () => {
        const tk = tabBtn.getAttribute('data-dtab') || 'blackhole';
        openGalaxyDrawer(tk);
        focusGalaxyCamera(tk);
      };
    });

    document.querySelectorAll('#h3-nav-dock .h3-nav-btn').forEach(btn => {
      btn.onclick = () => {
        const fk = btn.getAttribute('data-focus') || 'all';
        focusGalaxyCamera(fk);
        if (fk !== 'all') {
          openGalaxyDrawer(fk);
        } else {
          toggleBlackHoleDrawer(false);
        }
      };
    });

    if (testBhBtn) {
      testBhBtn.onclick = async () => {
        const origTxt = testBhBtn.textContent;
        testBhBtn.textContent = '⏳ 正在向黑洞注入 8 大广告探针...';
        testBhBtn.disabled = true;
        try {
          const tok = localStorage.getItem('ai_link_panel_token') || '';
          const r = await fetch('/api/dns/filter/test', {
            method: 'POST',
            headers: Object.assign({ 'Content-Type': 'application/json' }, tok ? { 'X-AI-Link-Token': tok } : {}),
            body: JSON.stringify({})
          });
          const j = await r.json();
          if (j && j.ok && j.blackhole) {
            state.bh = Object.assign({}, state.bh, j.blackhole);
            renderGalaxyDrawer();
            notify(`🕳️ 深空黑洞成功吞噬 ${j.swallowed_count}/${j.tested_count} 个高频广告源 (累计拦截 ${state.bh.blocked_queries} 次)`, 'info');
          }
        } catch (e) {
          notify('黑洞吞噬实测请求异常: ' + (e.message || e), 'warn');
        } finally {
          testBhBtn.disabled = false;
          testBhBtn.textContent = origTxt;
        }
      };
    }

    if (cfgBhBtn) {
      cfgBhBtn.onclick = () => {
        toggleBlackHoleDrawer(false);
        const settingsTabBtn = document.querySelector('[data-tab="dns"]') || document.querySelector('[data-tab="settings"]');
        if (settingsTabBtn) settingsTabBtn.click();
      };
    }

    document.getElementById('h3-btn-notify').onclick = () => {
      const pool = [
        [`🕳️ 黑洞引力场已吞噬广告域名 cpro.baidu.com (累计 ${state.bh.blocked_queries || 64} 次)`, 'info'],
        ['出口 VIP1-HY09 延迟波动，已无缝切换至最优专线节点', 'warn'],
        ['AdGuard 双擎规则库 (50,085 条 .srs + DNS Sinkhole) 校验正常', 'info'],
      ];
      const [m, l] = pool[Math.floor(Math.random() * pool.length)];
      notify(m, l);
    };
    document.getElementById('h3-btn-reset').onclick = () => {
      state.locked = null;
      toggleBlackHoleDrawer(false);
      focusGalaxyCamera('all');
    };
    window.__h3Resize = () => {
      W = ROOT.clientWidth || W; H = ROOT.clientHeight || H;
      camera.aspect = Math.max(0.2, W / Math.max(1, H));
      camera.updateProjectionMatrix();
      renderer.setSize(W, H);
    };
    renderGalaxyDrawer();
    animate();
  }

  window.Holo3D = {
    mount,
    resize: () => window.__h3Resize && window.__h3Resize(),
    setLive: d => {
      if (!d) return;
      LIVE.on = true;
      LIVE.conn = d.conn | 0;
      LIVE.down = d.down || 0;
      LIVE.up = d.up || 0;
      LIVE.exit = d.exit || '';
      LIVE.mem = d.mem || 0;
      if (window.__h3SetLive) window.__h3SetLive(d);
    },
    setActive: v => { window.__h3SetActive && window.__h3SetActive(v); },
    setGalaxy: d => { window.__h3SetGalaxy && window.__h3SetGalaxy(d); },
    setHealth: l => { window.__h3SetHealth && window.__h3SetHealth(l); },
    debug: () => (window.__h3Debug ? window.__h3Debug() : null),
    notify: (m, l) => { if (_notifyFn) _notifyFn(m, l || 'info'); },
    isMounted: () => mounted,
  };
})();
