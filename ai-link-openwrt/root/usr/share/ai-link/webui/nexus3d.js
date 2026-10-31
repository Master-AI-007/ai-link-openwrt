(function () {
  'use strict';
  if (window.NexusScene) return;

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const MAX_GALAXY_SATELLITES = 8;
  const MAX_BLACKHOLE_SATELLITES = 6;
  const MAX_LIVE_CONN_ARCS = 16;

  function fmtRateShort(bps) {
    const n = Number(bps || 0);
    if (!isFinite(n) || n <= 0) return '0 B/s';
    const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    let idx = 0;
    let val = n;
    while (val >= 1024 && idx < units.length - 1) { val /= 1024; idx++; }
    return (idx === 0 ? String(Math.round(val)) : val.toFixed(val >= 100 ? 0 : 1)) + ' ' + units[idx];
  }

  /* 3-Tier Speed Gear Engine (高 / 中 / 低) driven by real connection count & throughput rate */
  function computeSpeedGear(rateBps, conns) {
    const bps = Math.max(0, Number(rateBps || 0));
    const c = Math.max(0, Number(conns || 0));
    if (bps >= 200 * 1024 || c >= 12) {
      return {
        gear: 'high',
        label: '高',
        fullLabel: '高速',
        speed: 0.56,
        scale: 1.36,
        activeRatio: 1.0,
        badgeColor: '#6ee7f5'
      };
    }
    if (bps >= 15 * 1024 || c >= 3) {
      return {
        gear: 'med',
        label: '中',
        fullLabel: '中速',
        speed: 0.26,
        scale: 1.04,
        activeRatio: 0.65,
        badgeColor: '#f9a8d4'
      };
    }
    return {
      gear: 'low',
      label: '低',
      fullLabel: '低速',
      speed: (bps > 0 || c > 0) ? 0.095 : 0.055,
      scale: 0.78,
      activeRatio: 0.38,
      badgeColor: '#8ea0bc'
    };
  }

  class NexusUniverse {
    constructor(canvas, options) {
      this.canvas = canvas;
      this.shell = document.getElementById('scene-shell');
      this.labelLayer = document.getElementById('node-labels');
      this.labelCanvas = document.getElementById('label-canvas');
      this.labelCtx = this.labelCanvas.getContext('2d');
      this.tooltip = document.getElementById('node-tooltip');
      this.options = options || {};
      this.active = true;
      this.autoRotate = !reducedMotion;
      this.showLabels = false;
      this.surge = false;
      this.mode = 'panorama';
      this.selected = null;
      this.selectedMesh = null;
      this.dragging = false;
      this.dragDistance = 0;
      this.centers = {};
      this.selectable = [];
      this.labelObjects = [];
      this.packets = [];
      this.beams = [];
      this.beamsByKey = {};
      this.liveConnArcs = [];
      this.liveConnPackets = [];
      this.liveConnSummary = { totalArcs: 0, totalConns: 0, highCount: 0, medCount: 0, lowCount: 0 };
      this.lastSyncPayload = null;
      this.satellitesByCenter = { core: [], cn: [], global: [], blackhole: [] };
      this.clock = new THREE.Clock();
      this.raycaster = new THREE.Raycaster();
      this.pointer = new THREE.Vector2();
      this.current = { theta: .12, phi: 1.22, radius: 25.5, target: new THREE.Vector3(0, 0, 0) };
      this.desired = { theta: .12, phi: 1.22, radius: 25.5, target: new THREE.Vector3(0, 0, 0) };
      this.init();
    }

    computeSpeedGear(rateBps, conns) {
      return computeSpeedGear(rateBps, conns);
    }

    init() {
      this.renderer = null;
      try {
        this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.65));
        this.renderer.setClearColor(0x02040a, 0);
        if ('outputEncoding' in this.renderer && THREE.sRGBEncoding) this.renderer.outputEncoding = THREE.sRGBEncoding;
        if ('toneMapping' in this.renderer && THREE.ACESFilmicToneMapping) {
          this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
          this.renderer.toneMappingExposure = .96;
        }
      } catch (_) {
        this.renderer = null;
      }
      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.FogExp2(0x050710, .014);
      this.camera = new THREE.PerspectiveCamera(43, 1, .1, 180);
      this.world = new THREE.Group();
      this.scene.add(this.world);
      this.liveConnGroup = new THREE.Group();
      this.liveConnGroup.visible = false;
      this.world.add(this.liveConnGroup);
      this.scene.add(new THREE.AmbientLight(0x7080a0, .78));
      const key = new THREE.PointLight(0x78e8ff, 1.5, 58);
      key.position.set(3, 9, 12);
      this.scene.add(key);
      const rim = new THREE.PointLight(0xf9a8d4, 1.15, 48);
      rim.position.set(-10, 2, -8);
      this.scene.add(rim);
      this.glowTexture = this.createGlowTexture();
      this.buildBackdrop();
      this.buildCenters();
      this.buildInitialSatellites();
      this.buildBeams();
      this.buildSelectionHalo();
      this.bindControls();
      this.resizeObserver = new ResizeObserver(() => this.resize());
      this.resizeObserver.observe(this.shell);
      this.setMode('panorama');
      this.resize();
      this.updateCamera(1);
      if (this.renderer && this.renderer.setAnimationLoop) {
        this.renderer.setAnimationLoop(() => this.render());
      } else {
        const tick = () => { this.render(); requestAnimationFrame(tick); };
        requestAnimationFrame(tick);
      }
    }

    createGlowTexture() {
      const c = document.createElement('canvas');
      c.width = c.height = 128;
      const x = c.getContext('2d');
      const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
      g.addColorStop(0, 'rgba(255,255,255,1)');
      g.addColorStop(.12, 'rgba(255,255,255,.9)');
      g.addColorStop(.35, 'rgba(255,255,255,.25)');
      g.addColorStop(1, 'rgba(255,255,255,0)');
      x.fillStyle = g;
      x.fillRect(0, 0, 128, 128);
      return new THREE.CanvasTexture(c);
    }

    glow(color, scale, opacity) {
      const material = new THREE.SpriteMaterial({ map: this.glowTexture, color, transparent: true, opacity: opacity == null ? .45 : opacity, blending: THREE.AdditiveBlending, depthWrite: false });
      const sprite = new THREE.Sprite(material);
      sprite.scale.set(scale, scale, 1);
      return sprite;
    }

    /* Clean spatial reference backdrop: removed meaningless decorative spiral dust & random nebula clouds */
    buildBackdrop() {
      const starCount = 420;
      const positions = new Float32Array(starCount * 3);
      const colors = new Float32Array(starCount * 3);
      const color = new THREE.Color();
      for (let i = 0; i < starCount; i++) {
        const r = 34 + (i % 7) * 9;
        const theta = (i * 2.39996) % (Math.PI * 2);
        const phi = Math.acos(1 - 2 * ((i + 0.5) / starCount));
        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.cos(phi);
        positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
        color.set(i % 5 === 0 ? 0x70ddff : 0x6c7c99);
        colors[i * 3] = color.r;
        colors[i * 3 + 1] = color.g;
        colors[i * 3 + 2] = color.b;
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
      this.stars = new THREE.Points(geometry, new THREE.PointsMaterial({ size: .09, vertexColors: true, transparent: true, opacity: .52, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true }));
      this.scene.add(this.stars);
    }

    buildCenters() {
      this.centers.core = this.createCenter({
        id: 'core',
        name: '内核中枢 · 局域网终端星系',
        short: '内核中枢',
        subtitle: 'sing-box · 117.4 MiB',
        kind: 'core',
        galaxy: 'core',
        position: [0, 0, 0],
        radius: 1.42,
        color: 0x28b8d4,
        emissive: 0x28b8d4,
        accent: 0x6ee7f5,
        cssColor: '#6ee7f5',
        label: '终端 3 台 · 117.4 MiB'
      });
      /* Domestic Direct Mother Planet in Soft Pink (淡粉色 #f9a8d4) */
      this.centers.cn = this.createCenter({
        id: 'cn',
        name: '国内直连星系 · WAN 宽带',
        short: '国内直连',
        subtitle: 'WAN 宽带原生直通',
        kind: 'cn',
        galaxy: 'cn',
        position: [-7.4, -2.0, 1.2],
        radius: .88,
        color: 0xf9a8d4,
        emissive: 0xf472b6,
        accent: 0xfbcfe8,
        cssColor: '#f9a8d4',
        label: '国内直连 · 5 目标'
      });
      this.centers.global = this.createCenter({
        id: 'global',
        name: '海外代理星系 · 全球分流',
        short: '海外代理',
        subtitle: '智能分流与双组自动池',
        kind: 'global',
        galaxy: 'global',
        position: [7.2, .85, -.8],
        radius: 1.04,
        color: 0x7656dd,
        emissive: 0x7656dd,
        accent: 0xa994ff,
        cssColor: '#a994ff',
        label: '海外代理 · 6 目标'
      });
      this.centers.blackhole = this.createBlackhole();
    }

    createCenter(data) {
      const group = new THREE.Group();
      group.position.fromArray(data.position);
      this.world.add(group);
      const material = new THREE.MeshPhysicalMaterial({
        color: data.color,
        emissive: data.emissive || data.color,
        emissiveIntensity: data.id === 'cn' ? .34 : .26,
        roughness: .22,
        metalness: .3,
        clearcoat: 1,
        clearcoatRoughness: .22,
        transparent: true,
        opacity: .95
      });
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(data.radius, 48, 32), material);
      mesh.userData.data = data;
      group.add(mesh);
      this.selectable.push(mesh);
      const glow = this.glow(data.color, data.radius * 5.2, data.id === 'cn' ? .40 : .32);
      group.add(glow);

      /* Single data-driven indicator ring (removed redundant triple decorative rings & random wireframes) */
      const rings = new THREE.Group();
      group.add(rings);
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(data.radius * 1.68, .014, 6, 120),
        new THREE.MeshBasicMaterial({ color: data.color, transparent: true, opacity: .28, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      ring.rotation.x = Math.PI / 2;
      rings.add(ring);

      /* Single clean satellite orbit track */
      const orbits = new THREE.Group();
      group.add(orbits);
      this.addOrbitLines(orbits, 1, data.color);
      const satGroup = new THREE.Group();
      group.add(satGroup);
      const center = { data, group, mesh, glow, rings, orbits, satGroup };
      this.addLabel(mesh, data, true);
      return center;
    }

    createBlackhole() {
      const data = {
        id: 'blackhole',
        name: '黑洞拦截中枢 · 净网护盾',
        short: '黑洞拦截',
        subtitle: 'DNS + 路由双层拦截吞噬',
        kind: 'blackhole',
        galaxy: 'blackhole',
        position: [-5.8, 5.0, -5.0],
        radius: 1.05,
        color: 0xf2a558,
        accent: 0xff6d45,
        cssColor: '#f7bd68',
        label: '黑洞拦截 · 守护中'
      };
      const group = new THREE.Group();
      group.position.fromArray(data.position);
      this.world.add(group);
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(data.radius, 40, 28), new THREE.MeshBasicMaterial({ color: 0x010206 }));
      mesh.userData.data = data;
      group.add(mesh);
      this.selectable.push(mesh);
      const disk = new THREE.Mesh(new THREE.RingGeometry(1.18, 2.55, 120, 1), new THREE.MeshBasicMaterial({ color: 0xf49a52, transparent: true, opacity: .38, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }));
      disk.rotation.x = 1.22;
      disk.rotation.y = .2;
      group.add(disk);
      const rings = new THREE.Group();
      group.add(rings);
      const torus = new THREE.Mesh(new THREE.TorusGeometry(1.48, .035, 8, 120), new THREE.MeshBasicMaterial({ color: 0xffb366, transparent: true, opacity: .68, blending: THREE.AdditiveBlending, depthWrite: false }));
      torus.rotation.x = 1.22;
      torus.rotation.y = .2;
      rings.add(torus);
      const glow = this.glow(0xff7a3d, 6.6, .48);
      group.add(glow);

      /* Data-driven inward-spiraling intercepted request particles (scaled by real blocked count) */
      const particleCount = 180;
      const pos = new Float32Array(particleCount * 3);
      this.bhParticleMeta = [];
      for (let i = 0; i < particleCount; i++) {
        const a = (i / particleCount) * Math.PI * 2;
        const r = 1.15 + (i % 10) * 0.22;
        const y = ((i % 5) - 2) * .03;
        pos[i * 3] = Math.cos(a) * r;
        pos[i * 3 + 1] = y;
        pos[i * 3 + 2] = Math.sin(a) * r;
        this.bhParticleMeta.push({ a, r, y, speed: .65 + (i % 4) * .18 });
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      const particles = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xffa45c, size: .055, transparent: true, opacity: .72, blending: THREE.AdditiveBlending, depthWrite: false }));
      particles.rotation.x = 1.22;
      group.add(particles);

      const orbits = new THREE.Group();
      group.add(orbits);
      this.addOrbitLines(orbits, 1, 0xf2a558);
      const satGroup = new THREE.Group();
      group.add(satGroup);
      const center = { data, group, mesh, glow, rings, orbits, satGroup, disk, particles };
      this.addLabel(mesh, data, true);
      return center;
    }

    addOrbitLines(targetGroup, count, color) {
      for (let j = 0; j < count; j++) {
        const r = 2.25 + j * .55;
        const points = [];
        for (let i = 0; i <= 120; i++) {
          const a = i / 120 * Math.PI * 2;
          points.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
        }
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color, transparent: true, opacity: .14, blending: THREE.AdditiveBlending, depthWrite: false }));
        targetGroup.add(line);
      }
    }

    buildInitialSatellites() {
      this.rebuildCenterSatellites('core', [
        { id: 'dev-nas', name: 'NAS-Server', short: 'NAS-Server', ip: '10.10.10.10', subtitle: '局域网终端 · 10.10.10.10', meta: '↓180 KB/s', down_rate: 184320, up_rate: 24576, conns: 8, kind: 'device', region: 'core', status: 'ok', topRank: 0 },
        { id: 'dev-pc', name: 'Workstation-PC', short: 'Workstation-PC', ip: '10.10.10.224', subtitle: '局域网终端 · 10.10.10.224', meta: '↓416 KB/s', down_rate: 425984, up_rate: 51200, conns: 15, kind: 'device', region: 'core', status: 'ok', topRank: 1 },
        { id: 'dev-phone', name: 'iPhone-15-Pro', short: 'iPhone-15-Pro', ip: '10.10.10.88', subtitle: '无线局域网 · 10.10.10.88', meta: '↓8 KB/s', down_rate: 8192, up_rate: 2048, conns: 2, kind: 'device', region: 'core', status: 'ok', topRank: 2 }
      ]);
      this.rebuildCenterSatellites('cn', [
        { id: 'cn-wechat', name: 'WeChat 微信', short: 'WeChat', domain: 'weixin.qq.com', subtitle: '国内直连 · WAN 原生出口', meta: '18 ms', rtt: 18, down_rate: 22528, up_rate: 4096, conns: 3, kind: 'service', region: 'cn', status: 'ok', topRank: 0 },
        { id: 'cn-bili', name: 'Bilibili 哔哩哔哩', short: 'Bilibili', domain: 'bilibili.com', subtitle: '国内直连 · 原生 IPv6/IPv4', meta: '24 ms', rtt: 24, down_rate: 312000, up_rate: 16384, conns: 6, kind: 'service', region: 'cn', status: 'ok', topRank: 1 },
        { id: 'cn-douyin', name: '抖音直播 CDN', short: '抖音 CDN', domain: 'douyincdn.com', subtitle: '国内直连 · 硬件级旁路', meta: '15 ms', rtt: 15, down_rate: 49152, up_rate: 4096, conns: 4, kind: 'service', region: 'cn', status: 'ok', topRank: 2 },
        { id: 'cn-taobao', name: 'Taobao 淘宝', short: 'Taobao', domain: 'taobao.com', subtitle: '国内直连 · 阿里公共 DNS', meta: '21 ms', rtt: 21, down_rate: 10240, up_rate: 2048, conns: 1, kind: 'service', region: 'cn', status: 'ok', topRank: 3 },
        { id: 'cn-jd', name: 'JD.com 京东', short: 'JD.com', domain: 'jd.com', subtitle: '国内直连 · WAN 原生出口', meta: '19 ms', rtt: 19, down_rate: 6144, up_rate: 1024, conns: 1, kind: 'service', region: 'cn', status: 'ok', topRank: 4 }
      ]);
      this.rebuildCenterSatellites('global', [
        { id: 'gl-openai', name: 'OpenAI / ChatGPT', short: 'ChatGPT', domain: 'chatgpt.com', subtitle: '海外代理 · Shunt_AI', meta: '156 ms', rtt: 156, down_rate: 61440, up_rate: 12288, conns: 4, kind: 'service', region: 'global', status: 'ok', topRank: 0 },
        { id: 'gl-youtube', name: 'YouTube 4K/8K', short: 'YouTube', domain: 'youtube.com', subtitle: '海外代理 · Shunt_YouTube', meta: '142 ms', rtt: 142, down_rate: 368640, up_rate: 16384, conns: 14, kind: 'service', region: 'global', status: 'ok', topRank: 1 },
        { id: 'gl-google', name: 'Google 全生态', short: 'Google', domain: 'google.com', subtitle: '海外代理 · Shunt_Google', meta: '138 ms', rtt: 138, down_rate: 40960, up_rate: 8192, conns: 3, kind: 'service', region: 'global', status: 'ok', topRank: 2 },
        { id: 'gl-github', name: 'GitHub 开发者', short: 'GitHub', domain: 'github.com', subtitle: '海外代理 · Shunt_GitHub', meta: '164 ms', rtt: 164, down_rate: 30720, up_rate: 6144, conns: 3, kind: 'service', region: 'global', status: 'ok', topRank: 3 },
        { id: 'gl-telegram', name: 'Telegram 通讯', short: 'Telegram', domain: 'telegram.org', subtitle: '海外代理 · Shunt_Social', meta: '148 ms', rtt: 148, down_rate: 8192, up_rate: 2048, conns: 2, kind: 'service', region: 'global', status: 'ok', topRank: 4 },
        { id: 'gl-netflix', name: 'Netflix 流媒体', short: 'Netflix', domain: 'netflix.com', subtitle: '海外代理 · Shunt_Netflix', meta: '112 ms', rtt: 112, down_rate: 245760, up_rate: 8192, conns: 5, kind: 'service', region: 'global', status: 'ok', topRank: 5 }
      ]);
      this.rebuildCenterSatellites('blackhole', [
        { id: 'bh-0', name: 'otheve.beacon.qq.com', short: 'beacon.qq.com', domain: 'otheve.beacon.qq.com', subtitle: '隐私遥测探针 · DNS REFUSED', meta: '392.2k次', conns: 16, rateBps: 0, kind: 'blocked', region: 'blackhole', status: 'blocked', topRank: 0 },
        { id: 'bh-1', name: 'btrace.qq.com', short: 'btrace.qq.com', domain: 'btrace.qq.com', subtitle: '隐私遥测探针 · DNS REFUSED', meta: '44.2k次', conns: 6, rateBps: 0, kind: 'blocked', region: 'blackhole', status: 'blocked', topRank: 1 },
        { id: 'bh-2', name: 'cpro.baidu.com', short: 'cpro.baidu.com', domain: 'cpro.baidu.com', subtitle: '商业广告联盟 · 路由 REJECT', meta: '4.5k次', conns: 2, rateBps: 0, kind: 'blocked', region: 'blackhole', status: 'blocked', topRank: 2 },
        { id: 'bh-3', name: 'googleads.g.doubleclick.net', short: 'doubleclick.net', domain: 'googleads.g.doubleclick.net', subtitle: '商业广告联盟 · 路由 REJECT', meta: '908次', conns: 1, rateBps: 0, kind: 'blocked', region: 'blackhole', status: 'blocked', topRank: 3 }
      ]);
    }

    /* Rebuild satellites for a given galaxy center with strict upper bound & 3-tier speed gear tether spheres */
    rebuildCenterSatellites(centerId, items) {
      const center = this.centers[centerId];
      if (!center || !center.satGroup) return;
      const cap = centerId === 'blackhole' ? MAX_BLACKHOLE_SATELLITES : MAX_GALAXY_SATELLITES;
      const list = (items || []).slice(0, cap);

      const oldMeshes = new Set(this.satellitesByCenter[centerId].map(s => s.mesh));
      this.selectable = this.selectable.filter(m => !oldMeshes.has(m));
      this.labelObjects = this.labelObjects.filter(l => !oldMeshes.has(l.object));
      while (center.satGroup.children.length) {
        center.satGroup.remove(center.satGroup.children[0]);
      }
      this.satellitesByCenter[centerId] = [];

      const count = Math.max(1, list.length);
      list.forEach((item, idx) => {
        const isBh = centerId === 'blackhole';
        const isCn = centerId === 'cn';
        const isCore = centerId === 'core';
        const col = isBh
          ? (idx % 2 === 0 ? 0xff7a45 : 0xf7bd68)
          : isCn
            ? (idx % 2 === 0 ? 0xf9a8d4 : 0xfbcfe8)
            : isCore
              ? (item.isRemote ? 0xa994ff : 0x6ee7f5)
              : (item.status === 'suspect' ? 0xf7bd68 : (idx % 2 === 0 ? 0xa994ff : 0x6ee7f5));

        const radius = isBh ? .115 : (isCore ? .145 : .135);
        const geo = isBh ? new THREE.OctahedronGeometry(radius * 1.15, 0) : new THREE.SphereGeometry(radius, 18, 14);
        const mat = new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: .95 });
        const mesh = new THREE.Mesh(geo, mat);

        const orbitR = isBh ? 2.15 : (isCore ? 2.35 : 2.25);
        const angle = (idx / count) * Math.PI * 2;
        const yOff = ((idx % 3) - 1) * .28;
        mesh.position.set(Math.cos(angle) * orbitR, yOff, Math.sin(angle) * orbitR);

        const itemRateBps = Number(item.rateBps != null ? item.rateBps : ((Number(item.down_rate || 0) + Number(item.up_rate || 0))));
        const itemConns = Number(item.conns != null ? item.conns : (idx === 0 ? 6 : idx === 1 ? 3 : 1));
        const gearInfo = computeSpeedGear(itemRateBps, itemConns);

        const dataObj = Object.assign({
          id: item.id || (centerId + '-sat-' + idx),
          name: item.name || ('目标 ' + (idx + 1)),
          short: item.short || String(item.name || '').slice(0, 15),
          subtitle: item.subtitle || '',
          meta: item.meta || (item.rtt != null && item.rtt > 0 ? (item.rtt + ' ms') : fmtRateShort(itemRateBps)),
          kind: item.kind || (isCore ? 'device' : isBh ? 'blocked' : 'service'),
          galaxy: centerId,
          region: centerId,
          status: item.status || 'ok',
          rtt: item.rtt,
          rateBps: itemRateBps,
          conns: itemConns,
          speedGear: gearInfo.gear,
          speedGearLabel: gearInfo.label,
          speedGearFull: gearInfo.fullLabel,
          protocol: item.protocol || (isCore ? 'LAN' : isCn ? 'DIRECT' : isBh ? 'REJECT' : 'PROXY'),
          topRank: idx
        }, item, {
          rateBps: itemRateBps,
          conns: itemConns,
          speedGear: gearInfo.gear,
          speedGearLabel: gearInfo.label,
          speedGearFull: gearInfo.fullLabel
        });
        mesh.userData.data = dataObj;
        mesh.add(this.glow(col, isBh ? .85 : 1.0, .48));
        center.satGroup.add(mesh);

        const curve = new THREE.QuadraticBezierCurve3(
          new THREE.Vector3(0, 0, 0),
          new THREE.Vector3(mesh.position.x * .5, mesh.position.y + (isBh ? -.2 : .22), mesh.position.z * .5),
          mesh.position.clone()
        );
        const tether = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(curve.getPoints(20)),
          new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: isBh ? .24 : .20, blending: THREE.AdditiveBlending, depthWrite: false })
        );
        center.satGroup.add(tether);

        const tetherPackets = [];
        const sphereCount = gearInfo.gear === 'high' ? 2 : 1;
        for (let pIdx = 0; pIdx < sphereCount; pIdx++) {
          const pMesh = new THREE.Mesh(
            new THREE.SphereGeometry(.038 * gearInfo.scale, 8, 6),
            new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: .92, blending: THREE.AdditiveBlending })
          );
          pMesh.add(this.glow(col, .34 * gearInfo.scale, .62));
          center.satGroup.add(pMesh);
          tetherPackets.push({
            mesh: pMesh,
            curve,
            offset: (pIdx / sphereCount) + (idx * .13) % 1,
            speed: gearInfo.speed,
            scale: gearInfo.scale,
            gear: gearInfo.gear,
            inbound: isCore || isBh
          });
        }

        this.selectable.push(mesh);
        this.addLabel(mesh, dataObj, false);
        this.satellitesByCenter[centerId].push({
          mesh,
          tether,
          curve,
          tetherPackets,
          orbitR,
          angle,
          yOff,
          rateBps: itemRateBps,
          conns: itemConns,
          speedGear: gearInfo.gear,
          speedGearLabel: gearInfo.label,
          speed: (idx % 2 === 0 ? 1 : -1) * (.09 + (idx % 3) * .02)
        });
      });
    }

    /* Only build the 3 real routing trunks from Core to Global, CN, and Blackhole (removed meaningless cn_global beam) */
    buildBeams() {
      this.createBeam('core_global', '海外代理分流', this.centers.core, this.centers.global, 0x7adff2, 8, 3.4, { rateBps: 420 * 1024, conns: 16 });
      this.createBeam('core_cn', '国内宽带直连', this.centers.core, this.centers.cn, 0xf9a8d4, 7, 2.5, { rateBps: 140 * 1024, conns: 8 });
      this.createBeam('core_blackhole', '双层护盾阻断', this.centers.core, this.centers.blackhole, 0xf2a558, 5, 2.9, { rateBps: 0, conns: 4, hits: 483549 });
    }

    createBeam(key, title, from, to, color, packetCount, lift, initStats) {
      const a = from.group.position.clone();
      const b = to.group.position.clone();
      const mid = a.clone().lerp(b, .5);
      mid.y += lift;
      mid.z -= 1.2;
      const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(80)), new THREE.LineBasicMaterial({ color, transparent: true, opacity: .30, blending: THREE.AdditiveBlending, depthWrite: false }));
      this.world.add(line);
      this.beams.push(line);

      const gearInfo = computeSpeedGear(initStats ? initStats.rateBps : 32768, initStats ? initStats.conns : 4);
      const beamPackets = [];
      for (let i = 0; i < packetCount; i++) {
        const packet = new THREE.Mesh(new THREE.SphereGeometry(.054, 10, 8), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .96, blending: THREE.AdditiveBlending }));
        packet.add(this.glow(color, .54, .72));
        this.world.add(packet);
        const pktObj = {
          mesh: packet,
          curve,
          beamKey: key,
          index: i,
          totalOnBeam: packetCount,
          offset: i / packetCount,
          speed: gearInfo.speed,
          baseScale: gearInfo.scale,
          gear: gearInfo.gear,
          gearLabel: gearInfo.label,
          activeRatio: gearInfo.activeRatio
        };
        this.packets.push(pktObj);
        beamPackets.push(pktObj);
      }

      this.beamsByKey[key] = {
        key,
        title,
        fromId: from.data.id,
        toId: to.data.id,
        color,
        curve,
        line,
        midPoint: curve.getPoint(0.5),
        packets: beamPackets,
        rateBps: initStats ? initStats.rateBps : 32768,
        conns: initStats ? initStats.conns : 4,
        hits: initStats && initStats.hits != null ? initStats.hits : 0,
        gear: gearInfo.gear,
        gearLabel: gearInfo.label,
        gearFullLabel: gearInfo.fullLabel,
        speed: gearInfo.speed
      };
    }

    updateBeamSpeedGear(key, rateBps, conns, hits) {
      const beam = this.beamsByKey[key];
      if (!beam) return;
      const gearInfo = computeSpeedGear(rateBps, conns);
      beam.rateBps = Math.max(0, Number(rateBps || 0));
      beam.conns = Math.max(0, Number(conns || 0));
      if (hits != null) beam.hits = Number(hits || 0);
      beam.gear = gearInfo.gear;
      beam.gearLabel = gearInfo.label;
      beam.gearFullLabel = gearInfo.fullLabel;
      beam.speed = gearInfo.speed;
      if (beam.line && beam.line.material) {
        beam.line.material.opacity = gearInfo.gear === 'high' ? 0.46 : (gearInfo.gear === 'med' ? 0.32 : 0.20);
      }
      beam.packets.forEach(pkt => {
        pkt.speed = gearInfo.speed;
        pkt.baseScale = gearInfo.scale;
        pkt.gear = gearInfo.gear;
        pkt.gearLabel = gearInfo.label;
        pkt.activeRatio = gearInfo.activeRatio;
      });
    }

    /* Rebuild real 3D end-to-end connection trajectories when 流量激增 (Real 3D Connection Expression) is active */
    rebuildLiveConnectionArcs(payload) {
      while (this.liveConnGroup.children.length) {
        this.liveConnGroup.remove(this.liveConnGroup.children[0]);
      }
      this.liveConnArcs = [];
      this.liveConnPackets = [];

      const srcSats = this.satellitesByCenter.core || [];
      const cnSats = this.satellitesByCenter.cn || [];
      const globalSats = this.satellitesByCenter.global || [];
      const bhSats = this.satellitesByCenter.blackhole || [];

      const rawFlows = (payload && Array.isArray(payload.liveConnections) && payload.liveConnections.length)
        ? payload.liveConnections
        : [];

      const flows = rawFlows.length ? rawFlows.slice(0, MAX_LIVE_CONN_ARCS) : [];
      if (!flows.length) {
        globalSats.slice(0, 5).forEach((dstSat, i) => {
          const srcSat = srcSats[i % Math.max(1, srcSats.length)];
          const dData = dstSat.mesh.userData.data || {};
          const sData = srcSat ? (srcSat.mesh.userData.data || {}) : {};
          flows.push({
            id: 'flow-gl-' + i,
            srcId: sData.id || '',
            srcName: sData.name || 'LAN',
            dstGalaxy: 'global',
            dstId: dData.id || '',
            dstName: dData.short || dData.name || 'Global',
            rateBps: Number(dData.rateBps || 65536),
            conns: Number(dData.conns || 4),
            rule: dData.subtitle || 'Shunt_Proxy'
          });
        });
        cnSats.slice(0, 4).forEach((dstSat, i) => {
          const srcSat = srcSats[(i + 1) % Math.max(1, srcSats.length)];
          const dData = dstSat.mesh.userData.data || {};
          const sData = srcSat ? (srcSat.mesh.userData.data || {}) : {};
          flows.push({
            id: 'flow-cn-' + i,
            srcId: sData.id || '',
            srcName: sData.name || 'LAN',
            dstGalaxy: 'cn',
            dstId: dData.id || '',
            dstName: dData.short || dData.name || 'CN',
            rateBps: Number(dData.rateBps || 32768),
            conns: Number(dData.conns || 3),
            rule: 'DIRECT'
          });
        });
        bhSats.slice(0, 2).forEach((dstSat, i) => {
          const srcSat = srcSats[i % Math.max(1, srcSats.length)];
          const dData = dstSat.mesh.userData.data || {};
          const sData = srcSat ? (srcSat.mesh.userData.data || {}) : {};
          flows.push({
            id: 'flow-bh-' + i,
            srcId: sData.id || '',
            srcName: sData.name || 'LAN',
            dstGalaxy: 'blackhole',
            dstId: dData.id || '',
            dstName: dData.short || dData.name || 'Blocked',
            rateBps: 2048,
            conns: Number(dData.conns || 1),
            rule: 'REJECT'
          });
        });
      }

      let highCount = 0, medCount = 0, lowCount = 0, totalConns = 0;

      flows.slice(0, MAX_LIVE_CONN_ARCS).forEach((flow, idx) => {
        const gal = flow.dstGalaxy || 'global';
        const targetCenter = this.centers[gal] || this.centers.global;
        const targetSatPool = this.satellitesByCenter[gal] || [];

        let srcSat = srcSats.find(s => {
          const d = s.mesh.userData.data || {};
          return (flow.srcId && d.id === flow.srcId) || (flow.srcIp && (d.ip === flow.srcIp || String(d.subtitle || '').includes(flow.srcIp)));
        });
        if (!srcSat && srcSats.length) srcSat = srcSats[idx % srcSats.length];

        let dstSat = targetSatPool.find(s => {
          const d = s.mesh.userData.data || {};
          return (flow.dstId && d.id === flow.dstId) ||
            (flow.dstDomain && (d.domain === flow.dstDomain || String(d.name || '').toLowerCase().includes(String(flow.dstDomain).toLowerCase())));
        });
        if (!dstSat && targetSatPool.length) dstSat = targetSatPool[idx % targetSatPool.length];

        const srcWorld = new THREE.Vector3();
        if (srcSat && srcSat.mesh) {
          this.centers.core.satGroup.updateMatrixWorld(true);
          srcSat.mesh.getWorldPosition(srcWorld);
        } else {
          srcWorld.set((idx % 2 === 0 ? -1.8 : 1.8), 0.6, 1.5);
        }

        const coreHub = this.centers.core.group.position.clone().add(new THREE.Vector3(0, 0.35 + (idx % 3) * 0.22, 0));
        const targetHub = targetCenter.group.position.clone().add(new THREE.Vector3(0, 0.4 + (idx % 3) * 0.25, 0));

        const dstWorld = new THREE.Vector3();
        if (dstSat && dstSat.mesh) {
          targetCenter.satGroup.updateMatrixWorld(true);
          dstSat.mesh.getWorldPosition(dstWorld);
        } else {
          dstWorld.copy(targetCenter.group.position).add(new THREE.Vector3(1.2, 0.4, -0.8));
        }

        const midBridge = coreHub.clone().lerp(targetHub, 0.5);
        midBridge.y += 2.2 + (idx % 4) * 0.55;
        midBridge.z += ((idx % 2 === 0 ? 1 : -1) * (0.8 + (idx % 3) * 0.45));

        const curve = new THREE.CatmullRomCurve3([
          srcWorld,
          coreHub,
          midBridge,
          targetHub,
          dstWorld
        ]);

        const gearInfo = computeSpeedGear(flow.rateBps, flow.conns);
        if (gearInfo.gear === 'high') highCount++;
        else if (gearInfo.gear === 'med') medCount++;
        else lowCount++;
        totalConns += Math.max(1, Number(flow.conns || 1));

        const arcColor = gal === 'cn'
          ? 0xf9a8d4
          : gal === 'blackhole'
            ? 0xf7bd68
            : (gearInfo.gear === 'high' ? 0x6ee7f5 : 0xa994ff);

        const arcOpacity = gearInfo.gear === 'high' ? 0.58 : (gearInfo.gear === 'med' ? 0.42 : 0.28);
        const arcLine = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(curve.getPoints(72)),
          new THREE.LineBasicMaterial({ color: arcColor, transparent: true, opacity: arcOpacity, blending: THREE.AdditiveBlending, depthWrite: false })
        );
        this.liveConnGroup.add(arcLine);

        const sphereCount = gearInfo.gear === 'high' ? 3 : (gearInfo.gear === 'med' ? 2 : 1);
        const arcPackets = [];
        for (let sIdx = 0; sIdx < sphereCount; sIdx++) {
          const pMesh = new THREE.Mesh(
            new THREE.SphereGeometry(0.056 * gearInfo.scale, 10, 8),
            new THREE.MeshBasicMaterial({ color: arcColor, transparent: true, opacity: 0.98, blending: THREE.AdditiveBlending })
          );
          pMesh.add(this.glow(arcColor, 0.56 * gearInfo.scale, 0.78));
          this.liveConnGroup.add(pMesh);
          const pkt = {
            mesh: pMesh,
            curve,
            offset: (sIdx / sphereCount) + (idx * 0.09) % 1,
            speed: gearInfo.speed,
            scale: gearInfo.scale,
            gear: gearInfo.gear,
            gearLabel: gearInfo.label,
            dstGalaxy: gal
          };
          this.liveConnPackets.push(pkt);
          arcPackets.push(pkt);
        }

        this.liveConnArcs.push({
          id: flow.id || ('arc-' + idx),
          srcName: flow.srcName || 'LAN',
          dstName: flow.dstName || gal,
          dstGalaxy: gal,
          rateBps: Number(flow.rateBps || 0),
          conns: Number(flow.conns || 1),
          gear: gearInfo.gear,
          gearLabel: gearInfo.label,
          gearFullLabel: gearInfo.fullLabel,
          speed: gearInfo.speed,
          line: arcLine,
          curve,
          midPoint: midBridge,
          packets: arcPackets
        });
      });

      this.liveConnSummary = {
        totalArcs: this.liveConnArcs.length,
        totalConns,
        highCount,
        medCount,
        lowCount
      };
    }

    getLinkSpeedGears() {
      const trunks = {};
      Object.entries(this.beamsByKey).forEach(([k, b]) => {
        trunks[k] = {
          key: k,
          title: b.title,
          gear: b.gear,
          gearLabel: b.gearLabel,
          gearFullLabel: b.gearFullLabel,
          speed: b.speed,
          rateBps: b.rateBps,
          conns: b.conns
        };
      });
      return {
        trunks,
        surgeActive: this.surge,
        liveConnSummary: this.liveConnSummary,
        liveConnArcsCount: this.liveConnArcs.length
      };
    }

    buildSelectionHalo() {
      this.selectionHalo = this.glow(0x8df3ff, 2.3, .75);
      this.selectionHalo.visible = false;
      this.world.add(this.selectionHalo);
      this.selectionRing = new THREE.Mesh(new THREE.TorusGeometry(.5, .018, 5, 80), new THREE.MeshBasicMaterial({ color: 0x8df3ff, transparent: true, opacity: .75, blending: THREE.AdditiveBlending, depthWrite: false }));
      this.selectionRing.visible = false;
      this.world.add(this.selectionRing);
    }

    addLabel(object, data, cluster) {
      this.labelObjects.push({ object, data, cluster });
    }

    bindControls() {
      let lastX = 0;
      let lastY = 0;
      this.canvas.addEventListener('pointerdown', event => {
        this.dragging = true;
        this.dragDistance = 0;
        lastX = event.clientX;
        lastY = event.clientY;
        this.canvas.setPointerCapture(event.pointerId);
      });
      this.canvas.addEventListener('pointermove', event => {
        const dx = event.clientX - lastX;
        const dy = event.clientY - lastY;
        if (this.dragging) {
          this.dragDistance += Math.abs(dx) + Math.abs(dy);
          this.desired.theta -= dx * .005;
          this.desired.phi = clamp(this.desired.phi - dy * .004, .32, 2.5);
          this.autoRotate = false;
          if (this.options.onInteract) this.options.onInteract();
          this.tooltip.hidden = true;
        } else {
          this.hover(event);
        }
        lastX = event.clientX;
        lastY = event.clientY;
      });
      this.canvas.addEventListener('pointerup', event => {
        if (this.dragDistance < 6) this.pick(event);
        this.dragging = false;
        try { this.canvas.releasePointerCapture(event.pointerId); } catch (_) {}
      });
      this.canvas.addEventListener('pointercancel', () => { this.dragging = false; });
      this.canvas.addEventListener('pointerleave', () => { this.tooltip.hidden = true; });
      this.canvas.addEventListener('wheel', event => {
        event.preventDefault();
        this.desired.radius = clamp(this.desired.radius + event.deltaY * .012, 6.5, 43);
      }, { passive: false });
      window.addEventListener('keydown', event => {
        if (event.key === 'Escape' && this.options.page === 'galaxy') this.reset();
      });
    }

    updatePointer(event) {
      const rect = this.canvas.getBoundingClientRect();
      this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      return rect;
    }

    hitTest(event) {
      this.updatePointer(event);
      this.raycaster.setFromCamera(this.pointer, this.camera);
      const hits = this.raycaster.intersectObjects(this.selectable, false);
      return hits.length ? hits[0].object : null;
    }

    hover(event) {
      const mesh = this.hitTest(event);
      this.canvas.style.cursor = mesh ? 'pointer' : 'grab';
      if (!mesh) {
        this.tooltip.hidden = true;
        return;
      }
      const data = mesh.userData.data;
      const rect = this.canvas.getBoundingClientRect();
      this.tooltip.innerHTML = '<b></b><span></span>';
      this.tooltip.querySelector('b').textContent = data.name + (data.speedGearLabel ? (' · ⚡' + data.speedGearLabel + '速') : '');
      const subTxt = (data.subtitle || '') + (data.meta ? ' · ' + data.meta : (data.rtt != null ? ' · ' + data.rtt + ' ms' : ''));
      this.tooltip.querySelector('span').textContent = subTxt;
      this.tooltip.style.left = clamp(event.clientX - rect.left + 15, 8, rect.width - 210) + 'px';
      this.tooltip.style.top = clamp(event.clientY - rect.top + 15, 8, rect.height - 75) + 'px';
      this.tooltip.hidden = false;
    }

    pick(event) {
      const mesh = this.hitTest(event);
      if (mesh) this.select(mesh, true);
    }

    select(mesh, focus) {
      if (!mesh || !mesh.userData.data) return;
      this.selected = mesh.userData.data;
      this.selectedMesh = mesh;
      this.selectionHalo.visible = true;
      this.selectionRing.visible = true;
      const isCluster = Boolean(this.centers[this.selected.id]);
      if (focus) {
        if (isCluster) {
          this.setMode(this.selected.id);
          if (this.options.onMode) this.options.onMode(this.selected.id);
        } else {
          const position = new THREE.Vector3();
          mesh.getWorldPosition(position);
          this.desired.target.copy(position);
          this.desired.radius = 8.2;
        }
      }
      if (this.options.onSelect) this.options.onSelect(this.selected);
    }

    clearSelection() {
      this.selected = null;
      this.selectedMesh = null;
      this.selectionHalo.visible = false;
      this.selectionRing.visible = false;
    }

    setMode(mode) {
      const narrow = this.shell.clientWidth < 720;
      const views = {
        panorama: { target: [0, 0, 0], radius: narrow ? 34 : 25.5, theta: .12, phi: 1.22 },
        core: { target: [0, 0, 0], radius: 10.2, theta: .42, phi: 1.16 },
        cn: { target: [-7.4, -2.0, 1.2], radius: 10.2, theta: -.35, phi: 1.15 },
        global: { target: [7.2, .85, -.8], radius: 10.8, theta: .58, phi: 1.16 },
        blackhole: { target: [-5.8, 5.0, -5.0], radius: 9.8, theta: -.2, phi: 1.05 }
      };
      const view = views[mode] || views.panorama;
      this.mode = mode;
      this.desired.target.fromArray(view.target);
      this.desired.radius = view.radius;
      this.desired.theta = view.theta;
      this.desired.phi = view.phi;
      if (mode !== 'panorama' && this.centers[mode]) {
        this.selected = this.centers[mode].data;
        this.selectedMesh = this.centers[mode].mesh;
        this.selectionHalo.visible = true;
        this.selectionRing.visible = true;
        if (this.options.onSelect) this.options.onSelect(this.selected);
      }
      Object.entries(this.centers).forEach(([id, center]) => {
        const active = mode === 'panorama' || mode === id;
        center.glow.material.opacity = active ? (id === 'blackhole' ? .48 : (id === 'cn' ? .42 : .36)) : .12;
      });
    }

    reset() {
      this.clearSelection();
      this.setMode('panorama');
      if (this.options.onSelect) this.options.onSelect(null);
      if (this.options.onMode) this.options.onMode('panorama');
    }

    setAutoRotate(value) { this.autoRotate = value && !reducedMotion; }
    setLabels(value) { this.showLabels = value; }
    setSurge(value) {
      this.surge = Boolean(value);
      if (this.liveConnGroup) {
        this.liveConnGroup.visible = this.surge;
      }
      if (this.surge) {
        this.rebuildLiveConnectionArcs(this.lastSyncPayload);
      }
    }
    setActive(value) { this.active = value; }

    syncData(payload) {
      if (!payload) return;
      this.lastSyncPayload = payload;
      ['core', 'cn', 'global', 'blackhole'].forEach(cid => {
        if (payload[cid] && this.centers[cid]) {
          if (payload[cid].subtitle) this.centers[cid].data.subtitle = payload[cid].subtitle;
          if (payload[cid].label) this.centers[cid].data.label = payload[cid].label;
        }
      });
      if (Array.isArray(payload.coreSatellites) && payload.coreSatellites.length) {
        this.rebuildCenterSatellites('core', payload.coreSatellites);
      }
      if (Array.isArray(payload.cnSatellites) && payload.cnSatellites.length) {
        this.rebuildCenterSatellites('cn', payload.cnSatellites);
      }
      if (Array.isArray(payload.globalSatellites) && payload.globalSatellites.length) {
        this.rebuildCenterSatellites('global', payload.globalSatellites);
      }
      if (Array.isArray(payload.blackholeSatellites) && payload.blackholeSatellites.length) {
        this.rebuildCenterSatellites('blackhole', payload.blackholeSatellites);
      }

      const cnSats = payload.cnSatellites || [];
      const glSats = payload.globalSatellites || [];
      const bhSats = payload.blackholeSatellites || [];

      const cnRate = payload.linkStats && payload.linkStats.cn ? payload.linkStats.cn.rateBps : cnSats.reduce((s, x) => s + Number(x.rateBps || ((Number(x.down_rate || 0) + Number(x.up_rate || 0)))), 0);
      const cnConns = payload.linkStats && payload.linkStats.cn ? payload.linkStats.cn.conns : cnSats.reduce((s, x) => s + Number(x.conns || 1), 0);

      const glRate = payload.linkStats && payload.linkStats.global ? payload.linkStats.global.rateBps : glSats.reduce((s, x) => s + Number(x.rateBps || ((Number(x.down_rate || 0) + Number(x.up_rate || 0)))), 0);
      const glConns = payload.linkStats && payload.linkStats.global ? payload.linkStats.global.conns : glSats.reduce((s, x) => s + Number(x.conns || 1), 0);

      const bhRate = payload.linkStats && payload.linkStats.blackhole ? payload.linkStats.blackhole.rateBps : 0;
      const bhConns = payload.linkStats && payload.linkStats.blackhole ? payload.linkStats.blackhole.conns : Math.min(20, bhSats.length);
      const bhHits = payload.linkStats && payload.linkStats.blackhole ? payload.linkStats.blackhole.hits : 0;

      this.updateBeamSpeedGear('core_cn', cnRate, cnConns, 0);
      this.updateBeamSpeedGear('core_global', glRate, glConns, 0);
      this.updateBeamSpeedGear('core_blackhole', bhRate, bhConns, bhHits);

      this.rebuildLiveConnectionArcs(payload);
    }

    resize() {
      const width = Math.max(1, this.shell.clientWidth);
      const height = Math.max(1, this.shell.clientHeight);
      if (this.renderer) this.renderer.setSize(width, height, false);
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const pixelWidth = Math.round(width * dpr);
      const pixelHeight = Math.round(height * dpr);
      if (this.labelCanvas.width !== pixelWidth || this.labelCanvas.height !== pixelHeight) {
        this.labelCanvas.width = pixelWidth;
        this.labelCanvas.height = pixelHeight;
      }
      this.labelDpr = dpr;
    }

    updateCamera(dt) {
      const t = dt >= 1 ? 1 : 1 - Math.exp(-dt * 4.5);
      this.current.theta = lerp(this.current.theta, this.desired.theta, t);
      this.current.phi = lerp(this.current.phi, this.desired.phi, t);
      this.current.radius = lerp(this.current.radius, this.desired.radius, t);
      this.current.target.lerp(this.desired.target, t);
      const spherical = new THREE.Spherical(this.current.radius, this.current.phi, this.current.theta);
      this.camera.position.copy(this.current.target).add(new THREE.Vector3().setFromSpherical(spherical));
      this.camera.lookAt(this.current.target);
    }

    roundedRect(ctx, x, y, width, height, radius) {
      const r = Math.min(radius, width / 2, height / 2);
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + width - r, y);
      ctx.quadraticCurveTo(x + width, y, x + width, y + r);
      ctx.lineTo(x + width, y + height - r);
      ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
      ctx.lineTo(x + r, y + height);
      ctx.quadraticCurveTo(x, y + height, x, y + height - r);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
      ctx.closePath();
    }

    updateLabels() {
      const width = this.shell.clientWidth;
      const height = this.shell.clientHeight;
      const dpr = this.labelDpr || Math.min(window.devicePixelRatio || 1, 2);
      const ctx = this.labelCtx;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      const projected = [];
      const pos = new THREE.Vector3();
      this.labelObjects.forEach(item => {
        item.object.getWorldPosition(pos);
        pos.project(this.camera);
        const selected = !!(this.selected && this.selected.id === item.data.id);
        const gal = item.data.galaxy || item.data.region;
        const isFocusedGalaxy = this.mode !== 'panorama' && gal === this.mode;
        const topAllowed = !item.cluster && (item.data.topRank != null ? item.data.topRank < (isFocusedGalaxy ? 8 : (this.surge ? 5 : 3)) : false);
        const allowed = item.cluster || this.showLabels || selected || isFocusedGalaxy || topAllowed;
        if (!allowed || pos.z <= -1 || pos.z >= 1 || Math.abs(pos.x) > 1.06 || Math.abs(pos.y) > 1.06) return;
        projected.sortPriority = selected ? 0 : item.cluster ? 1 : (isFocusedGalaxy ? 2 : 3 + (item.data.topRank || 0));
        projected.push({
          item,
          selected,
          x: (pos.x * .5 + .5) * width,
          y: (-pos.y * .5 + .5) * height,
          z: pos.z,
          priority: projected.sortPriority
        });
      });
      projected.sort((a, b) => a.priority - b.priority || a.z - b.z);
      const caption = document.getElementById('scene-caption');
      const captionVisible = caption && !caption.classList.contains('dimmed');
      const safeZone = captionVisible ? { x: 8, y: 54, w: Math.min(width * .56, 360), h: width < 720 ? 140 : 170 } : null;
      const occupied = [];
      const inspector = document.getElementById('inspector');
      if (inspector && inspector.classList.contains('open')) {
        const shellRect = this.shell.getBoundingClientRect();
        const inspectorRect = inspector.getBoundingClientRect();
        occupied.push({ x: inspectorRect.left - shellRect.left - 12, y: inspectorRect.top - shellRect.top - 12, w: inspectorRect.width + 24, h: inspectorRect.height + 24 });
      }
      ctx.textBaseline = 'middle';
      projected.forEach(({ item, selected, x, y }) => {
        const data = item.data;
        const isCluster = item.cluster;
        const title = data.short || data.name;
        const gearSuffix = (!isCluster && data.speedGearLabel) ? (' · ' + data.speedGearLabel) : '';
        const meta = isCluster ? (data.label || data.subtitle) : ((data.meta || (data.rtt != null ? data.rtt + ' ms' : '活跃')) + gearSuffix);
        ctx.font = (isCluster ? '600 10.5px ' : '500 9px ') + 'Inter, "PingFang SC", sans-serif';
        const titleWidth = ctx.measureText(title).width;
        ctx.font = '400 8px Inter, "PingFang SC", sans-serif';
        const metaWidth = ctx.measureText(meta).width;
        const boxWidth = Math.min(220, titleWidth + metaWidth + (isCluster ? 36 : 28));
        const boxHeight = isCluster ? 30 : 21;
        const onRight = x + boxWidth + 22 < width - 8;
        const bx = clamp(onRight ? x + 12 : x - boxWidth - 12, 8, width - boxWidth - 8);
        const by = clamp(y - boxHeight / 2, 8, height - boxHeight - 8);
        const rect = { x: bx, y: by, w: boxWidth, h: boxHeight };
        const intersectsCaption = safeZone && !selected && !isCluster && !(rect.x + rect.w < safeZone.x || rect.x > safeZone.x + safeZone.w || rect.y + rect.h < safeZone.y || rect.y > safeZone.y + safeZone.h);
        if (intersectsCaption) return;
        const collides = occupied.some(other => !(rect.x + rect.w < other.x || rect.x > other.x + other.w || rect.y + rect.h < other.y || rect.y > other.y + other.h));
        if (collides && !selected && !isCluster) return;
        occupied.push(rect);
        const isCnNode = data.region === 'cn' || data.kind === 'cn' || data.galaxy === 'cn';
        const color = data.kind === 'blackhole' || data.region === 'blackhole'
          ? '#f7bd68'
          : isCnNode
            ? '#f9a8d4'
            : data.region === 'global' || data.kind === 'global'
              ? '#a994ff'
              : '#6ee7f5';
        ctx.strokeStyle = selected
          ? 'rgba(110,231,245,.82)'
          : isCluster
            ? (isCnNode ? 'rgba(249,168,212,.45)' : 'rgba(136,163,205,.32)')
            : 'rgba(126,148,184,.2)';
        ctx.lineWidth = selected ? 1.2 : .85;
        ctx.beginPath();
        const edgeX = onRight ? bx : bx + boxWidth;
        ctx.moveTo(x, y);
        ctx.lineTo(edgeX, by + boxHeight / 2);
        ctx.stroke();
        this.roundedRect(ctx, bx, by, boxWidth, boxHeight, isCluster ? 8 : 6);
        ctx.fillStyle = selected ? 'rgba(10,24,35,.96)' : isCluster ? 'rgba(7,13,25,.94)' : 'rgba(5,9,18,.88)';
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, selected ? 3.2 : 2.2, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(bx + 9, by + boxHeight / 2, 2.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.font = (isCluster ? '600 10.5px ' : '500 9px ') + 'Inter, "PingFang SC", sans-serif';
        ctx.fillStyle = selected ? '#f3fbff' : isCluster ? '#edf4ff' : '#c4d2e6';
        ctx.fillText(title, bx + 16, by + (isCluster ? 11 : boxHeight / 2));
        ctx.font = '400 8px Inter, "PingFang SC", sans-serif';
        ctx.fillStyle = data.region === 'blackhole' ? '#f7bd68' : isCnNode ? '#f9a8d4' : (data.status === 'suspect' ? '#c89451' : '#7b8aa8');
        if (isCluster) {
          ctx.fillText(meta, bx + 16, by + 22);
        } else {
          ctx.fillText(meta, bx + boxWidth - metaWidth - 7, by + boxHeight / 2);
        }
      });

      /* Readable Telemetry Data Pills on the 3 Real Routing Trunks (流速挡位 + 实时速率 + 并发连接数) */
      ['core_global', 'core_cn', 'core_blackhole'].forEach(bKey => {
        const bm = this.beamsByKey[bKey];
        if (!bm || !bm.midPoint) return;
        pos.copy(bm.midPoint);
        pos.project(this.camera);
        if (pos.z <= -1 || pos.z >= 1 || Math.abs(pos.x) > 0.96 || Math.abs(pos.y) > 0.96) return;
        const mx = (pos.x * .5 + .5) * width;
        const my = (-pos.y * .5 + .5) * height;
        const ratePart = bKey === 'core_blackhole'
          ? (bm.conns + ' 规则簇')
          : ('↓' + fmtRateShort(bm.rateBps) + ' · ' + bm.conns + '连');
        const pillTxt = '流速:' + bm.gearLabel + ' · ' + ratePart;
        ctx.font = '600 8px Inter, "PingFang SC", sans-serif';
        const pw = ctx.measureText(pillTxt).width + 14;
        const ph = 18;
        const px = clamp(mx - pw / 2, 8, width - pw - 8);
        const py = clamp(my - ph / 2, 8, height - ph - 8);
        const rect = { x: px, y: py, w: pw, h: ph };
        const collides = occupied.some(other => !(rect.x + rect.w < other.x || rect.x > other.x + other.w || rect.y + rect.h < other.y || rect.y > other.y + other.h));
        if (collides) return;
        occupied.push(rect);
        const pillColor = bKey === 'core_cn' ? '#f9a8d4' : (bKey === 'core_blackhole' ? '#f7bd68' : '#6ee7f5');
        this.roundedRect(ctx, px, py, pw, ph, 9);
        ctx.fillStyle = 'rgba(6, 12, 24, 0.92)';
        ctx.fill();
        ctx.strokeStyle = bm.gear === 'high' ? pillColor : 'rgba(148, 163, 196, 0.35)';
        ctx.lineWidth = 0.9;
        ctx.stroke();
        ctx.fillStyle = pillColor;
        ctx.fillText(pillTxt, px + 7, py + ph / 2);
      });

      /* When 流量激增 (Real 3D Connection Expression) is active, render HUD banner + readable flow tags */
      if (this.surge && this.liveConnSummary) {
        const s = this.liveConnSummary;
        const bannerTxt = '⚡ 真实连接 3D 表达已激活 · 实时映射 ' + s.totalArcs + ' 条跨星系轨迹 (' + s.totalConns + ' 并发连接) · 挡位: 高[' + s.highCount + '] / 中[' + s.medCount + '] / 低[' + s.lowCount + ']';
        ctx.font = '600 9.5px Inter, "PingFang SC", sans-serif';
        const bw = Math.min(width - 24, ctx.measureText(bannerTxt).width + 26);
        const bh = 26;
        const bx = (width - bw) / 2;
        const by = 56;
        this.roundedRect(ctx, bx, by, bw, bh, 13);
        ctx.fillStyle = 'rgba(8, 16, 30, 0.92)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(249, 168, 212, 0.55)';
        ctx.lineWidth = 1.1;
        ctx.stroke();
        ctx.fillStyle = '#f8fbff';
        ctx.fillText(bannerTxt, bx + 13, by + bh / 2);
      }
    }

    render() {
      const dt = Math.min(this.clock.getDelta(), .05);
      if (!this.active || document.hidden) return;
      const elapsed = this.clock.elapsedTime;
      if (this.autoRotate && !this.dragging) this.desired.theta += dt * .028;
      this.updateCamera(dt);
      if (this.stars) this.stars.rotation.y += dt * .0015;
      Object.entries(this.centers).forEach(([id, center], index) => {
        const rotSpeed = (.03 + index * .006);
        if (center.satGroup) {
          center.satGroup.rotation.y += dt * (id === 'blackhole' ? -rotSpeed * 1.2 : rotSpeed * .75);
        }
        center.mesh.rotation.y += dt * .11;
        if (center.disk && center.particles && this.bhParticleMeta) {
          center.disk.rotation.z -= dt * .24;
          const posAttr = center.particles.geometry.getAttribute('position');
          const arr = posAttr.array;
          const bhBeam = this.beamsByKey.core_blackhole;
          const pullMult = bhBeam && bhBeam.gear === 'high' ? 1.85 : (bhBeam && bhBeam.gear === 'med' ? 1.35 : 1.0);
          for (let i = 0; i < this.bhParticleMeta.length; i++) {
            const m = this.bhParticleMeta[i];
            m.a += dt * m.speed * (2.5 / Math.max(1.05, m.r)) * pullMult;
            m.r -= dt * .20 * m.speed * pullMult;
            if (m.r < 1.06) {
              m.r = 2.7 + (i % 5) * .15;
            }
            arr[i * 3] = Math.cos(m.a) * m.r;
            arr[i * 3 + 1] = m.y * ((m.r - 1.0) / 2.2);
            arr[i * 3 + 2] = Math.sin(m.a) * m.r;
          }
          posAttr.needsUpdate = true;
        }
      });

      /* Animate trunk beam spheres at their real 3-tier speed gear (高: 0.56 / 中: 0.26 / 低: 0.095) */
      this.packets.forEach((packet, i) => {
        const visibleCount = Math.max(2, Math.round(packet.totalOnBeam * (packet.activeRatio || 0.6)));
        packet.mesh.visible = packet.index < visibleCount || this.surge;
        if (!packet.mesh.visible) return;
        const speed = packet.speed || 0.26;
        const p = (elapsed * speed + packet.offset) % 1;
        packet.mesh.position.copy(packet.curve.getPoint(p));
        const pulse = (packet.baseScale || 1.0) * (1 + Math.sin(elapsed * 5 + i) * .12);
        packet.mesh.scale.setScalar(pulse);
      });

      /* Animate satellite tether spheres at their individual 3-tier speed gear */
      Object.values(this.satellitesByCenter).forEach(satList => {
        satList.forEach((sat, sIdx) => {
          if (!sat.tetherPackets) return;
          sat.tetherPackets.forEach((tp, pIdx) => {
            const rawT = (elapsed * tp.speed + tp.offset) % 1;
            const t = tp.inbound ? (1 - rawT) : rawT;
            tp.mesh.position.copy(tp.curve.getPoint(t));
            const pulse = tp.scale * (1 + Math.sin(elapsed * 6 + sIdx + pIdx) * .1);
            tp.mesh.scale.setScalar(pulse);
          });
        });
      });

      /* Animate real 3D live connection arcs when 流量激增 (this.surge) is enabled */
      if (this.surge && this.liveConnPackets.length) {
        this.liveConnPackets.forEach((pkt, idx) => {
          const p = (elapsed * pkt.speed + pkt.offset) % 1;
          pkt.mesh.position.copy(pkt.curve.getPoint(p));
          const pulse = pkt.scale * (1.12 + Math.sin(elapsed * 7 + idx) * .18);
          pkt.mesh.scale.setScalar(pulse);
        });
      }

      if (this.selectedMesh) {
        const position = new THREE.Vector3();
        this.selectedMesh.getWorldPosition(position);
        this.selectionHalo.position.copy(position);
        this.selectionRing.position.copy(position);
        this.selectionRing.lookAt(this.camera.position);
        const isCenter = Boolean(this.centers[this.selected.id]);
        const size = isCenter ? 2.2 : .75;
        this.selectionRing.scale.setScalar(size * (1 + Math.sin(elapsed * 3) * .08));
        this.selectionRing.rotation.z += dt * .35;
      }
      this.scene.updateMatrixWorld(true);
      this.updateLabels();
      if (this.renderer) this.renderer.render(this.scene, this.camera);
    }
  }

  window.NexusScene = {
    computeSpeedGear,
    create(canvas, options) {
      if (!window.THREE) return null;
      try {
        const instance = new NexusUniverse(canvas, options);
        window.__nexusScene = instance;
        return instance;
      } catch (error) {
        console.error('Nexus 3D initialization failed:', error);
        return null;
      }
    }
  };
})();
