'use strict';
'require view';
'require form';
'require uci';
'require poll';

return view.extend({
	load: function() {
		return uci.load('ai-link');
	},

	render: function() {
		var m, s, o;
		var host = window.location.hostname || '10.10.10.77';
		var port = uci.get('ai-link', 'global', 'panel_port') || '9099';
		var uciSecret = uci.get('ai-link', 'global', 'panel_secret') || 'ai-link-2026';
		var panelUrl = 'http://' + host + ':' + port + '/';
		var apiBase = 'http://' + host + ':' + port + '/api';
		var pwdVisible = false;
		var globalSecObj = uci.get('ai-link', 'global');
		var globalSecType = (globalSecObj && globalSecObj['.type']) ? globalSecObj['.type'] : 'ai-link';

		function escapeHtml(str) {
			return String(str == null ? '' : str)
				.replace(/&/g, '&amp;')
				.replace(/</g, '&lt;')
				.replace(/>/g, '&gt;')
				.replace(/"/g, '&quot;')
				.replace(/'/g, '&#39;');
		}

		m = new form.Map('ai-link', _('AI-LINK 智能分流网关'),
			_('专为全屋智能分流、抗 DNS 污染、回家内网穿透与多区域故障自愈设计的轻量透明代理网关（v1.0.0 正式版 · 纯血 Sing-box 内核）。'));

		s = m.section(form.NamedSection, 'global', globalSecType, _('实时运行中枢与快捷控制'));
		s.anonymous = true;

		o = s.option(form.DummyValue, '_webui_link', _('中枢控制台'));
		o.rawhtml = true;
		o.cfgvalue = function() {
			return '<div style="margin: 6px 0 14px 0; padding: 18px 20px; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 14px; border: 1px solid rgba(56,189,248,0.32); color: #f8fafc; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);">' +
				'<div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:14px;">' +
					'<div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">' +
						'<span style="font-size:17px; font-weight:800; color:#38bdf8; letter-spacing:0.4px;">⚡ AI-LINK 智能分流网关 v1.0.0</span>' +
						'<span id="luci-ailink-badge" style="padding:3px 10px; border-radius:999px; font-size:12px; font-weight:700; background:rgba(16,185,129,0.18); color:#34d399; border:1px solid rgba(16,185,129,0.4);">正在同步状态...</span>' +
					'</div>' +
					'<div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">' +
						'<span style="font-size:12px; color:#94a3b8; display:inline-flex; align-items:center; gap:6px;">面板密码: <code id="luci-panel-pwd-mask" style="background:#0f172a; padding:2px 7px; border-radius:5px; color:#e2e8f0; border:1px solid rgba(148,163,184,0.2);">••••••••</code> <button type="button" id="luci-btn-toggle-pwd" style="padding:2px 8px; border-radius:5px; border:1px solid rgba(148,163,184,0.3); background:rgba(30,41,59,0.8); color:#cbd5e1; font-size:11px; cursor:pointer;">👁️ 查看</button></span>' +
						'<a id="luci-open-panel-link" href="' + escapeHtml(panelUrl) + '" target="_blank" rel="noopener noreferrer" ' +
						   'style="display:inline-flex; align-items:center; gap:6px; padding:8px 16px; background:linear-gradient(135deg, #0284c7, #2563eb); color:#fff; border-radius:9px; font-weight:700; font-size:13px; text-decoration:none; box-shadow:0 4px 12px rgba(37,99,235,0.35);">' +
						   '🚀 打开 AI-LINK 独立全功能控制台 (:' + escapeHtml(port) + ')</a>' +
					'</div>' +
				'</div>' +

				'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(195px, 1fr)); gap:10px; margin-bottom:14px;">' +
					'<div style="padding:10px 12px; background:rgba(15,23,42,0.65); border-radius:10px; border:1px solid rgba(148,163,184,0.16);">' +
						'<div style="font-size:11px; color:#94a3b8; margin-bottom:4px;">代理内核 & 透明端口</div>' +
						'<div id="luci-kpi-core" style="font-size:13px; font-weight:700; color:#e2e8f0;">Sing-box (:7893 / :7890)</div>' +
					'</div>' +
					'<div style="padding:10px 12px; background:rgba(15,23,42,0.65); border-radius:10px; border:1px solid rgba(148,163,184,0.16);">' +
						'<div style="font-size:11px; color:#94a3b8; margin-bottom:4px;">nftables 表 & 当前分流模式</div>' +
						'<div id="luci-kpi-nft" style="font-size:13px; font-weight:700; color:#e2e8f0;">检测中...</div>' +
					'</div>' +
					'<div style="padding:10px 12px; background:rgba(15,23,42,0.65); border-radius:10px; border:1px solid rgba(148,163,184,0.16);">' +
						'<div style="font-size:11px; color:#94a3b8; margin-bottom:4px;">IPv6 架构 & DNS 接管状态</div>' +
						'<div id="luci-kpi-ipv6" style="font-size:13px; font-weight:700; color:#e2e8f0;">检测中...</div>' +
					'</div>' +
					'<div style="padding:10px 12px; background:rgba(15,23,42,0.65); border-radius:10px; border:1px solid rgba(148,163,184,0.16);">' +
						'<div style="font-size:11px; color:#94a3b8; margin-bottom:4px;">可用节点 & 广告拦截</div>' +
						'<div id="luci-kpi-nodes" style="font-size:13px; font-weight:700; color:#e2e8f0;">检测中...</div>' +
					'</div>' +
				'</div>' +

				'<div style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; padding-top:10px; border-top:1px solid rgba(148,163,184,0.15);">' +
					'<button type="button" id="luci-btn-toggle-proxy" style="padding:7px 13px; border-radius:8px; border:1px solid rgba(16,185,129,0.5); background:rgba(16,185,129,0.16); color:#6ee7b7; font-size:12.5px; font-weight:700; cursor:pointer;">⚡ 切换代理总开关</button>' +
					'<div style="display:inline-flex; align-items:center; gap:5px; padding:4px 9px; border-radius:8px; background:rgba(15,23,42,0.75); border:1px solid rgba(56,189,248,0.35);">' +
						'<span style="font-size:11.5px; color:#94a3b8; font-weight:600;">分流模式:</span>' +
						'<select id="luci-sel-routing-mode" style="background:transparent; color:#bae6fd; border:none; font-size:12px; font-weight:700; cursor:pointer; outline:none;">' +
							'<option value="rule_shunt" style="background:#0f172a; color:#f8fafc;">🧭 规则分流 (AI/流媒体/国内)</option>' +
							'<option value="global_proxy" style="background:#0f172a; color:#f8fafc;">🌍 全局代理 (所有流量走节点)</option>' +
							'<option value="direct_all" style="background:#0f172a; color:#f8fafc;">🏠 全局直连 (所有流量直连)</option>' +
							'<option value="cn_whitelist" style="background:#0f172a; color:#f8fafc;">🇨🇳 大陆白名单 (非CN走代理)</option>' +
							'<option value="gfw_list" style="background:#0f172a; color:#f8fafc;">🧱 GFW列表 (仅被墙域名代理)</option>' +
						'</select>' +
					'</div>' +
					'<button type="button" id="luci-btn-toggle-ipv6" style="padding:7px 13px; border-radius:8px; border:1px solid rgba(56,189,248,0.4); background:rgba(56,189,248,0.14); color:#7dd3fc; font-size:12.5px; font-weight:700; cursor:pointer;">🛡️ 切换 IPv6 模式</button>' +
					'<button type="button" id="luci-btn-toggle-bypass" style="padding:7px 13px; border-radius:8px; border:1px solid rgba(168,85,247,0.4); background:rgba(168,85,247,0.14); color:#d8b4fe; font-size:12.5px; font-weight:700; cursor:pointer;">🚀 国内硬件旁路: 开启中</button>' +
					'<button type="button" id="luci-btn-probe-now" style="padding:7px 13px; border-radius:8px; border:1px solid rgba(148,163,184,0.35); background:rgba(30,41,59,0.85); color:#e2e8f0; font-size:12.5px; font-weight:600; cursor:pointer;">🔍 立即全量测速</button>' +
					'<button type="button" id="luci-btn-restart-core" style="padding:7px 13px; border-radius:8px; border:1px solid rgba(148,163,184,0.35); background:rgba(30,41,59,0.85); color:#e2e8f0; font-size:12.5px; font-weight:600; cursor:pointer;">🔄 重载 Sing-box 内核</button>' +
					'<button type="button" id="luci-btn-flush-dns" style="padding:7px 13px; border-radius:8px; border:1px solid rgba(148,163,184,0.35); background:rgba(30,41,59,0.85); color:#e2e8f0; font-size:12.5px; font-weight:600; cursor:pointer;">🧹 刷新 DNS 缓存</button>' +
					'<button type="button" id="luci-btn-restore-archive" style="display:none; padding:7px 13px; border-radius:8px; border:1px solid rgba(250,204,21,0.5); background:rgba(250,204,21,0.15); color:#fef08a; font-size:12.5px; font-weight:700; cursor:pointer;">📦 从备份恢复配置</button>' +
					'<button type="button" id="luci-btn-uninstall" style="margin-left:auto; padding:7px 13px; border-radius:8px; border:1px solid rgba(239,68,68,0.45); background:rgba(239,68,68,0.15); color:#fca5a5; font-size:12.5px; font-weight:700; cursor:pointer;">🗑️ 安全卸载并恢复网络</button>' +
				'</div>' +
				'<div id="luci-ailink-msg" style="margin-top:10px; font-size:12px; color:#93c5fd; display:none; padding:7px 11px; border-radius:7px; background:rgba(15,23,42,0.8); border:1px solid rgba(56,189,248,0.3);"></div>' +
			'</div>' +
			'<div style="background:#0f172a; color:#f8fafc; padding:16px 18px; border-radius:12px; border:1px solid #334155; margin-bottom:10px;">' +
				'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">' +
					'<div>' +
						'<strong style="font-size:14px;">📦 订阅、分流规则库与组件更新中心</strong>' +
						'<div style="font-size:12px; color:#94a3b8;">自动使用下方配置的 GitHub 加速源拉取最新规则集与已配置的订阅源</div>' +
					'</div>' +
					'<div style="display:flex; gap:8px;">' +
						'<button type="button" id="luci-btn-check-updates" style="padding:6px 12px; border-radius:7px; border:1px solid rgba(148,163,184,0.35); background:rgba(30,41,59,0.85); color:#e2e8f0; font-size:12px; cursor:pointer;">🔍 检查更新状态</button>' +
						'<button type="button" id="luci-btn-update-all" style="padding:6px 12px; border-radius:7px; border:1px solid rgba(56,189,248,0.45); background:rgba(2,132,199,0.25); color:#bae6fd; font-size:12px; font-weight:700; cursor:pointer;">🚀 一键全部立即更新</button>' +
					'</div>' +
				'</div>' +
				'<table style="width:100%; font-size:13px; border-collapse:collapse; background:#1e293b; color:#f8fafc; border-radius:8px; overflow:hidden;">' +
					'<thead><tr style="background:#0f172a; color:#94a3b8; border-bottom:1px solid #334155;"><th style="padding:9px 12px; text-align:left; color:#94a3b8;">更新项目</th><th style="padding:9px 12px; text-align:left; color:#94a3b8;">当前状态</th><th style="padding:9px 12px; text-align:left; color:#94a3b8;">同步时间 / 详情</th><th style="padding:9px 12px; text-align:right; color:#94a3b8;">操作</th></tr></thead>' +
					'<tbody id="ailink-updates-tbody"><tr style="background:#1e293b; color:#f8fafc;"><td colspan="4" style="padding:10px 12px; color:#cbd5e1;">正在获取各模块更新状态...</td></tr></tbody>' +
				'</table>' +
			'</div>';
		};

		s = m.section(form.NamedSection, 'global', globalSecType, _('底层持久化参数（与上方快捷开关双向同步，点击底部「保存并应用」写入 UCI）'));
		s.anonymous = true;

		o = s.option(form.Flag, 'enabled', _('启用 AI-LINK 透明代理服务'),
			_('控制是否挂载 nftables 透明代理流量接管与 dnsmasq 7874 上游。取消勾选并「保存并应用」将立即卸载透明代理规则并恢复纯直连，WebUI 控制台 (:9099) 保持在线以便随时唤醒。'));
		o.rmempty = false;

		o = s.option(form.Flag, 'ipv6_proxy', _('开启 IPv6 透明代理 (v1.0.0 重构架构)'),
			_('【默认关闭 · 防漏加固模式】关闭时海外域名在 :7874 入口自动剥离 AAAA 记录（彻底阻断双栈环境下海外流量绕过 IPv4 代理直连泄漏），国内域名保留原生 IPv6 直连；开启时自动挂载 IPv6 TProxy 全栈透明代理与 Google/YouTube IPv6 QUIC 防降级规则。'));
		o.default = '0';
		o.rmempty = false;

		o = s.option(form.Flag, 'entry_bypass', _('国内大陆 IP 硬件级入口直连 (Entry Bypass)'),
			_('开启后，目的地址属于中国大陆 (@cn_ipv4) 的流量在 nftables 入口直接 return 走内核 Fastpath/硬件加速，并自动挂载旁路由对称 NAT 断流保护，实现跑满千兆宽带且零 CPU 损耗。'));
		o.default = '1';
		o.rmempty = false;

		o = s.option(form.Flag, 'block_quic', _('阻断海外 UDP 443 (QUIC) 防降级'),
			_('开启后强制浏览器回退至 TCP H2/TLS，显著提升 YouTube 4K/8K 与 Google 服务的连接稳定性与分流准确度。'));
		o.default = '1';
		o.rmempty = false;

		o = s.option(form.Flag, 'game_udp_direct', _('游戏高频 UDP 端口直连优化'),
			_('开启后非 53/443 的高频游戏联机 UDP 流量在防火墙入口直接放行，避免代理抖动。'));
		o.default = '1';
		o.rmempty = false;

		o = s.option(form.Flag, 'auto_mute_conflicts', _('自动检查并隔离冲突代理插件'),
			_('启动时自动检测并停止 OpenClash / PassWall / HomeProxy / Nikki 等冲突服务，防止多插件争抢 53 端口与 fwmark 导致断网。'));
		o.default = '1';
		o.rmempty = false;

		o = s.option(form.Value, 'gh_mirror', _('GitHub 规则与核心更新加速源'),
			_('用于加速下载 GeoIP / GeoSite 分流规则集与云端广告拦截规则。可选择预设加速源或填入自定义镜像地址。'));
		o.value('https://gh-proxy.com/', _('https://gh-proxy.com/ (默认高速加速源)'));
		o.value('https://ghfast.top/', _('https://ghfast.top/ (国内优选镜像源)'));
		o.value('https://mirror.ghproxy.com/', _('https://mirror.ghproxy.com/ (备用加速源)'));
		o.value('https://testingcf.jsdelivr.net/', _('https://testingcf.jsdelivr.net/ (Cloudflare CDN)'));
		o.value('', _('不使用镜像 (GitHub 官方直连)'));
		o.default = 'https://gh-proxy.com/';
		o.rmempty = true;

		o = s.option(form.Value, 'panel_port', _('独立控制面板端口'),
			_('默认监听 9099 端口。修改后需重启 ai-link 服务生效。'));
		o.datatype = 'port';
		o.default = '9099';
		o.rmempty = false;

		o = s.option(form.Value, 'max_outbounds', _('编译进内核的最大节点数 (Top-N 瘦身)'),
			_('针对软路由与硬路由内存优化：仅将测速最优的前 N 个节点编译进 Sing-box 运行配置，防止千节点订阅撑爆内存（推荐 120~200）。'));
		o.datatype = 'range(10, 500)';
		o.default = '200';
		o.rmempty = false;

		return m.render().then(function(mapEl) {
			var currentState = {
				ipv6_proxy: false,
				entry_bypass: true,
				enabled: true,
				routing_mode: 'rule_shunt',
				nft_table_mounted: false,
				active_node: 'direct'
			};
			var rmodeLabels = {
				rule_shunt: '规则分流',
				global_proxy: '全局代理',
				direct_all: '全局直连',
				cn_whitelist: '大陆白名单',
				gfw_list: 'GFW列表'
			};

			var renderKpiNft = function() {
				var kNft = mapEl.querySelector('#luci-kpi-nft');
				if (!kNft) return;
				var rmLabel = rmodeLabels[currentState.routing_mode] || currentState.routing_mode;
				kNft.innerHTML = (currentState.nft_table_mounted ? '✅ inet ai_link 已挂载' : '⏸️ 未挂载 (直连恢复)') +
					' <span style="font-size:11.5px; color:#38bdf8;">[' + rmLabel + ' · 出口: ' + (currentState.active_node || 'direct') + ']</span>';
			};

			var showMsg = function(txt, isErr) {
				var box = mapEl.querySelector('#luci-ailink-msg');
				if (!box) return;
				box.style.display = 'block';
				box.style.borderColor = isErr ? 'rgba(239,68,68,0.55)' : 'rgba(56,189,248,0.4)';
				box.style.color = isErr ? '#fca5a5' : '#bae6fd';
				box.textContent = txt;
			};

			var syncUciCheckboxDom = function(optName, boolVal) {
				var cb = mapEl.querySelector('input[type="checkbox"][name="cbid.ai-link.global.' + optName + '"]') ||
				         mapEl.querySelector('#widget\\.cbid\\.ai-link\\.global\\.' + optName);
				if (cb && cb.checked !== !!boolVal) {
					cb.checked = !!boolVal;
				}
			};

			var callApi = function(path, method, bodyObj) {
				var opts = { method: method || 'GET', headers: { 'X-AI-Link-Token': uciSecret } };
				if (bodyObj !== undefined) {
					opts.headers['Content-Type'] = 'application/json';
					opts.body = JSON.stringify(bodyObj);
				}
				return fetch(apiBase + path, opts).then(function(r) { return r.json(); });
			};

			var refreshStatus = function() {
				return Promise.all([
					callApi('/ops/diag', 'GET'),
					callApi('/status', 'GET').catch(function() { return {}; })
				]).then(function(results) {
					var d = results[0] || {};
					var st = results[1] || {};
					if (!d || !d.ok) return;
					var ops = st.ops_settings || {};
					var isActive = (d.routing_state === 'proxy') && (ops.enabled !== false) && !st.bypass_active;
					currentState.enabled = isActive;
					currentState.ipv6_proxy = !!d.ipv6_proxy;
					currentState.entry_bypass = (ops.entry_bypass !== undefined) ? !!ops.entry_bypass : true;
					currentState.routing_mode = d.routing_mode || st.routing_mode || currentState.routing_mode || 'rule_shunt';
					currentState.nft_table_mounted = !!d.nft_table_mounted;
					currentState.active_node = d.active_node || 'direct';

					// Sync bottom UCI form checkboxes with live state so LuCI form never drifts from top action bar
					syncUciCheckboxDom('enabled', isActive);
					syncUciCheckboxDom('ipv6_proxy', currentState.ipv6_proxy);
					syncUciCheckboxDom('entry_bypass', currentState.entry_bypass);
					if (ops.block_quic !== undefined) syncUciCheckboxDom('block_quic', !!ops.block_quic);
					if (ops.game_udp_direct !== undefined) syncUciCheckboxDom('game_udp_direct', !!ops.game_udp_direct);

					var badge = mapEl.querySelector('#luci-ailink-badge');
					if (badge) {
						badge.textContent = isActive ? ('● 运行中 · ' + (d.routing_label || '透明代理已激活')) : ('⏸️ 已暂停 · ' + (d.routing_label || '纯直连恢复模式'));
						badge.style.background = isActive ? 'rgba(16,185,129,0.18)' : 'rgba(245,158,11,0.2)';
						badge.style.color = isActive ? '#34d399' : '#fde68a';
						badge.style.borderColor = isActive ? 'rgba(16,185,129,0.45)' : 'rgba(245,158,11,0.45)';
					}
					var toggleBtn = mapEl.querySelector('#luci-btn-toggle-proxy');
					if (toggleBtn) {
						if (isActive) {
							toggleBtn.textContent = '⏸️ 暂停透明代理 (切回直连)';
							toggleBtn.style.borderColor = 'rgba(245,158,11,0.5)';
							toggleBtn.style.color = '#fde68a';
						} else {
							toggleBtn.textContent = '🟢 立即开启透明代理';
							toggleBtn.style.borderColor = 'rgba(16,185,129,0.55)';
							toggleBtn.style.color = '#6ee7b7';
						}
					}
					var rmodeSel = mapEl.querySelector('#luci-sel-routing-mode');
					if (rmodeSel && currentState.routing_mode) {
						rmodeSel.value = currentState.routing_mode;
					}
					var v6Btn = mapEl.querySelector('#luci-btn-toggle-ipv6');
					if (v6Btn) {
						v6Btn.textContent = currentState.ipv6_proxy ? '🛡️ 关闭 IPv6 代理 (切回防漏模式)' : '🛡️ 开启 IPv6 透明代理';
					}
					var bypassBtn = mapEl.querySelector('#luci-btn-toggle-bypass');
					if (bypassBtn) {
						bypassBtn.textContent = currentState.entry_bypass ? '🚀 国内硬件旁路: 已开启 (点击关闭)' : '🚀 国内硬件旁路: 已关闭 (点击开启)';
					}
					var kCore = mapEl.querySelector('#luci-kpi-core');
					if (kCore) {
						var p7893 = d.ports && d.ports['7893'];
						kCore.innerHTML = (d.singbox_check_ok ? '✅ 配置校验通过' : '⚠️ 校验告警') +
							' <span style="font-size:11.5px; color:#94a3b8;">(' + (p7893 ? ':7893 监听中' : ':7893 已停止') + ')</span>';
					}
					renderKpiNft();
					var kIpv6 = mapEl.querySelector('#luci-kpi-ipv6');
					if (kIpv6) {
						kIpv6.innerHTML = (d.ipv6_proxy ? '🌐 IPv6 透明代理开启' : '🛡️ 仅 IPv4 代理 (海外禁AAAA)') +
							' <span style="font-size:11.5px; color:#94a3b8;">(DNS :7874 ' + (d.dns_upstream_mounted ? '已接管' : '直连恢复') + ')</span>';
					}
					var kNodes = mapEl.querySelector('#luci-kpi-nodes');
					if (kNodes) {
						kNodes.innerHTML = '🟢 节点 ' + (d.nodes_alive || 0) + '/' + (d.nodes_total || 0) +
							' &nbsp;|&nbsp; 🛡️ 拦截 ' + (d.adblock_hits || 0) + ' 次 <span style="font-size:11px; color:#94a3b8;">(' + (d.adblock_rules || 0) + '条)</span>';
					}
					var arcBtn = mapEl.querySelector('#luci-btn-restore-archive');
					if (arcBtn) {
						arcBtn.style.display = d.has_backup_archive ? 'inline-block' : 'none';
					}
					var elUpdBody = mapEl.querySelector('#ailink-updates-tbody');
					if (elUpdBody && st.updatable_summary && Array.isArray(st.updatable_summary.items)) {
						var validItems = st.updatable_summary.items.filter(function(item) {
							return item && String(item.id || '').trim() !== '' && String(item.name || '').trim() !== '';
						});
						elUpdBody.innerHTML = validItems.map(function(item, idx) {
							var rowBg = (idx % 2 === 0) ? '#1e293b' : '#172033';
							var okBadge = item.status_ok
								? '<span style="color:#10b981;font-weight:bold;">✓ 正常</span>'
								: '<span style="color:#f59e0b;font-weight:bold;">⚠ 待更新</span>';
							var cellStyle = 'background:' + rowBg + ' !important;color:#f8fafc !important;padding:9px 12px;border-bottom:1px solid #334155;vertical-align:middle;';
							return '<tr style="background:' + rowBg + ' !important;color:#f8fafc !important;">' +
								'<td style="' + cellStyle + 'font-weight:bold;">' + escapeHtml(item.name) + '</td>' +
								'<td style="' + cellStyle + '">' + escapeHtml(item.current || '-') + '</td>' +
								'<td style="' + cellStyle + '">' + okBadge + ' · <span style="color:#cbd5e1;font-size:12px;">' + escapeHtml(item.updated_at || '-') + '</span></td>' +
								'<td style="' + cellStyle + 'text-align:right;">' +
									'<button type="button" data-upd-item="' + escapeHtml(item.id) + '" style="padding:4px 10px; border-radius:6px; border:1px solid rgba(56,189,248,0.4); background:rgba(2,132,199,0.2); color:#bae6fd; font-size:12px; cursor:pointer;">立即更新</button>' +
								'</td>' +
							'</tr>';
						}).join('');
						elUpdBody.querySelectorAll('[data-upd-item]').forEach(function(btn) {
							btn.addEventListener('click', function() {
								var itemId = btn.getAttribute('data-upd-item');
								btn.disabled = true;
								btn.textContent = '更新中...';
								callApi('/ops/update_item', 'POST', { item: itemId }).then(function(res) {
									btn.disabled = false;
									btn.textContent = '立即更新';
									var subRes = (res && res.results && res.results[itemId]) ? res.results[itemId] : null;
									showMsg(subRes && subRes.message ? subRes.message : ('✅ 已完成更新: ' + itemId), !!(subRes && subRes.ok === false));
									refreshStatus();
								}).catch(function() {
									btn.disabled = false;
									btn.textContent = '立即更新';
								});
							});
						});
					}
				}).catch(function() {
					var badge = mapEl.querySelector('#luci-ailink-badge');
					if (badge) {
						badge.textContent = '⚠️ 守护进程未响应 (请检查服务)';
						badge.style.background = 'rgba(239,68,68,0.2)';
						badge.style.color = '#fca5a5';
					}
				});
			};

			var bindBtn = function(sel, fn) {
				var el = mapEl.querySelector(sel);
				if (el) el.addEventListener('click', fn);
			};

			bindBtn('#luci-btn-toggle-pwd', function() {
				var elMask = mapEl.querySelector('#luci-panel-pwd-mask');
				var elBtn = mapEl.querySelector('#luci-btn-toggle-pwd');
				if (!elMask || !elBtn) return;
				pwdVisible = !pwdVisible;
				elMask.textContent = pwdVisible ? uciSecret : '••••••••';
				elBtn.textContent = pwdVisible ? '🙈 隐藏' : '👁️ 查看';
			});

			bindBtn('#luci-btn-check-updates', function() {
				showMsg('🔍 正在刷新订阅与分流规则库状态...', false);
				refreshStatus().then(function() {
					showMsg('✅ 已刷新所有组件与规则库最新状态。', false);
				});
			});

			bindBtn('#luci-btn-update-all', function() {
				var btn = mapEl.querySelector('#luci-btn-update-all');
				if (btn) { btn.disabled = true; btn.textContent = '正在全量更新...'; }
				showMsg('🚀 正在拉取全部订阅、GeoIP/GeoSite 分流规则集与云端广告规则...', false);
				callApi('/ops/update_item', 'POST', { item: 'all' }).then(function(r) {
					if (btn) { btn.disabled = false; btn.textContent = '🚀 一键全部立即更新'; }
					showMsg('✅ 全部已配置组件、分流规则集与云端过滤库已更新至最新！', !(r && r.ok !== false));
					refreshStatus();
				}).catch(function() {
					if (btn) { btn.disabled = false; btn.textContent = '🚀 一键全部立即更新'; }
				});
			});

			bindBtn('#luci-btn-toggle-proxy', function() {
				var targetEnable = !currentState.enabled;
				showMsg(targetEnable ? '正在开启透明代理、挂载 nftables 规则与 dnsmasq 7874 上游...' : '正在暂停透明代理、清理 nftables 与 dnsmasq 7874 上游并恢复局域网直连...', false);
				callApi(targetEnable ? '/restore_proxy' : '/recover_direct', 'POST', {}).then(function(r) {
					showMsg(r && r.ok ? (targetEnable ? '✅ 已开启 AI-LINK 透明代理服务（下方总开关已同步勾选）！' : '✅ 已切回纯直连模式，nftables 与 DNS 转发已卸载，下方总开关已同步取消勾选！') : '操作失败', !(r && r.ok));
					refreshStatus();
				});
			});

			var rmodeEl = mapEl.querySelector('#luci-sel-routing-mode');
			if (rmodeEl) {
				rmodeEl.addEventListener('change', function() {
					var newMode = rmodeEl.value;
					currentState.routing_mode = newMode;
					renderKpiNft();
					showMsg('正在切换分流模式为 [' + (rmodeLabels[newMode] || newMode) + '] 并热更新内核配置...', false);
					callApi('/shunt/update', 'POST', { routing_mode: newMode }).then(function(r) {
						if (r && r.routing_mode) {
							currentState.routing_mode = r.routing_mode;
							renderKpiNft();
						}
						showMsg(r && r.ok ? ('✅ 已切换分流模式为: ' + (rmodeLabels[currentState.routing_mode] || currentState.routing_mode)) : '切换分流模式失败', !(r && r.ok));
						refreshStatus();
					});
				});
			}

			bindBtn('#luci-btn-toggle-ipv6', function() {
				var nextV6 = !currentState.ipv6_proxy;
				showMsg('正在切换 IPv6 模式为: ' + (nextV6 ? '开启 IPv6 透明代理' : '关闭 IPv6 (海外禁 AAAA + 国内原生 IPv6 直连)') + '...', false);
				callApi('/ops/ipv6', 'POST', { ipv6_proxy: nextV6 }).then(function(r) {
					showMsg((r && r.message) ? r.message : '✅ IPv6 模式切换完成', !(r && r.ok));
					refreshStatus();
				});
			});

			bindBtn('#luci-btn-toggle-bypass', function() {
				var nextBypass = !currentState.entry_bypass;
				showMsg('正在切换国内大陆 IP 硬件级入口直连 (Entry Bypass): ' + (nextBypass ? '开启' : '关闭') + '...', false);
				callApi('/ops/settings', 'POST', { entry_bypass: nextBypass }).then(function(r) {
					showMsg(r && r.ok ? ('✅ 国内大陆 IP 硬件级入口直连已' + (nextBypass ? '开启' : '关闭') + '（已同步挂载旁路由对称 NAT 保护）') : '设置失败', !(r && r.ok));
					refreshStatus();
				});
			});

			bindBtn('#luci-btn-probe-now', function() {
				showMsg('🔍 已触发全量节点并发 URLTest 探针测速与智能选路...', false);
				callApi('/probe/run', 'POST', { manual: true }).then(function(r) {
					showMsg(r && r.ok ? '✅ 全量测速任务已在后台启动，约 3~5 秒后刷新节点健康度。' : '触发测速失败', !(r && r.ok));
					setTimeout(refreshStatus, 3500);
				});
			});

			bindBtn('#luci-btn-restart-core', function() {
				showMsg('🔄 正在重新生成配置并热重载 Sing-box 代理内核与 nftables 规则...', false);
				callApi('/ops/control', 'POST', { action: 'restart_core' }).then(function(r) {
					showMsg(r && r.ok ? ('✅ Sing-box 内核已重载 (PID: ' + (r.core_pid || 'running') + ')') : '内核重载失败', !(r && r.ok));
					refreshStatus();
				});
			});

			bindBtn('#luci-btn-flush-dns', function() {
				showMsg('🧹 正在清理 dnsmasq 与 Sing-box DNS 缓存...', false);
				callApi('/dns/flush_cache', 'POST', {}).then(function(r) {
					showMsg(r && r.ok ? '✅ DNS 缓存已彻底刷新！' : '刷新失败', !(r && r.ok));
					refreshStatus();
				});
			});

			bindBtn('#luci-btn-restore-archive', function() {
				if (!window.confirm('确认从 /root/ai-link-final-backup/etc-ai-link.tgz 恢复全部节点与分流配置吗？')) return;
				showMsg('📦 正在从备份归档恢复配置与节点...', false);
				callApi('/ops/restore_archive', 'POST', {}).then(function(r) {
					showMsg((r && r.message) ? r.message : '恢复完成', !(r && r.ok));
					refreshStatus();
				});
			});

			bindBtn('#luci-btn-uninstall', function() {
				if (!window.confirm('⚠️ 确认要安全卸载 AI-LINK 吗？\n\n卸载过程会自动停止代理、清空 nftables 规则、恢复 dnsmasq 默认解析，并将您的节点配置安全归档至 /root/ai-link-final-backup/etc-ai-link.tgz。')) return;
				var keepCfg = window.confirm('是否在卸载时保留 /etc/ai-link 配置目录以便日后重装直接复用？\n（点击【确定】保留配置，点击【取消】彻底删除配置但仍保留 /root 归档备份）');
				showMsg('🗑️ 正在执行安全卸载并恢复原机网络，请稍候...', false);
				callApi('/ops/uninstall', 'POST', { keep_config: keepCfg }).then(function(r) {
					showMsg((r && r.message) ? r.message : '正在卸载...', false);
					setTimeout(function() { window.location.href = '/cgi-bin/luci/'; }, 2500);
				});
			});

			refreshStatus();
			poll.add(refreshStatus, 6);
			return mapEl;
		});
	}
});
