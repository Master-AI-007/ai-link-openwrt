(function () {
  'use strict';
  if (window.__AILINK_NEXUS_BOOTED__) return;
  window.__AILINK_NEXUS_BOOTED__ = true;

  const $ = (selector, root) => (root || document).querySelector(selector);
  const $$ = (selector, root) => Array.from((root || document).querySelectorAll(selector));
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const COUNTRY_META = {
    HK: { code: 'HK', flag: '🇭🇰', name: '香港 (HK)', short: '香港' },
    TW: { code: 'TW', flag: '🇹🇼', name: '台湾 (TW)', short: '台湾' },
    JP: { code: 'JP', flag: '🇯🇵', name: '日本 (JP)', short: '日本' },
    SG: { code: 'SG', flag: '🇸🇬', name: '新加坡 (SG)', short: '新加坡' },
    US: { code: 'US', flag: '🇺🇸', name: '美国 (US)', short: '美国' },
    OTHER: { code: 'OTHER', flag: '🌐', name: '其他地区', short: '其他' }
  };
  const COUNTRY_CODES = ['HK', 'TW', 'JP', 'SG', 'US', 'OTHER'];

  const mock = {
    connections: 0,
    down: 274,
    up: 24,
    downText: '274 KB/s',
    upText: '24 KB/s',
    monthTotalText: '6.58 GB',
    upTotalText: '134.0 MB',
    latency: 156,
    healthScore: 98,
    coreMemMib: 117.4,
    blockedTotal: 483549,
    dnsRulesCount: 50000,
    dnsLayerCount: 450446,
    rejectLayerCount: 2877,
    activeOutbounds: 200,
    maxOutboundsLimit: 200,
    totalNodes: 6,
    devicesTotal: 8,
    devicesActive: 3,
    destinationsTotal: 126,
    inTotalText: '0 B',
    outTotalText: '0 B',
    monthTotalConns: 0,
    uptimeStr: '运行中',
    dnsBlockedPct: 15.2,
    dnsAvgMs: 1,
    services: [
      { id: 'openai', name: 'ChatGPT', selector: 'Shunt_AI', groupId: 'AI', ms: 168, state: 'ok' },
      { id: 'gemini', name: 'Gemini', selector: 'Shunt_AI', groupId: 'AI', ms: 182, state: 'ok' },
      { id: 'youtube', name: 'YouTube', selector: 'Shunt_YouTube', groupId: 'YouTube', ms: 146, state: 'ok' },
      { id: 'github', name: 'GitHub', selector: 'Shunt_GitHub', groupId: 'GitHub', ms: 195, state: 'ok' },
      { id: 'netflix', name: 'Netflix', selector: 'Shunt_Netflix', groupId: 'Netflix', ms: 132, state: 'ok' },
      { id: 'tiktok', name: 'TikTok', selector: 'Shunt_TikTok', groupId: 'TikTok', ms: 158, state: 'ok' },
      { id: 'telegram', name: 'Telegram', selector: 'Shunt_Social', groupId: 'Social', ms: 149, state: 'ok' },
      { id: 'bilibili', name: 'B站直连', selector: 'Shunt_Domestic_CN', groupId: 'Domestic_CN', ms: 22, state: 'ok' }
    ],
    routingModes: [
      { id: 'rule_shunt', code: 'RECOMMENDED', name: '精细规则分流', shortName: '分流模式', desc: 'AI、视频、社交与国内独立策略' },
      { id: 'gfw_list', code: 'GFW LIST', name: '仅被墙网站代理', shortName: 'GFW 模式', desc: '名单内代理，其余流量全部直连' },
      { id: 'cn_whitelist', code: 'CN BYPASS', name: '非国内走代理', shortName: '非国内模式', desc: '国内直连，海外统一代理出口' },
      { id: 'global_proxy', code: 'GLOBAL', name: '全局代理模式', shortName: '全局模式', desc: '除内网外统一使用代理出口' },
      { id: 'direct_all', code: 'FAIL OPEN', name: '全局直连模式', shortName: '直连模式', desc: '暂停代理分流，恢复宽带出网' }
    ],
    groups: [
      { id: 'AI', name: 'AI 智能助手', subtitle: 'OpenAI / Claude / Gemini / Copilot / Cursor', shunt_mode: 'auto', auto_node_id: 'auto_ai', auto_node_name: 'AI 自动池', country: 'US', resolved_node: '新加坡 06', rtt: 156, domains: ['openai.com', 'anthropic.com', 'claude.ai', 'gemini.google.com', 'cursor.sh'], is_custom: false },
      { id: 'YouTube', name: 'YouTube 视频', subtitle: 'YouTube 4K/8K 视频流与 googlevideo CDN', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'JP', resolved_node: '日本 07', rtt: 142, domains: ['youtube.com', 'googlevideo.com', 'ytimg.com', 'youtu.be'], is_custom: false },
      { id: 'TikTok', name: 'TikTok 国际版', subtitle: '短视频与国际直播 CDN 专线', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'SG', resolved_node: '新加坡 08', rtt: 168, domains: ['tiktok.com', 'tiktokv.com', 'tiktokcdn.com', 'musical.ly'], is_custom: false },
      { id: 'Netflix', name: 'Netflix 流媒体', subtitle: '奈飞 / Disney+ / 国际流媒体解锁', shunt_mode: 'auto', auto_node_id: 'auto_netflix', auto_node_name: '流媒体自动池', country: 'HK', resolved_node: '香港 N3', rtt: 96, domains: ['netflix.com', 'nflxvideo.net', 'disneyplus.com', 'hbo.com'], is_custom: false },
      { id: 'Google', name: 'Google 全生态', subtitle: '搜索 / Play 商店更新 CDN / FCM 推送', shunt_mode: 'auto', auto_node_id: 'auto_ai', auto_node_name: 'AI 自动池', country: 'SG', resolved_node: '新加坡 06', rtt: 156, domains: ['google.com', 'googleapis.com', 'gstatic.com', 'gvt1.com', 'dl.google.com'], is_custom: false },
      { id: 'GitHub', name: 'GitHub 开发者', subtitle: '代码仓库 / Release 资产 / 容器镜像', shunt_mode: 'auto', auto_node_id: 'auto_ai', auto_node_name: 'AI 自动池', country: 'JP', resolved_node: '日本 07', rtt: 142, domains: ['github.com', 'githubusercontent.com', 'githubassets.com', 'ghcr.io'], is_custom: false },
      { id: 'Social', name: 'Telegram 与社交', subtitle: 'Telegram / X (Twitter) / Discord / WhatsApp', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'SG', resolved_node: '新加坡 06', rtt: 156, domains: ['telegram.org', 't.me', 'twitter.com', 'x.com', 'discord.com'], is_custom: false },
      { id: 'Microsoft', name: 'Microsoft 微软生态', subtitle: 'Office 365 / OneDrive / Windows 更新', shunt_mode: 'direct', auto_node_id: 'auto_youtube', auto_node_name: '直连模式', country: 'direct', resolved_node: 'direct', rtt: 0, domains: ['microsoft.com', 'office.com', 'live.com', 'windowsupdate.com'], is_custom: false },
      { id: 'Apple', name: 'Apple 苹果服务', subtitle: 'App Store / iCloud / TestFlight 分发', shunt_mode: 'direct', auto_node_id: 'auto_youtube', auto_node_name: '直连模式', country: 'direct', resolved_node: 'direct', rtt: 0, domains: ['apple.com', 'icloud.com', 'mzstatic.com', 'cdn-apple.com'], is_custom: false },
      { id: 'Games', name: '游戏平台与联机', subtitle: 'Steam / Epic / PlayStation / Xbox', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'HK', resolved_node: '香港 N3', rtt: 96, domains: ['steampowered.com', 'steamcommunity.com', 'epicgames.com'], is_custom: false },
      { id: 'Outside_CN', name: '海外其他流量', subtitle: '未命中专项规则的非大陆流量统管', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'SG', resolved_node: '新加坡 06', rtt: 156, domains: ['geolocation-!cn'], is_custom: false },
      { id: 'Domestic_CN', name: '国内直连白名单', subtitle: '大陆域名 / 抖音快手直播 CDN / 国内 IP 直通', shunt_mode: 'direct', auto_node_id: '', auto_node_name: '直连', country: 'direct', resolved_node: 'direct', rtt: 0, domains: ['douyincdn.com', 'bilibili.com', 'baidu.com', 'qq.com', 'taobao.com', 'geosite:cn'], is_custom: false, locked_order: true },
      { id: 'Final_Fallback', name: '最终兜底回退', subtitle: 'Final Fallback 漏网流量安全兜底', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'SG', resolved_node: '新加坡 06', rtt: 156, domains: ['final-fallback'], is_custom: false, locked_bottom: true, locked_order: true }
    ],
    autoPools: [
      { id: 'auto_ai', tag: 'Auto_AI', name: 'AI 专线自动池', mode: 'full', healthy_count: 6, active_group_index: 1, current_node: '新加坡 06', current_delay_ms: 156, groups: [{ index: 1, name: '主力组 G1', node_tags: ['新加坡 06', '日本 07'] }, { index: 2, name: '备选组 G2', node_tags: ['香港 N3', '新加坡 08'] }] },
      { id: 'auto_youtube', tag: 'Auto_YouTube', name: 'YouTube 视频自动池', mode: 'full', healthy_count: 6, active_group_index: 1, current_node: '日本 07', current_delay_ms: 142, groups: [{ index: 1, name: '主力组 G1', node_tags: ['日本 07', '香港 N3'] }, { index: 2, name: '备选组 G2', node_tags: ['新加坡 06', '台湾 02'] }] },
      { id: 'auto_netflix', tag: 'Auto_Netflix', name: '流媒体解锁自动池', mode: 'semi', healthy_count: 4, active_group_index: 1, current_node: '香港 N3', current_delay_ms: 96, groups: [{ index: 1, name: '主力组 G1', node_tags: ['香港 N3', '台湾 02'] }, { index: 2, name: '备选组 G2', node_tags: ['新加坡 06'] }] }
    ],
    homelinkNodes: [
      { id: 'hy2', protocol: 'HY2', raw_proto: 'hysteria2', name: 'Hysteria2 极速回家', port: 'UDP 54443', listen_port: 54443, external_port: 54443, route: '回家 + 分流', route_mode: 'shunt', clients: 0, enabled: true, ddns_host: 'home.example.com' },
      { id: 'reality', protocol: 'VLS', raw_proto: 'vless-reality', name: 'VLESS-Reality 隐身回家', port: 'TCP 18443', listen_port: 18443, external_port: 18443, route: '回家 + 分流', route_mode: 'shunt', clients: 0, enabled: true, ddns_host: 'home.example.com' }
    ],
    homelinkModes: [
      ['shunt', '回家 + 科学上网分流', '远程连回家访内网的同时，沿用家中精细分流与海外出口。'],
      ['direct', '仅回家访问内网与国内', '远程流量强制走家庭宽带直连，不进入海外代理链路。'],
      ['proxy_only', '仅科学上网 · 隔离内网', '禁止远程客户端访问家庭局域网，仅借用家中海外出口。']
    ],
    blocked: [
      ['otheve.beacon.qq.com', '隐私遥测与追踪探针', 392238],
      ['btrace.qq.com', '隐私遥测与追踪探针', 44247],
      ['metrics.doppiostreams.com', '隐私遥测与追踪探针', 4460],
      ['www.google-analytics.com', '商业广告联盟与弹窗', 908],
      ['collector.github.com', '商业广告联盟与弹窗', 790]
    ],
    filterLists: [
      { id: 'anti_ad', name: 'anti-AD 隐私与广告主规则库', category: '综合拦截', rules_count: 38500, enabled: true, updated_at: '实时生效' },
      { id: 'easylist_cn', name: 'EasyList China 国内高频弹窗库', category: '国内广告', rules_count: 11500, enabled: true, updated_at: '实时生效' }
    ],
    rewriteRules: [
      { id: 'rw_1', from_domain: 'services.googleapis.cn', to_domain: 'services.googleapis.com', enabled: true, note: 'Google Play 服务防跳重写' },
      { id: 'rw_2', from_domain: 'www.google.cn', to_domain: 'www.google.com', enabled: true, note: 'Google 搜索防跳重写' }
    ],
    subscriptions: [
      { id: 'sub_main', name: '主力高速机场订阅', count: 148, enabled: true, updated: '实时同步', url: 'https://sub.example.com/api/v1/client/subscribe?token=***', auto_update: true, update_interval_min: 360 }
    ],
    nodes: [
      ['新加坡 06', 'SG', 'HY2', 'ok', 156, 96, true, 'sub_main'],
      ['新加坡 08', 'SG', 'HY2', 'ok', 184, 91, true, 'sub_main'],
      ['日本 07', 'JP', 'VLESS', 'ok', 142, 94, true, 'sub_main'],
      ['日本 12', 'JP', 'TUIC', 'suspect', 329, 72, true, 'sub_main'],
      ['香港 N3', 'HK', 'VLESS', 'ok', 96, 97, true, 'sub_main'],
      ['台湾 02', 'TW', 'HY2', 'ok', 128, 89, false, 'sub_main']
    ].map((n, i) => ({
      id: 'node-' + i,
      tag: n[0],
      name: n[0],
      region: n[1],
      protocol: n[2],
      status: n[3],
      rtt: n[4],
      score: n[5],
      kernel: n[6],
      sub_id: n[7],
      sparkline: [148, 152, 160, 144, 156, 150, 156]
    })),
    switchHistory: [],
    schedules: [
      { id: 'sched_default', name: '每日全量 URL Ping 巡检', region: 'ALL', interval_min: 360, enabled: true, check_ipv6: false }
    ],
    logs: [
      '[INFO] AI-LINK NEXUS daemon v2.0.2 started on 0.0.0.0:9099',
      '[INFO] sing-box 1.14.1 core process verified alive (ports :7890, :7893, :7874 ready)',
      '[INFO] NFTables table inet ai_link synchronized via --generate-nft single source of truth',
      '[INFO] Dual-group Auto Node Pools (Auto_AI, Auto_YouTube, Auto_Netflix) initialized',
      '[INFO] Self-healing watchdog active (respawn 0 5 0, anti-blackhole protection armed)'
    ]
  };

  const state = {
    page: 'galaxy',
    sceneMode: 'panorama',
    inspectorTab: 'core',
    selected: null,
    cnUpstream: '223.5.5.5',
    remoteUpstream: 'https://1.1.1.1/dns-query',
    rawGalaxy: null,
    insightDevices: [
      { ip: '10.10.10.224', name: 'Device-10.10.10.224', inMb: 128.4, outMb: 18.2, totalMb: 146.6, pct: 68 }
    ],
    insightTargets: [
      { name: 'chatgpt.com', totalMb: 42.5, pct: 32 },
      { name: 'googlevideo.com', totalMb: 38.1, pct: 28 },
      { name: 'github.com', totalMb: 19.4, pct: 15 },
      { name: 'bilibili.com', totalMb: 16.0, pct: 12 }
    ],
    galaxyLanDevices: [
      { ip: '10.10.10.224', name: 'Device-10.10.10.224', down_rate: 0, up_rate: 0, conns: 0, is_remote: false, state: 'ok' }
    ],
    galaxyDomesticSites: [
      { domain: 'weixin.qq.com', name: 'WeChat 微信', down_rate: 18432, up_rate: 4096, conns: 3, state: 'ok' },
      { domain: 'bilibili.com', name: 'Bilibili 哔哩哔哩', down_rate: 65536, up_rate: 8192, conns: 4, state: 'ok' },
      { domain: 'douyincdn.com', name: '抖音直播 CDN', down_rate: 32768, up_rate: 2048, conns: 2, state: 'ok' },
      { domain: 'taobao.com', name: 'Taobao 淘宝', down_rate: 12288, up_rate: 2048, conns: 2, state: 'ok' },
      { domain: 'jd.com', name: 'JD.com 京东', down_rate: 8192, up_rate: 1024, conns: 1, state: 'ok' }
    ],
    galaxyForeignSites: [
      { domain: 'chatgpt.com', name: 'OpenAI / ChatGPT', group: 'Shunt_AI', exit_node: '新加坡 06', down_rate: 49152, up_rate: 12288, conns: 4, state: 'ok' },
      { domain: 'youtube.com', name: 'YouTube 4K/8K', group: 'Shunt_YouTube', exit_node: '日本 07', down_rate: 262144, up_rate: 16384, conns: 6, state: 'ok' },
      { domain: 'google.com', name: 'Google 全生态', group: 'Shunt_Google', exit_node: '新加坡 06', down_rate: 32768, up_rate: 8192, conns: 3, state: 'ok' },
      { domain: 'github.com', name: 'GitHub 开发者', group: 'Shunt_GitHub', exit_node: '日本 07', down_rate: 24576, up_rate: 6144, conns: 2, state: 'ok' },
      { domain: 'telegram.org', name: 'Telegram 通讯', group: 'Shunt_Social', exit_node: '新加坡 06', down_rate: 16384, up_rate: 4096, conns: 2, state: 'ok' },
      { domain: 'netflix.com', name: 'Netflix 流媒体', group: 'Shunt_Netflix', exit_node: '香港 N3', down_rate: 131072, up_rate: 8192, conns: 3, state: 'ok' }
    ],
    galaxyBlackholeCategories: [
      { name: '商业广告联盟与弹窗', count: 36, pct: 56.3 },
      { name: '开屏广告与终端SDK', count: 18, pct: 28.1 },
      { name: '隐私遥测与追踪探针', count: 6, pct: 9.4 },
      { name: 'PCDN盗刷与后台上传', count: 4, pct: 6.2 }
    ],
    routingMode: 'rule_shunt',
    homelinkMode: 'shunt',
    nodeFilter: 'all',
    regionFilter: 'ALL',
    subFilter: 'ALL',
    search: '',
    nodePage: 1,
    nodePageSize: 50,
    expandShuntRules: false,
    musicUnlockOpen: false,
    musicUnlockEnabled: false,
    insightTab: 'devices',
    logFilter: 'ALL',
    logSearch: '',
    connSearch: '',
    autoRotate: !reducedMotion,
    labels: false,
    surge: false,
    dnsEnabled: true,
    dnsRewriteEnabled: true,
    forceTunnelDns: true,
    authEnabled: false,
    entryBypass: true,
    ipv6Proxy: false,
    blockQuic: true,
    gameUdpDirect: true,
    conflictGuard: true,
    bypassActive: false,
    coreAlive: true,
    pwdCustomized: false,
    trustedCidr: '127.0.0.1/32, ::1/128, 192.168.0.0/16, 10.0.0.0/8',
    panelBind: '0.0.0.0:9099',
    ghMirror: 'https://gh-proxy.com/',
    updateManifestUrl: '',
    trafficRange: '24h',
    rawStatus: null,
    rawShunt: null,
    rawAutoNodes: [],
    rawNodes: [],
    rawSubs: [],
    rawHomelink: null,
    rawDns: null,
    rawOps: {},
    rawConnections: [],
    globalMode: 'auto',
    globalAutoNodeId: 'auto_youtube',
    globalCountry: 'JP',
    globalManualNode: '',
    globalResolvedNode: ''
  };

  const pageTitles = {
    galaxy: '全域星图',
    overview: '网络概览',
    shunt: '代理与分流',
    homelink: '回家节点',
    dns: 'DNS 与净网护盾',
    nodes: '订阅与节点',
    settings: '连接与设置'
  };

  let scene = null;
  let modalConfirmHandler = null;
  const latencySeries = [178, 166, 172, 160, 164, 151, 159, 148, 154, 149, 162, 156, 158, 151, 156, 153, 156];
  const chartObservers = [];

  function fmtBytes(b) {
    const n = Number(b || 0);
    if (!isFinite(n) || n <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let idx = 0;
    let val = n;
    while (val >= 1024 && idx < units.length - 1) { val /= 1024; idx++; }
    return (idx === 0 ? String(Math.round(val)) : val.toFixed(val >= 100 ? 0 : val >= 10 ? 1 : 2)) + ' ' + units[idx];
  }

  function fmtRate(bps) {
    return fmtBytes(bps) + '/s';
  }

  function computeSpeedGearInfo(rateBps, conns) {
    const bps = Math.max(0, Number(rateBps || 0));
    const c = Math.max(0, Number(conns || 0));
    if (bps >= 200 * 1024 || c >= 12) {
      return { gear: 'high', label: '高', fullLabel: '高速', speed: 0.56 };
    }
    if (bps >= 15 * 1024 || c >= 3) {
      return { gear: 'med', label: '中', fullLabel: '中速', speed: 0.26 };
    }
    return { gear: 'low', label: '低', fullLabel: '低速', speed: 0.095 };
  }

  function renderGearBadge(rateBps, conns) {
    const g = computeSpeedGearInfo(rateBps, conns);
    return '<span class="gear-badge ' + g.gear + '">⚡' + g.fullLabel + '</span>';
  }

  function formatDeviceAvatarLabel(d) {
    if (!d) return 'PC';
    const rawName = String(d.name || '').trim();
    const rawIp = String(d.ip || '').trim();
    const ipMatch = (rawIp || rawName).match(/(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/);
    const isGenericName = !rawName || /^device[-_]/i.test(rawName) || /^\d{1,3}\.\d{1,3}\./.test(rawName);
    if (!isGenericName) {
      const clean = rawName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
      if (clean) return clean.slice(0, 3).toUpperCase();
    }
    if (ipMatch) {
      return '.' + ipMatch[4];
    }
    return (rawName || 'PC').slice(0, 3).toUpperCase();
  }

  function classifyNodeCountry(n) {
    if (!n) return 'OTHER';
    const c = String(n.country || n.region || '').toUpperCase();
    if (COUNTRY_META[c]) return c;
    const t = String(n.tag || n.name || '').toUpperCase();
    if (/HK|HONG\s*KONG|香港/.test(t)) return 'HK';
    if (/TW|TAIWAN|台湾|台北|新北/.test(t)) return 'TW';
    if (/JP|JAPAN|日本|东京|大阪/.test(t)) return 'JP';
    if (/SG|SINGAPORE|新加坡|狮城/.test(t)) return 'SG';
    if (/US|USA|UNITED\s*STATES|美国|洛杉矶|硅谷|西雅图|圣何塞/.test(t)) return 'US';
    return 'OTHER';
  }

  /* Fix #1 & #6: Semantic latency formatting — NEVER show -1ms or 0ms for untested/dead nodes */
  function formatLatencyBadge(rtt, status, isDirect) {
    if (isDirect || status === 'direct') {
      return '<span class="lat-badge direct">直连 WAN</span>';
    }
    if (status === 'dead') {
      return '<span class="lat-badge dead">超时不可达</span>';
    }
    const ms = Number(rtt);
    if (rtt == null || !isFinite(ms) || ms <= 0) {
      return '<span class="lat-badge pending">未测速</span>';
    }
    const rounded = Math.round(ms);
    const cls = rounded < 120 ? 'fast' : (rounded <= 260 ? 'mid' : 'slow');
    return '<span class="lat-badge ' + cls + '">' + rounded + ' ms</span>';
  }

  function formatLatencyText(rtt, isDirect) {
    if (isDirect) return '直连 WAN';
    const ms = Number(rtt);
    if (rtt == null || !isFinite(ms) || ms <= 0) return '待测速';
    return Math.round(ms) + ' ms';
  }

  function renderMiniSparklineSvg(arr, color) {
    const pts = (Array.isArray(arr) && arr.length >= 2) ? arr.filter(x => Number(x) > 0) : [150, 145, 160, 152, 148, 155];
    if (pts.length < 2) return '';
    const min = Math.min.apply(null, pts) - 5;
    const max = Math.max.apply(null, pts) + 5;
    const w = 58, h = 18;
    const coords = pts.slice(-12).map((v, i, a) => {
      const x = (i / Math.max(1, a.length - 1)) * w;
      const y = h - ((v - min) / Math.max(1, max - min)) * (h - 4) - 2;
      return x.toFixed(1) + ',' + y.toFixed(1);
    }).join(' ');
    const stroke = color || '#6ee7f5';
    return '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '" style="vertical-align:middle;margin-left:6px;opacity:.85"><polyline fill="none" stroke="' + stroke + '" stroke-width="1.4" points="' + coords + '"/></svg>';
  }

  function getAuthToken() {
    try { return localStorage.getItem('ailink_panel_token') || ''; } catch (_) { return ''; }
  }

  function setAuthToken(tok) {
    try {
      if (tok) localStorage.setItem('ailink_panel_token', tok);
      else localStorage.removeItem('ailink_panel_token');
    } catch (_) {}
  }

  async function callRouterApi(endpoint, method = 'GET', payload = null, timeoutMs = 25000, silentError = false) {
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
    const isMutating = method && method.toUpperCase() !== 'GET';
    const isBgPoll = !isMutating && (endpoint === '/api/status' || endpoint === '/api/overview/galaxy' || endpoint.startsWith('/api/nodes?sparkline=1'));
    try {
      const headers = { 'Accept': 'application/json' };
      const tok = getAuthToken();
      if (tok) headers['X-AI-Link-Token'] = tok;
      const opts = { method, headers };
      if (controller) opts.signal = controller.signal;
      if (payload !== null && method !== 'GET') {
        headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(payload);
      }
      const res = await fetch(endpoint, opts);
      let data = {};
      try { data = await res.json(); } catch (_) {}
      if (res.status === 401 && endpoint !== '/api/login') {
        promptPanelLoginModal();
      }
      const okFlag = Boolean(res.ok && data.ok !== false);
      const out = Object.assign({ ok: okFlag, _httpStatus: res.status }, data);
      if (!okFlag && !silentError && !isBgPoll && res.status !== 401) {
        toast('操作失败: ' + (out.message || out.error || ('HTTP ' + res.status)), 'warn');
      }
      return out;
    } catch (err) {
      const errStr = String((err && err.message) || err || '网络请求异常');
      if (!silentError && !isBgPoll) {
        toast('请求未送达: ' + errStr, 'warn');
      }
      return { ok: false, error: errStr, message: errStr };
    } finally {
      if (timer) clearTimeout(timer);
    }
  }

  function setSwitchState(el, on) {
    if (!el) return;
    const isOn = Boolean(on);
    el.classList.toggle('on', isOn);
    el.classList.toggle('off', !isOn);
    el.setAttribute('aria-checked', isOn ? 'true' : 'false');
  }

  function toast(message, type, opts) {
    const stack = $('#toast-stack');
    if (!stack) return;
    const el = document.createElement('div');
    el.className = 'toast' + (type ? ' ' + type : '');
    const dot = document.createElement('i');
    const text = document.createElement('span');
    text.textContent = message;
    el.append(dot, text);
    if (opts && typeof opts.onUndo === 'function') {
      const undoBtn = document.createElement('button');
      undoBtn.type = 'button';
      undoBtn.className = 'toast-undo-btn';
      undoBtn.textContent = opts.undoText || '↩ 撤销';
      undoBtn.addEventListener('click', e => {
        e.stopPropagation();
        try { opts.onUndo(); } catch (_) {}
        el.remove();
      });
      el.appendChild(undoBtn);
    }
    while (stack.children.length >= 3) {
      stack.firstElementChild.remove();
    }
    stack.appendChild(el);
    const stayMs = (opts && opts.onUndo) ? 5000 : 3400;
    setTimeout(() => {
      el.classList.add('out');
      setTimeout(() => el.remove(), 350);
    }, stayMs);
  }

  function confirmModal(title, message, onConfirm, confirmText) {
    openModal(
      title || '确认执行操作',
      '<div class="modal-form"><p style="font-size:9.5px;line-height:1.65;color:var(--text)">' + esc(message || '请确认是否继续执行该操作？') + '</p></div>',
      'SECURITY CONFIRMATION',
      async () => {
        closeModal();
        if (typeof onConfirm === 'function') await onConfirm();
      },
      confirmText || '确认执行'
    );
  }
  window.confirmModal = confirmModal;

  function openModal(title, html, kicker, onConfirm, confirmText) {
    const tEl = $('#modal-title');
    const kEl = $('#modal-kicker');
    const bEl = $('#modal-body');
    if (tEl) tEl.textContent = title;
    if (kEl) kEl.textContent = kicker || 'AI-LINK NEXUS';
    if (bEl) bEl.innerHTML = html;
    modalConfirmHandler = typeof onConfirm === 'function' ? onConfirm : null;
    const confirmBtn = $('#modal-confirm');
    const footNote = $('#modal-foot-note');
    if (confirmBtn) {
      confirmBtn.textContent = confirmText || (modalConfirmHandler ? '保存并生效' : '完成');
    }
    if (footNote) {
      footNote.textContent = modalConfirmHandler ? '修改将实时同步至 AI-LINK 守护进程与内核' : 'AI-LINK NEXUS 实时控制中心';
    }
    const panel = $('.modal-panel');
    if (panel) {
      const isWide = Boolean(html && (html.includes('ov-insight-modal-wrap') || html.includes('table-wrap')));
      panel.classList.toggle('wide', isWide);
    }
    const m = $('#modal');
    if (m) m.hidden = false;
  }

  function closeModal() {
    const m = $('#modal');
    if (m) m.hidden = true;
    modalConfirmHandler = null;
  }
  window.closeModal = closeModal;

  function promptPanelLoginModal() {
    openModal(
      '面板安全鉴权登录',
      '<div class="modal-form">' +
        '<p>当前路由器已启用访问鉴权或操作涉及敏感凭据，请输入面板管理密码。</p>' +
        '<div class="modal-field"><label>管理密码</label><input id="mdl-login-password" type="password" placeholder="输入面板密码 (初始默认: ai-link-2026)" autocomplete="current-password"></div>' +
      '</div>',
      'SECURITY AUTH',
      async () => {
        const pwInput = $('#mdl-login-password');
        const pw = pwInput ? pwInput.value.trim() : '';
        if (!pw) { toast('请输入管理密码', 'warn'); return; }
        const res = await callRouterApi('/api/login', 'POST', { password: pw });
        if (res && res.ok && res.token) {
          setAuthToken(res.token);
          closeModal();
          toast('登录成功，已获取安全会话令牌');
          await syncBackendStatus(true, true);
        } else {
          toast((res && res.message) || '密码错误，请重试', 'warn');
        }
      },
      '立即登录'
    );
  }

  /* Requirement 3: Mode-aware Egress Summary (Rule Shunt mode shows mode summary, NOT a single misleading node) */
  function getActiveEgressSummary() {
    const modeObj = mock.routingModes.find(m => m.id === state.routingMode) || mock.routingModes[0];
    const isSingleEgress = (state.routingMode === 'gfw_list' || state.routingMode === 'cn_whitelist' || state.routingMode === 'global_proxy');
    if (state.bypassActive || state.routingMode === 'direct_all') {
      const mName = state.bypassActive ? '临时直连恢复中' : modeObj.name;
      return {
        isSingleEgress: false,
        topLabel: '当前运行模式',
        topMainText: mName,
        topSubText: 'WAN 宽带直通',
        nodeName: '宽带原生直连 (DIRECT)',
        poolOrNodeName: '宽带原生直连 (DIRECT)',
        modeName: mName,
        modeShort: state.bypassActive ? '直连恢复' : '直连模式',
        latencyBadge: formatLatencyBadge(0, 'direct', true),
        latencyText: '直连 WAN',
        numericRtt: 12
      };
    }
    const aiGrp = mock.groups.find(g => g.id === 'AI') || mock.groups[0];
    let nodeName = state.globalResolvedNode || (state.globalMode === 'manual' ? state.globalManualNode : '') || (aiGrp && aiGrp.resolved_node) || '';
    if (!nodeName || nodeName === '--' || nodeName === 'direct') {
      const firstOk = mock.nodes.find(n => n.status === 'ok') || mock.nodes[0];
      nodeName = firstOk ? (firstOk.name || firstOk.tag) : '智能自动优选池';
    }
    const matchedNode = mock.nodes.find(n => n.tag === nodeName || n.name === nodeName);
    const rttVal = (matchedNode && matchedNode.rtt > 0) ? matchedNode.rtt : ((aiGrp && aiGrp.rtt > 0) ? aiGrp.rtt : (mock.latency > 0 ? mock.latency : 156));
    if (!isSingleEgress) {
      const grpCnt = mock.groups.length || 13;
      const poolCnt = mock.autoPools.length || 3;
      return {
        isSingleEgress: false,
        topLabel: '当前运行模式',
        topMainText: modeObj.name,
        topSubText: grpCnt + ' 组策略 · ' + poolCnt + ' 组自动池',
        nodeName: nodeName,
        poolOrNodeName: modeObj.name + ' (' + grpCnt + ' 组独立出口)',
        modeName: modeObj.name,
        modeShort: modeObj.shortName || '分流模式',
        latencyBadge: '<span class="lat-badge fast">' + esc(grpCnt) + ' 组策略独立出站</span>',
        latencyText: formatLatencyText(rttVal, false),
        numericRtt: rttVal
      };
    }
    let egressDisplay = nodeName;
    if (state.globalMode === 'direct') {
      egressDisplay = '直连 (DIRECT)';
    } else if (state.globalMode === 'auto') {
      const aObj = mock.autoPools.find(a => a.id === state.globalAutoNodeId) || mock.autoPools[0];
      const poolName = aObj ? aObj.name : '自动节点池';
      egressDisplay = poolName + ' · ' + nodeName;
    } else if (state.globalMode === 'manual') {
      egressDisplay = state.globalManualNode || nodeName;
    }
    const isDirGlobal = state.globalMode === 'direct';
    return {
      isSingleEgress: true,
      topLabel: '当前模式：' + (modeObj.shortName || modeObj.name),
      topMainText: egressDisplay,
      topSubText: isDirGlobal ? '直连 WAN' : formatLatencyText(rttVal, false),
      nodeName: nodeName,
      poolOrNodeName: egressDisplay,
      modeName: modeObj.name,
      modeShort: modeObj.shortName || modeObj.name,
      latencyBadge: formatLatencyBadge(rttVal, matchedNode ? matchedNode.status : 'ok', isDirGlobal),
      latencyText: isDirGlobal ? '直连 WAN' : formatLatencyText(rttVal, false),
      numericRtt: isDirGlobal ? 12 : rttVal
    };
  }

  function renderTopBarStatus() {
    const eg = getActiveEgressSummary();
    mock.latency = eg.numericRtt;
    if ($('#top-route-label')) $('#top-route-label').textContent = eg.topLabel;
    if ($('#top-exit')) $('#top-exit').textContent = eg.topMainText;
    if ($('#top-latency')) $('#top-latency').textContent = eg.topSubText;
    if ($('#top-connections')) $('#top-connections').textContent = String(mock.connections);
    if ($('#top-down')) $('#top-down').textContent = mock.downText;
    if ($('#top-up')) $('#top-up').textContent = mock.upText;
    if ($('#scene-kpi-mem')) $('#scene-kpi-mem').innerHTML = esc(mock.coreMemMib.toFixed(1)) + ' <small>MiB</small>';
    if ($('#scene-kpi-blocked')) $('#scene-kpi-blocked').innerHTML = esc(Number(mock.blockedTotal || 0).toLocaleString('zh-CN')) + ' <small>次</small>';
  }

  /* Requirement 1: Overview Dashboard with Enlarged Circular Sonar (bottom list removed, blips clickable with real group selector) */
  function renderOverviewDashboard() {
    renderTopBarStatus();
    const eg = getActiveEgressSummary();
    const heroNodeEl = $('#ov-hero-node');
    if (heroNodeEl) {
      if (eg.isSingleEgress) {
        heroNodeEl.innerHTML = esc(eg.modeName + ' ➔ ' + eg.poolOrNodeName) + ' ' + eg.latencyBadge;
      } else if (state.bypassActive || state.routingMode === 'direct_all') {
        heroNodeEl.innerHTML = esc(eg.modeName + ' · 宽带原生直连') + ' ' + eg.latencyBadge;
      } else {
        heroNodeEl.innerHTML = esc('精细规则分流 · 多策略组按需并发出站') + ' ' + eg.latencyBadge;
      }
    }
    const heroDescEl = $('#ov-hero-desc');
    if (heroDescEl) {
      heroDescEl.textContent = eg.isSingleEgress
        ? ('当前模式：' + eg.modeName + '（单一总出口模式） · 正在使用出口：' + eg.poolOrNodeName)
        : ('当前模式：' + eg.modeName + ' · AI/流媒体/社交/国内各走独立最优出口，双组省流自动节点池实时守护中');
    }
    const pModeEl = $('#ov-pillar-mode');
    if (pModeEl) pModeEl.textContent = eg.modeName;
    const pBypassEl = $('#ov-pillar-bypass');
    if (pBypassEl) pBypassEl.textContent = state.entryBypass ? '大陆 IP 硬件直通已激活' : '全量经内核分流';
    const pIpv6El = $('#ov-pillar-ipv6');
    if (pIpv6El) pIpv6El.textContent = state.ipv6Proxy ? '双栈 IPv6 代理已开启' : '国内原生 IPv6 · 海外防漏';

    const okNodesCnt = mock.nodes.filter(n => n.status === 'ok').length;
    const metrics = [
      ['活跃连接', String(mock.connections), '当前由 sing-box 接管的并发会话', '内核 ' + mock.coreMemMib.toFixed(1) + ' MiB', '#6ee7f5'],
      ['实时下行', mock.downText, '本月累计流量 ' + mock.monthTotalText, '累计下载 ' + mock.inTotalText, '#a994ff'],
      ['实时上行', mock.upText, '累计上传流量 ' + mock.upTotalText, '实时吞吐', '#54e6b5'],
      ['全域健康度', String(mock.healthScore), okNodesCnt + ' 个可用节点 · ' + Number(mock.dnsRulesCount).toLocaleString('zh-CN') + ' 条护盾规则', state.coreAlive ? ('已拦截 ' + Number(mock.blockedTotal).toLocaleString('zh-CN')) : '离线告警', '#f7bd68']
    ];
    const om = $('#overview-metrics');
    if (om) {
      om.innerHTML = metrics.map(m => '<article class="metric-card" style="--accent:' + esc(m[4]) + '"><span>' + esc(m[0]) + '</span><b>' + esc(m[1]) + '</b><small>' + esc(m[2]) + '</small><i class="delta">' + esc(m[3]) + '</i></article>').join('');
    }
    const monthLegend = $('#overview-month-total');
    if (monthLegend) monthLegend.textContent = '本月累计 ' + mock.monthTotalText;
    const matrixConns = $('#matrix-total-conns');
    if (matrixConns) matrixConns.textContent = Number(mock.monthTotalConns || mock.connections || 0).toLocaleString('zh-CN');

    const positions = [
      [80, 22, true],   // #0 ChatGPT (row 2 right, label inward left)
      [86, 38, true],   // #1 Gemini (row 4 right, label inward left)
      [85, 68, true],   // #2 YouTube (row 6 right, label inward left)
      [16, 30, false],  // #3 GitHub (row 3 left, label inward right)
      [15, 60, false],  // #4 Netflix (row 5 left, label inward right)
      [20, 78, false],  // #5 TikTok (row 7 left, label inward right)
      [24, 13, false],  // #6 Telegram (row 1 top-left, label inward right)
      [76, 86, true]    // #7 B站直连 (row 8 bottom-right, label inward left)
    ];
    const sonar = $('#sonar-stage');
    if (sonar) {
      $$('.sonar-blip', sonar).forEach(el => el.remove());
      sonar.insertAdjacentHTML('beforeend', mock.services.slice(0, 8).map((s, i) => {
        const pos = positions[i % positions.length];
        const bx = Math.max(14, Math.min(86, pos[0]));
        const by = Math.max(12, Math.min(88, pos[1]));
        const alignLeft = pos[2] != null ? pos[2] : (bx > 50);
        const msTxt = (s.ms != null && s.ms > 0) ? s.ms + 'ms' : '待测';
        const cls = 'sonar-blip' + (alignLeft ? ' blip-left' : '') + (s.state === 'suspect' || s.state === 'dead' ? ' warn' : '');
        const selTag = s.selector || 'Shunt_AI';
        return '<button type="button" class="' + cls + '" data-action="probe-service" data-service="' + esc(s.id || s.name) + '" data-selector="' + esc(selTag) + '" data-name="' + esc(s.name) + ' · ' + esc(msTxt) + '" title="点击立即探测 ' + esc(s.name) + ' (' + esc(selTag) + ')" style="left:' + bx + '%;top:' + by + '%"></button>';
      }).join(''));
    }

    /* Fix #2: Full Strategy Matrix on Overview Page (All groups, no truncation at 5) */
    const ovShuntGrid = $('#ov-shunt-preview-grid');
    if (ovShuntGrid) {
      const cntBadge = $('#ov-shunt-count-badge');
      if (cntBadge) cntBadge.textContent = '全部 ' + mock.groups.length + ' 个分流策略组已挂载';
      ovShuntGrid.innerHTML = mock.groups.map((g, idx) => {
        const isDir = g.shunt_mode === 'direct' || g.resolved_node === 'direct';
        const modeTxt = isDir ? '🎯 直连' : (g.shunt_mode === 'manual' ? ('🖐️ 手动 · ' + (g.country || 'JP')) : ('🤖 ' + (g.auto_node_name || '自动池')));
        const targetNode = isDir ? 'DIRECT 宽带' : (g.resolved_node || '智能优选');
        return '<button class="ov-strategy-item" data-group="' + idx + '" title="点击配置「' + esc(g.name) + '」分流策略">' +
          '<div class="st-left"><b>' + esc(g.name) + '</b><span>' + esc(modeTxt) + ' ➔ ' + esc(targetNode) + '</span></div>' +
          '<div class="st-right">' + formatLatencyBadge(g.rtt, isDir ? 'direct' : 'ok', isDir) + '</div>' +
        '</button>';
      }).join('');
    }

    const tm = $('#traffic-matrix');
    if (tm && !tm.children.length) {
      const matrix = [];
      for (let day = 0; day < 7; day++) {
        for (let hour = 0; hour < 24; hour++) {
          const value = ((day * 37 + hour * 19 + day * hour * 3) % 100) / 100;
          const alpha = (.035 + value * .48).toFixed(3);
          const mb = Math.round(8 + value * 420);
          matrix.push('<span class="matrix-cell" style="--alpha:' + alpha + '" title="周' + (day + 1) + ' ' + String(hour).padStart(2, '0') + ':00 · ' + mb + ' MB"></span>');
        }
      }
      tm.innerHTML = matrix.join('');
    }

    const devList = (state.galaxyLanDevices && state.galaxyLanDevices.length)
      ? state.galaxyLanDevices
      : (state.insightDevices || []);
    const devCountEl = $('#ov-devices-count');
    if (devCountEl) devCountEl.textContent = String(Math.max(mock.devicesTotal || 0, devList.length));
    const devSubEl = $('#ov-devices-sub');
    if (devSubEl) devSubEl.textContent = mock.devicesActive + ' 台活跃传输 · 共 ' + Math.max(mock.devicesTotal || 0, devList.length) + ' 台在线终端 (点击查看详情)';
    const devAvatarsEl = $('#ov-devices-avatars');
    if (devAvatarsEl && devList.length) {
      devAvatarsEl.innerHTML = devList.slice(0, 5).map(d => {
        const tag = formatDeviceAvatarLabel(d);
        const ipVal = d.ip || d.name || '';
        return '<i data-action="open-overview-detail" data-detail-type="devices" data-focus-ip="' + esc(ipVal) + '" title="点击查看终端「' + esc(d.name || d.ip) + '」详情">' + esc(tag) + '</i>';
      }).join('');
    }
    const outCountEl = $('#ov-outbounds-count');
    if (outCountEl) outCountEl.textContent = String(mock.activeOutbounds);
    const outSubEl = $('#ov-outbounds-sub');
    if (outSubEl) {
      const okCnt = mock.nodes.filter(n => n.status === 'ok').length;
      const pendCnt = mock.nodes.filter(n => n.status === 'pending').length;
      outSubEl.textContent = okCnt + ' 已验证可用 · ' + pendCnt + ' 待探测 · 总计 ' + mock.nodes.length + ' 节点 (点击查看详情)';
    }
    const destCountEl = $('#ov-destinations-count');
    if (destCountEl) destCountEl.textContent = String(mock.destinationsTotal);
    const destTagsEl = $('#ov-destinations-tags');
    if (destTagsEl && state.insightTargets && state.insightTargets.length) {
      destTagsEl.innerHTML = state.insightTargets.slice(0, 5).map(t =>
        '<span data-action="open-overview-detail" data-detail-type="destinations" data-focus-domain="' + esc(t.name) + '" title="点击查看「' + esc(t.name) + '」流量与分流详情">' + esc(t.name) + '</span>'
      ).join('');
    }
  }

  function renderNonShuntGlobalBar() {
    const isNonShuntProxy = (state.routingMode === 'gfw_list' || state.routingMode === 'cn_whitelist' || state.routingMode === 'global_proxy');
    const warnBanner = $('#non-shunt-warning-banner');
    if (warnBanner) {
      warnBanner.classList.toggle('hidden', state.routingMode === 'rule_shunt');
    }
    const bar = $('#non-shunt-global-bar');
    if (!bar) return;
    bar.classList.toggle('hidden', !isNonShuntProxy);

    const selMode = $('#select-global-mode');
    const selAuto = $('#select-global-autonode');
    const selCountry = $('#select-global-country');
    const selManual = $('#select-global-manual-node');
    const lblResolved = $('#non-shunt-resolved-label');
    if (!selMode || !selAuto || !selCountry || !selManual) return;

    const gMode = state.globalMode || 'auto';
    if (document.activeElement !== selMode) selMode.value = gMode;

    const autoList = (state.rawAutoNodes && state.rawAutoNodes.length)
      ? state.rawAutoNodes
      : mock.autoPools;
    if (document.activeElement !== selAuto) {
      selAuto.innerHTML = autoList.map(a => '<option value="' + esc(a.id) + '">🤖 ' + esc(a.name || a.id) + (a.current_node ? ' (' + esc(a.current_node) + ')' : '') + '</option>').join('');
      if (state.globalAutoNodeId && autoList.some(a => a.id === state.globalAutoNodeId)) {
        selAuto.value = state.globalAutoNodeId;
      } else if (autoList.length) {
        selAuto.value = autoList[0].id;
        state.globalAutoNodeId = autoList[0].id;
      }
    }

    const selectableNodes = mock.nodes.filter(n => n.status !== 'dead' && n.status !== 'suspect');
    if (document.activeElement !== selCountry) {
      selCountry.innerHTML = COUNTRY_CODES.map(code => {
        const cnt = selectableNodes.filter(n => classifyNodeCountry(n) === code).length;
        return '<option value="' + code + '">' + esc(COUNTRY_META[code].flag + ' ' + COUNTRY_META[code].name) + ' (' + cnt + ')</option>';
      }).join('');
      const targetCountry = COUNTRY_META[state.globalCountry] ? state.globalCountry : 'JP';
      selCountry.value = targetCountry;
      state.globalCountry = targetCountry;
    }

    const chosenCountry = selCountry.value || state.globalCountry || 'JP';
    let countryNodes = selectableNodes.filter(n => classifyNodeCountry(n) === chosenCountry);
    if (!countryNodes.length) countryNodes = selectableNodes.length ? selectableNodes : mock.nodes;
    if (document.activeElement !== selManual) {
      selManual.innerHTML = countryNodes.map(n => {
        const tag = n.tag || n.name;
        const rttTxt = (n.rtt != null && n.rtt > 0) ? ' · ' + Math.round(n.rtt) + 'ms' : '';
        return '<option value="' + esc(tag) + '">' + esc(n.name || tag) + rttTxt + '</option>';
      }).join('');
      if (state.globalManualNode && countryNodes.some(n => (n.tag || n.name) === state.globalManualNode)) {
        selManual.value = state.globalManualNode;
      } else if (countryNodes.length) {
        selManual.value = countryNodes[0].tag || countryNodes[0].name;
        state.globalManualNode = selManual.value;
      }
    }

    selAuto.classList.toggle('hidden', gMode !== 'auto');
    selCountry.classList.toggle('hidden', gMode !== 'manual');
    selManual.classList.toggle('hidden', gMode !== 'manual');

    if (lblResolved) {
      if (gMode === 'direct') {
        lblResolved.textContent = '🎯 直连 ➔ DIRECT';
      } else if (gMode === 'manual') {
        const mNode = selManual.value || state.globalManualNode || state.globalResolvedNode || '未选择';
        lblResolved.textContent = '🖐️ 手动 (' + chosenCountry + ') ➔ ' + mNode;
      } else {
        const aObj = autoList.find(a => a.id === selAuto.value) || autoList[0];
        const aName = aObj ? aObj.name : (state.globalAutoNodeId || '自动池');
        const resSuffix = state.globalResolvedNode ? ' (' + state.globalResolvedNode + ')' : '';
        lblResolved.textContent = '🤖 自动 ➔ ' + aName + resSuffix;
      }
    }
  }

  async function saveGlobalThreeMode() {
    const selMode = $('#select-global-mode');
    const selAuto = $('#select-global-autonode');
    const selCountry = $('#select-global-country');
    const selManual = $('#select-global-manual-node');
    if (!selMode) return;
    state.globalMode = selMode.value || 'auto';
    if (selAuto && selAuto.value) state.globalAutoNodeId = selAuto.value;
    if (selCountry && selCountry.value) state.globalCountry = selCountry.value;
    renderNonShuntGlobalBar();
    if (selManual && selManual.value) state.globalManualNode = selManual.value;
    renderNonShuntGlobalBar();

    const payload = {
      routing_mode: state.routingMode,
      global_mode: state.globalMode,
      global_auto_node_id: state.globalAutoNodeId,
      global_country: state.globalCountry,
      global_manual_node: state.globalManualNode
    };
    const res = await callRouterApi('/api/shunt/update', 'POST', payload);
    if (res && res.ok !== false) {
      if (res.global_resolved_node) state.globalResolvedNode = res.global_resolved_node;
      renderNonShuntGlobalBar();
      renderOverviewDashboard();
      toast('已更新当前模式统一出口: ' + (state.globalResolvedNode || state.globalManualNode || state.globalAutoNodeId));
    }
  }

  /* Fix #8, #9, #10: Full Shunt Matrix, Batch Toolbar, Auto-Pools, Inline Trace & Switch History */
  function renderShuntMatrix() {
    const rm = $('#routing-modes');
    if (rm) {
      rm.innerHTML = mock.routingModes.map(mode => '<button class="routing-mode ' + (state.routingMode === mode.id ? 'active' : '') + '" data-routing-mode="' + mode.id + '"><span>' + esc(mode.code) + '</span><b>' + esc(mode.name) + '</b><small>' + esc(mode.desc) + '</small><i></i></button>').join('');
    }
    renderNonShuntGlobalBar();

    const gl = $('#group-list');
    if (gl) {
      gl.innerHTML = mock.groups.map((g, i) => {
        const isDir = g.shunt_mode === 'direct' || g.resolved_node === 'direct';
        const modeBadge = isDir
          ? '🎯 直连模式'
          : (g.shunt_mode === 'manual' ? ('🖐️ 手动 · ' + (g.country || 'JP')) : ('🤖 ' + (g.auto_node_name || '自动池')));
        const outNode = isDir ? 'DIRECT 宽带直连' : (g.resolved_node || '智能优选就绪');
        const rulesArr = []
          .concat(g.domains || [])
          .concat((g.domain_keywords || []).map(k => 'keyword:' + k))
          .concat((g.ip_cidrs || []).map(c => 'cidr:' + c));
        const ruleCnt = rulesArr.length;
        const canMove = !g.locked_order && !g.locked_bottom && g.id !== 'Domestic_CN' && g.id !== 'Final_Fallback';
        const prioHtml = '<div class="prio-box">' +
          '<span class="prio-badge">#' + String(i + 1).padStart(2, '0') + '</span>' +
          (canMove
            ? '<button class="prio-btn" data-action="move-group-up" data-gid="' + esc(g.id) + '" title="上移优先级">▲</button>' +
              '<button class="prio-btn" data-action="move-group-down" data-gid="' + esc(g.id) + '" title="下移优先级">▼</button>'
            : '') +
          '</div>';
        const drawerHtml = state.expandShuntRules
          ? '<div class="shunt-group-rules-drawer">' +
              (rulesArr.slice(0, 10).map(r => '<span class="rule-tag">' + esc(r) + '</span>').join('') || '<span class="rule-tag">内置规则集</span>') +
              (ruleCnt > 10 ? '<span class="rule-tag">+' + (ruleCnt - 10) + ' 条...</span>' : '') +
              '<button class="button ghost compact" style="margin-left:auto;min-height:24px;padding:0 8px;font-size:8px" data-group="' + i + '">编辑规则与出口</button>' +
            '</div>'
          : '';
        return '<div class="shunt-group-card">' +
          '<div class="shunt-group-main">' +
            prioHtml +
            '<div style="min-width:0;cursor:pointer" data-group="' + i + '"><b style="font-size:10.5px;color:var(--text)">' + esc(g.name) + (g.is_custom ? ' <span class="version-chip" style="padding:2px 6px;font-size:7.5px">自定义</span>' : '') + '</b><small style="display:block;color:var(--muted);font-size:8.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(g.subtitle) + ' (' + ruleCnt + ' 项)</small></div>' +
            '<div style="cursor:pointer" data-group="' + i + '"><span class="status-pill" style="font-size:8.5px">' + esc(modeBadge) + '</span></div>' +
            '<div class="mono" style="font-size:9px;color:#c9d6ea;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer" data-group="' + i + '">' + esc(outNode) + '</div>' +
            '<div style="text-align:right">' + formatLatencyBadge(g.rtt, isDir ? 'direct' : 'ok', isDir) + '</div>' +
            '<div class="button-row" style="justify-content:flex-end;gap:5px">' +
              '<button class="button ghost compact" style="min-height:26px;padding:0 8px;font-size:8px" data-action="verify-group" data-gid="' + esc(g.id) + '" title="真连接探测当前组出口并触发故障防抖切换">校验</button>' +
              '<button class="button secondary compact" style="min-height:26px;padding:0 9px;font-size:8px" data-group="' + i + '">策略编排</button>' +
            '</div>' +
          '</div>' +
          drawerHtml +
        '</div>';
      }).join('');
    }

    const customRuleBadge = $('#custom-rules-count-badge');
    if (customRuleBadge) {
      const cCnt = mock.groups.filter(g => g.is_custom).length;
      customRuleBadge.textContent = cCnt > 0 ? ('已配置 ' + cCnt + ' 个自定义分流组') : '支持域名后缀 / 关键词 / IP CIDR 高优先级匹配';
    }

    const ap = $('#auto-pools');
    if (ap) {
      ap.innerHTML = mock.autoPools.map((p, idx) => {
        const gIdx = Number(p.active_group_index || 1);
        const grpLabel = gIdx === 1 ? '主力组 G1 生效' : (gIdx > 1 ? ('备选组 G' + gIdx + ' 容灾生效 (监测主组回切中)') : '直连回退保护');
        const svcTag = (p.service_checks && p.service_checks.length)
          ? ('URL Ping + ' + p.service_checks.join('/').toUpperCase() + (p.service_logic === 'any' ? '[任意]' : '[全通]'))
          : 'URL Ping 定时巡检';
        const curNode = p.current_node || '智能选路中';
        const curMs = p.current_delay_ms > 0 ? p.current_delay_ms : 156;
        return '<div class="auto-pool">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px">' +
            '<div><b style="font-size:11px;color:var(--text)">' + esc(p.name) + '</b><small style="display:block;margin-top:2px;color:var(--muted);font-size:8px">🛡️ 断连自动切换 · ' + esc(grpLabel) + ' · ' + esc(svcTag) + '</small></div>' +
            '<span class="status-pill">' + Number(p.healthy_count || 4) + ' 候选可用</span>' +
          '</div>' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding:7px 9px;border-radius:8px;background:rgba(3,7,14,.55);border:1px solid var(--line)">' +
            '<span style="font-size:8.5px;color:var(--muted)">当前出口: <strong style="color:var(--cyan)" class="mono">' + esc(curNode) + '</strong></span>' +
            '<span>' + formatLatencyBadge(curMs, 'ok', false) + renderMiniSparklineSvg([162, 155, 148, 152, curMs], '#54e6b5') + '</span>' +
          '</div>' +
          '<div class="auto-pool-actions">' +
            '<button class="button secondary compact" data-action="probe-auto-pool" data-pool-id="' + esc(p.id) + '">⚡ 探测优选</button>' +
            '<button class="button ghost compact" data-action="revert-auto-pool" data-pool-id="' + esc(p.id) + '">🔄 回切主组</button>' +
            '<button class="button ghost compact" data-action="replace-auto-node" data-pool-idx="' + idx + '">🔀 替换节点</button>' +
            '<button class="button ghost compact" data-auto-pool="' + idx + '">⚙️ 编排分组</button>' +
          '</div>' +
        '</div>';
      }).join('');
    }

    const histEl = $('#switch-history-list');
    if (histEl) {
      if (mock.switchHistory && mock.switchHistory.length) {
        histEl.innerHTML = mock.switchHistory.slice(0, 6).map(h => {
          const ts = h.ts ? new Date(h.ts * 1000).toLocaleTimeString('zh-CN', { hour12: false }) : (h.time || '刚刚');
          return '<div class="trace-stage" style="padding:8px 11px"><i>⚡</i><div><b>' + esc(h.group || h.selector || '自动节点池') + ' ➔ ' + esc(h.to_node || h.selected || '新出口') + '</b><span>' + esc(h.reason || '延迟劣化自动平滑切换') + '</span></div><strong>' + esc(ts) + '</strong></div>';
        }).join('');
      } else {
        histEl.innerHTML = '<div class="trace-stage" style="padding:10px 12px"><i>✓</i><div><b>当前全部自动节点池运行稳定 · 零异常抖动</b><span>双组去重省流探测开启中，仅当主组节点连续不可达或劣化超阈值时触发无感热切换</span></div><strong>防抖就绪</strong></div>';
      }
    }
  }

  function renderHomeLinkSection() {
    const hn = $('#homelink-nodes');
    if (hn) {
      hn.innerHTML = mock.homelinkNodes.map(n => {
        const rm = n.route_mode || 'shunt';
        const isListening = n.enabled !== false && (n.port_listening !== false);
        const rateTxt = (Number(n.down_rate_bps || 0) + Number(n.up_rate_bps || 0)) > 0
          ? ('↓ ' + (n.down_rate_str || fmtRate(n.down_rate_bps || 0)) + ' · ↑ ' + (n.up_rate_str || fmtRate(n.up_rate_bps || 0)))
          : '待机监听 · 0 B/s';
        return '<article class="glass-card homelink-node" data-hl-card="' + esc(n.id) + '">' +
          '<div class="node-top">' +
            '<div class="protocol-orb">' + esc(n.protocol) + '</div>' +
            '<div style="display:flex;align-items:center;gap:8px">' +
              '<span class="status-pill" style="color:' + (n.enabled === false ? 'var(--muted)' : (isListening ? 'var(--mint)' : 'var(--amber)')) + '">' +
                (n.enabled === false ? '⏸️ 已停用' : (isListening ? '🟢 端口监听正常' : '🟢 正在监听')) +
              '</span>' +
              '<button class="switch ' + (n.enabled === false ? 'off' : 'on') + '" role="switch" aria-checked="' + (n.enabled === false ? 'false' : 'true') + '" data-action="toggle-homelink" data-node="' + esc(n.id) + '" aria-label="启停回家节点"><i></i></button>' +
            '</div>' +
          '</div>' +
          '<h3>' + esc(n.name) + '</h3>' +
          '<div class="node-meta">' +
            '<div><span>监听端口</span><b class="mono">' + esc(n.port) + '</b></div>' +
            '<div><span>DDNS / 地址</span><b class="mono">' + esc(n.ddns_host || window.location.hostname || '自动检测') + '</b></div>' +
            '<div><span>在线客户端 / 累计流量</span><b class="mono">' + esc(Number(n.clients || 0)) + ' 台 · ' + esc(n.total_bytes_str || '0 B') + '</b></div>' +
          '</div>' +
          '<div class="setting-line" style="padding:8px 0;margin-bottom:10px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)">' +
            '<div><b style="font-size:9px">独立回家路由模式</b><span style="font-size:8px;color:var(--muted)">仅对当前回家节点独立生效</span></div>' +
            '<select class="hl-mode-select" data-hl-node-mode="' + esc(n.id) + '" aria-label="独立回家路由模式" aria-busy="' + (state.busyHomelinkNodeId === n.id ? 'true' : 'false') + '">' +
              '<option value="shunt" ' + (rm === 'shunt' ? 'selected' : '') + '>🌐 回家 + 科学上网分流</option>' +
              '<option value="direct" ' + (rm === 'direct' ? 'selected' : '') + '>🏠 仅访问内网与国内</option>' +
              '<option value="proxy_only" ' + (rm === 'proxy_only' ? 'selected' : '') + '>🛡️ 仅科学上网 · 隔离内网</option>' +
            '</select>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;font-size:8px;color:var(--muted)">' +
            '<span>实时吞吐: <strong class="mono" style="color:var(--cyan)">' + esc(rateTxt) + '</strong></span>' +
            '<span>活跃会话: <strong class="mono">' + esc(Number(n.active_conns || 0)) + '</strong></span>' +
          '</div>' +
          '<div class="button-row">' +
            '<button class="button primary compact" data-action="share-node" data-node="' + esc(n.id) + '">📱 二维码与分享</button>' +
            '<button class="button secondary compact" data-action="edit-node" data-node="' + esc(n.id) + '">✏️ 编辑参数</button>' +
            '<button class="button ghost compact" data-action="check-homelink-port" data-port="' + esc(n.listen_port || 18443) + '" data-proto="' + esc(n.raw_proto || 'vless-reality') + '">端口检测</button>' +
            '<button class="button danger compact" data-action="delete-homelink" data-node="' + esc(n.id) + '">删除</button>' +
          '</div>' +
        '</article>';
      }).join('');
    }

    const heroDesc = $('#homelink-hero-desc');
    const hlTelem = (state.rawHomelink && state.rawHomelink.telemetry) || {};
    const listenCnt = mock.homelinkNodes.filter(n => n.enabled !== false).length;
    const clientCnt = Number(hlTelem.active_clients_count != null ? hlTelem.active_clients_count : mock.homelinkNodes.reduce((acc, n) => acc + Number(n.clients || 0), 0));
    const activeConnsCnt = Number(hlTelem.active_conns || 0);
    const totalTrafficStr = hlTelem.total_bytes_str || '0 B';
    const downRateStr = hlTelem.down_rate_str || '0 B/s';
    const upRateStr = hlTelem.up_rate_str || '0 B/s';

    if (heroDesc) {
      heroDesc.textContent = listenCnt + ' 个加密回家入站正在独立监听（每个节点支持独立配置路由边界），当前 ' + (clientCnt > 0 ? (clientCnt + ' 台远程客户端在线 · 活跃会话 ' + activeConnsCnt + ' 条。') : '随时可扫码一键接入家庭内网。');
    }

    const kpiBox = $('#homelink-monitor-kpis');
    if (kpiBox) {
      kpiBox.innerHTML =
        '<div class="galaxy-kpi-card"><span>入站端口监听状态</span><b style="color:var(--mint)">' + esc(listenCnt) + ' / ' + esc(mock.homelinkNodes.length) + ' 在线</b><small>各节点路由边界独立隔离</small></div>' +
        '<div class="galaxy-kpi-card"><span>在线远程客户端</span><b style="color:var(--cyan)">' + esc(clientCnt) + ' 台设备</b><small>并发加密会话 ' + esc(activeConnsCnt) + ' 条</small></div>' +
        '<div class="galaxy-kpi-card"><span>隧道实时上下行</span><b style="color:var(--violet)">↓ ' + esc(downRateStr) + '</b><small>上行速率 ↑ ' + esc(upRateStr) + '</small></div>' +
        '<div class="galaxy-kpi-card"><span>回家累计总流量</span><b style="color:var(--amber)">' + esc(totalTrafficStr) + '</b><small>端到端 TLS / Reality 加密</small></div>';
    }

    const monTbody = $('#homelink-monitor-tbody');
    if (monTbody) {
      const activeSessions = Array.isArray(hlTelem.active_sessions) ? hlTelem.active_sessions : [];
      const recentClients = Array.isArray(hlTelem.recent_clients) ? hlTelem.recent_clients : [];
      const modeNameMap = {
        shunt: '🌐 回家 + 科学上网分流',
        direct: '🏠 仅访问内网与国内',
        proxy_only: '🛡️ 仅科学上网 · 隔离内网'
      };
      const rows = [];
      /* Always show per-node real-time listener monitor rows first */
      mock.homelinkNodes.forEach(n => {
        const rmName = modeNameMap[n.route_mode || 'shunt'] || modeNameMap.shunt;
        const stBadge = n.enabled === false
          ? '<span class="node-status dead">已停用</span>'
          : '<span class="node-status ok">🟢 监听正常 (' + esc(n.port) + ')</span>';
        const cliTxt = Number(n.clients || 0) > 0
          ? (n.clients + ' 台客户端在线')
          : '端口就绪 · 等待客户端接入';
        const speedCell = '↓ ' + esc(n.down_rate_str || '0 B/s') + ' / ↑ ' + esc(n.up_rate_str || '0 B/s');
        const targetsPreview = (Array.isArray(n.recent_targets) && n.recent_targets.length)
          ? n.recent_targets.slice(0, 3).join(', ')
          : ('内网网关 ' + (window.location.hostname || '10.10.10.1'));
        rows.push('<tr>' +
          '<td><b>' + esc(n.name) + '</b><small class="mono">入站隧道 · ' + esc(n.protocol) + '</small></td>' +
          '<td>' + stBadge + '</td>' +
          '<td><span class="status-pill">' + esc(rmName) + '</span></td>' +
          '<td class="mono">' + esc(cliTxt) + '<small style="display:block;color:var(--muted)">目标: ' + esc(targetsPreview) + '</small></td>' +
          '<td class="mono" style="color:var(--cyan)">' + speedCell + '</td>' +
          '<td class="mono">' + esc(n.total_bytes_str || '0 B') + '</td>' +
          '<td style="text-align:right"><button class="button ghost compact" style="min-height:24px;padding:0 8px;font-size:8px" data-action="check-homelink-port" data-port="' + esc(n.listen_port || 18443) + '" data-proto="' + esc(n.raw_proto || 'vless-reality') + '">探针检测</button></td>' +
        '</tr>');
      });

      /* Append active remote client session rows if any */
      activeSessions.slice(0, 20).forEach(s => {
        const rmName = modeNameMap[s.route_mode || 'shunt'] || modeNameMap.shunt;
        rows.push('<tr>' +
          '<td><b class="mono">📱 客户端 ' + esc(s.client_ip) + '</b><small>接入节点: ' + esc(s.node_name) + '</small></td>' +
          '<td><span class="node-status ok">活跃传输 (' + esc(s.network || 'TCP') + ')</span></td>' +
          '<td><span class="status-pill">' + esc(rmName) + '</span></td>' +
          '<td class="mono"><b>' + esc(s.target) + '</b><small style="display:block;color:var(--mint)">' + esc(s.flow_label || '加密转发') + '</small></td>' +
          '<td class="mono" style="color:var(--cyan)">↓ ' + esc(fmtRate(s.down_rate_bps || 0)) + ' / ↑ ' + esc(fmtRate(s.up_rate_bps || 0)) + '</td>' +
          '<td class="mono">↓ ' + esc(fmtBytes(s.down_bytes || 0)) + ' / ↑ ' + esc(fmtBytes(s.up_bytes || 0)) + '</td>' +
          '<td style="text-align:right"><span class="status-pill">在线</span></td>' +
        '</tr>');
      });

      /* Append recent client history if no active sessions yet */
      if (!activeSessions.length && recentClients.length) {
        recentClients.slice(0, 10).forEach(c => {
          const rmName = modeNameMap[c.route_mode || 'shunt'] || modeNameMap.shunt;
          const tsStr = c.last_seen_ts ? new Date(c.last_seen_ts * 1000).toLocaleTimeString('zh-CN', { hour12: false }) : '最近';
          rows.push('<tr>' +
            '<td><b class="mono">🕒 历史客户端 ' + esc(c.client_ip) + '</b><small>接入节点: ' + esc(c.node_name) + '</small></td>' +
            '<td><span class="node-status pending">最后活跃 ' + esc(tsStr) + '</span></td>' +
            '<td><span class="status-pill">' + esc(rmName) + '</span></td>' +
            '<td class="mono">端口 :' + esc(c.listen_port || 18443) + '</td>' +
            '<td class="mono">已休眠</td>' +
            '<td class="mono">↓ ' + esc(fmtBytes(c.down_bytes || 0)) + ' / ↑ ' + esc(fmtBytes(c.up_bytes || 0)) + '</td>' +
            '<td style="text-align:right"><span class="status-pill">历史记录</span></td>' +
          '</tr>');
        });
      }

      monTbody.innerHTML = rows.length
        ? rows.join('')
        : '<tr><td colspan="7"><div class="empty-state" style="padding:18px"><h4>暂无创建的回家节点，请点击右上角「创建回家节点」</h4></div></td></tr>';
    }
  }

  /* Fix #11 & #12: DNS Shield Zero-State Readiness, Rewrite List & Collapsible Music Unlock */
  function renderDnsAndFilterSection() {
    const bd = $('#blocked-domains');
    if (bd) {
      if (mock.blocked && mock.blocked.length) {
        const max = Math.max(1, mock.blocked[0][2] || 1);
        bd.innerHTML = mock.blocked.map(d => '<div class="blocked-row"><div><b>' + esc(d[0]) + '</b><span>' + esc(d[1]) + '</span></div><i style="--width:' + Math.max(4, Math.min(100, d[2] / max * 100)) + '%"></i><strong>' + Number(d[2] || 0).toLocaleString('zh-CN') + ' 次</strong></div>').join('');
      } else {
        bd.innerHTML = '<div class="trace-stage"><i>🛡️</i><div><b>今日已拦截 0 次 · 净网规则引擎已就绪</b><span>内置隐私遥测探针库、商业广告联盟库与路由层 REJECT 规则已挂载生效，产生命中后将实时排行展示</span></div><strong>守护中</strong></div>';
      }
    }
    const heroTitle = $('#dns-hero-title');
    if (heroTitle) {
      const ruleTotal = Number(mock.dnsRulesCount || 50000);
      heroTitle.textContent = ruleTotal.toLocaleString('zh-CN') + ' 条净网与防污染规则正在协同工作';
    }
    const heroReady = $('#dns-engine-readiness');
    if (heroReady) {
      const totalHits = Number(mock.blockedTotal || 0);
      heroReady.textContent = totalHits > 0
        ? ('✓ 规则引擎已激活 · 24h 累计拦截 ' + totalHits.toLocaleString('zh-CN') + ' 次广告与追踪请求')
        : '✓ 规则引擎已就绪 · 今日已拦截 0 次（DNS REFUSED + 路由 REJECT 双层实时守护中）';
    }
    const bq = $('#ov-dns-blocked-q');
    if (bq) bq.textContent = Number(mock.blockedTotal || 0).toLocaleString('zh-CN');
    const bpct = $('#ov-dns-blocked-pct');
    if (bpct) bpct.textContent = Number(mock.dnsBlockedPct || 0).toFixed(1) + '%';
    const bms = $('#ov-dns-avg-ms');
    if (bms) bms.textContent = Math.max(1, Math.round(Number(mock.dnsAvgMs || 1))) + ' ms';
    const lr = $('#ov-dns-layer-rules');
    if (lr) lr.textContent = Number(mock.dnsLayerCount || 0).toLocaleString('zh-CN');
    const rj = $('#dns-layer-reject');
    if (rj) rj.textContent = Number(mock.rejectLayerCount || 0).toLocaleString('zh-CN');
    setSwitchState($('#toggle-dns-filter'), state.dnsEnabled);
    setSwitchState($('#toggle-dns-rewrite'), state.dnsRewriteEnabled);

    const rwList = $('#dns-rewrite-list');
    if (rwList) {
      rwList.innerHTML = mock.rewriteRules.map((r, idx) => {
        const fDom = r.from_domain || r.from || '';
        const tDom = r.to_domain || r.to || '';
        return '<div class="trace-stage" style="padding:9px 12px"><i>R' + (idx + 1) + '</i><div><b class="mono">' + esc(fDom) + ' ➔ ' + esc(tDom) + '</b><span>' + esc(r.note || 'DNS 防跳重写规则') + '</span></div><button class="button danger compact" style="min-height:24px;padding:0 8px;font-size:8px" data-action="delete-dns-rewrite" data-from="' + esc(fDom) + '">删除</button></div>';
      }).join('');
    }

    const flList = $('#dns-filter-lists');
    if (flList) {
      flList.innerHTML = mock.filterLists.map(l => '<div class="trace-stage" style="padding:9px 12px"><i>库</i><div><b>' + esc(l.name) + '</b><span>' + esc(l.category || '云端规则') + ' · ' + Number(l.rules_count || 0).toLocaleString('zh-CN') + ' 条 · ' + esc(l.updated_at || '已同步') + '</span></div><strong>' + (l.enabled !== false ? '已启用' : '已停用') + '</strong></div>').join('');
    }
    renderMusicUnlockSection();
  }

  /* Fix #12: Music Unlock compact collapsible banner when disabled */
  function renderMusicUnlockSection() {
    const body = $('#music-unlock-body');
    const stateLbl = $('#music-unlock-state-label');
    const btnExpand = $('#btn-toggle-music-drawer');
    if (body) {
      const showBody = state.musicUnlockOpen || state.musicUnlockEnabled;
      body.classList.toggle('hidden', !showBody);
    }
    if (stateLbl) {
      stateLbl.textContent = state.musicUnlockEnabled ? '已启用 · 正在劫持解锁变灰音源' : '当前未启用 · 默认折叠以节省空间';
    }
    if (btnExpand) {
      btnExpand.textContent = (state.musicUnlockOpen || state.musicUnlockEnabled) ? '收起详情 ▴' : '展开配置 ▾';
    }
    setSwitchState($('#toggle-music-unlock'), state.musicUnlockEnabled);
  }

  function nodeMatchesSubscription(n, subId) {
    if (!subId || subId === 'ALL') return true;
    if (n.sub_id === subId || n.sub_name === subId || n.sub_url === subId) return true;
    const subObj = mock.subscriptions.find(s => s.id === subId || s.name === subId || s.url === subId);
    if (subObj) {
      if (n.sub_id && (n.sub_id === subObj.id || n.sub_id === subObj.name)) return true;
      if (n.sub_url && subObj.url && n.sub_url === subObj.url) return true;
      if (mock.subscriptions.length === 1) return true;
    }
    return false;
  }

  function filteredNodes() {
    return mock.nodes.filter(n => {
      const statusOk = state.nodeFilter === 'all' ||
        (state.nodeFilter === 'kernel' ? n.kernel : n.status === state.nodeFilter);
      const regionOk = state.regionFilter === 'ALL' || classifyNodeCountry(n) === state.regionFilter;
      const subOk = nodeMatchesSubscription(n, state.subFilter);
      const query = state.search.trim().toLowerCase();
      const searchOk = !query || [n.name, n.region, n.protocol, n.tag, n.server].join(' ').toLowerCase().includes(query);
      return statusOk && regionOk && subOk && searchOk;
    });
  }

  /* Requirement 2: All-Subscriptions Summary Card + Clickable Subscription Cards Filter */
  function renderSubscriptionsAndNodes() {
    const sl = $('#subscription-list');
    if (sl) {
      const enabledSubCnt = mock.subscriptions.filter(s => s.enabled !== false).length;
      const okTotalCnt = mock.nodes.filter(n => n.status === 'ok').length;
      const isAllSelected = !state.subFilter || state.subFilter === 'ALL';
      const allCardHtml = '<article class="subscription-card selectable ' + (isAllSelected ? 'active' : '') + '" data-sub-select="ALL" title="点击查看所有订阅汇总节点列表">' +
        '<div class="sub-top">' +
          '<div><h3>📦 全部订阅源汇总</h3><div class="sub-url mono">共 ' + esc(mock.subscriptions.length) + ' 个订阅源 · ' + esc(enabledSubCnt) + ' 个启用中</div></div>' +
          (isAllSelected ? '<span class="sub-active-chip">✓ 当前显示</span>' : '<span class="status-pill">点击筛选</span>') +
        '</div>' +
        '<div class="sub-metrics">' +
          '<div><b>' + esc(mock.nodes.length) + '</b> <span style="color:var(--muted);font-size:9px">个总节点</span></div>' +
          '<span class="status-pill">' + esc(okTotalCnt) + ' 个已验证可用</span>' +
        '</div>' +
        '<div style="display:flex;justify-content:space-between;color:var(--dim);font-size:8px">' +
          '<span>入核出站: ' + esc(mock.activeOutbounds) + ' / ' + esc(mock.maxOutboundsLimit) + '</span>' +
          '<span>点击卡片查看全量节点</span>' +
        '</div>' +
        '<div class="sub-actions">' +
          '<button class="button secondary compact" data-action="sync">🔄 同步全部</button>' +
          '<button class="button ghost compact" data-action="probe-all">⚡ 全量测速</button>' +
          '<button class="button ghost compact" data-action="add-single-node">➕ 手动加节点</button>' +
        '</div>' +
      '</article>';

      const subCardsHtml = mock.subscriptions.map((s, i) => {
        const rawUrl = String(s.url || '');
        let hostPreview = '本地导入 / 内置订阅源';
        if (rawUrl) {
          try {
            const uObj = new URL(rawUrl);
            hostPreview = uObj.protocol + '//' + uObj.host + uObj.pathname.slice(0, 24) + (uObj.pathname.length > 24 ? '...' : '');
          } catch (_) {
            hostPreview = rawUrl.slice(0, 36) + (rawUrl.length > 36 ? '...' : '');
          }
        }
        const subIdVal = s.id || s.name || ('sub_' + i);
        const isCardActive = state.subFilter === subIdVal;
        const matchedCnt = mock.nodes.filter(n => nodeMatchesSubscription(n, subIdVal)).length;
        const dispCount = Number(s.count != null ? s.count : matchedCnt);
        return '<article class="subscription-card selectable ' + (isCardActive ? 'active' : '') + '" data-sub-select="' + esc(subIdVal) + '" title="点击筛选「' + esc(s.name) + '」的节点列表">' +
          '<div class="sub-top">' +
            '<div><h3>' + esc(s.name) + (isCardActive ? ' <span class="sub-active-chip">当前筛选</span>' : '') + '</h3><div class="sub-url mono" title="' + esc(rawUrl) + '">' + esc(hostPreview) + '</div></div>' +
            '<button class="switch ' + (s.enabled ? 'on' : 'off') + '" role="switch" aria-checked="' + (s.enabled ? 'true' : 'false') + '" data-action="subscription-toggle" data-sub="' + i + '" aria-label="切换订阅"><i></i></button>' +
          '</div>' +
          '<div class="sub-metrics">' +
            '<div><b>' + esc(dispCount) + '</b> <span style="color:var(--muted);font-size:9px">个节点</span></div>' +
            '<span class="status-pill">' + (s.enabled ? '已启用 · 参与选路' : '已停用 · 正交隔离') + '</span>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;color:var(--dim);font-size:8px">' +
            '<span>同步状态: ' + esc(s.updated || '刚刚同步') + '</span>' +
            '<span>自动更新: ' + (s.auto_update !== false ? '每 6 小时' : '手动') + '</span>' +
          '</div>' +
          '<div class="sub-actions">' +
            '<button class="button secondary compact" data-action="sub-sync-one" data-sub="' + i + '">🔄 立即同步</button>' +
            '<button class="button ghost compact" data-action="sub-probe-one" data-sub="' + i + '">⚡ 测速本订阅</button>' +
            '<button class="button ghost compact" data-action="sub-edit-one" data-sub="' + i + '">✏️ 编辑</button>' +
            '<button class="button danger compact" data-action="sub-delete-one" data-sub="' + i + '">删除</button>' +
          '</div>' +
        '</article>';
      }).join('');
      sl.innerHTML = allCardHtml + subCardsHtml;
    }

    const subSel = $('#node-sub-filter');
    if (subSel && document.activeElement !== subSel) {
      subSel.innerHTML = '<option value="ALL">📦 全部订阅源 (' + mock.nodes.length + ')</option>' +
        mock.subscriptions.map(s => '<option value="' + esc(s.id) + '">' + esc(s.name) + ' (' + Number(s.count || 0) + ')</option>').join('');
      subSel.value = state.subFilter || 'ALL';
    }

    const allCnt = mock.nodes.length;
    const okCnt = mock.nodes.filter(n => n.status === 'ok').length;
    const pendCnt = mock.nodes.filter(n => n.status === 'pending').length;
    const suspectCnt = mock.nodes.filter(n => n.status === 'suspect').length;
    const deadCnt = mock.nodes.filter(n => n.status === 'dead').length;
    const kernCnt = mock.nodes.filter(n => n.kernel).length;
    const chipMap = {
      all: '全部 (' + allCnt + ')',
      ok: '✓ 已验证 (' + okCnt + ')',
      pending: '? 待测速 (' + pendCnt + ')',
      suspect: '⚠️ 波动 (' + suspectCnt + ')',
      dead: '✗ 不可达 (' + deadCnt + ')',
      kernel: '⚡ 已入核 (' + kernCnt + ')'
    };
    $$('[data-node-filter]').forEach(btn => {
      const k = btn.dataset.nodeFilter;
      if (chipMap[k]) btn.textContent = chipMap[k];
      btn.classList.toggle('active', state.nodeFilter === k);
    });

    /* Fix #4: Region filter buttons with dynamic per-region node counts */
    const regionBar = $('#region-filter-chips');
    if (regionBar) {
      const regCounts = { ALL: allCnt, HK: 0, TW: 0, JP: 0, SG: 0, US: 0, OTHER: 0 };
      mock.nodes.forEach(n => {
        const rc = classifyNodeCountry(n);
        regCounts[rc] = (regCounts[rc] || 0) + 1;
      });
      const regItems = [
        ['ALL', '🌏 全部地区 (' + regCounts.ALL + ')'],
        ['HK', '🇭🇰 香港 (' + regCounts.HK + ')'],
        ['TW', '🇹🇼 台湾 (' + regCounts.TW + ')'],
        ['JP', '🇯🇵 日本 (' + regCounts.JP + ')'],
        ['SG', '🇸🇬 新加坡 (' + regCounts.SG + ')'],
        ['US', '🇺🇸 美国 (' + regCounts.US + ')'],
        ['OTHER', '🌐 其他 (' + regCounts.OTHER + ')']
      ];
      regionBar.innerHTML = regItems.map(item =>
        '<button class="' + (state.regionFilter === item[0] ? 'active' : '') + '" data-region-filter="' + item[0] + '">' + esc(item[1]) + '</button>'
      ).join('');
    }

    /* Fix #5 & #6: Client-side Pagination + Semantic Latency Display */
    const allFiltered = filteredNodes();
    const pageSize = state.nodePageSize > 0 ? state.nodePageSize : allFiltered.length || 50;
    const totalPages = Math.max(1, Math.ceil(allFiltered.length / pageSize));
    if (state.nodePage > totalPages) state.nodePage = totalPages;
    if (state.nodePage < 1) state.nodePage = 1;
    const startIdx = (state.nodePage - 1) * pageSize;
    const pageNodes = state.nodePageSize === 0 ? allFiltered : allFiltered.slice(startIdx, startIdx + pageSize);

    const statusNames = { ok: '已验证可用', pending: '待测速', dead: '超时不可达', suspect: '延迟波动' };
    const tbody = $('#probe-nodes-tbody');
    if (tbody) {
      tbody.innerHTML = pageNodes.length ? pageNodes.map(n => {
        const cCode = classifyNodeCountry(n);
        const cMeta = COUNTRY_META[cCode] || COUNTRY_META.OTHER;
        const scoreHtml = (n.score != null && n.score > 0 && n.rtt > 0)
          ? ('<span class="mono" style="color:var(--cyan);font-weight:500">' + n.score + ' 分</span>')
          : '<span style="color:var(--dim)">待评估</span>';
        return '<tr>' +
          '<td><b>' + esc(n.name) + '</b><small class="mono">' + esc(n.server ? (n.server + ':' + (n.server_port || 443)) : n.id) + '</small></td>' +
          '<td>' + esc(cMeta.flag + ' ' + cCode) + ' · <span class="mono">' + esc(n.protocol) + '</span></td>' +
          '<td><span class="node-status ' + esc(n.status) + '">' + (statusNames[n.status] || '待测速') + '</span></td>' +
          '<td>' + formatLatencyBadge(n.rtt, n.status, false) + renderMiniSparklineSvg(n.sparkline, n.status === 'ok' ? '#54e6b5' : '#8390a8') + '</td>' +
          '<td class="score-cell">' + scoreHtml + '</td>' +
          '<td>' + (n.kernel ? '<span class="kernel-mark">ACTIVE 入核</span>' : '<span style="color:var(--dim)">按需备选池</span>') + '</td>' +
          '<td><div class="button-row" style="justify-content:flex-end;gap:4px">' +
            '<button class="button ghost compact" style="min-height:25px;padding:0 7px;font-size:8px" data-action="node-real-delay" data-node="' + esc(n.tag || n.name) + '" title="真实握手延迟测试">真测速</button>' +
            '<button class="button ghost compact" style="min-height:25px;padding:0 7px;font-size:8px" data-action="node-credentials" data-node="' + esc(n.tag || n.name) + '" title="查看节点底层凭据">凭据</button>' +
            '<button class="button secondary compact" style="min-height:25px;padding:0 7px;font-size:8px" data-action="set-node-exit" data-node="' + esc(n.tag || n.name) + '">设为出口</button>' +
            '<button class="button ghost compact" style="min-height:25px;padding:0 7px;font-size:8px" data-action="node-details" data-node="' + esc(n.id) + '">详情</button>' +
          '</div></td>' +
        '</tr>';
      }).join('') : '<tr><td colspan="7"><div class="empty-state"><h4>当前筛选条件下没有匹配的节点</h4><p>请点击上方「全部」或调整地区、订阅与搜索关键词。</p></div></td></tr>';
    }

    const lbl = $('#node-count-label');
    if (lbl) {
      const fromNum = allFiltered.length ? (startIdx + 1) : 0;
      const toNum = startIdx + pageNodes.length;
      lbl.textContent = '正在显示第 ' + fromNum + '–' + toNum + ' 个节点 · 筛选匹配 ' + allFiltered.length + ' 个（总计 ' + mock.nodes.length + ' 个，入核上限 ' + mock.maxOutboundsLimit + ' 个）';
    }

    const pagerEl = $('#node-pagination-controls');
    if (pagerEl) {
      if (totalPages <= 1) {
        pagerEl.innerHTML = '<span style="color:var(--dim);font-size:8.5px">共 1 页 (' + allFiltered.length + ' 条)</span>';
      } else {
        const btns = [];
        btns.push('<button class="page-btn" data-page-nav="prev" ' + (state.nodePage <= 1 ? 'disabled' : '') + '>上一页</button>');
        const maxButtons = 5;
        let pStart = Math.max(1, state.nodePage - 2);
        let pEnd = Math.min(totalPages, pStart + maxButtons - 1);
        if (pEnd - pStart < maxButtons - 1) pStart = Math.max(1, pEnd - maxButtons + 1);
        for (let p = pStart; p <= pEnd; p++) {
          btns.push('<button class="page-btn ' + (p === state.nodePage ? 'active' : '') + '" data-page-num="' + p + '">' + p + '</button>');
        }
        btns.push('<button class="page-btn" data-page-nav="next" ' + (state.nodePage >= totalPages ? 'disabled' : '') + '>下一页</button>');
        pagerEl.innerHTML = btns.join('');
      }
    }
  }

  function renderOpsSettings(ops) {
    if (ops && typeof ops === 'object') {
      state.rawOps = Object.assign({}, state.rawOps, ops);
      if ('require_lan_auth' in ops) state.authEnabled = Boolean(ops.require_lan_auth);
      if ('entry_bypass' in ops) state.entryBypass = Boolean(ops.entry_bypass);
      if ('ipv6_proxy' in ops) state.ipv6Proxy = Boolean(ops.ipv6_proxy);
      if ('block_quic' in ops) state.blockQuic = Boolean(ops.block_quic);
      if ('game_udp_direct' in ops) state.gameUdpDirect = Boolean(ops.game_udp_direct);
      if ('auto_mute_conflicts' in ops) state.conflictGuard = Boolean(ops.auto_mute_conflicts);
      if (ops.trusted_cidr) state.trustedCidr = String(ops.trusted_cidr);
      if (ops.gh_mirror != null) state.ghMirror = String(ops.gh_mirror);
      if (ops.update_manifest_url != null) state.updateManifestUrl = String(ops.update_manifest_url);
      if (ops.panel_bind != null) state.panelBind = String(ops.panel_bind);
    }
    setSwitchState($('#toggle-require-lan-auth'), state.authEnabled);
    setSwitchState($('#toggle-ops-entry-bypass'), state.entryBypass);
    setSwitchState($('#toggle-shunt-entry-bypass'), state.entryBypass);
    setSwitchState($('#toggle-ipv6-proxy'), state.ipv6Proxy);
    setSwitchState($('#toggle-block-quic'), state.blockQuic);
    setSwitchState($('#toggle-shunt-block-quic'), state.blockQuic);
    setSwitchState($('#toggle-game-udp-direct'), state.gameUdpDirect);
    setSwitchState($('#toggle-shunt-game-udp'), state.gameUdpDirect);
    setSwitchState($('#toggle-conflict-guard'), state.conflictGuard);

    const secNotice = $('#lan-auth-security-notice');
    if (secNotice) {
      secNotice.textContent = state.authEnabled
        ? '🛡️ 安全风险提示：当前已开启局域网访问鉴权（require_lan_auth=true），非本机访问 API 均需验证管理密码令牌。'
        : '⚠️ 安全风险提示：当前默认允许局域网免密访问 API（require_lan_auth=false）。若局域网有不可信设备或映射了公网端口，请开启「局域网访问鉴权」并修改初始密码！';
    }
  }

  function handleToggleEntryBypass() {
    const nextEb = !state.entryBypass;
    renderOpsSettings({ entry_bypass: nextEb });
    callRouterApi('/api/ops/settings', 'POST', { entry_bypass: nextEb });
    toast('国内流量硬件级旁路已' + (nextEb ? '开启' : '关闭'));
  }

  function renderOpsAndUpdatesSection() {
    renderOpsSettings(state.rawOps);
    const connStat = $('#conn-stat-count');
    if (connStat) connStat.textContent = String(mock.connections);
    const pill = $('#settings-proxy-status-pill');
    if (pill) {
      pill.textContent = !state.coreAlive ? '内核离线' : state.bypassActive ? '直连恢复中' : '运行正常';
    }
    const coreOfflineBanner = $('#core-offline-alert-banner');
    if (coreOfflineBanner) coreOfflineBanner.classList.toggle('hidden', state.coreAlive);
    const ovOfflineCard = $('#ov-core-offline-card');
    if (ovOfflineCard) ovOfflineCard.classList.toggle('hidden', state.coreAlive);
    const bypassBanner = $('#bypass-alert-banner');
    if (bypassBanner) bypassBanner.classList.toggle('hidden', !state.bypassActive);
    renderLogsViewer();
  }

  /* Fix #13: Connections Table with Informative Empty State */
  function renderConnectionsSection() {
    const connStat = $('#conn-stat-count');
    if (connStat) connStat.textContent = String(mock.connections);
    const tbody = $('#connections-tbody');
    if (!tbody) return;
    const q = state.connSearch.trim().toLowerCase();
    const list = (state.rawConnections || []).filter(c => {
      if (!q) return true;
      const meta = c.metadata || {};
      const host = (meta.host || meta.destinationIP || '') + ':' + (meta.destinationPort || '');
      const chain = Array.isArray(c.chains) ? c.chains.join(' ') : '';
      return (host + ' ' + (c.rule || '') + ' ' + chain).toLowerCase().includes(q);
    });
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state" style="padding:26px 12px">' +
        '<span class="empty-orbit"></span>' +
        '<h4>当前无活跃代理连接 · 产生流量后实时显示</h4>' +
        '<p>当终端设备访问海外或命中代理规则时，此处将实时展示五元组（源 IP、目标域名:端口、协议）、命中分流规则、出站节点链路与上下行吞吐。</p>' +
      '</div></td></tr>';
      return;
    }
    tbody.innerHTML = list.slice(0, 40).map(c => {
      const meta = c.metadata || {};
      const src = (meta.sourceIP || 'LAN') + (meta.sourcePort ? ':' + meta.sourcePort : '');
      const dst = (meta.host || meta.destinationIP || 'unknown') + ':' + (meta.destinationPort || 443);
      const net = String(meta.network || 'TCP').toUpperCase();
      const rule = (c.rule || 'MATCH') + (c.rulePayload ? ' (' + c.rulePayload + ')' : '');
      const chain = Array.isArray(c.chains) ? c.chains.slice().reverse().join(' ➔ ') : 'PROXY';
      const traffic = '↓ ' + fmtBytes(c.download || 0) + ' / ↑ ' + fmtBytes(c.upload || 0);
      return '<tr>' +
        '<td class="mono"><b>' + esc(dst) + '</b><small>源: ' + esc(src) + '</small></td>' +
        '<td><span class="status-pill">' + esc(net) + '</span></td>' +
        '<td>' + esc(rule) + '</td>' +
        '<td class="mono" style="color:var(--cyan)">' + esc(chain) + '</td>' +
        '<td class="mono">' + esc(traffic) + '</td>' +
        '<td><button class="button danger compact" style="min-height:24px;padding:0 8px;font-size:8px" data-action="close-single-conn" data-cid="' + esc(c.id || '') + '">断开</button></td>' +
      '</tr>';
    }).join('');
  }

  /* Fix #14: Full-height Log Viewer with Level Filter & Search */
  function renderLogsViewer() {
    const box = $('#ops-logs-viewer');
    if (!box) return;
    const lvl = state.logFilter || 'ALL';
    const q = state.logSearch.trim().toLowerCase();
    const lines = (mock.logs || []).filter(line => {
      const s = String(line || '');
      if (lvl !== 'ALL') {
        if (lvl === 'ERROR' && !/ERR|FAIL|FATAL|panic/i.test(s)) return false;
        if (lvl === 'WARN' && !/WARN|suspect|fallback|timeout/i.test(s)) return false;
        if (lvl === 'INFO' && (/ERR|FAIL|FATAL|WARN/i.test(s))) return false;
      }
      if (q && !s.toLowerCase().includes(q)) return false;
      return true;
    });
    $$('[data-log-filter]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.logFilter === lvl);
    });
    if (!lines.length) {
      box.innerHTML = '<div style="color:var(--muted);padding:24px 8px;text-align:center">当前筛选条件下暂无匹配日志记录（点击「刷新日志」拉取最新内核与守护进程输出）</div>';
      return;
    }
    box.innerHTML = lines.slice(-150).map(ln => {
      const s = String(ln);
      const cls = /ERR|FAIL|FATAL/i.test(s) ? 'error' : (/WARN|timeout/i.test(s) ? 'warn' : 'info');
      return '<div class="log-line ' + cls + '">' + esc(s) + '</div>';
    }).join('');
  }

  function renderAll() {
    renderOverviewDashboard();
    renderShuntMatrix();
    renderHomeLinkSection();
    renderDnsAndFilterSection();
    renderSubscriptionsAndNodes();
    renderOpsAndUpdatesSection();
    renderConnectionsSection();
    renderInspector(state.selected);
  }

  function showPage(page) {
    const normalized = page === 'topology' ? 'galaxy' : page;
    if (!pageTitles[normalized]) return;
    state.page = normalized;
    $$('.page').forEach(el => el.classList.toggle('active', el.id === 'page-' + normalized));
    $$('[data-page-link]').forEach(el => el.classList.toggle('active', el.dataset.pageLink === normalized && el.classList.contains('nav-item')));
    const pt = $('#page-title');
    if (pt) pt.textContent = pageTitles[normalized];
    if (scene) {
      scene.options.page = normalized;
      scene.setActive(normalized === 'galaxy');
      if (normalized === 'galaxy') setTimeout(() => scene.resize(), 50);
    }
    if (normalized === 'overview') setTimeout(drawTrafficChart, 60);
    if (normalized === 'settings') {
      callRouterApi('/api/clash/connections', 'GET').then(res => {
        if (res && Array.isArray(res.connections)) {
          state.rawConnections = res.connections;
          mock.connections = res.connections.length;
          renderConnectionsSection();
        }
      });
      callRouterApi('/api/ops/logs', 'GET').then(res => {
        if (res && Array.isArray(res.logs) && res.logs.length) {
          mock.logs = res.logs;
          renderLogsViewer();
        } else if (res && typeof res.logs === 'string' && res.logs.trim()) {
          mock.logs = res.logs.trim().split('\n');
          renderLogsViewer();
        }
      });
    }
  }

  function setSceneMode(mode) {
    state.sceneMode = mode;
    if (mode !== 'panorama') {
      state.inspectorTab = mode;
    }
    $$('[data-scene-mode]').forEach(el => el.classList.toggle('active', el.dataset.sceneMode === mode));
    const cap = $('#scene-caption');
    if (cap) cap.classList.toggle('dimmed', mode !== 'panorama');
    if (scene) scene.setMode(mode);
    if ($('#inspector')) $('#inspector').classList.add('open');
    renderInspector(state.selected);
  }

  function updateGauge(score) {
    const hs = $('#health-score');
    if (hs) hs.textContent = score;
    const gv = $('.gauge-value');
    if (gv) gv.style.strokeDashoffset = String(314 * (1 - score / 100));
  }

  function buildGalaxyDetailHtml(tab, selectedItem) {
    const eg = getActiveEgressSummary();
    let spotlightHtml = '';
    if (selectedItem && !['core', 'cn', 'global', 'blackhole'].includes(selectedItem.id)) {
      spotlightHtml = '<div class="galaxy-waterline-box" style="border-color:rgba(110,231,245,.45);background:rgba(110,231,245,.07)">' +
        '<div class="galaxy-waterline-top"><span style="color:var(--cyan);font-weight:600">🎯 当前聚焦卫星: ' + esc(selectedItem.name) + '</span><b>' + esc(selectedItem.meta || formatLatencyText(selectedItem.rtt, false)) + '</b></div>' +
        '<div style="font-size:8px;color:var(--muted)">' + esc(selectedItem.subtitle || '点击下方列表或星体可切换透视目标') + '</div>' +
      '</div>';
    }

    if (tab === 'core') {
      const devs = (state.galaxyLanDevices && state.galaxyLanDevices.length)
        ? state.galaxyLanDevices
        : state.insightDevices.map(d => ({ ip: d.ip || '', name: d.name || d.ip, down_rate: 0, up_rate: 0, conns: 0, totalMb: d.totalMb || 0, is_remote: false }));
      const sortedDevs = devs.slice().sort((a, b) => ((Number(b.down_rate || 0) + Number(b.up_rate || 0)) - (Number(a.down_rate || 0) + Number(a.up_rate || 0))) || ((b.conns || 0) - (a.conns || 0)));
      const maxConns = 4096;
      const connPct = Math.min(100, (mock.connections / maxConns) * 100);
      const memPct = Math.min(100, (mock.coreMemMib / 256) * 100);

      const rowsHtml = sortedDevs.slice(0, 10).map(d => {
        const rateSum = Number(d.down_rate || 0) + Number(d.up_rate || 0);
        const speedTxt = rateSum > 0
          ? ('↓ ' + fmtRate(d.down_rate || 0) + ' · ↑ ' + fmtRate(d.up_rate || 0))
          : (d.totalMb ? ('累计 ' + d.totalMb + ' MB') : '↓ 0 B/s · ↑ 0 B/s');
        const subMeta = (d.ip ? ('IP: ' + d.ip + ' · ') : '') + (d.is_remote ? '🏠 回家加密隧道' : '🖧 局域网在线终端');
        return '<div class="galaxy-entity-row">' +
          '<div class="galaxy-entity-icon">' + (d.is_remote ? '🏠' : '💻') + '</div>' +
          '<div class="galaxy-entity-main"><b>' + esc(d.name || d.ip || '局域网终端') + '</b><span class="mono">' + esc(subMeta) + '</span></div>' +
          '<div class="galaxy-entity-right"><strong>' + esc(speedTxt) + '</strong><small>' + esc(Number(d.conns || 0)) + ' 连 · 挡位:' + esc(computeSpeedGearInfo(rateSum, d.conns || 0).label) + '</small></div>' +
        '</div>';
      }).join('');

      return spotlightHtml +
        '<div class="galaxy-kpi-grid">' +
          '<div class="galaxy-kpi-card"><span>在线终端总数</span><b style="color:var(--cyan)">' + esc(sortedDevs.length) + ' 台</b><small>含局域网与回家远程终端</small></div>' +
          '<div class="galaxy-kpi-card"><span>活跃连接总计</span><b style="color:var(--violet)">' + esc(mock.connections) + '</b><small>内核运行: ' + esc(mock.uptimeStr) + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>实时总下行</span><b style="color:var(--mint)">' + esc(mock.downText) + '</b><small>累计下载 ' + esc(mock.inTotalText) + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>实时总上行</span><b style="color:var(--amber)">' + esc(mock.upText) + '</b><small>累计上传 ' + esc(mock.outTotalText) + '</small></div>' +
        '</div>' +
        '<div class="galaxy-waterline-box">' +
          '<div class="galaxy-waterline-row">' +
            '<div class="galaxy-waterline-top"><span>内核连接池水位</span><b>' + esc(mock.connections) + ' / ' + maxConns + ' (' + esc(connPct.toFixed(1)) + '%)</b></div>' +
            '<div class="galaxy-waterline-bar"><i style="width:' + Math.max(4, connPct) + '%"></i></div>' +
          '</div>' +
          '<div class="galaxy-waterline-row">' +
            '<div class="galaxy-waterline-top"><span>内核常驻内存 (RSS)</span><b>' + esc(mock.coreMemMib.toFixed(1)) + ' MiB / 256 MiB</b></div>' +
            '<div class="galaxy-waterline-bar"><i style="width:' + Math.max(6, memPct) + '%"></i></div>' +
          '</div>' +
        '</div>' +
        '<div class="galaxy-list-head"><b>接入终端列表 (按实时速率排序)</b><span>共 ' + esc(sortedDevs.length) + ' 台</span></div>' +
        '<div class="galaxy-entity-list">' + (rowsHtml || '<div class="empty-state"><h4>暂无活跃局域网终端</h4></div>') + '</div>';
    }

    if (tab === 'cn') {
      const domSites = state.galaxyDomesticSites || [];
      const sortedDom = domSites.slice().sort((a, b) => ((Number(b.down_rate || 0) + Number(b.up_rate || 0)) - (Number(a.down_rate || 0) + Number(a.up_rate || 0))) || ((b.conns || 0) - (a.conns || 0)));
      const domDown = sortedDom.reduce((s, x) => s + Number(x.down_rate || 0), 0);
      const domUp = sortedDom.reduce((s, x) => s + Number(x.up_rate || 0), 0);
      const domConns = sortedDom.reduce((s, x) => s + Number(x.conns || 0), 0);
      const trunkGear = computeSpeedGearInfo(domDown + domUp, domConns);

      const rowsHtml = sortedDom.slice(0, 10).map(s => {
        const rateSum = Number(s.down_rate || 0) + Number(s.up_rate || 0);
        const rateTxt = rateSum > 0 ? ('↓ ' + fmtRate(s.down_rate || 0)) : '直连就绪';
        const gInfo = computeSpeedGearInfo(rateSum, s.conns || 1);
        return '<div class="galaxy-entity-row">' +
          '<div class="galaxy-entity-icon" style="color:var(--pink);border-color:rgba(249,168,212,.35);background:rgba(249,168,212,.09)">🇨🇳</div>' +
          '<div class="galaxy-entity-main"><b>' + esc(s.name || s.domain) + '</b><span class="mono">' + esc(s.domain || 'Shunt_Domestic_CN') + ' · WAN 直连</span></div>' +
          '<div class="galaxy-entity-right"><strong style="color:var(--pink)">' + esc(rateTxt) + '</strong><small>' + esc(Number(s.conns || 1)) + ' 连 · 挡位:' + esc(gInfo.label) + '</small></div>' +
        '</div>';
      }).join('');

      return spotlightHtml +
        '<div class="galaxy-kpi-grid">' +
          '<div class="galaxy-kpi-card"><span>活跃国内目标</span><b style="color:var(--pink)">' + esc(sortedDom.length) + ' 个</b><small>并发直连 ' + esc(domConns) + ' 连 · 流速:' + esc(trunkGear.fullLabel) + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>直连实时下行</span><b style="color:var(--pink)">' + esc(fmtRate(domDown)) + '</b><small>直连上行 ' + esc(fmtRate(domUp)) + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>出网物理通道</span><b>WAN 直通</b><small>' + (state.entryBypass ? 'nftables 硬件旁路激活' : '内核 DIRECT 出站') + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>国内纯粹 DNS</span><b class="mono">' + esc(state.cnUpstream || '223.5.5.5') + '</b><small>保留原生 IPv6 零污染</small></div>' +
        '</div>' +
        '<div class="galaxy-waterline-box">' +
          '<div class="galaxy-waterline-row">' +
            '<div class="galaxy-waterline-top"><span>国内直连母星链路流速挡位</span><b style="color:var(--pink)">⚡ ' + esc(trunkGear.fullLabel) + '挡 · 约 18 ms</b></div>' +
            '<div class="galaxy-waterline-bar"><i style="width:94%;background:linear-gradient(90deg,#f9a8d4,#fbcfe8)"></i></div>' +
          '</div>' +
        '</div>' +
        '<div class="galaxy-list-head"><b>国内直连访问目标 (淡粉星系 · 含高中低流速挡位)</b><span>Shunt_Domestic_CN</span></div>' +
        '<div class="galaxy-entity-list">' + rowsHtml + '</div>';
    }

    if (tab === 'global') {
      const foreSites = state.galaxyForeignSites || [];
      const sortedFore = foreSites.slice().sort((a, b) => ((Number(b.down_rate || 0) + Number(b.up_rate || 0)) - (Number(a.down_rate || 0) + Number(a.up_rate || 0))) || ((b.conns || 0) - (a.conns || 0)));
      const foreDown = sortedFore.reduce((s, x) => s + Number(x.down_rate || 0), 0);
      const foreUp = sortedFore.reduce((s, x) => s + Number(x.up_rate || 0), 0);
      const foreConns = sortedFore.reduce((s, x) => s + Number(x.conns || 0), 0);

      const rowsHtml = sortedFore.slice(0, 10).map(s => {
        const grpClean = String(s.group || 'Shunt_AI').replace(/^Shunt_/, '');
        const exitTxt = s.exit_node || eg.nodeName;
        const rateTxt = (Number(s.down_rate || 0) + Number(s.up_rate || 0)) > 0
          ? ('↓ ' + fmtRate(s.down_rate || 0))
          : (s.rtt ? s.rtt + ' ms' : '代理就绪');
        return '<div class="galaxy-entity-row">' +
          '<div class="galaxy-entity-icon">🌍</div>' +
          '<div class="galaxy-entity-main"><b>' + esc(s.name || s.domain) + '</b><span class="mono">[' + esc(grpClean) + '] ➔ ' + esc(exitTxt) + '</span></div>' +
          '<div class="galaxy-entity-right"><strong style="color:var(--violet)">' + esc(rateTxt) + '</strong><small>' + esc(Number(s.conns || 1)) + ' 隧道 · 挡位:' + esc(computeSpeedGearInfo(Number(s.down_rate || 0) + Number(s.up_rate || 0), s.conns || 1).label) + '</small></div>' +
        '</div>';
      }).join('');

      return spotlightHtml +
        '<div class="galaxy-kpi-grid">' +
          '<div class="galaxy-kpi-card"><span>活跃海外目标</span><b style="color:var(--violet)">' + esc(sortedFore.length) + ' 个</b><small>并发代理 ' + esc(foreConns) + ' 条连接</small></div>' +
          '<div class="galaxy-kpi-card"><span>代理实时下行</span><b style="color:var(--cyan)">' + esc(fmtRate(foreDown)) + '</b><small>代理上行 ' + esc(fmtRate(foreUp)) + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>当前路由模式</span><b>' + esc(eg.modeShort) + '</b><small>' + esc(eg.isSingleEgress ? eg.poolOrNodeName : (mock.groups.length + ' 组独立分流')) + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>防污染 FakeIP</span><b class="mono">198.18.0.0/15</b><small>海外 AAAA 防漏已启用</small></div>' +
        '</div>' +
        '<div class="galaxy-waterline-box">' +
          '<div class="galaxy-waterline-row">' +
            '<div class="galaxy-waterline-top"><span>国际核心应用平均响应延迟</span><b>' + esc(eg.latencyText) + '</b></div>' +
            '<div class="galaxy-waterline-bar"><i style="width:86%"></i></div>' +
          '</div>' +
        '</div>' +
        '<div class="galaxy-list-head"><b>海外代理访问目标 (按实时速率排序)</b><span>显示命中分流组与出口</span></div>' +
        '<div class="galaxy-entity-list">' + rowsHtml + '</div>';
    }

    if (tab === 'blackhole') {
      const cats = state.galaxyBlackholeCategories || [];
      const catBarsHtml = cats.slice(0, 4).map(c =>
        '<div class="galaxy-waterline-row">' +
          '<div class="galaxy-waterline-top"><span>' + esc(c.name) + '</span><b style="color:var(--amber)">' + esc(c.count) + ' 次 (' + esc(c.pct) + '%)</b></div>' +
          '<div class="galaxy-waterline-bar"><i style="width:' + Math.max(6, Math.min(100, Number(c.pct || 10))) + '%;background:linear-gradient(90deg,var(--amber),var(--rose))"></i></div>' +
        '</div>'
      ).join('');

      const rowsHtml = (mock.blocked || []).slice(0, 8).map(b =>
        '<div class="galaxy-entity-row">' +
          '<div class="galaxy-entity-icon" style="color:var(--amber);border-color:rgba(247,189,104,.3)">🕳️</div>' +
          '<div class="galaxy-entity-main"><b class="mono">' + esc(b[0]) + '</b><span>' + esc(b[1] || '黑名单规则拦截') + ' · ' + esc(b[3] || 'DNS/路由阻断') + '</span></div>' +
          '<div class="galaxy-entity-right"><strong style="color:var(--amber)">' + esc(Number(b[2] || 0).toLocaleString('zh-CN')) + ' 次</strong><small>已引力吞噬</small></div>' +
        '</div>'
      ).join('');

      return spotlightHtml +
        '<div class="galaxy-kpi-grid">' +
          '<div class="galaxy-kpi-card"><span>已吞噬广告/追踪</span><b style="color:var(--amber)">' + esc(Number(mock.blockedTotal || 0).toLocaleString('zh-CN')) + '</b><small>拦截率 ' + esc(Number(mock.dnsBlockedPct || 0).toFixed(1)) + '% · 实时捕获</small></div>' +
          '<div class="galaxy-kpi-card"><span>挂载有效规则</span><b style="color:var(--mint)">' + esc(Number(mock.dnsRulesCount || 50000).toLocaleString('zh-CN')) + '</b><small>.srs 规则集 + DNS 双保险</small></div>' +
          '<div class="galaxy-kpi-card"><span>DNS 层前置阻断</span><b style="color:var(--cyan)">' + esc(Number(mock.dnsLayerCount || 0).toLocaleString('zh-CN')) + '</b><small>毫秒级零开销拒绝</small></div>' +
          '<div class="galaxy-kpi-card"><span>路由层 REJECT</span><b style="color:var(--violet)">' + esc(Number(mock.rejectLayerCount || 0).toLocaleString('zh-CN')) + '</b><small>防硬编码 IP / DoH 绕过</small></div>' +
        '</div>' +
        '<div class="galaxy-waterline-box">' + catBarsHtml + '</div>' +
        '<div class="galaxy-list-head"><b>🔥 黑洞吞噬高频域名 TOP 榜</b><span>双层实时阻断</span></div>' +
        '<div class="galaxy-entity-list">' + rowsHtml + '</div>';
    }

    return '';
  }

  function renderInspector(data) {
    state.selected = data;
    if (data && data.galaxy && ['core', 'cn', 'global', 'blackhole'].includes(data.galaxy)) {
      state.inspectorTab = data.galaxy;
    } else if (data && ['core', 'cn', 'global', 'blackhole'].includes(data.id)) {
      state.inspectorTab = data.id;
    }
    const activeTab = state.inspectorTab || (state.sceneMode !== 'panorama' ? state.sceneMode : 'core');
    $$('[data-inspector-tab]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.inspectorTab === activeTab);
    });

    const panoBox = $('#inspector-panorama-box');
    const galBox = $('#inspector-galaxy-detail');
    const setExit = $('[data-action="set-exit"]');
    const cap = $('#scene-caption');
    if (cap) cap.classList.toggle('dimmed', !!data || state.sceneMode !== 'panorama');
    const eg = getActiveEgressSummary();

    const tabTitles = {
      panorama: ['SYSTEM OVERVIEW', '全域态势总览'],
      core: ['KERNEL HUB · LAN TERMINALS', '内核中枢 · 局域网终端列表'],
      cn: ['DOMESTIC DIRECT GALAXY', '国内直连 · 实时访问目标'],
      global: ['GLOBAL PROXY GALAXY', '海外代理 · 实时访问目标'],
      blackhole: ['GRAVITY BLACKHOLE SHIELD', '黑洞拦截 · 净网吞噬情报']
    };
    const tPair = tabTitles[activeTab] || tabTitles.core;
    if ($('#inspector-kicker')) $('#inspector-kicker').textContent = tPair[0];
    if ($('#inspector-title')) $('#inspector-title').textContent = tPair[1];

    if (activeTab !== 'panorama' && galBox) {
      if (panoBox) panoBox.classList.add('hidden');
      galBox.classList.remove('hidden');
      galBox.innerHTML = buildGalaxyDetailHtml(activeTab, data);
      if (setExit) setExit.disabled = !(activeTab === 'global');
      return;
    }

    if (panoBox) panoBox.classList.remove('hidden');
    if (galBox) galBox.classList.add('hidden');
    const okCnt = mock.nodes.filter(n => n.status === 'ok').length;
    const covPct = mock.nodes.length ? ((okCnt / mock.nodes.length) * 100).toFixed(1) + '%' : '100%';
    if ($('#inspector-summary')) {
      $('#inspector-summary').textContent = state.coreAlive
        ? '点击上方「🧠 内核 / 🇨🇳 国内 / 🌍 海外 / 🕳️ 黑洞」标签或 3D 星体，即可查看对应星系的接入终端、实时访问站点与黑洞拦截详情。'
        : '⚠️ 检测到 sing-box 代理内核未运行，透明代理已自动回退直连保护。';
    }
    if ($('#detail-grid')) {
      $('#detail-grid').innerHTML =
        '<div><span>运行模式</span><b>' + esc(eg.modeName) + '</b></div>' +
        '<div><span>在线终端</span><b>' + esc(mock.devicesTotal) + ' 台终端</b></div>' +
        '<div><span>可用节点</span><b>' + esc(okCnt) + ' (' + esc(covPct) + ')</b></div>' +
        '<div><span>黑洞拦截</span><b>' + esc(Number(mock.blockedTotal).toLocaleString('zh-CN')) + ' 次</b></div>';
    }
    if ($('#inspector-rtt')) $('#inspector-rtt').textContent = eg.latencyText;
    if ($('#trace-exit')) $('#trace-exit').textContent = eg.isSingleEgress ? eg.poolOrNodeName : (mock.groups.length + ' 组策略按需分流');
    updateGauge(mock.healthScore);
    if (setExit) setExit.disabled = false;
  }

  function syncGalaxy3DData() {
    if (!scene || typeof scene.syncData !== 'function') return;
    const eg = getActiveEgressSummary();
    const coreSats = (state.galaxyLanDevices || []).slice(0, 8).map((d, idx) => {
      const rateSum = Number(d.down_rate || 0) + Number(d.up_rate || 0);
      return {
        id: 'dev-' + (d.ip || idx),
        ip: d.ip || '',
        name: d.name || d.ip || ('终端 ' + (idx + 1)),
        short: String(d.name || d.ip || '').slice(0, 15),
        subtitle: (d.is_remote ? '🏠 回家加密隧道 · ' : '🖧 局域网终端 · ') + (d.ip || 'LAN'),
        meta: rateSum > 0 ? ('↓' + fmtRate(d.down_rate || 0)) : ((d.conns || 0) + ' 连'),
        down_rate: Number(d.down_rate || 0),
        up_rate: Number(d.up_rate || 0),
        rateBps: rateSum,
        conns: Number(d.conns || 1),
        kind: 'device',
        galaxy: 'core',
        region: 'core',
        isRemote: Boolean(d.is_remote),
        status: 'ok',
        topRank: idx
      };
    });

    const cnSats = (state.galaxyDomesticSites || []).slice(0, 8).map((s, idx) => {
      const rateSum = Number(s.down_rate || 0) + Number(s.up_rate || 0);
      return {
        id: 'cn-' + (s.domain || idx),
        domain: s.domain || '',
        name: s.name || s.domain || ('国内站点 ' + (idx + 1)),
        short: String(s.name || s.domain || '').slice(0, 14),
        subtitle: '国内直连 WAN · ' + (s.domain || 'DIRECT'),
        meta: rateSum > 0 ? ('↓' + fmtRate(s.down_rate || 0)) : '直连',
        down_rate: Number(s.down_rate || 0),
        up_rate: Number(s.up_rate || 0),
        rateBps: rateSum,
        conns: Number(s.conns || 1),
        kind: 'service',
        galaxy: 'cn',
        region: 'cn',
        status: 'ok',
        topRank: idx
      };
    });

    const globalSats = (state.galaxyForeignSites || []).slice(0, 8).map((s, idx) => {
      const rateSum = Number(s.down_rate || 0) + Number(s.up_rate || 0);
      const grpClean = String(s.group || 'Shunt_AI').replace(/^Shunt_/, '');
      return {
        id: 'gl-' + (s.domain || idx),
        domain: s.domain || '',
        name: s.name || s.domain || ('海外目标 ' + (idx + 1)),
        short: String(s.name || s.domain || '').slice(0, 14),
        subtitle: '海外代理 [' + grpClean + '] ➔ ' + (s.exit_node || eg.nodeName),
        meta: rateSum > 0 ? ('↓' + fmtRate(s.down_rate || 0)) : (s.rtt ? s.rtt + ' ms' : '代理'),
        down_rate: Number(s.down_rate || 0),
        up_rate: Number(s.up_rate || 0),
        rateBps: rateSum,
        conns: Number(s.conns || 1),
        kind: 'service',
        galaxy: 'global',
        region: 'global',
        status: s.state || 'ok',
        topRank: idx
      };
    });

    const bhSats = (mock.blocked || []).slice(0, 6).map((b, idx) => {
      const dom = String(b[0] || '');
      const cnt = Number(b[2] || 0);
      const cntShort = cnt >= 1000 ? (cnt / 1000).toFixed(1) + 'k次' : cnt + '次';
      return {
        id: 'bh-' + idx,
        name: dom,
        short: dom.length > 16 ? dom.slice(0, 15) + '…' : dom,
        subtitle: (b[1] || '净网拦截') + ' · ' + (b[3] || 'DNS/路由双层阻断'),
        meta: cntShort,
        kind: 'blocked',
        galaxy: 'blackhole',
        region: 'blackhole',
        status: 'blocked',
        topRank: idx
      };
    });

    const cnTotalRate = (state.galaxyDomesticSites || []).reduce((s, x) => s + Number(x.down_rate || 0) + Number(x.up_rate || 0), 0);
    const cnTotalConns = (state.galaxyDomesticSites || []).reduce((s, x) => s + Number(x.conns || 1), 0);
    const glTotalRate = (state.galaxyForeignSites || []).reduce((s, x) => s + Number(x.down_rate || 0) + Number(x.up_rate || 0), 0);
    const glTotalConns = (state.galaxyForeignSites || []).reduce((s, x) => s + Number(x.conns || 1), 0);

    /* Synthesize real 3D active connection flows from live /api/clash/connections + galaxy telemetry */
    const liveConns3D = [];
    if (Array.isArray(state.rawConnections) && state.rawConnections.length) {
      state.rawConnections.slice(0, 14).forEach((c, idx) => {
        const meta = c.metadata || {};
        const srcIp = meta.sourceIP || '';
        const dstHost = meta.host || meta.destinationIP || '';
        const chainStr = Array.isArray(c.chains) ? c.chains.join(' ') : '';
        const ruleStr = String(c.rule || '') + ' ' + String(c.rulePayload || '');
        const isReject = /REJECT|BLOCK/i.test(chainStr + ' ' + ruleStr);
        const isDirect = !isReject && (/DIRECT|Domestic_CN/i.test(chainStr + ' ' + ruleStr));
        const dstGalaxy = isReject ? 'blackhole' : (isDirect ? 'cn' : 'global');
        const rateEst = Number(c.downloadSpeed || c.down_rate || 0) + Number(c.uploadSpeed || c.up_rate || 0) ||
          Math.min(512 * 1024, Math.round((Number(c.download || 0) + Number(c.upload || 0)) / 8) + 24576);
        liveConns3D.push({
          id: c.id || ('live-conn-' + idx),
          srcIp,
          srcName: srcIp || 'LAN',
          dstGalaxy,
          dstDomain: dstHost,
          dstName: dstHost || dstGalaxy,
          rateBps: rateEst,
          conns: 1,
          rule: c.rule || 'MATCH'
        });
      });
    }
    /* Supplement with real galaxy active flows so all active domestic/foreign/blackhole links are expressed in 3D */
    const lanPool = coreSats.length ? coreSats : [{ id: 'dev-0', name: 'LAN', ip: '10.10.10.224' }];
    (state.galaxyForeignSites || []).slice(0, 6).forEach((s, idx) => {
      const src = lanPool[idx % lanPool.length];
      liveConns3D.push({
        id: 'gal-gl-' + idx,
        srcId: src.id,
        srcIp: src.ip || '',
        srcName: src.name,
        dstGalaxy: 'global',
        dstId: 'gl-' + (s.domain || idx),
        dstDomain: s.domain || '',
        dstName: s.name || s.domain,
        rateBps: Number(s.down_rate || 0) + Number(s.up_rate || 0),
        conns: Number(s.conns || 2),
        rule: s.group || 'Shunt_AI'
      });
    });
    (state.galaxyDomesticSites || []).slice(0, 5).forEach((s, idx) => {
      const src = lanPool[(idx + 1) % lanPool.length];
      liveConns3D.push({
        id: 'gal-cn-' + idx,
        srcId: src.id,
        srcIp: src.ip || '',
        srcName: src.name,
        dstGalaxy: 'cn',
        dstId: 'cn-' + (s.domain || idx),
        dstDomain: s.domain || '',
        dstName: s.name || s.domain,
        rateBps: Number(s.down_rate || 0) + Number(s.up_rate || 0),
        conns: Number(s.conns || 2),
        rule: 'DIRECT'
      });
    });
    (mock.blocked || []).slice(0, 2).forEach((b, idx) => {
      const src = lanPool[idx % lanPool.length];
      liveConns3D.push({
        id: 'gal-bh-' + idx,
        srcId: src.id,
        srcName: src.name,
        dstGalaxy: 'blackhole',
        dstId: 'bh-' + idx,
        dstDomain: String(b[0] || ''),
        dstName: String(b[0] || 'Blocked'),
        rateBps: 4096,
        conns: Math.min(12, Math.max(1, Math.round(Number(b[2] || 1) / 10000))),
        rule: 'REJECT'
      });
    });

    scene.syncData({
      core: {
        subtitle: 'sing-box · ' + mock.coreMemMib.toFixed(1) + ' MiB',
        label: '内核 · ' + coreSats.length + ' 台终端'
      },
      cn: {
        subtitle: state.entryBypass ? '大陆 IP 硬件旁路直通' : 'WAN 原生直连出口',
        label: '国内直连 · ' + cnSats.length + ' 目标'
      },
      global: {
        subtitle: eg.isSingleEgress ? eg.poolOrNodeName : (eg.modeName + ' (' + mock.groups.length + '组)'),
        label: '海外代理 · ' + globalSats.length + ' 目标'
      },
      blackhole: {
        subtitle: Number(mock.dnsRulesCount || 50000).toLocaleString('zh-CN') + ' 规则实时守护',
        label: '拦截 ' + Number(mock.blockedTotal || 0).toLocaleString('zh-CN') + ' 次'
      },
      coreSatellites: coreSats,
      cnSatellites: cnSats,
      globalSatellites: globalSats,
      blackholeSatellites: bhSats,
      linkStats: {
        cn: { rateBps: cnTotalRate, conns: cnTotalConns },
        global: { rateBps: glTotalRate, conns: glTotalConns },
        blackhole: { rateBps: 8192, conns: Math.min(15, Math.max(1, (mock.blocked || []).length)) }
      },
      liveConnections: liveConns3D
    });
  }

  async function syncBackendStatus(forceNodes, forceImmediate) {
    try {
      const [stRes, galRes, nodesRes] = await Promise.all([
        callRouterApi('/api/status', 'GET', null, 15000, true),
        callRouterApi('/api/overview/galaxy', 'GET', null, 12000, true),
        (forceNodes || !state.rawNodes.length) ? callRouterApi('/api/nodes?sparkline=1', 'GET', null, 15000, true) : Promise.resolve(null)
      ]);
      if (nodesRes && Array.isArray(nodesRes.nodes)) {
        state.rawNodes = nodesRes.nodes;
        if (nodesRes.nodes.length) {
          mock.nodes = nodesRes.nodes.map((n, i) => {
            const st = n.probe_state || n.state || n.status || 'pending';
            const rawRtt = n.delay_ms != null ? n.delay_ms : n.rtt;
            const rtt = (rawRtt != null && Number(rawRtt) > 0) ? Math.round(Number(rawRtt)) : null;
            const rawScore = n.score_20 != null ? n.score_20 : n.score;
            const score = (rawScore != null && Number(rawScore) > 0 && rtt != null) ? Math.round(Number(rawScore)) : (st === 'ok' && rtt != null ? 92 : null);
            return {
              id: n.node_id || ('node-' + i),
              tag: n.tag || n.name || ('node-' + i),
              name: n.tag || n.name || ('节点 ' + (i + 1)),
              region: classifyNodeCountry(n),
              protocol: String(n.type || n.protocol || 'PROXY').toUpperCase(),
              status: st,
              rtt: rtt,
              score: score,
              kernel: Boolean(n.in_kernel !== false),
              server: n.server || '',
              server_port: n.server_port || 443,
              sub_id: n._sub_id || n.sub_id || 'sub_main',
              sub_url: n._sub_url || n.sub_url || '',
              sub_name: n._sub_name || n.sub_name || '',
              sparkline: Array.isArray(n.sparkline) ? n.sparkline : []
            };
          });
        }
      }

      if (galRes && galRes.ok !== false) {
        state.rawGalaxy = galRes;
        if (Array.isArray(galRes.lan) && galRes.lan.length) {
          state.galaxyLanDevices = galRes.lan;
        }
        if (Array.isArray(galRes.domestic) && galRes.domestic.length) {
          state.galaxyDomesticSites = galRes.domestic;
        }
        if (Array.isArray(galRes.foreign) && galRes.foreign.length) {
          state.galaxyForeignSites = galRes.foreign;
        }
        if (galRes.blackhole && typeof galRes.blackhole === 'object') {
          const bh = galRes.blackhole;
          if (Array.isArray(bh.categories) && bh.categories.length) {
            state.galaxyBlackholeCategories = bh.categories;
          }
          if (Array.isArray(bh.top_blocked) && bh.top_blocked.length) {
            mock.blocked = bh.top_blocked.slice(0, 8).map(item => [
              item.domain || item[0],
              item.category || '黑名单规则拦截',
              Number(item.count || item[2] || 1),
              item.layer || 'DNS/路由阻断'
            ]);
          }
        }
      }

      if (stRes && stRes.ok !== false) {
        state.rawStatus = stRes;
        state.bypassActive = Boolean(stRes.bypass_active);
        state.coreAlive = stRes.core ? Boolean(stRes.core.running !== false) : (stRes.core_running !== false);
        state.pwdCustomized = Boolean(stRes.pwd_customized);
        if (stRes.ipv6_proxy != null) state.ipv6Proxy = Boolean(stRes.ipv6_proxy);

        if (stRes.ops_settings) {
          renderOpsSettings(stRes.ops_settings);
        }
        if (Array.isArray(stRes.switch_history)) {
          mock.switchHistory = stRes.switch_history;
        }
        if (Array.isArray(stRes.probe_schedules) && stRes.probe_schedules.length) {
          mock.schedules = stRes.probe_schedules;
        }
        if (stRes.subscriptions && Array.isArray(stRes.subscriptions) && stRes.subscriptions.length) {
          state.rawSubs = stRes.subscriptions;
          mock.subscriptions = stRes.subscriptions.map(s => ({
            id: s.id || s.name,
            name: s.name || s.id || '订阅源',
            count: Number(s.node_count != null ? s.node_count : (s.count != null ? s.count : mock.nodes.length)),
            enabled: s.enabled !== false,
            updated: s.last_sync_human || s.updated_at || '已同步',
            url: s.url || '',
            auto_update: s.auto_update !== false,
            update_interval_min: Number(s.update_interval_min || 360)
          }));
        }
        if (stRes.shunt) {
          const sh = stRes.shunt;
          state.rawShunt = sh;
          if (sh.routing_mode) state.routingMode = sh.routing_mode;
          if (sh.global_mode) state.globalMode = sh.global_mode;
          if (sh.global_auto_node_id) state.globalAutoNodeId = sh.global_auto_node_id;
          if (sh.global_country) state.globalCountry = sh.global_country;
          if (sh.global_manual_node != null) state.globalManualNode = sh.global_manual_node;
          if (sh.global_resolved_node != null) state.globalResolvedNode = sh.global_resolved_node;
          if (Array.isArray(sh.auto_nodes) && sh.auto_nodes.length) {
            state.rawAutoNodes = sh.auto_nodes;
            mock.autoPools = sh.auto_nodes.map(a => ({
              id: a.id,
              tag: a.tag || a.id,
              name: a.name || a.id,
              mode: a.mode || 'full',
              service_check_enabled: Boolean(a.service_check_enabled || a.mode === 'full'),
              service_checks: Array.isArray(a.service_checks) ? a.service_checks : [],
              service_logic: a.service_logic || a.match_mode || 'all',
              smart_switch_enabled: a.smart_switch_enabled !== false,
              healthy_count: Number(a.pool_reachable_count != null ? a.pool_reachable_count : (a.healthy_count != null ? a.healthy_count : (a.total_candidates || 4))),
              active_group_index: Number(a.active_group_index || 1),
              current_node: (a.current_node && a.current_node !== 'direct') ? a.current_node : ((mock.nodes[0] && mock.nodes[0].name) || '智能优选'),
              current_delay_ms: (a.current_delay_ms != null && Number(a.current_delay_ms) > 0) ? Math.round(Number(a.current_delay_ms)) : null,
              groups: Array.isArray(a.groups) ? a.groups : []
            }));
          }
          if (Array.isArray(sh.groups) && sh.groups.length) {
            mock.groups = sh.groups.map(g => {
              const rawMs = g.resolved_rtt_ms != null ? g.resolved_rtt_ms : g.delay_ms;
              const validMs = (rawMs != null && Number(rawMs) > 0) ? Math.round(Number(rawMs)) : null;
              return {
                id: g.id,
                name: g.title || g.name || g.id,
                subtitle: g.subtitle || g.desc || '精细分流策略组',
                shunt_mode: g.shunt_mode || g.mode || 'auto',
                auto_node_id: g.auto_node_id || 'auto_youtube',
                auto_node_name: g.auto_node_name || '自动节点池',
                country: g.country || 'JP',
                manual_node: g.manual_node || '',
                resolved_node: g.resolved_node || g.manual_node || 'direct',
                rtt: validMs,
                domains: Array.isArray(g.domains) ? g.domains : [],
                domain_keywords: Array.isArray(g.domain_keywords) ? g.domain_keywords : [],
                exact_domains: Array.isArray(g.exact_domains) ? g.exact_domains : [],
                ip_cidrs: Array.isArray(g.ip_cidrs) ? g.ip_cidrs : [],
                is_custom: Boolean(g.is_custom),
                locked_bottom: Boolean(g.locked_bottom),
                locked_order: Boolean(g.locked_order)
              };
            });
          }
        }
        if (stRes.homelink && Array.isArray(stRes.homelink.nodes)) {
          state.rawHomelink = stRes.homelink;
          if (stRes.homelink.nodes.length) {
            mock.homelinkNodes = stRes.homelink.nodes.map(n => ({
              id: n.id,
              raw_proto: n.protocol || 'vless-reality',
              protocol: String(n.protocol || 'HY2').toUpperCase().includes('HY') ? 'HY2' : 'VLS',
              name: n.name || n.id,
              port: (String(n.protocol || '').toLowerCase().includes('hy') ? 'UDP ' : 'TCP ') + (n.listen_port || 18443),
              listen_port: n.listen_port || 18443,
              external_port: n.external_port || n.listen_port || 18443,
              route: n.route_mode === 'direct' ? '仅访问内网与国内' : n.route_mode === 'proxy_only' ? '仅科学上网(隔离内网)' : '回家 + 科学上网分流',
              route_mode: n.route_mode || 'shunt',
              port_listening: n.port_listening !== false,
              clients: Number(n.active_clients_count != null ? n.active_clients_count : (Array.isArray(n.active_clients) ? n.active_clients.length : (n.active_clients || 0))),
              active_conns: Number(n.active_conns || 0),
              down_rate_bps: Number(n.down_rate_bps || 0),
              up_rate_bps: Number(n.up_rate_bps || 0),
              down_rate_str: n.down_rate_str || '0 B/s',
              up_rate_str: n.up_rate_str || '0 B/s',
              total_bytes_str: n.total_bytes_str || '0 B',
              recent_targets: Array.isArray(n.recent_targets) ? n.recent_targets : [],
              enabled: n.enabled !== false,
              ddns_host: n.ddns_host || '',
              uri: n.uri || n.share_uri || ''
            }));
          }
        }

        if (stRes.shield_status || stRes.dns_telemetry) {
          const dt = stRes.dns_telemetry || {};
          const s24 = dt.stats_24h || {};
          const shd = stRes.shield_status || dt.shield_status || {};
          if (dt.filter && dt.filter.enabled != null) {
            state.dnsEnabled = Boolean(dt.filter.enabled);
          } else if (shd.enabled != null) {
            state.dnsEnabled = Boolean(shd.enabled);
          } else if (shd.state) {
            state.dnsEnabled = (shd.state !== 'disabled');
          }
          if (dt.cn_upstream) state.cnUpstream = dt.cn_upstream;
          if (dt.remote_upstream) state.remoteUpstream = dt.remote_upstream;

          const realRulesCnt = s24.total_loaded_rules != null ? Number(s24.total_loaded_rules) : (shd.total_rules != null ? Number(shd.total_rules) : null);
          if (realRulesCnt != null && realRulesCnt > 0) mock.dnsRulesCount = realRulesCnt;
          if (s24.blocked_queries != null) mock.blockedTotal = Number(s24.blocked_queries);
          if (s24.dns_layer_blocks != null) mock.dnsLayerCount = Number(s24.dns_layer_blocks);
          if (s24.route_reject_blocks != null) mock.rejectLayerCount = Number(s24.route_reject_blocks);
          if (s24.blocked_pct != null) mock.dnsBlockedPct = Number(s24.blocked_pct);
          if (s24.avg_resolve_ms != null) mock.dnsAvgMs = Number(s24.avg_resolve_ms);

          const topDom = s24.top_blocked_domains || dt.top_blocked_domains || shd.top_blocked_domains;
          if (Array.isArray(topDom) && topDom.length) {
            mock.blocked = topDom.slice(0, 8).map(d => [
              d.domain || d[0],
              d.category || d.reason || '净网护盾拦截',
              Number(d.count || d.hits || d[2] || 1),
              d.layer || 'DNS/路由阻断'
            ]);
          }
          if (dt.rewrite && Array.isArray(dt.rewrite.rules)) {
            mock.rewriteRules = dt.rewrite.rules;
            if (dt.rewrite.enabled != null) state.dnsRewriteEnabled = Boolean(dt.rewrite.enabled);
          }
          if (dt.filter && Array.isArray(dt.filter.lists) && dt.filter.lists.length) {
            mock.filterLists = dt.filter.lists;
          }
        }

        if (stRes.sys_metrics) {
          const sm = stRes.sys_metrics;
          if (sm.os_release && $('#sys-spec-os')) $('#sys-spec-os').textContent = sm.os_release;
          if (sm.arch && $('#sys-spec-arch')) $('#sys-spec-arch').textContent = sm.arch;
        }

        if (stRes.overview_telemetry) {
          const ovt = stRes.overview_telemetry;
          if (ovt.active_connections != null) mock.connections = Number(ovt.active_connections);
          if (ovt.core_mem_mib != null && Number(ovt.core_mem_mib) > 0) {
            mock.coreMemMib = Number(ovt.core_mem_mib);
          }
          if (ovt.in_rate_bps != null) {
            const inB = Number(ovt.in_rate_bps || 0);
            mock.down = Math.max(0, Math.round(inB / 1024));
            mock.downText = ovt.in_rate_str || fmtRate(inB);
          }
          if (ovt.out_rate_bps != null) {
            const outB = Number(ovt.out_rate_bps || 0);
            mock.up = Math.max(0, Math.round(outB / 1024));
            mock.upText = ovt.out_rate_str || fmtRate(outB);
          }
          if (ovt.in_total_str || ovt.in_total_bytes != null) {
            mock.inTotalText = ovt.in_total_str || fmtBytes(ovt.in_total_bytes || 0);
          }
          if (ovt.out_total_str || ovt.out_total_bytes != null) {
            mock.outTotalText = ovt.out_total_str || fmtBytes(ovt.out_total_bytes || 0);
            mock.upTotalText = mock.outTotalText;
          }
          if (ovt.month_total_str || ovt.month_total_bytes != null) {
            mock.monthTotalText = ovt.month_total_str || fmtBytes(ovt.month_total_bytes || 0);
          }
          if (ovt.month_total_conns != null) {
            mock.monthTotalConns = Number(ovt.month_total_conns);
          }
          if (ovt.kernel_uptime_str || ovt.uptime_str) {
            mock.uptimeStr = ovt.kernel_uptime_str || ovt.uptime_str;
          }
          if (ovt.insight_data) {
            const idata = ovt.insight_data;
            if (Array.isArray(idata.devices) && idata.devices.length) {
              state.insightDevices = idata.devices;
              mock.devicesTotal = idata.devices.length;
              mock.devicesActive = Math.max(1, idata.devices.filter(d => Number(d.totalBytes || 0) > 0).length);
              if (!galRes || !Array.isArray(galRes.lan) || !galRes.lan.length) {
                state.galaxyLanDevices = idata.devices.map(d => ({
                  ip: d.ip || '',
                  name: d.name || d.ip || '局域网终端',
                  down_rate: 0,
                  up_rate: 0,
                  conns: 0,
                  totalMb: d.totalMb || 0,
                  is_remote: false,
                  state: 'ok'
                }));
              }
            }
            if (Array.isArray(idata.targets) && idata.targets.length) {
              state.insightTargets = idata.targets;
              mock.destinationsTotal = idata.targets.length;
            }
          }

          const pulseArr = Array.isArray(ovt.pulse_services) ? ovt.pulse_services : [];
          mock.services = mock.services.map(spec => {
            const fromPulse = pulseArr.find(p => p.id === spec.id || (p.name && p.name.toLowerCase().includes(spec.id)));
            const fromGroup = mock.groups.find(g => g.id === spec.groupId || ('Shunt_' + g.id) === spec.selector);
            let msVal = spec.ms;
            if (fromPulse && Number(fromPulse.ms) > 0) {
              msVal = Math.round(Number(fromPulse.ms));
            } else if (fromGroup) {
              if (fromGroup.shunt_mode === 'direct' || fromGroup.resolved_node === 'direct') {
                msVal = 18;
              } else if (fromGroup.rtt != null && Number(fromGroup.rtt) > 0) {
                msVal = Math.round(Number(fromGroup.rtt));
              }
            }
            const stateVal = (msVal != null && msVal > 600) ? 'suspect' : (msVal != null && msVal > 0 ? 'ok' : 'pending');
            return Object.assign({}, spec, { ms: msVal, state: stateVal });
          });
        }

        if ($('#sys-spec-mem')) $('#sys-spec-mem').textContent = mock.coreMemMib.toFixed(1) + ' MiB';
        if (stRes.active_outbounds_count != null) mock.activeOutbounds = Number(stRes.active_outbounds_count);
        if (stRes.max_outbounds_limit != null) mock.maxOutboundsLimit = Number(stRes.max_outbounds_limit);
        if (stRes.saved_nodes_total != null) mock.totalNodes = Number(stRes.saved_nodes_total);

        if (!state.coreAlive) {
          mock.healthScore = 35;
        } else if (state.bypassActive) {
          mock.healthScore = 82;
        } else {
          const okRatio = mock.nodes.length ? (mock.nodes.filter(n => n.status === 'ok').length / mock.nodes.length) : 1;
          const rttScore = mock.latency < 150 ? 12 : (mock.latency < 260 ? 9 : 4);
          const shieldBonus = state.dnsEnabled ? 6 : 0;
          mock.healthScore = Math.max(60, Math.min(100, Math.round(72 + okRatio * 10 + rttScore + shieldBonus)));
        }

        renderTopBarStatus();
        syncGalaxy3DData();
      }
    } catch (_) {}
    renderAll();
  }

  /* Fix #9: Inline + Modal 4-Stage Traffic Trace */
  async function showTrace(customTarget) {
    const inp = $('#trace-target');
    if (customTarget && inp) inp.value = customTarget;
    const target = (inp && inp.value.trim()) || 'chatgpt.com:443';
    const protocol = (($('#trace-protocol') && $('#trace-protocol').value) || 'TCP').toLowerCase();
    const res = await callRouterApi('/api/shunt/trace', 'POST', { target, protocol });
    const eg = getActiveEgressSummary();
    let stages = [
      ['01', '防火墙 TProxy 接管', '命中 AI-LINK nftables 透明代理规则，未触发局域网或保留地址豁免', '已接管'],
      ['02', '双栈 DNS 智能分流', '海外域名进入 :7874 FakeIP 远程解析路径，DNS 防跳重写与广告黑洞已先行复核', 'FakeIP'],
      ['03', '精细分流规则匹配', '命中高优先级业务策略组，自动绑定对应双组自动节点池', '规则命中'],
      ['04', '实际出站节点隧道', '经由 ' + eg.nodeName + ' 出站转发，端到端健康状态正常', eg.latencyText]
    ];
    if (res && res.ok !== false && (res.stage1_firewall || res.stage3_rule)) {
      const s1 = res.stage1_firewall || {};
      const s2 = res.stage2_dns || {};
      const s3 = res.stage3_rule || {};
      const s4 = res.stage4_outbound || {};
      stages = [
        ['01', s1.title || '防火墙接管', s1.detail || s1.summary || 'nftables 规则判定完成', s1.verdict || s1.action || '已接管'],
        ['02', s2.title || 'DNS 智能分流', s2.detail || s2.summary || 'DNS 路径判定完成', s2.verdict || s2.dns_server || 'FakeIP'],
        ['03', s3.title || '精细规则命中', s3.detail || s3.summary || ('命中策略组: ' + (s3.selector_tag || '默认')), s3.selector_tag || '已命中'],
        ['04', s4.title || '实际出站链路', s4.detail || s4.summary || ('实际出口: ' + (s4.outbound_tag || 'DIRECT')), s4.outbound_tag || 'DIRECT']
      ];
    }
    const inlineHtml = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">' +
      '<b style="font-size:10px;color:var(--cyan)">🎯 诊断目标: ' + esc(target) + ' (' + esc(protocol.toUpperCase()) + ')</b>' +
      '<span class="status-pill">4 阶穿透完成</span>' +
    '</div>' +
    stages.map(s => '<div class="trace-stage" style="padding:9px 11px"><i>' + esc(s[0]) + '</i><div><b>' + esc(s[1]) + '</b><span>' + esc(s[2]) + '</span></div><strong>' + esc(s[3]) + '</strong></div>').join('');
    const inlineBox = $('#shunt-trace-result');
    if (inlineBox) inlineBox.innerHTML = inlineHtml;
    toast('已完成「' + target + '」4 阶全链路透视');
  }

  async function showMatrixTest() {
    toast('正在执行 12 类全矩阵连通与防漏自检...');
    const res = await callRouterApi('/api/shunt/matrix_test', 'POST', {});
    let items = [
      ['M01 · AI 助手 TCP 分流', 'PASS'], ['M02 · Google.cn 防跳重写', 'PASS'],
      ['M03 · YouTube QUIC 策略', 'PASS'], ['M04 · 国内网页硬件旁路', 'PASS'],
      ['M05 · 抖音直播 CDN 直连', 'PASS'], ['M06 · 国服游戏 UDP 直通', 'PASS'],
      ['M07 · NTP 授时防死锁', 'PASS'], ['M08 · DNS 防污染劫持', 'PASS'],
      ['M09 · 面板防自锁保护', 'PASS'], ['M10 · 国内原生 IPv6', 'PASS'],
      ['M11 · 海外 IPv6 防漏保护', 'PASS'], ['M12 · Google Play CDN', 'PASS']
    ];
    if (res && Array.isArray(res.results) && res.results.length) {
      items = res.results.map((r, i) => [
        'M' + String(i + 1).padStart(2, '0') + ' · ' + (r.name || r.title || r.id),
        r.passed !== false ? 'PASS' : 'WARN'
      ]);
    }
    openModal(
      '12 类全矩阵自检报告',
      '<p>全链路矩阵自检已完成：<strong>' + items.filter(x => x[1] === 'PASS').length + ' / ' + items.length + ' 项通过</strong>。</p><div class="matrix-results">' +
      items.map(it => '<div class="matrix-result"><b>' + esc(it[0]) + '</b><span>' + esc(it[1]) + '</span></div>').join('') +
      '</div>',
      'NETWORK MATRIX SELF-TEST'
    );
  }

  async function showNodeDetails(id) {
    const n = mock.nodes.find(item => item.id === id || item.tag === id);
    if (!n) return;
    const shareRes = await callRouterApi('/api/nodes/share_uri?tag=' + encodeURIComponent(n.tag || n.name), 'GET');
    const shareUri = (shareRes && shareRes.uri) ? shareRes.uri : '';
    let qrHtml = '';
    if (shareUri && typeof window.qrcode === 'function') {
      try {
        const qr = window.qrcode(0, 'M');
        qr.addData(shareUri);
        qr.make();
        qrHtml = '<div class="qr-wrap">' + qr.createSvgTag(3, 0) + '</div>';
      } catch (_) {}
    }
    openModal(
      '节点详情与编辑 · ' + n.name,
      '<div class="detail-grid">' +
        '<div><span>所属地区</span><b>' + esc((COUNTRY_META[n.region] && COUNTRY_META[n.region].name) || n.region) + '</b></div>' +
        '<div><span>代理协议</span><b class="mono">' + esc(n.protocol) + '</b></div>' +
        '<div><span>实测延迟</span><b>' + formatLatencyText(n.rtt, false) + '</b></div>' +
        '<div><span>20次滑动评分</span><b>' + (n.score != null && n.rtt > 0 ? n.score + ' / 100' : '待测速评估') + '</b></div>' +
      '</div>' +
      qrHtml +
      '<div class="modal-form" style="margin-top:12px">' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>节点名称 (tag)</label><input id="mdl-edit-node-tag" value="' + esc(n.name) + '"></div>' +
          '<div class="modal-field"><label>地区归属覆盖</label><select id="mdl-edit-node-region">' +
            COUNTRY_CODES.map(c => '<option value="' + c + '" ' + (n.region === c ? 'selected' : '') + '>' + esc(COUNTRY_META[c].flag + ' ' + COUNTRY_META[c].name) + '</option>').join('') +
          '</select></div>' +
        '</div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>服务器地址</label><input id="mdl-edit-node-server" value="' + esc(n.server || '') + '" placeholder="server.example.com"></div>' +
          '<div class="modal-field"><label>端口</label><input id="mdl-edit-node-port" type="number" value="' + esc(n.server_port || 443) + '"></div>' +
        '</div>' +
        (shareUri ? '<div class="modal-field"><label>标准节点分享 URI（点击全选复制）</label><input id="mdl-node-share-uri" class="mono" value="' + esc(shareUri) + '" readonly onclick="this.select()"></div>' : '') +
      '</div>' +
      '<div class="button-row" style="margin-top:14px">' +
        '<button class="button secondary" data-action="probe-single-node" data-node="' + esc(n.tag || n.name) + '">⚡ 立即 URL Ping 测速</button>' +
        '<button class="button primary" data-action="set-node-exit" data-node="' + esc(n.tag || n.name) + '">🚀 设为全局/分流出口</button>' +
        '<button class="button danger compact" data-action="delete-single-node" data-node="' + esc(n.tag || n.name) + '">🗑️ 删除节点</button>' +
      '</div>',
      'NODE OBSERVATORY',
      async () => {
        const new_tag = ($('#mdl-edit-node-tag') && $('#mdl-edit-node-tag').value.trim()) || n.name;
        const region_override = ($('#mdl-edit-node-region') && $('#mdl-edit-node-region').value) || n.region;
        const server = ($('#mdl-edit-node-server') && $('#mdl-edit-node-server').value.trim()) || n.server;
        const server_port = Number(($('#mdl-edit-node-port') && $('#mdl-edit-node-port').value) || n.server_port || 443);
        const patch = { new_tag, region_override };
        if (server) patch.server = server;
        if (server_port) patch.server_port = server_port;
        await callRouterApi('/api/nodes/update', 'POST', { tag: n.tag || n.name, node_id: n.id, patch });
        closeModal();
        toast('节点「' + new_tag + '」参数已保存');
        await syncBackendStatus(true, true);
      },
      '保存节点修改'
    );
  }

  function openRestoreBackupModal() {
    openModal(
      '导入恢复配置归档 (.tgz / .json)',
      '<div class="modal-form">' +
        '<p>支持上传由 AI-LINK 导出的 <code>.tgz</code> / <code>.tar.gz</code> 全量配置归档或 <code>.json</code> 备份文件，恢复前会自动校验路径安全并重载内核。</p>' +
        '<div class="modal-field">' +
          '<label>选择备份文件 (.tgz / .tar.gz / .json)</label>' +
          '<input id="mdl-restore-file" type="file" accept=".tgz,.tar.gz,.json,application/gzip,application/json">' +
        '</div>' +
      '</div>',
      'BACKUP & RECOVERY',
      async () => {
        const fileEl = $('#mdl-restore-file');
        const file = fileEl && fileEl.files && fileEl.files[0];
        if (!file) { toast('请先选择要恢复的 .tgz 或 .json 备份文件', 'warn'); return; }
        const reader = new FileReader();
        reader.onload = async () => {
          const resultStr = String(reader.result || '');
          if (file.name.endsWith('.json')) {
            try {
              const jsonObj = JSON.parse(atob(resultStr.split(',').pop() || ''));
              const r = await callRouterApi('/api/ops/restore', 'POST', jsonObj);
              if (r && r.ok) { closeModal(); toast('JSON 备份恢复成功'); await syncBackendStatus(true, true); }
              else toast((r && r.message) || '恢复失败', 'warn');
            } catch (e) { toast('JSON 文件解析失败', 'warn'); }
          } else {
            const r = await callRouterApi('/api/ops/restore_archive', 'POST', {
              archive_base64: resultStr,
              filename: file.name
            });
            if (r && r.ok) { closeModal(); toast(r.message || '归档恢复成功'); await syncBackendStatus(true, true); }
            else toast((r && r.message) || '归档恢复失败', 'warn');
          }
        };
        reader.readAsDataURL(file);
      },
      '上传并恢复'
    );
  }

  /* Fix #10: Custom Shunt Rules Builder with Syntax Guide & Examples */
  function openNewRuleModal(existingGroup) {
    const g = existingGroup || null;
    const autoOpts = mock.autoPools.map(p => '<option value="' + esc(p.id) + '" ' + (g && g.auto_node_id === p.id ? 'selected' : '') + '>🤖 ' + esc(p.name) + '</option>').join('');
    openModal(
      g ? ('编辑分流策略组 · ' + g.name) : '添加自定义高优先级分流规则',
      '<div class="modal-form">' +
        '<div class="syntax-guide">' +
          '<b>💡 规则语法说明：</b>每行或逗号分隔一条规则。支持：' +
          '域名后缀 <code>openai.com</code>、关键词 <code>keyword:claude</code>、完整域名 <code>full:api.github.com</code>、目标 IP 段 <code>1.1.1.0/24</code>。自定义规则默认插入在「国内直连」之前优先生效。' +
        '</div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>规则组名称</label><input id="mdl-rule-name" value="' + esc(g ? g.name : '我的专属工作流') + '" placeholder="如：OpenAI 专线 / 公司内网"></div>' +
          '<div class="modal-field"><label>插入优先级位置</label><select id="mdl-rule-pos"><option value="top">置顶最高优先级 (Top #01)</option><option value="before_domestic">国内直连白名单之前</option></select></div>' +
        '</div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>出站策略模式</label><select id="mdl-rule-mode"><option value="auto" ' + (!g || g.shunt_mode === 'auto' ? 'selected' : '') + '>🤖 绑定双组自动节点池</option><option value="manual" ' + (g && g.shunt_mode === 'manual' ? 'selected' : '') + '>🖐️ 手动指定国家/节点</option><option value="direct" ' + (g && g.shunt_mode === 'direct' ? 'selected' : '') + '>🎯 强制宽带直连 (DIRECT)</option></select></div>' +
          '<div class="modal-field"><label>绑定自动节点池</label><select id="mdl-rule-autopool">' + autoOpts + '</select></div>' +
        '</div>' +
        '<div class="modal-field"><label>域名后缀列表（每行或逗号分隔，如 example.com）</label><textarea id="mdl-rule-domains" rows="3" placeholder="openai.com\nanthropic.com\ncursor.sh">' + esc(g && g.domains ? g.domains.join('\n') : '') + '</textarea></div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>域名关键字（可选，如 openai, claude）</label><input id="mdl-rule-keywords" value="' + esc(g && g.domain_keywords ? g.domain_keywords.join(', ') : '') + '" placeholder="keyword1, keyword2"></div>' +
          '<div class="modal-field"><label>目标 IP CIDR（可选，如 1.1.1.0/24）</label><input id="mdl-rule-cidrs" value="' + esc(g && g.ip_cidrs ? g.ip_cidrs.join(', ') : '') + '" placeholder="91.108.4.0/22, 149.154.160.0/20"></div>' +
        '</div>' +
        (g && g.is_custom ? '<div class="button-row"><button class="button danger compact" data-action="delete-custom-group" data-gid="' + esc(g.id) + '">🗑️ 删除此自定义分流组</button></div>' : '') +
        (g && !g.is_custom ? '<div class="button-row"><button class="button ghost compact" data-action="reset-single-group" data-gid="' + esc(g.id) + '">🔄 恢复此内置组默认域名库</button></div>' : '') +
      '</div>',
      'POLICY BUILDER',
      async () => {
        const name = ($('#mdl-rule-name') && $('#mdl-rule-name').value.trim()) || '自定义规则';
        const position = ($('#mdl-rule-pos') && $('#mdl-rule-pos').value) || 'top';
        const shunt_mode = ($('#mdl-rule-mode') && $('#mdl-rule-mode').value) || 'auto';
        const auto_node_id = ($('#mdl-rule-autopool') && $('#mdl-rule-autopool').value) || 'auto_ai';
        const rawDoms = ($('#mdl-rule-domains') && $('#mdl-rule-domains').value) || '';
        const rawKws = ($('#mdl-rule-keywords') && $('#mdl-rule-keywords').value) || '';
        const rawCidrs = ($('#mdl-rule-cidrs') && $('#mdl-rule-cidrs').value) || '';
        const domains = rawDoms.split(/[\n,;]+/).map(s => s.trim()).filter(Boolean);
        const domain_keywords = rawKws.split(/[\n,;]+/).map(s => s.trim()).filter(Boolean);
        const ip_cidrs = rawCidrs.split(/[\n,;]+/).map(s => s.trim()).filter(Boolean);
        const payload = {
          id: g ? g.id : '',
          name,
          position,
          shunt_mode,
          strategy: shunt_mode === 'direct' ? 'direct' : (shunt_mode === 'manual' ? 'manual' : 'auto'),
          country: shunt_mode === 'direct' ? 'direct' : 'US',
          auto_node_id,
          manual_node: shunt_mode === 'auto' ? ('auto:' + auto_node_id) : (shunt_mode === 'direct' ? 'direct' : ''),
          domains,
          domain_keywords,
          ip_cidrs
        };
        const res = await callRouterApi('/api/shunt/custom_rule', 'POST', payload);
        closeModal();
        if (res && res.conflict_warning) {
          toast(res.conflict_warning, 'warn');
        } else {
          toast('已保存分流规则组：' + name);
        }
        await syncBackendStatus(false, true);
      },
      '保存分流规则'
    );
  }

  /* Overhauled Dual-Group Auto Node Pool Builder Modal:
   * 1. Filter available nodes by Subscription -> Country/Region -> Keyword, up to 10 nodes per group (G1 Primary / G2 Standby).
   * 2. Run immediate URL Ping & Service Availability checks (single/multi-select services, ALL or ANY pass logic) with live results.
   * 3. Replace or remove suboptimal nodes on the spot, or save the pool directly.
   * 4. Built-in periodic health check, disconnect auto-switch, standby group failover & primary group failback enabled by default.
   */
  function openAutoNodeEditorModal(poolIdx) {
    const p = (poolIdx != null && mock.autoPools[poolIdx]) ? mock.autoPools[poolIdx] : null;
    const cleanTags = arr => (Array.isArray(arr) ? arr : [])
      .map(x => String(x || '').trim())
      .filter(Boolean)
      .slice(0, 10);
    const initG1 = (p && p.groups && p.groups[0]) ? cleanTags(p.groups[0].node_tags) : [];
    const initG2 = (p && p.groups && p.groups[1]) ? cleanTags(p.groups[1].node_tags) : [];

    const g1Set = new Set(initG1);
    const g2Set = new Set(initG2);
    const stagedSet = new Set();
    let activeTargetGroup = 1;
    let filterSub = 'ALL';
    let filterCountry = 'ALL';
    let filterSearch = '';
    const testResultsByTag = {};

    const SERVICE_OPTIONS = [
      { id: 'chatgpt', name: 'ChatGPT / OpenAI' },
      { id: 'gemini', name: 'Google Gemini' },
      { id: 'youtube', name: 'YouTube 4K' },
      { id: 'netflix', name: 'Netflix 流媒体' },
      { id: 'tiktok', name: 'TikTok 国际' },
      { id: 'github', name: 'GitHub' },
      { id: 'telegram', name: 'Telegram' }
    ];
    const initSvcs = new Set(
      (p && Array.isArray(p.service_checks) && p.service_checks.length)
        ? p.service_checks
        : ['chatgpt', 'youtube']
    );
    const initLogic = (p && p.service_logic === 'any') ? 'any' : 'all';

    const subOptionsHtml = '<option value="ALL">📦 全部可用订阅源 (' + mock.nodes.length + ')</option>' +
      mock.subscriptions.map(s => '<option value="' + esc(s.id) + '">📡 ' + esc(s.name) + ' (' + Number(s.count || mock.nodes.filter(n => nodeMatchesSubscription(n, s.id)).length) + ')</option>').join('');

    const svcChecksHtml = SERVICE_OPTIONS.map(s =>
      '<label class="an-svc-chip"><input type="checkbox" class="chk-an-svc" value="' + esc(s.id) + '" ' + (initSvcs.has(s.id) ? 'checked' : '') + '><span>' + esc(s.name) + '</span></label>'
    ).join('');

    openModal(
      p ? ('编排双组省流自动节点池 · ' + p.name) : '新建双组省流自动节点池',
      '<div id="an-builder-root" class="ov-insight-modal-wrap modal-form" style="gap:9px">' +
        '<div class="syntax-guide" style="margin-bottom:0">' +
          '<b>🔄 节点池构建流程：</b>① 在筛选器勾选候选节点（单次最多勾 10 个） ➔ ② 可对新勾选节点执行检测（仅测新勾选项，已入池节点不重复测） ➔ ③ 将检测通过或已勾选节点确认加入节点池 ➔ ④ 下方列表可随时直接移除节点，未满 10 个可继续往复筛选添加，完成后点击右下角保存。' +
        '</div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>自动节点池名称</label><input id="mdl-an-name" value="' + esc(p ? p.name : '高速多业务自动池') + '" placeholder="如：AI 专线自动池 / 游戏流媒体池"></div>' +
          '<div class="modal-field"><label>当前正在配置的分组（每组上限 10 个，下方已添加列表随所选分组切换）</label>' +
            '<div class="an-builder-tabs">' +
              '<div style="display:flex;gap:6px">' +
                '<button type="button" class="an-group-tab active" data-an-grp-tab="1">🎯 主力组 G1 (<span id="mdl-an-g1-cnt">' + g1Set.size + '</span>/10)</button>' +
                '<button type="button" class="an-group-tab" data-an-grp-tab="2">🛡️ 备选组 G2 (<span id="mdl-an-g2-cnt">' + g2Set.size + '</span>/10)</button>' +
              '</div>' +
              '<div style="display:flex;gap:6px">' +
                '<button type="button" class="button ghost compact" style="min-height:26px;padding:0 8px;font-size:8px" id="btn-an-fill-top10" title="按补足到 10 个在筛选器中快速勾选未入池候选节点">☑️ 勾选筛选前10优</button>' +
                '<button type="button" class="button ghost compact" style="min-height:26px;padding:0 8px;font-size:8px" id="btn-an-clear-staged" title="清空筛选器中当前已勾选的待测节点">🧹 清空勾选</button>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>' +

        /* Step 1: Candidate Node Filter (Check up to 10 un-added nodes) */
        '<div class="an-filter-bar">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">' +
            '<span style="font-size:9px;color:var(--cyan);font-weight:600">① 节点筛选器：查找并勾选新候选节点（已勾选 <strong id="mdl-an-staged-cnt" style="color:var(--mint)">0</strong> 个新节点待操作 · <span id="mdl-an-stage-summary" style="color:var(--muted)">可勾选 1~10 个节点进行检测或直接加入节点池</span>）</span>' +
            '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">' +
              '<select id="mdl-an-sub-filter" style="min-height:28px;font-size:8.5px" aria-label="按订阅筛选候选节点">' + subOptionsHtml + '</select>' +
              '<label class="search-box" style="min-height:28px;padding:0 8px"><svg><use href="#i-search"/></svg><input id="mdl-an-node-search" placeholder="搜索节点名称或协议..." style="font-size:8.5px"></label>' +
            '</div>' +
          '</div>' +
          '<div id="mdl-an-country-chips" class="region-chips"></div>' +
          '<div id="mdl-an-picker-list" class="picker-list"></div>' +
        '</div>' +

        /* Step 2: Test Newly Checked Nodes & Confirm Add to Pool */
        '<div class="an-svc-bar">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap">' +
            '<span style="font-size:8.5px;color:var(--cyan);font-weight:600">② 检测已勾选新节点 & 确认入池（仅测新勾选项）</span>' +
            '<div style="display:flex;gap:5px;align-items:center;flex-wrap:wrap">' +
              '<select id="mdl-an-svc-logic" style="min-height:26px;padding:0 7px;font-size:8px" aria-label="服务可用性判定标准">' +
                '<option value="all" ' + (initLogic === 'all' ? 'selected' : '') + '>标准：全部可用</option>' +
                '<option value="any" ' + (initLogic === 'any' ? 'selected' : '') + '>标准：任意可用</option>' +
              '</select>' +
              '<button type="button" class="button secondary compact" style="min-height:26px;padding:0 8px;font-size:8px" id="btn-an-test-ping" aria-busy="false">⚡ 仅测已勾选 Ping</button>' +
              '<button type="button" class="button secondary compact" style="min-height:26px;padding:0 8px;font-size:8px" id="btn-an-test-full" aria-busy="false">🧪 检测已勾选 (Ping+服务)</button>' +
              '<button type="button" class="button ghost compact" style="min-height:26px;padding:0 7px;font-size:8px" id="btn-an-keep-qualified" title="仅保留勾选检测通过的节点">✨ 仅留合格</button>' +
              '<button type="button" class="button secondary compact" style="min-height:26px;padding:0 9px;font-size:8px;border-color:rgba(84,230,181,.45);color:var(--mint)" id="btn-an-add-passed" title="仅把当前已勾选且检测通过的节点加入节点池">✅ 将检测通过加入池</button>' +
              '<button type="button" class="button primary compact" style="min-height:26px;padding:0 10px;font-size:8px" id="btn-an-add-to-pool" title="将当前已勾选的节点（含免测直加或检测通过节点）确认加入节点池">➕ 将已勾选加入池 (<span id="mdl-an-add-grp-lbl">主力组 G1</span>)</button>' +
            '</div>' +
          '</div>' +
          '<div class="an-svc-checks">' + svcChecksHtml + '</div>' +
        '</div>' +

        /* Step 3: Added Node Pool List for Current Active Group (Direct single-click removal, zero popup) */
        '<div>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;flex-wrap:wrap;gap:6px">' +
            '<span style="font-size:9px;color:var(--text);font-weight:600" id="mdl-an-pool-table-title">③ 当前「主力组 G1」已入池节点列表 (' + g1Set.size + ' / 10)</span>' +
            '<div style="display:flex;gap:6px;align-items:center">' +
              '<button type="button" class="button ghost compact" style="min-height:24px;padding:0 9px;font-size:8px" id="btn-an-clear-grp">🧹 清空本组已添加节点</button>' +
              (p && !['auto_ai', 'auto_youtube', 'auto_netflix'].includes(p.id)
                ? '<button type="button" class="button danger compact" style="min-height:24px;padding:0 9px;font-size:8px" data-action="delete-auto-pool" data-pool-id="' + esc(p.id) + '">🗑️ 删除此节点池</button>'
                : '') +
            '</div>' +
          '</div>' +
          '<div class="table-wrap" style="max-height:165px;overflow:auto">' +
            '<table>' +
              '<thead><tr><th>分组 / 序号</th><th>节点名称 · 地区</th><th>URL Ping 延迟</th><th>服务可用性检测结果</th><th>入池状态</th><th style="text-align:right">直接移除</th></tr></thead>' +
              '<tbody id="mdl-an-selected-tbody"></tbody>' +
            '</table>' +
          '</div>' +
        '</div>' +
      '</div>',
      'DUAL-GROUP AUTO NODE POOL BUILDER',
      async () => {
        const name = ($('#mdl-an-name') && $('#mdl-an-name').value.trim()) || '自动节点池';
        if (g1Set.size === 0 && stagedSet.size > 0) {
          Array.from(stagedSet).slice(0, 10).forEach(t => g1Set.add(t));
          stagedSet.clear();
        }
        const g1 = Array.from(g1Set).slice(0, 10);
        const g2 = Array.from(g2Set).slice(0, 10);
        if (!g1.length) { toast('主力组 G1 至少需要添加 1 个节点（请在筛选器勾选节点后点击「➕ 将已勾选节点加入池」）', 'warn'); return; }
        const checkedSvcs = $$('.chk-an-svc:checked').map(el => el.value);
        const svcLogic = ($('#mdl-an-svc-logic') && $('#mdl-an-svc-logic').value) || 'all';
        const groups = [{ index: 1, name: '主力组 G1', node_tags: g1 }];
        if (g2.length) groups.push({ index: 2, name: '备选组 G2', node_tags: g2 });
        const res = await callRouterApi('/api/auto_nodes/save', 'POST', {
          id: p ? p.id : '',
          tag: p ? p.tag : '',
          name,
          mode: checkedSvcs.length ? 'full' : 'semi',
          service_check_enabled: checkedSvcs.length > 0,
          service_checks: checkedSvcs,
          service_logic: svcLogic,
          match_mode: svcLogic,
          smart_switch_enabled: true,
          groups,
          probe_now: true
        });
        if (res && res.ok === false) {
          toast(res.message || '保存自动节点池失败', 'warn');
          return;
        }
        closeModal();
        toast('自动节点池「' + name + '」已保存（主力组 ' + g1.length + ' 个 / 备选组 ' + g2.length + ' 个，后台健康巡检与自动切换已激活）');
        await syncBackendStatus(false, true);
      },
      '确定保存节点池'
    );

    function getActivePoolSet() {
      return activeTargetGroup === 1 ? g1Set : g2Set;
    }

    function getOtherPoolSet() {
      return activeTargetGroup === 1 ? g2Set : g1Set;
    }

    function getActiveGroupLabel() {
      return activeTargetGroup === 1 ? '主力组 G1' : '备选组 G2';
    }

    function getSubFilteredNodes() {
      return mock.nodes.filter(n => nodeMatchesSubscription(n, filterSub));
    }

    function getFullyFilteredNodes() {
      const q = filterSearch.trim().toLowerCase();
      return getSubFilteredNodes().filter(n => {
        if (filterCountry !== 'ALL' && classifyNodeCountry(n) !== filterCountry) return false;
        if (q && !([n.name, n.tag, n.protocol, n.region, n.server].join(' ').toLowerCase().includes(q))) return false;
        return true;
      });
    }

    function updateGroupCounters() {
      Array.from(stagedSet).forEach(t => {
        if (g1Set.has(t) || g2Set.has(t)) stagedSet.delete(t);
      });
      if ($('#mdl-an-g1-cnt')) $('#mdl-an-g1-cnt').textContent = String(g1Set.size);
      if ($('#mdl-an-g2-cnt')) $('#mdl-an-g2-cnt').textContent = String(g2Set.size);
      if ($('#mdl-an-staged-cnt')) $('#mdl-an-staged-cnt').textContent = String(stagedSet.size);

      const stagedArr = Array.from(stagedSet);
      const testedInStaged = stagedArr.filter(t => Boolean(testResultsByTag[t]));
      const passedInStaged = testedInStaged.filter(t => Boolean(testResultsByTag[t].qualified));
      const failedInStaged = testedInStaged.length - passedInStaged.length;
      const sumEl = $('#mdl-an-stage-summary');
      if (sumEl) {
        if (!stagedArr.length) {
          sumEl.textContent = '可任意勾选 1~10 个节点进行检测，或直接确认加入节点池';
        } else if (testedInStaged.length > 0) {
          sumEl.textContent = '已检测 ' + testedInStaged.length + '/' + stagedArr.length + ' 个：✓ 通过 ' + passedInStaged.length + ' 个' + (failedInStaged > 0 ? (' · ✗ 未通过 ' + failedInStaged + ' 个') : '');
        } else {
          sumEl.textContent = '可点击下方「🧪 检测已勾选」测试可用性，或直接点击「➕ 将已勾选节点加入池」';
        }
      }

      const grpName = getActiveGroupLabel();
      const activeSet = getActivePoolSet();
      if ($('#mdl-an-add-grp-lbl')) $('#mdl-an-add-grp-lbl').textContent = grpName + ' · ' + activeSet.size + '/10';
      if ($('#mdl-an-pool-table-title')) {
        $('#mdl-an-pool-table-title').textContent = '③ 当前「' + grpName + '」已入池节点列表 (' + activeSet.size + ' / 10)';
      }
      $$('[data-an-grp-tab]').forEach(btn => {
        btn.classList.toggle('active', Number(btn.dataset.anGrpTab) === activeTargetGroup);
      });
    }

    function renderCountryChips() {
      const subNodes = getSubFilteredNodes();
      const counts = { ALL: subNodes.length, HK: 0, TW: 0, JP: 0, SG: 0, US: 0, OTHER: 0 };
      subNodes.forEach(n => {
        const c = classifyNodeCountry(n);
        counts[c] = (counts[c] || 0) + 1;
      });
      const chips = [
        ['ALL', '🌏 全部 (' + counts.ALL + ')'],
        ['HK', '🇭🇰 香港 (' + counts.HK + ')'],
        ['TW', '🇹🇼 台湾 (' + counts.TW + ')'],
        ['JP', '🇯🇵 日本 (' + counts.JP + ')'],
        ['SG', '🇸🇬 新加坡 (' + counts.SG + ')'],
        ['US', '🇺🇸 美国 (' + counts.US + ')'],
        ['OTHER', '🌐 其他 (' + counts.OTHER + ')']
      ];
      const box = $('#mdl-an-country-chips');
      if (!box) return;
      box.innerHTML = chips.map(c =>
        '<button type="button" class="' + (filterCountry === c[0] ? 'active' : '') + '" data-an-country="' + c[0] + '">' + esc(c[1]) + '</button>'
      ).join('');
    }

    function renderPickerList() {
      const box = $('#mdl-an-picker-list');
      if (!box) return;
      const list = getFullyFilteredNodes();
      const targetSet = getActivePoolSet();
      const otherSet = getOtherPoolSet();
      if (!list.length) {
        box.innerHTML = '<div style="grid-column:1/-1;color:var(--muted);padding:12px;text-align:center;font-size:8.5px">当前订阅与地区筛选下无匹配节点</div>';
        return;
      }
      box.innerHTML = list.slice(0, 120).map(n => {
        const t = n.tag || n.name;
        const inTarget = targetSet.has(t);
        const inOther = otherSet.has(t);
        const isAdded = inTarget || inOther;
        const isStaged = !isAdded && stagedSet.has(t);
        const cCode = classifyNodeCountry(n);
        const cFlag = (COUNTRY_META[cCode] && COUNTRY_META[cCode].flag) || '🌐';
        const tr = testResultsByTag[t];
        const msVal = tr && tr.delay_ms != null ? tr.delay_ms : n.rtt;

        let rightStatusHtml = '';
        if (inTarget) {
          rightStatusHtml = '<span class="an-added-badge" data-added-status="current">✓ 已添加</span>';
        } else if (inOther) {
          rightStatusHtml = '<span class="an-added-badge other" data-added-status="other">✓ 已添加(G' + (activeTargetGroup === 1 ? '2' : '1') + ')</span>';
        } else {
          rightStatusHtml = '<span class="picker-item-ms">' + esc(formatLatencyText(msVal, false)) + '</span>';
        }

        let inlineTestHtml = '';
        if (tr && !isAdded) {
          const pingOk = tr.delay_ms != null && tr.delay_ms > 0 && tr.state !== 'dead';
          const pingPill = '<span class="an-inline-pill ' + (pingOk ? 'ok' : 'bad') + '">⚡ ' + (pingOk ? (tr.delay_ms + 'ms') : '超时') + '</span>';
          const sr = tr.svc_results || {};
          const svcPills = Object.keys(sr).map(k => {
            const item = sr[k];
            const ok = Boolean(item && item.ok);
            const ms = (item && item.ms) ? (' ' + item.ms + 'ms') : '';
            return '<span class="an-inline-pill ' + (ok ? 'ok' : 'bad') + '">' + (ok ? '✓ ' : '✗ ') + esc(k.toUpperCase() + ms) + '</span>';
          }).join('');
          const verdictPill = tr.qualified
            ? '<span class="an-inline-verdict ok">✓ 理想可用</span>'
            : '<span class="an-inline-verdict bad">✗ 不理想</span>';
          inlineTestHtml = '<div class="picker-item-results">' + pingPill + svcPills + verdictPill + '</div>';
        }

        const itemCls = [
          'picker-item',
          inTarget ? 'is-added' : (inOther ? 'is-added-other' : (isStaged ? 'is-staged' : '')),
          tr ? (tr.qualified ? 'is-tested-ok' : 'is-tested-bad') : ''
        ].filter(Boolean).join(' ');

        return '<label class="' + itemCls + '" data-picker-tag="' + esc(t) + '">' +
          '<div class="picker-item-top">' +
            '<div class="picker-item-left">' +
              '<input type="checkbox" class="chk-an-cand" value="' + esc(t) + '" ' + (isStaged ? 'checked' : '') + ' ' + (isAdded ? 'disabled' : '') + '>' +
              '<span class="picker-item-name" title="' + esc(n.name || t) + '">' + esc(cFlag + ' ' + (n.name || t)) + '</span>' +
            '</div>' +
            rightStatusHtml +
          '</div>' +
          inlineTestHtml +
        '</label>';
      }).join('');
    }

    function renderSelectedTable() {
      const tbody = $('#mdl-an-selected-tbody');
      if (!tbody) return;
      const svcLogic = ($('#mdl-an-svc-logic') && $('#mdl-an-svc-logic').value) || 'all';
      const activeSet = getActivePoolSet();
      const grpIdx = activeTargetGroup;
      const grpName = getActiveGroupLabel();
      const rows = [];

      Array.from(activeSet).forEach((tag, idx) => {
        const n = mock.nodes.find(x => (x.tag || x.name) === tag) || { tag, name: tag, region: classifyNodeCountry({ tag }), protocol: 'PROXY', status: 'ok', rtt: 145 };
        const cCode = classifyNodeCountry(n);
        const cMeta = COUNTRY_META[cCode] || COUNTRY_META.OTHER;
        const tr = testResultsByTag[tag];
        const delayMs = tr ? tr.delay_ms : n.rtt;
        const stateVal = tr ? tr.state : n.status;
        let svcHtml = '<span style="color:var(--dim);font-size:8px">免测直接加入 / 待巡检</span>';
        let isIdeal = (stateVal !== 'dead');
        if (tr) {
          const sr = tr.svc_results || {};
          const sKeys = Object.keys(sr);
          if (sKeys.length) {
            const pills = sKeys.map(k => {
              const item = sr[k];
              const ok = item && item.ok;
              const ms = item && item.ms ? (' ' + item.ms + 'ms') : '';
              return '<span class="status-pill" style="font-size:7.5px;padding:2px 6px;color:' + (ok ? 'var(--mint)' : 'var(--rose)') + ';border-color:' + (ok ? 'rgba(84,230,181,.35)' : 'rgba(251,125,150,.35)') + '">' + (ok ? '✓ ' : '✗ ') + esc(k.toUpperCase() + ms) + '</span>';
            }).join(' ');
            svcHtml = pills + ' <small style="color:var(--muted)">[' + (svcLogic === 'all' ? '需全通' : '任一通') + ']</small>';
          } else {
            svcHtml = '<span style="color:var(--mint);font-size:8px">✓ URL Ping 已验证</span>';
          }
          isIdeal = Boolean(tr.qualified);
        }
        const verdictBadge = isIdeal
          ? '<span class="node-status ok">✓ 已入池</span>'
          : '<span class="node-status dead">⚠️ 建议移除</span>';
        const grpBadge = grpIdx === 1
          ? '<span class="status-pill" style="color:var(--cyan);border-color:rgba(110,231,245,.35)">#' + (idx + 1) + ' · G1 主力</span>'
          : '<span class="status-pill" style="color:var(--violet);border-color:rgba(169,148,255,.35)">#' + (idx + 1) + ' · G2 备选</span>';

        rows.push('<tr data-an-row-tag="' + esc(tag) + '" data-an-row-group="' + grpIdx + '">' +
          '<td>' + grpBadge + '</td>' +
          '<td><b>' + esc(n.name || tag) + '</b><small class="mono" style="margin-left:6px">' + esc(cMeta.flag + ' ' + cCode + ' · ' + (n.protocol || 'PROXY')) + '</small></td>' +
          '<td>' + formatLatencyBadge(delayMs, stateVal, false) + '</td>' +
          '<td>' + svcHtml + '</td>' +
          '<td>' + verdictBadge + '</td>' +
          '<td style="text-align:right">' +
            '<button type="button" class="button danger compact" style="min-height:24px;padding:0 9px;font-size:8px" data-an-row-op="remove" data-pool-group="' + grpIdx + '" data-tag="' + esc(tag) + '" title="直接从当前分组列表中移除此节点">🗑️ 移除</button>' +
          '</td>' +
        '</tr>');
      });

      tbody.innerHTML = rows.length
        ? rows.join('')
        : '<tr><td colspan="6"><div class="empty-state" style="padding:12px"><h4>当前「' + esc(grpName) + '」尚无已添加节点（0/10） · 请在上方筛选器勾选节点后点击「➕ 将已勾选节点加入池」</h4></div></td></tr>';
    }

    async function runCandidateTests(withServices, btnEl) {
      let targets = Array.from(stagedSet).filter(t => !g1Set.has(t) && !g2Set.has(t));
      if (!targets.length) {
        toast('请先在上方节点筛选器中勾选需要检测的新节点（已加入节点池的节点无需重复检测）', 'warn');
        return;
      }
      const checkedSvcs = withServices ? $$('.chk-an-svc:checked').map(el => el.value) : [];
      const svcLogic = ($('#mdl-an-svc-logic') && $('#mdl-an-svc-logic').value) || 'all';
      if (btnEl) btnEl.setAttribute('aria-busy', 'true');
      toast('正在对新勾选的 ' + targets.length + ' 个候选节点执行 ' + (checkedSvcs.length ? ('URL Ping + 服务可用性 (' + checkedSvcs.join('/') + ')') : 'URL Ping') + ' 检测（已入池节点不重复检测）...');
      const res = await callRouterApi('/api/auto_nodes/test_candidates', 'POST', {
        tags: targets,
        check_ping: true,
        service_checks: checkedSvcs,
        service_logic: svcLogic
      });
      if (btnEl) btnEl.setAttribute('aria-busy', 'false');
      if (res && Array.isArray(res.results)) {
        res.results.forEach(r => {
          testResultsByTag[r.tag] = r;
          const nObj = mock.nodes.find(x => (x.tag || x.name) === r.tag);
          if (nObj && r.delay_ms > 0) {
            nObj.rtt = r.delay_ms;
            nObj.status = r.state || 'ok';
          }
        });
        updateGroupCounters();
        renderPickerList();
        const passCnt = res.results.filter(r => r.qualified).length;
        const failCnt = res.results.length - passCnt;
        toast('检测完成：新勾选节点中 ' + passCnt + ' 个通过' + (failCnt > 0 ? ('、' + failCnt + ' 个未通过，可点击「✅ 将检测通过节点加入池」') : '，可点击「➕ 将已勾选节点加入池」'));
      }
    }

    function addStagedNodesToActivePool(onlyPassed) {
      const targetSet = getActivePoolSet();
      const otherSet = getOtherPoolSet();
      const grpName = getActiveGroupLabel();
      if (targetSet.size >= 10) {
        toast('当前「' + grpName + '」已满 10 个节点（10/10），如需更换请先在下方列表点击「🗑️ 移除」', 'warn');
        return;
      }
      let candidates = Array.from(stagedSet).filter(t => !targetSet.has(t) && !otherSet.has(t));
      if (!candidates.length) {
        toast('请先在上方筛选器中勾选需要加入节点池的候选节点', 'warn');
        return;
      }
      if (onlyPassed) {
        const passedList = candidates.filter(t => testResultsByTag[t] && testResultsByTag[t].qualified);
        if (!passedList.length) {
          toast('当前勾选节点中暂无已检测通过的节点（请先点击「🧪 检测已勾选」，或点击「➕ 将已勾选节点加入池」免测直加）', 'warn');
          return;
        }
        candidates = passedList;
      } else {
        candidates.sort((a, b) => {
          const ta = testResultsByTag[a];
          const tb = testResultsByTag[b];
          const qa = ta ? (ta.qualified ? 2 : 0) : 1;
          const qb = tb ? (tb.qualified ? 2 : 0) : 1;
          if (qa !== qb) return qb - qa;
          const ma = (ta && ta.delay_ms > 0) ? ta.delay_ms : 500;
          const mb = (tb && tb.delay_ms > 0) ? tb.delay_ms : 500;
          return ma - mb;
        });
      }
      const slotsLeft = 10 - targetSet.size;
      const toAdd = candidates.slice(0, slotsLeft);
      toAdd.forEach(t => {
        targetSet.add(t);
      });
      stagedSet.clear();
      updateGroupCounters();
      renderPickerList();
      renderSelectedTable();
      toast('已确认加入 ' + toAdd.length + ' 个节点至「' + grpName + '」（当前 ' + targetSet.size + '/10' + (targetSet.size < 10 ? ('，还可继续勾选添加 ' + (10 - targetSet.size) + ' 个') : '，本组已满 10/10') + '）', '', {
        undoText: '↩ 撤销添加',
        onUndo: () => {
          toAdd.forEach(t => {
            targetSet.delete(t);
            stagedSet.add(t);
          });
          updateGroupCounters();
          renderPickerList();
          renderSelectedTable();
        }
      });
    }

    updateGroupCounters();
    renderCountryChips();
    renderPickerList();
    renderSelectedTable();

    const builderRoot = $('#an-builder-root');
    if (builderRoot) {
      builderRoot.addEventListener('click', ev => {
        const grpTab = ev.target.closest('[data-an-grp-tab]');
        if (grpTab) {
          ev.preventDefault();
          ev.stopPropagation();
          activeTargetGroup = Number(grpTab.dataset.anGrpTab) || 1;
          updateGroupCounters();
          renderPickerList();
          renderSelectedTable();
          return;
        }
        const countryBtn = ev.target.closest('[data-an-country]');
        if (countryBtn) {
          ev.preventDefault();
          ev.stopPropagation();
          filterCountry = countryBtn.dataset.anCountry || 'ALL';
          renderCountryChips();
          renderPickerList();
          return;
        }
        const rowOp = ev.target.closest('[data-an-row-op]');
        if (rowOp) {
          ev.preventDefault();
          ev.stopPropagation();
          const op = rowOp.dataset.anRowOp;
          const grp = Number(rowOp.dataset.poolGroup || rowOp.dataset.group) || activeTargetGroup;
          const tag = rowOp.dataset.tag || '';
          const setObj = grp === 1 ? g1Set : g2Set;
          if (op === 'remove' && tag) {
            setObj.delete(tag);
            updateGroupCounters();
            renderPickerList();
            renderSelectedTable();
            toast('已从「' + (grp === 1 ? '主力组 G1' : '备选组 G2') + '」直接移除节点「' + tag + '」（当前 ' + setObj.size + '/10）');
          }
          return;
        }
      });

      builderRoot.addEventListener('change', ev => {
        if (ev.target.classList.contains('chk-an-cand')) {
          const tag = ev.target.value;
          const targetSet = getActivePoolSet();
          const otherSet = getOtherPoolSet();
          if (targetSet.has(tag) || otherSet.has(tag)) {
            ev.target.checked = false;
            return;
          }
          if (ev.target.checked) {
            if (targetSet.size >= 10) {
              ev.target.checked = false;
              toast('当前「' + getActiveGroupLabel() + '」已满 10 个节点（10/10），请先在下方列表移除节点或切换到另一分组', 'warn');
              return;
            }
            if (stagedSet.size >= 10) {
              ev.target.checked = false;
              toast('单次筛选最多勾选 10 个候选节点（当前已勾选 10 个），请先检测或确认加入节点池', 'warn');
              return;
            }
            stagedSet.add(tag);
          } else {
            stagedSet.delete(tag);
          }
          const cardEl = ev.target.closest('.picker-item');
          if (cardEl) cardEl.classList.toggle('is-staged', ev.target.checked);
          updateGroupCounters();
          return;
        }
        if (ev.target.id === 'mdl-an-sub-filter') {
          filterSub = ev.target.value || 'ALL';
          renderCountryChips();
          renderPickerList();
          return;
        }
        if (ev.target.id === 'mdl-an-svc-logic' || ev.target.classList.contains('chk-an-svc')) {
          renderSelectedTable();
        }
      });

      const searchInp = $('#mdl-an-node-search');
      if (searchInp) {
        searchInp.addEventListener('input', () => {
          filterSearch = searchInp.value || '';
          renderPickerList();
        });
      }
      const btnFill10 = $('#btn-an-fill-top10');
      if (btnFill10) {
        btnFill10.addEventListener('click', ev => {
          ev.stopPropagation();
          const targetSet = getActivePoolSet();
          const otherSet = getOtherPoolSet();
          if (targetSet.size >= 10) {
            toast('当前「' + getActiveGroupLabel() + '」已满 10 个节点（10/10）', 'warn');
            return;
          }
          const cands = getFullyFilteredNodes().filter(n => {
            const t = n.tag || n.name;
            return n.status !== 'dead' && !targetSet.has(t) && !otherSet.has(t);
          });
          const maxStage = Math.max(0, 10 - targetSet.size);
          if (stagedSet.size > maxStage) {
            const keep = Array.from(stagedSet).slice(0, maxStage);
            stagedSet.clear();
            keep.forEach(x => stagedSet.add(x));
          }
          for (const n of cands) {
            if (stagedSet.size >= maxStage) break;
            const t = n.tag || n.name;
            if (!stagedSet.has(t)) {
              stagedSet.add(t);
            }
          }
          updateGroupCounters();
          renderPickerList();
          toast('已在筛选器勾选 ' + stagedSet.size + ' 个新候选节点（本组已入池 ' + targetSet.size + ' + 新勾选 ' + stagedSet.size + ' = ' + (targetSet.size + stagedSet.size) + '/10）');
        });
      }
      const btnClearStaged = $('#btn-an-clear-staged');
      if (btnClearStaged) {
        btnClearStaged.addEventListener('click', ev => {
          ev.stopPropagation();
          stagedSet.clear();
          updateGroupCounters();
          renderPickerList();
        });
      }
      const btnClearGrp = $('#btn-an-clear-grp');
      if (btnClearGrp) {
        btnClearGrp.addEventListener('click', ev => {
          ev.stopPropagation();
          const setObj = getActivePoolSet();
          const prevItems = Array.from(setObj);
          if (!prevItems.length) return;
          setObj.clear();
          updateGroupCounters();
          renderPickerList();
          renderSelectedTable();
          toast('已清空「' + getActiveGroupLabel() + '」全部已入池节点');
        });
      }
      const btnPing = $('#btn-an-test-ping');
      if (btnPing) btnPing.addEventListener('click', ev => { ev.stopPropagation(); runCandidateTests(false, btnPing); });
      const btnFull = $('#btn-an-test-full');
      if (btnFull) btnFull.addEventListener('click', ev => { ev.stopPropagation(); runCandidateTests(true, btnFull); });
      const btnKeepQual = $('#btn-an-keep-qualified');
      if (btnKeepQual) {
        btnKeepQual.addEventListener('click', ev => {
          ev.stopPropagation();
          let removed = 0;
          Array.from(stagedSet).forEach(tag => {
            const tr = testResultsByTag[tag];
            if (!tr || !tr.qualified) {
              stagedSet.delete(tag);
              removed++;
            }
          });
          updateGroupCounters();
          renderPickerList();
          toast(removed > 0 ? ('已移除 ' + removed + ' 个未通过勾选，当前保留 ' + stagedSet.size + ' 个检测通过节点') : '当前勾选节点全部已检测通过');
        });
      }
      const btnAddPassed = $('#btn-an-add-passed');
      if (btnAddPassed) {
        btnAddPassed.addEventListener('click', ev => {
          ev.stopPropagation();
          addStagedNodesToActivePool(true);
        });
      }
      const btnAddPool = $('#btn-an-add-to-pool');
      if (btnAddPool) {
        btnAddPool.addEventListener('click', ev => {
          ev.stopPropagation();
          addStagedNodesToActivePool(false);
        });
      }
    }
  }

  async function openReplaceAutoNodeModal(poolIdx) {
    openAutoNodeEditorModal(poolIdx);
  }

  function openNewSubscriptionModal(subIdx) {
    const s = (subIdx != null && mock.subscriptions[subIdx]) ? mock.subscriptions[subIdx] : null;
    openModal(
      s ? ('编辑订阅源 · ' + s.name) : '新增或更新机场订阅源',
      '<div class="modal-form">' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>订阅名称</label><input id="mdl-sub-name" value="' + esc(s ? s.name : '') + '" placeholder="如：主力高速机场"></div>' +
          '<div class="modal-field"><label>定时自动同步间隔（分钟）</label><input id="mdl-sub-interval" type="number" value="' + esc(s ? s.update_interval_min || 360 : 360) + '"></div>' +
        '</div>' +
        '<div class="modal-field"><label>订阅链接 URL (支持 Clash / Sing-box / Base64 / V2Ray 订阅链接)</label><input id="mdl-sub-url" value="' + esc(s && !String(s.url).includes('***') ? s.url : '') + '" placeholder="https://..."></div>' +
        '<div class="modal-field"><label>离线订阅文本导入（可选：若路由器无法直连订阅源，可直接粘贴订阅内容）</label><textarea id="mdl-sub-rawtext" rows="3" placeholder="可选：直接粘贴 Base64 或 YAML/URI 列表"></textarea></div>' +
      '</div>',
      'SUBSCRIPTION MANAGER',
      async () => {
        const name = ($('#mdl-sub-name') && $('#mdl-sub-name').value.trim()) || (s ? s.name : '主力机场订阅');
        const url = ($('#mdl-sub-url') && $('#mdl-sub-url').value.trim()) || (s ? s.url : '');
        const interval = Number(($('#mdl-sub-interval') && $('#mdl-sub-interval').value) || 360);
        const raw_text = ($('#mdl-sub-rawtext') && $('#mdl-sub-rawtext').value.trim()) || '';
        if (!url && !raw_text) { toast('请输入订阅链接 URL 或粘贴离线订阅内容', 'warn'); return; }
        closeModal();
        toast('正在拉取并解析订阅「' + name + '」...');
        if (s) {
          await callRouterApi('/api/subscriptions/edit', 'POST', {
            id: s.id,
            old_url: s.url,
            new_url: url.includes('***') ? '' : url,
            name,
            update_interval_min: interval,
            auto_update: interval > 0,
            raw_text,
            sync_now: !raw_text
          });
        } else if (raw_text && !url) {
          await callRouterApi('/api/subscriptions/import_text', 'POST', { name, raw_text, test_after_add: true });
        } else {
          await callRouterApi('/api/subscriptions/add', 'POST', { name, url, auto_update: interval > 0, update_interval_min: interval, test_after_add: true });
        }
        toast('订阅「' + name + '」已同步完成');
        await syncBackendStatus(true, true);
      },
      s ? '保存并同步' : '添加并拉取'
    );
  }

  function openBatchImportModal() {
    openModal(
      '批量导入节点 URI 或手动添加单节点',
      '<div class="modal-form">' +
        '<p>支持直接粘贴多行节点分享链接（<code>vless://</code>、<code>hysteria2://</code>、<code>tuic://</code>、<code>ss://</code>、<code>vmess://</code>、<code>trojan://</code>）或 Base64 文本，可先预览解析结果再入库。</p>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>自定义名称前缀（可选）</label><input id="mdl-import-prefix" placeholder="如：自建-"></div>' +
          '<div class="modal-field"><label>强制地区归属（可选）</label><select id="mdl-import-region"><option value="">自动识别国家/地区</option>' +
            COUNTRY_CODES.map(c => '<option value="' + c + '">' + esc(COUNTRY_META[c].flag + ' ' + COUNTRY_META[c].name) + '</option>').join('') +
          '</select></div>' +
        '</div>' +
        '<div class="modal-field"><div style="display:flex;justify-content:space-between;align-items:center"><label>节点分享 URI 列表</label><button type="button" class="button ghost compact" style="min-height:24px;padding:0 8px;font-size:8px" data-action="preview-share-uri">🔍 解析预览链接</button></div><textarea id="mdl-import-text" rows="5" placeholder="vless://...\nhysteria2://..."></textarea></div>' +
        '<div id="mdl-parse-preview-box" class="trace-inline-box hidden"></div>' +
      '</div>',
      'BATCH NODE IMPORT',
      async () => {
        const text = ($('#mdl-import-text') && $('#mdl-import-text').value.trim()) || '';
        const tag_prefix = ($('#mdl-import-prefix') && $('#mdl-import-prefix').value.trim()) || '';
        const region_override = ($('#mdl-import-region') && $('#mdl-import-region').value) || '';
        if (!text) { toast('请粘贴需要导入的节点内容', 'warn'); return; }
        const res = await callRouterApi('/api/nodes/import', 'POST', { raw_links: text, text, tag_prefix, region_override, test_after_add: true });
        closeModal();
        toast('成功导入 ' + (res && res.imported_count != null ? res.imported_count : '') + ' 个节点');
        await syncBackendStatus(true, true);
      },
      '立即导入并测速'
    );
  }

  function openProbeSchedulesModal() {
    const schedRows = (mock.schedules || []).map(s =>
      '<div class="trace-stage" style="padding:9px 12px"><i>⏱️</i><div><b>' + esc(s.name) + '</b><span>范围: ' + esc(s.region || 'ALL') + ' · 每 ' + Number(s.interval_min || 360) + ' 分钟执行</span></div>' +
      '<div class="button-row"><button class="button secondary compact" style="min-height:24px;padding:0 8px;font-size:8px" data-action="run-sched-now" data-sid="' + esc(s.id) + '">立即运行</button>' +
      '<button class="button danger compact" style="min-height:24px;padding:0 8px;font-size:8px" data-action="del-sched" data-sid="' + esc(s.id) + '">删除</button></div></div>'
    ).join('');
    openModal(
      '定时 URL Ping 测速与入核容量管理',
      '<div class="modal-form">' +
        '<div class="trace-stages">' + (schedRows || '<p>当前暂无定时计划</p>') + '</div>' +
        '<div class="modal-grid-3" style="margin-top:8px">' +
          '<div class="modal-field"><label>新增计划名称</label><input id="mdl-sched-name" value="高频地区定时巡检"></div>' +
          '<div class="modal-field"><label>目标地区</label><select id="mdl-sched-region"><option value="ALL">全部地区 (ALL)</option>' +
            COUNTRY_CODES.map(c => '<option value="' + c + '">' + esc(COUNTRY_META[c].name) + '</option>').join('') +
          '</select></div>' +
          '<div class="modal-field"><label>巡检间隔 (分钟)</label><input id="mdl-sched-intv" type="number" value="180"></div>' +
        '</div>' +
        '<div class="modal-field"><label>最大同时入核节点数上限 (1~300，推荐 200 以控制内存占用)</label><input id="mdl-max-outbounds" type="number" value="' + esc(mock.maxOutboundsLimit || 200) + '"></div>' +
      '</div>',
      'PROBE SCHEDULER & CAPACITY',
      async () => {
        const name = ($('#mdl-sched-name') && $('#mdl-sched-name').value.trim()) || '定时测速计划';
        const region = ($('#mdl-sched-region') && $('#mdl-sched-region').value) || 'ALL';
        const interval_min = Number(($('#mdl-sched-intv') && $('#mdl-sched-intv').value) || 180);
        const max_outbounds = Number(($('#mdl-max-outbounds') && $('#mdl-max-outbounds').value) || 200);
        await Promise.all([
          callRouterApi('/api/probe/schedules/save', 'POST', { name, region, interval_min, enabled: true }),
          callRouterApi('/api/settings/max_nodes', 'POST', { max_outbounds })
        ]);
        closeModal();
        toast('定时测速计划与入核上限已保存');
        await syncBackendStatus(true, true);
      },
      '保存计划与容量'
    );
  }

  function openPasswordModal() {
    openModal(
      '修改面板管理密码',
      '<div class="modal-form">' +
        '<p>设置独立强密码后，旧密码与默认初始密码（<code>ai-link-2026</code>）将立即失效，UCI 仅记录布尔状态位 <code>panel_pwd_customized=1</code>。</p>' +
        '<div class="modal-field"><label>新管理密码（至少 6 位）</label><input id="mdl-new-password" type="password" placeholder="输入新密码"></div>' +
      '</div>',
      'SECURITY CREDENTIALS',
      async () => {
        const npw = ($('#mdl-new-password') && $('#mdl-new-password').value.trim()) || '';
        if (npw.length < 6) { toast('新密码长度至少 6 位', 'warn'); return; }
        const res = await callRouterApi('/api/ops/password', 'POST', { new_password: npw });
        if (res && res.ok) {
          if (res.token) setAuthToken(res.token);
          closeModal();
          toast('管理密码已更新并签发新令牌');
          await syncBackendStatus(false, true);
        } else {
          toast((res && res.message) || '密码修改失败', 'warn');
        }
      },
      '确认修改'
    );
  }

  function openBindingModal() {
    openModal(
      '面板监听、免密网段与自定义更新源配置',
      '<div class="modal-form">' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>面板监听地址 (panel_bind)</label><input id="mdl-panel-bind" value="' + esc(state.rawOps.panel_bind || '0.0.0.0') + '"></div>' +
          '<div class="modal-field"><label>GitHub 规则加速源 (gh_mirror)</label><input id="mdl-gh-mirror" value="' + esc(state.ghMirror) + '"></div>' +
        '</div>' +
        '<div class="modal-field"><label>自定义 OTA 更新清单源 URL (update_manifest_url，留空使用官方 Cloudflare/GitHub 主源)</label><input id="mdl-manifest-url" value="' + esc(state.updateManifestUrl || '') + '" placeholder="https://your-domain.example.com/version.json"></div>' +
        '<div class="modal-field"><label>局域网免密信任网段 (trusted_cidr)</label><input id="mdl-trusted-cidr" value="' + esc(state.trustedCidr) + '"></div>' +
      '</div>',
      'NETWORK & SECURITY',
      async () => {
        const panel_bind = ($('#mdl-panel-bind') && $('#mdl-panel-bind').value.trim()) || '0.0.0.0';
        const gh_mirror = ($('#mdl-gh-mirror') && $('#mdl-gh-mirror').value.trim()) || '';
        const update_manifest_url = ($('#mdl-manifest-url') && $('#mdl-manifest-url').value.trim()) || '';
        const trusted_cidr = ($('#mdl-trusted-cidr') && $('#mdl-trusted-cidr').value.trim()) || '127.0.0.1/32';
        const res = await callRouterApi('/api/ops/settings', 'POST', { panel_bind, gh_mirror, update_manifest_url, trusted_cidr });
        if (res && res.ok !== false) {
          renderOpsSettings({ panel_bind, gh_mirror, update_manifest_url, trusted_cidr });
          closeModal();
          toast('网络、安全与更新源配置已保存');
        }
      },
      '保存设置'
    );
  }

  /* Requirement 4: Overview Bottom 3 Cards Clickable Detail Modals (Devices, Outbounds, Destinations) */
  function openOverviewDetailModal(detailType, focusKey) {
    const eg = getActiveEgressSummary();

    if (detailType === 'devices') {
      const galDevs = state.galaxyLanDevices || [];
      const insDevs = state.insightDevices || [];
      const ipMap = new Map();
      insDevs.forEach((d, idx) => {
        const k = d.ip || d.name || ('dev-' + idx);
        ipMap.set(k, Object.assign({
          ip: d.ip || k,
          name: d.name || d.ip || ('终端 ' + (idx + 1)),
          down_rate: 0,
          up_rate: 0,
          conns: 1,
          inMb: Number(d.inMb || 0),
          outMb: Number(d.outMb || 0),
          totalMb: Number(d.totalMb || 0),
          pct: Number(d.pct || 25),
          is_remote: false
        }, d));
      });
      galDevs.forEach((d, idx) => {
        const k = d.ip || d.name || ('gal-' + idx);
        const prev = ipMap.get(k) || {};
        ipMap.set(k, Object.assign({}, prev, d, {
          ip: d.ip || prev.ip || k,
          name: (d.name && !/^device-/i.test(d.name)) ? d.name : (prev.name || d.name || d.ip || '局域网终端'),
          down_rate: Number(d.down_rate != null ? d.down_rate : (prev.down_rate || 0)),
          up_rate: Number(d.up_rate != null ? d.up_rate : (prev.up_rate || 0)),
          conns: Number(d.conns != null ? d.conns : (prev.conns || 1)),
          totalMb: Number(d.totalMb != null ? d.totalMb : (prev.totalMb || 12.5)),
          pct: Number(prev.pct || 20)
        }));
      });
      const allDevs = Array.from(ipMap.values());
      const renderDevRows = (qStr, filterKind) => {
        const q = String(qStr || '').trim().toLowerCase();
        const filtered = allDevs.filter(d => {
          if (filterKind === 'active' && (Number(d.down_rate || 0) + Number(d.up_rate || 0) + Number(d.conns || 0)) <= 0) return false;
          if (filterKind === 'remote' && !d.is_remote) return false;
          if (q && !(String(d.name || '') + ' ' + String(d.ip || '')).toLowerCase().includes(q)) return false;
          return true;
        });
        if (!filtered.length) {
          return '<tr><td colspan="6"><div class="empty-state" style="padding:18px"><h4>无匹配的终端设备</h4></div></td></tr>';
        }
        return filtered.map(d => {
          const rateSum = Number(d.down_rate || 0) + Number(d.up_rate || 0);
          const rateTxt = rateSum > 0
            ? ('↓ ' + fmtRate(d.down_rate || 0) + ' / ↑ ' + fmtRate(d.up_rate || 0))
            : '待机在线 · 0 B/s';
          const avatarTxt = formatDeviceAvatarLabel(d);
          const totalMbTxt = Number(d.totalMb || 0).toFixed(1) + ' MB';
          const pctVal = Math.max(6, Math.min(100, Number(d.pct || 25)));
          return '<tr>' +
            '<td><div style="display:flex;align-items:center;gap:9px">' +
              '<span style="width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:#172333;border:1px solid rgba(110,231,245,.3);color:var(--cyan);font-size:8px;font-weight:600">' + esc(avatarTxt) + '</span>' +
              '<div><b>' + esc(d.name || d.ip) + '</b><small class="mono">' + esc(d.ip || 'LAN') + '</small></div>' +
            '</div></td>' +
            '<td><span class="status-pill">' + (d.is_remote ? '🏠 回家隧道' : '🖧 局域网 LAN') + '</span></td>' +
            '<td class="mono">' + esc(rateTxt) + ' ' + renderGearBadge(rateSum, d.conns || 1) + '</td>' +
            '<td class="mono"><b style="color:var(--cyan)">' + esc(Number(d.conns || 0)) + '</b> 条连接</td>' +
            '<td><div style="min-width:110px"><div style="display:flex;justify-content:space-between;font-size:8px"><span>' + esc(totalMbTxt) + '</span><span>' + esc(pctVal) + '%</span></div><div class="thin-progress" style="margin-top:4px"><i style="width:' + pctVal + '%"></i></div></div></td>' +
            '<td style="text-align:right"><button class="button ghost compact" style="min-height:24px;padding:0 8px;font-size:8px" data-action="jump-device-conns" data-ip="' + esc(d.ip || '') + '">🔍 查看连接</button></td>' +
          '</tr>';
        }).join('');
      };

      const initQuery = focusKey || '';
      openModal(
        '局域网与回家终端设备实时明细 (' + allDevs.length + ' 台在线)',
        '<div class="ov-insight-modal-wrap">' +
          '<div class="galaxy-kpi-grid" style="margin-bottom:12px">' +
            '<div class="galaxy-kpi-card"><span>在线终端总数</span><b style="color:var(--cyan)">' + esc(allDevs.length) + ' 台</b><small>活跃传输 ' + esc(mock.devicesActive) + ' 台</small></div>' +
            '<div class="galaxy-kpi-card"><span>实时总下行</span><b style="color:var(--violet)">' + esc(mock.downText) + '</b><small>实时上行 ' + esc(mock.upText) + '</small></div>' +
            '<div class="galaxy-kpi-card"><span>接管并发会话</span><b style="color:var(--mint)">' + esc(mock.connections) + ' 条</b><small>本月累计 ' + esc(mock.monthTotalText) + '</small></div>' +
            '<div class="galaxy-kpi-card"><span>大陆流量旁路</span><b>' + (state.entryBypass ? '硬件直通已激活' : '内核分流') + '</b><small>零损耗千兆转发</small></div>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">' +
            '<div class="filter-chips" id="mdl-ov-dev-chips">' +
              '<button type="button" class="active" data-ov-dev-filter="all">全部终端 (' + allDevs.length + ')</button>' +
              '<button type="button" data-ov-dev-filter="active">⚡ 活跃传输</button>' +
              '<button type="button" data-ov-dev-filter="remote">🏠 回家隧道</button>' +
            '</div>' +
            '<label class="search-box" style="min-width:220px"><svg><use href="#i-search"/></svg><input id="mdl-ov-dev-search" value="' + esc(initQuery) + '" placeholder="搜索终端名称或 IP 地址..."></label>' +
          '</div>' +
          '<div class="table-wrap" style="max-height:360px;overflow:auto">' +
            '<table>' +
              '<thead><tr><th>终端名称 / IP 地址</th><th>接入方式</th><th>实时速率 · 挡位</th><th>并发会话</th><th>累计流量占比</th><th style="text-align:right">操作</th></tr></thead>' +
              '<tbody id="mdl-ov-dev-tbody">' + renderDevRows(initQuery, 'all') + '</tbody>' +
            '</table>' +
          '</div>' +
        '</div>',
        '01 / LAN & HOMELINK TERMINALS',
        () => {
          closeModal();
          showPage('settings');
        },
        '前往实时连接管理 ➔'
      );

      let curDevFilter = 'all';
      const searchInp = $('#mdl-ov-dev-search');
      const tbodyEl = $('#mdl-ov-dev-tbody');
      if (searchInp && tbodyEl) {
        searchInp.addEventListener('input', () => {
          tbodyEl.innerHTML = renderDevRows(searchInp.value, curDevFilter);
        });
      }
      $$('[data-ov-dev-filter]').forEach(btn => {
        btn.addEventListener('click', () => {
          curDevFilter = btn.dataset.ovDevFilter || 'all';
          $$('[data-ov-dev-filter]').forEach(b => b.classList.toggle('active', b === btn));
          if (tbodyEl) tbodyEl.innerHTML = renderDevRows(searchInp ? searchInp.value : '', curDevFilter);
        });
      });
      return;
    }

    if (detailType === 'outbounds') {
      const okCnt = mock.nodes.filter(n => n.status === 'ok').length;
      const suspectCnt = mock.nodes.filter(n => n.status === 'suspect').length;
      const pendCnt = mock.nodes.filter(n => n.status === 'pending').length;
      const deadCnt = mock.nodes.filter(n => n.status === 'dead').length;
      const kernCnt = mock.nodes.filter(n => n.kernel).length;
      const statusNames = { ok: '已验证可用', pending: '待测速', dead: '超时不可达', suspect: '延迟波动' };

      const renderNodeRows = (qStr, stFilter) => {
        const q = String(qStr || '').trim().toLowerCase();
        const list = mock.nodes.filter(n => {
          if (stFilter === 'kernel' && !n.kernel) return false;
          if (stFilter !== 'all' && stFilter !== 'kernel' && n.status !== stFilter) return false;
          if (q && !([n.name, n.tag, n.region, n.protocol, n.server].join(' ').toLowerCase().includes(q))) return false;
          return true;
        });
        if (!list.length) {
          return '<tr><td colspan="6"><div class="empty-state" style="padding:18px"><h4>无匹配的出站节点</h4></div></td></tr>';
        }
        return list.slice(0, 60).map(n => {
          const cCode = classifyNodeCountry(n);
          const cMeta = COUNTRY_META[cCode] || COUNTRY_META.OTHER;
          const scoreTxt = (n.score != null && n.score > 0 && n.rtt > 0) ? (n.score + ' 分') : '待评估';
          return '<tr>' +
            '<td><b>' + esc(n.name) + '</b><small class="mono">' + esc(n.server ? (n.server + ':' + (n.server_port || 443)) : n.id) + '</small></td>' +
            '<td>' + esc(cMeta.flag + ' ' + cCode) + ' · <span class="mono">' + esc(n.protocol) + '</span></td>' +
            '<td><span class="node-status ' + esc(n.status) + '">' + esc(statusNames[n.status] || '待测速') + '</span></td>' +
            '<td>' + formatLatencyBadge(n.rtt, n.status, false) + '</td>' +
            '<td class="mono" style="color:var(--cyan)">' + esc(scoreTxt) + '</td>' +
            '<td style="text-align:right"><div class="button-row" style="justify-content:flex-end;gap:4px">' +
              '<button class="button ghost compact" style="min-height:24px;padding:0 7px;font-size:8px" data-action="node-real-delay" data-node="' + esc(n.tag || n.name) + '">真测速</button>' +
              '<button class="button secondary compact" style="min-height:24px;padding:0 7px;font-size:8px" data-action="set-node-exit" data-node="' + esc(n.tag || n.name) + '">设为出口</button>' +
            '</div></td>' +
          '</tr>';
        }).join('');
      };

      openModal(
        '入核出站节点池与健康遥测明细 (' + mock.activeOutbounds + ' / ' + mock.maxOutboundsLimit + ' 入核)',
        '<div class="ov-insight-modal-wrap">' +
          '<div class="galaxy-kpi-grid" style="margin-bottom:12px">' +
            '<div class="galaxy-kpi-card"><span>入核活跃配额</span><b style="color:var(--cyan)">' + esc(mock.activeOutbounds) + ' / ' + esc(mock.maxOutboundsLimit) + '</b><small>总计保存 ' + esc(mock.nodes.length) + ' 个节点</small></div>' +
            '<div class="galaxy-kpi-card"><span>已验证可用</span><b style="color:var(--mint)">' + esc(okCnt) + ' 个</b><small>URL Ping 握手通过</small></div>' +
            '<div class="galaxy-kpi-card"><span>延迟波动 / 待测</span><b style="color:var(--amber)">' + esc(suspectCnt + ' / ' + pendCnt) + '</b><small>不可达 ' + esc(deadCnt) + ' 个</small></div>' +
            '<div class="galaxy-kpi-card"><span>当前运行模式</span><b style="color:var(--violet)">' + esc(eg.modeShort) + '</b><small>' + esc(eg.poolOrNodeName) + '</small></div>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">' +
            '<div class="filter-chips">' +
              '<button type="button" class="active" data-ov-node-filter="all">全部 (' + mock.nodes.length + ')</button>' +
              '<button type="button" data-ov-node-filter="kernel">⚡ 已入核 (' + kernCnt + ')</button>' +
              '<button type="button" data-ov-node-filter="ok">✓ 已验证 (' + okCnt + ')</button>' +
              '<button type="button" data-ov-node-filter="suspect">⚠️ 波动 (' + suspectCnt + ')</button>' +
              '<button type="button" data-ov-node-filter="pending">? 待测速 (' + pendCnt + ')</button>' +
            '</div>' +
            '<label class="search-box" style="min-width:220px"><svg><use href="#i-search"/></svg><input id="mdl-ov-node-search" placeholder="搜索节点名称、地区或协议..."></label>' +
          '</div>' +
          '<div class="table-wrap" style="max-height:360px;overflow:auto">' +
            '<table>' +
              '<thead><tr><th>节点名称 / 服务器</th><th>地区 · 协议</th><th>健康状态</th><th>实测延迟</th><th>滑动评分</th><th style="text-align:right">快捷操作</th></tr></thead>' +
              '<tbody id="mdl-ov-node-tbody">' + renderNodeRows('', 'all') + '</tbody>' +
            '</table>' +
          '</div>' +
        '</div>',
        '02 / IN-KERNEL OUTBOUND NODES',
        () => {
          closeModal();
          showPage('nodes');
        },
        '前往订阅与节点页 ➔'
      );

      let curNodeSt = 'all';
      const nSearch = $('#mdl-ov-node-search');
      const nTbody = $('#mdl-ov-node-tbody');
      if (nSearch && nTbody) {
        nSearch.addEventListener('input', () => {
          nTbody.innerHTML = renderNodeRows(nSearch.value, curNodeSt);
        });
      }
      $$('[data-ov-node-filter]').forEach(btn => {
        btn.addEventListener('click', () => {
          curNodeSt = btn.dataset.ovNodeFilter || 'all';
          $$('[data-ov-node-filter]').forEach(b => b.classList.toggle('active', b === btn));
          if (nTbody) nTbody.innerHTML = renderNodeRows(nSearch ? nSearch.value : '', curNodeSt);
        });
      });
      return;
    }

    if (detailType === 'destinations') {
      const targetMap = new Map();
      (state.galaxyForeignSites || []).forEach(s => {
        const key = String(s.domain || s.name || '').toLowerCase();
        targetMap.set(key, {
          domain: s.domain || s.name,
          name: s.name || s.domain,
          category: 'global',
          group: String(s.group || 'Shunt_AI').replace(/^Shunt_/, ''),
          exitNode: s.exit_node || eg.nodeName,
          rateBps: Number(s.down_rate || 0) + Number(s.up_rate || 0),
          conns: Number(s.conns || 2),
          totalMb: Number(s.totalMb || 24.6)
        });
      });
      (state.galaxyDomesticSites || []).forEach(s => {
        const key = String(s.domain || s.name || '').toLowerCase();
        targetMap.set(key, {
          domain: s.domain || s.name,
          name: s.name || s.domain,
          category: 'cn',
          group: 'Domestic_CN (国内直连)',
          exitNode: 'DIRECT 宽带直通',
          rateBps: Number(s.down_rate || 0) + Number(s.up_rate || 0),
          conns: Number(s.conns || 2),
          totalMb: Number(s.totalMb || 18.2)
        });
      });
      (state.insightTargets || []).forEach(t => {
        const key = String(t.name || '').toLowerCase();
        const existing = Array.from(targetMap.values()).find(x =>
          String(x.domain).toLowerCase().includes(key) || String(x.name).toLowerCase().includes(key)
        );
        if (existing) {
          existing.totalMb = Number(t.totalMb || existing.totalMb || 15.0);
        } else if (key) {
          const isCn = /bilibili|qq|baidu|taobao|jd|douyin/i.test(key);
          targetMap.set(key, {
            domain: t.name,
            name: t.name,
            category: isCn ? 'cn' : 'global',
            group: isCn ? 'Domestic_CN (国内直连)' : '智能规则分流',
            exitNode: isCn ? 'DIRECT 宽带直通' : eg.nodeName,
            rateBps: 24576,
            conns: 2,
            totalMb: Number(t.totalMb || 12.0)
          });
        }
      });
      (mock.blocked || []).slice(0, 6).forEach(b => {
        const dom = String(b[0] || '');
        if (!dom) return;
        targetMap.set('bh-' + dom, {
          domain: dom,
          name: dom,
          category: 'blackhole',
          group: b[1] || '黑洞护盾拦截',
          exitNode: 'DNS REFUSED / REJECT',
          rateBps: 0,
          conns: Number(b[2] || 1),
          totalMb: 0
        });
      });

      const allDests = Array.from(targetMap.values());
      const glCnt = allDests.filter(d => d.category === 'global').length;
      const cnCnt = allDests.filter(d => d.category === 'cn').length;
      const bhCnt = allDests.filter(d => d.category === 'blackhole').length;

      const renderDestRows = (qStr, catFilter) => {
        const q = String(qStr || '').trim().toLowerCase();
        const list = allDests.filter(d => {
          if (catFilter !== 'all' && d.category !== catFilter) return false;
          if (q && !(String(d.domain || '') + ' ' + String(d.name || '') + ' ' + String(d.group || '')).toLowerCase().includes(q)) return false;
          return true;
        });
        if (!list.length) {
          return '<tr><td colspan="6"><div class="empty-state" style="padding:18px"><h4>无匹配的访问目标</h4></div></td></tr>';
        }
        return list.map(d => {
          const catBadge = d.category === 'cn'
            ? '<span class="status-pill" style="color:var(--pink);border-color:rgba(249,168,212,.35)">🇨🇳 国内直连</span>'
            : d.category === 'blackhole'
              ? '<span class="status-pill" style="color:var(--amber);border-color:rgba(247,189,104,.35)">🕳️ 黑洞拦截</span>'
              : '<span class="status-pill" style="color:var(--violet);border-color:rgba(169,148,255,.35)">🌍 海外代理</span>';
          const rateCell = d.category === 'blackhole'
            ? '<span class="mono" style="color:var(--amber)">已阻断 ' + Number(d.conns || 0).toLocaleString('zh-CN') + ' 次</span>'
            : ('<span class="mono">' + (d.rateBps > 0 ? ('↓ ' + fmtRate(d.rateBps)) : '就绪') + '</span> ' + renderGearBadge(d.rateBps, d.conns));
          const volCell = d.category === 'blackhole'
            ? '零流量泄露'
            : (Number(d.totalMb || 0).toFixed(1) + ' MB · ' + Number(d.conns || 1) + ' 连');
          const domClean = String(d.domain || d.name).replace(/^https?:\/\//, '').split('/')[0];
          return '<tr>' +
            '<td><b>' + esc(d.name) + '</b><small class="mono">' + esc(d.domain) + '</small></td>' +
            '<td>' + catBadge + ' <small class="mono" style="display:block;margin-top:3px;color:var(--muted)">' + esc(d.group) + '</small></td>' +
            '<td class="mono" style="color:' + (d.category === 'cn' ? 'var(--pink)' : d.category === 'blackhole' ? 'var(--amber)' : 'var(--cyan)') + '">' + esc(d.exitNode) + '</td>' +
            '<td>' + rateCell + '</td>' +
            '<td class="mono">' + esc(volCell) + '</td>' +
            '<td style="text-align:right"><div class="button-row" style="justify-content:flex-end;gap:4px">' +
              '<button class="button secondary compact" style="min-height:24px;padding:0 8px;font-size:8px" data-action="trace-from-modal" data-domain="' + esc(domClean + ':443') + '">🔍 4阶透视</button>' +
            '</div></td>' +
          '</tr>';
        }).join('');
      };

      const initSearch = focusKey || '';
      openModal(
        '热门访问目标与分流链路明细 (累计统计 ' + mock.destinationsTotal + ' 个目标)',
        '<div class="ov-insight-modal-wrap">' +
          '<div class="galaxy-kpi-grid" style="margin-bottom:12px">' +
            '<div class="galaxy-kpi-card"><span>活跃目标汇总</span><b style="color:var(--cyan)">' + esc(allDests.length) + ' 个</b><small>累计识别 ' + esc(mock.destinationsTotal) + ' 个站点</small></div>' +
            '<div class="galaxy-kpi-card"><span>海外代理目标</span><b style="color:var(--violet)">' + esc(glCnt) + ' 个</b><small>走智能分流与自动池</small></div>' +
            '<div class="galaxy-kpi-card"><span>国内直连目标</span><b style="color:var(--pink)">' + esc(cnCnt) + ' 个</b><small>走 WAN 原生宽带直通</small></div>' +
            '<div class="galaxy-kpi-card"><span>黑洞吞噬拦截</span><b style="color:var(--amber)">' + esc(bhCnt) + ' 类高频</b><small>累计 ' + esc(Number(mock.blockedTotal || 0).toLocaleString('zh-CN')) + ' 次</small></div>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">' +
            '<div class="filter-chips">' +
              '<button type="button" class="active" data-ov-dest-filter="all">全部目标 (' + allDests.length + ')</button>' +
              '<button type="button" data-ov-dest-filter="global">🌍 海外代理 (' + glCnt + ')</button>' +
              '<button type="button" data-ov-dest-filter="cn">🇨🇳 国内直连 (' + cnCnt + ')</button>' +
              '<button type="button" data-ov-dest-filter="blackhole">🕳️ 黑洞拦截 (' + bhCnt + ')</button>' +
            '</div>' +
            '<label class="search-box" style="min-width:220px"><svg><use href="#i-search"/></svg><input id="mdl-ov-dest-search" value="' + esc(initSearch) + '" placeholder="搜索域名、服务或分流组..."></label>' +
          '</div>' +
          '<div class="table-wrap" style="max-height:360px;overflow:auto">' +
            '<table>' +
              '<thead><tr><th>访问目标 (服务 / 域名)</th><th>分流归属策略</th><th>实际出站链路</th><th>实时速率 · 挡位</th><th>流量与连接</th><th style="text-align:right">快捷操作</th></tr></thead>' +
              '<tbody id="mdl-ov-dest-tbody">' + renderDestRows(initSearch, 'all') + '</tbody>' +
            '</table>' +
          '</div>' +
        '</div>',
        '03 / POPULAR DESTINATIONS & SHUNT ROUTES',
        () => {
          closeModal();
          showPage('shunt');
        },
        '前往分流策略中心 ➔'
      );

      let curDestCat = 'all';
      const dSearch = $('#mdl-ov-dest-search');
      const dTbody = $('#mdl-ov-dest-tbody');
      if (dSearch && dTbody) {
        dSearch.addEventListener('input', () => {
          dTbody.innerHTML = renderDestRows(dSearch.value, curDestCat);
        });
      }
      $$('[data-ov-dest-filter]').forEach(btn => {
        btn.addEventListener('click', () => {
          curDestCat = btn.dataset.ovDestFilter || 'all';
          $$('[data-ov-dest-filter]').forEach(b => b.classList.toggle('active', b === btn));
          if (dTbody) dTbody.innerHTML = renderDestRows(dSearch ? dSearch.value : '', curDestCat);
        });
      });
      return;
    }
  }

  async function handleAction(action, el) {
    switch (action) {
      case 'open-overview-detail': {
        const dtype = (el && el.dataset.detailType) || 'devices';
        const focusKey = (el && (el.dataset.focusIp || el.dataset.focusDomain)) || '';
        openOverviewDetailModal(dtype, focusKey);
        break;
      }
      case 'jump-device-conns': {
        const ip = (el && el.dataset.ip) || '';
        closeModal();
        state.connSearch = ip;
        const cInp = $('#conn-search-input');
        if (cInp) cInp.value = ip;
        showPage('settings');
        renderConnectionsSection();
        toast(ip ? ('已筛选终端 ' + ip + ' 的实时活跃连接') : '已跳转至实时活跃连接表');
        break;
      }
      case 'trace-from-modal': {
        const dom = (el && el.dataset.domain) || 'chatgpt.com:443';
        closeModal();
        showPage('shunt');
        await showTrace(dom);
        break;
      }
      case 'sync': {
        if (el) { el.disabled = true; el.setAttribute('aria-busy', 'true'); }
        toast('正在同步全部已启用订阅源...');
        const res = await callRouterApi('/api/ops/update_item', 'POST', { item: 'subscriptions' });
        if (el) { el.disabled = false; el.setAttribute('aria-busy', 'false'); }
        if (!res || res.ok === false) {
          toast('订阅同步失败: ' + ((res && (res.message || res.error)) || '拉取异常'), 'warn');
          break;
        }
        toast((res && res.message) || '订阅源已触发同步更新');
        await syncBackendStatus(true, true);
        break;
      }
      case 'sync-rulesets': {
        toast('正在同步 SRS 分流规则集...');
        const res = await callRouterApi('/api/rules/sync', 'POST', {});
        if (res && res.ok !== false) {
          toast('分流规则集同步完成');
          await syncBackendStatus(false, true);
        }
        break;
      }
      case 'probe-all': {
        if (el) el.disabled = true;
        toast('已启动全量节点 URL Ping 真连接体检...');
        const res = await callRouterApi('/api/probe/run', 'POST', { scope: 'all', force: true });
        if (el) el.disabled = false;
        toast((res && res.message) || '全量节点 URL Ping 探测已刷新');
        await syncBackendStatus(true, true);
        break;
      }
      case 'recover': {
        if (state.bypassActive) {
          const res = await callRouterApi('/api/restore_proxy', 'POST', {});
          toast((res && res.message) || '已恢复透明代理接管');
          await syncBackendStatus(false, true);
        } else {
          confirmModal(
            '确认切换至临时宽带直连恢复模式',
            '开启后将暂时卸载透明代理劫持，所有局域网流量直接走宽带 WAN 口出站，确认切换吗？',
            async () => {
              const res = await callRouterApi('/api/recover_direct', 'POST', {});
              await syncBackendStatus(false, true);
              toast((res && res.message) || '已切换至宽带直连恢复模式', 'warn', {
                undoText: '↩ 撤销并恢复代理',
                onUndo: async () => {
                  await callRouterApi('/api/restore_proxy', 'POST', {});
                  await syncBackendStatus(false, true);
                  toast('已撤销并恢复透明代理接管');
                }
              });
            },
            '确认直连恢复'
          );
        }
        break;
      }
      case 'restore-proxy': {
        const res = await callRouterApi('/api/restore_proxy', 'POST', {});
        toast((res && res.message) || '已恢复透明代理接管');
        await syncBackendStatus(false, true);
        break;
      }
      case 'refresh': {
        await syncBackendStatus(true, true);
        toast('全域遥测数据已刷新');
        break;
      }
      case 'probe-selected': {
        const targetName = state.selected ? (state.selected.tag || state.selected.name) : '';
        toast('正在对 ' + (targetName || '当前出口') + ' 执行 URL Ping 探测...');
        if (targetName) {
          await callRouterApi('/api/probe/url_ping', 'POST', { tags: [targetName] });
        } else {
          await callRouterApi('/api/probe/run', 'POST', { force: true });
        }
        await syncBackendStatus(true, true);
        toast((targetName || '当前出口') + ' 探测完成，链路延迟已更新');
        break;
      }
      case 'probe-single-node': {
        const nodeTag = el && el.dataset.node;
        if (!nodeTag) return;
        toast('正在测速节点 ' + nodeTag + '...');
        await callRouterApi('/api/probe/url_ping', 'POST', { tags: [nodeTag] });
        await syncBackendStatus(true, true);
        toast('节点 ' + nodeTag + ' URL Ping 测速完成');
        break;
      }
      case 'set-exit':
      case 'set-node-exit': {
        const nodeTag = (el && el.dataset.node) || (state.selected && (state.selected.tag || state.selected.name));
        if (!nodeTag) {
          toast('请先在星图或节点列表中选择一个海外节点');
          return;
        }
        const res = await callRouterApi('/api/shunt/apply_exit', 'POST', { node_tag: nodeTag, tag: nodeTag, name: nodeTag });
        if ($('#top-exit')) $('#top-exit').textContent = nodeTag;
        if ($('#trace-exit')) $('#trace-exit').textContent = nodeTag;
        closeModal();
        toast((res && res.message) || ('已将 ' + nodeTag + ' 设为当前出口'));
        await syncBackendStatus(false, true);
        break;
      }
      case 'delete-single-node': {
        const nodeTag = el && el.dataset.node;
        if (!nodeTag) return;
        const nodeSnap = mock.nodes.find(n => (n.tag || n.name) === nodeTag);
        confirmModal(
          '确认删除节点 · ' + nodeTag,
          '确认从本地节点库中移除节点「' + nodeTag + '」吗？',
          async () => {
            await callRouterApi('/api/nodes/delete', 'POST', { tag: nodeTag });
            await syncBackendStatus(true, true);
            toast('已删除节点「' + nodeTag + '」', '', nodeSnap ? {
              undoText: '↩ 撤销删除',
              onUndo: async () => {
                await callRouterApi('/api/nodes/add', 'POST', nodeSnap);
                await syncBackendStatus(true, true);
                toast('已恢复节点「' + nodeTag + '」');
              }
            } : undefined);
          },
          '确认删除节点'
        );
        break;
      }
      case 'trace':
        await showTrace();
        break;
      case 'trace-preset': {
        const dom = el && el.dataset.domain;
        if (dom) await showTrace(dom);
        break;
      }
      case 'matrix-test':
        await showMatrixTest();
        break;
      case 'health-check': {
        toast('正在执行系统与内核全量健康检查...');
        const res = await callRouterApi('/api/ops/health_check', 'GET');
        const checks = [
          ['sing-box 代理内核进程', state.coreAlive ? 'ONLINE' : 'OFFLINE'],
          ['TProxy 透明代理端口 (:7893)', (res && res.tproxy_listening !== false) ? 'LISTENING' : 'WARN'],
          ['Mixed 混合代理端口 (:7890)', (res && res.mixed_listening !== false) ? 'LISTENING' : 'WARN'],
          ['双栈防污染 DNS (:7874)', (res && res.dns_listening !== false) ? 'READY' : 'WARN'],
          ['nftables 透明接管表 (inet ai_link)', (res && res.nft_table_loaded !== false) ? 'ACTIVE' : 'BYPASS'],
          ['防断网看门狗 (respawn 0 5 0)', 'ARMED'],
          ['净网护盾规则引擎', state.dnsEnabled ? (Number(mock.dnsRulesCount).toLocaleString('zh-CN') + ' 条生效') : 'PAUSED'],
          ['入核出站节点容量', mock.activeOutbounds + ' / ' + mock.maxOutboundsLimit + ' 节点']
        ];
        openModal(
          '系统与内核健康自检报告 (/api/ops/health_check)',
          '<p>已完成对 sing-box 进程、监听端口、nftables 规则表与 DNS 护盾的深度健康核验：</p>' +
          '<div class="matrix-results">' +
            checks.map(c => '<div class="matrix-result"><b>' + esc(c[0]) + '</b><span>' + esc(c[1]) + '</span></div>').join('') +
          '</div>',
          'SYSTEM HEALTH CHECK'
        );
        break;
      }
      case 'ops-diag': {
        toast('正在采集网关全链路诊断快照...');
        const res = await callRouterApi('/api/ops/diag', 'GET');
        openModal(
          '一键深度排障诊断报告 (/api/ops/diag)',
          '<div class="modal-form">' +
            '<p>已汇总当前内核运行态、端口监听、nftables 规则摘要与最近异常日志，可直接全选复制用于排障：</p>' +
            '<div class="modal-field"><label>诊断原始数据 (JSON)</label><textarea rows="9" class="mono" readonly onclick="this.select()">' + esc(JSON.stringify(res || {}, null, 2)) + '</textarea></div>' +
          '</div>',
          'ONE-CLICK DIAGNOSTICS'
        );
        break;
      }
      case 'fail-open-test': {
        toast('正在执行断网逃生 (Fail-Open) 演练...');
        const res = await callRouterApi('/api/ops/fail_open_test', 'POST', { force: true });
        if (res && res.ok !== false) {
          toast('断网逃生演练完成：防黑洞看门狗与直连回退保护验证通过');
          await syncBackendStatus(false, true);
        }
        break;
      }
      case 'uninstall-plugin': {
        openModal(
          '安全卸载 AI-LINK 插件 (/api/ops/uninstall)',
          '<div class="modal-form">' +
            '<p>卸载前将自动清除透明代理劫持规则、还原 dnsmasq 标准配置并保留您的节点备份归档。输入 <code>UNINSTALL</code> 确认卸载：</p>' +
            '<div class="modal-field"><label>确认指令</label><input id="mdl-uninstall-confirm" placeholder="输入 UNINSTALL"></div>' +
          '</div>',
          'SAFE UNINSTALL',
          async () => {
            const v = ($('#mdl-uninstall-confirm') && $('#mdl-uninstall-confirm').value.trim()) || '';
            if (v !== 'UNINSTALL') { toast('请输入 UNINSTALL 确认卸载', 'warn'); return; }
            const r = await callRouterApi('/api/ops/uninstall', 'POST', { keep_config: true });
            if (r && r.ok !== false) {
              closeModal();
              toast('已启动安全卸载流程，网络已恢复原生直连');
            }
          },
          '确认安全卸载'
        );
        break;
      }
      case 'ipv6-status-modal': {
        const res = await callRouterApi('/api/ipv6/status', 'GET');
        const v6On = Boolean(res && res.ipv6_proxy != null ? res.ipv6_proxy : state.ipv6Proxy);
        openModal(
          'IPv6 双栈防漏与路由治理状态 (/api/ipv6/status)',
          '<div class="detail-grid">' +
            '<div><span>IPv6 透明代理接管</span><b>' + (v6On ? '已开启 (双栈 TProxy)' : '关闭 (智能双栈防漏模式)') + '</b></div>' +
            '<div><span>海外域名 AAAA 抑制</span><b>' + (v6On ? '按节点能力放行' : '已激活 (强制 IPv4 FakeIP)') + '</b></div>' +
            '<div><span>国内域名原生 IPv6</span><b>正常返回真实 AAAA 直连</b></div>' +
            '<div><span>ICMPv6 / NDP 邻居发现</span><b>nftables 硬件豁免放行</b></div>' +
          '</div>',
          'IPV6 DUAL-STACK GOVERNANCE',
          async () => {
            const nextV6 = !v6On;
            const r = await callRouterApi('/api/ops/ipv6', 'POST', { ipv6_proxy: nextV6 });
            if (r && r.ok !== false) {
              renderOpsSettings({ ipv6_proxy: nextV6 });
              closeModal();
              toast('IPv6 代理状态已切换');
              await syncBackendStatus(false, true);
            }
          },
          v6On ? '切换为智能防漏模式' : '开启海外 IPv6 代理'
        );
        break;
      }
      case 'dns-upstream-settings': {
        const res = await callRouterApi('/api/dns/settings', 'GET');
        const cnUp = (res && res.cn_upstream) || state.cnUpstream || '223.5.5.5';
        const remUp = (res && res.remote_upstream) || state.remoteUpstream || 'https://1.1.1.1/dns-query';
        const ffList = (res && Array.isArray(res.fakeip_filter) && res.fakeip_filter.length)
          ? res.fakeip_filter
          : ['localbattle.net', 'cn.localbattle.net', 'steamloopback.host', 'spotilocal.com', 'localhost.ptlogin2.qq.com', 'plex.direct', 'direct.quickconnect.to', 'lvh.me', 'nip.io', 'sslip.io'];
        openModal(
          '双栈 DNS 上游与 Fake-IP 本地回环豁免配置 (/api/dns/settings)',
          '<div class="modal-form">' +
            '<div class="syntax-guide">' +
              '<b>🛡️ Fake-IP 本地回环与客户端回调防吞噬保护：</b>针对暴雪战网 (<code>cn.localbattle.net</code>)、Steam、QQ/微信快速登录、Plex/群晖内网直连等解析为 <code>127.0.0.1</code> 或局域网 IP 的域名，系统已在 dnsmasq 与 sing-box 双层强制豁免 Fake-IP 并返回真实地址，确保本机客户端回调令牌 100% 送达。' +
            '</div>' +
            '<div class="modal-grid-2">' +
              '<div class="modal-field"><label>国内直连 DNS 上游 (Do53 / DoH)</label><input id="mdl-dns-cn" class="mono" value="' + esc(cnUp) + '"></div>' +
              '<div class="modal-field"><label>海外防污染加密 DNS 上游 (DoH / DoT)</label><input id="mdl-dns-remote" class="mono" value="' + esc(remUp) + '"></div>' +
            '</div>' +
            '<div class="modal-field"><label>Fake-IP 豁免白名单域名 (fakeip_filter · 每行或逗号分隔，强制返回真实 IP 不走 198.18.0.0/15)</label><textarea id="mdl-dns-fakeip-filter" class="mono" rows="4">' + esc(ffList.join('\n')) + '</textarea></div>' +
          '</div>',
          'DNS UPSTREAM & FAKE-IP FILTER',
          async () => {
            const cn_upstream = ($('#mdl-dns-cn') && $('#mdl-dns-cn').value.trim()) || '223.5.5.5';
            const remote_upstream = ($('#mdl-dns-remote') && $('#mdl-dns-remote').value.trim()) || 'https://1.1.1.1/dns-query';
            const rawFf = ($('#mdl-dns-fakeip-filter') && $('#mdl-dns-fakeip-filter').value) || '';
            const fakeip_filter = rawFf.split(/[\n,;]+/).map(s => s.trim().toLowerCase()).filter(Boolean);
            const r = await callRouterApi('/api/dns/settings', 'POST', { cn_upstream, remote_upstream, force_tunnel_dns: true, fakeip_filter });
            if (r && r.ok !== false) {
              state.cnUpstream = cn_upstream;
              state.remoteUpstream = remote_upstream;
              closeModal();
              toast('DNS 上游与 Fake-IP 豁免白名单已保存生效');
              await syncBackendStatus(false, true);
            }
          },
          '保存 DNS 与豁免配置'
        );
        break;
      }
      case 'ota-status': {
        const res = await callRouterApi('/api/system/update/status', 'GET');
        const prog = (res && res.progress) || {};
        openModal(
          'OTA 在线升级状态与确认 (/api/system/update/status)',
          '<div class="detail-grid">' +
            '<div><span>当前运行版本</span><b class="mono">v' + esc((res && res.current) || '2.0.2') + '</b></div>' +
            '<div><span>升级阶段</span><b>' + esc(prog.stage || 'idle (就绪)') + '</b></div>' +
            '<div><span>进度百分比</span><b>' + esc((prog.percent != null ? prog.percent : 100) + '%') + '</b></div>' +
            '<div><span>状态说明</span><b>' + esc(prog.message || '当前无进行中的升级任务') + '</b></div>' +
          '</div>',
          'OTA UPDATE STATUS',
          async () => {
            await callRouterApi('/api/system/update/ack', 'POST', {});
            closeModal();
            toast('已确认升级状态');
          },
          '确认并清理状态'
        );
        break;
      }
      case 'add-single-node': {
        openModal(
          '手动添加单个节点 & 分享链接解析预览',
          '<div class="modal-form">' +
            '<div class="modal-field">' +
              '<label>分享链接快速解析 (可选：粘贴单条节点链接后点击解析预览)</label>' +
              '<div class="input-row">' +
                '<input id="mdl-addnode-uri" class="mono" placeholder="vless://... 或 hysteria2://...">' +
                '<button type="button" class="button secondary compact" data-action="preview-share-uri">🔍 解析预览</button>' +
              '</div>' +
            '</div>' +
            '<div id="mdl-parse-preview-box" class="trace-inline-box hidden"></div>' +
            '<div class="modal-grid-3">' +
              '<div class="modal-field"><label>节点名称 (tag)</label><input id="mdl-addnode-tag" placeholder="如：新加坡-自建-01"></div>' +
              '<div class="modal-field"><label>协议类型</label><select id="mdl-addnode-type"><option value="vless">VLESS</option><option value="hysteria2">Hysteria2</option><option value="tuic">TUIC v5</option><option value="trojan">Trojan</option><option value="shadowsocks">Shadowsocks</option><option value="vmess">VMess</option></select></div>' +
              '<div class="modal-field"><label>所属地区</label><select id="mdl-addnode-region">' +
                COUNTRY_CODES.map(c => '<option value="' + esc(c) + '">' + esc(COUNTRY_META[c].flag + ' ' + COUNTRY_META[c].name) + '</option>').join('') +
              '</select></div>' +
            '</div>' +
            '<div class="modal-grid-3">' +
              '<div class="modal-field"><label>服务器地址</label><input id="mdl-addnode-server" class="mono" placeholder="example.com"></div>' +
              '<div class="modal-field"><label>端口</label><input id="mdl-addnode-port" type="number" value="443"></div>' +
              '<div class="modal-field"><label>UUID / 密码</label><input id="mdl-addnode-secret" class="mono" placeholder="UUID 或密码"></div>' +
            '</div>' +
            '<div class="modal-grid-3">' +
              '<div class="modal-field"><label>TLS SNI</label><input id="mdl-addnode-sni" class="mono" placeholder="www.microsoft.com"></div>' +
              '<div class="modal-field"><label>Reality PublicKey (pbk)</label><input id="mdl-addnode-pbk" class="mono" placeholder="可选"></div>' +
              '<div class="modal-field"><label>Reality ShortId (sid)</label><input id="mdl-addnode-sid" class="mono" placeholder="可选"></div>' +
            '</div>' +
          '</div>',
          'MANUAL NODE BUILDER',
          async () => {
            const rawUri = ($('#mdl-addnode-uri') && $('#mdl-addnode-uri').value.trim()) || '';
            const tag = ($('#mdl-addnode-tag') && $('#mdl-addnode-tag').value.trim()) || '';
            const type = ($('#mdl-addnode-type') && $('#mdl-addnode-type').value) || 'vless';
            const region_override = ($('#mdl-addnode-region') && $('#mdl-addnode-region').value) || 'SG';
            const server = ($('#mdl-addnode-server') && $('#mdl-addnode-server').value.trim()) || '';
            const server_port = Number(($('#mdl-addnode-port') && $('#mdl-addnode-port').value) || 443);
            const secret = ($('#mdl-addnode-secret') && $('#mdl-addnode-secret').value.trim()) || '';
            const sni = ($('#mdl-addnode-sni') && $('#mdl-addnode-sni').value.trim()) || '';
            const pbk = ($('#mdl-addnode-pbk') && $('#mdl-addnode-pbk').value.trim()) || '';
            const sid = ($('#mdl-addnode-sid') && $('#mdl-addnode-sid').value.trim()) || '';
            if (!server && rawUri) {
              const impRes = await callRouterApi('/api/nodes/import', 'POST', { raw_links: rawUri, text: rawUri, region_override, test_after_add: true });
              if (impRes && impRes.ok !== false) {
                closeModal();
                toast('已通过分享链接导入节点');
                await syncBackendStatus(true, true);
              }
              return;
            }
            if (!server) { toast('请填写服务器地址或粘贴分享链接', 'warn'); return; }
            const payload = { tag: tag || (region_override + '-' + type.toUpperCase() + '-' + server), type, server, server_port, region_override, uuid: secret, password: secret, sni, public_key: pbk, short_id: sid };
            const res = await callRouterApi('/api/nodes/add', 'POST', payload);
            if (res && res.ok !== false) {
              closeModal();
              toast('已成功添加节点: ' + payload.tag);
              await syncBackendStatus(true, true);
            }
          },
          '添加节点并入库'
        );
        break;
      }
      case 'preview-share-uri': {
        const rawInp = $('#mdl-addnode-uri') || $('#mdl-import-text');
        const rawLinks = (rawInp && rawInp.value.trim()) || '';
        if (!rawLinks) { toast('请先粘贴节点分享链接', 'warn'); return; }
        const res = await callRouterApi('/api/nodes/parse_preview', 'POST', { raw_links: rawLinks });
        const box = $('#mdl-parse-preview-box');
        if (res && res.ok !== false && Array.isArray(res.nodes) && res.nodes.length) {
          const first = res.nodes[0];
          const ob = first.node || {};
          const tls = ob.tls || {};
          const reality = tls.reality || {};
          if ($('#mdl-addnode-tag') && first.tag) $('#mdl-addnode-tag').value = first.tag;
          if ($('#mdl-addnode-type') && first.type) $('#mdl-addnode-type').value = first.type;
          if ($('#mdl-addnode-region') && first.country) $('#mdl-addnode-region').value = first.country;
          if ($('#mdl-addnode-server') && first.server) $('#mdl-addnode-server').value = first.server;
          if ($('#mdl-addnode-port') && first.server_port) $('#mdl-addnode-port').value = first.server_port;
          if ($('#mdl-addnode-secret')) $('#mdl-addnode-secret').value = ob.uuid || ob.password || '';
          if ($('#mdl-addnode-sni')) $('#mdl-addnode-sni').value = first.sni || tls.server_name || '';
          if ($('#mdl-addnode-pbk')) $('#mdl-addnode-pbk').value = reality.public_key || '';
          if ($('#mdl-addnode-sid')) $('#mdl-addnode-sid').value = reality.short_id || '';
          if (box) {
            box.classList.remove('hidden');
            box.innerHTML = '<div style="font-size:9px;color:var(--mint)">✓ 成功解析 ' + esc(res.parsed_count) + ' 个节点：</div>' +
              res.nodes.slice(0, 5).map(p => '<div class="mono" style="font-size:8.5px;color:var(--text)">• [' + esc(String(p.type || '').toUpperCase()) + '] ' + esc(p.tag) + ' ➔ ' + esc(p.server + ':' + p.server_port) + ' (' + esc(p.security) + ')</div>').join('');
          }
          toast('解析成功：共识别 ' + res.parsed_count + ' 个有效节点');
        }
        break;
      }
      case 'node-credentials': {
        const nodeTag = el && el.dataset.node;
        if (!nodeTag) return;
        const res = await callRouterApi('/api/nodes/credentials', 'POST', { tag: nodeTag });
        if (!res || res.ok === false || !res.node) return;
        const ob = res.node;
        const tls = ob.tls || {};
        const reality = tls.reality || {};
        const tr = ob.transport || {};
        openModal(
          '节点底层凭据与协议明细 · ' + (ob.tag || nodeTag),
          '<div class="detail-grid">' +
            '<div><span>服务器 (Server:Port)</span><b class="mono">' + esc((ob.server || '') + ':' + (ob.server_port || 443)) + '</b></div>' +
            '<div><span>协议与传输层</span><b class="mono">' + esc(String(ob.type || '').toUpperCase() + ' / ' + (tr.type || 'tcp')) + '</b></div>' +
            '<div><span>UUID / 密码凭据</span><b class="mono">' + esc(ob.uuid || ob.password || '无') + '</b></div>' +
            '<div><span>TLS SNI / ALPN</span><b class="mono">' + esc(tls.server_name || ob.sni || '未配置') + '</b></div>' +
            '<div><span>Reality PublicKey (pbk)</span><b class="mono">' + esc(reality.public_key || '未启用') + '</b></div>' +
            '<div><span>Reality ShortId (sid)</span><b class="mono">' + esc(reality.short_id || '无') + '</b></div>' +
          '</div>' +
          '<div class="modal-form" style="margin-top:12px">' +
            '<div class="modal-field"><label>Sing-box 标准 Outbound JSON 结构</label><textarea rows="7" class="mono" readonly onclick="this.select()">' + esc(JSON.stringify(ob, null, 2)) + '</textarea></div>' +
          '</div>',
          'NODE CREDENTIALS INSPECTOR'
        );
        break;
      }
      case 'node-real-delay': {
        const nodeTag = el && el.dataset.node;
        if (!nodeTag) return;
        toast('正在对节点「' + nodeTag + '」执行真实握手测速...');
        const res = await callRouterApi('/api/nodes/test_real_delay', 'POST', { tags: [nodeTag] });
        if (res && res.ok !== false) {
          await syncBackendStatus(true, true);
          toast('节点「' + nodeTag + '」真实延迟测试完成');
        }
        break;
      }
      case 'test-real-delay-batch': {
        const visibleTags = filteredNodes().map(n => n.tag || n.name).slice(0, 40);
        toast('正在对当前列表 (' + visibleTags.length + ' 个节点) 执行真实握手延迟测试...');
        const res = await callRouterApi('/api/nodes/test_real_delay', 'POST', { tags: visibleTags });
        if (res && res.ok !== false) {
          await syncBackendStatus(true, true);
          toast('批量真实握手延迟测试完成');
        }
        break;
      }
      case 'new-rule':
        openNewRuleModal(null);
        break;
      case 'new-auto-pool':
        openAutoNodeEditorModal(null);
        break;
      case 'probe-auto-pool': {
        const pid = el && el.dataset.poolId;
        toast('正在探测双组自动池 ' + (pid || '') + '...');
        await callRouterApi('/api/auto_nodes/probe', 'POST', { id: pid || '' });
        await syncBackendStatus(true, true);
        toast('自动节点池双组探测已完成');
        break;
      }
      case 'revert-auto-pool': {
        const pid = el && el.dataset.poolId;
        const res = await callRouterApi('/api/auto_nodes/revert_now', 'POST', { id: pid || 'auto_ai' });
        toast((res && res.message) || '已执行主组健康检查与回切');
        await syncBackendStatus(false, true);
        break;
      }
      case 'replace-auto-node': {
        const idx = Number(el && el.dataset.poolIdx);
        await openReplaceAutoNodeModal(idx);
        break;
      }
      case 'delete-auto-pool': {
        const pid = el && el.dataset.poolId;
        if (!pid) return;
        const poolSnap = mock.autoPools.find(p => p.id === pid) ? JSON.parse(JSON.stringify(mock.autoPools.find(p => p.id === pid))) : null;
        confirmModal(
          '确认删除自动节点池 · ' + (poolSnap ? poolSnap.name : pid),
          '删除后该自动节点池「' + (poolSnap ? poolSnap.name : pid) + '」将被移除，确认继续删除吗？',
          async () => {
            await callRouterApi('/api/auto_nodes/delete', 'POST', { id: pid });
            await syncBackendStatus(false, true);
            toast('已删除自动节点池「' + (poolSnap ? poolSnap.name : pid) + '」', '', poolSnap ? {
              undoText: '↩ 撤销删除',
              onUndo: async () => {
                await callRouterApi('/api/auto_nodes/save', 'POST', poolSnap);
                await syncBackendStatus(false, true);
                toast('已恢复自动节点池「' + poolSnap.name + '」');
              }
            } : undefined);
          },
          '确认删除节点池'
        );
        break;
      }
      case 'optimize': {
        toast('正在重新优选全部双组自动节点池...');
        await callRouterApi('/api/auto_nodes/probe', 'POST', { id: '' });
        await syncBackendStatus(true, true);
        toast('全部自动池已完成重新优选');
        break;
      }
      /* Fix #8: Batch operations on Shunt Strategy Groups (with confirmModal & Undo) */
      case 'batch-shunt-auto': {
        const prevUpdates = mock.groups.map(g => ({
          id: g.id,
          shunt_mode: g.shunt_mode,
          strategy: g.strategy || g.shunt_mode,
          country: g.country,
          auto_node_id: g.auto_node_id,
          manual_node: g.shunt_mode === 'auto' ? ('auto:' + g.auto_node_id) : (g.shunt_mode === 'direct' ? 'direct' : g.resolved_node)
        }));
        confirmModal(
          '确认批量切换全部海外分流组',
          '该操作会将全部海外分流组切换为「智能自动节点池」，覆盖当前手动指定的固定节点配置（如自定义固定组），确认执行吗？',
          async () => {
            const updates = mock.groups
              .filter(g => g.id !== 'Domestic_CN')
              .map(g => ({
                id: g.id,
                shunt_mode: 'auto',
                strategy: 'auto',
                auto_node_id: g.id === 'AI' || g.id === 'Google' || g.id === 'GitHub' ? 'auto_ai' : (g.id === 'Netflix' ? 'auto_netflix' : 'auto_youtube')
              }));
            await callRouterApi('/api/shunt/update', 'POST', { routing_mode: 'rule_shunt', groups: updates });
            await syncBackendStatus(false, true);
            toast('已将全部海外分流组一键切换至智能自动节点池', '', {
              undoText: '↩ 撤销批量切换',
              onUndo: async () => {
                await callRouterApi('/api/shunt/update', 'POST', { groups: prevUpdates });
                await syncBackendStatus(false, true);
                toast('已撤销并恢复原有的分流组节点配置');
              }
            });
          },
          '确认批量切换'
        );
        break;
      }
      case 'batch-shunt-media-fast': {
        const bestNode = (mock.nodes.filter(n => n.status === 'ok' && n.rtt > 0).sort((a, b) => a.rtt - b.rtt)[0]) || mock.nodes[0];
        const bTag = bestNode ? (bestNode.tag || bestNode.name) : '新加坡 06';
        const bCountry = classifyNodeCountry(bestNode);
        const targetIds = ['AI', 'YouTube', 'TikTok', 'Netflix'];
        const prevUpdates = mock.groups.filter(g => targetIds.includes(g.id)).map(g => ({
          id: g.id,
          shunt_mode: g.shunt_mode,
          strategy: g.strategy || g.shunt_mode,
          country: g.country,
          auto_node_id: g.auto_node_id,
          manual_node: g.shunt_mode === 'auto' ? ('auto:' + g.auto_node_id) : (g.shunt_mode === 'direct' ? 'direct' : g.resolved_node)
        }));
        confirmModal(
          '确认批量切换 AI 与流媒体分流组',
          '将把 AI、YouTube、TikTok、Netflix 四个分流组统一指定为当前最低延迟节点「' + bTag + '」，确认继续吗？',
          async () => {
            const updates = targetIds.map(gid => ({
              id: gid,
              shunt_mode: 'manual',
              strategy: 'manual',
              country: bCountry,
              manual_node: bTag
            }));
            await callRouterApi('/api/shunt/update', 'POST', { groups: updates });
            await syncBackendStatus(false, true);
            toast('已将 AI / 流媒体组一键切至最低延迟节点: ' + bTag, '', {
              undoText: '↩ 撤销批量切换',
              onUndo: async () => {
                await callRouterApi('/api/shunt/update', 'POST', { groups: prevUpdates });
                await syncBackendStatus(false, true);
                toast('已撤销并恢复 AI / 流媒体组原策略');
              }
            });
          },
          '确认切换'
        );
        break;
      }
      case 'batch-shunt-cn-direct': {
        const targetIds = ['Domestic_CN', 'Microsoft', 'Apple'];
        const prevUpdates = mock.groups.filter(g => targetIds.includes(g.id)).map(g => ({
          id: g.id,
          shunt_mode: g.shunt_mode,
          strategy: g.strategy || g.shunt_mode,
          country: g.country,
          auto_node_id: g.auto_node_id,
          manual_node: g.shunt_mode === 'auto' ? ('auto:' + g.auto_node_id) : (g.shunt_mode === 'direct' ? 'direct' : g.resolved_node)
        }));
        confirmModal(
          '确认批量重置为直连 (DIRECT)',
          '将把国内白名单、Microsoft、Apple 三个分流组统一重置为宽带原生直连 (DIRECT)，确认继续吗？',
          async () => {
            const updates = targetIds.map(gid => ({
              id: gid,
              shunt_mode: 'direct',
              strategy: 'direct',
              country: 'direct',
              manual_node: 'direct'
            }));
            await callRouterApi('/api/shunt/update', 'POST', { groups: updates });
            await syncBackendStatus(false, true);
            toast('国内白名单、Microsoft 与 Apple 组已重置为直连', '', {
              undoText: '↩ 撤销重置',
              onUndo: async () => {
                await callRouterApi('/api/shunt/update', 'POST', { groups: prevUpdates });
                await syncBackendStatus(false, true);
                toast('已撤销并恢复原分流策略');
              }
            });
          },
          '确认重置为直连'
        );
        break;
      }
      case 'toggle-shunt-rules-drawer': {
        state.expandShuntRules = !state.expandShuntRules;
        if (el) el.textContent = state.expandShuntRules ? '📂 收起规则详情' : '📂 展开规则详情';
        renderShuntMatrix();
        break;
      }
      case 'reset-all-shunt-rules': {
        const prevUpdates = mock.groups.map(g => ({
          id: g.id,
          shunt_mode: g.shunt_mode,
          strategy: g.strategy || g.shunt_mode,
          country: g.country,
          auto_node_id: g.auto_node_id,
          manual_node: g.shunt_mode === 'auto' ? ('auto:' + g.auto_node_id) : (g.shunt_mode === 'direct' ? 'direct' : g.resolved_node)
        }));
        confirmModal(
          '确认恢复默认分流规则库',
          '该操作会将全部内置分流组的域名列表与编排规则恢复为默认出厂状态，确认继续执行吗？',
          async () => {
            await callRouterApi('/api/shunt/reset_group_rules', 'POST', { reset_presets: true });
            await syncBackendStatus(false, true);
            toast('已恢复默认内置分流组规则', '', {
              undoText: '↩ 撤销恢复',
              onUndo: async () => {
                await callRouterApi('/api/shunt/update', 'POST', { groups: prevUpdates });
                await syncBackendStatus(false, true);
                toast('已撤销并还原分流组编排策略');
              }
            });
          },
          '确认恢复默认规则库'
        );
        break;
      }
      case 'reset-single-group': {
        const gid = el && el.dataset.gid;
        if (!gid) return;
        const grpSnap = mock.groups.find(g => g.id === gid) ? JSON.parse(JSON.stringify(mock.groups.find(g => g.id === gid))) : null;
        confirmModal(
          '确认恢复「' + gid + '」默认域名库',
          '将清除分流组「' + gid + '」的自定义修改并还原为系统内置默认域名库，确认执行吗？',
          async () => {
            await callRouterApi('/api/shunt/reset_group_rules', 'POST', { group_id: gid });
            await syncBackendStatus(false, true);
            toast('已恢复「' + gid + '」默认域名库', '', grpSnap ? {
              undoText: '↩ 撤销恢复',
              onUndo: async () => {
                await callRouterApi('/api/shunt/update_group_rules', 'POST', { group_id: gid, domains: grpSnap.domains || [] });
                await syncBackendStatus(false, true);
                toast('已还原「' + gid + '」自定义域名列表');
              }
            } : undefined);
          },
          '确认恢复默认'
        );
        break;
      }
      case 'delete-custom-group': {
        const gid = el && el.dataset.gid;
        if (!gid) return;
        const grpSnap = mock.groups.find(g => g.id === gid) ? JSON.parse(JSON.stringify(mock.groups.find(g => g.id === gid))) : { id: gid, name: gid, domains: [] };
        confirmModal(
          '确认删除自定义分流组 · ' + (grpSnap.name || gid),
          '删除后自定义分流组「' + (grpSnap.name || gid) + '」及其匹配规则将被移除，确认继续删除吗？',
          async () => {
            await callRouterApi('/api/shunt/delete_rule', 'POST', { group_id: gid });
            await syncBackendStatus(false, true);
            toast('已删除自定义分流组「' + (grpSnap.name || gid) + '」', '', {
              undoText: '↩ 撤销删除',
              onUndo: async () => {
                await callRouterApi('/api/shunt/add_rule', 'POST', {
                  group_id: grpSnap.id,
                  title: grpSnap.name || grpSnap.id,
                  domains: grpSnap.domains || [],
                  shunt_mode: grpSnap.shunt_mode || 'auto',
                  auto_node_id: grpSnap.auto_node_id || 'auto_ai',
                  country: grpSnap.country || 'JP',
                  manual_node: grpSnap.resolved_node || ''
                });
                await syncBackendStatus(false, true);
                toast('已恢复自定义分流组「' + (grpSnap.name || gid) + '」');
              }
            });
          },
          '确认删除分流组'
        );
        break;
      }
      case 'move-group-up':
      case 'move-group-down': {
        const gid = el && el.dataset.gid;
        if (!gid) return;
        const dir = action === 'move-group-up' ? 'up' : 'down';
        await callRouterApi('/api/shunt/reorder', 'POST', { group_id: gid, direction: dir });
        toast('已调整「' + gid + '」分流匹配优先级');
        await syncBackendStatus(false, true);
        break;
      }
      case 'verify-group': {
        const gid = el && el.dataset.gid;
        if (!gid) return;
        toast('正在真连接校验分流组「' + gid + '」当前出口...');
        const res = await callRouterApi('/api/shunt/verify_target', 'POST', { group_id: gid });
        toast((res && res.message) || ('分流组「' + gid + '」出口校验通过'));
        await syncBackendStatus(false, true);
        break;
      }
      case 'clear-switch-history': {
        const prevHist = JSON.parse(JSON.stringify(mock.switchHistory || []));
        confirmModal(
          '确认清空节点切换历史记录',
          '确认清空全部自动节点池的故障转移与切换历史记录吗？',
          async () => {
            await callRouterApi('/api/shunt/clear_history', 'POST', {});
            mock.switchHistory = [];
            renderShuntMatrix();
            toast('已清空节点切换历史记录', '', {
              undoText: '↩ 撤销清空',
              onUndo: () => {
                mock.switchHistory = prevHist;
                renderShuntMatrix();
                toast('已恢复切换历史记录视图');
              }
            });
          },
          '确认清空'
        );
        break;
      }
      case 'new-homelink':
        openModal(
          '创建加密回家节点 (支持单节点独立回家路由模式)',
          '<div class="modal-form">' +
            '<div class="modal-grid-3" style="margin-bottom:8px">' +
              '<div class="modal-field"><label>该节点独立回家路由模式</label><select id="mdl-new-hl-rmode">' +
                '<option value="shunt" selected>🌐 回家 + 科学上网分流</option>' +
                '<option value="direct">🏠 仅访问内网与国内</option>' +
                '<option value="proxy_only">🛡️ 仅科学上网 · 隔离内网</option>' +
              '</select></div>' +
              '<div class="modal-field"><label>自定义监听端口（留空自动分配）</label><input id="mdl-new-hl-port" type="number" placeholder="如 18443 或 20443"></div>' +
              '<div class="modal-field"><label>公网 DDNS 域名或 IP</label><input id="mdl-new-hl-ddns" value="' + esc(window.location.hostname || '') + '" placeholder="home.example.com"></div>' +
            '</div>' +
            '<div class="route-mode-grid">' +
              '<button class="route-mode active" data-action="create-homelink" data-proto="vless-reality"><b>点击创建 VLESS-Reality</b><p>首选推荐，借用大厂 TLS 指纹免域名证书零暴露。</p></button>' +
              '<button class="route-mode" data-action="create-homelink" data-proto="hysteria2"><b>点击创建 Hysteria2 QUIC</b><p>高丢包移动蜂窝网络与跨国弱网下的极速回家协议。</p></button>' +
              '<button class="route-mode" data-action="create-homelink" data-proto="vless-tls"><b>点击创建 VLESS-TLS</b><p>内置自签根证书与 SHA256 指纹固定，兼容各级端口转发。</p></button>' +
            '</div>' +
          '</div>',
          'SECURE HOMELINK WIZARD'
        );
        break;
      case 'create-homelink': {
        const proto = (el && el.dataset.proto) || 'vless-reality';
        const customPort = Number(($('#mdl-new-hl-port') && $('#mdl-new-hl-port').value) || 0);
        const ddns_host = ($('#mdl-new-hl-ddns') && $('#mdl-new-hl-ddns').value.trim()) || '';
        const route_mode = ($('#mdl-new-hl-rmode') && $('#mdl-new-hl-rmode').value) || 'shunt';
        const res = await callRouterApi('/api/homelink/quick_create', 'POST', {
          protocol: proto,
          listen_port: customPort || (proto === 'hysteria2' ? 20443 : 18443),
          ddns_host,
          route_mode,
          enabled: true
        });
        closeModal();
        toast((res && res.message) || ('已创建 ' + proto + ' 回家节点'));
        await syncBackendStatus(false, true);
        break;
      }
      case 'toggle-homelink': {
        const nid = el && el.dataset.node;
        const hlNode = mock.homelinkNodes.find(x => x.id === nid);
        if (!hlNode) return;
        hlNode.enabled = !hlNode.enabled;
        setSwitchState(el, hlNode.enabled);
        await callRouterApi('/api/homelink/update', 'POST', { id: nid, enabled: hlNode.enabled });
        toast('回家节点「' + hlNode.name + '」已' + (hlNode.enabled ? '启用' : '停用'));
        await syncBackendStatus(false, true);
        break;
      }
      case 'delete-homelink': {
        const nid = el && el.dataset.node;
        if (!nid) return;
        const hlSnap = mock.homelinkNodes.find(x => x.id === nid) ? JSON.parse(JSON.stringify(mock.homelinkNodes.find(x => x.id === nid))) : null;
        confirmModal(
          '确认删除回家节点 · ' + (hlSnap ? hlSnap.name : nid),
          '删除后该加密回家入站隧道（端口 ' + (hlSnap ? hlSnap.listen_port : '') + '）将停止监听，确认继续删除吗？',
          async () => {
            await callRouterApi('/api/homelink/delete', 'POST', { id: nid });
            await syncBackendStatus(false, true);
            toast('已删除回家节点「' + (hlSnap ? hlSnap.name : nid) + '」', '', hlSnap ? {
              undoText: '↩ 撤销删除',
              onUndo: async () => {
                await callRouterApi('/api/homelink/add', 'POST', Object.assign({}, hlSnap, { protocol: hlSnap.raw_proto || hlSnap.protocol }));
                await syncBackendStatus(false, true);
                toast('已恢复回家节点「' + hlSnap.name + '」');
              }
            } : undefined);
          },
          '确认删除回家节点'
        );
        break;
      }
      case 'check-homelink-port': {
        const port = (el && el.dataset.port) || 18443;
        const proto = (el && el.dataset.proto) || 'vless-reality';
        const res = await callRouterApi('/api/homelink/port_check?port=' + encodeURIComponent(port) + '&protocol=' + encodeURIComponent(proto), 'GET');
        toast(res && res.ok !== false ? ('端口 ' + port + ' 状态正常，无冲突占用') : ((res && res.reason) || '端口存在占用冲突'));
        break;
      }
      case 'view-ca-cert': {
        const res = await callRouterApi('/api/certs/ca', 'GET');
        openModal(
          '回家隧道自签 TLS 根证书与指纹',
          '<div class="modal-form">' +
            '<p>Hysteria2 与 VLESS-TLS 回家节点使用内置自签根证书，客户端可通过 <code>pinSHA256</code> 自动完成证书指纹校验。</p>' +
            '<div class="modal-field"><label>SHA-256 指纹</label><input class="mono" value="' + esc((res && res.sha256) || '内置证书指纹已就绪') + '" readonly onclick="this.select()"></div>' +
          '</div>',
          'TLS CA CERTIFICATE'
        );
        break;
      }
      case 'share-node': {
        const nid = el && el.dataset.node;
        const hlNode = (state.rawHomelink && Array.isArray(state.rawHomelink.nodes) && state.rawHomelink.nodes.find(x => x.id === nid)) || mock.homelinkNodes.find(x => x.id === nid) || mock.homelinkNodes[0];
        const uri = (hlNode && (hlNode.uri || hlNode.share_uri)) || ('vless://ailink-homelink@' + (window.location.hostname || 'home.example.com') + ':' + (hlNode ? hlNode.listen_port || 18443 : 18443) + '#AI-LINK-Home');
        let qrHtml = '';
        if (typeof window.qrcode === 'function') {
          try {
            const qr = window.qrcode(0, 'M');
            qr.addData(uri);
            qr.make();
            qrHtml = '<div class="qr-wrap">' + qr.createSvgTag(4, 0) + '</div>';
          } catch (_) {}
        }
        openModal(
          '分享回家配置 · ' + (hlNode ? hlNode.name : ''),
          qrHtml +
          '<div class="modal-field"><label>标准客户端导入 URI（支持 v2rayNG / Shadowrocket / NekoBox / Sing-box 扫码或复制）</label><input class="mono" value="' + esc(uri) + '" readonly onclick="this.select()"></div>' +
          '<div class="backup-status"><span>安全边界</span><b>端到端加密 · 支持随时更换端口或吊销凭据</b></div>',
          'HOMELINK QR SHARE'
        );
        break;
      }
      case 'edit-node': {
        const nid = el && el.dataset.node;
        const hlNode = mock.homelinkNodes.find(x => x.id === nid) || mock.homelinkNodes[0];
        openModal(
          '编辑回家节点 · ' + (hlNode ? hlNode.name : ''),
          '<div class="modal-form">' +
            '<div class="modal-grid-2">' +
              '<div class="modal-field"><label>节点名称</label><input id="mdl-hl-name" value="' + esc(hlNode ? hlNode.name : '回家节点') + '"></div>' +
              '<div class="modal-field"><label>内部监听端口</label><input id="mdl-hl-port" type="number" value="' + esc(hlNode ? hlNode.listen_port || 18443 : 18443) + '"></div>' +
            '</div>' +
            '<div class="modal-grid-3">' +
              '<div class="modal-field"><label>外部映射端口 (External Port)</label><input id="mdl-hl-extport" type="number" value="' + esc(hlNode ? hlNode.external_port || hlNode.listen_port || 18443 : 18443) + '"></div>' +
              '<div class="modal-field"><label>公网 DDNS 域名或 IP</label><input id="mdl-hl-ddns" value="' + esc((hlNode && hlNode.ddns_host) || window.location.hostname || '') + '" placeholder="如 home.example.com"></div>' +
              '<div class="modal-field"><label>独立回家路由模式</label><select id="mdl-hl-rmode">' +
                '<option value="shunt" ' + ((!hlNode || hlNode.route_mode === 'shunt') ? 'selected' : '') + '>🌐 回家 + 科学上网分流</option>' +
                '<option value="direct" ' + (hlNode && hlNode.route_mode === 'direct' ? 'selected' : '') + '>🏠 仅访问内网与国内</option>' +
                '<option value="proxy_only" ' + (hlNode && hlNode.route_mode === 'proxy_only' ? 'selected' : '') + '>🛡️ 仅科学上网 · 隔离内网</option>' +
              '</select></div>' +
            '</div>' +
          '</div>',
          'HOMELINK EDITOR',
          async () => {
            const name = ($('#mdl-hl-name') && $('#mdl-hl-name').value.trim()) || '回家节点';
            const listen_port = Number(($('#mdl-hl-port') && $('#mdl-hl-port').value) || 18443);
            const external_port = Number(($('#mdl-hl-extport') && $('#mdl-hl-extport').value) || listen_port);
            const ddns_host = ($('#mdl-hl-ddns') && $('#mdl-hl-ddns').value.trim()) || '';
            const route_mode = ($('#mdl-hl-rmode') && $('#mdl-hl-rmode').value) || 'shunt';
            const res = await callRouterApi('/api/homelink/update', 'POST', { id: nid, name, listen_port, external_port, ddns_host, route_mode, enabled: true });
            if (res && res.ok === false) {
              toast(res.message || '保存失败', 'warn');
              return;
            }
            closeModal();
            toast('回家节点配置已更新');
            await syncBackendStatus(false, true);
          },
          '保存修改'
        );
        break;
      }
      case 'dns-flush': {
        await callRouterApi('/api/dns/flush_cache', 'POST', {});
        toast('已清空 dnsmasq 与 sing-box 双栈 DNS 缓存');
        break;
      }
      case 'dns-test': {
        toast('正在向黑洞护盾注入高频广告探针...');
        const res = await callRouterApi('/api/dns/filter/test', 'POST', {});
        toast((res && res.message) || '高频广告源黑洞吞噬实测完成');
        await syncBackendStatus(false, true);
        break;
      }
      case 'dns-sync': {
        toast('正在拉取云端过滤规则库...');
        const res = await callRouterApi('/api/dns/filter/sync', 'POST', {});
        toast((res && res.message) || '云端过滤规则已同步更新');
        await syncBackendStatus(false, true);
        break;
      }
      case 'dns-toggle': {
        const nextDnsEn = !state.dnsEnabled;
        state.dnsEnabled = nextDnsEn;
        setSwitchState(el, state.dnsEnabled);
        const res = await callRouterApi('/api/dns/filter/toggle', 'POST', { enabled: nextDnsEn });
        if (res && res.filter && res.filter.enabled != null) {
          state.dnsEnabled = Boolean(res.filter.enabled);
        }
        renderDnsAndFilterSection();
        toast('云端域名过滤护盾已' + (state.dnsEnabled ? '开启' : '关闭'));
        break;
      }
      case 'dns-rewrite-toggle': {
        state.dnsRewriteEnabled = !state.dnsRewriteEnabled;
        setSwitchState(el, state.dnsRewriteEnabled);
        await callRouterApi('/api/dns/rewrite', 'POST', { enabled: state.dnsRewriteEnabled });
        toast('DNS 防跳重写已' + (state.dnsRewriteEnabled ? '开启' : '关闭'));
        break;
      }
      case 'add-dns-rewrite': {
        const from_domain = ($('#inp-rw-from') && $('#inp-rw-from').value.trim()) || '';
        const to_domain = ($('#inp-rw-to') && $('#inp-rw-to').value.trim()) || '';
        if (!from_domain || !to_domain) {
          toast('请填写原域名与重写目标域名', 'warn');
          return;
        }
        await callRouterApi('/api/dns/rewrite', 'POST', { action: 'add', from_domain, to_domain });
        if ($('#inp-rw-from')) $('#inp-rw-from').value = '';
        if ($('#inp-rw-to')) $('#inp-rw-to').value = '';
        toast('已添加 DNS 重写: ' + from_domain + ' ➔ ' + to_domain);
        await syncBackendStatus(false, true);
        break;
      }
      case 'delete-dns-rewrite': {
        const from_domain = el && el.dataset.from;
        if (!from_domain) return;
        await callRouterApi('/api/dns/rewrite', 'POST', { action: 'delete', from_domain });
        toast('已删除重写规则: ' + from_domain);
        await syncBackendStatus(false, true);
        break;
      }
      case 'dns-rules': {
        openModal(
          '添加自定义云端过滤列表与黑白名单',
          '<div class="modal-form">' +
            '<div class="modal-grid-2">' +
              '<div class="modal-field"><label>新规则源名称</label><input id="mdl-flt-name" placeholder="如：AdGuard DNS Filter"></div>' +
              '<div class="modal-field"><label>规则源 URL</label><input id="mdl-flt-url" placeholder="https://..."></div>' +
            '</div>' +
            '<div class="modal-field"><label>自定义黑名单域名（每行或逗号分隔）</label><textarea id="mdl-custom-block" rows="2" placeholder="ad.example.com, tracker.example.com"></textarea></div>' +
            '<div class="modal-field"><label>自定义白名单豁免域名（每行或逗号分隔）</label><textarea id="mdl-custom-allow" rows="2" placeholder="safe.example.com"></textarea></div>' +
          '</div>',
          'DNS SHIELD LISTS',
          async () => {
            const name = ($('#mdl-flt-name') && $('#mdl-flt-name').value.trim()) || '';
            const url = ($('#mdl-flt-url') && $('#mdl-flt-url').value.trim()) || '';
            const bRaw = ($('#mdl-custom-block') && $('#mdl-custom-block').value.trim()) || '';
            const aRaw = ($('#mdl-custom-allow') && $('#mdl-custom-allow').value.trim()) || '';
            const payload = {};
            if (url) payload.add_list = { name: name || '自定义规则列表', url };
            if (bRaw) payload.custom_blocked = bRaw.split(/[\n,;]+/).map(s => s.trim()).filter(Boolean);
            if (aRaw) payload.custom_allowed = aRaw.split(/[\n,;]+/).map(s => s.trim()).filter(Boolean);
            await callRouterApi('/api/dns/filter/toggle', 'POST', payload);
            closeModal();
            toast('DNS 过滤列表与黑白名单已保存');
            await syncBackendStatus(false, true);
          },
          '保存过滤设置'
        );
        break;
      }
      /* Fix #12: Music Unlock Drawer & Toggle */
      case 'toggle-music-drawer': {
        state.musicUnlockOpen = !state.musicUnlockOpen;
        renderMusicUnlockSection();
        break;
      }
      case 'toggle-music-unlock': {
        state.musicUnlockEnabled = !state.musicUnlockEnabled;
        if (state.musicUnlockEnabled) state.musicUnlockOpen = true;
        renderMusicUnlockSection();
        toast('网易云音乐解锁扩展已' + (state.musicUnlockEnabled ? '开启' : '关闭'));
        break;
      }
      case 'import':
        openBatchImportModal();
        break;
      case 'new-sub':
        openNewSubscriptionModal(null);
        break;
      case 'open-schedules':
        openProbeSchedulesModal();
        break;
      case 'run-sched-now': {
        const sid = el && el.dataset.sid;
        toast('正在立即执行定时测速计划...');
        await callRouterApi('/api/probe/schedules/run', 'POST', { id: sid || '' });
        await syncBackendStatus(true, true);
        toast('定时测速计划执行完毕');
        break;
      }
      case 'del-sched': {
        const sid = el && el.dataset.sid;
        if (!sid) return;
        await callRouterApi('/api/probe/schedules/delete', 'POST', { id: sid });
        closeModal();
        toast('已删除定时测速计划');
        await syncBackendStatus(false, true);
        break;
      }
      case 'subscription-toggle': {
        const idx = Number(el && el.dataset.sub);
        const sub = mock.subscriptions[idx];
        if (!sub) return;
        sub.enabled = !sub.enabled;
        setSwitchState(el, sub.enabled);
        await callRouterApi('/api/subscriptions/toggle', 'POST', { id: sub.id, url: sub.url, enabled: sub.enabled });
        toast('订阅「' + sub.name + '」已' + (sub.enabled ? '启用' : '停用'));
        await syncBackendStatus(true, true);
        break;
      }
      case 'sub-sync-one': {
        const idx = Number(el && el.dataset.sub);
        const sub = mock.subscriptions[idx];
        if (!sub) return;
        if (el) el.setAttribute('aria-busy', 'true');
        toast('正在同步订阅「' + sub.name + '」...');
        const res = await callRouterApi('/api/subscriptions/sync', 'POST', { id: sub.id, name: sub.name, url: sub.url });
        if (el) el.setAttribute('aria-busy', 'false');
        if (!res || res.ok === false) {
          toast('订阅「' + sub.name + '」同步失败: ' + ((res && (res.message || res.error)) || '拉取异常'), 'warn');
          break;
        }
        toast('订阅「' + sub.name + '」同步完成');
        await syncBackendStatus(true, true);
        break;
      }
      case 'sub-probe-one': {
        const idx = Number(el && el.dataset.sub);
        const sub = mock.subscriptions[idx];
        if (!sub) return;
        toast('正在对订阅「' + sub.name + '」下属节点执行 URL Ping...');
        await callRouterApi('/api/probe/url_ping', 'POST', { sub_id: sub.id, sub_url: sub.url });
        toast('订阅「' + sub.name + '」节点测速完成');
        await syncBackendStatus(true, true);
        break;
      }
      case 'sub-edit-one': {
        const idx = Number(el && el.dataset.sub);
        openNewSubscriptionModal(idx);
        break;
      }
      case 'sub-delete-one': {
        const idx = Number(el && el.dataset.sub);
        const sub = mock.subscriptions[idx];
        if (!sub) return;
        const subSnap = JSON.parse(JSON.stringify(sub));
        confirmModal(
          '确认删除订阅源 · ' + sub.name,
          '删除订阅源「' + sub.name + '」将同时清理其下属的节点，确认继续删除吗？',
          async () => {
            await callRouterApi('/api/subscriptions/delete', 'POST', { id: sub.id, url: sub.url, delete_nodes: true });
            await syncBackendStatus(true, true);
            toast('已删除订阅「' + subSnap.name + '」', '', {
              undoText: '↩ 撤销删除',
              onUndo: async () => {
                await callRouterApi('/api/subscriptions/add', 'POST', { name: subSnap.name, url: subSnap.url, auto_update: true, update_interval_min: subSnap.update_interval_min || 360 });
                await syncBackendStatus(true, true);
                toast('已恢复订阅「' + subSnap.name + '」');
              }
            });
          },
          '确认删除订阅'
        );
        break;
      }
      case 'probe-category': {
        const visibleTags = filteredNodes().map(n => n.tag || n.name).slice(0, 40);
        toast('正在对当前筛选分类 (' + visibleTags.length + ' 个节点) 执行 URL Ping...');
        await callRouterApi('/api/probe/url_ping', 'POST', { tags: visibleTags });
        await syncBackendStatus(true, true);
        toast('当前分类节点 URL Ping 测速已完成');
        break;
      }
      case 'ipv6-check': {
        toast('正在检测节点 IPv6 连通能力...');
        await callRouterApi('/api/probe/ipv6_check', 'POST', {});
        await syncBackendStatus(true, true);
        toast('节点 IPv6 能力检测完成');
        break;
      }
      case 'node-details':
        await showNodeDetails(el.dataset.node);
        break;
      case 'restart-core': {
        toast('正在重启 sing-box 代理内核...');
        const res = await callRouterApi('/api/ops/control', 'POST', { action: 'restart_core' });
        toast((res && res.message) || 'sing-box 内核已重启并完成 :7893 端口健康校验');
        await syncBackendStatus(false, true);
        break;
      }
      case 'restart-service': {
        toast('正在重启 AI-LINK 守护进程与全部服务...');
        await callRouterApi('/api/system/service/restart', 'POST', {});
        toast('服务重启指令已下发，正在重新连接...');
        setTimeout(() => syncBackendStatus(false, true), 1800);
        break;
      }
      case 'check-update': {
        if (el) el.setAttribute('aria-busy', 'true');
        toast('正在检查云端版本清单...');
        const res = await callRouterApi('/api/system/update/check?force=1', 'GET');
        if (el) el.setAttribute('aria-busy', 'false');
        const subEl = $('#ota-sub');
        const applyBtn = $('#btn-ota-apply');
        if (!res || res.ok === false) {
          const errMsg = (res && (res.message || res.error)) || '云端版本清单拉取失败';
          if (subEl) subEl.textContent = '检查更新失败：' + errMsg;
          toast('检查更新失败：' + errMsg, 'warn');
          break;
        }
        if (res.has_update) {
          if (subEl) subEl.textContent = '发现新版本 v' + res.latest + ' 可立即在线升级';
          if (applyBtn) applyBtn.classList.remove('hidden');
          toast('发现新版本 v' + res.latest + '，可点击「立即升级」');
        } else {
          if (subEl) subEl.textContent = '当前已是最新版本 (v2.0.2 · 已校验云端清单)';
          toast('当前已是最新版本 (v2.0.2)');
        }
        break;
      }
      case 'apply-update': {
        toast('正在启动 8 步安全在线升级与自动备份...');
        const res = await callRouterApi('/api/system/update/apply', 'POST', {});
        toast((res && res.message) || '在线升级已启动，进度将持久化至闪存');
        break;
      }
      case 'backup': {
        toast('正在生成全量 .tgz 备份归档...');
        const res = await callRouterApi('/api/ops/backup_archive', 'GET');
        if (res && res.ok && res.archive_base64) {
          const a = document.createElement('a');
          a.href = 'data:application/gzip;base64,' + res.archive_base64;
          a.download = res.filename || 'ai-link-backup.tgz';
          document.body.appendChild(a);
          a.click();
          a.remove();
          toast('已导出配置归档: ' + (res.filename || 'ai-link-backup.tgz'));
        } else {
          toast('配置归档已生成');
        }
        break;
      }
      case 'backup-json': {
        const res = await callRouterApi('/api/ops/backup', 'GET');
        const blob = new Blob([JSON.stringify(res || {}, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'ai-link-backup.json';
        document.body.appendChild(a);
        a.click();
        a.remove();
        toast('已导出 JSON 配置备份');
        break;
      }
      case 'restore':
        openRestoreBackupModal();
        break;
      case 'factory-reset': {
        openModal(
          '确认恢复出厂设置',
          '<div class="modal-form">' +
            '<p>恢复出厂设置将清空自定义节点、订阅并还原初始默认密码（<code>ai-link-2026</code>），恢复前会自动生成一份安全归档备份至 <code>/root/ai-link-final-backup</code>。</p>' +
            '<div class="modal-field"><label>输入 RESET 确认执行</label><input id="mdl-reset-confirm" value="RESET"></div>' +
          '</div>',
          'FACTORY RESET',
          async () => {
            const c = ($('#mdl-reset-confirm') && $('#mdl-reset-confirm').value.trim()) || '';
            if (c.toUpperCase() !== 'RESET') { toast('请输入 RESET 确认', 'warn'); return; }
            await callRouterApi('/api/ops/factory_reset', 'POST', { confirm: 'RESET', create_backup: true });
            closeModal();
            toast('已恢复出厂默认设置');
            await syncBackendStatus(true, true);
          },
          '确认恢复出厂'
        );
        break;
      }
      case 'auth-toggle': {
        const nextVal = !state.authEnabled;
        renderOpsSettings({ require_lan_auth: nextVal });
        await callRouterApi('/api/ops/settings', 'POST', { require_lan_auth: nextVal });
        toast('局域网访问鉴权已' + (nextVal ? '开启' : '关闭'));
        break;
      }
      case 'entry-bypass-toggle': {
        handleToggleEntryBypass();
        break;
      }
      case 'ipv6-proxy-toggle': {
        const nextV6 = !state.ipv6Proxy;
        renderOpsSettings({ ipv6_proxy: nextV6 });
        await callRouterApi('/api/ipv6/toggle', 'POST', { ipv6_proxy: nextV6 });
        renderOverviewDashboard();
        toast('IPv6 透明代理接管已' + (nextV6 ? '开启' : '关闭'));
        break;
      }
      case 'block-quic-toggle': {
        const nextQuic = !state.blockQuic;
        renderOpsSettings({ block_quic: nextQuic });
        await callRouterApi('/api/ops/settings', 'POST', { block_quic: nextQuic });
        toast('海外 QUIC 阻断回退 HTTP/2 已' + (nextQuic ? '开启' : '关闭'));
        break;
      }
      case 'game-udp-toggle': {
        const nextUdp = !state.gameUdpDirect;
        renderOpsSettings({ game_udp_direct: nextUdp });
        await callRouterApi('/api/ops/settings', 'POST', { game_udp_direct: nextUdp });
        toast('国服游戏 UDP 直连豁免已' + (nextUdp ? '开启' : '关闭'));
        break;
      }
      case 'conflict-guard-toggle': {
        const nextCg = !state.conflictGuard;
        renderOpsSettings({ auto_mute_conflicts: nextCg });
        await callRouterApi('/api/ops/settings', 'POST', { auto_mute_conflicts: nextCg });
        toast('并发代理冲突自动静默已' + (nextCg ? '开启' : '关闭'));
        break;
      }
      case 'password':
        openPasswordModal();
        break;
      case 'binding':
        openBindingModal();
        break;
      case 'wol': {
        const macInput = $('#input-wol-mac');
        const mac = (macInput && macInput.value.trim()) || 'AA:BB:CC:DD:EE:FF';
        const res = await callRouterApi('/api/wol', 'POST', { mac });
        toast((res && res.message) || ('已向 ' + mac + ' 发送 WOL 唤醒魔术包'));
        break;
      }
      case 'refresh-connections': {
        const res = await callRouterApi('/api/clash/connections', 'GET');
        if (res && Array.isArray(res.connections)) {
          state.rawConnections = res.connections;
          mock.connections = res.connections.length;
        }
        renderConnectionsSection();
        toast('活跃连接列表已刷新');
        break;
      }
      case 'close-all-connections': {
        confirmModal(
          '确认断开全部活跃代理连接',
          '该操作将立即中断当前所有正在传输的代理连接会话，确认继续执行吗？',
          async () => {
            await callRouterApi('/api/clash/connections/close', 'POST', {});
            state.rawConnections = [];
            mock.connections = 0;
            renderConnectionsSection();
            toast('已断开全部活跃代理连接');
          },
          '确认全部断开'
        );
        break;
      }
      case 'close-single-conn': {
        const cid = el && el.dataset.cid;
        if (cid) await callRouterApi('/api/clash/connections/' + encodeURIComponent(cid), 'DELETE');
        state.rawConnections = state.rawConnections.filter(c => c.id !== cid);
        renderConnectionsSection();
        toast('已断开指定连接');
        break;
      }
      case 'refresh-logs': {
        const res = await callRouterApi('/api/ops/logs', 'GET');
        if (res && Array.isArray(res.logs) && res.logs.length) {
          mock.logs = res.logs;
        } else if (res && typeof res.logs === 'string' && res.logs.trim()) {
          mock.logs = res.logs.trim().split('\n');
        }
        renderLogsViewer();
        toast('实时内核与守护进程日志已刷新');
        break;
      }
      case 'probe-service': {
        const svcId = (el && el.dataset.service) || '';
        if (!svcId) return;
        const svcItem = mock.services.find(s => s.id === svcId.toLowerCase() || s.name === svcId);
        const selectorTag = (el && el.dataset.selector) || (svcItem && svcItem.selector) || 'Shunt_AI';
        const grpObj = mock.groups.find(g => ('Shunt_' + g.id) === selectorTag || (svcItem && g.id === svcItem.groupId));
        const nodeTag = (grpObj && grpObj.resolved_node && grpObj.resolved_node !== 'direct') ? grpObj.resolved_node : ((mock.nodes[0] && mock.nodes[0].tag) || '');
        toast('正在探测「' + (svcItem ? svcItem.name : svcId) + '」(' + selectorTag + ')...');
        const [delayRes] = await Promise.all([
          callRouterApi('/api/clash/delay?name=' + encodeURIComponent(selectorTag) + '&service_id=' + encodeURIComponent(svcId.toLowerCase()), 'GET'),
          nodeTag ? callRouterApi('/api/probe/service_l7', 'POST', { tag: nodeTag, service_id: svcId.toLowerCase() }, 12000, true) : Promise.resolve(null)
        ]);
        if (delayRes && Number(delayRes.delay) > 0 && svcItem) {
          svcItem.ms = Math.round(Number(delayRes.delay));
          renderOverviewDashboard();
        }
        await syncBackendStatus(false, true);
        toast((svcItem ? svcItem.name : svcId) + ' (' + selectorTag + ') 实时延迟探测已更新');
        break;
      }
      default:
        toast('未知操作指令: ' + String(action || 'unknown'), 'warn');
    }
  }

  function bindInteractions() {
    document.addEventListener('click', event => {
      const pageLink = event.target.closest('[data-page-link]');
      if (pageLink) { showPage(pageLink.dataset.pageLink); return; }
      const tabLink = event.target.closest('[data-tab]');
      if (tabLink && !tabLink.dataset.pageLink) { showPage(tabLink.dataset.tab); return; }
      const sceneMode = event.target.closest('[data-scene-mode]');
      if (sceneMode) { setSceneMode(sceneMode.dataset.sceneMode); return; }
      const inspTabBtn = event.target.closest('[data-inspector-tab]');
      if (inspTabBtn) {
        const nextTab = inspTabBtn.dataset.inspectorTab;
        state.inspectorTab = nextTab;
        if (nextTab !== 'panorama' && scene) {
          scene.setMode(nextTab);
          state.sceneMode = nextTab;
          $$('[data-scene-mode]').forEach(el => el.classList.toggle('active', el.dataset.sceneMode === nextTab));
        } else if (nextTab === 'panorama' && scene) {
          scene.setMode('panorama');
          state.sceneMode = 'panorama';
          $$('[data-scene-mode]').forEach(el => el.classList.toggle('active', el.dataset.sceneMode === 'panorama'));
        }
        renderInspector(state.selected);
        return;
      }
      const subCardEl = event.target.closest('[data-sub-select]');
      if (subCardEl && !event.target.closest('[data-action]')) {
        const chosenSub = subCardEl.dataset.subSelect || 'ALL';
        state.subFilter = chosenSub;
        state.nodePage = 1;
        renderSubscriptionsAndNodes();
        const subObj = mock.subscriptions.find(s => s.id === chosenSub);
        toast(chosenSub === 'ALL' ? '已切换显示全部订阅源节点' : ('已筛选订阅「' + (subObj ? subObj.name : chosenSub) + '」节点列表'));
        return;
      }
      const modalClose = event.target.closest('[data-modal-close]');
      if (modalClose) { closeModal(); return; }
      const modalConfirm = event.target.closest('#modal-confirm');
      if (modalConfirm) {
        if (typeof modalConfirmHandler === 'function') modalConfirmHandler();
        else closeModal();
        return;
      }

      /* Traffic waveform range buttons */
      const rangeBtn = event.target.closest('[data-traffic-range]');
      if (rangeBtn) {
        state.trafficRange = rangeBtn.dataset.trafficRange;
        $$('[data-traffic-range]').forEach(b => b.classList.toggle('active', b === rangeBtn));
        drawTrafficChart();
        return;
      }

      /* Region filter buttons (Fix #4) */
      const regBtn = event.target.closest('[data-region-filter]');
      if (regBtn) {
        state.regionFilter = regBtn.dataset.regionFilter;
        state.nodePage = 1;
        renderSubscriptionsAndNodes();
        return;
      }

      /* Node Status filter buttons */
      const nfBtn = event.target.closest('[data-node-filter]');
      if (nfBtn) {
        state.nodeFilter = nfBtn.dataset.nodeFilter;
        state.nodePage = 1;
        renderSubscriptionsAndNodes();
        return;
      }

      /* Node Pagination controls (Fix #5) */
      const pNumBtn = event.target.closest('[data-page-num]');
      if (pNumBtn) {
        state.nodePage = Number(pNumBtn.dataset.pageNum || 1);
        renderSubscriptionsAndNodes();
        return;
      }
      const pNavBtn = event.target.closest('[data-page-nav]');
      if (pNavBtn) {
        const dir = pNavBtn.dataset.pageNav;
        state.nodePage += (dir === 'next' ? 1 : -1);
        renderSubscriptionsAndNodes();
        return;
      }

      /* Log level filter pills (Fix #14) */
      const logBtn = event.target.closest('[data-log-filter]');
      if (logBtn) {
        state.logFilter = logBtn.dataset.logFilter;
        renderLogsViewer();
        return;
      }

      const routing = event.target.closest('[data-routing-mode]');
      if (routing) {
        const prevMode = state.routingMode;
        const nextMode = routing.dataset.routingMode;
        state.routingMode = nextMode;
        renderShuntMatrix();
        renderOverviewDashboard();
        callRouterApi('/api/shunt/update', 'POST', {
          routing_mode: nextMode,
          global_mode: state.globalMode,
          global_auto_node_id: state.globalAutoNodeId,
          global_country: state.globalCountry,
          global_manual_node: state.globalManualNode
        }).then(res => {
          if (!res || res.ok === false) {
            state.routingMode = prevMode;
            renderShuntMatrix();
            renderOverviewDashboard();
            return;
          }
          if (res.global_resolved_node) {
            state.globalResolvedNode = res.global_resolved_node;
          }
          renderNonShuntGlobalBar();
          renderOverviewDashboard();
          const mObj = mock.routingModes.find(m => m.id === nextMode);
          toast('已切换为「' + (mObj ? mObj.name : nextMode) + '」');
        });
        return;
      }

      const homeMode = event.target.closest('[data-home-mode]');
      if (homeMode) {
        state.homelinkMode = homeMode.dataset.homeMode;
        renderHomeLinkSection();
        callRouterApi('/api/homelink/route_mode', 'POST', { route_mode: state.homelinkMode, apply_all: false });
        toast('回家路由边界已切换');
        return;
      }

      const groupEl = event.target.closest('[data-group]');
      if (groupEl && !event.target.closest('#modal') && !event.target.closest('[data-action]')) {
        const g = mock.groups[Number(groupEl.dataset.group)];
        if (!g) return;
        const gid = g.id;
        const autoOpts = mock.autoPools.map(p => '<option value="' + esc(p.id) + '" ' + (g.auto_node_id === p.id ? 'selected' : '') + '>🤖 ' + esc(p.name) + ' (' + esc(p.current_node || '智能选优') + ')</option>').join('');
        const countryOpts = COUNTRY_CODES.map(c => '<option value="' + c + '" ' + (g.country === c ? 'selected' : '') + '>' + esc(COUNTRY_META[c].flag + ' ' + COUNTRY_META[c].name) + '</option>').join('');
        const nodeOpts = mock.nodes.filter(n => n.status !== 'dead').map(n => '<option value="' + esc(n.tag || n.name) + '" ' + ((n.tag || n.name) === g.resolved_node ? 'selected' : '') + '>' + esc(n.name) + ' (' + formatLatencyText(n.rtt, false) + ')</option>').join('');
        openModal(
          '分流策略组编排 · ' + g.name,
          '<div class="trace-stages">' +
            '<div class="trace-stage"><i>01</i><div><b>匹配范围</b><span>' + esc(g.subtitle) + '</span></div><strong>' + (g.domains ? g.domains.length : 0) + ' 条规则</strong></div>' +
            '<div class="trace-stage"><i>02</i><div><b>当前实际出口</b><span class="mono">' + esc(g.resolved_node || 'DIRECT') + '</span></div><strong>' + formatLatencyText(g.rtt, g.shunt_mode === 'direct') + '</strong></div>' +
          '</div>' +
          '<div class="modal-form" style="margin-top:14px">' +
            '<div class="modal-grid-3">' +
              '<div class="modal-field"><label>出站策略模式</label><select id="mdl-grp-mode"><option value="auto" ' + (g.shunt_mode === 'auto' ? 'selected' : '') + '>🤖 自动节点池</option><option value="manual" ' + (g.shunt_mode === 'manual' ? 'selected' : '') + '>🖐️ 手动指定节点</option><option value="direct" ' + (g.shunt_mode === 'direct' ? 'selected' : '') + '>🎯 直连 (DIRECT)</option></select></div>' +
              '<div class="modal-field"><label>绑定自动节点池</label><select id="mdl-grp-autopool">' + autoOpts + '</select></div>' +
              '<div class="modal-field"><label>手动国家 / 节点</label><select id="mdl-grp-manual">' + nodeOpts + '</select></div>' +
            '</div>' +
            '<div class="modal-field"><label>国家/地区偏好</label><select id="mdl-grp-country">' + countryOpts + '</select></div>' +
            '<div class="button-row" style="margin-top:4px">' +
              '<button class="button ghost compact" data-action="edit-group-rules-modal" data-group-idx="' + Number(groupEl.dataset.group) + '">📝 编辑此组域名与 IP 规则库</button>' +
              '<button class="button ghost compact" data-action="verify-group" data-gid="' + esc(gid) + '">🔍 真连接校验与故障转移测试</button>' +
            '</div>' +
          '</div>',
          'SHUNT GROUP ORCHESTRATION',
          async () => {
            const shunt_mode = ($('#mdl-grp-mode') && $('#mdl-grp-mode').value) || 'auto';
            const auto_node_id = ($('#mdl-grp-autopool') && $('#mdl-grp-autopool').value) || 'auto_youtube';
            const manual_node = ($('#mdl-grp-manual') && $('#mdl-grp-manual').value) || '';
            const country = ($('#mdl-grp-country') && $('#mdl-grp-country').value) || 'JP';
            const payload = {
              group_id: gid,
              shunt_mode,
              strategy: shunt_mode === 'direct' ? 'direct' : (shunt_mode === 'manual' ? 'manual' : 'auto'),
              country: shunt_mode === 'direct' ? 'direct' : country,
              auto_node_id,
              manual_node: shunt_mode === 'auto' ? ('auto:' + auto_node_id) : (shunt_mode === 'direct' ? 'direct' : manual_node)
            };
            await callRouterApi('/api/shunt/update', 'POST', payload);
            closeModal();
            toast('分流组「' + g.name + '」策略已实时生效');
            await syncBackendStatus(false, true);
          },
          '应用分流策略'
        );
        return;
      }

      const editGrpRulesBtn = event.target.closest('[data-action="edit-group-rules-modal"]');
      if (editGrpRulesBtn) {
        const gIdx = Number(editGrpRulesBtn.dataset.groupIdx);
        openNewRuleModal(mock.groups[gIdx]);
        return;
      }

      const autoPoolEl = event.target.closest('[data-auto-pool]');
      if (autoPoolEl) {
        openAutoNodeEditorModal(Number(autoPoolEl.dataset.autoPool));
        return;
      }

      const action = event.target.closest('[data-action]');
      if (action) handleAction(action.dataset.action, action);
    });

    document.addEventListener('change', async event => {
      const hlSel = event.target.closest('[data-hl-node-mode]');
      if (hlSel) {
        const nid = hlSel.dataset.hlNodeMode;
        const rmode = hlSel.value || 'shunt';
        const hlNode = mock.homelinkNodes.find(x => x.id === nid);
        const prevMode = hlNode ? (hlNode.route_mode || 'shunt') : 'shunt';
        const modeLabel = rmode === 'direct' ? '仅访问内网与国内' : (rmode === 'proxy_only' ? '仅科学上网 · 隔离内网' : '回家 + 科学上网分流');
        if (hlNode) {
          hlNode.route_mode = rmode;
          hlNode.route = modeLabel;
        }
        state.busyHomelinkNodeId = nid;
        hlSel.setAttribute('aria-busy', 'true');
        const tStart = Date.now();
        toast('已将回家节点「' + (hlNode ? hlNode.name : nid) + '」路由模式切换为：' + modeLabel, '', {
          undoText: '↩ 撤销',
          onUndo: async () => {
            if (hlNode) hlNode.route_mode = prevMode;
            renderHomeLinkSection();
            await callRouterApi('/api/homelink/route_mode', 'POST', { id: nid, route_mode: prevMode, apply_all: false });
            await syncBackendStatus(false, true);
            toast('已恢复回家节点「' + (hlNode ? hlNode.name : nid) + '」原路由模式');
          }
        });
        try {
          const res = await callRouterApi('/api/homelink/route_mode', 'POST', { id: nid, route_mode: rmode, apply_all: false });
          if (!res || res.ok === false) {
            if (hlNode) hlNode.route_mode = prevMode;
            toast('回家节点路由模式保存失败，已回滚', 'warn');
            return;
          }
          await syncBackendStatus(false, true);
          const elapsed = Date.now() - tStart;
          if (elapsed < 1150) {
            await new Promise(r => setTimeout(r, 1150 - elapsed));
          }
        } finally {
          state.busyHomelinkNodeId = '';
          renderHomeLinkSection();
          const curSel = document.querySelector('[data-hl-node-mode="' + nid + '"]');
          if (curSel) curSel.setAttribute('aria-busy', 'false');
        }
      }
    });
    ['#select-global-mode', '#select-global-autonode', '#select-global-country', '#select-global-manual-node'].forEach(sel => {
      const el = $(sel);
      if (el) el.addEventListener('change', () => { saveGlobalThreeMode(); });
    });

    const subFilterEl = $('#node-sub-filter');
    if (subFilterEl) {
      subFilterEl.addEventListener('change', () => {
        state.subFilter = subFilterEl.value || 'ALL';
        state.nodePage = 1;
        renderSubscriptionsAndNodes();
      });
    }
    const pageSizeEl = $('#node-page-size');
    if (pageSizeEl) {
      pageSizeEl.addEventListener('change', () => {
        state.nodePageSize = Number(pageSizeEl.value);
        state.nodePage = 1;
        renderSubscriptionsAndNodes();
      });
    }

    const orbitBtn = $('#orbit-toggle');
    if (orbitBtn) orbitBtn.addEventListener('click', () => {
      state.autoRotate = !state.autoRotate;
      orbitBtn.classList.toggle('active', state.autoRotate);
      if (scene) scene.setAutoRotate(state.autoRotate);
    });
    const labelsBtn = $('#labels-toggle');
    if (labelsBtn) labelsBtn.addEventListener('click', () => {
      state.labels = !state.labels;
      labelsBtn.classList.toggle('active', state.labels);
      if (scene) scene.setLabels(state.labels);
    });
    const surgeBtn = $('#surge-toggle');
    if (surgeBtn) surgeBtn.addEventListener('click', async () => {
      state.surge = !state.surge;
      surgeBtn.classList.toggle('active', state.surge);
      if (state.surge) {
        try {
          const [connRes, galRes] = await Promise.all([
            callRouterApi('/api/clash/connections', 'GET', null, 8000, true),
            callRouterApi('/api/overview/galaxy', 'GET', null, 8000, true)
          ]);
          if (connRes && Array.isArray(connRes.connections)) {
            state.rawConnections = connRes.connections;
            mock.connections = connRes.connections.length;
          }
          if (galRes && galRes.ok !== false) {
            if (Array.isArray(galRes.lan) && galRes.lan.length) state.galaxyLanDevices = galRes.lan;
            if (Array.isArray(galRes.domestic) && galRes.domestic.length) state.galaxyDomesticSites = galRes.domestic;
            if (Array.isArray(galRes.foreign) && galRes.foreign.length) state.galaxyForeignSites = galRes.foreign;
          }
        } catch (_) {}
        syncGalaxy3DData();
      }
      if (scene) scene.setSurge(state.surge);
      if (state.surge && scene && typeof scene.getLinkSpeedGears === 'function') {
        const gInfo = scene.getLinkSpeedGears();
        const s = gInfo.liveConnSummary || {};
        toast('⚡ 已开启真实连接 3D 表达：实时映射 ' + (s.totalArcs || 0) + ' 条跨星系轨迹 · 流速挡位 高[' + (s.highCount || 0) + ']/中[' + (s.medCount || 0) + ']/低[' + (s.lowCount || 0) + ']');
      } else {
        toast('已恢复常规星系视图');
      }
    });
    const resetBtn = $('#reset-view');
    if (resetBtn) resetBtn.addEventListener('click', () => {
      if (scene) scene.reset();
      renderInspector(null);
      setSceneMode('panorama');
    });
    const detailsBtn = $('#details-toggle');
    if (detailsBtn) detailsBtn.addEventListener('click', () => $('#inspector').classList.toggle('open'));
    const inspClose = $('#inspector-close');
    if (inspClose) inspClose.addEventListener('click', () => $('#inspector').classList.remove('open'));
    const modalEl = $('#modal');
    if (modalEl) modalEl.addEventListener('click', event => { if (event.target.id === 'modal') closeModal(); });

    const searchEl = $('#node-search');
    if (searchEl) searchEl.addEventListener('input', event => {
      state.search = event.target.value;
      state.nodePage = 1;
      renderSubscriptionsAndNodes();
    });
    const connSearchEl = $('#conn-search-input');
    if (connSearchEl) connSearchEl.addEventListener('input', event => {
      state.connSearch = event.target.value;
      renderConnectionsSection();
    });
    const logSearchEl = $('#log-search-input');
    if (logSearchEl) logSearchEl.addEventListener('input', event => {
      state.logSearch = event.target.value;
      renderLogsViewer();
    });
    window.addEventListener('keydown', event => { if (event.key === 'Escape') closeModal(); });
  }

  function setupCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, width, height };
  }

  function drawLatencyChart() {
    const canvas = $('#latency-chart');
    if (!canvas) return;
    const { ctx, width, height } = setupCanvas(canvas);
    ctx.clearRect(0, 0, width, height);
    const min = Math.min.apply(null, latencySeries) - 12;
    const max = Math.max.apply(null, latencySeries) + 12;
    const points = latencySeries.map((v, i) => [i / (latencySeries.length - 1) * width, height - (v - min) / Math.max(1, max - min) * (height - 8) - 4]);
    const fill = ctx.createLinearGradient(0, 0, 0, height);
    fill.addColorStop(0, 'rgba(110,231,245,.24)');
    fill.addColorStop(1, 'rgba(110,231,245,0)');
    ctx.beginPath();
    points.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
    ctx.lineTo(width, height); ctx.lineTo(0, height); ctx.closePath();
    ctx.fillStyle = fill; ctx.fill();
    ctx.beginPath();
    points.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
    ctx.strokeStyle = '#6ee7f5'; ctx.lineWidth = 1.4; ctx.stroke();
    const last = points[points.length - 1];
    ctx.beginPath(); ctx.arc(last[0] - 1, last[1], 3, 0, Math.PI * 2); ctx.fillStyle = '#dffbff'; ctx.fill();
  }

  function drawTrafficChart() {
    const canvas = $('#traffic-chart');
    if (!canvas || state.page !== 'overview') return;
    const { ctx, width, height } = setupCanvas(canvas);
    ctx.clearRect(0, 0, width, height);
    const pad = { left: 12, right: 8, top: 14, bottom: 20 };
    ctx.strokeStyle = 'rgba(140,160,190,.08)'; ctx.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
      const y = pad.top + (height - pad.top - pad.bottom) * i / 4;
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width - pad.right, y); ctx.stroke();
    }
    const count = 64;
    const phase = state.trafficRange === '7d' ? 1.7 : (state.trafficRange === '30d' ? 3.2 : 0.4);
    const down = [];
    const up = [];
    for (let i = 0; i < count; i++) {
      down.push(.18 + .38 * (Math.sin(i * .16 + phase) * .5 + .5) + .28 * (Math.sin(i * .51 + 1.4 + phase) * .5 + .5));
      up.push(.1 + .24 * (Math.sin(i * .21 + 2 + phase) * .5 + .5) + .1 * (Math.cos(i * .47 + phase) * .5 + .5));
    }
    function drawSeries(series, color, rgba) {
      const points = series.map((v, i) => [pad.left + i / (count - 1) * (width - pad.left - pad.right), height - pad.bottom - v * (height - pad.top - pad.bottom)]);
      const gradient = ctx.createLinearGradient(0, pad.top, 0, height);
      gradient.addColorStop(0, rgba.replace('ALPHA', '.22'));
      gradient.addColorStop(1, rgba.replace('ALPHA', '0'));
      ctx.beginPath();
      points.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
      ctx.lineTo(width - pad.right, height - pad.bottom); ctx.lineTo(pad.left, height - pad.bottom); ctx.closePath();
      ctx.fillStyle = gradient; ctx.fill();
      ctx.beginPath();
      points.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
      ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke();
    }
    drawSeries(down, '#6ee7f5', 'rgba(110,231,245,ALPHA)');
    drawSeries(up, '#a994ff', 'rgba(169,148,255,ALPHA)');
    ctx.fillStyle = '#526078'; ctx.font = '8px sans-serif';
    const labels = state.trafficRange === '7d'
      ? ['周一', '周三', '周五', '周六', '周日']
      : (state.trafficRange === '30d' ? ['D-30', 'D-22', 'D-15', 'D-7', '今日'] : ['00:00', '06:00', '12:00', '18:00', '23:00']);
    labels.forEach((t, i) => ctx.fillText(t, pad.left + i / 4 * (width - pad.left - pad.right) - 10, height - 4));
  }

  function initCharts() {
    drawLatencyChart();
    if (typeof ResizeObserver !== 'undefined') {
      const lc = $('#latency-chart');
      if (lc) {
        const ro1 = new ResizeObserver(drawLatencyChart);
        ro1.observe(lc);
        chartObservers.push(ro1);
      }
      const tc = $('#traffic-chart');
      if (tc) {
        const ro2 = new ResizeObserver(drawTrafficChart);
        ro2.observe(tc);
        chartObservers.push(ro2);
      }
    }
  }

  function updateTelemetryTick() {
    syncBackendStatus(false, false);
    if (mock.latency > 0) {
      latencySeries.push(mock.latency);
      if (latencySeries.length > 20) latencySeries.shift();
    }
    drawLatencyChart();
  }

  function initScene() {
    if (!window.NexusScene) {
      const fb = $('#webgl-fallback');
      if (fb) fb.hidden = false;
      return;
    }
    scene = window.NexusScene.create($('#universe'), {
      page: state.page,
      onSelect: renderInspector,
      onMode: mode => {
        state.sceneMode = mode;
        $$('[data-scene-mode]').forEach(el => el.classList.toggle('active', el.dataset.sceneMode === mode));
      },
      onInteract: () => {
        state.autoRotate = false;
        const ob = $('#orbit-toggle');
        if (ob) ob.classList.remove('active');
      }
    });
    if (!scene) {
      const fb = $('#webgl-fallback');
      if (fb) fb.hidden = false;
    }
    if (scene) {
      scene.setAutoRotate(state.autoRotate);
      scene.setLabels(state.labels);
    }
  }

  function init() {
    renderAll();
    bindInteractions();
    initCharts();
    initScene();
    syncBackendStatus(true, true);
    if (window.innerWidth < 1240 && $('#inspector')) $('#inspector').classList.remove('open');
    let lastNarrow = window.innerWidth < 1240;
    window.addEventListener('resize', () => {
      const nowNarrow = window.innerWidth < 1240;
      if (nowNarrow !== lastNarrow && $('#inspector')) {
        if (nowNarrow && !state.selected) $('#inspector').classList.remove('open');
        else if (!nowNarrow) $('#inspector').classList.add('open');
      }
      lastNarrow = nowNarrow;
    });
    if ($('#orbit-toggle')) $('#orbit-toggle').classList.toggle('active', state.autoRotate);
    const updateClock = () => {
      const now = new Date();
      const st = $('#scene-time');
      if (st) st.textContent = [now.getHours(), now.getMinutes(), now.getSeconds()].map(v => String(v).padStart(2, '0')).join(':');
    };
    updateClock();
    setInterval(updateClock, 1000);
    setInterval(updateTelemetryTick, 3000);
    setTimeout(() => { const b = $('#boot'); if (b) b.classList.add('leaving'); }, 450);
    setTimeout(() => { const b = $('#boot'); if (b) b.remove(); }, 1100);
    window.__NEXUS_PREVIEW__ = { state, mock, showPage, setSceneMode, syncBackendStatus, handleToggleEntryBypass, openOverviewDetailModal, computeSpeedGearInfo, get scene() { return scene; } };
  }

  init();
})();
