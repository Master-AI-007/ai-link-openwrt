'use strict';
'require view';
'require form';
'require uci';
'require poll';
'require fs';

return view.extend({
	handleSaveApply: null,
	handleSave: null,
	handleReset: null,

	load: function() {
		return uci.load('ai-link');
	},

	render: function() {
		var m, s, o;
		var host = window.location.hostname || '10.10.10.77';
		var port = uci.get('ai-link', 'global', 'panel_port') || '9099';
		var pwdCustFlag = String(uci.get('ai-link', 'global', 'panel_pwd_customized') || '');
		var uciSecretRaw = String(uci.get('ai-link', 'global', 'panel_secret') || '');
		var pwdIsCustom = (pwdCustFlag === '1') || (uciSecretRaw !== '' && (uciSecretRaw === '__custom__' || /^sha256:/i.test(uciSecretRaw) || uciSecretRaw !== 'ai-link-2026'));
		var uciSecret = pwdIsCustom ? '' : (uciSecretRaw || '请见 /etc/ai-link/initial_password 或执行 ai-link password');
		var luciToken = (function() { try { return String(localStorage.getItem('ailink_panel_token') || ''); } catch(e) { return ''; } })();
		var currentVer = String(uci.get('ai-link', 'global', 'app_version') || '2.5.14');
		var pwdFieldHtml = pwdIsCustom
			? '<span style="font-size:12px; color:#94a3b8; display:inline-flex; align-items:center; gap:6px;">面板密码: <code id="luci-panel-pwd-mask" style="background:#0f172a; padding:2px 7px; border-radius:5px; color:#e2e8f0; border:1px solid rgba(148,163,184,0.2);">已自定义 · 不回显</code> <span style="font-size:11px; color:#64748b;">（忘记可执行 ai-link password 重置）</span></span>'
			: '<span style="font-size:12px; color:#94a3b8; display:inline-flex; align-items:center; gap:6px;">面板密码: <code id="luci-panel-pwd-mask" style="background:#0f172a; padding:2px 7px; border-radius:5px; color:#e2e8f0; border:1px solid rgba(148,163,184,0.2);">••••••••</code> <button type="button" id="luci-btn-toggle-pwd" style="padding:2px 8px; border-radius:5px; border:1px solid rgba(148,163,184,0.3); background:rgba(30,41,59,0.8); color:#cbd5e1; font-size:11px; cursor:pointer;">查看</button></span>';
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
			_('专为全屋智能分流、抗 DNS 污染、回家内网穿透与多区域故障自愈设计的轻量透明代理网关（v2.5.2 正式版 · 纯血 Sing-box 内核）。'));

		s = m.section(form.NamedSection, 'global', globalSecType, _('运行状态概览与基础控制'));
		s.anonymous = true;

		var svcCardHtml = function() {
			var btn = function(id, label, bg, fg, border) {
				return '<button type="button" id="' + id + '" style="padding:7px 14px; border-radius:8px; border:1px solid ' + border +
					'; background:' + bg + '; color:' + fg + '; font-size:12.5px; font-weight:700; cursor:pointer;">' + label + '</button>';
			};
			return '<div style="margin: 6px 0 12px 0; padding: 14px 18px; background: linear-gradient(135deg,#0b1220 0%,#101d33 100%); border-radius: 12px; border: 1px solid rgba(56,189,248,0.3); color:#e2e8f0;">' +
				'<div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;">' +
					'<div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">' +
						'<strong style="font-size:14px; color:#e2e8f0;">基础服务与代理开关</strong>' +
						'<span id="luci-svc-badge" style="padding:3px 10px; border-radius:999px; font-size:12px; font-weight:700; background:rgba(148,163,184,0.15); color:#cbd5e1; border:1px solid rgba(148,163,184,0.3);">检测中…</span>' +
						'<span id="luci-svc-meta" style="font-size:12px; color:#94a3b8;"></span>' +
					'</div>' +
					'<div style="display:flex; gap:8px; flex-wrap:wrap;">' +
						btn('luci-btn-svc-start', '▶ 启动服务', 'rgba(16,185,129,0.2)', '#6ee7b7', 'rgba(16,185,129,0.5)') +
						btn('luci-btn-svc-stop', '⏹ 停止服务', 'rgba(239,68,68,0.16)', '#fca5a5', 'rgba(239,68,68,0.45)') +
						btn('luci-btn-svc-restart', '🔄 重启服务', 'rgba(2,132,199,0.22)', '#bae6fd', 'rgba(56,189,248,0.45)') +
						btn('luci-btn-toggle-proxy', '⚡ 切换代理接管', 'rgba(16,185,129,0.16)', '#6ee7b7', 'rgba(16,185,129,0.5)') +
						btn('luci-btn-restart-core', '🔄 重载内核', 'rgba(30,41,59,0.85)', '#e2e8f0', 'rgba(148,163,184,0.35)') +
						btn('luci-btn-svc-boot', '🔁 开机自启', 'rgba(148,163,184,0.14)', '#cbd5e1', 'rgba(148,163,184,0.35)') +
					'</div>' +
				'</div>' +
				'<div id="luci-svc-hint" style="margin-top:9px; font-size:12px; color:#94a3b8; line-height:1.6;">' +
					'LuCI 面板仅保留基础服务启停、透明代理接管开关与 OTA 在线升级；所有节点池、精细分流、DNS 护盾、回家网关与高级设置请在 :9099 独立控制台中操作。' +
				'</div>' +
			'</div>';
		};

		o = s.option(form.DummyValue, '_webui_link', _('运行状态与控制台入口'));
		o.rawhtml = true;
		o.cfgvalue = function() {
			return svcCardHtml() +
			'<div style="margin: 6px 0 14px 0; padding: 18px 20px; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 14px; border: 1px solid rgba(56,189,248,0.32); color: #f8fafc; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);">' +
				'<div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:14px;">' +
					'<div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">' +
						'<span style="font-size:17px; font-weight:800; color:#38bdf8; letter-spacing:0.4px;">AI-LINK 智能分流网关 v' + escapeHtml(currentVer) + '</span>' +
						'<span id="luci-ailink-badge" style="padding:3px 10px; border-radius:999px; font-size:12px; font-weight:700; background:rgba(16,185,129,0.18); color:#34d399; border:1px solid rgba(16,185,129,0.4);">正在同步状态...</span>' +
					'</div>' +
					'<div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">' +
						pwdFieldHtml +
						'<a id="luci-open-panel-link" href="' + escapeHtml(panelUrl) + '" target="_blank" rel="noopener noreferrer" ' +
						   'style="display:inline-flex; align-items:center; gap:6px; padding:8px 16px; background:linear-gradient(135deg, #0284c7, #2563eb); color:#fff; border-radius:9px; font-weight:700; font-size:13px; text-decoration:none; box-shadow:0 4px 12px rgba(37,99,235,0.35);">' +
						   '打开 AI-LINK 独立全功能控制台 (:' + escapeHtml(port) + ')</a>' +
					'</div>' +
				'</div>' +

				'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(195px, 1fr)); gap:10px;">' +
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
				'<div id="luci-ailink-msg" style="margin-top:10px; font-size:12px; color:#93c5fd; display:none; padding:7px 11px; border-radius:7px; background:rgba(15,23,42,0.8); border:1px solid rgba(56,189,248,0.3);"></div>' +
			'</div>' +
			'<div style="background:linear-gradient(135deg,#0b1220 0%,#101d33 100%); color:#f8fafc; padding:16px 18px; border-radius:12px; border:1px solid rgba(56,189,248,0.28); margin-bottom:10px;">' +
				'<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">' +
					'<div>' +
						'<strong style="font-size:14px; color:#e2e8f0;">⬆️ 插件版本与在线更新 (OTA)</strong>' +
						'<div id="luci-ota-sub" style="font-size:12px; color:#94a3b8; margin-top:2px;">当前 v' + escapeHtml(currentVer) + ' · 点击「检查更新」获取最新版本，支持全程在线热更新与失败自动回滚</div>' +
					'</div>' +
					'<div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">' +
						'<button type="button" id="luci-btn-ota-check" style="padding:6px 12px; border-radius:7px; border:1px solid rgba(148,163,184,0.35); background:rgba(30,41,59,0.85); color:#e2e8f0; font-size:12px; cursor:pointer;">🔍 检查更新</button>' +
						'<button type="button" id="luci-btn-ota-apply" disabled style="padding:6px 12px; border-radius:7px; border:1px solid rgba(148,163,184,0.22); background:rgba(30,41,59,0.5); color:#64748b; font-size:12px; font-weight:700; cursor:not-allowed;">⬆️ 立即更新</button>' +
						'<a id="luci-ota-notes" href="#" target="_blank" rel="noopener noreferrer" style="display:none; padding:6px 12px; border-radius:7px; border:1px solid rgba(56,189,248,0.4); background:rgba(2,132,199,0.18); color:#bae6fd; font-size:12px; text-decoration:none;">📄 更新说明</a>' +
					'</div>' +
				'</div>' +
				'<div id="luci-ota-progress-wrap" style="display:none; margin-top:12px;">' +
					'<div style="height:6px; background:#0f172a; border-radius:999px; overflow:hidden; border:1px solid rgba(148,163,184,0.18);">' +
						'<div id="luci-ota-bar" style="height:100%; width:0%; background:linear-gradient(90deg,#0284c7,#38bdf8); transition:width .3s ease;"></div>' +
					'</div>' +
					'<div id="luci-ota-stage" style="font-size:12px; color:#bae6fd; margin-top:7px;"></div>' +
					'<pre id="luci-ota-log" style="display:none; margin-top:8px; max-height:150px; overflow:auto; font-size:11px; line-height:1.5; color:#94a3b8; background:#060a14; border:1px solid rgba(148,163,184,0.15); border-radius:7px; padding:8px 10px; white-space:pre-wrap;"></pre>' +
				'</div>' +
			'</div>';
		};

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
					' <span style="font-size:11.5px; color:#38bdf8;">[' + escapeHtml(rmLabel) + ' · 出口: ' + escapeHtml(currentState.active_node || 'direct') + ']</span>';
			};

			var showMsg = function(txt, isErr) {
				var box = mapEl.querySelector('#luci-ailink-msg');
				if (!box) return;
				box.style.display = 'block';
				box.style.borderColor = isErr ? 'rgba(239,68,68,0.55)' : 'rgba(56,189,248,0.4)';
				box.style.color = isErr ? '#fca5a5' : '#bae6fd';
				box.textContent = txt;
			};

			var callApi = function(path, method, bodyObj) {
				var opts = { method: method || 'GET', headers: {} };
				if (luciToken) {
					opts.headers['X-AI-Link-Token'] = luciToken;
				}
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
							toggleBtn.textContent = '⏸️ 暂停透明代理';
							toggleBtn.style.borderColor = 'rgba(245,158,11,0.5)';
							toggleBtn.style.color = '#fde68a';
						} else {
							toggleBtn.textContent = '🟢 开启透明代理';
							toggleBtn.style.borderColor = 'rgba(16,185,129,0.55)';
							toggleBtn.style.color = '#6ee7b7';
						}
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
						var bypassTxt = currentState.entry_bypass ? '国内旁路:开' : '国内旁路:关';
						kIpv6.innerHTML = (d.ipv6_proxy ? '🌐 IPv6 代理已开启' : '🛡️ 仅 IPv4 (禁AAAA)') +
							' <span style="font-size:11.5px; color:#94a3b8;">(' + bypassTxt + ' · DNS ' + (d.dns_upstream_mounted ? '已接管' : '直连') + ')</span>';
					}
					var kNodes = mapEl.querySelector('#luci-kpi-nodes');
					if (kNodes) {
						kNodes.innerHTML = '🟢 节点 ' + (d.nodes_alive || 0) + '/' + (d.nodes_total || 0) +
							' &nbsp;|&nbsp; 🛡️ 拦截 ' + (d.adblock_hits || 0) + ' 次 <span style="font-size:11px; color:#94a3b8;">(' + (d.adblock_rules || 0) + '条)</span>';
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

			var svcBusy = false;
			var svcLast = {};

			var svcReadState = function() {
				return fs.exec('/etc/init.d/ai-link', ['svc_state']).then(function(r) {
					var out = (r && r.stdout) ? String(r.stdout) : '';
					var st = {};
					out.trim().split(/\s+/).forEach(function(kv) {
						var i = kv.indexOf('=');
						if (i > 0) st[kv.slice(0, i)] = kv.slice(i + 1);
					});
					return st;
				}).catch(function() { return {}; });
			};

			var svcRender = function(st) {
				var badge = mapEl.querySelector('#luci-svc-badge');
				var meta = mapEl.querySelector('#luci-svc-meta');
				var hint = mapEl.querySelector('#luci-svc-hint');
				var bStart = mapEl.querySelector('#luci-btn-svc-start');
				var bStop = mapEl.querySelector('#luci-btn-svc-stop');
				var bRestart = mapEl.querySelector('#luci-btn-svc-restart');
				var bBoot = mapEl.querySelector('#luci-btn-svc-boot');
				if (!badge) return;

				var has = function(k) { return st && st[k] !== undefined; };
				svcLast = st || {};
				if (!has('daemon')) {
					badge.textContent = '状态未知';
					badge.style.background = 'rgba(148,163,184,0.15)';
					badge.style.color = '#cbd5e1';
					badge.style.borderColor = 'rgba(148,163,184,0.3)';
					if (meta) meta.textContent = '无法读取服务状态';
					return;
				}

				var running = st.daemon === '1';
				var coreUp = st.core === '1';
				var nftUp = st.nft === '1';
				var enabled = st.enabled === '1';
				var bootOn = st.boot === '1';

				badge.textContent = running ? (coreUp ? '● 运行中' : '◐ 部分运行（内核未起）') : '⏹ 已停止';
				badge.style.background = running ? (coreUp ? 'rgba(16,185,129,0.18)' : 'rgba(245,158,11,0.2)') : 'rgba(239,68,68,0.18)';
				badge.style.color = running ? (coreUp ? '#34d399' : '#fde68a') : '#fca5a5';
				badge.style.borderColor = running ? (coreUp ? 'rgba(16,185,129,0.45)' : 'rgba(245,158,11,0.45)') : 'rgba(239,68,68,0.45)';

				if (meta) {
					meta.innerHTML =
						'开机自启: <b style="color:' + (bootOn ? '#34d399' : '#f87171') + ';">' + (bootOn ? '已启用' : '已禁用') + '</b>' +
						' · 透明代理接管: <b style="color:' + (enabled ? '#34d399' : '#94a3b8') + ';">' + (enabled ? '开启' : '暂停') + '</b>' +
						' · nftables: <b style="color:' + (nftUp ? '#34d399' : '#94a3b8') + ';">' + (nftUp ? '已挂载' : '未挂载') + '</b>' +
						' · 面板端口: <b style="color:#bae6fd;">:' + escapeHtml(st.port || '9099') + '</b>';
				}

				if (hint) {
					if (!running) {
						hint.innerHTML = '⚠️ <b style="color:#fca5a5;">守护进程未运行</b>，面板 :' + escapeHtml(st.port || '9099') +
							' 当前不可访问。点「▶ 启动服务」即可恢复（无需 SSH）。';
						hint.style.color = '#fca5a5';
					} else if (!coreUp && enabled) {
						hint.innerHTML = '🚨 <b style="color:#fca5a5;">Sing-box 内核未运行</b>：防黑洞看门狗已自动撤除 nftables 重定向并回退直连以保障不断网，请点上方「🔄 重启服务」或「🔄 重载内核」恢复。';
						hint.style.color = '#fca5a5';
					} else {
						hint.innerHTML = 'LuCI 面板仅保留基础服务启停、透明代理接管开关与 OTA 在线升级；所有节点池、精细分流、DNS 护盾、回家网关与高级设置请在 :' + escapeHtml(st.port || '9099') + ' 独立控制台中操作。';
						hint.style.color = '#94a3b8';
					}
				}

				var setBtn = function(el, on) {
					if (!el) return;
					el.disabled = !on || svcBusy;
					el.style.opacity = (on && !svcBusy) ? '1' : '0.45';
					el.style.cursor = (on && !svcBusy) ? 'pointer' : 'not-allowed';
				};
				setBtn(bStart, !running);
				setBtn(bStop, running);
				setBtn(bRestart, true);
				if (bBoot) {
					bBoot.textContent = bootOn ? '🔁 关闭开机自启' : '🔁 开启开机自启';
					setBtn(bBoot, true);
				}
			};

			var svcRefresh = function() {
				return svcReadState().then(function(st) { svcRender(st); return st; });
			};

			var svcRun = function(action, label) {
				if (svcBusy) return;
				svcBusy = true;
				var badge = mapEl.querySelector('#luci-svc-badge');
				if (badge) {
					badge.textContent = '⏳ ' + label + '中…';
					badge.style.background = 'rgba(2,132,199,0.2)';
					badge.style.color = '#bae6fd';
					badge.style.borderColor = 'rgba(56,189,248,0.45)';
				}
				svcRefresh();
				fs.exec('/etc/init.d/ai-link', [action]).then(function(r) {
					var code = (r && typeof r.code === 'number') ? r.code : 0;
					var errTxt = (r && r.stderr) ? String(r.stderr).trim() : '';
					if (code !== 0 && errTxt) {
						showMsg('❌ ' + label + '失败（退出码 ' + code + '）：' + errTxt.slice(0, 200), true);
					}
					return new Promise(function(res) { setTimeout(res, 1500); });
				}).then(function() {
					return svcRefresh();
				}).then(function() {
					return new Promise(function(res) { setTimeout(res, 2000); });
				}).then(function() {
					return svcRefresh();
				}).then(function() {
					svcBusy = false;
					svcRefresh();
					setTimeout(function() { refreshStatus(); }, 2500);
				}).catch(function(e) {
					svcBusy = false;
					showMsg('❌ ' + label + '请求失败：' + (e && e.message ? e.message : e), true);
					svcRefresh();
				});
			};

			bindBtn('#luci-btn-svc-start', function() { svcRun('start', '启动服务'); });
			bindBtn('#luci-btn-svc-stop', function() {
				if (!window.confirm('确认停止 AI-LINK 服务？\n\n· 守护进程与 sing-box 内核都会结束\n· 面板 :9099 将无法访问\n· 网络会恢复为纯直连（不影响正常上网）\n\n停止后可在本页「▶ 启动服务」随时恢复。')) return;
				svcRun('stop', '停止服务');
			});
			bindBtn('#luci-btn-svc-restart', function() { svcRun('restart', '重启服务'); });
			bindBtn('#luci-btn-svc-boot', function() {
				var bootNow = svcLast.boot === '1';
				svcRun(bootNow ? 'disable' : 'enable', bootNow ? '关闭开机自启' : '开启开机自启');
			});

			bindBtn('#luci-btn-toggle-proxy', function() {
				var targetEnable = !currentState.enabled;
				showMsg(targetEnable ? '正在开启透明代理、挂载 nftables 规则与 dnsmasq 7874 上游...' : '正在暂停透明代理、清理 nftables 与 dnsmasq 7874 上游并恢复局域网直连...', false);
				callApi(targetEnable ? '/restore_proxy' : '/recover_direct', 'POST', {}).then(function(r) {
					showMsg(r && r.ok ? (targetEnable ? '✅ 已开启 AI-LINK 透明代理服务！' : '✅ 已切回纯直连模式，nftables 与 DNS 转发已卸载！') : '操作失败', !(r && r.ok));
					refreshStatus();
					svcRefresh();
				});
			});

			bindBtn('#luci-btn-restart-core', function() {
				showMsg('🔄 正在重新生成配置并热重载 Sing-box 代理内核与 nftables 规则...', false);
				callApi('/ops/control', 'POST', { action: 'restart_core' }).then(function(r) {
					showMsg(r && r.ok ? ('✅ Sing-box 内核已重载 (PID: ' + (r.core_pid || 'running') + ')') : '内核重载失败', !(r && r.ok));
					refreshStatus();
					svcRefresh();
				});
			});

			bindBtn('#luci-btn-toggle-pwd', function() {
				var elMask = mapEl.querySelector('#luci-panel-pwd-mask');
				var elBtn = mapEl.querySelector('#luci-btn-toggle-pwd');
				if (!elMask || !elBtn || !uciSecret) return;
				pwdVisible = !pwdVisible;
				elMask.textContent = pwdVisible ? uciSecret : '••••••••';
				elBtn.textContent = pwdVisible ? '隐藏' : '查看';
			});

			setTimeout(function() { svcRefresh(); }, 300);
			setInterval(function() { if (!svcBusy) svcRefresh(); }, 5000);

			// ================= OTA 在线更新模块 =================
			var otaTimer = null;

			var otaRenderProgress = function(p) {
				var wrap = mapEl.querySelector('#luci-ota-progress-wrap');
				var bar = mapEl.querySelector('#luci-ota-bar');
				var stage = mapEl.querySelector('#luci-ota-stage');
				var logEl = mapEl.querySelector('#luci-ota-log');
				if (!wrap || !bar || !stage) return;
				wrap.style.display = 'block';
				var pct = Math.max(0, Math.min(100, parseInt(p.percent, 10) || 0));
				bar.style.width = pct + '%';
				bar.style.background = (p.result === 'failed' || p.stage === 'failed')
					? 'linear-gradient(90deg,#dc2626,#f87171)'
					: 'linear-gradient(90deg,#0284c7,#38bdf8)';
				var icon = p.stage === 'done' ? '✅ ' : (p.stage === 'failed' ? '❌ ' : '⏳ ');
				stage.textContent = icon + (p.stage_text || '') + ' · ' + pct + '%' + (p.message ? ' — ' + p.message : '');
				stage.style.color = p.stage === 'done' ? '#34d399' : (p.stage === 'failed' ? '#fca5a5' : '#bae6fd');
				if (logEl && Array.isArray(p.log) && p.log.length) {
					logEl.style.display = 'block';
					logEl.textContent = p.log.slice(-18).join('\n');
					logEl.scrollTop = logEl.scrollHeight;
				}
			};

			var otaPollOnce = function() {
				return callApi('/system/update/status', 'GET').then(function(r) {
					var p = (r && r.progress) || {};
					if (!p.stage) return p;
					otaRenderProgress(p);
					if (p.finished) {
						if (otaTimer) { clearInterval(otaTimer); otaTimer = null; }
						var sub = mapEl.querySelector('#luci-ota-sub');
						if (sub && p.stage === 'done') {
							sub.innerHTML = '已升级到 <b style="color:#34d399">v' + escapeHtml(p.target || currentVer) + '</b> · 建议刷新页面查看新版本界面';
						}
						var applyBtn = mapEl.querySelector('#luci-btn-ota-apply');
						if (applyBtn) {
							applyBtn.disabled = true;
							applyBtn.textContent = '⬆️ 立即更新';
							applyBtn.style.borderColor = 'rgba(148,163,184,0.22)';
							applyBtn.style.background = 'rgba(30,41,59,0.5)';
							applyBtn.style.color = '#64748b';
							applyBtn.style.cursor = 'not-allowed';
						}
						refreshStatus();
					}
					return p;
				}).catch(function() { return null; });
			};

			var otaStartPolling = function() {
				if (otaTimer) return;
				otaPollOnce();
				otaTimer = setInterval(otaPollOnce, 2000);
			};

			bindBtn('#luci-btn-ota-check', function() {
				var btn = mapEl.querySelector('#luci-btn-ota-check');
				var applyBtn = mapEl.querySelector('#luci-btn-ota-apply');
				var sub = mapEl.querySelector('#luci-ota-sub');
				var notes = mapEl.querySelector('#luci-ota-notes');
				if (!btn) return;
				btn.disabled = true;
				btn.textContent = '⏳ 检查中...';
				callApi('/system/update/check?force=1', 'GET').then(function(r) {
					btn.disabled = false;
					btn.textContent = '🔍 检查更新';
					if (!r || !r.ok) {
						showMsg('❌ ' + ((r && r.message) || '版本检查失败，请检查网络后重试'), true);
						if (sub) sub.textContent = '当前 v' + currentVer + ' · 版本检查失败（网络不通或清单不可达）';
						return;
					}
					if (notes && r.notes_url) {
						notes.href = r.notes_url;
						notes.style.display = 'inline-block';
					}
					if (r.has_update) {
						if (sub) sub.innerHTML = '当前 <b>v' + escapeHtml(r.current) + '</b> → 最新 <b style="color:#34d399">v' + escapeHtml(r.latest) + '</b>' +
							(r.release_date ? ' · 发布于 ' + escapeHtml(r.release_date) : '');
						if (applyBtn) {
							applyBtn.disabled = false;
							applyBtn.textContent = '⬆️ 立即更新到 v' + r.latest;
							applyBtn.style.borderColor = 'rgba(16,185,129,0.55)';
							applyBtn.style.background = 'rgba(16,185,129,0.2)';
							applyBtn.style.color = '#6ee7b7';
							applyBtn.style.cursor = 'pointer';
						}
						var hl = (r.highlights && r.highlights.length) ? ('\n\n本次更新要点：\n· ' + r.highlights.slice(0, 5).join('\n· ')) : '';
						showMsg('🎉 发现新版本 v' + r.latest + '，点击「立即更新」即可在线升级。' + hl, false);
					} else {
						var t = r.checked_at ? new Date(r.checked_at * 1000).toLocaleTimeString() : '';
						if (sub) sub.innerHTML = '当前 <b>v' + escapeHtml(r.current) + '</b> 已是最新版本' + (t ? '（检查于 ' + t + '）' : '');
						if (applyBtn) {
							applyBtn.disabled = true;
							applyBtn.textContent = '⬆️ 立即更新';
							applyBtn.style.borderColor = 'rgba(148,163,184,0.22)';
							applyBtn.style.background = 'rgba(30,41,59,0.5)';
							applyBtn.style.color = '#64748b';
							applyBtn.style.cursor = 'not-allowed';
						}
						showMsg('✅ 当前已是最新版本 v' + r.current, false);
					}
				}).catch(function() {
					btn.disabled = false;
					btn.textContent = '🔍 检查更新';
					showMsg('❌ 版本检查请求失败', true);
				});
			});

			bindBtn('#luci-btn-ota-apply', function() {
				var applyBtn = mapEl.querySelector('#luci-btn-ota-apply');
				if (!applyBtn || applyBtn.disabled) return;
				var targetTxt = applyBtn.textContent.replace('⬆️ 立即更新到 ', '').trim();
				if (!window.confirm('确认在线升级 AI-LINK 插件？\n\n目标版本：' + targetTxt +
					'\n\n· 升级约需 1-3 分钟，期间面板与代理会短暂中断\n' +
					'· 节点、订阅、分流规则、面板密码等配置会自动备份并完整保留\n' +
					'· 若升级后健康检查失败，会自动回滚到当前版本\n\n是否继续？')) return;
				applyBtn.disabled = true;
				applyBtn.textContent = '⏳ 正在启动升级...';
				callApi('/system/update/apply', 'POST', {}).then(function(r) {
					if (!r || !r.ok) {
						applyBtn.disabled = false;
						applyBtn.textContent = '⬆️ 重试更新';
						showMsg('❌ ' + ((r && r.message) || '升级启动失败'), true);
						return;
					}
					showMsg('🚀 ' + (r.message || '升级已开始，请勿关闭页面'), false);
					var wrap = mapEl.querySelector('#luci-ota-progress-wrap');
					if (wrap) wrap.style.display = 'block';
					otaStartPolling();
				}).catch(function() {
					applyBtn.disabled = false;
					applyBtn.textContent = '⬆️ 重试更新';
					showMsg('❌ 升级请求发送失败', true);
				});
			});

			setTimeout(function() {
				callApi('/system/update/status', 'GET').then(function(r) {
					var p = (r && r.progress) || {};
					if (!p.stage) return;
					otaRenderProgress(p);
					if (p.running) otaStartPolling();
				}).catch(function() {});
			}, 900);

			refreshStatus();
			poll.add(refreshStatus, 6);
			return mapEl;
		});
	}
});
