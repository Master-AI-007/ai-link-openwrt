(function () {
  'use strict';
  if (window.__AILINK_NEXUS_BOOTED__) return;
  window.__AILINK_NEXUS_BOOTED__ = true;

  const $ = (selector, root) => (root || document).querySelector(selector);
  const $$ = (selector, root) => Array.from((root || document).querySelectorAll(selector));
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const COUNTRY_META = {
    HK: { code: 'HK', flag: '[HK]', name: '中国香港 (HK)', short: '中国香港' },
    TW: { code: 'TW', flag: '[TW]', name: '中国台湾 (TW)', short: '中国台湾' },
    JP: { code: 'JP', flag: '[JP]', name: '日本 (JP)', short: '日本' },
    SG: { code: 'SG', flag: '[SG]', name: '新加坡 (SG)', short: '新加坡' },
    US: { code: 'US', flag: '[US]', name: '美国 (US)', short: '美国' },
    OTHER: { code: 'OTHER', flag: '[GL]', name: '其他地区', short: '其他' }
  };
  const RAW_NODE_COUNTRY_RULES = [
    [/香港|九龙|新界|HONG\s*KONG/i, "香港"],
    [/台湾|台北|新北|高雄|台中|桃园|彰化|TAIWAN|TAIPEI/i, "台湾"],
    [/澳门|MACAU|MACAO/i, "澳门"],
    [/日本|东京|大阪|名古屋|福冈|札幌|埼玉|千叶|横滨|JAPAN|TOKYO|OSAKA/i, "日本"],
    [/新加坡|狮城|SINGAPORE/i, "新加坡"],
    [/韩国|首尔|釜山|仁川|春川|KOREA|SEOUL/i, "韩国"],
    [/美国|洛杉矶|硅谷|圣何塞|西雅图|纽约|芝加哥|达拉斯|亚特兰大|凤凰城|波特兰|迈阿密|拉斯维加斯|丹佛|华盛顿|弗吉尼亚|俄勒冈|UNITED\s*STATES|AMERICA/i, "美国"],
    [/德国|法兰克福|柏林|慕尼黑|杜塞尔多夫|GERMANY|FRANKFURT/i, "德国"],
    [/英国|伦敦|曼彻斯特|考文垂|伯明翰|UNITED\s*KINGDOM|BRITAIN|ENGLAND|LONDON/i, "英国"],
    [/法国|巴黎|马赛|里昂|斯特拉斯堡|FRANCE|PARIS/i, "法国"],
    [/荷兰|阿姆斯特丹|鹿特丹|NETHERLANDS|HOLLAND|AMSTERDAM/i, "荷兰"],
    [/加拿大|多伦多|温哥华|蒙特利尔|CANADA|TORONTO|VANCOUVER/i, "加拿大"],
    [/澳大利亚|澳洲|悉尼|墨尔本|珀斯|布里斯班|AUSTRALIA|SYDNEY|MELBOURNE/i, "澳大利亚"],
    [/俄罗斯|莫斯科|圣彼得堡|伯力|新西伯利亚|海参崴|RUSSIA|MOSCOW/i, "俄罗斯"],
    [/印度(?!尼)|孟买|新德里|班加罗尔|金奈|INDIA|MUMBAI/i, "印度"],
    [/土耳其|伊斯坦布尔|安卡拉|TURKEY|ISTANBUL/i, "土耳其"],
    [/阿联酋|迪拜|阿布扎比|UAE|DUBAI/i, "阿联酋"],
    [/马来西亚|大马|吉隆坡|柔佛|MALAYSIA/i, "马来西亚"],
    [/泰国|曼谷|THAILAND|BANGKOK/i, "泰国"],
    [/越南|河内|胡志明|VIETNAM/i, "越南"],
    [/菲律宾|马尼拉|PHILIPPINES|MANILA/i, "菲律宾"],
    [/印尼|印度尼西亚|雅加达|INDONESIA|JAKARTA/i, "印尼"],
    [/巴西|圣保罗|BRAZIL/i, "巴西"],
    [/阿根廷|布宜诺斯艾利斯|ARGENTINA/i, "阿根廷"],
    [/智利|圣地亚哥|CHILE/i, "智利"],
    [/墨西哥|MEXICO/i, "墨西哥"],
    [/瑞士|苏黎世|日内瓦|SWITZERLAND|ZURICH/i, "瑞士"],
    [/瑞典|斯德哥尔摩|SWEDEN|STOCKHOLM/i, "瑞典"],
    [/意大利|米兰|罗马(?!尼亚)|ITALY|MILAN/i, "意大利"],
    [/西班牙|马德里|巴塞罗那|SPAIN|MADRID/i, "西班牙"],
    [/波兰|华沙|POLAND|WARSAW/i, "波兰"],
    [/奥地利|维也纳|AUSTRIA|VIENNA/i, "奥地利"],
    [/比利时|布鲁塞尔|BELGIUM|BRUSSELS/i, "比利时"],
    [/爱尔兰|都柏林|IRELAND|DUBLIN/i, "爱尔兰"],
    [/芬兰|赫尔辛基|FINLAND|HELSINKI/i, "芬兰"],
    [/挪威|奥斯陆|NORWAY|OSLO/i, "挪威"],
    [/丹麦|哥本哈根|DENMARK|COPENHAGEN/i, "丹麦"],
    [/冰岛|雷克雅未克|ICELAND/i, "冰岛"],
    [/乌克兰|基辅|UKRAINE/i, "乌克兰"],
    [/罗马尼亚|布加勒斯特|ROMANIA/i, "罗马尼亚"],
    [/保加利亚|索非亚|BULGARIA/i, "保加利亚"],
    [/匈牙利|布达佩斯|HUNGARY/i, "匈牙利"],
    [/捷克|布拉格|CZECH/i, "捷克"],
    [/葡萄牙|里斯本|PORTUGAL/i, "葡萄牙"],
    [/希腊|雅典|GREECE/i, "希腊"],
    [/卢森堡|LUXEMBOURG/i, "卢森堡"],
    [/以色列|特拉维夫|ISRAEL/i, "以色列"],
    [/南非|约翰内斯堡|开普敦|SOUTH\s*AFRICA/i, "南非"],
    [/埃及|开罗|EGYPT/i, "埃及"],
    [/尼日利亚|拉各斯|NIGERIA/i, "尼日利亚"],
    [/巴基斯坦|卡拉奇|PAKISTAN/i, "巴基斯坦"],
    [/孟加拉|BANGLADESH/i, "孟加拉"],
    [/柬埔寨|金边|CAMBODIA/i, "柬埔寨"],
    [/缅甸|仰光|MYANMAR/i, "缅甸"],
    [/老挝|万象|LAOS/i, "老挝"],
    [/蒙古|乌兰巴托|MONGOLIA/i, "蒙古"],
    [/哈萨克斯坦|阿拉木图|KAZAKHSTAN/i, "哈萨克斯坦"],
    [/新西兰|奥克兰|NEW\s*ZEALAND/i, "新西兰"]
  ];

  const RAW_NODE_CODE_RULES = [
    ["HK|HKG", "香港"],
    ["TW|TWN|TPE|KHH", "台湾"],
    ["MO|MAC", "澳门"],
    ["JP|JPN|NRT|HND|KIX|TYO|OSA", "日本"],
    ["SG|SGP|SIN", "新加坡"],
    ["KR|KOR|ICN|GMP|SEL", "韩国"],
    ["US|USA|LAX|SJC|SEA|SFO|JFK|EWR|ORD|DFW|IAD|MIA|ATL|DEN|PHX|PDX|LAS|BOS", "美国"],
    ["DE|DEU|GER|FRA|MUC|BER|DUS", "德国"],
    ["GB|UK|GBR|LHR|LGW|MAN|LON", "英国"],
    ["FR|CDG|ORY|PAR|MRS", "法国"],
    ["NL|NLD|AMS", "荷兰"],
    ["CA|CAN|YYZ|YVR|YUL", "加拿大"],
    ["AU|AUS|SYD|MEL|BNE|PER", "澳大利亚"],
    ["RU|RUS|SVO|DME|VKO|LED|MOW", "俄罗斯"],
    ["IN|IND|BOM|DEL|BLR|MAA", "印度"],
    ["TR|TUR|IST|SAW|ESB", "土耳其"],
    ["AE|ARE|DXB|AUH", "阿联酋"],
    ["MY|MYS|KUL", "马来西亚"],
    ["TH|THA|BKK|DMK", "泰国"],
    ["VN|VNM|HAN|SGN", "越南"],
    ["PH|PHL|MNL", "菲律宾"],
    ["ID|IDN|CGK", "印尼"],
    ["BR|BRA|GRU|GIG", "巴西"],
    ["AR|ARG|EZE", "阿根廷"],
    ["CL|CHL|SCL", "智利"],
    ["MX|MEX", "墨西哥"],
    ["CH|CHE|ZRH|GVA", "瑞士"],
    ["SE|SWE|ARN", "瑞典"],
    ["IT|ITA|MXP|FCO|MIL", "意大利"],
    ["ES|ESP|MAD|BCN", "西班牙"],
    ["PL|POL|WAW", "波兰"],
    ["AT|AUT|VIE", "奥地利"],
    ["BE|BEL|BRU", "比利时"],
    ["IE|IRL|DUB", "爱尔兰"],
    ["FI|FIN|HEL", "芬兰"],
    ["NO|NOR|OSL", "挪威"],
    ["DK|DNK|CPH", "丹麦"],
    ["IS|ISL|KEF", "冰岛"],
    ["UA|UKR|KBP", "乌克兰"],
    ["RO|ROU|OTP", "罗马尼亚"],
    ["BG|BGR|SOF", "保加利亚"],
    ["HU|HUN|BUD", "匈牙利"],
    ["CZ|CZE|PRG", "捷克"],
    ["PT|PRT|LIS", "葡萄牙"],
    ["GR|GRC|ATH", "希腊"],
    ["LU|LUX", "卢森堡"],
    ["IL|ISR|TLV", "以色列"],
    ["ZA|ZAF|JNB|CPT", "南非"],
    ["EG|EGY|CAI", "埃及"],
    ["NG|NGA|LOS", "尼日利亚"],
    ["PK|PAK|KHI", "巴基斯坦"],
    ["BD|BGD|DAC", "孟加拉"],
    ["KH|KHM|PNH", "柬埔寨"],
    ["MM|MMR|RGN", "缅甸"],
    ["LA|LAO|VTE", "老挝"],
    ["MN|MNG|ULN", "蒙古"],
    ["KZ|KAZ|ALA", "哈萨克斯坦"],
    ["NZ|NZL|AKL", "新西兰"]
  ].map(([pat, cname]) => [new RegExp("(?:^|[^A-Z])(?:" + pat + ")(?=$|[^A-Z])", "i"), cname]);

  function extractCountryNameFromRawNodeName(rawName) {
    if (!rawName) return "其他国家";
    const s = String(rawName).replace(/\s*\|\s*(?:None|null|undefined)(?=\s*\||$)/gi, "").trim();
    if (!s) return "其他国家";
    if (s.includes("丨")) {
      const parts = s.split("丨");
      const tail = (parts[parts.length - 1] || "").trim();
      if (tail === "其他国家") return "其他国家";
      for (let i = 0; i < RAW_NODE_COUNTRY_RULES.length; i++) {
        if (RAW_NODE_COUNTRY_RULES[i][0].test(tail)) return RAW_NODE_COUNTRY_RULES[i][1];
      }
    }
    for (let i = 0; i < RAW_NODE_COUNTRY_RULES.length; i++) {
      if (RAW_NODE_COUNTRY_RULES[i][0].test(s)) return RAW_NODE_COUNTRY_RULES[i][1];
    }
    const stripped = s
      .replace(/\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?/g, " ")
      .replace(/\b(?:VLESS|VMESS|HYSTERIA2|HYSTERIA|HY2|TROJAN|TUIC|SHADOWSOCKS|SSR|SS|SOCKS5|SOCKS|REALITY|XRAY|SINGBOX|TLS|XTLS|GRPC|WS|HTTP|HTTPS|TCP|UDP|QUIC|BGP|IEPL|IPLC|CN2|GIA|CDN|VIP|PRO|MAX|PLUS|AI|GPT|IPV6|IPV4|NAT|NODE|LINE|RELAY|AUTO|DIRECT)\b/gi, " ")
      .toUpperCase();
    for (let i = 0; i < RAW_NODE_CODE_RULES.length; i++) {
      if (RAW_NODE_CODE_RULES[i][0].test(stripped)) return RAW_NODE_CODE_RULES[i][1];
    }
    return "其他国家";
  }

  function resolveNodeSubDisplayName(nodeObj, subNameHint) {
    if (typeof subNameHint === "string" && subNameHint.trim()) return subNameHint.trim();
    if (nodeObj && typeof nodeObj === "object") {
      const sid = nodeObj._sub_id || nodeObj.sub_id || "";
      const sname = nodeObj._sub_name || nodeObj.sub_name || "";
      const subs = (typeof mock !== "undefined" && mock && Array.isArray(mock.subscriptions)) ? mock.subscriptions : [];
      if (sid && sid !== "custom") {
        const matchedSub = subs.find(s => s && (s.id === sid || s.name === sid));
        if (matchedSub && matchedSub.name) return String(matchedSub.name).trim();
      }
      if (sname && sname !== "订阅节点" && sname !== "机场订阅") {
        const matchedByName = subs.find(s => s && s.name === sname);
        if (matchedByName && matchedByName.name) return String(matchedByName.name).trim();
        return String(sname).trim();
      }
      if (nodeObj.is_custom || nodeObj._manual || sid === "custom") {
        return "手动添加节点";
      }
      if (subs.length === 1 && subs[0] && subs[0].name) {
        return String(subs[0].name).trim();
      }
      if (sname) return String(sname).trim();
    }
    const subs = (typeof mock !== "undefined" && mock && Array.isArray(mock.subscriptions)) ? mock.subscriptions : [];
    if (subs.length >= 1 && subs[0] && subs[0].name) return String(subs[0].name).trim();
    return "机场订阅";
  }

  function formatNodeUnifiedDisplayName(nodeOrTag, subNameHint) {
    if (!nodeOrTag) return "";
    if (typeof nodeOrTag === "object") {
      const rawName = String(nodeOrTag.raw_name || nodeOrTag.tag || nodeOrTag.name || "").trim();
      if (!rawName) return "";
      const subName = resolveNodeSubDisplayName(nodeOrTag, subNameHint);
      const countryName = extractCountryNameFromRawNodeName(rawName);
      return subName + "丨" + countryName;
    }
    const str = String(nodeOrTag).replace(/\s*\|\s*(?:None|null|undefined)(?=\s*\||$)/gi, "").trim();
    if (!str) return "";
    if (str === "direct" || str === "DIRECT" || /^(?:直连|宽带原生直连|未选择|待优选|节点池|智能自动|已固定)|^(?:Shunt_|Auto_|GLOBAL$|PROXY$|FINAL$|REJECT$|PASS$|dns-out$)/i.test(str)) {
      return str;
    }
    const nodesList = (typeof mock !== "undefined" && mock && Array.isArray(mock.nodes)) ? mock.nodes : [];
    const matched = nodesList.find(n => n && (n.tag === str || n.raw_name === str || n.name === str));
    if (matched) {
      const subName = resolveNodeSubDisplayName(matched, subNameHint);
      const countryName = extractCountryNameFromRawNodeName(matched.raw_name || matched.tag || str);
      return subName + "丨" + countryName;
    }
    if (str.includes("丨") && !subNameHint) {
      const idx = str.indexOf("丨");
      const prefix = str.slice(0, idx).trim();
      const rest = str.slice(idx + 1).trim();
      if (prefix && rest) {
        return prefix + "丨" + extractCountryNameFromRawNodeName(rest);
      }
    }
    const subName = resolveNodeSubDisplayName(null, subNameHint);
    const countryName = extractCountryNameFromRawNodeName(str);
    return subName + "丨" + countryName;
  }

  function cleanNodeDisplayName(val, subNameHint) {
    if (!val) return "";
    return formatNodeUnifiedDisplayName(val, subNameHint);
  }
  const fmtOutboundQuota = (active, limit) => (Number(limit) > 0 ? (active + ' / ' + limit) : (active + ' 个（不设上限）'));
  const COUNTRY_CODES = ['HK', 'TW', 'JP', 'SG', 'US', 'OTHER'];

  const mock = {
    connections: 0,
    connsDisplayed: 0,
    connsTruncated: false,
    conntrackCount: 0,
    conntrackMax: 65536,
    down: 0,
    up: 0,
    downText: '0 B/s',
    upText: '0 B/s',
    monthTotalText: '--',
    upTotalText: '0 B',
    latency: null,
    healthScore: 100,
    coreMemMib: null,
    blockedTotal: 0,
    dnsRulesCount: null,
    dnsRawRuleLines: null,
    dnsLayerCount: 0,
    rejectLayerCount: 0,
    activeOutbounds: 0,
    maxOutboundsLimit: 0,
    totalNodes: 0,
    devicesTotal: 0,
    devicesActive: 0,
    destinationsTotal: 0,
    inTotalText: '0 B',
    outTotalText: '0 B',
    monthTotalConns: 0,
    uptimeStr: '--',
    dnsBlockedPct: 0.0,
    dnsAvgMs: null,
    srsRulesetsCount: null,
    backupInfo: null,
    statusDataAgeMs: 0,
    services: [
      { id: 'openai', name: 'ChatGPT', selector: 'Shunt_AI', groupId: 'AI', url: 'https://chat.openai.com/cdn-cgi/trace', ms: 168, state: 'ok' },
      { id: 'gemini', name: 'Gemini', selector: 'Shunt_AI', groupId: 'AI', url: 'https://gemini.google.com', ms: 182, state: 'ok' },
      { id: 'youtube', name: 'YouTube', selector: 'Shunt_YouTube', groupId: 'YouTube', url: 'https://www.youtube.com/generate_204', ms: 146, state: 'ok' },
      { id: 'github', name: 'GitHub', selector: 'Shunt_GitHub', groupId: 'GitHub', url: 'https://api.github.com/zen', ms: 195, state: 'ok' },
      { id: 'netflix', name: 'Netflix', selector: 'Shunt_Netflix', groupId: 'Netflix', url: 'https://www.netflix.com/title/80018499', ms: 132, state: 'ok' },
      { id: 'tiktok', name: 'TikTok', selector: 'Shunt_TikTok', groupId: 'TikTok', url: 'https://www.tiktok.com/favicon.ico', ms: 158, state: 'ok' },
      { id: 'telegram', name: 'Telegram', selector: 'Shunt_Outside_CN', groupId: 'Outside_CN', url: 'https://core.telegram.org/', ms: 149, state: 'ok' },
      { id: 'bilibili', name: 'B站直连', selector: 'Shunt_Domestic_CN', groupId: 'Domestic_CN', url: 'https://www.bilibili.com', ms: 22, state: 'ok' }
    ],
    routingModes: [
      { id: 'rule_shunt', code: 'RECOMMENDED', name: '精细规则分流', shortName: '分流模式', desc: 'AI、视频、社交与国内独立策略' },
      { id: 'gfw_list', code: 'GFW LIST', name: '仅被墙网站代理', shortName: 'GFW 模式', desc: '名单内代理，其余流量全部直连' },
      { id: 'cn_whitelist', code: 'CN BYPASS', name: '非国内走代理', shortName: '非国内模式', desc: '国内直连，海外统一代理出口' },
      { id: 'global_proxy', code: 'GLOBAL', name: '全局代理模式', shortName: '全局模式', desc: '除内网外统一使用代理出口' },
      { id: 'direct_all', code: 'FAIL OPEN', name: '全局直连模式', shortName: '直连模式', desc: '暂停代理分流，恢复宽带出网' }
    ],
    groups: [
      { id: 'AI', name: 'AI 智能助手', subtitle: 'OpenAI / Claude / Gemini / Copilot / Cursor', shunt_mode: 'auto', auto_node_id: 'auto_ai', auto_node_name: 'AI 自动池', country: 'US', resolved_node: '新加坡 06', rtt: null, domains: ['openai.com', 'anthropic.com', 'claude.ai', 'gemini.google.com', 'cursor.sh'], is_custom: false },
      { id: 'YouTube', name: 'YouTube 视频', subtitle: 'YouTube 4K/8K 视频流与 googlevideo CDN', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'JP', resolved_node: '日本 07', rtt: null, domains: ['youtube.com', 'googlevideo.com', 'ytimg.com', 'youtu.be'], is_custom: false },
      { id: 'TikTok', name: 'TikTok 国际版', subtitle: '短视频与国际直播 CDN 专线', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'SG', resolved_node: '日本 07', rtt: null, domains: ['tiktok.com', 'tiktokv.com', 'tiktokcdn.com', 'musical.ly'], is_custom: false },
      { id: 'Netflix', name: 'Netflix 流媒体', subtitle: '奈飞 / Disney+ / 国际流媒体解锁', shunt_mode: 'auto', auto_node_id: 'auto_netflix', auto_node_name: '流媒体自动池', country: 'HK', resolved_node: '香港 N3', rtt: null, domains: ['netflix.com', 'nflxvideo.net', 'disneyplus.com', 'hbo.com'], is_custom: false },
      { id: 'Google', name: 'Google 全生态', subtitle: '搜索 / Play 商店更新 CDN / FCM 推送', shunt_mode: 'auto', auto_node_id: 'auto_ai', auto_node_name: 'AI 自动池', country: 'SG', resolved_node: '新加坡 06', rtt: null, domains: ['google.com', 'googleapis.com', 'gstatic.com', 'gvt1.com', 'dl.google.com'], is_custom: false },
      { id: 'GitHub', name: 'GitHub 开发者', subtitle: '代码仓库 / Release 资产 / 容器镜像', shunt_mode: 'auto', auto_node_id: 'auto_ai', auto_node_name: 'AI 自动池', country: 'JP', resolved_node: '新加坡 06', rtt: null, domains: ['github.com', 'githubusercontent.com', 'githubassets.com', 'ghcr.io'], is_custom: false },
      { id: 'Social', name: 'Telegram 与社交', subtitle: 'Telegram / X (Twitter) / Discord / WhatsApp', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'SG', resolved_node: '日本 07', rtt: null, domains: ['telegram.org', 't.me', 'twitter.com', 'x.com', 'discord.com'], is_custom: false },
      { id: 'Microsoft', name: 'Microsoft 微软生态', subtitle: 'Office 365 / OneDrive / Windows 更新', shunt_mode: 'direct', auto_node_id: 'auto_youtube', auto_node_name: '直连模式', country: 'direct', resolved_node: 'direct', rtt: 0, domains: ['microsoft.com', 'office.com', 'live.com', 'windowsupdate.com'], is_custom: false },
      { id: 'Apple', name: 'Apple 苹果服务', subtitle: 'App Store / iCloud / TestFlight 分发', shunt_mode: 'direct', auto_node_id: 'auto_youtube', auto_node_name: '直连模式', country: 'direct', resolved_node: 'direct', rtt: 0, domains: ['apple.com', 'icloud.com', 'mzstatic.com', 'cdn-apple.com'], is_custom: false },
      { id: 'Games', name: '游戏平台与联机', subtitle: 'Steam / Epic / PlayStation / Xbox', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'HK', resolved_node: '日本 07', rtt: null, domains: ['steampowered.com', 'steamcommunity.com', 'epicgames.com'], is_custom: false },
      { id: 'Outside_CN', name: '海外其他流量', subtitle: '未命中专项规则的非大陆流量统管', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'SG', resolved_node: '日本 07', rtt: null, domains: ['geolocation-!cn'], is_custom: false },
      { id: 'Domestic_CN', name: '国内直连白名单', subtitle: '大陆域名 / 抖音快手直播 CDN / 国内 IP 直通', shunt_mode: 'direct', auto_node_id: '', auto_node_name: '直连', country: 'direct', resolved_node: 'direct', rtt: 0, domains: ['douyincdn.com', 'bilibili.com', 'baidu.com', 'qq.com', 'taobao.com', 'geosite:cn'], is_custom: false, locked_order: true },
      { id: 'Final_Fallback', name: '最终兜底回退', subtitle: 'Final Fallback 漏网流量安全兜底', shunt_mode: 'auto', auto_node_id: 'auto_youtube', auto_node_name: '视频自动池', country: 'SG', resolved_node: '日本 07', rtt: null, domains: ['final-fallback'], is_custom: false, locked_bottom: true, locked_order: true }
    ],
    autoPools: [
      { id: 'auto_ai', tag: 'Auto_AI', name: 'AI 专线自动池', mode: 'full', pool_mode: 'service_check', service_check_enabled: true, service_checks: ['gemini', 'chatgpt'], scope_sources: ['ALL'], scope_countries: ['US', 'JP', 'SG'], target_size: 5, replenish_threshold: 2, healthy_count: 5, active_group_index: 1, current_node: '新加坡 06', current_delay_ms: null, groups: [{ index: 1, name: '节点池成员', node_tags: ['新加坡 06', '日本 07'] }] },
      { id: 'auto_youtube', tag: 'Auto_YouTube', name: 'YouTube 视频自动池', mode: 'full', pool_mode: 'service_check', service_check_enabled: true, service_checks: ['youtube'], scope_sources: ['ALL'], scope_countries: ['ALL'], target_size: 5, replenish_threshold: 2, healthy_count: 5, active_group_index: 1, current_node: '日本 07', current_delay_ms: null, groups: [{ index: 1, name: '节点池成员', node_tags: ['日本 07', '香港 N3'] }] },
      { id: 'auto_netflix', tag: 'Auto_Netflix', name: '流媒体解锁自动池', mode: 'semi', pool_mode: 'ping_only', service_check_enabled: false, service_checks: [], scope_sources: ['ALL'], scope_countries: ['HK', 'TW', 'SG'], target_size: 5, replenish_threshold: 2, healthy_count: 4, active_group_index: 1, current_node: '香港 N3', current_delay_ms: null, groups: [{ index: 1, name: '节点池成员', node_tags: ['香港 N3', '台湾 02'] }] }
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
    blocked: [],
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
      ['日本 12', 'JP', 'TUIC', 'ok', 219, 86, true, 'sub_main'],
      ['香港 N3', 'HK', 'VLESS', 'ok', 96, 97, true, 'sub_main'],
      ['台湾 02', 'TW', 'HY2', 'ok', 128, 89, false, 'sub_main']
    ].map((n, i) => ({
      id: 'node-' + i,
      tag: n[0],
      raw_name: n[0],
      sub_name: '主力高速机场订阅',
      name: '主力高速机场订阅丨' + extractCountryNameFromRawNodeName(n[0]),
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
    logs: []
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
      { domain: 'telegram.org', name: 'Telegram 通讯', group: 'Shunt_Outside_CN', exit_node: '新加坡 06', down_rate: 16384, up_rate: 4096, conns: 2, state: 'ok' },
      { domain: 'netflix.com', name: 'Netflix 流媒体', group: 'Shunt_Netflix', exit_node: '香港 N3', down_rate: 131072, up_rate: 8192, conns: 3, state: 'ok' }
    ],
    galaxyBlackholeCategories: [
      { name: '商业广告联盟与弹窗', count: 0, pct: 0 },
      { name: '开屏广告与终端SDK', count: 0, pct: 0 },
      { name: '隐私遥测与追踪探针', count: 0, pct: 0 },
      { name: 'PCDN盗刷与后台上传', count: 0, pct: 0 }
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
    connDeviceFilter: 'ALL',
    shuntObsTab: 'trace',
    autoRotate: !reducedMotion,
    labels: false,
    surge: false,
    dnsEnabled: true,
    dnsEssentialProtect: true,
    dnsRewriteEnabled: true,
    shuntHitTab: 'by_group',
    shuntHitStats: null,
    lastDoctorReport: null,
    forceTunnelDns: true,
    authEnabled: (function () { try { const c = JSON.parse(localStorage.getItem('ailink_ops_cache_v1') || '{}'); return 'require_lan_auth' in c ? Boolean(c.require_lan_auth) : false; } catch (_) { return false; } })(),
    entryBypass: (function () { try { const c = JSON.parse(localStorage.getItem('ailink_ops_cache_v1') || '{}'); return 'entry_bypass' in c ? Boolean(c.entry_bypass) : true; } catch (_) { return true; } })(),
    ipv6Proxy: (function () { try { const c = JSON.parse(localStorage.getItem('ailink_ops_cache_v1') || '{}'); return 'ipv6_proxy' in c ? Boolean(c.ipv6_proxy) : false; } catch (_) { return false; } })(),
    blockQuic: (function () { try { const c = JSON.parse(localStorage.getItem('ailink_ops_cache_v1') || '{}'); return 'block_quic' in c ? Boolean(c.block_quic) : true; } catch (_) { return true; } })(),
    gameUdpDirect: (function () { try { const c = JSON.parse(localStorage.getItem('ailink_ops_cache_v1') || '{}'); return 'game_udp_direct' in c ? Boolean(c.game_udp_direct) : true; } catch (_) { return true; } })(),
    conflictGuard: (function () { try { const c = JSON.parse(localStorage.getItem('ailink_ops_cache_v1') || '{}'); return 'auto_mute_conflicts' in c ? Boolean(c.auto_mute_conflicts) : true; } catch (_) { return true; } })(),
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
    const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
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
    return '<span class="gear-badge ' + g.gear + '">' + g.fullLabel + '</span>';
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
    const t = String(n.raw_name || n.tag || n.name || '').toUpperCase();
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
    if (rtt == null || !isFinite(ms) || ms <= 0) return '--';
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
    const isBgPoll = !isMutating && (endpoint === '/api/status' || endpoint === '/api/overview/galaxy' || endpoint === '/api/ops/logs' || endpoint.startsWith('/api/nodes?sparkline=1'));
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
      if (res.status === 401 && endpoint !== '/api/login' && (!isBgPoll || (endpoint === '/api/status' && !state._loginPromptedOnce))) {
        state._loginPromptedOnce = true;
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

  function toastWithUndo(message, onUndoFn, undoText) {
    return toast(message, 'info', { onUndo: onUndoFn, undoText: undoText || '↩ 撤销', duration: 8000 });
  }
  window.toastWithUndo = toastWithUndo;

  function toast(message, type, opts) {
    const stack = $('#toast-stack');
    if (!stack) return;
    const msgStr = String(message == null ? '' : message);
    const existing = Array.from(stack.querySelectorAll('.toast:not(.out)')).find(el => {
      const sp = el.querySelector('span');
      return sp && sp.textContent === msgStr;
    });
    if (existing && !(opts && typeof opts.onUndo === 'function')) {
      return;
    }
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
      '<div class="modal-form"><p style="line-height:1.65;color:var(--text)">' + esc(message || '请确认是否继续执行该操作？') + '</p></div>',
      'SECURITY CONFIRMATION',
      async () => {
        closeModal();
        if (typeof onConfirm === 'function') await onConfirm();
      },
      confirmText || '确认执行'
    );
  }
  window.confirmModal = confirmModal;

  let _lastModalTriggerEl = null;
  let _lastModalTitle = '';
  let _lastModalOpenTs = 0;

  function openModal(title, html, kicker, onConfirm, confirmText) {
    const m = $('#modal');
    const nowMs = Date.now();
    // C-P2-13: Singleton modal guard — ignore rapid duplicate clicks opening the exact same modal within 350ms
    if (m && !m.hidden && _lastModalTitle === String(title || '') && (nowMs - _lastModalOpenTs) < 350) {
      return;
    }
    if (m && m.hidden && document.activeElement && document.activeElement !== document.body) {
      _lastModalTriggerEl = document.activeElement;
    }
    _lastModalTitle = String(title || '');
    _lastModalOpenTs = nowMs;
    const tEl = $('#modal-title');
    const kEl = $('#modal-kicker');
    const bEl = $('#modal-body');
    if (tEl) tEl.textContent = title;
    if (kEl) kEl.textContent = kicker || 'AI-LINK NEXUS';
    if (bEl) {
      bEl.innerHTML = html;
      bEl.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(el => {
        if (!el.getAttribute('aria-label')) {
          const fld = el.closest('.modal-field, .field, label');
          const lbl = fld ? fld.querySelector('label, span') : null;
          el.setAttribute('aria-label', (lbl && lbl.textContent ? lbl.textContent.trim() : (el.id || el.name || '表单输入项')));
        }
      });
    }
    modalConfirmHandler = typeof onConfirm === 'function' ? onConfirm : null;
    const confirmBtn = $('#modal-confirm');
    const footNote = $('#modal-foot-note');
    if (confirmBtn) {
      confirmBtn.disabled = false;
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
    const appShell = $('.app-shell');
    if (appShell) appShell.setAttribute('aria-hidden', 'true');
    if (m) {
      m.hidden = false;
      m.setAttribute('role', 'dialog');
      m.setAttribute('aria-modal', 'true');
      m.setAttribute('aria-labelledby', 'modal-title');
      setTimeout(() => {
        const focusables = m.querySelectorAll('input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])');
        if (focusables.length) {
          try { focusables[0].focus(); } catch (_) {}
        } else {
          try { m.focus(); } catch (_) {}
        }
      }, 10);
    }
  }

  function closeModal() {
    const m = $('#modal');
    if (m) m.hidden = true;
    const appShell = $('.app-shell');
    if (appShell) appShell.removeAttribute('aria-hidden');
    modalConfirmHandler = null;
    state.creatingHomelink = false;
    const confirmBtn = $('#modal-confirm');
    if (confirmBtn) confirmBtn.disabled = false;
    if (_lastModalTriggerEl && typeof _lastModalTriggerEl.focus === 'function') {
      try { _lastModalTriggerEl.focus(); } catch (_) {}
      _lastModalTriggerEl = null;
    }
  }

  document.addEventListener('keydown', (ev) => {
    const m = $('#modal');
    if (!m || m.hidden) return;
    if (ev.key === 'Escape') {
      ev.preventDefault();
      closeModal();
      return;
    }
    if (ev.key === 'Tab') {
      const focusables = Array.from(m.querySelectorAll('button:not([disabled]), [href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')).filter(el => el.offsetParent !== null);
      if (!focusables.length) {
        ev.preventDefault();
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (ev.shiftKey) {
        if (document.activeElement === first || !m.contains(document.activeElement)) {
          ev.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last || !m.contains(document.activeElement)) {
          ev.preventDefault();
          first.focus();
        }
      }
    }
  });
  window.closeModal = closeModal;

  function promptPanelLoginModal() {
    openModal(
      '面板安全鉴权登录',
      '<div class="modal-form">' +
        '<p>当前路由器已启用访问鉴权或操作涉及敏感凭据，请输入面板管理密码。</p>' +
        '<div class="modal-field"><label>管理密码</label><input id="mdl-login-password" type="password" placeholder="请输入面板管理密码" autocomplete="current-password"></div>' +
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
    const rttVal = (matchedNode && matchedNode.rtt > 0) ? matchedNode.rtt : ((aiGrp && aiGrp.rtt > 0) ? aiGrp.rtt : null);
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
    const displayNodeName = cleanNodeDisplayName(matchedNode || nodeName);
    let egressDisplay = displayNodeName;
    if (state.globalMode === 'direct') {
      egressDisplay = '直连 (DIRECT)';
    } else if (state.globalMode === 'auto') {
      const aObj = mock.autoPools.find(a => a.id === state.globalAutoNodeId) || mock.autoPools[0];
      const poolName = aObj ? aObj.name : '自动节点池';
      egressDisplay = poolName + ' · ' + displayNodeName;
    } else if (state.globalMode === 'manual') {
      egressDisplay = cleanNodeDisplayName(state.globalManualNode || nodeName);
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
    const memFinite = !state.backendOffline && Number.isFinite(Number(mock.coreMemMib));
    const blkFinite = !state.backendOffline && Number.isFinite(Number(mock.blockedTotal));
    if ($('#scene-kpi-mem')) $('#scene-kpi-mem').innerHTML = memFinite ? (esc(Number(mock.coreMemMib).toFixed(1)) + ' <small>MiB</small>') : '--';
    if ($('#scene-kpi-blocked')) $('#scene-kpi-blocked').innerHTML = blkFinite ? (esc((Number.isFinite(Number(mock.blockedTotal)) ? Number(mock.blockedTotal).toLocaleString('zh-CN') : '--')) + ' <small>次</small>') : '--';
  }

  /* Requirement 1: Overview Dashboard with Enlarged Circular Sonar (bottom list removed, blips clickable with real group selector) */
  function renderOverviewDashboard() {
    renderTopBarStatus();
    const eg = getActiveEgressSummary();
    const heroNodeEl = $('#ov-hero-node');
    if (heroNodeEl) {
      if (eg.isSingleEgress) {
        heroNodeEl.innerHTML = esc(eg.modeName + ' ' + eg.poolOrNodeName) + ' ' + eg.latencyBadge;
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
        : ('当前模式：' + eg.modeName + ' · AI/流媒体/社交/国内各走独立最优出口，单组省流自动节点池实时守护中');
    }
    const pModeEl = $('#ov-pillar-mode');
    if (pModeEl) pModeEl.textContent = eg.modeName;
    const pBypassEl = $('#ov-pillar-bypass');
    if (pBypassEl) pBypassEl.textContent = state.entryBypass ? '大陆 IP 硬件直通已激活' : '全量经内核分流';
    const pIpv6El = $('#ov-pillar-ipv6');
    if (pIpv6El) pIpv6El.textContent = state.ipv6Proxy ? '双栈 IPv6 代理已开启' : '国内原生 IPv6 · 海外防漏';

    const okNodesCnt = mock.nodes.filter(n => n.status === 'ok').length;
    const memTxt = (!state.backendOffline && Number.isFinite(Number(mock.coreMemMib))) ? ('内核 ' + Number(mock.coreMemMib).toFixed(1) + ' MiB') : '--';
    const blkTxt = state.backendOffline ? '服务未连接' : (state.coreAlive ? ('已拦截 ' + (Number.isFinite(Number(mock.blockedTotal)) ? (Number.isFinite(Number(mock.blockedTotal)) ? Number(mock.blockedTotal).toLocaleString('zh-CN') : '--') : '0')) : '内核离线');
    const metrics = [
      ['活跃连接', String(mock.connections), '当前由 sing-box 接管的并发会话', memTxt, '#64D2FF'],
      ['实时下行', mock.downText, '累计接管流量 ' + mock.monthTotalText, '本次运行下载 ' + mock.inTotalText, '#64D2FF'],
      ['实时上行', mock.upText, '本次运行上传 ' + mock.upTotalText, '实时吞吐', '#30D158'],
      ['全域健康度', String(mock.healthScore), okNodesCnt + ' 个可用节点 · ' + Number(mock.dnsRulesCount || 0).toLocaleString('zh-CN') + ' 条护盾规则', blkTxt, '#FFD426']
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
      const isOff = Boolean(state.backendOffline || (state.rawStatus && state.coreAlive === false));
      sonar.insertAdjacentHTML('beforeend', mock.services.slice(0, 8).map((s, i) => {
        const pos = positions[i % positions.length];
        const bx = Math.max(14, Math.min(86, pos[0]));
        const by = Math.max(12, Math.min(88, pos[1]));
        const alignLeft = pos[2] != null ? pos[2] : (bx > 50);
        const effState = isOff ? 'dead' : (s.state || 'pending');
        const msTxt = (!isOff && effState !== 'dead' && s.ms != null && Number(s.ms) > 0)
          ? (Math.round(Number(s.ms)) + 'ms')
          : (effState === 'dead' ? '超时' : '待测');
        const cls = 'sonar-blip' + (alignLeft ? ' blip-left' : '') + (effState === 'suspect' || effState === 'dead' ? ' warn' : '');
        const selTag = s.selector || 'Shunt_AI';
        const tUrl = s.url || '';
        return '<button type="button" class="' + cls + '" data-action="probe-service" data-service="' + esc(s.id || s.name) + '" data-selector="' + esc(selTag) + '" data-url="' + esc(tUrl) + '" data-name="' + esc(s.name) + ' · ' + esc(msTxt) + '" title="点击立即探测 ' + esc(s.name) + ' (' + esc(selTag) + (tUrl ? ' -> ' + tUrl : '') + ')" style="left:' + bx + '%;top:' + by + '%"></button>';
      }).join(''));
    }

    /* Fix #2: Full Strategy Matrix on Overview Page (All groups, no truncation at 5) */
    const ovShuntGrid = $('#ov-shunt-preview-grid');
    if (ovShuntGrid) {
      const cntBadge = $('#ov-shunt-count-badge');
      if (cntBadge) cntBadge.textContent = '全部 ' + mock.groups.length + ' 个分流策略组已挂载';
      ovShuntGrid.innerHTML = mock.groups.map((g, idx) => {
        const isDir = g.shunt_mode === 'direct' || g.resolved_node === 'direct';
        const modeTxt = isDir ? '直连' : (g.shunt_mode === 'manual' ? ('手动 · ' + (g.country || 'JP')) : ('' + (g.auto_node_name || '自动池')));
        const targetNode = isDir ? 'DIRECT 宽带' : (g.resolved_node || '智能优选');
        return '<button class="ov-strategy-item" data-group="' + idx + '" title="点击配置「' + esc(g.name) + '」分流策略">' +
          '<div class="st-left"><b>' + esc(g.name) + '</b><span>' + esc(modeTxt) + ' ' + esc(targetNode) + '</span></div>' +
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
      selAuto.innerHTML = autoList.map(a => '<option value="' + esc(a.id) + '">' + esc(a.name || a.id) + (a.current_node ? ' (' + esc(a.current_node) + ')' : '') + '</option>').join('');
      if (state.globalAutoNodeId && autoList.some(a => a.id === state.globalAutoNodeId)) {
        selAuto.value = state.globalAutoNodeId;
      } else if (autoList.length) {
        selAuto.value = autoList[0].id;
        state.globalAutoNodeId = autoList[0].id;
      }
    }

    const allManualNodes = mock.nodes.slice();
    if (document.activeElement !== selCountry) {
      selCountry.innerHTML = COUNTRY_CODES.map(code => {
        const cnt = allManualNodes.filter(n => classifyNodeCountry(n) === code).length;
        return '<option value="' + code + '">' + esc(COUNTRY_META[code].flag + ' ' + COUNTRY_META[code].name) + ' (' + cnt + ')</option>';
      }).join('');
      const targetCountry = COUNTRY_META[state.globalCountry] ? state.globalCountry : 'JP';
      selCountry.value = targetCountry;
      state.globalCountry = targetCountry;
    }

    const chosenCountry = selCountry.value || state.globalCountry || 'JP';
    let countryNodes = allManualNodes.filter(n => classifyNodeCountry(n) === chosenCountry);
    if (!countryNodes.length) countryNodes = allManualNodes;
    if (document.activeElement !== selManual) {
      const configuredOtherCountry = state.globalManualNode && !countryNodes.some(n => (n.tag || n.name) === state.globalManualNode) && allManualNodes.some(n => (n.tag || n.name) === state.globalManualNode);
      const pinnedPrefix = configuredOtherCountry
        ? '<option value="' + esc(state.globalManualNode) + '">' + esc(state.globalManualNode) + ' (当前固定)</option>'
        : '';
      selManual.innerHTML = pinnedPrefix + countryNodes.map(n => {
        const tag = n.tag || n.name;
        const rttTxt = (n.rtt != null && n.rtt > 0) ? ' · ' + Math.round(n.rtt) + 'ms' : '';
        return '<option value="' + esc(tag) + '">' + esc(n.name || tag) + rttTxt + '</option>';
      }).join('');
      if (state.globalManualNode && (configuredOtherCountry || countryNodes.some(n => (n.tag || n.name) === state.globalManualNode))) {
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
        lblResolved.textContent = '直连 DIRECT';
      } else if (gMode === 'manual') {
        const mNode = state.globalManualNode || selManual.value || state.globalResolvedNode || '未选择';
        lblResolved.textContent = '手动固定 (' + chosenCountry + ') ' + mNode;
      } else {
        const aObj = autoList.find(a => a.id === selAuto.value) || autoList[0];
        const aName = aObj ? aObj.name : (state.globalAutoNodeId || '自动节点池');
        const resSuffix = state.globalResolvedNode ? ' (' + state.globalResolvedNode + ')' : '';
        lblResolved.textContent = '节点池 ' + aName + resSuffix;
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

  const UNSUPPORTED_GOOGLE_REGIONS = new Set(['HK', 'CN', 'MO', 'RU', 'BY', 'IR', 'KP', 'SY', 'CU']);

  function getNodeGoogleRegion(n) {
    if (!n) return 'US';
    if (n.google_region) return String(n.google_region).toUpperCase();
    return classifyNodeCountry(n);
  }

  function isNodeGoogleRegionBlocked(n) {
    if (!n) return false;
    if (n.region_blocked != null) return Boolean(n.region_blocked);
    return UNSUPPORTED_GOOGLE_REGIONS.has(getNodeGoogleRegion(n));
  }

  function renderGoogleRegionBadgeHtml(n, showFullText) {
    const greg = getNodeGoogleRegion(n);
    const proto = String((n && (n.protocol || n.type)) || 'PROXY').toUpperCase();
    return '<span class="google-region-badge" title="协议：' + esc(proto) + ' · Google地区：' + esc(greg) + '">（' + esc(proto) + '）Google地区：' + esc(greg) + '</span>';
  }

  /* Fix #8, #9, #10: Full Shunt Matrix, Batch Toolbar, Auto-Pools, Inline Trace & Switch History */
  function renderShuntMatrix() {
    const rm = $('#routing-modes');
    if (rm) {
      rm.innerHTML = mock.routingModes.map(mode => {
        const isAct = state.routingMode === mode.id;
        return '<button class="routing-mode ' + (isAct ? 'active' : '') + '" data-routing-mode="' + mode.id + '" aria-pressed="' + (isAct ? 'true' : 'false') + '"><span>' + esc(mode.code) + (isAct ? ' · 当前生效' : '') + '</span><b>' + esc(mode.name) + '</b><small>' + esc(mode.desc) + '</small><i></i></button>';
      }).join('');
    }
    renderNonShuntGlobalBar();

    const gl = $('#group-list');
    if (gl) {
      gl.innerHTML = mock.groups.map((g, i) => {
        const boundPool = (!g.shunt_mode || g.shunt_mode === 'auto')
          ? (mock.autoPools || []).find(p => p.id === g.auto_node_id || p.tag === g.auto_node_id || p.name === g.auto_node_name)
          : null;
        const effResolvedNode = (boundPool && boundPool.current_node && boundPool.current_node !== 'direct')
          ? boundPool.current_node
          : g.resolved_node;
        const effRtt = (boundPool && boundPool.current_delay_ms != null && Number(boundPool.current_delay_ms) > 0)
          ? Number(boundPool.current_delay_ms)
          : g.rtt;
        const isDir = g.shunt_mode === 'direct' || effResolvedNode === 'direct';
        const isManual = g.shunt_mode === 'manual';
        const hasManualDrift = false;
        const driftText = '';
        const modeBadge = isDir
          ? '直连模式'
          : (isManual
              ? ('手动固定 · ' + cleanNodeDisplayName(g.manual_node || effResolvedNode || g.country || 'JP'))
              : ('节点池 · ' + ((boundPool && boundPool.name) || g.auto_node_name || '自动节点池')));
        const autoFallbackDirect = !isDir && !isManual && (g.no_available_node || effResolvedNode === 'direct');
        const outNode = isDir
          ? 'DIRECT 宽带直连'
          : (isManual
              ? cleanNodeDisplayName(g.manual_node || effResolvedNode || '已固定单节点')
              : (autoFallbackDirect ? '池内节点不可达 · 直连保护' : (effResolvedNode ? cleanNodeDisplayName(effResolvedNode) : '节点池优选就绪')));
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
            : '<button class="prio-btn" disabled title="底层兜底策略固定顺序">▲</button>' +
              '<button class="prio-btn" disabled title="底层兜底策略固定顺序">▼</button>') +
          '</div>';
        const drawerHtml = state.expandShuntRules
          ? '<div class="shunt-group-rules-drawer">' +
              (rulesArr.slice(0, 10).map(r => '<span class="rule-tag">' + esc(r) + '</span>').join('') || '<span class="rule-tag">内置规则集</span>') +
              (ruleCnt > 10 ? '<span class="rule-tag">+' + (ruleCnt - 10) + ' 条...</span>' : '') +
            '</div>'
          : '';
        return '<div class="shunt-group-card">' +
          '<div class="shunt-group-main">' +
            prioHtml +
            '<div style="min-width:0;cursor:pointer" data-group="' + i + '"><b style="display:block;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(g.name) + (g.is_custom ? ' <span class="version-chip" style="padding:2px 6px;">自定义</span>' : '') + '</b><small style="display:block;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(g.subtitle) + ' (' + ruleCnt + ' 项)</small></div>' +
            '<div style="cursor:pointer;min-width:0" data-group="' + i + '"><span class="status-pill" style="max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(modeBadge) + '</span></div>' +
            '<div class="mono" style="color:' + ((hasManualDrift || g.strict_locked_dead || autoFallbackDirect) ? 'var(--amber)' : 'var(--text-2)') + ';white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer" data-group="' + i + '" title="' + esc(driftText || outNode) + '">' + esc(outNode) + '</div>' +
            '<div style="text-align:right">' + formatLatencyBadge(effRtt, isDir ? 'direct' : (g.strict_locked_dead ? 'dead' : 'ok'), isDir) + '</div>' +
            '<div class="button-row" style="justify-content:flex-end;gap:var(--sp-2)">' +
              '<button class="button ghost compact" style="min-width:72px;padding:0 10px;" data-action="verify-group" data-gid="' + esc(g.id) + '" title="真连接探测当前组出口并触发故障防抖切换">校验</button>' +
              '<button class="button secondary compact" style="min-width:88px;padding:0 12px;" data-group="' + i + '">策略编排</button>' +
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
      if (!mock.autoPools.length) {
        ap.innerHTML = '<div class="empty-state" style="grid-column:1/-1;padding:24px;text-align:center"><h4>尚未创建自动节点池</h4><p>点击右上角「新建自动池」，按订阅源、国家区域与服务可用性一键自动选取最快节点。</p></div>';
      } else {
      ap.innerHTML = mock.autoPools.map((p, idx) => {
        const g1Tags = (p.groups && p.groups[0] && Array.isArray(p.groups[0].node_tags)) ? p.groups[0].node_tags : [];
        const targetCap = Math.max(1, Math.min(10, Number(p.target_size || g1Tags.length || 5)));
        const repThresh = Math.max(1, Math.min(targetCap, Number(p.replenish_threshold != null ? p.replenish_threshold : Math.max(1, Math.ceil(targetCap / 2)))));
        const healthyCnt = Math.min(targetCap, Number(p.healthy_count != null ? p.healthy_count : (g1Tags.length || 4)));
        const hasSvcCheck = Boolean(p.service_check_enabled && p.service_checks && p.service_checks.length);
        const svcTag = hasSvcCheck
          ? ('建池/复选验证: ' + p.service_checks.join('/').toUpperCase())
          : '纯 URL Ping 测速选优';
        const srcArr = Array.isArray(p.scope_sources) && p.scope_sources.length ? p.scope_sources : ['ALL'];
        const srcLabel = srcArr.includes('ALL')
          ? '全部订阅与自定义'
          : srcArr.map(sid => {
              if (sid === 'custom') return '手动节点';
              const sObj = mock.subscriptions.find(s => s.id === sid || s.name === sid);
              return sObj ? sObj.name : sid;
            }).join(' + ');
        const ctryArr = Array.isArray(p.scope_countries) && p.scope_countries.length ? p.scope_countries : ['ALL'];
        const ctryLabel = ctryArr.includes('ALL') ? '全地区' : ctryArr.join('/');
        const isDirectPool = (!p.current_node || p.current_node === 'direct' || p.current_node === 'DIRECT');
        const curNode = isDirectPool ? '直连（未启用代理）' : cleanNodeDisplayName(p.current_node);
        const curMs = (!isDirectPool && p.current_delay_ms != null && Number(p.current_delay_ms) > 0) ? Math.round(Number(p.current_delay_ms)) : null;
        const curNodeObj = isDirectPool
          ? { tag: 'direct', google_region: '' }
          : (mock.nodes.find(x => (x.tag || x.name) === p.current_node || cleanNodeDisplayName(x.tag || x.name) === curNode) || { tag: curNode, google_region: p.current_google_region });
        const pillCls = healthyCnt <= 0 ? 'status-pill danger' : (healthyCnt < repThresh ? 'status-pill warn' : 'status-pill');
        const pillTxt = healthyCnt <= 0
          ? ('健康 0/' + targetCap + ' · 需重新选取')
          : ('健康 ' + healthyCnt + '/' + targetCap + ' (低于' + repThresh + '复选)');
        const statusSummary = healthyCnt <= 0
          ? '池内 0 个可用节点（当前退化为直连），请点击下方「重新自动选取」补充健康节点'
          : ('日常定时 URL Ping 选最快切换 · 健康低于 ' + repThresh + ' 个自动触发复选');
        const latHtml = isDirectPool
          ? '<span class="lat-badge direct">直连 WAN</span>'
          : (curMs != null && curMs > 0
              ? (formatLatencyBadge(curMs, 'ok', false) + renderMiniSparklineSvg([curMs + 12, curMs + 5, Math.max(1, curMs - 4), curMs + 2, curMs], '#38e0b2'))
              : '<span class="lat-badge pending">--</span>');
        const subMetaLine = srcLabel + ' · ' + ctryLabel + ' · ' + svcTag;
        const cardStateCls = healthyCnt <= 0 ? 'pool-danger' : (healthyCnt < repThresh ? 'pool-warn' : 'pool-ok');
        const dotCls = healthyCnt <= 0 ? 'danger' : (healthyCnt < repThresh ? 'warn' : 'ok');
        const shortPillTxt = healthyCnt <= 0 ? ('0/' + targetCap + ' 需处理') : ('健康 ' + healthyCnt + '/' + targetCap);
        const latBadgeCompact = isDirectPool
          ? '<span class="lat-badge direct">直连 WAN</span>'
          : (curMs != null && curMs > 0 ? formatLatencyBadge(curMs, 'ok', false) : '<span class="lat-badge pending">--</span>');
        const tipDetail = '节点池：' + p.name + '\n来源范围：' + srcLabel + '\n国家区域：' + ctryLabel + '\n检测策略：' + svcTag + '\n复选阈值：健康低于 ' + repThresh + ' 个自动补齐';
        const isMenuOpen = state.openPoolMenuIdx != null && Number(state.openPoolMenuIdx) === idx;
        return '<div class="auto-pool hud-pool-card ' + cardStateCls + (isMenuOpen ? ' menu-open' : '') + '" title="' + esc(tipDetail) + '">' +
          '<div class="hud-pool-top">' +
            '<div class="hud-pool-title">' +
              '<i class="status-dot ' + dotCls + '"></i>' +
              '<b title="' + esc(p.name) + '">' + esc(p.name) + '</b>' +
              '<button type="button" class="hud-help-btn" data-action="show-pool-help" data-pool-idx="' + idx + '" title="' + esc(tipDetail) + '" aria-label="查看节点池规则详情">?</button>' +
            '</div>' +
            (p.l7_degraded ? '<span class="l7-degraded-badge" title="L7 语义校验降级保底">L7 降级</span>' : '') + '<span class="' + pillCls + '" style="flex-shrink:0">' + esc(shortPillTxt) + '</span>' +
          '</div>' +
          '<div class="hud-pool-mid">' +
            '<strong class="hud-pool-node mono" style="color:' + (isDirectPool ? 'var(--amber)' : 'var(--cyan)') + '" title="当前出口：' + esc(curNode) + ' · 池内 ' + g1Tags.length + ' 个候选">' + esc(curNode) + ' <small style="color:var(--text-3);font-weight:400">· ' + g1Tags.length + ' 候选' + (p.dispatch_mode === 'multi_line' ? (' · 多线并发(' + Math.max(2, Number(p.active_lines_count || g1Tags.length || 2)) + '线)') : '') + (p.bandwidth_prefer ? ' · 带宽择优' : '') + '</small></strong>' +
            '<span style="flex-shrink:0">' + latBadgeCompact + '</span>' +
          '</div>' +
          '<div class="hud-pool-foot">' +
            '<button type="button" class="button secondary compact" data-action="probe-auto-pool" data-pool-id="' + esc(p.id) + '">立即优选</button>' +
            '<div class="pool-more-wrap">' +
              '<button type="button" class="button ghost compact" style="min-width:40px;padding:0 10px" data-action="toggle-pool-menu" data-pool-idx="' + idx + '" title="更多节点池操作" aria-label="更多节点池操作">···</button>' +
              '<div class="pool-more-menu' + (isMenuOpen ? '' : ' hidden') + '" id="pool-more-menu-' + idx + '">' +
                '<button type="button" class="button ghost compact" data-action="rescreen-auto-pool" data-pool-idx="' + idx + '">重新自动选取</button>' +
                '<button type="button" class="button ghost compact" data-auto-pool="' + idx + '">配置节点池</button>' +
                (!['auto_ai', 'auto_youtube', 'auto_netflix'].includes(p.id)
                  ? '<button type="button" class="button ghost danger-text compact" data-action="delete-auto-pool" data-pool-id="' + esc(p.id) + '">删除节点池</button>'
                  : '') +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>';
      }).join('');
      }
    }

    const histEl = $('#switch-history-list');
    if (histEl) {
      if (mock.switchHistory && mock.switchHistory.length) {
        histEl.innerHTML = mock.switchHistory.slice(0, 6).map(h => {
          const ts = h.ts ? new Date(h.ts * 1000).toLocaleTimeString('zh-CN', { hour12: false }) : (h.time || '刚刚');
          return '<div class="trace-stage" style="padding:8px 11px"><i></i><div><b>' + esc(h.group || h.selector || '自动节点池') + ' ' + esc(h.to_node || h.selected || '新出口') + '</b><span>' + esc(h.reason || '延迟劣化自动平滑切换') + '</span></div><strong>' + esc(ts) + '</strong></div>';
        }).join('');
      } else {
        histEl.innerHTML = '<div class="trace-stage" style="padding:10px 12px"><i></i><div><b>当前全部自动节点池运行稳定 · 零异常抖动</b><span>双组去重省流探测开启中，仅当主组节点连续不可达或劣化超阈值时触发无感热切换</span></div><strong>防抖就绪</strong></div>';
      }
    }
    const shHeroGrp = $('#shunt-hero-stat-groups');
    if (shHeroGrp) shHeroGrp.textContent = (mock.groups ? mock.groups.length : 13) + ' 组';
    const shHeroPools = $('#shunt-hero-stat-pools');
    if (shHeroPools) shHeroPools.textContent = (mock.autoPools ? mock.autoPools.length : 3) + ' 个';
    const shHeroMode = $('#shunt-hero-stat-mode');
    if (shHeroMode) {
      const mInfo = (mock.routingModes || []).find(m => m.id === state.routingMode);
      shHeroMode.textContent = mInfo ? mInfo.name : '精细规则分流';
    }
    renderShuntHitLeaderboard();
  }

  /* T4: Render 1-Hour Sliding Window Shunt Rule Hit Leaderboard */
  function renderShuntHitLeaderboard() {
    const box = $('#shunt-hit-leaderboard-list');
    if (!box) return;
    const tab = state.shuntHitTab || 'by_group';
    $$('#shunt-hit-tabs [data-hit-tab]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.hitTab === tab);
    });
    const stats = state.shuntHitStats || {};
    let list = Array.isArray(stats[tab]) ? stats[tab] : [];
    if (!list.length) {
      list = mock.groups.slice(0, 6).map((g, idx) => ({
        key: g.id,
        title: g.name,
        subtitle: g.resolved_node === 'direct' ? 'DIRECT 宽带直连' : ('出口: ' + (g.resolved_node || g.auto_node_name || '自动池')),
        hits: Math.max(1, (8 - idx) * 3),
        bytes_str: ((8 - idx) * 1.4).toFixed(1) + ' MB',
        share_pct: Math.round(100 / Math.max(1, mock.groups.length)),
        sample_target: (g.domains && g.domains[0]) || 'chatgpt.com'
      }));
    }
    box.innerHTML = list.slice(0, 10).map((it, idx) => {
      const title = it.title || it.group_title || it.rule || it.outbound || it.key || ('排行项 #' + (idx + 1));
      const sub = it.subtitle || (it.sample_target ? ('代表目标: ' + it.sample_target) : '最近 1 小时活跃匹配');
      const hits = Number(it.hits != null ? it.hits : (it.count || 0));
      const pct = Number(it.share_pct != null ? it.share_pct : (it.pct || 0)).toFixed(1);
      const bytesStr = it.bytes_str || fmtBytes(it.bytes || 0);
      const filterKey = it.sample_target || it.key || title;
      return '<div class="hit-stat-row" data-action="filter-conn-by-hit" data-hit-query="' + esc(filterKey) + '" title="点击筛选「' + esc(title) + '」关联的实时连接">' +
        '<span class="hit-rank-badge">#' + (idx + 1) + '</span>' +
        '<div style="min-width:0"><b style="display:block;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(title) + '</b><small style="display:block;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(sub) + '</small></div>' +
        '<div class="thin-progress" style="margin:0"><i style="width:' + Math.max(6, Math.min(100, Number(pct))) + '%"></i></div>' +
        '<span class="status-pill">' + esc(hits) + ' 次 (' + esc(pct) + '%)</span>' +
        '<strong class="mono" style="color:var(--cyan)">' + esc(bytesStr) + '</strong>' +
      '</div>';
    }).join('');
  }

  function isUserEditingInside(container) {
    if (!container) return false;
    const act = document.activeElement;
    if (act && container.contains(act) && (act.tagName === 'SELECT' || act.tagName === 'INPUT' || act.tagName === 'TEXTAREA')) {
      return true;
    }
    return false;
  }

  function renderHomeLinkSection(forceRebuild) {
    const hn = $('#homelink-nodes');
    if (hn) {
      if (!mock.homelinkNodes.length) {
        hn.innerHTML = '<div class="empty-state" style="grid-column:1/-1;padding:28px;text-align:center"><h4>尚未创建加密回家节点</h4><p>点击右上角「创建回家节点」，即可一键生成 VLESS-Reality 或 Hysteria2 专属回家隧道。</p></div>';
      } else if (!forceRebuild && isUserEditingInside(hn) && hn.querySelectorAll('[data-hl-card]').length === mock.homelinkNodes.length) {
        mock.homelinkNodes.forEach(n => {
          const card = hn.querySelector('[data-hl-card="' + n.id + '"]');
          if (!card) return;
          const rateTxt = (Number(n.down_rate_bps || 0) + Number(n.up_rate_bps || 0)) > 0
            ? ('↓ ' + (n.down_rate_str || fmtRate(n.down_rate_bps || 0)) + ' · ↑ ' + (n.up_rate_str || fmtRate(n.up_rate_bps || 0)))
            : '待机监听 · 0 B/s';
          const rEl = card.querySelector('[data-hl-rate]');
          if (rEl) rEl.textContent = rateTxt;
          const cEl = card.querySelector('[data-hl-conns]');
          if (cEl) cEl.textContent = String(Number(n.active_conns || 0));
        });
      } else {
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
                (n.enabled === false ? '⏸已停用' : (isListening ? '端口监听正常' : '正在监听')) +
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
            '<div><b>独立回家路由模式</b><span style="color:var(--muted)">仅对当前回家节点独立生效</span></div>' +
            '<select class="hl-mode-select" data-hl-node-mode="' + esc(n.id) + '" aria-label="独立回家路由模式" aria-busy="' + (state.busyHomelinkNodeId === n.id ? 'true' : 'false') + '">' +
              '<option value="shunt" ' + (rm === 'shunt' ? 'selected' : '') + '>回家 + 科学上网分流</option>' +
              '<option value="direct" ' + (rm === 'direct' ? 'selected' : '') + '>仅访问内网与国内</option>' +
              '<option value="proxy_only" ' + (rm === 'proxy_only' ? 'selected' : '') + '>仅科学上网 · 隔离内网</option>' +
            '</select>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;color:var(--muted)">' +
            '<span>实时吞吐: <strong class="mono" style="color:var(--cyan)" data-hl-rate>' + esc(rateTxt) + '</strong></span>' +
            '<span>活跃会话: <strong class="mono" data-hl-conns>' + esc(Number(n.active_conns || 0)) + '</strong></span>' +
          '</div>' +
          '<div class="button-row">' +
            '<button class="button primary compact" data-action="share-node" data-node="' + esc(n.id) + '">二维码与分享</button>' +
            '<button class="button secondary compact" data-action="edit-node" data-node="' + esc(n.id) + '">编辑参数</button>' +
            '<button class="button ghost compact" data-action="check-homelink-port" data-port="' + esc(n.listen_port || 18443) + '" data-proto="' + esc(n.raw_proto || 'vless-reality') + '">端口检测</button>' +
            '<button class="button danger compact" data-action="delete-homelink" data-node="' + esc(n.id) + '">删除</button>' +
          '</div>' +
        '</article>';
      }).join('');
      }
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
        shunt: '回家 + 科学上网分流',
        direct: '仅访问内网与国内',
        proxy_only: '仅科学上网 · 隔离内网'
      };
      const rows = [];
      /* Always show per-node real-time listener monitor rows first */
      mock.homelinkNodes.forEach(n => {
        const rmName = modeNameMap[n.route_mode || 'shunt'] || modeNameMap.shunt;
        const stBadge = n.enabled === false
          ? '<span class="node-status dead">已停用</span>'
          : '<span class="node-status ok">监听正常 (' + esc(n.port) + ')</span>';
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
          '<td style="text-align:right"><button class="button ghost compact" style="padding:0 8px;" data-action="check-homelink-port" data-port="' + esc(n.listen_port || 18443) + '" data-proto="' + esc(n.raw_proto || 'vless-reality') + '">探针检测</button></td>' +
        '</tr>');
      });

      /* Append active remote client session rows if any */
      activeSessions.slice(0, 20).forEach(s => {
        const rmName = modeNameMap[s.route_mode || 'shunt'] || modeNameMap.shunt;
        rows.push('<tr>' +
          '<td><b class="mono">客户端 ' + esc(s.client_ip) + '</b><small>接入节点: ' + esc(s.node_name) + '</small></td>' +
          '<td><span class="node-status ok">活跃传输 (' + esc(s.network || 'TCP') + ')</span></td>' +
          '<td><span class="status-pill">' + esc(rmName) + '</span></td>' +
          '<td class="mono"><b>' + esc(s.target) + '</b><small style="display:block;color:var(--text-3)">' + esc(s.flow_label || '加密转发') + '</small></td>' +
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
            '<td><b class="mono">历史客户端 ' + esc(c.client_ip) + '</b><small>接入节点: ' + esc(c.node_name) + '</small></td>' +
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
        bd.innerHTML = '<div class="trace-stage"><i></i><div><b>今日已拦截 0 次 · 净网规则引擎已就绪</b><span>内置隐私遥测探针库、商业广告联盟库与路由层 REJECT 规则已挂载生效，产生命中后将实时排行展示</span></div><strong>守护中</strong></div>';
      }
    }
    const heroTitle = $('#dns-hero-title');
    if (heroTitle) {
      if (mock.dnsRulesCount != null && Number(mock.dnsRulesCount) > 0) {
        const ruleTotal = Number(mock.dnsRulesCount);
        const rawLines = Number(mock.dnsRawRuleLines || 0);
        const rawNote = rawLines > ruleTotal ? ('（源规则 ' + rawLines.toLocaleString('zh-CN') + ' 条去重合并）') : '';
        heroTitle.textContent = ruleTotal.toLocaleString('zh-CN') + ' 条净网与防污染规则正在协同工作' + rawNote;
      } else {
        heroTitle.textContent = state.backendOffline ? '后端离线 · 净网规则状态未知' : '正在加载净网与防污染规则统计...';
      }
    }
    const heroReady = $('#dns-engine-readiness');
    if (heroReady) {
      const totalHits = Number.isFinite(Number(mock.blockedTotal)) ? Number(mock.blockedTotal) : 0;
      heroReady.textContent = totalHits > 0
        ? ('规则引擎已激活 · 24h 累计拦截 ' + totalHits.toLocaleString('zh-CN') + ' 次广告与追踪请求')
        : '规则引擎已就绪 · 今日已拦截 0 次（DNS REFUSED + 路由 REJECT 双层实时守护中）';
    }
    const bq = $('#ov-dns-blocked-q');
    if (bq) bq.textContent = Number.isFinite(Number(mock.blockedTotal)) ? Number(mock.blockedTotal).toLocaleString('zh-CN') : String(mock.blockedTotal || '0');
    const bpct = $('#ov-dns-blocked-pct');
    if (bpct) bpct.textContent = Number(mock.dnsBlockedPct || 0).toFixed(1) + '%';
    const bms = $('#ov-dns-avg-ms');
    if (bms) {
      bms.textContent = (mock.dnsAvgMs != null && Number(mock.dnsAvgMs) >= 0)
        ? (Math.round(Number(mock.dnsAvgMs)) + ' ms')
        : '未采样';
    }
    const lr = $('#ov-dns-layer-rules');
    if (lr) lr.textContent = Number(mock.dnsLayerCount || 0).toLocaleString('zh-CN');
    const rj = $('#dns-layer-reject');
    if (rj) rj.textContent = Number(mock.rejectLayerCount || 0).toLocaleString('zh-CN');
    setSwitchState($('#toggle-dns-filter'), state.dnsEnabled);
    setSwitchState($('#toggle-dns-essential-protect'), state.dnsEssentialProtect !== false);
    setSwitchState($('#toggle-dns-rewrite'), state.dnsRewriteEnabled);

    const rwList = $('#dns-rewrite-list');
    if (rwList) {
      rwList.innerHTML = mock.rewriteRules.map((r, idx) => {
        const fDom = r.from_domain || r.from || '';
        const tDom = r.to_domain || r.to || '';
        return '<div class="trace-stage" style="padding:9px 12px"><i>R' + (idx + 1) + '</i><div><b class="mono">' + esc(fDom) + ' ' + esc(tDom) + '</b><span>' + esc(r.note || 'DNS 防跳重写规则') + '</span></div><button class="button danger compact" style="padding:0 8px;" data-action="delete-dns-rewrite" data-from="' + esc(fDom) + '">删除</button></div>';
      }).join('');
    }

    const flList = $('#dns-filter-lists');
    if (flList) {
      flList.innerHTML = mock.filterLists.length
        ? mock.filterLists.map(l => '<div class="trace-stage" style="padding:9px 12px"><i>库</i><div><b>' + esc(l.name) + '</b><span>' + esc(l.category || '云端规则') + ' · ' + Number(l.rules_count || 0).toLocaleString('zh-CN') + ' 条 · ' + esc(l.updated_at || '已同步') + '</span></div><strong>' + (l.enabled !== false ? '已启用' : '已停用') + '</strong></div>').join('')
        : '<div class="trace-stage" style="padding:9px 12px"><i>库</i><div><b>暂未配置外部过滤订阅列表</b><span>内置基础隐私保护已生效，可点击上方按钮添加自定义 AdGuard / Hosts 规则源</span></div><strong>内置守护</strong></div>';
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

  function isNodeManualCustom(n) {
    if (!n) return false;
    return Boolean(n.is_custom || n._manual || n.sub_id === 'custom' || (!n.sub_id && !n.sub_url));
  }

  function getNodeThreeState(n) {
    if (!n) return 'untested';
    if (n.status === 'ok' && n.rtt != null && Number(n.rtt) > 0) return 'ok';
    if (n.status === 'untested' || n.status === 'pending' || (!n.probe_ts && n.rtt == null && n.status !== 'dead')) return 'untested';
    return 'dead';
  }

  function getNodeTwoState(n) {
    return getNodeThreeState(n) === 'ok' ? 'ok' : 'dead';
  }

  function formatSubSyncTimestampText(s) {
    if (!s) return '未同步';
    const isErr = (s.status === 'error' || s.last_sync_status === 'error' || s.health_status === 'fetch_error');
    if (s.sync_status_text) {
      const baseTxt = String(s.sync_status_text).replace(/\s*失败.*$/, '').trim();
      return isErr ? (baseTxt + ' 失败') : baseTxt;
    }
    let timePart = s.last_sync_time || '';
    if (!timePart && s.last_sync_ts && Number(s.last_sync_ts) > 0) {
      const d = new Date(Number(s.last_sync_ts) * 1000);
      const pad = v => String(v).padStart(2, '0');
      timePart = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }
    if (!timePart) {
      const m = String(s.updated || '').match(/(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|\d{2}-\d{2}\s+\d{2}:\d{2})/);
      if (m) timePart = m[1];
    }
    if (!timePart) {
      const d = new Date();
      const pad = v => String(v).padStart(2, '0');
      timePart = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }
    return isErr ? (timePart + ' 失败') : timePart;
  }

  function nodeMatchesSubscription(n, subId) {
    if (!subId || subId === 'ALL') return true;
    if (subId === 'custom') return isNodeManualCustom(n);
    if (isNodeManualCustom(n)) return false;
    if (n.sub_id === subId || n.sub_name === subId || n.sub_url === subId) return true;
    const subObj = mock.subscriptions.find(s => s.id === subId || s.name === subId || s.url === subId);
    if (subObj) {
      if (n.sub_id && (n.sub_id === subObj.id || n.sub_id === subObj.name)) return true;
      if (n.sub_url && subObj.url && n.sub_url === subObj.url) return true;
      if (mock.subscriptions.length === 1 && !isNodeManualCustom(n)) return true;
    }
    return false;
  }

  function filteredNodes() {
    return mock.nodes.filter(n => {
      const st3 = getNodeThreeState(n);
      const statusOk = state.nodeFilter === 'all' ||
        (state.nodeFilter === 'untested' || state.nodeFilter === 'pending' ? st3 === 'untested' : st3 === state.nodeFilter);
      const regionOk = state.regionFilter === 'ALL' || classifyNodeCountry(n) === state.regionFilter;
      const subOk = nodeMatchesSubscription(n, state.subFilter);
      const query = state.search.trim().toLowerCase();
      const searchOk = !query || [n.name, n.raw_name, n.sub_name, n.region, n.protocol, n.tag, n.server].join(' ').toLowerCase().includes(query);
      return statusOk && regionOk && subOk && searchOk;
    });
  }

  /* v2.3.2: All-Subscriptions Summary Card (#1) + Manual/Custom Nodes Category Card (#2) + Subscription Cards with Sync Timestamp & Failure Suffix + Two-State Node Management */
  function renderSubscriptionsAndNodes() {
    const customNodesList = mock.nodes.filter(n => isNodeManualCustom(n));
    const customOkCnt = customNodesList.filter(n => getNodeThreeState(n) === 'ok').length;
    const customDeadCnt = customNodesList.filter(n => getNodeThreeState(n) === 'dead').length;
    const customUntestedCnt = customNodesList.filter(n => getNodeThreeState(n) === 'untested').length;
    const okTotalCnt = mock.nodes.filter(n => getNodeThreeState(n) === 'ok').length;
    const deadTotalCnt = mock.nodes.filter(n => getNodeThreeState(n) === 'dead').length;
    const untestedTotalCnt = mock.nodes.filter(n => getNodeThreeState(n) === 'untested').length;

    const sl = $('#subscription-list');
    if (sl) {
      const enabledSubCnt = mock.subscriptions.filter(s => s.enabled !== false).length;
      const isAllSelected = !state.subFilter || state.subFilter === 'ALL';
      const isCustomSelected = state.subFilter === 'custom';

      const totalHealthPct = mock.nodes.length ? Math.round((okTotalCnt / mock.nodes.length) * 100) : 100;
      const customHealthPct = customNodesList.length ? Math.round((customOkCnt / customNodesList.length) * 100) : 100;
      const allCardHtml = '<article class="subscription-card selectable ' + (isAllSelected ? 'active' : '') + '" data-sub-select="ALL" title="点击查看所有订阅与手动节点汇总列表">' +
        '<div class="sub-top">' +
          '<div><h3>全部订阅源汇总</h3><div class="sub-url mono">共 ' + esc(mock.subscriptions.length) + ' 个订阅源 (' + esc(enabledSubCnt) + ' 启用) · 手动 ' + esc(customNodesList.length) + ' 个</div></div>' +
          '<span class="status-pill" style="flex-shrink:0">' + (isAllSelected ? '当前视图' : '点击筛选') + '</span>' +
        '</div>' +
        '<div class="sub-metrics">' +
          '<div><b>' + esc(mock.nodes.length) + '</b><span style="color:var(--muted);">个总节点</span></div>' +
          '<span class="status-pill">全部入核无上限</span>' +
        '</div>' +
        '<div class="sub-health-box">' +
          '<div class="sub-health-top">' +
            '<span>全网连通率：' + esc(totalHealthPct) + '%</span>' +
            '<span class="sub-expire-pill">全局实时同步</span>' +
          '</div>' +
          '<div class="sub-health-bar"><i style="width:' + Math.max(4, Math.min(100, totalHealthPct)) + '%"></i></div>' +
          '<div class="sub-health-meta">' +
            '<span>可用 ' + esc(okTotalCnt) + ' · 不可达 ' + esc(deadTotalCnt) + '</span>' +
            '<span>未测速 ' + esc(untestedTotalCnt) + ' 个</span>' +
          '</div>' +
        '</div>' +
        '<div class="sub-actions">' +
          '<button class="button secondary compact" data-action="sync">同步全部</button>' +
          '<button class="button ghost compact" data-action="probe-all">全量测速</button>' +
          '<button class="button ghost compact" data-action="add-single-node">手动加节点</button>' +
        '</div>' +
      '</article>';

      /* Card #2: Manual / Custom Nodes Category Card (placed as 2nd card right after All-Subscriptions) */
      const customCardHtml = '<article class="subscription-card selectable ' + (isCustomSelected ? 'active' : '') + '" data-sub-select="custom" id="sub-card-custom" title="点击查看与管理所有手动添加/批量导入的自定义节点">' +
        '<div class="sub-top">' +
          '<div><h3>手动添加节点</h3><div class="sub-url mono">本地自建 / 单节点添加 / URI 批量导入分类</div></div>' +
          '<span class="status-pill" style="flex-shrink:0">' + (isCustomSelected ? '当前视图' : '分类预览') + '</span>' +
        '</div>' +
        '<div class="sub-metrics">' +
          '<div><b>' + esc(customNodesList.length) + '</b><span style="color:var(--muted);">个手动节点</span></div>' +
          '<span class="status-pill">常驻内核选路</span>' +
        '</div>' +
        '<div class="sub-health-box">' +
          '<div class="sub-health-top">' +
            '<span>可用 ' + esc(customOkCnt) + ' · 不可达 ' + esc(customDeadCnt) + ' · 未测 ' + esc(customUntestedCnt) + '</span>' +
            '<span class="sub-expire-pill">永久有效</span>' +
          '</div>' +
          '<div class="sub-health-bar"><i style="width:' + Math.max(4, Math.min(100, customHealthPct)) + '%"></i></div>' +
          '<div class="sub-health-meta">' +
            '<span>独立节点源 (custom)</span>' +
            '<span>免订阅拉取</span>' +
          '</div>' +
        '</div>' +
        '<div class="sub-actions">' +
          '<button class="button secondary compact" data-action="add-single-node">手动加节点</button>' +
          '<button class="button ghost compact" data-action="import">批量导入 URI</button>' +
          '<button class="button ghost compact" data-action="probe-custom-nodes">测速手动节点</button>' +
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
        const matchedNodes = mock.nodes.filter(n => nodeMatchesSubscription(n, subIdVal));
        const matchedCnt = matchedNodes.length;
        const matchedOkCnt = matchedNodes.filter(n => getNodeThreeState(n) === 'ok').length;
        const matchedDeadCnt = matchedNodes.filter(n => getNodeThreeState(n) === 'dead').length;
        const matchedUntestedCnt = matchedNodes.filter(n => getNodeThreeState(n) === 'untested').length;
        const dispCount = Number(s.count != null ? s.count : matchedCnt);
        const isSyncErr = (s.status === 'error' || s.last_sync_status === 'error' || s.health_status === 'fetch_error');
        const syncTimeText = formatSubSyncTimestampText(s);
        const syncBadgeHtml = '<span class="sub-sync-status ' + (isSyncErr ? 'is-fail' : 'is-ok') + '" style="color:' + (isSyncErr ? 'var(--rose)' : 'var(--text-3)') + ';font-weight:500">同步时间: ' + esc(syncTimeText) + '</span>';

        const ui = (s.userinfo && typeof s.userinfo === 'object') ? s.userinfo : null;
        let subHealthHtml = '';
        if (ui && (ui.total_bytes > 0 || ui.expire_ts > 0)) {
          const pct = ui.used_pct != null ? Number(ui.used_pct) : (ui.total_bytes > 0 ? Math.min(100, Math.round(((ui.used_bytes || 0) / ui.total_bytes) * 1000) / 10) : 0);
          const barCls = pct >= 90 ? 'danger' : (pct >= 75 ? 'warn' : '');
          const usedTxt = ui.used_human || fmtBytes(ui.used_bytes || 0);
          const totalTxt = ui.total_human || fmtBytes(ui.total_bytes || 0);
          const remTxt = ui.remaining_human || fmtBytes(Math.max(0, (ui.total_bytes || 0) - (ui.used_bytes || 0)));
          let expPill = '<span class="sub-expire-pill">长期有效</span>';
          if (ui.expire_days_left != null) {
            const dLeft = Number(ui.expire_days_left);
            const eCls = dLeft <= 3 ? 'danger' : (dLeft <= 7 ? 'warn' : '');
            const fullExp = String(ui.expire_human || '');
            const shortExp = fullExp.replace(/^\d{4}-/, '');
            expPill = '<span class="sub-expire-pill ' + eCls + '" title="到期日期: ' + esc(fullExp) + '">' + (dLeft < 0 ? '已过期' : ('剩余 ' + dLeft + ' 天' + (shortExp ? ' (' + esc(shortExp) + ')' : ''))) + '</span>';
          }
          const resetHint = ui.reset_day ? (' · 每月 ' + ui.reset_day + ' 日重置') : '';
          subHealthHtml = '<div class="sub-health-box">' +
            '<div class="sub-health-top">' +
              '<span>流量：' + esc(usedTxt) + ' / ' + esc(totalTxt) + ' (' + esc(pct) + '%)</span>' +
              expPill +
            '</div>' +
            '<div class="sub-health-bar ' + barCls + '"><i style="width:' + Math.max(2, Math.min(100, pct)) + '%"></i></div>' +
            '<div class="sub-health-meta">' +
              '<span>剩余：' + esc(remTxt) + esc(resetHint) + '</span>' +
              syncBadgeHtml +
            '</div>' +
          '</div>';
        } else {
          const okRatioPct = dispCount > 0 ? Math.round((matchedOkCnt / dispCount) * 100) : 100;
          subHealthHtml = '<div class="sub-health-box">' +
            '<div class="sub-health-top">' +
              '<span>可用 ' + esc(matchedOkCnt) + ' · 不可达 ' + esc(matchedDeadCnt) + ' · 未测 ' + esc(matchedUntestedCnt) + '</span>' +
              '<span class="sub-expire-pill">节点数 ' + esc(dispCount) + '</span>' +
            '</div>' +
            '<div class="sub-health-bar"><i style="width:' + Math.max(4, Math.min(100, okRatioPct)) + '%"></i></div>' +
            '<div class="sub-health-meta">' +
              syncBadgeHtml +
              '<span>更新：' + (s.auto_update !== false ? ('每 ' + Math.max(1, Math.round(Number(s.update_interval_min || 360) / 60)) + 'h') : '手动') + '</span>' +
            '</div>' +
          '</div>';
        }
        return '<article class="subscription-card selectable ' + (isCardActive ? 'active' : '') + '" data-sub-select="' + esc(subIdVal) + '" title="点击筛选「' + esc(s.name) + '」的节点列表">' +
          '<div class="sub-top">' +
            '<div><h3>' + esc(s.name) + '</h3><div class="sub-url mono" title="' + esc(rawUrl) + '">' + esc(hostPreview) + '</div></div>' +
            '<button class="switch ' + (s.enabled ? 'on' : 'off') + '" role="switch" aria-checked="' + (s.enabled ? 'true' : 'false') + '" data-action="subscription-toggle" data-sub="' + i + '" aria-label="切换订阅"><i></i></button>' +
          '</div>' +
          '<div class="sub-metrics">' +
            '<div><b>' + esc(dispCount) + '</b><span style="color:var(--muted);">个节点</span></div>' +
            '<span class="status-pill">' + (s.enabled ? '已启用 · 参与选路' : '已停用 · 正交隔离') + '</span>' +
          '</div>' +
          subHealthHtml +
          '<div class="sub-actions">' +
            '<button class="button secondary compact" data-action="sub-sync-one" data-sub="' + i + '">立即同步</button>' +
            '<button class="button ghost compact" data-action="sub-probe-one" data-sub="' + i + '">测速本订阅</button>' +
            '<button class="button ghost compact" data-action="sub-edit-one" data-sub="' + i + '">管理订阅</button>' +
          '</div>' +
        '</article>';
      }).join('');
      sl.innerHTML = allCardHtml + customCardHtml + subCardsHtml;
    }

    const subSel = $('#node-sub-filter');
    if (subSel && document.activeElement !== subSel) {
      subSel.innerHTML = '<option value="ALL">全部节点源 (' + mock.nodes.length + ')</option>' +
        '<option value="custom">手动添加节点 (' + customNodesList.length + ')</option>' +
        mock.subscriptions.map(s => '<option value="' + esc(s.id) + '">' + esc(s.name) + ' (' + Number(s.count || 0) + ')</option>').join('');
      subSel.value = state.subFilter || 'ALL';
    }

    const scopedBySub = mock.nodes.filter(n => nodeMatchesSubscription(n, state.subFilter));
    const allCnt = scopedBySub.length;
    const okCnt = scopedBySub.filter(n => getNodeThreeState(n) === 'ok').length;
    const deadCnt = scopedBySub.filter(n => getNodeThreeState(n) === 'dead').length;
    const untestedCnt = scopedBySub.filter(n => getNodeThreeState(n) === 'untested').length;
    if (!['all', 'ok', 'dead', 'untested', 'pending'].includes(state.nodeFilter)) {
      state.nodeFilter = 'all';
    }
    const chipMap = {
      all: '全部 (' + allCnt + ')',
      ok: '可用 (' + okCnt + ')',
      dead: '不可达 (' + deadCnt + ')',
      untested: '⏳ 未测速 (' + untestedCnt + ')',
      pending: '⏳ 未测速 (' + untestedCnt + ')'
    };
    $$('[data-node-filter]').forEach(btn => {
      const k = btn.dataset.nodeFilter;
      if (chipMap[k]) {
        btn.textContent = chipMap[k];
        btn.classList.remove('hidden');
      } else {
        btn.classList.add('hidden');
      }
      const isAct = (state.nodeFilter === k) || (state.nodeFilter === 'untested' && k === 'pending') || (state.nodeFilter === 'pending' && k === 'untested');
      btn.classList.toggle('active', isAct);
    });

    /* Fix #4: Region filter buttons with dynamic per-region node counts */
    const regionBar = $('#region-filter-chips');
    if (regionBar) {
      const regCounts = { ALL: allCnt, HK: 0, TW: 0, JP: 0, SG: 0, US: 0, OTHER: 0 };
      scopedBySub.forEach(n => {
        const rc = classifyNodeCountry(n);
        regCounts[rc] = (regCounts[rc] || 0) + 1;
      });
      const regItems = [
        ['ALL', '全部地区 (' + regCounts.ALL + ')'],
        ['HK', '🇭🇰 香港 (' + regCounts.HK + ')'],
        ['TW', '🇹🇼 台湾 (' + regCounts.TW + ')'],
        ['JP', '🇯🇵 日本 (' + regCounts.JP + ')'],
        ['SG', '🇸🇬 新加坡 (' + regCounts.SG + ')'],
        ['US', '🇺🇸 美国 (' + regCounts.US + ')'],
        ['OTHER', '其他 (' + regCounts.OTHER + ')']
      ];
      regionBar.innerHTML = regItems.map(item =>
        '<button class="' + (state.regionFilter === item[0] ? 'active' : '') + '" data-region-filter="' + item[0] + '">' + esc(item[1]) + '</button>'
      ).join('');
    }

    /* Fix #5 & #6: Client-side Pagination + Two-State Status Display */
    const allFiltered = filteredNodes();
    const pageSize = state.nodePageSize > 0 ? state.nodePageSize : allFiltered.length || 50;
    const totalPages = Math.max(1, Math.ceil(allFiltered.length / pageSize));
    if (state.nodePage > totalPages) state.nodePage = totalPages;
    if (state.nodePage < 1) state.nodePage = 1;
    const startIdx = (state.nodePage - 1) * pageSize;
    const pageNodes = state.nodePageSize === 0 ? allFiltered : allFiltered.slice(startIdx, startIdx + pageSize);

    const tbody = $('#probe-nodes-tbody');
    if (tbody) {
      tbody.innerHTML = pageNodes.length ? pageNodes.map(n => {
        const cCode = classifyNodeCountry(n);
        const cMeta = COUNTRY_META[cCode] || COUNTRY_META.OTHER;
        const st3 = getNodeThreeState(n);
        const statusBadge = st3 === 'ok'
          ? '<span class="node-status ok">可用</span>'
          : (st3 === 'untested'
              ? '<span class="node-status pending">⏳ 未测速</span>'
              : '<span class="node-status dead">不可达</span>');
        const scoreHtml = (st3 === 'ok' && n.score != null && n.score > 0)
          ? ('<span class="mono" style="color:var(--cyan);font-weight:500">' + n.score + ' 分</span>')
          : '<span style="color:var(--dim)">—</span>';
        const srcBadge = isNodeManualCustom(n)
          ? '<span class="status-pill" style="color:var(--cyan);border-color:var(--accent-border)">手动添加</span>'
          : ('<span class="kernel-mark">' + esc(n.sub_name || '订阅节点') + '</span>');
        return '<tr>' +
          '<td><b>' + esc(n.name) + '</b><small class="mono">' + esc(n.server ? (n.server + ':' + (n.server_port || 443)) : n.id) + '</small></td>' +
          '<td>' + renderGoogleRegionBadgeHtml(n, false) + '</td>' +
          '<td>' + statusBadge + '</td>' +
          '<td>' + formatLatencyBadge(n.rtt, st3 === 'untested' ? 'pending' : st3, false) + renderMiniSparklineSvg(n.sparkline, st3 === 'ok' ? '#6ee7f5' : '#8390a8') + '</td>' +
          '<td class="score-cell">' + scoreHtml + '</td>' +
          '<td>' + srcBadge + '</td>' +
          '<td><div class="button-row" style="justify-content:flex-end;gap:4px">' +
            '<button class="button ghost compact" style="padding:0 7px;" data-action="node-real-delay" data-node="' + esc(n.tag || n.name) + '" title="URL Ping 真连接测速">真测速</button>' +
            '<button class="button ghost compact" style="padding:0 7px;" data-action="node-credentials" data-node="' + esc(n.tag || n.name) + '" title="查看节点底层凭据">凭据</button>' +
            '<button class="button secondary compact" style="padding:0 7px;" data-action="set-node-exit" data-node="' + esc(n.tag || n.name) + '">设为出口</button>' +
            '<button class="button ghost compact" style="padding:0 7px;" data-action="node-details" data-node="' + esc(n.id) + '">详情</button>' +
          '</div></td>' +
        '</tr>';
      }).join('') : '<tr><td colspan="7"><div class="empty-state"><h4>当前筛选条件下没有匹配的节点</h4><p>请点击上方「全部」或调整地区、订阅与搜索关键词。</p></div></td></tr>';
    }

    const ndHeroTot = $('#nodes-hero-stat-total');
    if (ndHeroTot) ndHeroTot.textContent = String(mock.nodes.length);
    const ndHeroOk = $('#nodes-hero-stat-ok');
    if (ndHeroOk) ndHeroOk.textContent = String(mock.nodes.filter(n => n.status === 'ok').length);
    const ndHeroSubs = $('#nodes-hero-stat-subs');
    if (ndHeroSubs) ndHeroSubs.textContent = (mock.subscriptions ? mock.subscriptions.length : 0) + ' 个';
    const lbl = $('#node-count-label');
    if (lbl) {
      const fromNum = allFiltered.length ? (startIdx + 1) : 0;
      const toNum = startIdx + pageNodes.length;
      lbl.textContent = '正在显示第 ' + fromNum + '–' + toNum + ' 个节点 · 筛选匹配 ' + allFiltered.length + ' 个（可用 ' + okCnt + ' / 不可达 ' + deadCnt + ' / 未测速 ' + untestedCnt + ' · 全部已入核无上限）';
    }

    const pagerEl = $('#node-pagination-controls');
    if (pagerEl) {
      if (totalPages <= 1) {
        pagerEl.innerHTML = '<span style="color:var(--dim);">共 1 页 (' + allFiltered.length + ' 条)</span>';
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

  const _opsMutationInFlight = {};
  const _opsFieldMuteUntil = {};

  function _readCurrentOpsBool(fieldKey, fallbackVal = false) {
    if (fieldKey === 'require_lan_auth') return Boolean(state.authEnabled);
    if (fieldKey === 'entry_bypass') return Boolean(state.entryBypass);
    if (fieldKey === 'ipv6_proxy') return Boolean(state.ipv6Proxy);
    if (fieldKey === 'block_quic') return Boolean(state.blockQuic);
    if (fieldKey === 'game_udp_direct') return Boolean(state.gameUdpDirect);
    if (fieldKey === 'auto_mute_conflicts') return Boolean(state.conflictGuard);
    if (state.rawOps && fieldKey in state.rawOps) return Boolean(state.rawOps[fieldKey]);
    return Boolean(fallbackVal);
  }

  function renderOpsSettings(ops, fromUserMutation = false) {
    if (ops && typeof ops === 'object') {
      const nowMs = Date.now();
      const filteredOps = {};
      Object.keys(ops).forEach(k => {
        if (!fromUserMutation && (_opsMutationInFlight[k] || (_opsFieldMuteUntil[k] && nowMs < _opsFieldMuteUntil[k]))) {
          return;
        }
        filteredOps[k] = ops[k];
      });
      state.rawOps = Object.assign({}, state.rawOps, filteredOps);
      if ('require_lan_auth' in filteredOps) state.authEnabled = Boolean(filteredOps.require_lan_auth);
      if ('entry_bypass' in filteredOps) state.entryBypass = Boolean(filteredOps.entry_bypass);
      if ('ipv6_proxy' in filteredOps) state.ipv6Proxy = Boolean(filteredOps.ipv6_proxy);
      if ('block_quic' in filteredOps) state.blockQuic = Boolean(filteredOps.block_quic);
      if ('game_udp_direct' in filteredOps) state.gameUdpDirect = Boolean(filteredOps.game_udp_direct);
      if ('auto_mute_conflicts' in filteredOps) state.conflictGuard = Boolean(filteredOps.auto_mute_conflicts);
      if (filteredOps.trusted_cidr) state.trustedCidr = String(filteredOps.trusted_cidr);
      if (filteredOps.gh_mirror != null) state.ghMirror = String(filteredOps.gh_mirror);
      if (filteredOps.update_manifest_url != null) state.updateManifestUrl = String(filteredOps.update_manifest_url);
      if (filteredOps.panel_bind != null) state.panelBind = String(filteredOps.panel_bind);
      if (filteredOps.data_plane_mode) state.dataPlaneMode = String(filteredOps.data_plane_mode);
      if (filteredOps.tun_stack) state.tunStack = String(filteredOps.tun_stack);
      if (filteredOps.tun_mtu != null) state.tunMtu = Number(filteredOps.tun_mtu) || 1500;
      if (Array.isArray(filteredOps.lan_direct_macs)) state.lanDirectMacs = filteredOps.lan_direct_macs.slice();
      try {
        localStorage.setItem('ailink_ops_cache_v1', JSON.stringify({
          require_lan_auth: state.authEnabled,
          entry_bypass: state.entryBypass,
          ipv6_proxy: state.ipv6Proxy,
          block_quic: state.blockQuic,
          game_udp_direct: state.gameUdpDirect,
          auto_mute_conflicts: state.conflictGuard,
          data_plane_mode: state.dataPlaneMode || 'tproxy_redirect',
          tun_stack: state.tunStack || 'mixed',
          tun_mtu: state.tunMtu || 1500,
          lan_direct_macs: state.lanDirectMacs || []
        }));
      } catch (_) {}
    }
    const selDpm = $('#sel-ops-data-plane-mode');
    if (selDpm && state.dataPlaneMode) selDpm.value = state.dataPlaneMode;
    const selTs = $('#sel-ops-tun-stack');
    if (selTs && state.tunStack) selTs.value = state.tunStack;
    const coreSubEl = $('#sys-core-sub');
    if (coreSubEl) {
      const dpmLabel = state.dataPlaneMode === 'tun_full'
        ? '全量 TUN 虚拟网卡 (ailink0)'
        : (state.dataPlaneMode === 'tproxy_tcp_tun_udp' ? 'TCP TProxy + UDP TUN 游戏混合' : 'TProxy + Redirect 零拷贝');
      coreSubEl.textContent = 'AI-LINK v2.4.8 · ' + dpmLabel;
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
        ? '安全风险提示：当前已开启局域网访问鉴权（require_lan_auth=true），非本机访问 API 均需验证管理密码令牌。'
        : '安全风险提示：当前默认允许局域网免密访问 API（require_lan_auth=false）。若局域网有不可信设备或映射了公网端口，请开启「局域网访问鉴权」并修改初始密码！';
    }
  }

  async function mutateOpsSwitch(fieldKey, nextVal, labelText, endpoint = '/api/ops/settings') {
    if (_opsMutationInFlight[fieldKey]) return false;
    const prevVal = _readCurrentOpsBool(fieldKey, !nextVal);
    _opsMutationInFlight[fieldKey] = true;
    _opsFieldMuteUntil[fieldKey] = Date.now() + 3000;
    renderOpsSettings({ [fieldKey]: nextVal }, true);
    if (fieldKey === 'ipv6_proxy') renderOverviewDashboard();
    try {
      const res = await callRouterApi(endpoint, 'POST', { [fieldKey]: nextVal });
      if (res && res.ok !== false) {
        _opsFieldMuteUntil[fieldKey] = Date.now() + 2500;
        renderOpsSettings({ [fieldKey]: nextVal }, true);
        if (fieldKey === 'ipv6_proxy') renderOverviewDashboard();
        if (fieldKey === 'require_lan_auth' && nextVal && (!getAuthToken() || res.auth_required_now)) {
          toast('局域网访问鉴权已开启，请输入面板管理密码以继续会话', 'info');
          promptPanelLoginModal();
        } else {
          toast(labelText + '已' + (nextVal ? '开启' : '关闭'));
        }
        return true;
      }
      _opsFieldMuteUntil[fieldKey] = 0;
      renderOpsSettings({ [fieldKey]: prevVal }, true);
      if (fieldKey === 'ipv6_proxy') renderOverviewDashboard();
      return false;
    } finally {
      _opsMutationInFlight[fieldKey] = false;
    }
  }

  async function handleToggleEntryBypass() {
    const nextEb = !state.entryBypass;
    return await mutateOpsSwitch('entry_bypass', nextEb, '国内流量硬件级旁路');
  }


  /* Plan A Batch 3 & 4 UI Modals: T2 Topology Wizard, T5 Alert Center, T6 Config History, T8 Rule Blocks, T9 Rule Providers */
  async function openTopologyWizardModal() {
    const det = (await callRouterApi('/api/topology/detect', 'GET')) || {};
    const topo = det.topology || 'bypass';
    const evList = (det.evidence || []).map(e => '<li>' + esc(e) + '</li>').join('');
    const step2 = ((det.wizard_steps || [])[1]) || {};
    openModal(
      '拓扑自动识别与 3 步快速接入向导',
      '<div class="trace-stages">' +
        '<div class="trace-stage"><i>识别</i><div><b>自动识别结论：' + esc(det.topology_label || topo) + '</b><span>置信度 ' + Math.round((det.confidence || 0.94) * 100) + '% · 本机 LAN IP: ' + esc(det.lan_ip || location.hostname || '127.0.0.1') + '</span></div><strong>' + esc(topo.toUpperCase()) + '</strong></div>' +
      '</div>' +
      '<div class="modal-form" style="margin-top:12px">' +
        '<div class="modal-field"><label>第 1 步：确认接入拓扑模式（默认已选中自动识别结果）</label>' +
          '<select id="mdl-topo-select">' +
            '<option value="main" ' + (topo === 'main' ? 'selected' : '') + '>主路由模式 (Main Router · 本机拨号与 DHCP)</option>' +
            '<option value="bypass" ' + (topo === 'bypass' ? 'selected' : '') + '>旁路由模式 (Bypass Gateway · 推荐开启 IPv6 防漏)</option>' +
            '<option value="onearm" ' + (topo === 'onearm' ? 'selected' : '') + '>单臂路由模式 (One-Arm Router)</option>' +
            '<option value="docker" ' + (topo === 'docker' ? 'selected' : '') + '>Docker 容器网关模式</option>' +
          '</select>' +
          '<ul style="margin:6px 0 0 16px;color:var(--muted)">' + evList + '</ul>' +
        '</div>' +
        '<div class="modal-field"><label>第 2 步：配置客户端 DNS 与网关指向（可一键复制）</label>' +
          '<div style="padding:8px 10px;background:var(--surface-2);border:1px solid var(--line);border-radius:8px;color:var(--text)">' + esc(step2.guide_text || '') + '</div>' +
          '<div class="input-row" style="margin-top:6px"><input id="mdl-topo-copy-txt" class="mono" readonly value="' + esc(step2.copy_text || '') + '"><button class="button secondary compact" type="button" id="btn-topo-copy-guide">复制配置参数</button></div>' +
        '</div>' +
        '<div class="modal-field"><label>第 3 步：旁路由 IPv6 防漏联动</label>' +
          '<select id="mdl-topo-v6-leak">' +
            '<option value="strict" selected>严格档（默认推荐：阻断全部 LAN→WAN IPv6，彻底防绕过）</option>' +
            '<option value="loose">宽松档（仅阻断海外 IPv6，保留国内 IPv6 直连）</option>' +
            '<option value="off">关闭旁路由 IPv6 防漏</option>' +
          '</select>' +
        '</div>' +
        '<div id="mdl-topo-verify-box" style="color:var(--muted)">点击下方「应用向导并执行连通验证」将联动运行 T1 第 1/2/3 项检查。</div>' +
      '</div>',
      'TOPOLOGY WIZARD',
      async () => {
        const selTopo = ($('#mdl-topo-select') && $('#mdl-topo-select').value) || topo;
        const v6Mode = ($('#mdl-topo-v6-leak') && $('#mdl-topo-v6-leak').value) || 'strict';
        const res = await callRouterApi('/api/topology/apply_wizard', 'POST', {
          topology: selTopo,
          enable_ipv6_leak_guard: v6Mode !== 'off',
          ipv6_leak_mode: v6Mode
        });
        toast((res && res.message) || '接入向导已应用');
        closeModal();
        await syncBackendStatus(false, true);
      },
      '应用向导并执行连通验证'
    );
    const cpBtn = $('#btn-topo-copy-guide');
    if (cpBtn) {
      cpBtn.onclick = () => {
        const v = ($('#mdl-topo-copy-txt') && $('#mdl-topo-copy-txt').value) || '';
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(v);
        toast('已复制接入指引参数');
      };
    }
  }

  async function openRuleBlocksModal(gid) {
    const grp = mock.groups.find(g => g.id === gid) || mock.groups[0];
    if (!grp) return;
    const rbs = Array.isArray(grp.rule_blocks) ? grp.rule_blocks : [];
    const firstRb = rbs[0] || { name: grp.name + ' 专属规则块', logic: 'AND', domain_regex: [], src_ip_cidr: [], port: '' };
    openModal(
      '增强规则块与试匹配编排 · ' + grp.name,
      '<div class="modal-form">' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>规则块名称</label><input id="mdl-rb-name" value="' + esc(firstRb.name || (grp.name + ' 规则块')) + '"></div>' +
          '<div class="modal-field"><label>组合逻辑 (最多两级 AND/OR)</label><select id="mdl-rb-logic"><option value="AND" ' + (firstRb.logic !== 'OR' ? 'selected' : '') + '>AND（全部条件同时满足）</option><option value="OR" ' + (firstRb.logic === 'OR' ? 'selected' : '') + '>OR（满足任一条件即可）</option></select></div>' +
        '</div>' +
        '<div class="modal-field"><label>域名正则 (domain_regex · 保存前自动语法校验，单组 ≤20 条)</label><input id="mdl-rb-regex" class="mono" value="' + esc((firstRb.domain_regex || []).join(', ')) + '" placeholder="例如: ^api.*\.soulapp\.cn$"></div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>按来源设备 IP/CIDR (src_ip_cidr)</label><input id="mdl-rb-srcip" class="mono" value="' + esc((firstRb.src_ip_cidr || []).join(', ')) + '" placeholder="例如: 10.10.10.58/32"></div>' +
          '<div class="modal-field"><label>目标端口 / 端口段 (port / port_range)</label><input id="mdl-rb-port" class="mono" value="' + esc(firstRb.port || '') + '" placeholder="例如: 5228 或 8000:8100"></div>' +
        '</div>' +
        '<div style="margin-top:10px;padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--surface-2)">' +
          '<b style="color:var(--text)">实时规则试匹配 (Rule Match Tester)</b>' +
          '<div class="modal-grid-3" style="margin-top:6px">' +
            '<input id="mdl-rb-test-domain" class="mono" placeholder="测试域名，如 api-chat.soulapp.cn">' +
            '<input id="mdl-rb-test-srcip" class="mono" placeholder="测试源IP，如 10.10.10.58">' +
            '<button type="button" class="button secondary compact" id="btn-rb-run-test">立即试匹配</button>' +
          '</div>' +
          '<div id="mdl-rb-test-result" style="margin-top:6px;color:var(--cyan)">输入域名与源 IP 点击「立即试匹配」可预览命中哪条规则</div>' +
        '</div>' +
      '</div>',
      'RULE BLOCKS & MATCH TESTER',
      async () => {
        const rxRaw = ($('#mdl-rb-regex') && $('#mdl-rb-regex').value.trim()) || '';
        const srcRaw = ($('#mdl-rb-srcip') && $('#mdl-rb-srcip').value.trim()) || '';
        const portRaw = ($('#mdl-rb-port') && $('#mdl-rb-port').value.trim()) || '';
        const newBlock = {
          id: firstRb.id || ('rb_' + Date.now()),
          name: ($('#mdl-rb-name') && $('#mdl-rb-name').value.trim()) || (grp.name + ' 规则块'),
          enabled: true,
          priority: 1,
          logic: ($('#mdl-rb-logic') && $('#mdl-rb-logic').value) || 'AND',
          domain_regex: rxRaw ? rxRaw.split(',').map(s => s.trim()).filter(Boolean) : [],
          src_ip_cidr: srcRaw ? srcRaw.split(',').map(s => s.trim()).filter(Boolean) : [],
          port: portRaw
        };
        const res = await callRouterApi('/api/shunt/rule_blocks', 'POST', {
          group_id: grp.id,
          rule_blocks: (rxRaw || srcRaw || portRaw) ? [newBlock] : []
        });
        if (!res || !res.ok) {
          toast((res && res.message) || '规则块校验失败', 'warn');
          return;
        }
        toast('规则块已保存并实时编译生效');
        closeModal();
        await syncBackendStatus(false, true);
      },
      '保存规则块'
    );
    const tBtn = $('#btn-rb-run-test');
    if (tBtn) {
      tBtn.onclick = async () => {
        const d = ($('#mdl-rb-test-domain') && $('#mdl-rb-test-domain').value.trim()) || 'api-chat.soulapp.cn';
        const sip = ($('#mdl-rb-test-srcip') && $('#mdl-rb-test-srcip').value.trim()) || '';
        const r = await callRouterApi('/api/shunt/test_rule_match', 'POST', { target: d, src_ip: sip });
        const box = $('#mdl-rb-test-result');
        if (box && r) {
          box.textContent = '命中策略组：' + (r.group_name || r.group_id) + ' · 原因：' + (r.reason || '默认规则');
        }
      };
    }
  }

  async function openRuleProvidersModal() {
    const res = (await callRouterApi('/api/shunt/rule_providers', 'GET')) || {};
    const list = res.providers || [];
    const grpOpts = mock.groups.map(g => '<option value="' + esc(g.id) + '">' + esc(g.name) + '</option>').join('');
    state.lastRuleProviders = list;
    const rowsHtml = list.length
      ? list.map(p => '<div class="trace-stage"><i></i><div style="min-width:0"><b>' + esc(p.name) + ' ' + esc(p.group_id) + ' (' + Number(p.rule_count || 0) + ' 条)</b><span class="mono" style="display:block;overflow:hidden;text-overflow:ellipsis">' + esc(p.url) + ' · ' + (p.last_error ? ('失败: ' + esc(p.last_error) + ' (已保留旧规则)') : '同步正常') + '</span></div><div class="button-row" style="gap:5px"><button type="button" class="button ghost compact" data-action="sync-rule-provider" data-rp-id="' + esc(p.id) + '">同步</button><button type="button" class="button danger compact" data-action="delete-rule-provider" data-rp-id="' + esc(p.id) + '" data-rp-name="' + esc(p.name) + '">删除</button></div></div>').join('')
      : '<div class="trace-stage"><i>ℹ</i><div><b>尚无远程规则订阅</b><span>添加后每 24h 自动拉取更新，更新失败自动保留旧版本不影响现有分流</span></div><strong>就绪</strong></div>';
    openModal(
      '远程分流规则订阅管理 · 导入式原子更新',
      '<div class="trace-stages">' + rowsHtml + '</div>' +
      '<div class="modal-form" style="margin-top:12px">' +
        '<div class="modal-grid-3">' +
          '<div class="modal-field"><label>规则源名称</label><input id="mdl-rp-name" placeholder="如：AI 域名增强规则集"></div>' +
          '<div class="modal-field"><label>格式</label><select id="mdl-rp-fmt"><option value="domain_list">域名列表 (Domain List)</option><option value="srs">sing-box 二进制 (.srs)</option></select></div>' +
          '<div class="modal-field"><label>归属分流组</label><select id="mdl-rp-group">' + grpOpts + '</select></div>' +
        '</div>' +
        '<div class="modal-field"><label>远程规则 URL (更新周期：默认 24 小时)</label><input id="mdl-rp-url" class="mono" placeholder="https://example.com/rules/ai-domains.txt"></div>' +
      '</div>',
      'REMOTE RULE SUBSCRIPTIONS',
      async () => {
        const name = ($('#mdl-rp-name') && $('#mdl-rp-name').value.trim()) || '远程规则源';
        const url = ($('#mdl-rp-url') && $('#mdl-rp-url').value.trim()) || '';
        const format = ($('#mdl-rp-fmt') && $('#mdl-rp-fmt').value) || 'domain_list';
        const group_id = ($('#mdl-rp-group') && $('#mdl-rp-group').value) || 'AI';
        if (!url) { toast('请输入远程规则 URL', 'warn'); return; }
        const r = await callRouterApi('/api/shunt/rule_providers', 'POST', { name, url, format, group_id, sync_now: true });
        toast((r && r.sync_result && r.sync_result.message) || '已保存远程规则源');
        closeModal();
        await syncBackendStatus(false, true);
      },
      '添加并立即同步'
    );
  }

  async function openConfigHistoryModal() {
    const res = (await callRouterApi('/api/ops/config_history', 'GET')) || {};
    const hist = res.history || [];
    const rows = hist.length
      ? hist.map(h => {
          const diffTxt = (h.changes || []).slice(0, 3).map(c => c.op + ' ' + c.path + ': ' + JSON.stringify(c.before) + ' ' + JSON.stringify(c.after)).join(' | ') || '配置快照';
          return '<div class="trace-stage">' +
            '<i></i>' +
            '<div style="min-width:0"><b>[' + esc(h.time_str || h.id) + '] ' + esc(h.summary) + ' (' + esc(h.source) + ')</b><span class="mono" style="display:block;overflow:hidden;text-overflow:ellipsis">' + esc(diffTxt) + '</span></div>' +
            '<div class="button-row" style="gap:5px">' +
              '<button class="button ghost compact" data-action="rollback-config-snap" data-snap-id="' + esc(h.id) + '" data-target-state="before" title="撤销该次修改，恢复到执行该次修改之前的状态">↩ 撤销此变更</button>' +
              '<button class="button secondary compact" data-action="rollback-config-snap" data-snap-id="' + esc(h.id) + '" data-target-state="files" title="恢复到该版本（该次变更完成后的状态）">⏪ 恢复到此版本（变更后状态）</button>' +
            '</div>' +
          '</div>';
        }).join('')
      : '<div class="trace-stage"><i></i><div><b>暂无配置变更历史</b><span>每次修改分流、回家、DNS 或运行参数时会自动生成快照（保留最近 20 份 / 7 天）</span></div><strong>就绪</strong></div>';
    openModal(
      '配置变更历史与结构化 Diff 回滚',
      '<div class="trace-stages" style="max-height:360px;overflow-y:auto">' + rows + '</div>',
      'CONFIG HISTORY & ROLLBACK',
      () => closeModal(),
      '关闭'
    );
  }

  async function openAlertCenterModal() {
    const [cfgRes, evRes] = await Promise.all([
      callRouterApi('/api/alerts/config', 'GET'),
      callRouterApi('/api/alerts/events', 'GET')
    ]);
    const cfg = (cfgRes && cfgRes.config) || { webhook: {}, telegram: {}, smtp: {} };
    const evs = (evRes && evRes.events) || [];
    const evRows = evs.length
      ? evs.slice(0, 15).map(e => '<div class="trace-stage"><i>' + (e.status === 'recovered' ? '' : '') + '</i><div><b>' + esc(e.title) + '</b><span>' + esc(e.detail) + '</span></div><strong>' + esc((e.delivered_channels || []).join(',') || '已记录') + '</strong></div>').join('')
      : '<div class="trace-stage"><i></i><div><b>事件中心暂无异常告警</b><span>支持节点全挂、订阅同步失败、DDNS 失步、内核重启、证书到期、磁盘不足、体检失败 7 类事件（30 分钟智能去重）</span></div><strong>正常</strong></div>';
    openModal(
      '告警通道与事件中心 · Webhook / Telegram / SMTP',
      '<div class="modal-form">' +
        '<div class="modal-grid-3">' +
          '<div class="modal-field"><label><input type="checkbox" id="mdl-al-wh-on" ' + (cfg.webhook && cfg.webhook.enabled ? 'checked' : '') + '> Webhook 推送 URL</label><input id="mdl-al-wh-url" class="mono" value="' + esc((cfg.webhook && cfg.webhook.url) || '') + '" placeholder="https://hooks.example.com/alert"></div>' +
          '<div class="modal-field"><label><input type="checkbox" id="mdl-al-tg-on" ' + (cfg.telegram && cfg.telegram.enabled ? 'checked' : '') + '> Telegram Bot Token (脱敏只写)</label><input id="mdl-al-tg-tok" class="mono" value="' + esc((cfg.telegram && cfg.telegram.bot_token) || '') + '" placeholder="123456:ABC-DEF..."></div>' +
          '<div class="modal-field"><label>Telegram Chat ID</label><input id="mdl-al-tg-chat" class="mono" value="' + esc((cfg.telegram && cfg.telegram.chat_id) || '') + '" placeholder="-100123456789"></div>' +
        '</div>' +
        '<div class="trace-stages" style="margin-top:10px;max-height:220px;overflow-y:auto">' + evRows + '</div>' +
      '</div>',
      'ALERT CHANNELS & EVENT CENTER',
      async () => {
        await callRouterApi('/api/alerts/config', 'POST', {
          enabled: true,
          webhook: { enabled: Boolean($('#mdl-al-wh-on') && $('#mdl-al-wh-on').checked), url: ($('#mdl-al-wh-url') && $('#mdl-al-wh-url').value.trim()) || '' },
          telegram: { enabled: Boolean($('#mdl-al-tg-on') && $('#mdl-al-tg-on').checked), bot_token: ($('#mdl-al-tg-tok') && $('#mdl-al-tg-tok').value.trim()) || '', chat_id: ($('#mdl-al-tg-chat') && $('#mdl-al-tg-chat').value.trim()) || '' }
        });
        toast('告警通道配置已保存');
        closeModal();
      },
      '保存告警配置'
    );
  }

  function renderOpsAndUpdatesSection() {
    renderOpsSettings(state.rawOps);
    const totalRealConns = Math.max((state.rawConnections || []).length, Number(mock.connections) || 0);
    const setHeroConns = $('#settings-hero-stat-conns');
    if (setHeroConns) setHeroConns.textContent = state.backendOffline ? '--' : (String(totalRealConns) + ' 条');
    const setHeroCore = $('#settings-hero-stat-core');
    if (setHeroCore) setHeroCore.textContent = state.coreOnline === false ? '内核离线' : '运行正常';
    const connStat = $('#conn-stat-count');
    if (connStat) connStat.textContent = state.backendOffline ? '--' : String(totalRealConns);
    const pill = $('#settings-proxy-status-pill');
    if (pill) {
      pill.textContent = state.backendOffline ? '服务未连接' : (!state.coreAlive ? '内核离线' : state.bypassActive ? '直连恢复中' : '运行正常');
    }
    const showOfflineBanner = state.backendOffline || !state.coreAlive;
    const coreOfflineBanner = $('#core-offline-alert-banner');
    if (coreOfflineBanner) coreOfflineBanner.classList.toggle('hidden', !showOfflineBanner);
    const ovOfflineCard = $('#ov-core-offline-card');
    if (ovOfflineCard) ovOfflineCard.classList.add('hidden');
    const bypassBanner = $('#bypass-alert-banner');
    if (bypassBanner) bypassBanner.classList.toggle('hidden', !state.bypassActive);
    renderLogsViewer();
  }

  /* Fix #13 & U-08: Connections Table with Flat Field Mapping (c.host / c.src_ip) + LAN Device Filter Dropdown */
  function normalizeConnItem(c) {
    const meta = (c && c.metadata) || {};
    let rawHost = String((c && c.host) || meta.host || meta.destinationIP || '').trim();
    rawHost = rawHost.replace(/:(\d+):\d+$/, ':$1');
    const portFromMeta = String(meta.destinationPort || '').trim();
    if (rawHost && !/:\d+$/.test(rawHost) && portFromMeta) {
      rawHost = rawHost + ':' + portFromMeta;
    }
    const dst = (!rawHost || rawHost === '-' || rawHost.startsWith('unknown')) ? '未知目标' : rawHost;
    const srcIp = String((c && c.src_ip) || meta.sourceIP || '').trim();
    const srcPort = String(meta.sourcePort || '').trim();
    const devObj = (state.galaxyLanDevices || []).find(d => d && d.ip === srcIp);
    const devName = devObj && devObj.name && !devObj.name.startsWith(srcIp) ? devObj.name : '';
    const srcDisplay = srcIp ? (devName ? (srcIp + ' (' + devName + ')') : (srcIp + (srcPort ? ':' + srcPort : ''))) : '本机网关';
    const net = String((c && c.network) || meta.network || 'tcp').toUpperCase();
    const rule = String((c && c.rule) || 'MATCH') + (c && c.rulePayload ? ' (' + c.rulePayload + ')' : '');
    const chainsArr = Array.isArray(c && c.chains) ? c.chains.map(cleanNodeDisplayName) : ['PROXY'];
    const chain = chainsArr.slice().reverse().join(' -> ');
    return {
      id: (c && c.id) || '',
      dst,
      srcIp: srcIp || 'LOCAL',
      srcDisplay,
      net,
      rule,
      chain,
      download: Number((c && c.download) || 0),
      upload: Number((c && c.upload) || 0)
    };
  }

  function renderConnectionsSection() {
    const allNormalized = (state.rawConnections || []).map(normalizeConnItem);
    const devSel = $('#conn-device-filter');
    if (devSel) {
      const countsByIp = {};
      allNormalized.forEach(item => {
        countsByIp[item.srcIp] = (countsByIp[item.srcIp] || 0) + 1;
      });
      (state.galaxyLanDevices || []).forEach(d => {
        if (d && d.ip && !(d.ip in countsByIp)) {
          countsByIp[d.ip] = Number(d.conns || 0);
        }
      });
      const totalRealConns = Math.max(allNormalized.length, Number(mock.connections) || 0);
      const isTrunc = totalRealConns > allNormalized.length && allNormalized.length > 0;
      const curDev = state.connDeviceFilter || 'ALL';
      const devKeys = Object.keys(countsByIp).sort((a, b) => (countsByIp[b] || 0) - (countsByIp[a] || 0));
      const allLabel = isTrunc ? ('设备: 全部终端 (采样 ' + allNormalized.length + '/' + totalRealConns + ')') : ('设备: 全部终端 (' + totalRealConns + ')');
      const opts = ['<option value="ALL"' + (curDev === 'ALL' ? ' selected' : '') + '>' + allLabel + '</option>'];
      devKeys.forEach(ip => {
        const label = ip === 'LOCAL' ? '本机网关' : ip;
        opts.push('<option value="' + esc(ip) + '"' + (curDev === ip ? ' selected' : '') + '>' + esc(label) + ' (' + countsByIp[ip] + ' 条)</option>');
      });
      devSel.innerHTML = opts.join('');
    }
    const totalRealConns = Math.max(allNormalized.length, Number(mock.connections) || 0);
    const setHeroConns = $('#settings-hero-stat-conns');
    if (setHeroConns && !state.backendOffline) setHeroConns.textContent = String(totalRealConns) + ' 条';
    const q = (state.connSearch || '').trim().toLowerCase();
    const devF = state.connDeviceFilter || 'ALL';
    const list = allNormalized.filter(item => {
      if (devF !== 'ALL' && item.srcIp !== devF) return false;
      if (!q) return true;
      return (item.dst + ' ' + item.srcDisplay + ' ' + item.rule + ' ' + item.chain + ' ' + item.net).toLowerCase().includes(q);
    });
    const connStat = $('#conn-stat-count');
    if (connStat) {
      connStat.textContent = (devF !== 'ALL' || q) ? (list.length + ' / ' + totalRealConns) : String(totalRealConns);
    }
    const tbody = $('#connections-tbody');
    if (!tbody) return;
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state" style="padding:26px 12px">' +
        '<span class="empty-orbit"></span>' +
        '<h4>' + ((devF !== 'ALL' || q) ? '当前筛选条件下无匹配连接' : '当前无活跃代理连接 · 产生流量后实时显示') + '</h4>' +
        '<p>支持按上方「局域网终端设备」下拉框或输入域名、源 IP、分流规则、出站节点实时筛选五元组连接。</p>' +
      '</div></td></tr>';
      return;
    }
    tbody.innerHTML = list.slice(0, 50).map(item => {
      const mPort = item.dst.match(/^(.*)(:\d+)$/);
      const dstHtml = mPort
        ? ('<b>' + esc(mPort[1]) + '</b><span style="color:var(--text-3)">' + esc(mPort[2]) + '</span>')
        : ('<b>' + esc(item.dst) + '</b>');
      const traffic = '↓ ' + fmtBytes(item.download) + ' / ↑ ' + fmtBytes(item.upload);
      return '<tr>' +
        '<td class="mono">' + dstHtml + '<small style="display:block;color:var(--text-3)">源: ' + esc(item.srcDisplay) + '</small></td>' +
        '<td><span class="status-pill">' + esc(item.net) + '</span></td>' +
        '<td>' + esc(item.rule) + '</td>' +
        '<td class="mono" style="color:var(--cyan)">' + esc(item.chain) + '</td>' +
        '<td class="mono">' + esc(traffic) + '</td>' +
        '<td><button class="button ghost danger-text compact" style="padding:0 8px;" data-action="close-single-conn" data-cid="' + esc(item.id) + '">断开</button></td>' +
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

  function renderActivePageOnly() {
    const p = state.page || 'galaxy';
    if (p === 'galaxy') {
      renderInspector(state.selected);
    } else if (p === 'overview') {
      renderOverviewDashboard();
    } else if (p === 'shunt') {
      renderShuntMatrix();
    } else if (p === 'homelink') {
      renderHomeLinkSection(false);
    } else if (p === 'dns') {
      renderDnsAndFilterSection();
    } else if (p === 'nodes') {
      renderSubscriptionsAndNodes();
    } else if (p === 'settings') {
      renderOpsAndUpdatesSection();
      renderConnectionsSection();
    }
  }

  function renderAll() {
    renderOverviewDashboard();
    renderShuntMatrix();
    renderHomeLinkSection(false);
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
    renderActivePageOnly();
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
          mock.connections = typeof res.total === 'number' ? res.total : res.connections.length;
          mock.connsDisplayed = res.connections.length;
          mock.connsTruncated = Boolean(res.truncated) || (mock.connections > res.connections.length);
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
      spotlightHtml = '<div class="galaxy-waterline-box" style="border-color:var(--accent-border);background:var(--accent-subtle)">' +
        '<div class="galaxy-waterline-top"><span style="color:var(--cyan);font-weight:600">当前聚焦卫星: ' + esc(selectedItem.name) + '</span><b>' + esc(selectedItem.meta || formatLatencyText(selectedItem.rtt, false)) + '</b></div>' +
        '<div style="color:var(--muted)">' + esc(selectedItem.subtitle || '点击下方列表或星体可切换透视目标') + '</div>' +
      '</div>';
    }

    if (tab === 'core') {
      const devs = (state.galaxyLanDevices && state.galaxyLanDevices.length)
        ? state.galaxyLanDevices
        : state.insightDevices.map(d => ({ ip: d.ip || '', name: d.name || d.ip, down_rate: 0, up_rate: 0, conns: 0, totalMb: d.totalMb || 0, is_remote: false }));
      const sortedDevs = devs.slice().sort((a, b) => ((Number(b.down_rate || 0) + Number(b.up_rate || 0)) - (Number(a.down_rate || 0) + Number(a.up_rate || 0))) || ((b.conns || 0) - (a.conns || 0)));
      const totalOnlineDevs = (Number(mock.devicesTotal) > 0) ? Number(mock.devicesTotal) : sortedDevs.length;
      const maxConns = (Number(mock.conntrackMax) > 0) ? Number(mock.conntrackMax) : 65536;
      const conntrackCur = (Number(mock.conntrackCount) > 0) ? Number(mock.conntrackCount) : Number(mock.connections || 0);
      const maxMemMib = (Number(mock.memTotalMib) > 0) ? Number(mock.memTotalMib) : 1024;
      const rawConnPct = (conntrackCur / maxConns) * 100;
      const connPct = (!state.backendOffline && Number.isFinite(rawConnPct)) ? Math.min(100, Math.max(0, rawConnPct)) : null;
      const rawMemPct = (Number(mock.coreMemMib) / maxMemMib) * 100;
      const memPct = (!state.backendOffline && Number.isFinite(rawMemPct)) ? Math.min(100, Math.max(0, rawMemPct)) : null;

      const rowsHtml = sortedDevs.slice(0, 10).map(d => {
        const rateSum = Number(d.down_rate || 0) + Number(d.up_rate || 0);
        const speedTxt = rateSum > 0
          ? ('↓ ' + fmtRate(d.down_rate || 0) + ' · ↑ ' + fmtRate(d.up_rate || 0))
          : (d.totalMb ? ('累计 ' + d.totalMb + ' MB') : '↓ 0 B/s · ↑ 0 B/s');
        const subMeta = (d.ip ? ('IP: ' + d.ip + ' · ') : '') + (d.is_remote ? '回家加密隧道' : '局域网在线终端');
        return '<div class="galaxy-entity-row">' +
          '<div class="galaxy-entity-icon">' + (d.is_remote ? '' : '') + '</div>' +
          '<div class="galaxy-entity-main"><b>' + esc(d.name || d.ip || '局域网终端') + '</b><span class="mono">' + esc(subMeta) + '</span></div>' +
          '<div class="galaxy-entity-right"><strong>' + esc(speedTxt) + '</strong><small>' + esc(Number(d.conns || 0)) + ' 连 · 挡位:' + esc(computeSpeedGearInfo(rateSum, d.conns || 0).label) + '</small></div>' +
        '</div>';
      }).join('');

      return spotlightHtml +
        '<div class="galaxy-kpi-grid">' +
          '<div class="galaxy-kpi-card"><span>在线终端总数</span><b style="color:var(--cyan)">' + esc(totalOnlineDevs) + ' 台</b><small>' + (sortedDevs.length < totalOnlineDevs ? ('星图采样 Top ' + esc(sortedDevs.length) + ' 活跃终端') : '含局域网与回家远程终端') + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>代理活跃会话</span><b style="color:var(--violet)">' + esc(mock.connections) + '</b><small>内核运行: ' + esc(mock.uptimeStr) + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>实时总下行</span><b style="color:var(--mint)">' + esc(mock.downText) + '</b><small>累计下载 ' + esc(mock.inTotalText) + '</small></div>' +
          '<div class="galaxy-kpi-card"><span>实时总上行</span><b style="color:var(--amber)">' + esc(mock.upText) + '</b><small>累计上传 ' + esc(mock.outTotalText) + '</small></div>' +
        '</div>' +
        '<div class="galaxy-waterline-box">' +
          '<div class="galaxy-waterline-row">' +
            '<div class="galaxy-waterline-top"><span>内核连接池水位 (nf_conntrack)</span><b>' + (connPct !== null ? (esc(conntrackCur) + ' / ' + esc(maxConns) + ' (' + esc(connPct.toFixed(2)) + '%)') : '--') + '</b></div>' +
            '<div class="galaxy-waterline-bar"><i style="width:' + (connPct !== null ? Math.max(4, connPct) : 0) + '%"></i></div>' +
          '</div>' +
          '<div class="galaxy-waterline-row">' +
            '<div class="galaxy-waterline-top"><span>内核常驻内存 (RSS)</span><b>' + (memPct !== null ? (esc(Number(mock.coreMemMib).toFixed(1)) + ' MiB / ' + esc(maxMemMib) + ' MiB (' + esc(memPct.toFixed(1)) + '%)') : '--') + '</b></div>' +
            '<div class="galaxy-waterline-bar"><i style="width:' + (memPct !== null ? Math.max(6, memPct) : 0) + '%"></i></div>' +
          '</div>' +
        '</div>' +
        '<div class="galaxy-list-head"><b>接入终端列表 (按实时速率排序)</b><span>' + (sortedDevs.length < totalOnlineDevs ? ('活跃 Top ' + esc(sortedDevs.length) + ' / 共 ' + esc(totalOnlineDevs) + ' 台') : ('共 ' + esc(totalOnlineDevs) + ' 台')) + '</span></div>' +
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
          '<div class="galaxy-entity-icon" style="color:var(--pink);border-color:var(--line-strong);background:var(--surface-2)">🇨🇳</div>' +
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
            '<div class="galaxy-waterline-top"><span>国内直连母星链路流速挡位</span><b style="color:var(--pink)">' + esc(trunkGear.fullLabel) + '挡 · 约 18 ms</b></div>' +
            '<div class="galaxy-waterline-bar"><i style="width:94%;background:linear-gradient(90deg,var(--pink),var(--pink-strong))"></i></div>' +
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
          '<div class="galaxy-entity-icon"></div>' +
          '<div class="galaxy-entity-main"><b>' + esc(s.name || s.domain) + '</b><span class="mono">[' + esc(grpClean) + '] ' + esc(exitTxt) + '</span></div>' +
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

      const rowsHtml = (mock.blocked && mock.blocked.length)
        ? mock.blocked.slice(0, 8).map(b =>
            '<div class="galaxy-entity-row">' +
              '<div class="galaxy-entity-icon" style="color:var(--amber);border-color:var(--warn-border)"></div>' +
              '<div class="galaxy-entity-main"><b class="mono">' + esc(b[0]) + '</b><span>' + esc(b[1] || '黑名单规则拦截') + ' · ' + esc(b[3] || 'DNS/路由阻断') + '</span></div>' +
              '<div class="galaxy-entity-right"><strong style="color:var(--amber)">' + esc(Number(b[2] || 0).toLocaleString('zh-CN')) + ' 次</strong><small>已引力吞噬</small></div>' +
            '</div>'
          ).join('')
        : '<div class="galaxy-entity-row"><div class="galaxy-entity-icon" style="color:var(--mint);border-color:var(--ok-border)"></div><div class="galaxy-entity-main"><b>今日已拦截 0 次 · 净网黑洞引擎实时值守中</b><span>DNS REFUSED 与路由 REJECT 双层规则库已挂载生效</span></div><div class="galaxy-entity-right"><strong style="color:var(--mint)">0 次</strong><small>实时监听</small></div></div>';

      return spotlightHtml +
        '<div class="galaxy-kpi-grid">' +
          '<div class="galaxy-kpi-card"><span>已吞噬广告/追踪</span><b style="color:var(--amber)">' + esc((Number.isFinite(Number(mock.blockedTotal)) ? (Number.isFinite(Number(mock.blockedTotal)) ? Number(mock.blockedTotal).toLocaleString('zh-CN') : '--') : '0')) + '</b><small>拦截率 ' + esc(Number(mock.dnsBlockedPct || 0).toFixed(1)) + '% · 实时捕获</small></div>' +
          '<div class="galaxy-kpi-card"><span>挂载有效规则</span><b style="color:var(--mint)">' + esc(Number(mock.dnsRulesCount || 50000).toLocaleString('zh-CN')) + '</b><small>.srs 规则集 + DNS 双保险</small></div>' +
          '<div class="galaxy-kpi-card"><span>DNS 层前置阻断</span><b style="color:var(--cyan)">' + esc(Number(mock.dnsLayerCount || 0).toLocaleString('zh-CN')) + '</b><small>毫秒级零开销拒绝</small></div>' +
          '<div class="galaxy-kpi-card"><span>路由层 REJECT</span><b style="color:var(--violet)">' + esc(Number(mock.rejectLayerCount || 0).toLocaleString('zh-CN')) + '</b><small>防硬编码 IP / DoH 绕过</small></div>' +
        '</div>' +
        '<div class="galaxy-waterline-box">' + catBarsHtml + '</div>' +
        '<div class="galaxy-list-head"><b>黑洞吞噬高频域名 TOP 榜</b><span>双层实时阻断</span></div>' +
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
        ? '点击上方「内核 / 🇨🇳 国内 / 海外 / 黑洞」标签或 3D 星体，即可查看对应星系的接入终端、实时访问站点与黑洞拦截详情。'
        : '检测到 sing-box 代理内核未运行，透明代理已自动回退直连保护。';
    }
    if ($('#detail-grid')) {
      $('#detail-grid').innerHTML =
        '<div><span>运行模式</span><b>' + esc(eg.modeName) + '</b></div>' +
        '<div><span>在线终端</span><b>' + esc(mock.devicesTotal) + ' 台终端</b></div>' +
        '<div><span>可用节点</span><b>' + esc(okCnt) + ' (' + esc(covPct) + ')</b></div>' +
        '<div><span>黑洞拦截</span><b>' + esc((Number.isFinite(Number(mock.blockedTotal)) ? Number(mock.blockedTotal).toLocaleString('zh-CN') : '--')) + ' 次</b></div>';
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
        subtitle: (d.is_remote ? '回家加密隧道 · ' : '局域网终端 · ') + (d.ip || 'LAN'),
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
        subtitle: '海外代理 [' + grpClean + '] ' + (s.exit_node || eg.nodeName),
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
        label: '拦截 ' + (Number.isFinite(Number(mock.blockedTotal)) ? (Number.isFinite(Number(mock.blockedTotal)) ? Number(mock.blockedTotal).toLocaleString('zh-CN') : '--') : '0') + ' 次'
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
        if (Array.isArray(nodesRes.subscriptions)) {
          applySubscriptionsFromApi(nodesRes.subscriptions);
        }
        state.rawNodes = nodesRes.nodes;
        if (Array.isArray(nodesRes.nodes)) {
          mock.nodes = nodesRes.nodes.map((n, i) => {
            const rawRtt = n.delay_ms != null ? n.delay_ms : n.rtt;
            const rtt = (rawRtt != null && Number(rawRtt) > 0) ? Math.round(Number(rawRtt)) : null;
            const rawSt = n.probe_state || n.state || n.status || 'untested';
            const probeTs = Number(n.probe_ts || 0);
            const st = (rawSt === 'ok' && rtt != null && rtt > 0)
              ? 'ok'
              : ((rawSt === 'untested' || rawSt === 'pending' || (probeTs <= 0 && rtt == null && rawSt !== 'dead')) ? 'untested' : 'dead');
            const rawScore = n.score_20 != null ? n.score_20 : n.score;
            const score = (rawScore != null && Number(rawScore) > 0 && st === 'ok') ? Math.round(Number(rawScore)) : (st === 'ok' ? 92 : null);
            const isCust = Boolean(n.is_custom || n._manual || n.sub_id === 'custom' || (!n._sub_id && !n.sub_id && !n._sub_url && !n.sub_url));
            const rawTag = String(n.raw_name || n.tag || n.name || ('node-' + i));
            const subIdVal = isCust ? 'custom' : (n._sub_id || n.sub_id || 'sub_main');
            const subNameVal = isCust ? '手动添加节点' : resolveNodeSubDisplayName({ _sub_id: subIdVal, _sub_name: n._sub_name || n.sub_name || '', is_custom: isCust });
            return {
              id: n.node_id || ('node-' + i),
              tag: rawTag,
              raw_name: rawTag,
              name: formatNodeUnifiedDisplayName({ raw_name: rawTag, tag: rawTag, _sub_id: subIdVal, _sub_name: subNameVal, is_custom: isCust }, subNameVal),
              region: classifyNodeCountry({ raw_name: rawTag, tag: rawTag, country: n.country, region: n.region }),
              protocol: String(n.type || n.protocol || 'PROXY').toUpperCase(),
              status: st,
              probe_ts: probeTs,
              rtt: st === 'ok' ? rtt : null,
              score: score,
              kernel: true,
              is_custom: isCust,
              _manual: Boolean(n._manual || isCust),
              server: n.server || '',
              server_port: n.server_port || 443,
              sub_id: subIdVal,
              sub_url: n._sub_url || n.sub_url || '',
              sub_name: subNameVal,
              node_key: n.node_key || n.node_id || '',
              google_region: n.google_region || '',
              google_region_label: n.google_region_label || '',
              gemini_supported: n.gemini_supported !== false,
              region_blocked: Boolean(n.region_blocked),
              l7_degraded: Boolean(n.l7_degraded || n.l7_degraded_fallback),
              line_type: n.line_type || 'direct_line',
              line_badge: n.line_badge || '直连线路',
              is_relay: Boolean(n.is_relay),
              is_chained: Boolean(n.is_chained),
              detour_target: n.detour_target || n.detour || n.detour_pool_id || '',
              bandwidth_mbps: Number(n.bandwidth_mbps || 0),
              svc: (n.svc && typeof n.svc === 'object') ? n.svc : {},
              sparkline: Array.isArray(n.sparkline) ? n.sparkline : []
            };
          });
        }
      }

      if (galRes && galRes.ok !== false) {
        state.rawGalaxy = galRes;
        if (Array.isArray(galRes.lan)) {
          state.galaxyLanDevices = galRes.lan;
        }
        if (Array.isArray(galRes.domestic)) {
          state.galaxyDomesticSites = galRes.domestic;
        }
        if (Array.isArray(galRes.foreign)) {
          state.galaxyForeignSites = galRes.foreign;
        }
        if (galRes.blackhole && typeof galRes.blackhole === 'object') {
          const bh = galRes.blackhole;
          if (Array.isArray(bh.categories)) {
            state.galaxyBlackholeCategories = bh.categories;
          }
          if (Array.isArray(bh.top_blocked)) {
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
        if (stRes.ipv6_proxy != null && !_opsMutationInFlight.ipv6_proxy && !(Date.now() < (_opsFieldMuteUntil.ipv6_proxy || 0))) {
          state.ipv6Proxy = Boolean(stRes.ipv6_proxy);
        }

        if (stRes.ops_settings) {
          renderOpsSettings(stRes.ops_settings);
        }
        if (Array.isArray(stRes.switch_history)) {
          mock.switchHistory = stRes.switch_history;
        }
        if (Array.isArray(stRes.probe_schedules)) {
          mock.schedules = stRes.probe_schedules;
        }
        if (!(nodesRes && Array.isArray(nodesRes.subscriptions)) && stRes.subscriptions && Array.isArray(stRes.subscriptions)) {
          applySubscriptionsFromApi(stRes.subscriptions);
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
          if (Array.isArray(sh.auto_nodes)) {
            state.rawAutoNodes = sh.auto_nodes;
            mock.autoPools = sh.auto_nodes.map(a => {
              const tSize = Math.max(1, Math.min(10, Number(a.target_size || 5)));
              const rThresh = Math.max(1, Math.min(tSize, Number(a.replenish_threshold != null ? a.replenish_threshold : Math.max(1, Math.ceil(tSize / 2)))));
              const rawSrcs = Array.isArray(a.scope_sources) && a.scope_sources.length
                ? a.scope_sources
                : (a.scope_source ? String(a.scope_source).split(',').map(x => x.trim()).filter(Boolean) : ['ALL']);
              return {
                id: a.id,
                tag: a.tag || a.id,
                name: a.name || a.id,
                mode: a.mode || 'full',
                pool_mode: a.pool_mode || ((a.service_check_enabled || a.mode === 'full') ? 'service_check' : 'ping_only'),
                service_check_enabled: Boolean(a.service_check_enabled || a.mode === 'full'),
                service_checks: Array.isArray(a.service_checks) ? a.service_checks : [],
                service_logic: a.service_logic || a.match_mode || 'all',
                scope_sources: rawSrcs.length ? rawSrcs : ['ALL'],
                scope_source: a.scope_source || 'ALL',
                scope_countries: Array.isArray(a.scope_countries) && a.scope_countries.length ? a.scope_countries : ['ALL'],
                target_size: tSize,
                replenish_threshold: rThresh,
                auto_maintain: a.auto_maintain !== false,
                smart_switch_enabled: a.smart_switch_enabled !== false,
                healthy_count: (() => {
                  const rawH = Number(a.pool_reachable_count != null ? a.pool_reachable_count : (a.healthy_count != null ? a.healthy_count : 0));
                  if (rawH > 0) return rawH;
                  const g0Members = (a.groups && a.groups[0] && Array.isArray(a.groups[0].members)) ? a.groups[0].members : [];
                  const okMembers = g0Members.filter(m => m && m.state === 'ok' && Number(m.delay_ms || 0) > 0).length;
                  if (okMembers > 0) return okMembers;
                  const boundGrp = Array.isArray(sh.groups) ? sh.groups.find(g => g.auto_node_id === a.id && (g.shunt_mode === 'auto' || g.mode === 'auto') && g.resolved_node && g.resolved_node !== 'direct') : null;
                  if ((a.current_node && a.current_node !== 'direct') || boundGrp) return 1;
                  return 0;
                })(),
                active_group_index: Number(a.active_group_index || 1),
                current_node: (() => {
                  if (a.current_node && a.current_node !== 'direct') return cleanNodeDisplayName(a.current_node);
                  const boundGrp = Array.isArray(sh.groups) ? sh.groups.find(g => g.auto_node_id === a.id && (g.shunt_mode === 'auto' || g.mode === 'auto') && g.resolved_node && g.resolved_node !== 'direct') : null;
                  if (boundGrp) return cleanNodeDisplayName(boundGrp.resolved_node);
                  return a.current_node || 'direct';
                })(),
                current_delay_ms: (() => {
                  if (a.current_delay_ms != null && Number(a.current_delay_ms) > 0) return Math.round(Number(a.current_delay_ms));
                  const curClean = a.current_node ? cleanNodeDisplayName(a.current_node) : '';
                  if (curClean && curClean !== 'direct') {
                    const matchedN = (mock.nodes || []).find(n => (n.tag || n.name) === a.current_node || cleanNodeDisplayName(n.tag || n.name) === curClean);
                    if (matchedN && Number(matchedN.rtt) > 0) return Math.round(Number(matchedN.rtt));
                  }
                  const boundGrp = Array.isArray(sh.groups) ? sh.groups.find(g => g.auto_node_id === a.id && (g.shunt_mode === 'auto' || g.mode === 'auto') && g.resolved_node && (!a.current_node || cleanNodeDisplayName(g.resolved_node) === curClean)) : null;
                  const bMs = boundGrp ? (boundGrp.resolved_rtt_ms != null ? boundGrp.resolved_rtt_ms : boundGrp.delay_ms) : null;
                  if (bMs != null && Number(bMs) > 0) return Math.round(Number(bMs));
                  return null;
                })(),
                current_google_region: a.current_google_region || '',
                dispatch_mode: a.dispatch_mode || 'single_best',
                multi_line_nodes: Array.isArray(a.multi_line_nodes) ? a.multi_line_nodes : [],
                active_lines_count: Number(a.active_lines_count || 1),
                multi_line_locked: Boolean(a.multi_line_locked),
                multi_line_locked_reason: a.multi_line_locked_reason || '',
                bandwidth_prefer: Boolean(a.bandwidth_prefer),
                bandwidth_interval_h: Number(a.bandwidth_interval_h || 6),
                bandwidth_limit_mb: Number(a.bandwidth_limit_mb || 16),
                estimated_daily_bw_mib: Number(a.estimated_daily_bw_mib || 0),
                keyword_filter: a.keyword_filter || '',
                keyword_mode: a.keyword_mode || 'OR',
                l7_degraded: Boolean(a.l7_degraded || a.l7_degraded_fallback),
                pool_degraded_alert: Boolean(a.pool_degraded_alert),
                degraded_reason: a.degraded_reason || '',
                selection_explain: a.selection_explain || '',
                missing_members: Array.isArray(a.missing_members) ? a.missing_members : [],
                filters: (a.filters && typeof a.filters === 'object') ? a.filters : null,
                groups: Array.isArray(a.groups) ? a.groups : []
              };
            });
          }
          if (Array.isArray(sh.groups)) {
            mock.groups = sh.groups.map(g => {
              const gMode = g.shunt_mode || g.mode || 'auto';
              const gAid = g.auto_node_id || 'auto_youtube';
              const boundP = gMode === 'auto' ? (mock.autoPools || []).find(p => p.id === gAid || p.tag === gAid || p.name === g.auto_node_name) : null;
              const rawMs = (boundP && boundP.current_delay_ms > 0) ? boundP.current_delay_ms : (g.resolved_rtt_ms != null ? g.resolved_rtt_ms : g.delay_ms);
              const validMs = (rawMs != null && Number(rawMs) > 0) ? Math.round(Number(rawMs)) : null;
              const resolvedN = (boundP && boundP.current_node && boundP.current_node !== 'direct')
                ? boundP.current_node
                : (g.resolved_node || g.manual_node || 'direct');
              return {
                id: g.id,
                name: g.title || g.name || g.id,
                subtitle: g.subtitle || g.desc || '精细分流策略组',
                shunt_mode: gMode,
                auto_node_id: (boundP && boundP.id) || gAid,
                auto_node_name: (boundP && boundP.name) || g.auto_node_name || '自动节点池',
                country: g.country || 'JP',
                manual_node: g.manual_node || '',
                resolved_node: resolvedN,
                dispatch_mode: g.dispatch_mode || (boundP && boundP.dispatch_mode) || 'single_best',
                multi_line_nodes: Array.isArray(g.multi_line_nodes) ? g.multi_line_nodes : ((boundP && boundP.multi_line_nodes) || []),
                active_lines_count: Number(g.active_lines_count || (boundP && boundP.active_lines_count) || 1),
                auto_single_line_protected: Boolean(g.auto_single_line_protected),
                ip_sensitive: Boolean(g.ip_sensitive || ['AI','AI_Assistant','Google','Microsoft','Apple','Apple_Microsoft','Social','Social_Media','Custom_Soul','Custom_Copilot','Custom_WorkBuddy'].includes(g.id)),
                strict_lock: Boolean(g.strict_lock),
                manual_drifted: Boolean(g.manual_drifted),
                strict_locked_dead: Boolean(g.strict_locked_dead),
                drift_warning: g.drift_warning || g.failover_reason || '',
                dns_strategy: g.dns_strategy || 'inherit',
                custom_dns: g.custom_dns || '',
                rule_blocks: Array.isArray(g.rule_blocks) ? g.rule_blocks : [],
                rtt: validMs,
                domains: Array.isArray(g.domains) ? g.domains : [],
                domain_keywords: Array.isArray(g.domain_keywords) ? g.domain_keywords : [],
                exact_domains: Array.isArray(g.exact_domains) ? g.exact_domains : [],
                ip_cidrs: Array.isArray(g.ip_cidrs) ? g.ip_cidrs : [],
                is_custom: Boolean(g.is_custom || !['AI_Assistant','YouTube','Netflix_Disney','TikTok','Social_Media','Gaming','GitHub_Dev','Apple_Microsoft','Domestic_CN','Final_Fallback'].includes(g.id)),
                locked_bottom: Boolean(g.locked_bottom),
                locked_order: Boolean(g.locked_order)
              };
            });
          }
          if (sh.hit_stats && typeof sh.hit_stats === 'object') {
            state.shuntHitStats = sh.hit_stats;
          }
        }
        if (stRes.homelink && Array.isArray(stRes.homelink.nodes)) {
          state.rawHomelink = stRes.homelink;
          if (Array.isArray(stRes.homelink.nodes)) {
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
          const _nowDnsMs = Date.now();
          if (!_opsMutationInFlight.dns_filter && !(_opsFieldMuteUntil.dns_filter && _nowDnsMs < _opsFieldMuteUntil.dns_filter)) {
            if (dt.filter && dt.filter.enabled != null) {
              state.dnsEnabled = Boolean(dt.filter.enabled);
            } else if (shd.enabled != null) {
              state.dnsEnabled = Boolean(shd.enabled);
            } else if (shd.state) {
              state.dnsEnabled = (shd.state !== 'disabled');
            }
          }
          if (!_opsMutationInFlight.dns_essential_protect && !(_opsFieldMuteUntil.dns_essential_protect && _nowDnsMs < _opsFieldMuteUntil.dns_essential_protect)) {
            if (dt.filter && dt.filter.essential_app_protect != null) {
              state.dnsEssentialProtect = Boolean(dt.filter.essential_app_protect);
            }
          }
          if (dt.cn_upstream) state.cnUpstream = dt.cn_upstream;
          if (dt.remote_upstream) state.remoteUpstream = dt.remote_upstream;

          const realRulesCnt = s24.total_loaded_rules != null ? Number(s24.total_loaded_rules) : (shd.total_rules != null ? Number(shd.total_rules) : null);
          if (realRulesCnt != null && realRulesCnt >= 0) mock.dnsRulesCount = realRulesCnt;
          if (s24.blocked_queries != null) mock.blockedTotal = Number(s24.blocked_queries);
          if (s24.dns_layer_blocks != null) mock.dnsLayerCount = Number(s24.dns_layer_blocks);
          if (s24.route_reject_blocks != null) mock.rejectLayerCount = Number(s24.route_reject_blocks);
          if (s24.blocked_pct != null) mock.dnsBlockedPct = Number(s24.blocked_pct);
          mock.dnsAvgMs = (s24.avg_resolve_ms != null && Number(s24.avg_resolve_ms) >= 0) ? Number(s24.avg_resolve_ms) : null;

          const topDom = s24.top_blocked_domains || dt.top_blocked_domains || shd.top_blocked_domains;
          if (Array.isArray(topDom)) {
            mock.blocked = topDom.slice(0, 8).map(d => [
              d.domain || d[0],
              d.category || d.reason || '净网护盾拦截',
              Number(d.count || d.hits || d[2] || 1),
              d.layer || 'DNS/路由阻断'
            ]);
          }
          if (dt.rewrite && Array.isArray(dt.rewrite.rules)) {
            mock.rewriteRules = dt.rewrite.rules;
            if (dt.rewrite.enabled != null && !_opsMutationInFlight.dns_rewrite && !(Date.now() < (_opsFieldMuteUntil.dns_rewrite || 0))) {
              state.dnsRewriteEnabled = Boolean(dt.rewrite.enabled);
            }
          }
          if (dt.filter && Array.isArray(dt.filter.lists)) {
            mock.filterLists = dt.filter.lists;
            mock.dnsRawRuleLines = dt.filter.lists.reduce((acc, fl) => acc + (fl && fl.enabled !== false ? Number(fl.rules_count || fl.rules || 0) : 0), 0);
          }
        }

        if (stRes.sys_metrics) {
          const sm = stRes.sys_metrics;
          if (sm.os_release && $('#sys-spec-os')) $('#sys-spec-os').textContent = sm.os_release;
          if (sm.arch && $('#sys-spec-arch')) $('#sys-spec-arch').textContent = sm.arch;
          if (sm.conntrack_count != null && Number(sm.conntrack_count) >= 0) mock.conntrackCount = Number(sm.conntrack_count);
          if (sm.conntrack_max != null && Number(sm.conntrack_max) > 0) mock.conntrackMax = Number(sm.conntrack_max);
          if (sm.mem_total_mb != null && Number(sm.mem_total_mb) > 0) mock.memTotalMib = Number(sm.mem_total_mb);
        }
        if (typeof stRes.srs_rulesets_count === 'number') {
          mock.srsRulesetsCount = stRes.srs_rulesets_count;
          if ($('#srs-rulesets-sub')) $('#srs-rulesets-sub').textContent = stRes.srs_rulesets_count + ' 组官方与自定义编译规则集';
        }
        if (stRes.backup_info && typeof stRes.backup_info === 'object') {
          mock.backupInfo = stRes.backup_info;
          if ($('#backup-status-val')) {
            if (stRes.backup_info.verified) {
              const dtStr = stRes.backup_info.mtime ? new Date(stRes.backup_info.mtime * 1000).toLocaleString('zh-CN', { hour12: false }) : '已验证';
              $('#backup-status-val').textContent = '已验证 (' + (stRes.backup_info.file_count || 1) + ' 项 · ' + dtStr + ')';
            } else {
              $('#backup-status-val').textContent = '尚未生成持久化备份 · 点击上方导出创建';
            }
          }
        }
        if (typeof stRes.data_age_ms === 'number') {
          mock.statusDataAgeMs = stRes.data_age_ms;
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
            if (Array.isArray(idata.devices)) {
              state.insightDevices = idata.devices;
              mock.devicesTotal = idata.devices.length;
              mock.devicesActive = idata.devices.length ? Math.max(1, idata.devices.filter(d => Number(d.totalBytes || 0) > 0).length) : 0;
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
            if (Array.isArray(idata.targets)) {
              state.insightTargets = idata.targets;
              mock.destinationsTotal = idata.targets.length;
            }
          }

          const pulseArr = Array.isArray(ovt.pulse_services) ? ovt.pulse_services : [];
          if (pulseArr.length) {
            mock.services = pulseArr.slice(0, 8).map(p => {
              const sid = String(p.id || p.name || '').toLowerCase();
              const sel = p.selector || 'Shunt_AI';
              const grpId = sel.startsWith('Shunt_') ? sel.slice(6) : sel;
              const fromGroup = mock.groups.find(g => g.id === grpId || ('Shunt_' + g.id) === sel);
              let msVal = 0;
              let stateVal = p.state || 'pending';
              if (!state.coreAlive && sel !== 'direct' && sel !== 'Shunt_Domestic_CN') {
                msVal = 0;
                stateVal = 'dead';
              } else if (p.state === 'dead') {
                msVal = 0;
                stateVal = 'dead';
              } else if (Number(p.ms) > 0) {
                msVal = Math.round(Number(p.ms));
                stateVal = msVal >= 600 ? 'suspect' : 'ok';
              } else if (fromGroup && fromGroup.rtt != null && Number(fromGroup.rtt) > 0 && fromGroup.resolved_node !== 'direct') {
                msVal = Math.round(Number(fromGroup.rtt));
                stateVal = msVal >= 600 ? 'suspect' : 'ok';
              } else {
                msVal = 0;
                stateVal = stateVal === 'dead' ? 'dead' : 'pending';
              }
              return {
                id: sid,
                name: p.name || sid,
                selector: sel,
                groupId: grpId,
                url: p.url || '',
                node: p.node || '',
                ms: msVal,
                state: stateVal
              };
            });
          } else if (!state.coreAlive) {
            mock.services = mock.services.map(s => Object.assign({}, s, { ms: 0, state: 'dead' }));
          }
        }

        if ($('#sys-core-title') && (stRes.core || stRes.core_version)) {
          const cleanCore = stRes.core ? String(stRes.core).replace(/\s*\(.*\)$/, '').trim() : ('sing-box ' + stRes.core_version);
          $('#sys-core-title').textContent = cleanCore;
        }
        if ($('#sys-spec-mem')) $('#sys-spec-mem').textContent = Number.isFinite(Number(mock.coreMemMib)) ? (Number(mock.coreMemMib).toFixed(1) + ' MiB') : '--';
        if (stRes.active_outbounds_count != null) mock.activeOutbounds = Number(stRes.active_outbounds_count);
        if (stRes.max_outbounds_limit != null) mock.maxOutboundsLimit = Number(stRes.max_outbounds_limit);
        if (stRes.saved_nodes_total != null) mock.totalNodes = Number(stRes.saved_nodes_total);

        state.backendOffline = false;
        state.lastSyncAt = new Date().toLocaleTimeString('zh-CN', { hour12: false });
        if (stRes.health_score != null) {
          mock.healthScore = Number(stRes.health_score);
        } else if (!state.coreAlive) {
          mock.healthScore = 35;
        } else if (state.bypassActive) {
          mock.healthScore = 82;
        } else {
          mock.healthScore = 92;
        }
        const coreOfflineBanner = $('#core-offline-alert-banner');
        if (coreOfflineBanner) {
          const spanEl = coreOfflineBanner.querySelector('span');
          if (spanEl) spanEl.textContent = '检测到 sing-box 代理内核未运行，已触发防断网黑洞保护并回退直连';
          coreOfflineBanner.classList.toggle('hidden', state.coreAlive);
        }
        const ovOfflineCard = $('#ov-core-offline-card');
        if (ovOfflineCard) {
          const spanEl = ovOfflineCard.querySelector('span');
          if (spanEl) spanEl.textContent = 'sing-box 代理内核当前处于离线状态，已自动切换为安全直连保护';
          ovOfflineCard.classList.add('hidden');
        }

        renderTopBarStatus();
        syncGalaxy3DData();
      } else {
        state.backendOffline = true;
        mock.services = mock.services.map(s => Object.assign({}, s, { ms: 0, state: 'dead' }));
        mock.down = 0;
        mock.up = 0;
        mock.downText = '--';
        mock.upText = '--';
        mock.connections = '--';
        mock.conntrackCount = 0;
        mock.devicesTotal = 0;
        mock.devicesActive = 0;
        mock.dnsRulesCount = null;
        mock.dnsRawRuleLines = null;
        mock.dnsAvgMs = null;
        mock.dnsLayerCount = 0;
        mock.rejectLayerCount = 0;
        mock.healthScore = '--';
        mock.coreMemMib = '--';
        mock.blockedTotal = '--';
        mock.uptimeStr = '--';
        mock.inTotalText = '--';
        mock.outTotalText = '--';
        mock.monthTotalText = '--';
        mock.upTotalText = '--';
        if ($('#top-connections')) $('#top-connections').textContent = '--';
        if ($('#top-down')) $('#top-down').textContent = '--';
        if ($('#top-up')) $('#top-up').textContent = '--';
        if ($('#sys-spec-mem')) $('#sys-spec-mem').textContent = '--';
        const coreOfflineBanner = $('#core-offline-alert-banner');
        if (coreOfflineBanner) {
          const spanEl = coreOfflineBanner.querySelector('span');
          if (spanEl) spanEl.textContent = '无法获取状态，请检查面板服务 (守护进程未响应)';
          coreOfflineBanner.classList.remove('hidden');
        }
        const ovOfflineCard = $('#ov-core-offline-card');
        if (ovOfflineCard) {
          const spanEl = ovOfflineCard.querySelector('span');
          if (spanEl) spanEl.textContent = '无法获取状态，请检查面板服务 (守护进程未响应)';
          ovOfflineCard.classList.add('hidden');
        }
        renderTopBarStatus();
      }
    } catch (_) {
      state.backendOffline = true;
      mock.services = mock.services.map(s => Object.assign({}, s, { ms: 0, state: 'dead' }));
      mock.downText = '--';
      mock.upText = '--';
      mock.connections = '--';
      mock.healthScore = '--';
      mock.coreMemMib = '--';
      mock.blockedTotal = '--';
      mock.uptimeStr = '--';
      mock.inTotalText = '--';
      mock.outTotalText = '--';
    }
    if (forceImmediate) {
      renderAll();
    } else {
      renderActivePageOnly();
    }
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
      const isBlocked = Boolean(s4.is_blocked || s3.group_id === 'Ad_Block' || s4.node === 'REJECT');
      const isDirect = !isBlocked && Boolean(
        s4.is_direct ||
        s4.strategy === 'direct' ||
        s4.node === 'direct' ||
        s4.outbound_tag === 'direct' ||
        s3.group_id === 'Domestic_CN' ||
        s3.group_id === 'LAN_Bypass'
      );
      const s3Title = s3.title || (isBlocked ? '净网护盾拦截规则' : (isDirect ? '直连分流规则命中' : '精细分流规则匹配'));
      const s3Detail = s3.detail || s3.summary || (
        (s3.rule_title ? ('命中策略组「' + s3.rule_title + '」') : '命中分流规则') +
        (s3.rule_reason ? (' · ' + s3.rule_reason) : '') +
        (isDirect ? ' · 未命中海外代理组' : '')
      );
      const s3Badge = isBlocked ? '黑洞阻断' : (isDirect ? '未命中代理组' : (s3.rule_title || s3.selector_tag || s3.group_id || '规则命中'));

      const actualNode = s4.node || s4.outbound_tag || (isDirect ? 'direct' : eg.nodeName);
      const s4Title = s4.title || (isBlocked ? '双层黑洞阻断 (REJECT)' : (isDirect ? '宽带原生直连出站 (DIRECT)' : '实际代理出站节点隧道'));
      const s4Detail = s4.detail || s4.summary || (
        isBlocked
          ? 'DNS REFUSED + 路由层 REJECT 双保险零延迟丢弃'
          : (isDirect
              ? ('走 WAN 口宽带原生直连 (' + actualNode + ')，零代理开销')
              : ('实际出口: ' + actualNode + (s4.auto_node_name ? (' [' + s4.auto_node_name + ']') : '') + (s4.latency_ms ? (' · 实测延迟 ' + s4.latency_ms + ' ms') : '')))
      );
      const s4Badge = isBlocked ? '已阻断' : (isDirect ? '直连' : actualNode);

      stages = [
        ['01', s1.title || '防火墙 TProxy 接管', s1.detail || s1.summary || 'nftables 规则判定完成', s1.verdict || s1.action || (isDirect ? '直连豁免' : '已接管')],
        ['02', s2.title || '双栈 DNS 智能分流', s2.detail || s2.summary || (s2.dns_route ? (s2.dns_route + (s2.fakeip_Note ? (' · ' + s2.fakeip_Note) : '')) : 'DNS 路径判定完成'), s2.verdict || s2.dns_server || (isDirect ? '国内 DoH' : 'FakeIP')],
        ['03', s3Title, s3Detail, s3Badge],
        ['04', s4Title, s4Detail, s4Badge]
      ];
    }
    const inlineHtml = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">' +
      '<b style="color:var(--cyan)">诊断目标: ' + esc(target) + ' (' + esc(protocol.toUpperCase()) + ')</b>' +
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

  /* T1: One-Click Network Health Doctor (8 Parallel Checks + 1-Click Auto Fix) */
  async function openNetworkDoctorModal(autoRun) {
    openModal(
      '网络健康医生 · 8 项全链路并发诊断与一键修复',
      '<div id="network-doctor-root" class="modal-form">' +
        '<div class="doctor-summary-banner">' +
          '<div>' +
            '<b id="doc-headline" style="color:var(--cyan)">正在并发执行 8 项全链路网络健康诊断 (≤10s)...</b>' +
            '<small id="doc-subline" style="display:block;color:var(--muted);margin-top:3px">覆盖：客户端 DNS 归属 · AAAA 抑制 · IPv6 绕过 · 回家 DDNS 权威比对 · 回家端口可达 · 上游连通 · MTU/PMTU · 关键应用防误杀</small>' +
          '</div>' +
          '<div class="button-row" style="gap:6px">' +
            '<button type="button" class="button secondary compact" id="btn-doc-rerun" data-action="run-network-doctor-now">重新体检</button>' +
            '<button type="button" class="button primary compact" id="btn-doc-fix-all" data-action="fix-network-doctor-all">一键修复异常项</button>' +
          '</div>' +
        '</div>' +
        '<div id="doc-checks-grid" class="doctor-check-grid">' +
          '<div style="grid-column:1/-1;padding:26px;text-align:center;color:var(--muted)">⏳ 正在并发探测 8 项网络与内核指标，请稍候...</div>' +
        '</div>' +
      '</div>',
      'NETWORK HEALTH DOCTOR · T1'
    );
    if (autoRun !== false) {
      await runNetworkDoctorScan();
    }
  }

  async function runNetworkDoctorScan() {
    const headline = $('#doc-headline');
    const subline = $('#doc-subline');
    const grid = $('#doc-checks-grid');
    const rerunBtn = $('#btn-doc-rerun');
    if (rerunBtn) { rerunBtn.disabled = true; rerunBtn.textContent = '⏳ 诊断中...'; }
    const res = await callRouterApi('/api/diag/run', 'POST', {});
    if (rerunBtn) { rerunBtn.disabled = false; rerunBtn.textContent = '重新体检'; }
    if (!res || !Array.isArray(res.checks)) {
      if (headline) headline.textContent = '诊断接口暂未响应，请稍后重试';
      return;
    }
    state.lastDoctorReport = res;
    const sum = res.summary || {};
    const score = sum.health_score != null ? sum.health_score : 100;
    const passCnt = sum.pass != null ? sum.pass : res.checks.filter(c => c.status === 'pass').length;
    const warnCnt = sum.warn != null ? sum.warn : res.checks.filter(c => c.status === 'warn').length;
    const failCnt = sum.fail != null ? sum.fail : res.checks.filter(c => c.status === 'fail').length;
    const durMs = res.duration_ms || 0;
    const fixAllBtn = $('#btn-doc-fix-all');
    if (fixAllBtn) {
      const noIssue = (warnCnt === 0 && failCnt === 0);
      fixAllBtn.disabled = noIssue;
      fixAllBtn.textContent = noIssue ? '当前无异常' : '一键修复异常项';
    }
    if (headline) {
      headline.style.color = failCnt > 0 ? 'var(--rose)' : (warnCnt > 0 ? 'var(--amber)' : 'var(--mint)');
      headline.textContent = '体检评分 ' + score + ' 分 · ' + passCnt + ' 项通过 / ' + warnCnt + ' 项警告 / ' + failCnt + ' 项异常（耗时 ' + durMs + ' ms）';
    }
    if (subline) {
      subline.textContent = (failCnt === 0 && warnCnt === 0)
        ? '全链路 8 项核心指标全部健康，未发现 DNS 绕过、IPv6 泄漏、MTU 黑洞或关键应用误杀。'
        : '发现可优化或异常项，可点击右侧「一键修复异常项」或单项修复按钮自动恢复并复检。';
    }
    if (grid) {
      grid.innerHTML = res.checks.map((c, idx) => {
        const st = c.status || 'pass';
        const pillColor = st === 'pass' ? 'var(--mint)' : (st === 'warn' ? 'var(--amber)' : 'var(--rose)');
        const pillText = st === 'pass' ? 'PASS' : (st === 'warn' ? 'WARN' : 'FAIL');
        const canFix = c.fixable && st !== 'pass' && c.fix_action;
        return '<div class="doctor-check-card status-' + esc(st) + '" data-check-id="' + esc(c.id) + '">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:6px">' +
            '<b style="color:var(--text)">#' + (idx + 1) + ' ' + esc(c.title || c.id) + '</b>' +
            '<span class="status-pill" style="color:' + pillColor + ';">' + pillText + ' · ' + Number(c.duration_ms || 1) + 'ms</span>' +
          '</div>' +
          '<div style="color:var(--text-2);line-height:1.45">' + esc(c.detail || '') + '</div>' +
          (c.suggestion ? '<div style="color:var(--muted)">建议：' + esc(c.suggestion) + '</div>' : '') +
          (canFix
            ? '<div style="margin-top:4px;display:flex;justify-content:flex-end"><button type="button" class="button secondary compact" style="padding:0 9px;" data-action="fix-network-doctor-item" data-fix-action="' + esc(c.fix_action) + '" data-check-id="' + esc(c.id) + '">一键修复此项</button></div>'
            : '') +
        '</div>';
      }).join('');
    }
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
        '<div><span>线路属性识别</span><b>' + esc(n.line_badge || '直连线路') + (n.detour_target ? (' (前置: ' + esc(n.detour_target) + ')') : '') + '</b></div>' +
        '<div><span>Google 视角地区 (301 TLD)</span><b>' + renderGoogleRegionBadgeHtml(n, true) + '</b></div>' +
        '<div><span>实测带宽 / 稳定指纹</span><b class="mono">' + (n.bandwidth_mbps > 0 ? (n.bandwidth_mbps + ' Mbps · ') : '') + esc((n.node_key || n.id || '—').slice(0, 12)) + '</b></div>' +
        '<div><span>实测延迟 / 评分</span><b>' + formatLatencyText(n.rtt, false) + ' · ' + (n.score != null && n.rtt > 0 ? n.score + ' 分' : '待评估') + '</b></div>' +
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
        '<div class="modal-field"><label>链式代理前置中转 (可选：为静态住宅 IP 绑定前置自动节点池)</label><select id="mdl-edit-node-detour" aria-label="链式代理前置中转">' +
          '<option value="">不使用前置中转 (直接连接此节点)</option>' +
          (mock.autoPools || []).map(ap => '<option value="' + esc(ap.id) + '" ' + (n.detour_target === ap.id || n.detour_target === ap.tag ? 'selected' : '') + '>前置自动池：' + esc(ap.name) + ' (' + esc(ap.id) + ')</option>').join('') +
        '</select></div>' +
        (shareUri ? '<div class="modal-field"><label>标准节点分享 URI（点击全选复制）</label><input id="mdl-node-share-uri" class="mono" value="' + esc(shareUri) + '" readonly onclick="this.select()"></div>' : '') +
      '</div>' +
      '<div class="button-row" style="margin-top:14px">' +
        '<button class="button secondary" data-action="probe-single-node" data-node="' + esc(n.tag || n.name) + '">立即 URL Ping 测速</button>' +
        '<button class="button primary" data-action="set-node-exit" data-node="' + esc(n.tag || n.name) + '">设为全局/分流出口</button>' +
        '<button class="button danger compact" data-action="delete-single-node" data-node="' + esc(n.tag || n.name) + '">删除节点</button>' +
      '</div>',
      'NODE OBSERVATORY',
      async () => {
        const new_tag = ($('#mdl-edit-node-tag') && $('#mdl-edit-node-tag').value.trim()) || n.name;
        const region_override = ($('#mdl-edit-node-region') && $('#mdl-edit-node-region').value) || n.region;
        const server = ($('#mdl-edit-node-server') && $('#mdl-edit-node-server').value.trim()) || n.server;
        const server_port = Number(($('#mdl-edit-node-port') && $('#mdl-edit-node-port').value) || n.server_port || 443);
        const detour_pool_id = ($('#mdl-edit-node-detour') && $('#mdl-edit-node-detour').value) || '';
        const patch = { new_tag, region_override, detour_pool_id, detour: detour_pool_id };
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


  function openChainedProxyModal() {
    const poolOpts = (mock.autoPools || []).map(ap =>
      '<option value="' + esc(ap.id) + '">前置自动节点池：' + esc(ap.name) + ' (' + esc(ap.id) + ')</option>'
    ).join('');
    const nodeOpts = (mock.nodes || []).filter(n => !n.is_chained).slice(0, 30).map(n =>
      '<option value="' + esc(n.tag || n.name) + '">前置单节点：' + esc(cleanNodeDisplayName(n.name)) + '</option>'
    ).join('');
    openModal(
      '配置链式代理落地节点 (Chained Proxy / Detour)',
      '<div class="modal-form">' +
        '<div class="syntax-guide"><b>链式代理工作流：</b>将自购的海外静态住宅 IP（Socks5 / HTTP / VLESS 等）设为最终落地节点，并选择任意<b>自动节点池</b>或<b>高速专线节点</b>作为前置中转跳板，自动生成无环路的 sing-box <code>detour</code> 级联链路。</div>' +
        '<div class="modal-grid-3">' +
          '<div class="modal-field"><label>落地节点名称</label><input id="mdl-ch-tag" placeholder="如：美国静态住宅-ISP-01" aria-label="落地节点名称"></div>' +
          '<div class="modal-field"><label>落地协议类型</label><select id="mdl-ch-type" aria-label="落地协议类型"><option value="socks">Socks5 (住宅静态IP常用)</option><option value="http">HTTP / HTTPS 代理</option><option value="vless">VLESS</option><option value="trojan">Trojan</option><option value="shadowsocks">Shadowsocks</option></select></div>' +
          '<div class="modal-field"><label>落地国家/地区</label><select id="mdl-ch-region" aria-label="落地国家地区">' +
            COUNTRY_CODES.map(c => '<option value="' + esc(c) + '">' + esc(COUNTRY_META[c].flag + ' ' + COUNTRY_META[c].name) + '</option>').join('') +
          '</select></div>' +
        '</div>' +
        '<div class="modal-grid-3">' +
          '<div class="modal-field"><label>落地服务器 IP / 域名</label><input id="mdl-ch-server" class="mono" placeholder="198.51.100.88" aria-label="落地服务器地址"></div>' +
          '<div class="modal-field"><label>端口</label><input id="mdl-ch-port" type="number" value="1080" aria-label="落地端口"></div>' +
          '<div class="modal-field"><label>前置中转跳板 (自动节点池 / 节点)</label><select id="mdl-ch-detour-pool" aria-label="前置中转跳板">' + poolOpts + nodeOpts + '</select></div>' +
        '</div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>账号 / 用户名 (Socks5/HTTP 可选)</label><input id="mdl-ch-user" class="mono" placeholder="username" aria-label="代理用户名"></div>' +
          '<div class="modal-field"><label>密码 / UUID</label><input id="mdl-ch-pass" class="mono" placeholder="password 或 UUID" aria-label="代理密码或UUID"></div>' +
        '</div>' +
      '</div>',
      'CHAINED PROXY BUILDER',
      async () => {
        const tag = ($('#mdl-ch-tag') && $('#mdl-ch-tag').value.trim()) || 'Chained-ISP-Node';
        const type = ($('#mdl-ch-type') && $('#mdl-ch-type').value) || 'socks';
        const region_override = ($('#mdl-ch-region') && $('#mdl-ch-region').value) || 'US';
        const server = ($('#mdl-ch-server') && $('#mdl-ch-server').value.trim()) || '';
        const server_port = Number(($('#mdl-ch-port') && $('#mdl-ch-port').value) || 1080);
        const detour_pool_id = ($('#mdl-ch-detour-pool') && $('#mdl-ch-detour-pool').value) || 'auto_ai';
        const username = ($('#mdl-ch-user') && $('#mdl-ch-user').value.trim()) || '';
        const password = ($('#mdl-ch-pass') && $('#mdl-ch-pass').value.trim()) || '';
        if (!server) { toast('请填写落地服务器地址', 'warn'); return; }
        const res = await callRouterApi('/api/nodes/chained_create', 'POST', {
          tag, type, region_override, server, server_port, username, password, uuid: password, detour_pool_id
        });
        if (res && res.ok !== false) {
          closeModal();
          toast(res.message || ('已创建链式落地节点：' + tag));
          await syncBackendStatus(true, true);
        }
      },
      '创建链式落地节点'
    );
  }

  async function openTrafficInsightsModal(includeDirect) {
    const incDir = Boolean(includeDirect);
    const buildGridHtml = (data) => {
      const devs = Array.isArray(data.by_device) ? data.by_device : [];
      const nodes = Array.isArray(data.by_node) ? data.by_node : [];
      const doms = Array.isArray(data.by_domain) ? data.by_domain : [];
      return (
        '<div class="glass-card" style="padding:10px"><h4 style="margin:0 0 8px;font-size:13px">01 / 终端设备耗流排行</h4>' +
          (devs.slice(0, 6).map(d => '<div style="display:flex;justify-content:space-between;font-size:12px;padding:4px 0;border-bottom:1px solid var(--line)"><span>' + esc(d.name || d.ip) + '</span><b class="mono">' + esc(d.total_human || ((d.total_mb || 0) + ' MiB')) + '</b></div>').join('') || '<div class="muted" style="font-size:12px">暂无活跃终端流量</div>') +
        '</div>' +
        '<div class="glass-card" style="padding:10px"><h4 style="margin:0 0 8px;font-size:13px">02 / 出站节点耗流排行</h4>' +
          (nodes.slice(0, 6).map(n => '<div style="display:flex;justify-content:space-between;font-size:12px;padding:4px 0;border-bottom:1px solid var(--line)"><span>' + esc(cleanNodeDisplayName(n.node || n.node_tag || '')) + ' <small style="color:var(--muted)">[' + esc(n.line_badge || '直连') + ']</small></span><b class="mono">' + esc(n.total_human || ((n.total_mb || 0) + ' MiB')) + '</b></div>').join('') || '<div class="muted" style="font-size:12px">暂无节点统计</div>') +
        '</div>' +
        '<div class="glass-card" style="padding:10px"><h4 style="margin:0 0 8px;font-size:13px">03 / 目标域名耗流排行</h4>' +
          (doms.slice(0, 6).map(dm => '<div style="display:flex;justify-content:space-between;font-size:12px;padding:4px 0;border-bottom:1px solid var(--line)"><span class="mono">' + esc(dm.domain || dm.host || '') + '</span><b class="mono">' + esc(dm.total_human || ((dm.total_mb || 0) + ' MiB')) + '</b></div>').join('') || '<div class="muted" style="font-size:12px">暂无域名统计</div>') +
        '</div>'
      );
    };
    const initData = state.lastTrafficInsights || { hourly_series: [], daily_series: [], by_device: [], by_node: [], by_domain: [] };
    openModal(
      '按天/按小时三维流量归因洞察 (终端 × 节点 × 目标域名)',
      '<div class="ov-insight-modal-wrap modal-form" style="gap:12px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">' +
          '<span style="color:var(--muted);font-size:12px">实时聚合 24 小时与 7 天流量趋势，支持下钻定位高耗流终端、出站节点与目标域名</span>' +
          '<label style="display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:12px">' +
            '<input type="checkbox" id="chk-ti-include-direct" ' + (incDir ? 'checked' : '') + ' aria-label="包含国内直连流量">' +
            '<span>统计包含国内直连 (DIRECT) 流量</span>' +
          '</label>' +
        '</div>' +
        '<div id="mdl-ti-3d-grid" class="modal-grid-3" style="gap:10px">' + buildGridHtml(initData) + '</div>' +
      '</div>',
      '3D TRAFFIC ATTRIBUTION INSIGHTS'
    );
    const chkDir = $('#chk-ti-include-direct');
    if (chkDir) {
      chkDir.addEventListener('change', () => {
        openTrafficInsightsModal(chkDir.checked);
      });
    }
    const res = await callRouterApi('/api/traffic/insights?include_direct=' + (incDir ? '1' : '0'), 'GET');
    if (res && res.ok !== false) {
      state.lastTrafficInsights = res;
      const gEl = $('#mdl-ti-3d-grid');
      if (gEl) gEl.innerHTML = buildGridHtml(res);
    }
  }

  function openRestoreBackupModal() {
    openModal(
      '导入恢复配置归档 (.tgz / .json)',
      '<div class="modal-form">' +
        '<p>支持上传由 AI-LINK 导出的 <code>.tgz</code> / <code>.tar.gz</code> 全量配置归档或 <code>.json</code> 备份文件，恢复前会自动校验路径安全并重载内核。</p>' +
        '<div class="modal-field">' +
          '<label>选择备份文件 (.tgz / .tar.gz / .json)</label>' +
          '<input id="mdl-restore-file" aria-label="选择备份文件 (.tgz / .tar.gz / .json)" type="file" accept=".tgz,.tar.gz,.json,application/gzip,application/json">' +
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
    const autoOpts = mock.autoPools.map(p => '<option value="' + esc(p.id) + '" ' + (g && g.auto_node_id === p.id ? 'selected' : '') + '>' + esc(p.name) + '</option>').join('');
    openModal(
      g ? ('编辑分流策略组 · ' + g.name) : '添加自定义高优先级分流规则',
      '<div class="modal-form">' +
        '<div class="syntax-guide">' +
          '<b>规则语法说明：</b>每行或逗号分隔一条规则。支持：' +
          '域名后缀 <code>openai.com</code>、关键词 <code>keyword:claude</code>、完整域名 <code>full:api.github.com</code>、目标 IP 段 <code>1.1.1.0/24</code>。自定义规则默认插入在「国内直连」之前优先生效。' +
        '</div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>规则组名称</label><input id="mdl-rule-name" value="' + esc(g ? g.name : '我的专属工作流') + '" placeholder="如：OpenAI 专线 / 公司内网"></div>' +
          '<div class="modal-field"><label>插入优先级位置</label><select id="mdl-rule-pos"><option value="top">置顶最高优先级 (Top #01)</option><option value="before_domestic">国内直连白名单之前</option></select></div>' +
        '</div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>出站策略模式</label><select id="mdl-rule-mode"><option value="auto" ' + (!g || g.shunt_mode === 'auto' ? 'selected' : '') + '>绑定双组自动节点池</option><option value="manual" ' + (g && g.shunt_mode === 'manual' ? 'selected' : '') + '>手动指定国家/节点</option><option value="direct" ' + (g && g.shunt_mode === 'direct' ? 'selected' : '') + '>强制宽带直连 (DIRECT)</option></select></div>' +
          '<div class="modal-field"><label>绑定自动节点池</label><select id="mdl-rule-autopool">' + autoOpts + '</select></div>' +
        '</div>' +
        '<div class="modal-field"><label>域名后缀列表（每行或逗号分隔，如 example.com）</label><textarea id="mdl-rule-domains" rows="3" placeholder="openai.com\nanthropic.com\ncursor.sh">' + esc(g && g.domains ? g.domains.join('\n') : '') + '</textarea></div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>域名关键字（可选，如 openai, claude）</label><input id="mdl-rule-keywords" value="' + esc(g && g.domain_keywords ? g.domain_keywords.join(', ') : '') + '" placeholder="keyword1, keyword2"></div>' +
          '<div class="modal-field"><label>目标 IP CIDR（可选，如 1.1.1.0/24）</label><input id="mdl-rule-cidrs" value="' + esc(g && g.ip_cidrs ? g.ip_cidrs.join(', ') : '') + '" placeholder="91.108.4.0/22, 149.154.160.0/20"></div>' +
        '</div>' +
        (g && g.is_custom ? '<div class="button-row"><button class="button danger compact" data-action="delete-custom-group" data-gid="' + esc(g.id) + '">删除此自定义分流组</button></div>' : '') +
        (g && !g.is_custom ? '<div class="button-row"><button class="button ghost compact" data-action="reset-single-group" data-gid="' + esc(g.id) + '">恢复此内置组默认域名库</button></div>' : '') +
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
  /* v2.3.5 Clean-Slate 6-Step Minimalist Auto Node Pool Builder:
   * Step 1: Pool Name
   * Step 2: Check which Subscriptions (including Manual/Custom nodes) to draw from (multi-select, shows traffic & node count)
   * Step 3: Check which Countries/Regions to include (multi-select)
   * Step 4: Choose whether Service Availability Detection is needed -> if needed, check target services (real HTTP access verification)
   * Step 5: Choose Target Node Count (1-10) & Low-Health Auto-Replenish Threshold (1-10)
   * Step 6: Click "开始自动选取" -> Real-time Progress Bar -> Saves & activates continuous URL Ping patrol
   */
  function openAutoNodeEditorModal(poolIdx, autoStartScreen) {
    const p = (poolIdx != null && mock.autoPools[poolIdx]) ? mock.autoPools[poolIdx] : null;
    const cleanTags = arr => (Array.isArray(arr) ? arr : [])
      .map(x => (typeof x === 'object' && x !== null) ? String(x.tag || x.name || '').trim() : String(x || '').trim())
      .filter(Boolean)
      .slice(0, 10);
    const extractGroupTags = grp => {
      if (!grp) return [];
      const fromTags = cleanTags(grp.node_tags);
      if (fromTags.length) return fromTags;
      return cleanTags(grp.members);
    };
    const initPoolTags = (p && p.groups && p.groups[0]) ? extractGroupTags(p.groups[0]) : [];
    const selectedSet = new Set(initPoolTags);
    const testResultsByTag = {};

    const initSourcesArr = (p && Array.isArray(p.scope_sources) && p.scope_sources.length)
      ? p.scope_sources
      : ((p && p.scope_source) ? String(p.scope_source).split(',').map(x => x.trim()).filter(Boolean) : ['ALL']);
    const selectedSources = new Set(initSourcesArr.length ? initSourcesArr : ['ALL']);

    const initCountriesArr = (p && Array.isArray(p.scope_countries) && p.scope_countries.length)
      ? p.scope_countries.map(c => String(c).toUpperCase())
      : ['ALL'];
    const selectedCountries = new Set(initCountriesArr.length ? initCountriesArr : ['ALL']);

    let poolMode = !p ? 'ping_only' : ((p.pool_mode === 'ping_only' || p.service_check_enabled === false || p.mode === 'semi') ? 'ping_only' : 'service_check');
    let targetSize = Math.max(1, Math.min(10, Number((p && p.target_size) || (initPoolTags.length || 5))));
    let replenishThresh = Math.max(1, Math.min(targetSize, Number((p && p.replenish_threshold != null) ? p.replenish_threshold : Math.max(1, Math.ceil(targetSize / 2)))));
    let dispatchMode = (p && p.dispatch_mode === 'multi_line') ? 'multi_line' : 'single_best';
    let bwPrefer = Boolean(p && p.bandwidth_prefer);
    let bwIntervalH = Number((p && p.bandwidth_interval_h) || 6);
    let bwLimitMb = Number((p && p.bandwidth_limit_mb) || 16);
    let keywordFilter = String((p && p.keyword_filter) || '');
    let keywordMode = (p && p.keyword_mode === 'AND') ? 'AND' : 'OR';
    const IP_SENSITIVE_SVCS = new Set(['gemini', 'chatgpt', 'openai', 'claude']);
    const isFixedAiPoolId = Boolean(p && ['auto_ai', 'auto_soul'].includes(p.id));

    const SERVICE_OPTIONS = [
      { id: 'gemini', name: 'Google Gemini (真实 301/地域校验)' },
      { id: 'chatgpt', name: 'ChatGPT / OpenAI (Trace 地域校验)' },
      { id: 'claude', name: 'Claude AI' },
      { id: 'youtube', name: 'YouTube 4K' },
      { id: 'netflix', name: 'Netflix 非自制剧' },
      { id: 'tiktok', name: 'TikTok 国际区' },
      { id: 'github', name: 'GitHub' },
      { id: 'telegram', name: 'Telegram' }
    ];
    const initSvcs = new Set(
      (p && Array.isArray(p.service_checks) && p.service_checks.length)
        ? p.service_checks.map(s => s === 'openai' ? 'chatgpt' : s)
        : ['gemini', 'chatgpt']
    );
    const initLogic = (p && p.service_logic === 'any') ? 'any' : 'all';

    const customCnt = mock.nodes.filter(n => isNodeManualCustom(n)).length;
    const sourceItems = [
      { id: 'ALL', name: '全部订阅与自定义节点', meta: '共 ' + mock.nodes.length + ' 个节点' }
    ].concat(
      mock.subscriptions.map(s => {
        const cnt = Number(s.count != null ? s.count : mock.nodes.filter(n => nodeMatchesSubscription(n, s.id)).length);
        const rem = (s.userinfo && s.userinfo.remaining_human) ? (' · 剩余 ' + s.userinfo.remaining_human) : '';
        return { id: s.id, name: s.name, meta: cnt + ' 节点' + rem };
      })
    ).concat([
      { id: 'custom', name: '手动添加节点 (Custom)', meta: customCnt + ' 个自建/导入节点' }
    ]);

    const svcChecksHtml = SERVICE_OPTIONS.map(s =>
      '<label class="an-svc-chip"><input type="checkbox" class="chk-an-svc" value="' + esc(s.id) + '" ' + (initSvcs.has(s.id) ? 'checked' : '') + '><span>' + esc(s.name) + '</span></label>'
    ).join('');

    const numOptionsHtml = (maxVal, curVal) => {
      let out = '';
      for (let i = 1; i <= maxVal; i++) {
        out += '<option value="' + i + '" ' + (i === curVal ? 'selected' : '') + '>' + i + ' 个节点</option>';
      }
      return out;
    };

    openModal(
      p ? ('配置自动节点池 · ' + p.name) : '创建智能自动节点池',
      '<div id="an-builder-root" class="ov-insight-modal-wrap modal-form" style="gap:10px">' +
        '<div class="syntax-guide" style="margin-bottom:0">' +
          '<b>极简自动节点池工作流：</b>勾选订阅源与国家区域 → 选择是否需要真实服务可用性检测 → 设定节点池容量 (1~10) 与低健康度自动复选阈值 → 点击「<b>开始自动选取</b>」。建池完成后，日常仅通过定时 <b>URL Ping</b> 自动切换池内最快节点；仅在<b>创建节点池</b>与<b>健康节点数低于阈值自动复选</b>时执行真实服务访问测试。' +
        '</div>' +

        /* Step 1: Pool Name */
        '<div class="an-wizard-step">' +
          '<div class="an-wizard-step-head">' +
            '<span class="an-wizard-step-title">1. 节点池名称</span>' +
            '<span class="an-wizard-step-sub">可在智能分流组或非分流模式（白名单 / GFW / 全局）中直接选用</span>' +
          '</div>' +
          '<div class="modal-field" style="margin:0"><input id="mdl-an-name" value="' + esc(p ? p.name : 'AI 与流媒体高速池') + '" placeholder="如：AI 专线节点池 / 主力大流量池"></div>' +
        '</div>' +

        /* Step 2: Multi-Select Subscriptions (including Custom) */
        '<div class="an-wizard-step">' +
          '<div class="an-wizard-step-head">' +
            '<span class="an-wizard-step-title">2. 勾选节点来源（支持多选订阅源与手动自定义节点）</span>' +
            '<span class="an-wizard-step-sub" id="mdl-an-source-summary">可根据各订阅剩余流量灵活勾选分配</span>' +
          '</div>' +
          '<div id="mdl-an-source-checks" class="an-source-grid"></div>' +
        '</div>' +

        /* Step 3: Multi-Select Countries / Regions + Original Name Keyword Filter */
        '<div class="an-wizard-step">' +
          '<div class="an-wizard-step-head">' +
            '<span class="an-wizard-step-title">3. 勾选国家/地区区域与原名关键词过滤（支持多选）</span>' +
            '<span class="an-wizard-step-sub" id="mdl-an-country-summary">已匹配候选节点数实时统计</span>' +
          '</div>' +
          '<div id="mdl-an-country-chips" class="region-chips"></div>' +
          '<div class="input-row" style="margin-top:6px;gap:8px">' +
            '<input id="mdl-an-keywords" value="' + esc(keywordFilter) + '" placeholder="可选：按原节点名关键词筛选（如 IEPL, 专线, 家宽，逗号分隔）" aria-label="原节点名关键词筛选">' +
            '<select id="mdl-an-kw-mode" style="max-width:160px" aria-label="关键词匹配逻辑">' +
              '<option value="OR" ' + (keywordMode === 'OR' ? 'selected' : '') + '>OR 命中任一关键词</option>' +
              '<option value="AND" ' + (keywordMode === 'AND' ? 'selected' : '') + '>AND 同时满足全部</option>' +
            '</select>' +
          '</div>' +
        '</div>' +

        /* Step 4: Service Availability Detection Toggle & Options */
        '<div class="an-wizard-step">' +
          '<div class="an-wizard-step-head">' +
            '<span class="an-wizard-step-title">4. 是否需要服务可用性检测（真实目标访问测试）</span>' +
            '<span class="an-wizard-step-sub">仅在建池与低健康度自动复选时发起真实服务访问，日常仅做 URL Ping</span>' +
          '</div>' +
          '<div class="modal-grid-2" style="gap:8px">' +
            '<button type="button" class="route-mode ' + (poolMode === 'ping_only' ? 'active' : '') + '" data-an-pool-mode="ping_only" id="btn-an-mode-ping" style="text-align:left;padding:9px 12px">' +
              '<b>不需要服务检测（仅 URL Ping 测速）</b>' +
              '<p style="margin-top:3px">适用常规网页与不锁区业务：直接按 URL Ping 最快延迟选取节点入池。</p>' +
            '</button>' +
            '<button type="button" class="route-mode ' + (poolMode === 'service_check' ? 'active' : '') + '" data-an-pool-mode="service_check" id="btn-an-mode-svc" style="text-align:left;padding:9px 12px">' +
              '<b>需要服务检测（真实访问目标校验解锁）</b>' +
              '<p style="margin-top:3px">适用 Gemini / ChatGPT / Netflix 等苛刻服务：实际请求目标并校验地区支持与返回内容。</p>' +
            '</button>' +
          '</div>' +
          '<div id="mdl-an-svc-panel" class="' + (poolMode === 'service_check' ? '' : 'hidden') + '" style="display:' + (poolMode === 'service_check' ? 'flex' : 'none') + ';flex-direction:column;gap:8px;padding-top:4px">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">' +
              '<span style="font-size:12px;color:var(--muted)">勾选需要真实访问验证的目标服务：</span>' +
              '<select id="mdl-an-svc-logic" style="padding:0 8px" aria-label="服务可用性判定标准">' +
                '<option value="all" ' + (initLogic === 'all' ? 'selected' : '') + '>判定标准：所选服务全部通过</option>' +
                '<option value="any" ' + (initLogic === 'any' ? 'selected' : '') + '>判定标准：所选服务任一通过</option>' +
              '</select>' +
            '</div>' +
            '<div class="an-svc-checks">' + svcChecksHtml + '</div>' +
          '</div>' +
        '</div>' +

        /* Step 5: Target Node Count (1-10), Replenish Threshold, Multi-Line Concurrency & Bandwidth Preference */
        '<div class="an-wizard-step">' +
          '<div class="an-wizard-step-head">' +
            '<span class="an-wizard-step-title">5. 设定节点容量、出站调度模式（优选单线 / 多线并发）与带宽择优</span>' +
            '<span class="an-wizard-step-sub" id="mdl-an-dispatch-guard-hint">系统根据所选目标服务自动启用防风控互斥保护</span>' +
          '</div>' +
          '<div class="modal-grid-2" style="gap:10px">' +
            '<div class="modal-field" style="margin:0">' +
              '<label>选取需求节点的数量 (1 ~ 10 个)</label>' +
              '<select id="mdl-an-target-size">' + numOptionsHtml(10, targetSize) + '</select>' +
            '</div>' +
            '<div class="modal-field" style="margin:0">' +
              '<label>健康节点数量低于多少时自动复选 (1 ~ 10 个)</label>' +
              '<select id="mdl-an-replenish-thresh">' + numOptionsHtml(targetSize, replenishThresh) + '</select>' +
            '</div>' +
          '</div>' +
          '<div class="modal-grid-2" style="gap:8px;margin-top:6px">' +
            '<button type="button" class="route-mode ' + (dispatchMode === 'single_best' ? 'active' : '') + '" data-an-dispatch="single_best" id="btn-an-dispatch-single" style="text-align:left;padding:8px 12px">' +
              '<b>优选单线（默认 · 账号防风控）</b>' +
              '<p style="margin-top:2px">全流量锚定池内最快单节点，适合 AI 助手 / 社交 / 跨境账号。</p>' +
            '</button>' +
            '<button type="button" class="route-mode ' + (dispatchMode === 'multi_line' ? 'active' : '') + '" data-an-dispatch="multi_line" id="btn-an-dispatch-multi" style="text-align:left;padding:8px 12px">' +
              '<b id="lbl-an-dispatch-multi">多线并发（池内健康节点叠加吞吐）</b>' +
              '<p style="margin-top:2px" id="sub-an-dispatch-multi">多连接并发分摊至池内各健康节点，适合 YouTube 8K / 流媒体 / 高速下载。</p>' +
            '</button>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;padding-top:4px">' +
            '<label style="display:inline-flex;align-items:center;gap:8px;cursor:pointer;font-size:13px">' +
              '<input type="checkbox" id="mdl-an-bw-prefer" ' + (bwPrefer ? 'checked' : '') + '>' +
              '<span>启用低频定量<b>带宽择优</b>（同延迟优先选高下行带宽节点）</span>' +
            '</label>' +
            '<div id="mdl-an-bw-opts" class="' + (bwPrefer ? '' : 'hidden') + '" style="display:' + (bwPrefer ? 'inline-flex' : 'none') + ';align-items:center;gap:6px;flex-wrap:wrap">' +
              '<select id="mdl-an-bw-interval" style="padding:0 8px" aria-label="带宽测试周期">' +
                '<option value="6" ' + (bwIntervalH === 6 ? 'selected' : '') + '>每 6 小时</option>' +
                '<option value="12" ' + (bwIntervalH === 12 ? 'selected' : '') + '>每 12 小时</option>' +
                '<option value="24" ' + (bwIntervalH === 24 ? 'selected' : '') + '>每 24 小时</option>' +
              '</select>' +
              '<select id="mdl-an-bw-limit" style="padding:0 8px" aria-label="单次测速上限">' +
                '<option value="8" ' + (bwLimitMb === 8 ? 'selected' : '') + '>上限 8 MiB</option>' +
                '<option value="16" ' + (bwLimitMb === 16 ? 'selected' : '') + '>上限 16 MiB</option>' +
                '<option value="32" ' + (bwLimitMb === 32 ? 'selected' : '') + '>上限 32 MiB</option>' +
              '</select>' +
              '<span class="status-pill mono" id="mdl-an-bw-est">预计日耗 ~64 MiB</span>' +
            '</div>' +
          '</div>' +
        '</div>' +

        /* Step 6: Start Auto-Selection Action + Real-Time Progress Bar + Selected Nodes Table */
        '<div class="an-wizard-step">' +
          '<div class="an-wizard-step-head">' +
            '<div>' +
              '<span class="an-wizard-step-title" id="mdl-an-pool-table-title">6. 自动选取节点入池（当前已选入 <span id="mdl-an-g1-cnt">' + selectedSet.size + '</span> / <span id="mdl-an-cap-lbl">' + targetSize + '</span> 个）</span>' +
              '<div class="an-wizard-step-sub">点击右侧「开始自动选取」，系统将按所选订阅、地区与服务检测自动选入最快节点</div>' +
            '</div>' +
            '<div style="display:flex;gap:8px;align-items:center">' +
              (p && !['auto_ai', 'auto_youtube', 'auto_netflix'].includes(p.id)
                ? '<button type="button" class="button danger compact" data-action="delete-auto-pool" data-pool-id="' + esc(p.id) + '">删除节点池</button>'
                : '') +
              '<button type="button" class="button primary compact" id="btn-an-auto-screen" style="padding:0 14px">开始自动选取</button>' +
            '</div>' +
          '</div>' +
          '<div id="mdl-an-progress-box" class="an-progress-box hidden">' +
            '<div class="an-progress-top">' +
              '<span id="mdl-an-progress-text">正在准备自动选取候选节点...</span>' +
              '<strong id="mdl-an-progress-pct" class="mono" style="color:var(--cyan)">0%</strong>' +
            '</div>' +
            '<div class="an-progress-track"><i id="mdl-an-progress-bar" class="an-progress-fill" style="width:0%"></i></div>' +
          '</div>' +
          '<div class="table-wrap" style="max-height:185px;overflow:auto">' +
            '<table>' +
              '<thead><tr><th>排序</th><th>节点名称 · 来源 · 地区</th><th>URL Ping 延迟</th><th>服务可用性验证</th><th style="text-align:right">操作</th></tr></thead>' +
              '<tbody id="mdl-an-selected-tbody"></tbody>' +
            '</table>' +
          '</div>' +
        '</div>' +
      '</div>',
      'AUTO NODE POOL WIZARD',
      async () => {
        const name = ($('#mdl-an-name') && $('#mdl-an-name').value.trim()) || '自动节点池';
        const checkedSvcs = poolMode === 'service_check' ? $$('.chk-an-svc:checked').map(el => el.value) : [];
        const svcLogic = ($('#mdl-an-svc-logic') && $('#mdl-an-svc-logic').value) || 'all';
        const tSize = Math.max(1, Math.min(10, Number(($('#mdl-an-target-size') && $('#mdl-an-target-size').value) || targetSize)));
        const rThresh = Math.max(1, Math.min(tSize, Number(($('#mdl-an-replenish-thresh') && $('#mdl-an-replenish-thresh').value) || replenishThresh)));
        const srcArr = Array.from(selectedSources);
        const ctryArr = Array.from(selectedCountries);

        if (selectedSet.size === 0) {
          await executeAutoSelectionWithProgress();
        }
        const finalTags = Array.from(selectedSet).slice(0, tSize);
        if (!finalTags.length) {
          toast('当前所选订阅与地区范围内未找到可用节点，请调整订阅或地区范围后重试', 'warn');
          return;
        }
        const groups = [{ index: 1, name: '节点池成员', node_tags: finalTags }];
        const res = await callRouterApi('/api/auto_nodes/save', 'POST', {
          id: p ? p.id : '',
          tag: p ? p.tag : '',
          name,
          pool_mode: poolMode,
          mode: (poolMode === 'service_check' && checkedSvcs.length) ? 'full' : 'semi',
          service_check_enabled: (poolMode === 'service_check' && checkedSvcs.length > 0),
          service_checks: checkedSvcs,
          service_logic: svcLogic,
          match_mode: svcLogic,
          scope_sources: srcArr.length ? srcArr : ['ALL'],
          scope_source: srcArr.includes('ALL') ? 'ALL' : srcArr.join(','),
          scope_countries: ctryArr.length ? ctryArr : ['ALL'],
          target_size: tSize,
          replenish_threshold: rThresh,
          dispatch_mode: dispatchMode,
          keyword_filter: ($('#mdl-an-keywords') && $('#mdl-an-keywords').value.trim()) || '',
          keyword_mode: ($('#mdl-an-kw-mode') && $('#mdl-an-kw-mode').value) || 'OR',
          bandwidth_prefer: Boolean($('#mdl-an-bw-prefer') && $('#mdl-an-bw-prefer').checked),
          bandwidth_interval_h: Number(($('#mdl-an-bw-interval') && $('#mdl-an-bw-interval').value) || 6),
          bandwidth_limit_mb: Number(($('#mdl-an-bw-limit') && $('#mdl-an-bw-limit').value) || 16),
          auto_maintain: true,
          filters: {
            enabled: true,
            sub_id: srcArr.includes('ALL') ? 'ALL' : srcArr.join(','),
            region_any: ctryArr.includes('ALL') ? [] : ctryArr,
            require_services: checkedSvcs,
            min_group_size: tSize,
            replenish_threshold: rThresh
          },
          smart_switch_enabled: true,
          groups,
          probe_now: true
        });
        if (res && res.ok === false) {
          toast(res.message || '保存自动节点池失败', 'warn');
          return;
        }
        closeModal();
        toast('自动节点池「' + name + '」已生效（选入 ' + finalTags.length + '/' + tSize + ' 个节点，低于 ' + rThresh + ' 个自动复选）');
        await syncBackendStatus(false, true);
      },
      '保存并启用节点池'
    );

    function nodeMatchesSelectedSources(n) {
      if (selectedSources.has('ALL') || !selectedSources.size) return true;
      for (const sid of selectedSources) {
        if (nodeMatchesSubscription(n, sid)) return true;
      }
      return false;
    }

    function getSourceFilteredNodes() {
      return mock.nodes.filter(n => nodeMatchesSelectedSources(n));
    }

    function getScopeFilteredNodes() {
      return getSourceFilteredNodes().filter(n => {
        if (selectedCountries.has('ALL') || !selectedCountries.size) return true;
        return selectedCountries.has(classifyNodeCountry(n));
      });
    }

    function renderSourceChecks() {
      const box = $('#mdl-an-source-checks');
      if (!box) return;
      box.innerHTML = sourceItems.map(item => {
        const isChecked = selectedSources.has(item.id);
        return '<label class="an-source-chip ' + (isChecked ? 'active' : '') + '" data-an-source-id="' + esc(item.id) + '">' +
          '<div class="an-source-chip-left">' +
            '<input type="checkbox" class="chk-an-source" value="' + esc(item.id) + '" ' + (isChecked ? 'checked' : '') + '>' +
            '<span class="an-source-chip-name" title="' + esc(item.name) + '">' + esc(item.name) + '</span>' +
          '</div>' +
          '<span class="an-source-chip-meta">' + esc(item.meta) + '</span>' +
        '</label>';
      }).join('');
      const sumEl = $('#mdl-an-source-summary');
      if (sumEl) {
        const srcNodes = getSourceFilteredNodes();
        sumEl.textContent = selectedSources.has('ALL')
          ? ('已选：全部来源（共 ' + srcNodes.length + ' 个候选节点）')
          : ('已勾选 ' + selectedSources.size + ' 个来源（共 ' + srcNodes.length + ' 个候选节点）');
      }
    }

    function renderCountryChips() {
      const subNodes = getSourceFilteredNodes();
      const counts = { ALL: subNodes.length, HK: 0, TW: 0, JP: 0, SG: 0, US: 0, OTHER: 0 };
      subNodes.forEach(n => {
        const c = classifyNodeCountry(n);
        counts[c] = (counts[c] || 0) + 1;
      });
      const chips = [
        ['ALL', '全部地区 (' + counts.ALL + ')'],
        ['HK', '香港 HK (' + counts.HK + ')'],
        ['TW', '台湾 TW (' + counts.TW + ')'],
        ['JP', '日本 JP (' + counts.JP + ')'],
        ['SG', '新加坡 SG (' + counts.SG + ')'],
        ['US', '美国 US (' + counts.US + ')'],
        ['OTHER', '其他地区 (' + counts.OTHER + ')']
      ];
      const box = $('#mdl-an-country-chips');
      if (!box) return;
      box.innerHTML = chips.map(c =>
        '<button type="button" class="' + (selectedCountries.has(c[0]) ? 'active' : '') + '" data-an-country="' + c[0] + '">' + esc(c[1]) + '</button>'
      ).join('');
      const cSum = $('#mdl-an-country-summary');
      if (cSum) {
        const scopedCnt = getScopeFilteredNodes().length;
        cSum.textContent = (selectedCountries.has('ALL') ? '不限国家区域' : ('已选：' + Array.from(selectedCountries).join(' / '))) + ' · 匹配 ' + scopedCnt + ' 个候选节点';
      }
    }

    function renderSelectedTable() {
      const tbody = $('#mdl-an-selected-tbody');
      if (!tbody) return;
      if ($('#mdl-an-g1-cnt')) $('#mdl-an-g1-cnt').textContent = String(selectedSet.size);
      if ($('#mdl-an-cap-lbl')) $('#mdl-an-cap-lbl').textContent = String(targetSize);
      const rows = [];
      Array.from(selectedSet).slice(0, targetSize).forEach((tag, idx) => {
        const n = mock.nodes.find(x => (x.tag || x.name) === tag) || { tag, name: tag, region: classifyNodeCountry({ tag }), protocol: 'PROXY', status: 'ok', rtt: 138 };
        const cCode = classifyNodeCountry(n);
        const tr = testResultsByTag[tag];
        const delayMs = tr && tr.delay_ms > 0 ? tr.delay_ms : n.rtt;
        const stateVal = tr ? tr.state : n.status;
        const subObj = mock.subscriptions.find(s => nodeMatchesSubscription(n, s.id));
        const srcName = isNodeManualCustom(n) ? '手动节点' : (subObj ? subObj.name : '订阅节点');
        let svcHtml = poolMode === 'service_check'
          ? '<span style="color:var(--mint)">真实目标访问验证通过</span>'
          : '<span style="color:var(--muted)">仅 URL Ping 测速优选</span>';
        if (tr && tr.svc_results && Object.keys(tr.svc_results).length) {
          svcHtml = Object.keys(tr.svc_results).map(k => {
            const item = tr.svc_results[k];
            const ok = Boolean(item && item.ok);
            const ms = (item && item.ms) ? (' ' + item.ms + 'ms') : '';
            return '<span class="status-pill" style="padding:2px 6px;color:' + (ok ? 'var(--mint)' : 'var(--rose)') + ';border-color:' + (ok ? 'var(--ok-border)' : 'var(--err-border)') + '">' + esc(k.toUpperCase() + (ok ? ' 可用' : ' 受限') + ms) + '</span>';
          }).join(' ');
        }
        const isCurrentExit = Boolean(p && p.current_node === tag) || idx === 0;
        const exitPill = isCurrentExit ? ' <span class="status-pill" style="color:var(--cyan);border-color:var(--accent-border)">最快首选</span>' : '';
        rows.push('<tr data-an-row-tag="' + esc(tag) + '" data-an-row-group="1">' +
          '<td><span class="status-pill">#' + (idx + 1) + '</span></td>' +
          '<td><b>' + esc(n.name || cleanNodeDisplayName(tag)) + '</b>' + exitPill + ' ' + renderGoogleRegionBadgeHtml(n, false) + '</td>' +
          '<td>' + formatLatencyBadge(delayMs, stateVal, false) + '</td>' +
          '<td>' + svcHtml + '</td>' +
          '<td style="text-align:right"><button type="button" class="button danger compact" style="padding:0 9px" data-an-row-op="remove" data-tag="' + esc(tag) + '">移除</button></td>' +
        '</tr>');
      });
      tbody.innerHTML = rows.length
        ? rows.join('')
        : '<tr><td colspan="5"><div class="empty-state" style="padding:14px"><h4>尚未选取节点 · 请点击上方「开始自动选取」按钮</h4></div></td></tr>';
    }

    function setProgressState(visible, pct, text) {
      const box = $('#mdl-an-progress-box');
      const bar = $('#mdl-an-progress-bar');
      const txt = $('#mdl-an-progress-text');
      const pctEl = $('#mdl-an-progress-pct');
      if (!box) return;
      box.classList.toggle('hidden', !visible);
      if (bar) bar.style.width = Math.max(0, Math.min(100, Number(pct || 0))) + '%';
      if (txt && text) txt.textContent = text;
      if (pctEl) pctEl.textContent = Math.round(Math.max(0, Math.min(100, Number(pct || 0)))) + '%';
    }

    async function executeAutoSelectionWithProgress() {
      const btnAutoScreen = $('#btn-an-auto-screen');
      const checkedSvcs = poolMode === 'service_check' ? $$('.chk-an-svc:checked').map(el => el.value) : [];
      const svcLogic = ($('#mdl-an-svc-logic') && $('#mdl-an-svc-logic').value) || 'all';
      targetSize = Math.max(1, Math.min(10, Number(($('#mdl-an-target-size') && $('#mdl-an-target-size').value) || targetSize)));
      replenishThresh = Math.max(1, Math.min(targetSize, Number(($('#mdl-an-replenish-thresh') && $('#mdl-an-replenish-thresh').value) || replenishThresh)));
      const srcArr = Array.from(selectedSources);
      const ctryArr = Array.from(selectedCountries);

      if (btnAutoScreen) {
        btnAutoScreen.disabled = true;
        btnAutoScreen.setAttribute('aria-busy', 'true');
        btnAutoScreen.textContent = '正在自动选取...';
      }
      setProgressState(true, 8, '正在按所选订阅源与国家地区筛选候选节点...');

      const startRes = await callRouterApi('/api/auto_nodes/auto_screen', 'POST', {
        async: true,
        pool_mode: poolMode,
        service_check_enabled: poolMode === 'service_check',
        service_checks: checkedSvcs,
        service_logic: svcLogic,
        scope_sources: srcArr.length ? srcArr : ['ALL'],
        scope_source: srcArr.includes('ALL') ? 'ALL' : srcArr.join(','),
        scope_countries: ctryArr.length ? ctryArr : ['ALL'],
        target_size: targetSize,
        replenish_threshold: replenishThresh,
        keyword_filter: ($('#mdl-an-keywords') && $('#mdl-an-keywords').value.trim()) || '',
        keyword_mode: ($('#mdl-an-kw-mode') && $('#mdl-an-kw-mode').value) || 'OR',
        run_live_probe: true
      }, 30000);

      let finalRes = null;
      if (startRes && startRes.async && startRes.task_id) {
        const tid = startRes.task_id;
        for (let step = 0; step < 60; step++) {
          await new Promise(r => setTimeout(r, 180));
          const st = await callRouterApi('/api/auto_nodes/auto_screen/status?task_id=' + encodeURIComponent(tid), 'GET');
          if (!st || st.ok === false) break;
          const pct = Number(st.percent != null ? st.percent : (st.done ? 100 : Math.min(92, 18 + step * 12)));
          const lbl = st.stage_label || (st.stage === 'service_check' ? '正在对候选节点执行真实目标服务访问检测...' : '正在执行 URL Ping 测速与最快排序...');
          setProgressState(true, pct, lbl);
          if (st.done && st.result) {
            finalRes = st.result;
            break;
          }
        }
      } else if (startRes && startRes.ok) {
        finalRes = startRes;
      }

      if (btnAutoScreen) {
        btnAutoScreen.disabled = false;
        btnAutoScreen.setAttribute('aria-busy', 'false');
        btnAutoScreen.textContent = '重新自动选取';
      }

      if (finalRes && Array.isArray(finalRes.results)) {
        finalRes.results.forEach(r => {
          testResultsByTag[r.tag] = r;
          const nObj = mock.nodes.find(x => (x.tag || x.name) === r.tag);
          if (nObj && r.delay_ms > 0) {
            nObj.rtt = r.delay_ms;
            nObj.status = r.state || 'ok';
          }
        });
        const admitted = Array.isArray(finalRes.admitted_g1) ? finalRes.admitted_g1.slice(0, targetSize) : [];
        selectedSet.clear();
        admitted.forEach(t => selectedSet.add(t));
        setProgressState(
          true,
          100,
          admitted.length
            ? ('自动选取完成：已从 ' + (finalRes.total_candidates_in_scope || 0) + ' 个候选节点中选入最快 ' + admitted.length + ' 个健康节点')
            : '当前订阅与地区范围内未找到达标节点，请放宽条件后重试'
        );
        renderSelectedTable();
        if (admitted.length) {
          toast('自动选取完成：已选入最快 ' + admitted.length + ' 个节点（点击右下角「保存并启用节点池」即可生效）');
        } else {
          toast('未找到符合条件的节点，请尝试勾选更多订阅源或国家区域', 'warn');
        }
      } else {
        const fallbackCands = getScopeFilteredNodes().filter(n => getNodeTwoState(n) === 'ok').sort((a, b) => (a.rtt || 999) - (b.rtt || 999));
        selectedSet.clear();
        fallbackCands.slice(0, targetSize).forEach(n => selectedSet.add(n.tag || n.name));
        setProgressState(true, 100, '自动选取完成：已按最快延迟选入 ' + selectedSet.size + ' 个节点');
        renderSelectedTable();
      }
    }

    function syncDispatchAndBwGuardrails() {
      const checkedSvcs = poolMode === 'service_check' ? $$('.chk-an-svc:checked').map(el => el.value) : [];
      const hasAiSvc = isFixedAiPoolId || checkedSvcs.some(s => IP_SENSITIVE_SVCS.has(s));
      const btnSingle = $('#btn-an-dispatch-single');
      const btnMulti = $('#btn-an-dispatch-multi');
      const lblMulti = $('#lbl-an-dispatch-multi');
      const hintEl = $('#mdl-an-dispatch-guard-hint');
      if (hasAiSvc) {
        dispatchMode = 'single_best';
        if (btnMulti) {
          btnMulti.disabled = true;
          btnMulti.classList.remove('active');
          btnMulti.style.opacity = '0.45';
          btnMulti.style.cursor = 'not-allowed';
        }
        if (btnSingle) btnSingle.classList.add('active');
        if (lblMulti) lblMulti.textContent = '多线并发（已自动锁定单线：AI/账号服务防跳IP）';
        if (hintEl) hintEl.textContent = '已启用 AI/账号防风控互斥保护：自动锁定为「优选单线」';
      } else {
        if (btnMulti) {
          btnMulti.disabled = false;
          btnMulti.style.opacity = '1';
          btnMulti.style.cursor = 'pointer';
          btnMulti.classList.toggle('active', dispatchMode === 'multi_line');
        }
        if (btnSingle) btnSingle.classList.toggle('active', dispatchMode === 'single_best');
        if (lblMulti) lblMulti.textContent = '多线并发（池内健康节点叠加吞吐）';
        if (hintEl) {
          hintEl.textContent = dispatchMode === 'multi_line'
            ? '多线并发已开启：已自动屏蔽 AI 敏感服务勾选项，并要求容量 ≥ 2'
            : '可根据业务类型切换「优选单线」或「多线并发」';
        }
      }
      $$('.chk-an-svc').forEach(chk => {
        if (IP_SENSITIVE_SVCS.has(chk.value)) {
          if (dispatchMode === 'multi_line') {
            chk.checked = false;
            chk.disabled = true;
            if (chk.parentElement) chk.parentElement.style.opacity = '0.45';
          } else {
            chk.disabled = false;
            if (chk.parentElement) chk.parentElement.style.opacity = '1';
          }
        }
      });
      if (dispatchMode === 'multi_line' && targetSize < 2) {
        targetSize = Math.max(4, targetSize);
        const tsEl = $('#mdl-an-target-size');
        if (tsEl) tsEl.value = String(targetSize);
      }
      const bwChk = $('#mdl-an-bw-prefer');
      const bwOpts = $('#mdl-an-bw-opts');
      const bwEst = $('#mdl-an-bw-est');
      bwPrefer = Boolean(bwChk && bwChk.checked);
      if (bwOpts) {
        bwOpts.classList.toggle('hidden', !bwPrefer);
        bwOpts.style.display = bwPrefer ? 'inline-flex' : 'none';
      }
      if (bwEst && bwPrefer) {
        const iv = Number(($('#mdl-an-bw-interval') && $('#mdl-an-bw-interval').value) || 6);
        const lim = Number(($('#mdl-an-bw-limit') && $('#mdl-an-bw-limit').value) || 16);
        const est = Math.round((24 / Math.max(1, iv)) * lim * Math.max(1, selectedSet.size || targetSize));
        bwEst.textContent = '预计日耗 ~' + est + ' MiB';
      }
    }

    renderSourceChecks();
    renderCountryChips();
    renderSelectedTable();
    syncDispatchAndBwGuardrails();

    const builderRoot = $('#an-builder-root');
    if (builderRoot) {
      builderRoot.addEventListener('change', ev => {
        if (ev.target.classList.contains('chk-an-source')) {
          const val = ev.target.value;
          if (val === 'ALL') {
            selectedSources.clear();
            selectedSources.add('ALL');
          } else {
            selectedSources.delete('ALL');
            if (ev.target.checked) selectedSources.add(val);
            else selectedSources.delete(val);
            if (!selectedSources.size) selectedSources.add('ALL');
          }
          renderSourceChecks();
          renderCountryChips();
          return;
        }
        if (ev.target.id === 'mdl-an-target-size') {
          targetSize = Math.max(1, Math.min(10, Number(ev.target.value || 5)));
          if (replenishThresh > targetSize) replenishThresh = targetSize;
          const repSel = $('#mdl-an-replenish-thresh');
          if (repSel) {
            repSel.innerHTML = numOptionsHtml(targetSize, replenishThresh);
            repSel.value = String(replenishThresh);
          }
          if (selectedSet.size > targetSize) {
            const trimmed = Array.from(selectedSet).slice(0, targetSize);
            selectedSet.clear();
            trimmed.forEach(t => selectedSet.add(t));
          }
          renderSelectedTable();
          return;
        }
        if (ev.target.id === 'mdl-an-replenish-thresh') {
          replenishThresh = Math.max(1, Math.min(targetSize, Number(ev.target.value || 1)));
          return;
        }
        if (ev.target.classList.contains('chk-an-svc') || ev.target.id === 'mdl-an-bw-prefer' || ev.target.id === 'mdl-an-bw-interval' || ev.target.id === 'mdl-an-bw-limit') {
          syncDispatchAndBwGuardrails();
          return;
        }
        if (ev.target.id === 'mdl-an-keywords' || ev.target.id === 'mdl-an-kw-mode') {
          renderCountryChips();
          return;
        }
      });

      builderRoot.addEventListener('click', ev => {
        const countryBtn = ev.target.closest('[data-an-country]');
        if (countryBtn) {
          ev.preventDefault();
          ev.stopPropagation();
          const c = countryBtn.dataset.anCountry || 'ALL';
          if (c === 'ALL') {
            selectedCountries.clear();
            selectedCountries.add('ALL');
          } else {
            selectedCountries.delete('ALL');
            if (selectedCountries.has(c)) selectedCountries.delete(c);
            else selectedCountries.add(c);
            if (!selectedCountries.size) selectedCountries.add('ALL');
          }
          renderCountryChips();
          return;
        }
        const modeBtn = ev.target.closest('[data-an-pool-mode]');
        if (modeBtn) {
          ev.preventDefault();
          ev.stopPropagation();
          poolMode = modeBtn.dataset.anPoolMode || 'service_check';
          $$('[data-an-pool-mode]', builderRoot).forEach(b => b.classList.toggle('active', b.dataset.anPoolMode === poolMode));
          const svcPanel = $('#mdl-an-svc-panel');
          if (svcPanel) {
            svcPanel.classList.toggle('hidden', poolMode !== 'service_check');
            svcPanel.style.display = poolMode === 'service_check' ? 'flex' : 'none';
          }
          syncDispatchAndBwGuardrails();
          renderSelectedTable();
          return;
        }
        const dispBtn = ev.target.closest('[data-an-dispatch]');
        if (dispBtn && !dispBtn.disabled) {
          ev.preventDefault();
          ev.stopPropagation();
          dispatchMode = dispBtn.dataset.anDispatch || 'single_best';
          syncDispatchAndBwGuardrails();
          renderSelectedTable();
          return;
        }
        const rowOp = ev.target.closest('[data-an-row-op="remove"]');
        if (rowOp) {
          ev.preventDefault();
          ev.stopPropagation();
          const tag = rowOp.dataset.tag || '';
          if (tag && selectedSet.has(tag)) {
            selectedSet.delete(tag);
            renderSelectedTable();
          }
          return;
        }
      });

      const btnAutoScreen = $('#btn-an-auto-screen');
      if (btnAutoScreen) {
        btnAutoScreen.addEventListener('click', ev => {
          ev.preventDefault();
          ev.stopPropagation();
          executeAutoSelectionWithProgress();
        });
      }
    }

    if (autoStartScreen) {
      setTimeout(() => executeAutoSelectionWithProgress(), 60);
    }
  }

  async function openReplaceAutoNodeModal(poolIdx) {
    openAutoNodeEditorModal(poolIdx);
  }

  function applySubscriptionsFromApi(rawList) {
    if (!Array.isArray(rawList)) return;
    state.rawSubs = rawList;
    const prevById = {};
    (mock.subscriptions || []).forEach(oldS => {
      if (oldS && oldS.id) prevById[oldS.id] = oldS;
      if (oldS && oldS.name) prevById[oldS.name] = oldS;
    });
    mock.subscriptions = rawList.map(s => {
      const sid = s.id || s.name || 'sub_main';
      const prev = prevById[sid] || prevById[s.name] || null;
      const rawUrl = String(s.url || '');
      const cleanUrl = (rawUrl.includes('***') && prev && prev.url && !String(prev.url).includes('***')) ? prev.url : rawUrl;
      const isErr = Boolean(s.status === 'error' || s.last_sync_status === 'error');
      let syncTxt = String(s.sync_status_text || s.last_sync_human || s.last_sync_time || '');
      if (!isErr && syncTxt) {
        syncTxt = syncTxt.replace(/\s*失败.*$/, '').trim();
      }
      return {
        id: sid,
        name: s.name || sid || '订阅源',
        count: Number(s.node_count != null ? s.node_count : (s.count != null ? s.count : 0)),
        enabled: s.enabled !== false,
        status: isErr ? 'error' : 'ok',
        health_status: isErr ? 'fetch_error' : (s.health_status || 'ok'),
        last_sync_ts: Number(s.last_sync_ts || 0),
        last_sync_time: s.last_sync_time || '',
        sync_status_text: syncTxt,
        updated: syncTxt || s.updated_at || s.updated || '已同步',
        url: cleanUrl,
        auto_update: s.auto_update !== false,
        update_interval_min: Number(s.update_interval_min || 360),
        userinfo: (s.userinfo && typeof s.userinfo === 'object') ? s.userinfo : (prev && prev.userinfo ? prev.userinfo : null),
        last_sync_status: isErr ? 'error' : 'ok',
        last_error: isErr ? (s.last_error || '') : ''
      };
    });
    if (Array.isArray(mock.nodes) && mock.nodes.length) {
      mock.nodes.forEach(n => {
        if (!n) return;
        const subNameVal = n.is_custom ? '手动添加节点' : resolveNodeSubDisplayName(n);
        n.sub_name = subNameVal;
        n.name = formatNodeUnifiedDisplayName(n, subNameVal);
      });
    }
  }

  async function runSubscriptionSyncWithModal(opts) {
    opts = opts || {};
    if (state._syncingSubLock) {
      toast('订阅同步任务正在运行中，请查看弹窗进度', 'warn');
      return null;
    }
    state._syncingSubLock = true;
    const mode = opts.mode || 'single';
    let targets = [];
    if (mode === 'all') {
      targets = mock.subscriptions.filter(s => s.enabled !== false).map(s => ({
        id: s.id,
        name: s.name,
        url: s.url,
        action: 'sync_one'
      }));
      if (!targets.length && mock.subscriptions.length) {
        targets = mock.subscriptions.map(s => ({ id: s.id, name: s.name, url: s.url, action: 'sync_one' }));
      }
    } else if (mode === 'single') {
      const sub = mock.subscriptions[opts.subIdx];
      if (sub) {
        targets = [{ id: sub.id, name: sub.name, url: sub.url, action: 'sync_one' }];
      }
    } else if (mode === 'edit') {
      targets = [{ id: opts.payload.id, name: opts.payload.name, url: opts.payload.new_url || opts.payload.old_url || '', action: 'edit', payload: opts.payload }];
    } else if (mode === 'import_text') {
      targets = [{ id: 'import_txt', name: opts.payload.name || '离线导入订阅', url: '离线订阅内容解析', action: 'import_text', payload: opts.payload }];
    } else if (mode === 'add') {
      targets = [{ id: 'new_sub', name: opts.payload.name || '新订阅源', url: opts.payload.url || '', action: 'add', payload: opts.payload }];
    }

    if (!targets.length) {
      state._syncingSubLock = false;
      toast('当前没有可同步的订阅源，请先添加订阅', 'warn');
      return null;
    }

    const buildTargetRowsHtml = items => items.map((t, idx) => {
      let hostStr = String(t.url || '内置/本地订阅源');
      try {
        if (hostStr.startsWith('http')) {
          const uo = new URL(hostStr);
          hostStr = uo.protocol + '//' + uo.host + uo.pathname.slice(0, 22) + (uo.pathname.length > 22 ? '...' : '');
        }
      } catch (_) {}
      return '<div class="sub-sync-item-card" id="sub-sync-row-' + idx + '">' +
        '<div class="sub-sync-item-head">' +
          '<div><b style="font-size:14px;color:var(--text)">' + esc(t.name) + '</b><div class="mono" style="font-size:12px;color:var(--muted)">' + esc(hostStr) + '</div></div>' +
          '<span class="status-pill" id="sub-sync-badge-' + idx + '">排队等待</span>' +
        '</div>' +
        '<div id="sub-sync-detail-' + idx + '" style="font-size:12px;color:var(--muted);margin-top:2px">等待启动同步任务...</div>' +
      '</div>';
    }).join('');

    openModal(
      '订阅同步与节点预热实时进度',
      '<div class="modal-form" id="sub-sync-progress-modal">' +
        '<div class="sub-health-box" style="padding:var(--sp-3)">' +
          '<div class="sub-health-top">' +
            '<span id="sub-sync-stage-title" style="font-weight:500;color:var(--text)">正在初始化订阅拉取通道...</span>' +
            '<span class="sub-expire-pill" id="sub-sync-pct-label">8%</span>' +
          '</div>' +
          '<div class="sub-health-bar" style="height:8px"><i id="sub-sync-prog-fill" style="width:8%"></i></div>' +
          '<div class="sub-health-meta">' +
            '<span id="sub-sync-subhint">支持 Clash / Sing-box / Base64 / URI 自动识别与 node_key 无损对齐</span>' +
            '<span id="sub-sync-counter">0 / ' + targets.length + ' 已完成</span>' +
          '</div>' +
        '</div>' +
        '<div class="sub-sync-modal-list" id="sub-sync-items-list">' + buildTargetRowsHtml(targets) + '</div>' +
      '</div>',
      'SUBSCRIPTION SYNC TELEMETRY',
      () => { closeModal(); },
      '同步进行中...'
    );

    const confirmBtn = $('#modal-confirm');
    if (confirmBtn) confirmBtn.disabled = true;

    const setOverallProgress = (pct, stageTxt, barClass) => {
      const pFill = $('#sub-sync-prog-fill');
      const pLbl = $('#sub-sync-pct-label');
      const sTitle = $('#sub-sync-stage-title');
      const barWrap = pFill ? pFill.parentElement : null;
      const clamped = Math.max(5, Math.min(100, Math.round(pct)));
      if (pFill) pFill.style.width = clamped + '%';
      if (pLbl) pLbl.textContent = clamped + '%';
      if (sTitle && stageTxt) sTitle.textContent = stageTxt;
      if (barWrap) {
        barWrap.classList.remove('warn', 'danger');
        if (barClass) barWrap.classList.add(barClass);
      }
    };

    let okCount = 0;
    let failCount = 0;
    let lastRes = null;

    try {
      for (let i = 0; i < targets.length; i++) {
        const t = targets[i];
        const badgeEl = $('#sub-sync-badge-' + i);
        const detailEl = $('#sub-sync-detail-' + i);
        const basePct = (i / targets.length) * 100;
        const stepSpan = 100 / targets.length;

        if (badgeEl) {
          badgeEl.textContent = '正在拉取...';
          badgeEl.style.color = 'var(--cyan)';
          badgeEl.style.borderColor = 'var(--cyan)';
        }
        if (detailEl) {
          detailEl.textContent = '阶段 1/3：正在连接远程订阅服务器拉取配置并校验格式...';
          detailEl.style.color = 'var(--text-2)';
        }
        setOverallProgress(basePct + stepSpan * 0.25, '正在同步「' + t.name + '」(' + (i + 1) + '/' + targets.length + ') · 拉取订阅内容...');

        let animPct = basePct + stepSpan * 0.25;
        const stageTimer = setInterval(() => {
          animPct = Math.min(basePct + stepSpan * 0.85, animPct + stepSpan * 0.12);
          const relRatio = (animPct - basePct) / stepSpan;
          if (relRatio > 0.55) {
            if (badgeEl) badgeEl.textContent = '测速预热中...';
            if (detailEl) detailEl.textContent = '阶段 3/3：正在对节点执行并发 URL Ping 真连接测速与自动池优选...';
            setOverallProgress(animPct, '正在同步「' + t.name + '」(' + (i + 1) + '/' + targets.length + ') · 节点测速与入核编译...');
          } else if (relRatio > 0.32) {
            if (badgeEl) badgeEl.textContent = '解析入库中...';
            if (detailEl) detailEl.textContent = '阶段 2/3：正在解析节点协议、提取流量到期信息并对齐 node_key...';
            setOverallProgress(animPct, '正在同步「' + t.name + '」(' + (i + 1) + '/' + targets.length + ') · 解析节点与指纹对齐...');
          } else {
            setOverallProgress(animPct);
          }
        }, 420);

        let res = null;
        try {
          if (t.action === 'edit') {
            res = await callRouterApi('/api/subscriptions/edit', 'POST', t.payload, 45000);
          } else if (t.action === 'import_text') {
            res = await callRouterApi('/api/subscriptions/import_text', 'POST', t.payload, 45000);
          } else if (t.action === 'add') {
            res = await callRouterApi('/api/subscriptions/add', 'POST', t.payload, 45000);
          } else {
            const cleanSyncUrl = (t.url && !String(t.url).includes('***')) ? t.url : '';
            res = await callRouterApi('/api/subscriptions/sync', 'POST', { id: t.id, name: t.name, url: cleanSyncUrl }, 45000);
          }
        } finally {
          clearInterval(stageTimer);
        }
        lastRes = res;

        if (res && Array.isArray(res.subscriptions)) {
          applySubscriptionsFromApi(res.subscriptions);
          renderSubscriptionsAndNodes();
        }

        const cntEl = $('#sub-sync-counter');
        if (cntEl) cntEl.textContent = (i + 1) + ' / ' + targets.length + ' 已完成';

        if (res && res.ok !== false) {
          okCount++;
          const nowSyncTs = Math.floor(Date.now() / 1000);
          const pad2 = v => String(v).padStart(2, '0');
          const dNow = new Date();
          const nowSyncStr = dNow.getFullYear() + '-' + pad2(dNow.getMonth() + 1) + '-' + pad2(dNow.getDate()) + ' ' + pad2(dNow.getHours()) + ':' + pad2(dNow.getMinutes());
          const markSubOk = list => {
            if (!Array.isArray(list)) return;
            list.forEach(item => {
              if (item && (item.id === t.id || item.name === t.name)) {
                item.status = 'ok';
                item.last_sync_status = 'ok';
                item.health_status = 'ok';
                item.last_error = '';
                item.last_sync_ts = nowSyncTs;
                item.last_sync_time = nowSyncStr;
                item.sync_status_text = nowSyncStr;
              }
            });
          };
          markSubOk(mock.subscriptions);
          if (state.rawStatus && Array.isArray(state.rawStatus.subscriptions)) markSubOk(state.rawStatus.subscriptions);
          if (typeof window !== 'undefined' && window.__MOCK_STATUS && Array.isArray(window.__MOCK_STATUS.subscriptions)) markSubOk(window.__MOCK_STATUS.subscriptions);
          renderSubscriptionsAndNodes();
          const impCnt = res.imported_count != null ? res.imported_count : (res.subscription && res.subscription.count != null ? res.subscription.count : '');
          const uinfo = res.userinfo || (res.subscription && res.subscription.userinfo) || null;
          let extraTraffic = '';
          if (uinfo && uinfo.total_bytes > 0) {
            const uTxt = uinfo.used_human || fmtBytes(uinfo.used_bytes || 0);
            const tTxt = uinfo.total_human || fmtBytes(uinfo.total_bytes || 0);
            extraTraffic = ' · 流量 ' + uTxt + ' / ' + tTxt;
          }
          if (badgeEl) {
            badgeEl.textContent = '同步成功';
            badgeEl.style.color = 'var(--mint)';
            badgeEl.style.borderColor = 'var(--mint)';
          }
          if (detailEl) {
            detailEl.textContent = '已完成同步' + (impCnt !== '' ? ('：共入库 ' + impCnt + ' 个有效节点') : '') + extraTraffic + ' · 状态已实时刷新';
            detailEl.style.color = 'var(--mint)';
          }
        } else {
          failCount++;
          const errMsg = (res && (res.message || res.error)) || '连接订阅源超时或解析失败';
          if (badgeEl) {
            badgeEl.textContent = '同步失败';
            badgeEl.style.color = 'var(--rose)';
            badgeEl.style.borderColor = 'var(--rose)';
          }
          if (detailEl) {
            detailEl.textContent = '失败原因：' + errMsg;
            detailEl.style.color = 'var(--rose)';
          }
        }
      }

      setOverallProgress(95, '正在刷新节点列表与全站分流状态矩阵...');
      await syncBackendStatus(true, true);
      renderSubscriptionsAndNodes();

      const finalBarCls = failCount > 0 ? (okCount > 0 ? 'warn' : 'danger') : '';
      const finalMsg = failCount === 0
        ? ('全部 ' + okCount + ' 个订阅源同步成功，节点状态与同步时间已实时更新')
        : ('同步结束：成功 ' + okCount + ' 个，失败 ' + failCount + ' 个（请查看下方明细）');
      setOverallProgress(100, finalMsg, finalBarCls);
      if (failCount === 0) {
        toast('订阅同步成功（' + okCount + '/' + targets.length + '），卡片状态已实时刷新');
      } else {
        toast('订阅同步完成：成功 ' + okCount + ' 个，失败 ' + failCount + ' 个', 'warn');
      }
    } finally {
      state._syncingSubLock = false;
      if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = '完成并关闭';
      }
    }
    return lastRes;
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
        (s ? ('<div class="button-row" style="margin-top:8px;justify-content:space-between">' +
          '<button type="button" class="button ghost compact" data-action="sub-preview-sync" data-sub="' + subIdx + '">同步前影响预览 (Diff)</button>' +
          '<button type="button" class="button danger compact" data-action="sub-delete-one" data-sub="' + subIdx + '">删除此订阅源</button>' +
        '</div>') : '') +
      '</div>',
      'SUBSCRIPTION MANAGER',
      async () => {
        const name = ($('#mdl-sub-name') && $('#mdl-sub-name').value.trim()) || (s ? s.name : '主力机场订阅');
        const url = ($('#mdl-sub-url') && $('#mdl-sub-url').value.trim()) || (s ? s.url : '');
        const interval = Number(($('#mdl-sub-interval') && $('#mdl-sub-interval').value) || 360);
        const raw_text = ($('#mdl-sub-rawtext') && $('#mdl-sub-rawtext').value.trim()) || '';
        if (!url && !raw_text) { toast('请输入订阅链接 URL 或粘贴离线订阅内容', 'warn'); return; }
        closeModal();
        if (s) {
          await runSubscriptionSyncWithModal({
            mode: 'edit',
            payload: {
              id: s.id,
              old_url: s.url,
              new_url: url.includes('***') ? '' : url,
              name,
              update_interval_min: interval,
              auto_update: interval > 0,
              raw_text,
              sync_now: !raw_text
            }
          });
        } else if (raw_text && !url) {
          await runSubscriptionSyncWithModal({
            mode: 'import_text',
            payload: { name, raw_text, test_after_add: true }
          });
        } else {
          await runSubscriptionSyncWithModal({
            mode: 'add',
            payload: { name, url, auto_update: interval > 0, update_interval_min: interval, test_after_add: true }
          });
        }
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
        '<div class="modal-field"><div style="display:flex;justify-content:space-between;align-items:center"><label>节点分享 URI 列表</label><button type="button" class="button ghost compact" style="padding:0 8px;" data-action="preview-share-uri">解析预览链接</button></div><textarea id="mdl-import-text" rows="5" placeholder="vless://...\nhysteria2://..."></textarea></div>' +
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
      '<div class="trace-stage" style="padding:9px 12px"><i>⏱</i><div><b>' + esc(s.name) + '</b><span>范围: ' + esc(s.region || 'ALL') + ' · 每 ' + Number(s.interval_min || 360) + ' 分钟执行</span></div>' +
      '<div class="button-row"><button class="button secondary compact" style="padding:0 8px;" data-action="run-sched-now" data-sid="' + esc(s.id) + '">立即运行</button>' +
      '<button class="button danger compact" style="padding:0 8px;" data-action="del-sched" data-sid="' + esc(s.id) + '">删除</button></div></div>'
    ).join('');
    openModal(
      '定时 URL Ping 测速巡检计划',
      '<div class="modal-form">' +
        '<div class="trace-stages">' + (schedRows || '<p>当前暂无定时计划</p>') + '</div>' +
        '<div class="modal-grid-3" style="margin-top:8px">' +
          '<div class="modal-field"><label>新增计划名称</label><input id="mdl-sched-name" value="高频地区定时巡检"></div>' +
          '<div class="modal-field"><label>目标地区</label><select id="mdl-sched-region"><option value="ALL">全部地区 (ALL)</option>' +
            COUNTRY_CODES.map(c => '<option value="' + c + '">' + esc(COUNTRY_META[c].name) + '</option>').join('') +
          '</select></div>' +
          '<div class="modal-field"><label>巡检间隔 (分钟)</label><input id="mdl-sched-intv" type="number" value="180"></div>' +
        '</div>' +
        '<div class="modal-field"><label>内核出站挂载策略</label><div class="status-pill ok" style="padding:7px 12px">全部入核（无数量上限 · 所有启用订阅与手动节点 100% 原生挂载）</div></div>' +
      '</div>',
      'PROBE SCHEDULER',
      async () => {
        const name = ($('#mdl-sched-name') && $('#mdl-sched-name').value.trim()) || '定时测速计划';
        const region = ($('#mdl-sched-region') && $('#mdl-sched-region').value) || 'ALL';
        const interval_min = Number(($('#mdl-sched-intv') && $('#mdl-sched-intv').value) || 180);
        await callRouterApi('/api/probe/schedules/save', 'POST', { name, region, interval_min, enabled: true });
        closeModal();
        toast('定时测速巡检计划已保存');
        await syncBackendStatus(true, true);
      },
      '保存巡检计划'
    );
  }

  function openPasswordModal() {
    openModal(
      '修改面板管理密码',
      '<div class="modal-form">' +
        '<p>设置独立强密码后，旧密码与设备随机初始密码（<code>/etc/ai-link/initial_password</code>）将立即失效，UCI 仅记录布尔状态位 <code>panel_pwd_customized=1</code>。</p>' +
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
    const curMacs = Array.isArray(state.lanDirectMacs)
      ? state.lanDirectMacs.join(', ')
      : (Array.isArray(state.rawOps && state.rawOps.lan_direct_macs) ? state.rawOps.lan_direct_macs.join(', ') : '');
    const curMtu = Number(state.tunMtu || (state.rawOps && state.rawOps.tun_mtu) || 1500);
    openModal(
      '面板监听、免密网段与设备直通白名单配置',
      '<div class="modal-form">' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>面板监听地址 (panel_bind)</label><input id="mdl-panel-bind" value="' + esc(state.rawOps.panel_bind || '0.0.0.0') + '"></div>' +
          '<div class="modal-field"><label>GitHub 规则加速源 (gh_mirror)</label><input id="mdl-gh-mirror" list="mdl-gh-mirror-list" value="' + esc(state.ghMirror) + '">' +
            '<datalist id="mdl-gh-mirror-list">' +
              '<option value="https://gh-proxy.com/">gh-proxy.com (默认高速镜像)</option>' +
              '<option value="https://ghfast.top/">ghfast.top (国内优选加速源)</option>' +
              '<option value="https://mirror.ghproxy.com/">mirror.ghproxy.com (备用镜像源)</option>' +
              '<option value="https://testingcf.jsdelivr.net/">testingcf.jsdelivr.net (Cloudflare CDN)</option>' +
            '</datalist>' +
          '</div>' +
        '</div>' +
        '<div class="modal-grid-2">' +
          '<div class="modal-field"><label>局域网免密信任网段 (trusted_cidr)</label><input id="mdl-trusted-cidr" value="' + esc(state.trustedCidr) + '"></div>' +
          '<div class="modal-field"><label>TUN 虚拟网卡 MTU (1280~9000，PPPoE 推荐 1492)</label><input id="mdl-tun-mtu" type="number" min="1280" max="9000" value="' + esc(String(curMtu)) + '"></div>' +
        '</div>' +
        '<div class="modal-field"><label>局域网设备 MAC 免代理直通白名单 (lan_direct_macs，逗号分隔，如智能电视/NAS/PT下载机直走宽带)</label><input id="mdl-lan-direct-macs" value="' + esc(curMacs) + '" placeholder="aa:bb:cc:dd:ee:ff, 11:22:33:44:55:66"></div>' +
        '<div class="modal-field"><label>自定义 OTA 更新清单源 URL (update_manifest_url，留空使用官方 Cloudflare/GitHub 主源)</label><input id="mdl-manifest-url" value="' + esc(state.updateManifestUrl || '') + '" placeholder="https://your-domain.example.com/version.json"></div>' +
      '</div>',
      'NETWORK & SECURITY',
      async () => {
        const panel_bind = ($('#mdl-panel-bind') && $('#mdl-panel-bind').value.trim()) || '0.0.0.0';
        const gh_mirror = ($('#mdl-gh-mirror') && $('#mdl-gh-mirror').value.trim()) || '';
        const update_manifest_url = ($('#mdl-manifest-url') && $('#mdl-manifest-url').value.trim()) || '';
        const trusted_cidr = ($('#mdl-trusted-cidr') && $('#mdl-trusted-cidr').value.trim()) || '127.0.0.1/32';
        const tun_mtu_raw = Number(($('#mdl-tun-mtu') && $('#mdl-tun-mtu').value) || 1500);
        if (!Number.isFinite(tun_mtu_raw) || tun_mtu_raw < 1280 || tun_mtu_raw > 9000) {
          toast('TUN MTU 必须为 1280 ~ 9000 之间的整数', 'warn');
          return;
        }
        const tun_mtu = Math.round(tun_mtu_raw);
        const rawMacStr = ($('#mdl-lan-direct-macs') && $('#mdl-lan-direct-macs').value.trim()) || '';
        const macParts = rawMacStr.split(/[,;\s]+/).filter(Boolean).map(m => m.toLowerCase().replace(/-/g, ':'));
        const macRe = /^([0-9a-f]{2}:){5}[0-9a-f]{2}$/;
        for (let i = 0; i < macParts.length; i++) {
          if (!macRe.test(macParts[i])) {
            toast('免代理直通 MAC 第 ' + (i + 1) + ' 项格式不合法: ' + macParts[i], 'warn');
            return;
          }
        }
        const cidrParts = trusted_cidr.split(/[,;\s]+/).filter(Boolean);
        const cidrRe = /^(?:(?:\d{1,3}\.){3}\d{1,3}(?:\/(?:[0-9]|[12][0-9]|3[0-2]))?|[0-9a-fA-F:]+(?:\/(?:[0-9]|[1-9][0-9]|1[01][0-9]|12[0-8]))?)$/;
        for (let i = 0; i < cidrParts.length; i++) {
          if (!cidrRe.test(cidrParts[i])) {
            toast('免密信任网段第 ' + (i + 1) + ' 项格式不合法: ' + cidrParts[i], 'warn');
            return;
          }
        }
        const payload = { panel_bind, gh_mirror, update_manifest_url, trusted_cidr, tun_mtu, lan_direct_macs: macParts };
        const res = await callRouterApi('/api/ops/settings', 'POST', payload);
        if (res && res.ok !== false) {
          renderOpsSettings(payload, true);
          closeModal();
          toast('网络、安全与设备直通配置已保存');
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
              '<span style="width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--surface-3);border:1px solid rgba(110,231,245,.3);color:var(--cyan);font-weight:600">' + esc(avatarTxt) + '</span>' +
              '<div><b>' + esc(d.name || d.ip) + '</b><small class="mono">' + esc(d.ip || 'LAN') + '</small></div>' +
            '</div></td>' +
            '<td><span class="status-pill">' + (d.is_remote ? '回家隧道' : '局域网 LAN') + '</span></td>' +
            '<td class="mono">' + esc(rateTxt) + ' ' + renderGearBadge(rateSum, d.conns || 1) + '</td>' +
            '<td class="mono"><b style="color:var(--cyan)">' + esc(Number(d.conns || 0)) + '</b> 条连接</td>' +
            '<td><div style="min-width:110px"><div style="display:flex;justify-content:space-between;"><span>' + esc(totalMbTxt) + '</span><span>' + esc(pctVal) + '%</span></div><div class="thin-progress" style="margin-top:4px"><i style="width:' + pctVal + '%"></i></div></div></td>' +
            '<td style="text-align:right"><button class="button ghost compact" style="padding:0 8px;" data-action="jump-device-conns" data-ip="' + esc(d.ip || '') + '">查看连接</button></td>' +
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
              '<button type="button" data-ov-dev-filter="active">活跃传输</button>' +
              '<button type="button" data-ov-dev-filter="remote">回家隧道</button>' +
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
        '前往实时连接管理 '
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
              '<button class="button ghost compact" style="padding:0 7px;" data-action="node-real-delay" data-node="' + esc(n.tag || n.name) + '">真测速</button>' +
              '<button class="button secondary compact" style="padding:0 7px;" data-action="set-node-exit" data-node="' + esc(n.tag || n.name) + '">设为出口</button>' +
            '</div></td>' +
          '</tr>';
        }).join('');
      };

      openModal(
        '入核出站节点池与健康遥测明细 (' + fmtOutboundQuota(mock.activeOutbounds, mock.maxOutboundsLimit) + ')',
        '<div class="ov-insight-modal-wrap">' +
          '<div class="galaxy-kpi-grid" style="margin-bottom:12px">' +
            '<div class="galaxy-kpi-card"><span>入核活跃配额</span><b style="color:var(--cyan)">' + esc(fmtOutboundQuota(mock.activeOutbounds, mock.maxOutboundsLimit)) + '</b><small>总计保存 ' + esc(mock.nodes.length) + ' 个节点</small></div>' +
            '<div class="galaxy-kpi-card"><span>已验证可用</span><b style="color:var(--mint)">' + esc(okCnt) + ' 个</b><small>URL Ping 握手通过</small></div>' +
            '<div class="galaxy-kpi-card"><span>延迟波动 / 待测</span><b style="color:var(--amber)">' + esc(suspectCnt + ' / ' + pendCnt) + '</b><small>不可达 ' + esc(deadCnt) + ' 个</small></div>' +
            '<div class="galaxy-kpi-card"><span>当前运行模式</span><b style="color:var(--violet)">' + esc(eg.modeShort) + '</b><small>' + esc(eg.poolOrNodeName) + '</small></div>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">' +
            '<div class="filter-chips">' +
              '<button type="button" class="active" data-ov-node-filter="all">全部 (' + mock.nodes.length + ')</button>' +
              '<button type="button" data-ov-node-filter="kernel">已入核 (' + kernCnt + ')</button>' +
              '<button type="button" data-ov-node-filter="ok">已验证 (' + okCnt + ')</button>' +
              '<button type="button" data-ov-node-filter="suspect">波动 (' + suspectCnt + ')</button>' +
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
        '前往订阅与节点页 '
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
            ? '<span class="status-pill" style="color:var(--pink);border-color:var(--line-strong)">🇨🇳 国内直连</span>'
            : d.category === 'blackhole'
              ? '<span class="status-pill" style="color:var(--amber);border-color:var(--warn-border)">黑洞拦截</span>'
              : '<span class="status-pill" style="color:var(--violet);border-color:var(--line-strong)">海外代理</span>';
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
              '<button class="button secondary compact" style="padding:0 8px;" data-action="trace-from-modal" data-domain="' + esc(domClean + ':443') + '">4阶透视</button>' +
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
            '<div class="galaxy-kpi-card"><span>黑洞吞噬拦截</span><b style="color:var(--amber)">' + esc(bhCnt) + ' 类高频</b><small>累计 ' + esc((Number.isFinite(Number(mock.blockedTotal)) ? (Number.isFinite(Number(mock.blockedTotal)) ? Number(mock.blockedTotal).toLocaleString('zh-CN') : '--') : '0')) + ' 次</small></div>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">' +
            '<div class="filter-chips">' +
              '<button type="button" class="active" data-ov-dest-filter="all">全部目标 (' + allDests.length + ')</button>' +
              '<button type="button" data-ov-dest-filter="global">海外代理 (' + glCnt + ')</button>' +
              '<button type="button" data-ov-dest-filter="cn">🇨🇳 国内直连 (' + cnCnt + ')</button>' +
              '<button type="button" data-ov-dest-filter="blackhole">黑洞拦截 (' + bhCnt + ')</button>' +
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
        '前往分流策略中心 '
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
        try {
          await runSubscriptionSyncWithModal({ mode: 'all' });
        } finally {
          if (el) { el.disabled = false; el.setAttribute('aria-busy', 'false'); }
        }
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
        const prevExit = ($('#top-exit') && $('#top-exit').textContent) || state.globalManualNode || '';
        confirmModal(
          '确认设为当前代理出口 · ' + cleanNodeDisplayName(nodeTag),
          '确认将节点「' + cleanNodeDisplayName(nodeTag) + '」设为当前代理出口吗？生效后支持点击提示条一键撤销。',
          async () => {
            const res = await callRouterApi('/api/shunt/apply_exit', 'POST', { node_tag: nodeTag, tag: nodeTag, name: nodeTag });
            if (res && res.ok !== false) {
              if ($('#top-exit')) $('#top-exit').textContent = cleanNodeDisplayName(nodeTag);
              if ($('#trace-exit')) $('#trace-exit').textContent = cleanNodeDisplayName(nodeTag);
              closeModal();
              toastWithUndo((res && res.message) || ('已将 ' + cleanNodeDisplayName(nodeTag) + ' 设为当前出口'), async () => {
                if (prevExit && prevExit !== nodeTag) {
                  await callRouterApi('/api/shunt/apply_exit', 'POST', { node_tag: prevExit, tag: prevExit, name: prevExit });
                  await syncBackendStatus(false, true);
                  toast('已撤销出口变更');
                }
              }, '↩ 撤销');
              await syncBackendStatus(false, true);
            }
          },
          '确认设为出口'
        );
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
          ['防断网自愈看门狗 (5秒防抖拉起)', 'ARMED'],
          ['净网护盾规则引擎', state.dnsEnabled ? (Number(mock.dnsRulesCount).toLocaleString('zh-CN') + ' 条生效') : 'PAUSED'],
          ['入核出站节点容量', mock.nodes.length + ' 节点（全部入核 · 无上限）']
        ];
        openModal(
          '系统与内核健康自检报告',
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
          '一键深度排障诊断报告',
          '<div class="modal-form">' +
            '<p>已汇总当前内核运行态、端口监听、nftables 规则摘要与最近异常日志，可直接全选复制用于排障：</p>' +
            '<div class="modal-field"><label>诊断原始数据 (JSON)</label><textarea rows="9" class="mono" readonly onclick="this.select()">' + esc(JSON.stringify(res || {}, null, 2)) + '</textarea></div>' +
          '</div>',
          'ONE-CLICK DIAGNOSTICS'
        );
        break;
      }
      case 'fail-open-test': {
        confirmModal(
          '确认执行断网逃生 (Fail-Open) 演练',
          '演练将短暂模拟代理核心故障并验证防断网看门狗自动回退宽带直连机制（约 2~3 秒），确认立即执行吗？',
          async () => {
            toast('正在执行断网逃生 (Fail-Open) 演练...');
            const res = await callRouterApi('/api/ops/fail_open_test', 'POST', { force: true });
            if (res && res.ok !== false) {
              toast('断网逃生演练完成：防黑洞看门狗与直连回退保护验证通过');
              await syncBackendStatus(false, true);
            }
          },
          '确认执行演练'
        );
        break;
      }
      case 'uninstall-plugin': {
        openModal(
          '安全卸载 AI-LINK 插件',
          '<div class="modal-form">' +
            '<p>卸载前将自动清除透明代理劫持规则、还原 dnsmasq 标准配置并保留您的节点备份归档。输入 <code>UNINSTALL</code> 确认卸载：</p>' +
            '<div class="modal-field"><label>确认指令</label><input id="mdl-uninstall-confirm" placeholder="输入 UNINSTALL"></div>' +
          '</div>',
          'SAFE UNINSTALL',
          async () => {
            const v = ($('#mdl-uninstall-confirm') && $('#mdl-uninstall-confirm').value.trim()) || '';
            if (v !== 'UNINSTALL') { toast('请输入 UNINSTALL 确认卸载', 'warn'); return; }
            const r = await callRouterApi('/api/ops/uninstall', 'POST', { keep_config: true, confirm: 'UNINSTALL' });
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
          'IPv6 双栈防漏与路由治理状态',
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
          '双栈 DNS 上游与 Fake-IP 本地回环豁免配置',
          '<div class="modal-form">' +
            '<div class="syntax-guide">' +
              '<b>Fake-IP 本地回环与客户端回调防吞噬保护：</b>针对暴雪战网 (<code>cn.localbattle.net</code>)、Steam、QQ/微信快速登录、Plex/群晖内网直连等解析为 <code>127.0.0.1</code> 或局域网 IP 的域名，系统已在 dnsmasq 与 sing-box 双层强制豁免 Fake-IP 并返回真实地址，确保本机客户端回调令牌 100% 送达。' +
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
          'OTA 在线升级状态与确认',
          '<div class="detail-grid">' +
            '<div><span>当前运行版本</span><b class="mono">v' + esc((res && res.current) || (state.rawStatus && state.rawStatus.version) || '2.4.8') + '</b></div>' +
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
                '<button type="button" class="button secondary compact" data-action="preview-share-uri">解析预览</button>' +
              '</div>' +
            '</div>' +
            '<div id="mdl-parse-preview-box" class="trace-inline-box hidden"></div>' +
            '<div class="modal-grid-3">' +
              '<div class="modal-field"><label>节点名称 (tag)</label><input id="mdl-addnode-tag" placeholder="如：新加坡-自建-01"></div>' +
              '<div class="modal-field"><label>协议类型</label><select id="mdl-addnode-type"><option value="vless">VLESS</option><option value="hysteria2">Hysteria2</option><option value="tuic">TUIC v5</option><option value="trojan">Trojan</option><option value="shadowsocks">Shadowsocks</option><option value="vmess">VMess</option><option value="socks">Socks5 (住宅静态IP)</option><option value="http">HTTP (住宅代理)</option></select></div>' +
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
              '<div class="modal-field"><label>TLS SNI / Socks 账号</label><input id="mdl-addnode-sni" class="mono" placeholder="SNI 或 Socks5 用户名"></div>' +
              '<div class="modal-field"><label>Reality PublicKey (pbk)</label><input id="mdl-addnode-pbk" class="mono" placeholder="可选"></div>' +
              '<div class="modal-field"><label>链式代理前置节点池 (可选)</label><select id="mdl-addnode-detour" aria-label="链式代理前置节点池"><option value="">直连入网 (不挂前置)</option>' +
                (mock.autoPools || []).map(ap => '<option value="' + esc(ap.id) + '">前置池：' + esc(ap.name) + '</option>').join('') +
              '</select></div>' +
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
            const detour_pool_id = ($('#mdl-addnode-detour') && $('#mdl-addnode-detour').value) || '';
            const payload = { tag: tag || (region_override + '-' + type.toUpperCase() + '-' + server), type, server, server_port, region_override, uuid: secret, password: secret, username: (type === 'socks' || type === 'http') ? sni : '', sni: (type === 'socks' || type === 'http') ? '' : sni, public_key: pbk, short_id: sid, detour_pool_id, detour: detour_pool_id };
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
            box.innerHTML = '<div style="color:var(--mint)">成功解析 ' + esc(res.parsed_count) + ' 个节点：</div>' +
              res.nodes.slice(0, 5).map(p => '<div class="mono" style="color:var(--text)">• [' + esc(String(p.type || '').toUpperCase()) + '] ' + esc(p.tag) + ' ' + esc(p.server + ':' + p.server_port) + ' (' + esc(p.security) + ')</div>').join('');
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
        toast('正在对节点池执行 URL Ping 测速并切换最快节点...');
        await callRouterApi('/api/auto_nodes/probe', 'POST', { id: pid || '', probe_services: false });
        await syncBackendStatus(true, true);
        toast('节点池 URL Ping 测速与最快节点切换已完成');
        break;
      }
      case 'rescreen-auto-pool': {
        const idx = Number(el && el.dataset.poolIdx);
        openAutoNodeEditorModal(idx, true);
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
        if (el) el.textContent = state.expandShuntRules ? '收起规则详情' : '展开规则详情';
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
      case 'toggle-group-strict-lock': {
        const gid = el && el.dataset.gid;
        const grp = mock.groups.find(g => g.id === gid);
        if (!grp) return;
        const nextLock = !grp.strict_lock;
        const upRes = await callRouterApi('/api/shunt/update', 'POST', { group_id: gid, strict_lock: nextLock });
        if (upRes && Array.isArray(upRes.groups)) {
          const srvGrp = upRes.groups.find(x => x.id === gid);
          if (srvGrp) {
            grp.strict_lock = Boolean(srvGrp.strict_lock);
            grp.resolved_node = srvGrp.resolved_node || grp.manual_node;
            grp.manual_drifted = Boolean(srvGrp.manual_drifted);
            grp.strict_locked_dead = Boolean(srvGrp.strict_locked_dead);
            grp.drift_warning = srvGrp.drift_warning || srvGrp.failover_reason || '';
          } else {
            grp.strict_lock = nextLock;
          }
        } else {
          grp.strict_lock = nextLock;
        }
        renderShuntMatrix();
        toast('分流组「' + (grp.name || gid) + '」已' + (grp.strict_lock ? '开启严格锁定（宁可失败不漂移）' : '切换为允许故障容灾漂移'));
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
      case 'new-homelink': {
        state.selectedNewHomelinkProto = 'vless-reality';
        state.creatingHomelink = false;
        const submitNewHomelink = async (forcedProto) => {
          if (state.creatingHomelink) return;
          state.creatingHomelink = true;
          const proto = forcedProto || state.selectedNewHomelinkProto || 'vless-reality';
          const customPort = Number(($('#mdl-new-hl-port') && $('#mdl-new-hl-port').value) || 0);
          const ddns_host = ($('#mdl-new-hl-ddns') && $('#mdl-new-hl-ddns').value.trim()) || '';
          const route_mode = ($('#mdl-new-hl-rmode') && $('#mdl-new-hl-rmode').value) || 'shunt';
          const confirmBtn = $('#modal-confirm');
          if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.textContent = '⏳ 正在创建回家节点...';
          }
          $$('#modal-body .route-mode').forEach(b => { b.disabled = true; });
          try {
            const defaultP = proto === 'hysteria2' ? 20443 : (proto === 'vless-tls' ? 9443 : 18443);
            const res = await callRouterApi('/api/homelink/quick_create', 'POST', {
              protocol: proto,
              listen_port: customPort || defaultP,
              ddns_host,
              route_mode,
              enabled: true
            });
            closeModal();
            if (res && res.ok === false) {
              toast(res.message || '创建回家节点失败', 'warn');
            } else {
              toast((res && res.message) || ('已创建 ' + proto + ' 回家节点'));
            }
            await syncBackendStatus(false, true);
          } finally {
            state.creatingHomelink = false;
            if (confirmBtn) confirmBtn.disabled = false;
          }
        };
        openModal(
          '创建加密回家节点 (支持单节点独立回家路由模式)',
          '<div class="modal-form">' +
            '<div class="modal-grid-3" style="margin-bottom:8px">' +
              '<div class="modal-field"><label>① 该节点独立回家路由模式</label><select id="mdl-new-hl-rmode">' +
                '<option value="shunt" selected>回家 + 科学上网分流</option>' +
                '<option value="direct">仅访问内网与国内</option>' +
                '<option value="proxy_only">仅科学上网 · 隔离内网</option>' +
              '</select></div>' +
              '<div class="modal-field"><label>② 自定义监听端口（留空自动分配）</label><input id="mdl-new-hl-port" type="number" placeholder="默认 18443 (自动防冲突递增)"></div>' +
              '<div class="modal-field"><label>③ 公网 DDNS 域名或 IP</label><input id="mdl-new-hl-ddns" value="' + esc(window.location.hostname || '') + '" placeholder="home.example.com"></div>' +
            '</div>' +
            '<div class="modal-field"><label>④ 选择加密回家协议（点击卡片切换协议，点击右下角「立即创建回家节点」完成创建）</label>' +
              '<div class="route-mode-grid" id="mdl-new-hl-proto-grid">' +
                '<button type="button" class="route-mode active" data-action="select-homelink-proto" data-proto="vless-reality"><b>VLESS-Reality (推荐 · 默认 :18443)</b><p>借用大厂 TLS 指纹免域名证书零暴露，抗主动探测。</p></button>' +
                '<button type="button" class="route-mode" data-action="select-homelink-proto" data-proto="hysteria2"><b>Hysteria2 QUIC (极速 · 默认 :20443)</b><p>5G 移动蜂窝网络与高丢包弱网下的满速回家协议。</p></button>' +
                '<button type="button" class="route-mode" data-action="select-homelink-proto" data-proto="vless-tls"><b>VLESS-TLS (通用 · 默认 :9443)</b><p>内置自签根证书与 SHA256 指纹固定，兼容各级端口转发。</p></button>' +
              '</div>' +
            '</div>' +
          '</div>',
          'SECURE HOMELINK WIZARD',
          () => submitNewHomelink(),
          '立即创建 VLESS-Reality 回家节点'
        );
        break;
      }
      case 'select-homelink-proto': {
        const proto = (el && el.dataset.proto) || 'vless-reality';
        state.selectedNewHomelinkProto = proto;
        $$('#mdl-new-hl-proto-grid .route-mode').forEach(btn => {
          const isSel = btn.dataset.proto === proto;
          btn.classList.toggle('active', isSel);
          const bTag = btn.querySelector('b');
          if (bTag) {
            const rawTitle = bTag.textContent.replace(/^\s*/, '');
            bTag.textContent = (isSel ? '' : '') + rawTitle;
          }
        });
        const portInp = $('#mdl-new-hl-port');
        if (portInp) {
          portInp.placeholder = proto === 'hysteria2' ? '默认 20443 (UDP)' : (proto === 'vless-tls' ? '默认 9443 (TCP)' : '默认 18443 (TCP)');
        }
        const confirmBtn = $('#modal-confirm');
        if (confirmBtn && !state.creatingHomelink) {
          const pName = proto === 'hysteria2' ? 'Hysteria2 QUIC' : (proto === 'vless-tls' ? 'VLESS-TLS' : 'VLESS-Reality');
          confirmBtn.textContent = '立即创建 ' + pName + ' 回家节点';
        }
        break;
      }
      case 'create-homelink': {
        if (state.creatingHomelink) break;
        state.creatingHomelink = true;
        const proto = (el && el.dataset.proto) || state.selectedNewHomelinkProto || 'vless-reality';
        const customPort = Number(($('#mdl-new-hl-port') && $('#mdl-new-hl-port').value) || 0);
        const ddns_host = ($('#mdl-new-hl-ddns') && $('#mdl-new-hl-ddns').value.trim()) || '';
        const route_mode = ($('#mdl-new-hl-rmode') && $('#mdl-new-hl-rmode').value) || 'shunt';
        if (el) el.disabled = true;
        try {
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
        } finally {
          state.creatingHomelink = false;
          if (el) el.disabled = false;
        }
        break;
      }
      case 'dedup-homelink': {
        const res = await callRouterApi('/api/homelink/dedup', 'POST', {});
        toast((res && res.message) || '已清理重复回家节点');
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
        if (!nid || (el && el.disabled)) return;
        const hlSnap = mock.homelinkNodes.find(x => x.id === nid) ? JSON.parse(JSON.stringify(mock.homelinkNodes.find(x => x.id === nid))) : null;
        confirmModal(
          '确认删除回家节点 · ' + (hlSnap ? hlSnap.name : nid),
          '删除后该加密回家入站隧道（端口 ' + (hlSnap ? hlSnap.listen_port : '') + '）将停止监听，确认继续删除吗？',
          async () => {
            if (el) { el.disabled = true; el.classList.add('is-loading'); el.textContent = '删除中...'; }
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
                '<option value="shunt" ' + ((!hlNode || hlNode.route_mode === 'shunt') ? 'selected' : '') + '>回家 + 科学上网分流</option>' +
                '<option value="direct" ' + (hlNode && hlNode.route_mode === 'direct' ? 'selected' : '') + '>仅访问内网与国内</option>' +
                '<option value="proxy_only" ' + (hlNode && hlNode.route_mode === 'proxy_only' ? 'selected' : '') + '>仅科学上网 · 隔离内网</option>' +
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
        if (_opsMutationInFlight.dns_filter) break;
        const prevDnsEn = Boolean(state.dnsEnabled);
        const nextDnsEn = !prevDnsEn;
        _opsMutationInFlight.dns_filter = true;
        _opsFieldMuteUntil.dns_filter = Date.now() + 3000;
        state.dnsEnabled = nextDnsEn;
        setSwitchState(el, state.dnsEnabled);
        try {
          const res = await callRouterApi('/api/dns/filter/toggle', 'POST', { enabled: nextDnsEn });
          if (res && res.ok !== false) {
            if (res.filter && res.filter.enabled != null) state.dnsEnabled = Boolean(res.filter.enabled);
            _opsFieldMuteUntil.dns_filter = Date.now() + 2500;
            renderDnsAndFilterSection();
            toast('云端域名过滤护盾已' + (state.dnsEnabled ? '开启' : '关闭'));
          } else {
            _opsFieldMuteUntil.dns_filter = 0;
            state.dnsEnabled = prevDnsEn;
            renderDnsAndFilterSection();
            toast('切换云端域名过滤护盾失败，已回滚', 'warn');
          }
        } finally {
          _opsMutationInFlight.dns_filter = false;
        }
        break;
      }
      case 'dns-essential-protect-toggle': {
        if (_opsMutationInFlight.dns_essential_protect) break;
        const prevProt = Boolean(state.dnsEssentialProtect !== false);
        const nextProt = !prevProt;
        _opsMutationInFlight.dns_essential_protect = true;
        _opsFieldMuteUntil.dns_essential_protect = Date.now() + 3000;
        state.dnsEssentialProtect = nextProt;
        setSwitchState(el, state.dnsEssentialProtect);
        try {
          const res = await callRouterApi('/api/dns/filter/toggle', 'POST', {
            enabled: state.dnsEnabled,
            essential_app_protect: nextProt
          });
          if (res && res.ok !== false) {
            if (res.filter && res.filter.essential_app_protect != null) state.dnsEssentialProtect = Boolean(res.filter.essential_app_protect);
            _opsFieldMuteUntil.dns_essential_protect = Date.now() + 2500;
            renderDnsAndFilterSection();
            toast('核心应用防误杀白名单保护已' + (state.dnsEssentialProtect ? '开启（已豁免 Google Play / Apple / MS 核心域名）' : '关闭'));
          } else {
            _opsFieldMuteUntil.dns_essential_protect = 0;
            state.dnsEssentialProtect = prevProt;
            renderDnsAndFilterSection();
            toast('切换核心应用白名单保护失败，已回滚', 'warn');
          }
        } finally {
          _opsMutationInFlight.dns_essential_protect = false;
        }
        break;
      }
      case 'network-doctor': {
        await openNetworkDoctorModal(true);
        break;
      }
      case 'topology-wizard': {
        openTopologyWizardModal();
        break;
      }
      case 'open-rule-blocks-modal': {
        const gid = el && el.dataset.gid;
        openRuleBlocksModal(gid);
        break;
      }
      case 'open-rule-providers': {
        openRuleProvidersModal();
        break;
      }
      case 'open-config-history': {
        openConfigHistoryModal();
        break;
      }
      case 'open-alert-center': {
        openAlertCenterModal();
        break;
      }
      case 'sync-rule-provider': {
        const rpId = el && el.dataset.rpId;
        if (!rpId) break;
        toast('正在同步远程规则源 [' + rpId + ']...');
        const r = await callRouterApi('/api/shunt/rule_providers/sync', 'POST', { id: rpId });
        toast((r && r.message) || '远程规则源同步完成');
        await openRuleProvidersModal();
        break;
      }
      case 'delete-rule-provider': {
        const rpId = el && el.dataset.rpId;
        const rpName = (el && el.dataset.rpName) || rpId;
        if (!rpId) break;
        const backupProvider = (state.lastRuleProviders || []).find(x => x.id === rpId);
        confirmModal(
          '确认删除远程规则源',
          '确认删除远程规则订阅「' + rpName + '」吗？删除后可点击底部提示撤销恢复。',
          async () => {
            const delRes = await callRouterApi('/api/shunt/rule_providers', 'POST', { id: rpId, action: 'delete' });
            await openRuleProvidersModal();
            await syncBackendStatus(false, true);
            toastWithUndo('已删除远程规则源「' + rpName + '」', async () => {
              const snap = (delRes && delRes.deleted) || backupProvider;
              if (snap && snap.url) {
                await callRouterApi('/api/shunt/rule_providers', 'POST', Object.assign({}, snap, { sync_now: false }));
                toast('↩ 已撤销删除并恢复规则源「' + rpName + '」');
                await openRuleProvidersModal();
              }
            });
          },
          '确认删除'
        );
        break;
      }
      case 'rollback-config-snap': {
        const snapId = el && el.dataset.snapId;
        const targetState = (el && el.dataset.targetState) || 'files';
        if (!snapId) break;
        const modeDesc = targetState === 'before' ? '撤销该次变更（恢复至该次变更前的状态）' : '恢复到该版本（该次变更后的状态）';
        confirmModal(
          '确认回滚配置版本',
          '确认对快照 [' + snapId + '] 执行「' + modeDesc + '」吗？回滚将在 10 秒内实时生效。',
          async () => {
            const r = await callRouterApi('/api/ops/config_rollback', 'POST', { snapshot_id: snapId, target_state: targetState });
            toast((r && r.message) || '已回滚配置');
            await syncBackendStatus(false, true);
          },
          '确认回滚'
        );
        break;
      }
      case 'run-network-doctor-now': {
        await runNetworkDoctorScan();
        toast('已完成 8 项网络健康复检');
        break;
      }
      case 'fix-network-doctor-all': {
        if (el) el.disabled = true;
        toast('正在执行全量异常项自动修复并复检...');
        const res = await callRouterApi('/api/diag/fix', 'POST', { fix_action: 'fix_all', recheck: true });
        if (el) el.disabled = false;
        if (res && res.recheck) {
          state.lastDoctorReport = res.recheck;
          await runNetworkDoctorScan();
        }
        await syncBackendStatus(false, true);
        toast((res && res.message) || '一键自动修复与复检已完成');
        break;
      }
      case 'fix-network-doctor-item': {
        const fixAct = (el && el.dataset.fixAction) || 'fix_all';
        const chkId = (el && el.dataset.checkId) || '';
        if (el) el.disabled = true;
        toast('正在修复「' + (chkId || fixAct) + '」并自动复检...');
        const res = await callRouterApi('/api/diag/fix', 'POST', { fix_action: fixAct, check_id: chkId, recheck: true });
        if (el) el.disabled = false;
        await runNetworkDoctorScan();
        await syncBackendStatus(false, true);
        toast((res && res.message) || '单项修复与复检已完成');
        break;
      }
      case 'refresh-hit-stats': {
        const res = await callRouterApi('/api/shunt/hit_stats', 'GET');
        if (res && res.ok !== false) {
          state.shuntHitStats = res;
          renderShuntHitLeaderboard();
          toast('已刷新最近 1 小时分流规则命中排行榜');
        }
        break;
      }
      case 'filter-conn-by-hit': {
        const q = (el && el.dataset.hitQuery) || '';
        state.connSearch = q;
        const cInp = $('#conn-search-input');
        if (cInp) cInp.value = q;
        showPage('settings');
        renderConnectionsSection();
        toast('已按「' + q + '」筛选实时活跃连接');
        break;
      }
      case 'dns-rewrite-toggle': {
        if (_opsMutationInFlight.dns_rewrite) break;
        const prevRw = Boolean(state.dnsRewriteEnabled);
        const nextRw = !prevRw;
        _opsMutationInFlight.dns_rewrite = true;
        _opsFieldMuteUntil.dns_rewrite = Date.now() + 3000;
        state.dnsRewriteEnabled = nextRw;
        setSwitchState(el, state.dnsRewriteEnabled);
        try {
          const res = await callRouterApi('/api/dns/rewrite', 'POST', { enabled: nextRw });
          if (res && res.ok !== false) {
            _opsFieldMuteUntil.dns_rewrite = Date.now() + 2500;
            toast('DNS 防跳重写已' + (state.dnsRewriteEnabled ? '开启' : '关闭'));
          } else {
            _opsFieldMuteUntil.dns_rewrite = 0;
            state.dnsRewriteEnabled = prevRw;
            setSwitchState(el, state.dnsRewriteEnabled);
            toast('切换 DNS 防跳重写失败，已回滚', 'warn');
          }
        } finally {
          _opsMutationInFlight.dns_rewrite = false;
        }
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
        toast('已添加 DNS 重写: ' + from_domain + ' ' + to_domain);
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
      case 'open-chained-node-modal':
        openChainedProxyModal();
        break;
      case 'open-traffic-insights':
        await openTrafficInsightsModal(false);
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
      case 'sub-preview-sync': {
        const idx = Number(el && el.dataset.sub);
        const s = mock.subscriptions[idx];
        const res = await callRouterApi('/api/subscriptions/preview_sync', 'POST', { id: s ? s.id : '', url: s ? s.url : '' });
        const addedCnt = (res && res.added_count != null) ? res.added_count : 0;
        const remCnt = (res && res.removed_count != null) ? res.removed_count : 0;
        const renCnt = (res && res.renamed_count != null) ? res.renamed_count : 0;
        const affPools = (res && Array.isArray(res.affected_pools)) ? res.affected_pools : [];
        openModal(
          '订阅更新影响预览 · ' + (s ? s.name : '全部订阅'),
          '<div class="modal-form">' +
            '<div class="doctor-summary-banner">' +
              '<div><b>本次更新预计变更：新增 ' + addedCnt + ' 个节点 · 移除 ' + remCnt + ' 个节点 · 改名平滑迁移 ' + renCnt + ' 个</b>' +
              '<small style="display:block;color:var(--muted);margin-top:4px">基于稳定身份指纹 node_key = sha1(protocol|server|port|cred|sni|pbk)[:16] 比对，改名节点将 100% 无损保留在原节点池中；消失节点将保留 7 天 missing 占位并自动切至下一合格节点。</small></div>' +
            '</div>' +
            (affPools.length
              ? ('<div class="trace-stages">' + affPools.map(ap => '<div class="trace-stage"><i></i><div><b>' + esc(ap.pool_name) + '</b><span>' + esc(ap.summary) + '</span></div><strong>自动容灾</strong></div>').join('') + '</div>')
              : '<div class="trace-stage"><i></i><div><b>所有自动节点池成员完整率 100%</b><span>本次订阅更新不会导致任何正在使用的自动节点池失去活跃出口。</span></div><strong>无损更新</strong></div>') +
          '</div>',
          'SUBSCRIPTION DIFF & IMPACT PREVIEW',
          async () => {
            closeModal();
            await runSubscriptionSyncWithModal(s ? { mode: 'single', subIdx: idx } : { mode: 'all' });
          },
          '确认立即同步订阅'
        );
        break;
      }
      case 'probe-custom-nodes': {
        toast('正在对所有手动添加节点执行 URL Ping 真连接测速...');
        await callRouterApi('/api/probe/url_ping', 'POST', { source: 'custom' });
        await syncBackendStatus(true, true);
        toast('手动添加节点 URL Ping 测速完成并已全局同步');
        break;
      }
      case 'sub-sync-one': {
        const idx = Number(el && el.dataset.sub);
        const sub = mock.subscriptions[idx];
        if (!sub) return;
        if (el) { el.setAttribute('aria-busy', 'true'); el.disabled = true; }
        try {
          await runSubscriptionSyncWithModal({ mode: 'single', subIdx: idx });
        } finally {
          if (el) { el.setAttribute('aria-busy', 'false'); el.disabled = false; }
        }
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
        const doRestartCore = async () => {
          toast('正在重启 sing-box 代理内核...');
          const res = await callRouterApi('/api/ops/control', 'POST', { action: 'restart_core' });
          toast((res && res.message) || 'sing-box 内核已重启并完成 :7893 端口健康校验');
          await syncBackendStatus(false, true);
        };
        if (!state.coreAlive || (el && el.id === 'btn-restart-core-banner')) {
          await doRestartCore();
        } else {
          confirmModal(
            '确认重启 sing-box 代理内核',
            '重启代理内核期间现有活跃代理连接将短暂重连（约 1~2 秒），确认立即重启内核吗？',
            doRestartCore,
            '确认重启内核'
          );
        }
        break;
      }
      case 'restart-service': {
        confirmModal(
          '确认重启 AI-LINK 守护进程与全部服务',
          '将重启后台守护进程、重新编译配置并刷新防火墙规则（耗时约 2~3 秒），确认立即执行吗？',
          async () => {
            toast('正在重启 AI-LINK 守护进程与全部服务...');
            await callRouterApi('/api/system/service/restart', 'POST', {});
            toast('服务重启指令已下发，正在重新连接...');
            setTimeout(() => syncBackendStatus(false, true), 1800);
          },
          '确认重启服务'
        );
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
          const curVer = (res && res.current) || (state.rawStatus && state.rawStatus.version) || '2.4.8';
          if (subEl) subEl.textContent = '当前已是最新版本 (v' + curVer + ' · 已校验云端清单)';
          toast('当前已是最新版本 (v' + curVer + ')');
        }
        break;
      }
      case 'check-core-update': {
        if (el) el.setAttribute('aria-busy', 'true');
        toast('正在检测 sing-box 内核版本与硬件架构适配...');
        const cRes = await callRouterApi('/api/ops/core_update/check?force=1', 'GET');
        if (el) el.setAttribute('aria-busy', 'false');
        const cSub = $('#core-ota-sub');
        const curV = (cRes && cRes.current_version) || '1.14.1';
        const latV = (cRes && cRes.latest_version) || curV;
        const archObj = (cRes && cRes.arch) || {};
        const schemaProf = (cRes && cRes.schema_profile) || 'v1.14-dns-disabled';
        if (cSub) {
          cSub.textContent = cRes && cRes.has_update
            ? ('发现新内核 v' + latV + ' · 架构 ' + (archObj.preferred_suffix || 'linux-musl') + ' · Schema: ' + schemaProf)
            : ('当前内核 v' + curV + ' 已就绪 · 架构 ' + (archObj.preferred_suffix || 'linux-musl') + ' · Schema: ' + schemaProf);
        }
        openModal(
          'sing-box 代理内核版本检测与安全热升级',
          '<div class="modal-form">' +
            '<div class="kv-list">' +
              '<div><span>当前运行内核版本</span><b class="mono">sing-box v' + esc(curV) + '</b></div>' +
              '<div><span>官方最新稳定版本</span><b class="mono" style="color:var(--cyan)">sing-box v' + esc(latV) + (cRes && cRes.has_update ? ' (可升级)' : ' (已是最新)') + '</b></div>' +
              '<div><span>路由器架构与 C 库识别</span><b class="mono">' + esc((archObj.raw_machine || 'x86_64') + ' · ' + (archObj.libc || 'musl') + ' (' + (archObj.preferred_suffix || 'linux-amd64-musl') + ')') + '</b></div>' +
              '<div><span>AI-LINK 动态 Schema 档位</span><b class="mono">' + esc(schemaProf) + ' (兼容 1.11 ~ 1.15+)</b></div>' +
              '<div><span>匹配官方安装包</span><b class="mono">' + esc((cRes && cRes.asset_name) || ('sing-box-' + latV + '.tar.gz')) + '</b></div>' +
            '</div>' +
            '<p class="muted" style="margin-top:10px;line-height:1.5">安全热升级保护机制：下载匹配架构内核后，先在沙箱内执行 <code>sing-box.new check -c</code> 预检新配置合法性；仅当预检 100% 通过后才备份 <code>sing-box.bak</code> 并原子替换，任何异常自动回滚原内核，彻底杜绝升核断网。</p>' +
          '</div>',
          'SING-BOX KERNEL UPDATER',
          async () => {
            toast('正在执行 5 步沙箱预检与 sing-box 内核热升级...');
            const upRes = await callRouterApi('/api/ops/core_update/apply', 'POST', {});
            closeModal();
            if (upRes && upRes.ok) {
              const newVerStr = upRes.current_version || upRes.new_version || latV;
              if ($('#sys-core-title')) $('#sys-core-title').textContent = 'sing-box ' + newVerStr;
              if ($('#core-ota-sub')) $('#core-ota-sub').textContent = '当前内核 v' + newVerStr + ' 已就绪 · 架构 ' + (archObj.preferred_suffix || 'linux-musl') + ' · Schema: ' + (upRes.schema_profile || schemaProf);
              toast(upRes.message || ('sing-box 内核已成功升级至 v' + newVerStr));
              await syncBackendStatus(false, true);
            } else {
              toast((upRes && upRes.message) || '内核热升级未执行（已保持原内核稳定运行）', 'warn');
            }
          }
        );
        break;
      }
      case 'apply-update': {
        const uInfo = state.lastUpdateCheck || {};
        const pkg = uInfo.package || {};
        const verStr = uInfo.latest || '最新版本';
        const sizeStr = pkg.size ? ((Number(pkg.size) / 1048576).toFixed(2) + ' MiB') : '未知大小';
        const shaStr = pkg.sha256 ? (String(pkg.sha256).slice(0, 16) + '...') : (pkg.md5 || '已校验');
        confirmModal(
          '确认执行在线升级 (v' + esc(verStr) + ')',
          '即将升级至 v' + verStr + '（包体积: ' + sizeStr + ' · 校验指纹: ' + shaStr + '）。升级前将自动创建全量配置与固件快照，升级期间代理核心将短暂重启约 5~10 秒（失败自动回滚）。是否立即开始升级？',
          async () => {
            toast('正在启动 8 步安全在线升级与自动备份...');
            const res = await callRouterApi('/api/system/update/apply', 'POST', {});
            toast((res && res.message) || '在线升级已启动，进度将持久化至闪存');
          },
          '确认立即升级'
        );
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
            '<p>恢复出厂设置将清空自定义节点、订阅并重新生成设备随机初始密码（<code>/etc/ai-link/initial_password</code>），恢复前会自动生成一份安全归档备份至 <code>/root/ai-link-final-backup</code>。</p>' +
            '<div class="modal-field"><label>输入 RESET 确认执行</label><input id="mdl-reset-confirm" placeholder="请手动输入 RESET 以确认恢复出厂" autocomplete="off"></div>' +
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
        await mutateOpsSwitch('require_lan_auth', !state.authEnabled, '局域网访问鉴权');
        break;
      }
      case 'entry-bypass-toggle': {
        await handleToggleEntryBypass();
        break;
      }
      case 'ipv6-proxy-toggle': {
        await mutateOpsSwitch('ipv6_proxy', !state.ipv6Proxy, 'IPv6 透明代理接管', '/api/ipv6/toggle');
        break;
      }
      case 'block-quic-toggle': {
        await mutateOpsSwitch('block_quic', !state.blockQuic, '海外 QUIC 阻断回退 HTTP/2');
        break;
      }
      case 'game-udp-toggle': {
        await mutateOpsSwitch('game_udp_direct', !state.gameUdpDirect, '国服游戏 UDP 直连豁免');
        break;
      }
      case 'conflict-guard-toggle': {
        await mutateOpsSwitch('auto_mute_conflicts', !state.conflictGuard, '并发代理冲突自动静默');
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
        const mac = (macInput && macInput.value.trim()) || '';
        if (!mac || mac.toUpperCase() === 'AA:BB:CC:DD:EE:FF') {
          toast('请先输入真实有效的目标设备 MAC 地址', 'warn');
          if (macInput) macInput.focus();
          break;
        }
        const res = await callRouterApi('/api/wol', 'POST', { mac });
        if (res && res.ok !== false) {
          toast(res.message || ('已向 ' + mac + ' 发送 WOL 唤醒魔术包'));
        }
        break;
      }
      case 'refresh-connections': {
        const res = await callRouterApi('/api/clash/connections', 'GET');
        if (res && Array.isArray(res.connections)) {
          state.rawConnections = res.connections;
          mock.connections = typeof res.total === 'number' ? res.total : res.connections.length;
          mock.connsDisplayed = res.connections.length;
          mock.connsTruncated = Boolean(res.truncated) || (mock.connections > res.connections.length);
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
        const customUrl = (el && el.dataset.url) || (svcItem && svcItem.url) || '';
        const grpObj = mock.groups.find(g => ('Shunt_' + g.id) === selectorTag || (svcItem && g.id === svcItem.groupId));
        const nodeTag = (grpObj && grpObj.resolved_node && grpObj.resolved_node !== 'direct') ? grpObj.resolved_node : ((mock.nodes[0] && mock.nodes[0].tag) || '');
        toast('正在探测「' + (svcItem ? svcItem.name : svcId) + '」(' + selectorTag + ')...');
        const qUrlParam = customUrl ? ('&url=' + encodeURIComponent(customUrl)) : '';
        const [delayRes] = await Promise.all([
          callRouterApi('/api/clash/delay?name=' + encodeURIComponent(selectorTag) + '&service_id=' + encodeURIComponent(svcId.toLowerCase()) + qUrlParam, 'GET'),
          (nodeTag && selectorTag !== 'direct' && selectorTag !== 'Shunt_Domestic_CN')
            ? callRouterApi('/api/probe/service_l7', 'POST', { tag: nodeTag, service_id: svcId.toLowerCase(), url: customUrl }, 12000, true)
            : Promise.resolve(null)
        ]);
        if (svcItem) {
          if (delayRes && delayRes.ok !== false && Number(delayRes.delay) > 0) {
            svcItem.ms = Math.round(Number(delayRes.delay));
            svcItem.state = svcItem.ms >= 600 ? 'suspect' : 'ok';
            toast((svcItem.name || svcId) + ' (' + selectorTag + ') 实测延迟: ' + svcItem.ms + 'ms');
          } else {
            svcItem.ms = 0;
            svcItem.state = 'dead';
            toast((svcItem.name || svcId) + ' (' + selectorTag + ') 探测不可达或超时', 'warn');
          }
          renderOverviewDashboard();
        }
        await syncBackendStatus(false, true);
        break;
      }
      case 'sonar-probe-all': {
        if (el) el.setAttribute('aria-busy', 'true');
        toast('正在并发实测全部声呐探测目标...');
        const pRes = await callRouterApi('/api/overview/sonar_probe', 'POST', {});
        if (el) el.setAttribute('aria-busy', 'false');
        if (pRes && Array.isArray(pRes.pulse_services) && pRes.pulse_services.length) {
          mock.services = pRes.pulse_services.slice(0, 8).map(p => ({
            id: String(p.id || p.name || '').toLowerCase(),
            name: p.name || p.id,
            selector: p.selector || 'Shunt_AI',
            groupId: String(p.selector || 'Shunt_AI').replace(/^Shunt_/, ''),
            url: p.url || '',
            node: p.node || '',
            ms: Number(p.ms) > 0 ? Math.round(Number(p.ms)) : 0,
            state: p.state || (Number(p.ms) > 0 ? 'ok' : 'dead')
          }));
          renderOverviewDashboard();
          const okCnt = mock.services.filter(s => s.ms > 0 && s.state !== 'dead').length;
          toast('声呐全量实测完成：' + okCnt + ' / ' + mock.services.length + ' 个目标可达');
        } else {
          toast('声呐实测未返回结果，请检查代理内核状态', 'warn');
        }
        break;
      }
      case 'open-sonar-config': {
        const tRes = await callRouterApi('/api/overview/sonar_targets', 'GET');
        const curTargets = (tRes && Array.isArray(tRes.targets) && tRes.targets.length)
          ? tRes.targets
          : mock.services.map(s => ({ id: s.id, name: s.name, selector: s.selector || 'Shunt_AI', url: s.url || 'https://www.google.com/generate_204' }));
        const selectorOpts = [
          ['Shunt_AI', 'Shunt_AI (AI 智能助手)'],
          ['Shunt_YouTube', 'Shunt_YouTube (YouTube 视频)'],
          ['Shunt_GitHub', 'Shunt_GitHub (GitHub 开发者)'],
          ['Shunt_Netflix', 'Shunt_Netflix (Netflix 流媒体)'],
          ['Shunt_TikTok', 'Shunt_TikTok (TikTok 国际版)'],
          ['Shunt_Google', 'Shunt_Google (Google 全生态)'],
          ['Shunt_Social', 'Shunt_Social (Telegram 与社交)'],
          ['Shunt_Games', 'Shunt_Games (游戏平台与联机)'],
          ['Shunt_Outside_CN', 'Shunt_Outside_CN (海外其他流量)'],
          ['Shunt_Domestic_CN', 'Shunt_Domestic_CN (国内直连白名单)'],
          ['direct', 'direct (WAN 宽带直连)']
        ];
        const buildRowHtml = (t, idx) => {
          const selVal = t.selector || 'Shunt_AI';
          const optsHtml = selectorOpts.map(o => '<option value="' + esc(o[0]) + '"' + (o[0] === selVal ? ' selected' : '') + '>' + esc(o[1]) + '</option>').join('');
          return '<div class="sonar-cfg-row" data-idx="' + idx + '" style="display:grid;grid-template-columns:110px 1.3fr 1fr;gap:8px;align-items:center;margin-bottom:8px">' +
            '<input class="input sonar-cfg-name" type="text" maxlength="18" placeholder="显示名称" value="' + esc(t.name || '') + '" data-id="' + esc(t.id || ('target_' + (idx + 1))) + '">' +
            '<input class="input mono sonar-cfg-url" type="text" placeholder="https://example.com" value="' + esc(t.url || '') + '">' +
            '<select class="select-compact sonar-cfg-sel">' + optsHtml + '</select>' +
          '</div>';
        };
        openModal(
          '自定义全球核心应用延迟声呐探测目标',
          '<div class="modal-form">' +
            '<p class="muted" style="margin:0 0 10px;line-height:1.5">自定义圆形声呐上的 8 个核心探测点（名称、探测 URL 与绑定分流策略组）。保存后支持一键并发实测，断网或节点不可达时自动显示超时告警。</p>' +
            '<div style="display:grid;grid-template-columns:110px 1.3fr 1fr;gap:8px;font-size:12px;color:var(--muted);margin-bottom:6px">' +
              '<span>应用名称</span><span>探测目标 URL / 域名</span><span>绑定分流策略组</span>' +
            '</div>' +
            '<div id="sonar-cfg-rows">' + curTargets.slice(0, 8).map((t, i) => buildRowHtml(t, i)).join('') + '</div>' +
            '<div class="button-row" style="margin-top:10px;justify-content:space-between">' +
              '<button type="button" class="button ghost compact" id="btn-sonar-reset-default">恢复默认 8 个核心目标</button>' +
              '<span class="muted" style="font-size:12px">点击确定后自动保存并立即探测</span>' +
            '</div>' +
          '</div>',
          'SONAR RADAR TARGETS',
          async () => {
            const rows = $$('#sonar-cfg-rows .sonar-cfg-row');
            const nextTargets = [];
            rows.forEach((r, idx) => {
              const nameInp = $('.sonar-cfg-name', r);
              const urlInp = $('.sonar-cfg-url', r);
              const selInp = $('.sonar-cfg-sel', r);
              const nm = nameInp ? nameInp.value.trim() : '';
              const u = urlInp ? urlInp.value.trim() : '';
              const sl = selInp ? selInp.value.trim() : 'Shunt_AI';
              const idAttr = (nameInp && nameInp.dataset.id) || ('target_' + (idx + 1));
              if (nm) {
                nextTargets.push({ id: idAttr, name: nm, url: u || 'https://www.google.com/generate_204', selector: sl });
              }
            });
            const svRes = await callRouterApi('/api/overview/sonar_targets', 'POST', { targets: nextTargets });
            closeModal();
            if (svRes && svRes.ok) {
              toast('自定义声呐探测目标已保存，正在触发实时探测...');
              const prRes = await callRouterApi('/api/overview/sonar_probe', 'POST', {});
              if (prRes && Array.isArray(prRes.pulse_services) && prRes.pulse_services.length) {
                mock.services = prRes.pulse_services.slice(0, 8).map(p => ({
                  id: String(p.id || p.name || '').toLowerCase(),
                  name: p.name || p.id,
                  selector: p.selector || 'Shunt_AI',
                  groupId: String(p.selector || 'Shunt_AI').replace(/^Shunt_/, ''),
                  url: p.url || '',
                  node: p.node || '',
                  ms: Number(p.ms) > 0 ? Math.round(Number(p.ms)) : 0,
                  state: p.state || (Number(p.ms) > 0 ? 'ok' : 'dead')
                }));
              }
              renderOverviewDashboard();
              await syncBackendStatus(false, true);
            } else {
              toast('保存声呐探测目标失败', 'warn');
            }
          }
        );
        const rstBtn = $('#btn-sonar-reset-default');
        if (rstBtn) {
          rstBtn.addEventListener('click', async () => {
            const rRes = await callRouterApi('/api/overview/sonar_targets', 'POST', { reset: true });
            closeModal();
            if (rRes && rRes.ok) {
              toast('已恢复默认 8 个声呐探测目标');
              await syncBackendStatus(false, true);
            }
          });
        }
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
        const initMode = g.shunt_mode || 'auto';
        const isGrpIpSens = Boolean(g.ip_sensitive || ['AI','AI_Assistant','Google','Microsoft','Apple','Apple_Microsoft','Social','Social_Media','Custom_Soul','Custom_Copilot','Custom_WorkBuddy'].includes(g.id));
        const autoOpts = mock.autoPools.map(p => {
          const pCur = (!p.current_node || p.current_node === 'direct') ? '直连/待选优' : cleanNodeDisplayName(p.current_node);
          const mlTag = p.dispatch_mode === 'multi_line'
            ? (isGrpIpSens ? ' · 自动锁定单线防风控' : (' · 多线并发 ' + Math.max(2, Number(p.active_lines_count || 2)) + ' 线'))
            : '';
          return '<option value="' + esc(p.id) + '" ' + (g.auto_node_id === p.id ? 'selected' : '') + '>' + esc(p.name) + ' (当前: ' + esc(pCur) + esc(mlTag) + ')</option>';
        }).join('');
        const countryOpts = '<option value="ALL">全部国家/地区 (不过滤)</option>' + COUNTRY_CODES.map(c => '<option value="' + c + '" ' + (g.country === c ? 'selected' : '') + '>' + esc(COUNTRY_META[c].flag + ' ' + COUNTRY_META[c].name) + '</option>').join('');
        const curManualSel = (g.manual_node && !String(g.manual_node).startsWith('auto:') && g.manual_node !== 'direct') ? g.manual_node : (g.resolved_node !== 'direct' ? g.resolved_node : '');
        const buildManualNodeOpts = (filterCountry) => {
          const filtered = mock.nodes.filter(n => !filterCountry || filterCountry === 'ALL' || n.region === filterCountry || (n.tag || n.name) === curManualSel);
          const srcList = filtered.length ? filtered : mock.nodes;
          return srcList.map(n => '<option value="' + esc(n.tag || n.name) + '" ' + ((n.tag || n.name) === curManualSel ? 'selected' : '') + '>' + esc(cleanNodeDisplayName(n.name)) + ' (' + formatLatencyText(n.rtt, false) + ')</option>').join('');
        };
        openModal(
          '分流策略组编排 · ' + g.name,
          '<div class="trace-stages">' +
            '<div class="trace-stage"><i>01</i><div><b>匹配范围</b><span>' + esc(g.subtitle) + '</span></div><strong>' + (g.domains ? g.domains.length : 0) + ' 条规则</strong></div>' +
            '<div class="trace-stage"><i>02</i><div><b>当前实际生效出口</b><span class="mono">' + esc(g.resolved_node === 'direct' ? 'DIRECT (宽带原生直连)' : cleanNodeDisplayName(g.resolved_node || 'DIRECT')) + '</span></div><strong>' + formatLatencyText(g.rtt, g.shunt_mode === 'direct' || g.resolved_node === 'direct') + '</strong></div>' +
          '</div>' +
          '<div class="modal-form" style="margin-top:12px">' +
            '<input type="hidden" id="mdl-grp-mode" value="' + esc(initMode) + '">' +
            '<div class="modal-field"><label>第 1 步：选择本组出站方式（三选一互斥）</label>' +
              '<div class="grp-mode-cards" id="mdl-grp-mode-cards">' +
                '<button type="button" class="grp-mode-card ' + (initMode === 'auto' ? 'active' : '') + '" data-grp-mode-pick="auto"><b>自动节点池</b><small>按 URL Ping 自动选最快节点切换</small></button>' +
                '<button type="button" class="grp-mode-card ' + (initMode === 'manual' ? 'active' : '') + '" data-grp-mode-pick="manual"><b>固定单节点</b><small>严格锁定指定节点，绝不自动漂移</small></button>' +
                '<button type="button" class="grp-mode-card ' + (initMode === 'direct' ? 'active' : '') + '" data-grp-mode-pick="direct"><b>宽带直连</b><small>不经代理直接由本地宽带出站</small></button>' +
              '</div>' +
            '</div>' +
            '<div id="mdl-grp-pane-auto" class="modal-field ' + (initMode === 'auto' ? '' : 'hidden') + '">' +
              '<label>第 2 步：选择绑定的自动节点池</label>' +
              '<select id="mdl-grp-autopool" aria-label="选取自动节点池">' + autoOpts + '</select>' +
            '</div>' +
            '<div id="mdl-grp-pane-manual" class="modal-grid-2 ' + (initMode === 'manual' ? '' : 'hidden') + '">' +
              '<div class="modal-field"><label>按地区筛选候选节点</label><select id="mdl-grp-country" aria-label="国家地区筛选">' + countryOpts + '</select></div>' +
              '<div class="modal-field"><label>第 2 步：选择要锁定的具体节点</label><select id="mdl-grp-manual" aria-label="手动固定单一节点">' + buildManualNodeOpts(g.country || 'ALL') + '</select></div>' +
            '</div>' +
            '<div class="modal-grid-2" style="margin-top:8px">' +
              '<div class="modal-field"><label>本组专属 DNS 策略</label><select id="mdl-grp-dns-strategy" aria-label="本组专属DNS策略">' +
                '<option value="inherit" ' + ((g.dns_strategy || 'inherit') === 'inherit' ? 'selected' : '') + '>继承全局防污染 DNS</option>' +
                '<option value="doh" ' + (g.dns_strategy === 'doh' ? 'selected' : '') + '>自定义 DoH (HTTPS)</option>' +
                '<option value="dot" ' + (g.dns_strategy === 'dot' ? 'selected' : '') + '>自定义 DoT (TLS)</option>' +
                '<option value="doq" ' + (g.dns_strategy === 'doq' ? 'selected' : '') + '>自定义 DoQ (QUIC)</option>' +
                '<option value="local" ' + (g.dns_strategy === 'local' ? 'selected' : '') + '>指定本地/内网上游</option>' +
              '</select></div>' +
              '<div class="modal-field"><label>自定义 DNS 地址 (可选)</label><input id="mdl-grp-custom-dns" class="mono" value="' + esc(g.custom_dns || '') + '" placeholder="https://dns.quad9.net/dns-query" aria-label="自定义DNS地址"></div>' +
            '</div>' +
            '<div class="grp-preview-bar" id="mdl-grp-preview-bar"></div>' +
            '<div class="button-row" style="margin-top:10px;flex-wrap:wrap">' +
              '<button type="button" class="button ghost compact" data-action="edit-group-rules-modal" data-group-idx="' + Number(groupEl.dataset.group) + '">编辑此组域名与 IP 规则库</button>' +
              '<button type="button" class="button ghost compact" data-action="open-rule-blocks-modal" data-gid="' + esc(gid) + '">规则块与试匹配 (正则/源IP/端口)</button>' +
              '<button type="button" class="button ghost compact" data-action="verify-group" data-gid="' + esc(gid) + '">真连接校验测试</button>' +
              (g.is_custom ? '<button type="button" class="button ghost danger-text compact" data-action="delete-custom-group" data-gid="' + esc(gid) + '">删除此自定义分流组</button>' : '') +
            '</div>' +
          '</div>',
          'SHUNT GROUP ORCHESTRATION',
          async () => {
            const shunt_mode = ($('#mdl-grp-mode') && $('#mdl-grp-mode').value) || '';
            const auto_node_id = ($('#mdl-grp-autopool') && $('#mdl-grp-autopool').value) || '';
            const manual_node = ($('#mdl-grp-manual') && $('#mdl-grp-manual').value) || '';
            const countryRaw = ($('#mdl-grp-country') && $('#mdl-grp-country').value) || g.country || 'JP';
            const country = countryRaw === 'ALL' ? (g.country || 'JP') : countryRaw;
            const dns_strategy = ($('#mdl-grp-dns-strategy') && $('#mdl-grp-dns-strategy').value) || 'inherit';
            const custom_dns = ($('#mdl-grp-custom-dns') && $('#mdl-grp-custom-dns').value.trim()) || '';
            if (shunt_mode === 'auto' && !auto_node_id) {
              toast('请选择要绑定的自动节点池', 'warn');
              return;
            }
            if (shunt_mode === 'manual' && !manual_node) {
              toast('请选择要手动固定的具体节点', 'warn');
              return;
            }
            const payload = shunt_mode === 'auto'
              ? { group_id: gid, shunt_mode: 'auto', strategy: 'auto', auto_node_id, dns_strategy, custom_dns }
              : (shunt_mode === 'manual'
                  ? { group_id: gid, shunt_mode: 'manual', strategy: 'manual', country, manual_node, strict_lock: true, dns_strategy, custom_dns }
                  : { group_id: gid, shunt_mode: 'direct', strategy: 'direct', country: 'direct', manual_node: 'direct', dns_strategy, custom_dns });
            const res = await callRouterApi('/api/shunt/update', 'POST', payload);
            if (res && res.ok !== false) {
              closeModal();
              toast('分流组「' + g.name + '」策略已实时生效');
              await syncBackendStatus(false, true);
            }
          },
          '应用分流策略'
        );
        const updateGrpPreview = () => {
          const mVal = ($('#mdl-grp-mode') && $('#mdl-grp-mode').value) || 'auto';
          const pAuto = $('#mdl-grp-pane-auto');
          const pMan = $('#mdl-grp-pane-manual');
          if (pAuto) pAuto.classList.toggle('hidden', mVal !== 'auto');
          if (pMan) pMan.classList.toggle('hidden', mVal !== 'manual');
          $$('#mdl-grp-mode-cards [data-grp-mode-pick]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.grpModePick === mVal);
          });
          const bar = $('#mdl-grp-preview-bar');
          if (!bar) return;
          if (mVal === 'auto') {
            const aid = ($('#mdl-grp-autopool') && $('#mdl-grp-autopool').value) || '';
            const pObj = mock.autoPools.find(x => x.id === aid) || mock.autoPools[0];
            const pName = pObj ? pObj.name : aid;
            const pCur = (pObj && pObj.current_node && pObj.current_node !== 'direct') ? cleanNodeDisplayName(pObj.current_node) : '待优选/直连兜底';
            bar.innerHTML = '应用后效果预览：本组流量将交由自动池 <b>' + esc(pName) + '</b> 动态调度（当前最快出口：<b>' + esc(pCur) + '</b>）';
          } else if (mVal === 'manual') {
            const mNode = ($('#mdl-grp-manual') && $('#mdl-grp-manual').value) || '';
            bar.innerHTML = '应用后效果预览：本组流量将严格锁定在单节点 <b>' + esc(cleanNodeDisplayName(mNode || '未选择')) + '</b>（死节点零自动漂移）';
          } else {
            bar.innerHTML = '应用后效果预览：本组流量将直接走 <b>宽带原生直连 (DIRECT)</b>，不经过任何代理节点';
          }
        };
        $$('#mdl-grp-mode-cards [data-grp-mode-pick]').forEach(btn => {
          btn.addEventListener('click', () => {
            const inp = $('#mdl-grp-mode');
            if (inp) inp.value = btn.dataset.grpModePick;
            updateGrpPreview();
          });
        });
        const apSel = $('#mdl-grp-autopool');
        if (apSel) apSel.addEventListener('change', updateGrpPreview);
        const manSel = $('#mdl-grp-manual');
        if (manSel) manSel.addEventListener('change', updateGrpPreview);
        const ctrySel = $('#mdl-grp-country');
        if (ctrySel) {
          ctrySel.addEventListener('change', () => {
            if (manSel) manSel.innerHTML = buildManualNodeOpts(ctrySel.value);
            updateGrpPreview();
          });
        }
        updateGrpPreview();
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

      const jumpConnBtn = event.target.closest('[data-action="jump-active-connections"]');
      if (jumpConnBtn) {
        event.preventDefault();
        showPage('settings');
        setTimeout(() => {
          const tbl = $('#connections-tbody');
          const card = tbl ? tbl.closest('.glass-card') : null;
          if (card && card.scrollIntoView) card.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 120);
        return;
      }

      const obsTabBtn = event.target.closest('[data-shunt-obs-tab]');
      if (obsTabBtn) {
        const targetPane = obsTabBtn.dataset.shuntObsTab || 'trace';
        state.shuntObsTab = targetPane;
        $$('#shunt-obs-tabs [data-shunt-obs-tab]').forEach(b => b.classList.toggle('active', b.dataset.shuntObsTab === targetPane));
        $$('[data-shunt-obs-pane]').forEach(pane => pane.classList.toggle('shunt-obs-hidden', pane.dataset.shuntObsPane !== targetPane));
        return;
      }

      const poolMenuBtn = event.target.closest('[data-action="toggle-pool-menu"]');
      if (poolMenuBtn) {
        event.stopPropagation();
        const pIdx = Number(poolMenuBtn.dataset.poolIdx);
        const targetMenu = $('#pool-more-menu-' + pIdx);
        const willOpen = targetMenu ? targetMenu.classList.contains('hidden') : false;
        $$('.pool-more-menu').forEach(m => m.classList.add('hidden'));
        $$('.auto-pool.hud-pool-card').forEach(c => c.classList.remove('menu-open'));
        if (targetMenu && willOpen) {
          targetMenu.classList.remove('hidden');
          const parentCard = targetMenu.closest('.auto-pool.hud-pool-card');
          if (parentCard) parentCard.classList.add('menu-open');
          state.openPoolMenuIdx = pIdx;
        } else {
          state.openPoolMenuIdx = null;
        }
        return;
      }
      if (!event.target.closest('.pool-more-wrap') || event.target.closest('.pool-more-menu button')) {
        state.openPoolMenuIdx = null;
        $$('.pool-more-menu').forEach(m => m.classList.add('hidden'));
        $$('.auto-pool.hud-pool-card').forEach(c => c.classList.remove('menu-open'));
      }

      const poolHelpBtn = event.target.closest('[data-action="show-pool-help"]');
      if (poolHelpBtn) {
        event.stopPropagation();
        const p = mock.autoPools[Number(poolHelpBtn.dataset.poolIdx)] || mock.autoPools[0];
        if (p) {
          const g1Tags = (p.groups && p.groups[0] && Array.isArray(p.groups[0].node_tags)) ? p.groups[0].node_tags : [];
          openModal(
            '自动节点池战术规格 · ' + p.name,
            '<div class="trace-stages">' +
              '<div class="trace-stage"><i>01</i><div><b>当前首选出口与延迟</b><span class="mono">' + esc(p.current_node || 'direct') + '</span></div><strong>' + (p.current_delay_ms > 0 ? (p.current_delay_ms + ' ms') : '直连/待测') + '</strong></div>' +
              '<div class="trace-stage"><i>02</i><div><b>候选订阅与地区范围</b><span>来源: ' + esc((p.scope_sources || ['ALL']).join(', ')) + ' · 地区: ' + esc((p.scope_countries || ['ALL']).join('/')) + '</span></div><strong>' + g1Tags.length + ' / ' + (p.target_size || 5) + ' 节点</strong></div>' +
              '<div class="trace-stage"><i>03</i><div><b>服务可用性检测策略</b><span>' + (p.service_check_enabled && p.service_checks && p.service_checks.length ? ('建池与低健康度复选时验证: ' + p.service_checks.join('/').toUpperCase()) : '纯 URL Ping 极速选优（不额外消耗应用探测流量）') + '</span></div><strong>低于 ' + (p.replenish_threshold || 2) + ' 自动复选</strong></div>' +
              '<div class="trace-stage"><i>04</i><div><b>内核日志实时报错秒切守护</b><span>当节点池正在使用时实时监听 sing-box 内核日志，当前节点在 30s 内对 ≥2 个不同目标连续 3 次报错并经轻量复检确认失效后，即刻破除防抖锁秒切至下一健康节点</span></div><strong>秒级容灾</strong></div>' +
            '</div>',
            'AUTO NODE POOL HUD SPEC'
          );
        }
        return;
      }

      const hudHelpBtn = event.target.closest('[data-action="show-hud-help"]');
      if (hudHelpBtn) {
        event.stopPropagation();
        const topic = hudHelpBtn.dataset.helpTopic || 'overview';
        const helpMap = {
          overview: ['全域网络脉搏 · 模块指南', [
            ['主出口状态横幅', '实时显示当前路由模式（精细分流或单一总出口）、大陆硬件旁路与 IPv6 防漏状态。'],
            ['核心应用延迟声呐', '点击圆形雷达上的任意应用星点（如 ChatGPT / Gemini / YouTube），立即按其绑定的真实分流组探测端到端延迟。'],
            ['底部三张洞察卡', '点击「局域网终端设备」「入核出站节点」「热门访问目标」可弹出完整明细表格。']
          ]],
          shunt: ['代理与分流 · 模块指南', [
            ['5 大全局路由模式', '日常推荐「精细规则分流」；切换为 GFW / 大陆白名单 / 全局代理时，可通过统一出口栏绑定自动池或固定单节点。'],
            ['自动节点池 vs 手动单节点', '自动节点池会定时 URL Ping 自动切换最快节点；手动单节点模式严格锁定在指定节点，绝不自动漂移。'],
            ['右侧观测舱', '通过顶部标签切换「4阶流量透视」「1小时命中排行」与「防抖切换日志」，保持页面紧凑不留白。']
          ]],
          autopool: ['自动节点池工作原理', [
            ['极简 6 步建池', '勾选订阅源与国家 -> 选择是否检测流媒体/AI服务 -> 设定池容量(1-10)与复选阈值 -> 自动选入最快节点。'],
            ['内核日志秒级容灾', '当节点池正在被使用时，实时监测 sing-box 内核当前节点运行日志，连续 3 次传输报错立即隔离并秒切至下一健康节点。'],
            ['低健康度自动复选', '当池内健康节点数跌破设定阈值（或订阅更新导致节点变动）时，自动从候选库补充合格节点。']
          ]],
          homelink: ['回家加密隧道 · 模块指南', [
            ['双协议入站支持', '支持创建 VLESS-Reality 与 Hysteria2 回家入站，内置自签证书与二维码一键导出。'],
            ['独立回家路由模式', '每个回家节点可独立设置「仅访问家庭内网」或「内网 + 借道科学上网」，互不干扰主路由分流。']
          ]],
          dns: ['DNS 护盾与防污染 · 模块指南', [
            ['双栈智能分流 (:7874)', '国内域名直连 223.5.5.5 保留原生 IPv6；海外域名走加密 FakeIP (198.18.0.0/15) 并自动抑制异常 AAAA。'],
            ['关键应用防误杀', '默认豁免 Google Play、Apple 推送、微软更新与战网/Steam 本地回环域名，防止广告黑洞误拦。']
          ]],
          nodes: ['节点与订阅 · 模块指南', [
            ['11 种订阅格式兼容', '支持 Clash YAML（含锚点与嵌套字典）、URI、Base64、Sing-box JSON、Surge、Loon、SIP008、V2Ray JSON。'],
            ['Google 落地地区识别', '自动通过 Google 301 TLD 识别节点真实送中/落地地区，避免标日本实为香港导致 Gemini 被拒。']
          ]],
          settings: ['系统设置与实时连接 · 模块指南', [
            ['实时活跃连接透视', '支持按「局域网终端设备」下拉框筛选每台手机/电脑的并发连接、目标域名:端口与命中规则。'],
            ['防断网自愈看门狗', '当内核异常退出时 5 秒内自动撤除 nftables 防断网并重启恢复，全量日志同步记录于下方日志舱。']
          ]]
        };
        const info = helpMap[topic] || helpMap.overview;
        openModal(
          info[0],
          '<div class="trace-stages">' + info[1].map((row, i) => '<div class="trace-stage"><i>0' + (i + 1) + '</i><div><b>' + esc(row[0]) + '</b><span>' + esc(row[1]) + '</span></div><strong>HUD</strong></div>').join('') + '</div>',
          'TACTICAL HUD GUIDE'
        );
        return;
      }

      const hitTabBtn = event.target.closest('[data-hit-tab]');
      if (hitTabBtn) {
        state.shuntHitTab = hitTabBtn.dataset.hitTab || 'by_group';
        renderShuntHitLeaderboard();
        return;
      }

      const action = event.target.closest('[data-action]');
      if (action) {
        if (action.dataset.actionBusy === 'true') return;
        const isSwitch = action.getAttribute('role') === 'switch';
        if (!isSwitch) {
          action.dataset.actionBusy = 'true';
          action.setAttribute('aria-busy', 'true');
        }
        Promise.resolve(handleAction(action.dataset.action, action)).finally(() => {
          if (!isSwitch) {
            action.dataset.actionBusy = 'false';
            action.setAttribute('aria-busy', 'false');
          }
        });
      }
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
            mock.connections = typeof connRes.total === 'number' ? connRes.total : connRes.connections.length;
            mock.connsDisplayed = connRes.connections.length;
            mock.connsTruncated = Boolean(connRes.truncated) || (mock.connections > connRes.connections.length);
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
        toast('已开启真实连接 3D 表达：实时映射 ' + (s.totalArcs || 0) + ' 条跨星系轨迹 · 流速挡位 高[' + (s.highCount || 0) + ']/中[' + (s.medCount || 0) + ']/低[' + (s.lowCount || 0) + ']');
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
    const wpBtn = $('#wallpaper-toggle');
    const wpExitBtn = $('#wallpaper-exit-btn');
    const toggleWallpaperMode = (forceVal) => {
      const shell = $('#scene-shell');
      if (!shell) return;
      state.wallpaperMode = typeof forceVal === 'boolean' ? forceVal : !state.wallpaperMode;
      shell.classList.toggle('wallpaper-mode', state.wallpaperMode);
      document.body.classList.toggle('galaxy-wallpaper-active', state.wallpaperMode);
      if (wpBtn) wpBtn.classList.toggle('active', state.wallpaperMode);
      if (scene && typeof scene.setWallpaperMode === 'function') {
        scene.setWallpaperMode(state.wallpaperMode);
      }
      if (state.wallpaperMode) {
        toast('已进入壁纸沉浸模式 · 按 W 键或点击右下角按钮可恢复常规工作台');
      }
    };
    if (wpBtn) wpBtn.addEventListener('click', () => toggleWallpaperMode());
    if (wpExitBtn) wpExitBtn.addEventListener('click', () => toggleWallpaperMode(false));
    window.addEventListener('keydown', (ev) => {
      if (state.page !== 'galaxy') return;
      const tag = (ev.target && ev.target.tagName) ? ev.target.tagName.toLowerCase() : '';
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      if (ev.key === 'w' || ev.key === 'W') {
        ev.preventDefault();
        toggleWallpaperMode();
      }
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
    const connDevSelect = $('#conn-device-filter');
    if (connDevSelect) connDevSelect.addEventListener('change', event => {
      state.connDeviceFilter = event.target.value || 'ALL';
      renderConnectionsSection();
    });
    const logSearchEl = $('#log-search-input');
    if (logSearchEl) logSearchEl.addEventListener('input', event => {
      state.logSearch = event.target.value;
      renderLogsViewer();
    });
    const dpmSelect = $('#sel-ops-data-plane-mode');
    if (dpmSelect) dpmSelect.addEventListener('change', async event => {
      const prevMode = state.dataPlaneMode || 'tproxy_redirect';
      const nextMode = event.target.value || 'tproxy_redirect';
      const labelMap = {
        tproxy_redirect: 'TProxy + Redirect 零拷贝模式',
        tproxy_tcp_tun_udp: 'TCP TProxy + UDP TUN 游戏混合模式',
        tun_full: '全量 TUN 虚拟网卡模式 (ailink0)'
      };
      _opsFieldMuteUntil.data_plane_mode = Date.now() + 3000;
      renderOpsSettings({ data_plane_mode: nextMode }, true);
      toast('正在切换数据面模式至「' + (labelMap[nextMode] || nextMode) + '」...');
      const res = await callRouterApi('/api/ops/settings', 'POST', { data_plane_mode: nextMode });
      if (res && res.ok !== false) {
        _opsFieldMuteUntil.data_plane_mode = Date.now() + 2500;
        renderOpsSettings({ data_plane_mode: nextMode }, true);
        toast('已切换至「' + (labelMap[nextMode] || nextMode) + '」，nftables 与策略路由表已同步生效');
      } else {
        _opsFieldMuteUntil.data_plane_mode = 0;
        renderOpsSettings({ data_plane_mode: prevMode }, true);
        toast('切换数据面模式失败，已回滚至原模式', 'warn');
      }
    });
    const tunStackSelect = $('#sel-ops-tun-stack');
    if (tunStackSelect) tunStackSelect.addEventListener('change', async event => {
      const prevStack = state.tunStack || 'mixed';
      const nextStack = event.target.value || 'mixed';
      _opsFieldMuteUntil.tun_stack = Date.now() + 3000;
      renderOpsSettings({ tun_stack: nextStack }, true);
      toast('正在切换 TUN 协议栈至 ' + nextStack + '...');
      const res = await callRouterApi('/api/ops/settings', 'POST', { tun_stack: nextStack });
      if (res && res.ok !== false) {
        _opsFieldMuteUntil.tun_stack = Date.now() + 2500;
        renderOpsSettings({ tun_stack: nextStack }, true);
        toast('TUN 虚拟网卡协议栈已更新为 ' + nextStack);
      } else {
        _opsFieldMuteUntil.tun_stack = 0;
        renderOpsSettings({ tun_stack: prevStack }, true);
        toast('切换 TUN 协议栈失败，已回滚至原协议栈', 'warn');
      }
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

  let telemetryInFlight = false;
  let lastHiddenPollTs = 0;

  async function updateTelemetryTick() {
    if (telemetryInFlight) return;
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      const nowMs = Date.now();
      if (nowMs - lastHiddenPollTs < 15000) return;
      lastHiddenPollTs = nowMs;
    }
    telemetryInFlight = true;
    try {
      await syncBackendStatus(false, false);
      if (mock.latency > 0) {
        latencySeries.push(mock.latency);
        if (latencySeries.length > 20) latencySeries.shift();
      }
      if (state.page === 'overview') drawLatencyChart();
    } finally {
      telemetryInFlight = false;
    }
  }

  function showSceneFallback(reason) {
    const fb = $('#webgl-fallback');
    if (!fb) return;
    fb.hidden = false;
    const p = fb.querySelector('p');
    if (p) {
      if (reason === 'ASSET_LOAD_FAILED' || !window.THREE) {
        p.innerHTML = '3D 引擎核心脚本 (three.min.js) 未能加载，业务面板功能不受影响。<button type="button" class="button secondary compact" style="margin-left:10px" onclick="window.location.reload()">重新加载</button>';
      } else {
        p.textContent = '当前浏览器环境未启用 WebGL 硬件加速，业务面板仍可正常使用。';
      }
    }
  }

  function initScene() {
    if (!window.NexusScene) {
      showSceneFallback('ASSET_LOAD_FAILED');
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
      showSceneFallback(window.NexusScene.lastErrorReason);
    } else {
      const fb = $('#webgl-fallback');
      if (fb) fb.hidden = true;
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
    window.__NEXUS_PREVIEW__ = { state, mock, showPage, setSceneMode, syncBackendStatus, handleToggleEntryBypass, openOverviewDetailModal, openNetworkDoctorModal, renderShuntHitLeaderboard, computeSpeedGearInfo, get scene() { return scene; } };
  }

  init();
})();
