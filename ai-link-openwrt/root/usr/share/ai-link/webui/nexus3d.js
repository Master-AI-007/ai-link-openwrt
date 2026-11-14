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
      this.wallpaperMode = false;
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
      this.current = { theta: .16, phi: 1.18, radius: 24.5, target: new THREE.Vector3(0, 0, 0) };
      this.desired = { theta: .16, phi: 1.18, radius: 24.5, target: new THREE.Vector3(0, 0, 0) };
      this.init();
    }

    computeSpeedGear(rateBps, conns) {
      return computeSpeedGear(rateBps, conns);
    }

    init() {
      this.renderer = null;
      this.isSoftwareWebGL = false;
      try {
        this.renderer = new THREE.WebGLRenderer({
          canvas: this.canvas,
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance'
        });
        try {
          const gl = this.renderer.getContext();
          const dbg = gl && gl.getExtension('WEBGL_debug_renderer_info');
          const rStr = dbg ? String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) || '') : '';
          if (/SwiftShader|llvmpipe|Software|Basic Render/i.test(rStr)) {
            this.isSoftwareWebGL = true;
          }
        } catch (_) {}
        this.renderer.setPixelRatio(this.isSoftwareWebGL ? 1.0 : Math.min(window.devicePixelRatio || 1, 2.0));
        this.renderer.setClearColor(0x02040a, 0);
        if ('outputEncoding' in this.renderer && THREE.sRGBEncoding) this.renderer.outputEncoding = THREE.sRGBEncoding;
        if ('toneMapping' in this.renderer && THREE.ACESFilmicToneMapping) {
          this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
          this.renderer.toneMappingExposure = 1.12;
        }
      } catch (_) {
        this.renderer = null;
      }
      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.FogExp2(0x03060f, .0108);
      this.camera = new THREE.PerspectiveCamera(42, 1, .1, 200);
      this.world = new THREE.Group();
      this.scene.add(this.world);
      this.liveConnGroup = new THREE.Group();
      this.liveConnGroup.visible = false;
      this.world.add(this.liveConnGroup);

      /* Studio-grade three-point celestial lighting */
      this.scene.add(new THREE.AmbientLight(0x8899bb, .88));
      const key = new THREE.PointLight(0x78e8ff, 1.9, 68);
      key.position.set(5, 11, 14);
      this.scene.add(key);
      const rim = new THREE.PointLight(0xf9a8d4, 1.5, 58);
      rim.position.set(-12, 3, -9);
      this.scene.add(rim);
      const violetFill = new THREE.PointLight(0x9b82ff, 1.3, 54);
      violetFill.position.set(11, -5, -10);
      this.scene.add(violetFill);

      this.glowTexture = this.createGlowTexture();
      this.coronaTexture = this.createCoronaTexture();
      this.accretionTexture = this.createAccretionDiskTexture();
      this.buildBackdrop();
      this.buildEclipticPlane();
      this.buildCenters();
      this.buildInitialSatellites();
      this.buildBeams();
      this.buildSelectionHalo();
      this.bindControls();
      if (this.canvas && !this._webglCtxListenersBound) {
        this._webglCtxListenersBound = true;
        this.canvas.addEventListener('webglcontextlost', (ev) => {
          ev.preventDefault();
          this.active = false;
          if (this._rafId) { cancelAnimationFrame(this._rafId); this._rafId = 0; }
          const fb = document.getElementById('webgl-fallback');
          if (fb) fb.hidden = false;
        }, false);
        this.canvas.addEventListener('webglcontextrestored', () => {
          const fb = document.getElementById('webgl-fallback');
          if (fb) fb.hidden = true;
          this.active = true;
          this.init();
        }, false);
      }
      this.resizeObserver = new ResizeObserver(() => this.resize());
      this.resizeObserver.observe(this.shell);
      this.setMode('panorama');
      this.resize();
      this.updateCamera(1);
      this._rafId = 0;
      this._loopRunning = false;
      this._tickBound = () => {
        if (!this._loopRunning) return;
        const pageEl = document.getElementById("page-galaxy");
        if (!this.active || document.hidden || (pageEl && !pageEl.classList.contains("active"))) {
          this.stopLoop();
          return;
        }
        this.render();
        if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches && !this.dragging) {
          this.stopLoop();
          return;
        }
        if (this.isSoftwareWebGL && !this.dragging) {
          this._swTimer = setTimeout(() => {
            if (this._loopRunning) this._rafId = requestAnimationFrame(this._tickBound);
          }, 180);
          return;
        }
        this._rafId = requestAnimationFrame(this._tickBound);
      };
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) this.stopLoop();
        else if (this.active) this.startLoop();
      });
      this.startLoop();
    }

    createGlowTexture() {
      const c = document.createElement('canvas');
      c.width = c.height = 256;
      const x = c.getContext('2d');
      const g = x.createRadialGradient(128, 128, 0, 128, 128, 128);
      g.addColorStop(0, 'rgba(255,255,255,1)');
      g.addColorStop(.11, 'rgba(255,255,255,.92)');
      g.addColorStop(.28, 'rgba(255,255,255,.40)');
      g.addColorStop(.58, 'rgba(255,255,255,.09)');
      g.addColorStop(1, 'rgba(255,255,255,0)');
      x.fillStyle = g;
      x.fillRect(0, 0, 256, 256);
      return new THREE.CanvasTexture(c);
    }

    /* Multi-ring atmospheric corona halo for wallpaper-grade mother planets */
    createCoronaTexture() {
      const c = document.createElement('canvas');
      c.width = c.height = 256;
      const x = c.getContext('2d');
      const g = x.createRadialGradient(128, 128, 8, 128, 128, 126);
      g.addColorStop(0, 'rgba(255,255,255,0.96)');
      g.addColorStop(0.22, 'rgba(255,255,255,0.54)');
      g.addColorStop(0.45, 'rgba(255,255,255,0.20)');
      g.addColorStop(0.70, 'rgba(255,255,255,0.05)');
      g.addColorStop(1, 'rgba(255,255,255,0)');
      x.fillStyle = g;
      x.fillRect(0, 0, 256, 256);
      x.strokeStyle = 'rgba(255,255,255,0.24)';
      x.lineWidth = 1.25;
      x.beginPath();
      x.arc(128, 128, 56, 0, Math.PI * 2);
      x.stroke();
      return new THREE.CanvasTexture(c);
    }

    /* Procedural planetary telemetry surface texture (equirectangular 512x256) */
    createPlanetTexture(kind) {
      const c = document.createElement('canvas');
      c.width = 512;
      c.height = 256;
      const ctx = c.getContext('2d');
      const palettes = {
        core: { bg0: '#083344', bg1: '#1588a8', band: 'rgba(110,231,245,0.36)', grid: 'rgba(165,243,252,0.28)', dot: '#cffafe' },
        cn: { bg0: '#4a1230', bg1: '#be3e7c', band: 'rgba(249,168,212,0.40)', grid: 'rgba(251,207,232,0.28)', dot: '#fce7f3' },
        global: { bg0: '#1e1348', bg1: '#5538b5', band: 'rgba(169,148,255,0.38)', grid: 'rgba(216,180,254,0.28)', dot: '#ede9fe' }
      };
      const p = palettes[kind] || palettes.core;
      const grad = ctx.createLinearGradient(0, 0, 0, 256);
      grad.addColorStop(0, p.bg0);
      grad.addColorStop(0.5, p.bg1);
      grad.addColorStop(1, p.bg0);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 512, 256);

      /* Atmospheric zonal flow bands */
      for (let i = 0; i < 14; i++) {
        const y = (i / 14) * 256;
        const h = 4 + (i % 3) * 4;
        ctx.fillStyle = p.band;
        ctx.globalAlpha = 0.16 + (i % 4) * 0.06;
        ctx.fillRect(0, y, 512, h);
      }
      ctx.globalAlpha = 1;

      /* Precision geodesic latitude/longitude telemetry grid */
      ctx.strokeStyle = p.grid;
      ctx.lineWidth = 1;
      for (let lon = 0; lon < 512; lon += 32) {
        ctx.beginPath();
        ctx.moveTo(lon, 0);
        ctx.lineTo(lon, 256);
        ctx.stroke();
      }
      for (let lat = 32; lat < 256; lat += 32) {
        ctx.beginPath();
        ctx.moveTo(0, lat);
        ctx.lineTo(512, lat);
        ctx.stroke();
      }

      /* Glowing orbital city/node clusters */
      ctx.fillStyle = p.dot;
      for (let k = 0; k < 52; k++) {
        const x = ((k * 97 + 31) % 490) + 11;
        const y = ((k * 53 + 19) % 190) + 33;
        const r = 1.3 + (k % 3) * 0.95;
        ctx.globalAlpha = 0.48 + (k % 5) * 0.1;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      return new THREE.CanvasTexture(c);
    }

    /* Relativistic Blackhole Accretion Disk Texture */
    createAccretionDiskTexture() {
      const c = document.createElement('canvas');
      c.width = c.height = 512;
      const ctx = c.getContext('2d');
      const cx = 256, cy = 256;
      const g = ctx.createRadialGradient(cx, cy, 88, cx, cy, 250);
      g.addColorStop(0, 'rgba(0,0,0,0)');
      g.addColorStop(0.06, 'rgba(255,248,225,0.97)');
      g.addColorStop(0.18, 'rgba(255,190,105,0.90)');
      g.addColorStop(0.42, 'rgba(244,132,62,0.54)');
      g.addColorStop(0.72, 'rgba(186,62,28,0.20)');
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, 512, 512);

      /* Swirling spiral filaments inside the accretion disk */
      ctx.save();
      ctx.translate(cx, cy);
      for (let i = 0; i < 36; i++) {
        const r = 96 + (i / 36) * 140;
        ctx.strokeStyle = i % 2 === 0 ? 'rgba(255,230,175,0.24)' : 'rgba(255,140,66,0.18)';
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.arc(0, 0, r, (i * 0.4) % (Math.PI * 2), ((i * 0.4) + 1.8) % (Math.PI * 2));
        ctx.stroke();
      }
      ctx.restore();
      return new THREE.CanvasTexture(c);
    }

    glow(color, scale, opacity, useCorona) {
      const material = new THREE.SpriteMaterial({
        map: useCorona ? (this.coronaTexture || this.glowTexture) : this.glowTexture,
        color,
        transparent: true,
        opacity: opacity == null ? .45 : opacity,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      });
      const sprite = new THREE.Sprite(material);
      sprite.scale.set(scale, scale, 1);
      return sprite;
    }

    /* High-definition multi-spectral deep-space starfield + subtle nebula glow sprites (preserves !this.dust contract) */
    buildBackdrop() {
      const starCount = 760;
      const positions = new Float32Array(starCount * 3);
      const colors = new Float32Array(starCount * 3);
      const color = new THREE.Color();
      const palette = [0x9be8ff, 0xd8e6ff, 0xf9a8d4, 0xb8a5ff, 0x7b8fb2, 0xffe4b5];
      for (let i = 0; i < starCount; i++) {
        const r = 34 + (i % 9) * 8.5;
        const theta = (i * 2.3999632) % (Math.PI * 2);
        const phi = Math.acos(1 - 2 * ((i + 0.5) / starCount));
        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.cos(phi);
        positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
        color.set(palette[i % palette.length]);
        colors[i * 3] = color.r;
        colors[i * 3 + 1] = color.g;
        colors[i * 3 + 2] = color.b;
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
      this.stars = new THREE.Points(
        geometry,
        new THREE.PointsMaterial({
          size: .115,
          vertexColors: true,
          transparent: true,
          opacity: .72,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
          sizeAttenuation: true
        })
      );
      this.scene.add(this.stars);

      /* Deep-space atmospheric nebula glow backdrops aligned with the 4 galaxy sectors */
      const nebulaSpecs = [
        { pos: [14, 3, -18], color: 0x5b3fd6, scale: 28, opacity: 0.14 },
        { pos: [-15, -4, -14], color: 0xd9468f, scale: 25, opacity: 0.11 },
        { pos: [-11, 10, -18], color: 0xe07b2e, scale: 24, opacity: 0.11 },
        { pos: [0, 0, -16], color: 0x1892b8, scale: 30, opacity: 0.12 }
      ];
      nebulaSpecs.forEach(ns => {
        const sp = this.glow(ns.color, ns.scale, ns.opacity, false);
        sp.position.fromArray(ns.pos);
        this.scene.add(sp);
      });
    }

    /* Astrometric Ecliptic Coordinate Plane around Core Hub for spatial depth */
    buildEclipticPlane() {
      const ecliptic = new THREE.Group();
      ecliptic.position.set(0, -2.1, 0);
      this.world.add(ecliptic);
      [4.6, 8.8, 13.2].forEach((radius, idx) => {
        const pts = [];
        const segs = 160;
        for (let i = 0; i <= segs; i++) {
          const a = (i / segs) * Math.PI * 2;
          pts.push(new THREE.Vector3(Math.cos(a) * radius, 0, Math.sin(a) * radius));
        }
        const ringLine = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(pts),
          new THREE.LineBasicMaterial({
            color: idx === 0 ? 0x6ee7f5 : (idx === 1 ? 0x8b9dc3 : 0x6366f1),
            transparent: true,
            opacity: idx === 0 ? 0.13 : (idx === 1 ? 0.08 : 0.05),
            blending: THREE.AdditiveBlending,
            depthWrite: false
          })
        );
        ecliptic.add(ringLine);
      });
      this.eclipticPlane = ecliptic;
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
        radius: .92,
        color: 0xf9a8d4,
        emissive: 0xf472b6,
        accent: 0xfbcfe8,
        cssColor: '#f9a8d4',
        label: '宽带直连 · 5 目标'
      });
      this.centers.global = this.createCenter({
        id: 'global',
        name: '海外代理星系 · 全球分流',
        short: '海外代理',
        subtitle: '智能分流与双组自动池',
        kind: 'global',
        galaxy: 'global',
        position: [7.2, .85, -.8],
        radius: 1.08,
        color: 0x7656dd,
        emissive: 0x7656dd,
        accent: 0xa994ff,
        cssColor: '#a994ff',
        label: '智能分流 · 6 目标'
      });
      this.centers.blackhole = this.createBlackhole();
    }

    createCenter(data) {
      const group = new THREE.Group();
      group.position.fromArray(data.position);
      this.world.add(group);

      const surfaceTex = this.createPlanetTexture(data.id);
      const material = new THREE.MeshLambertMaterial({
        color: data.color,
        emissive: data.emissive || data.color,
        emissiveMap: surfaceTex,
        emissiveIntensity: data.id === 'cn' ? .48 : (data.id === 'core' ? .44 : .40),
        transparent: true,
        opacity: .97
      });
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(data.radius, 28, 20), material);
      mesh.userData.data = data;
      group.add(mesh);
      this.selectable.push(mesh);

      /* Volumetric atmospheric limb shell */
      const atmoShell = new THREE.Mesh(
        new THREE.SphereGeometry(data.radius * 1.12, 40, 28),
        new THREE.MeshBasicMaterial({
          color: data.accent || data.color,
          transparent: true,
          opacity: .18,
          side: THREE.BackSide,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        })
      );
      group.add(atmoShell);

      /* Multi-layer corona glow */
      const glow = this.glow(data.color, data.radius * 6.0, data.id === 'cn' ? .48 : .40, true);
      group.add(glow);

      /* Precision dual-tilted astrometric rings + pulse wave ring */
      const rings = new THREE.Group();
      group.add(rings);
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(data.radius * 1.66, .017, 10, 140),
        new THREE.MeshBasicMaterial({ color: data.color, transparent: true, opacity: .40, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      ring.rotation.x = Math.PI / 2;
      rings.add(ring);

      const tiltedRing = new THREE.Mesh(
        new THREE.TorusGeometry(data.radius * 1.92, .010, 8, 120),
        new THREE.MeshBasicMaterial({ color: data.accent || data.color, transparent: true, opacity: .22, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      tiltedRing.rotation.x = Math.PI / 2.35;
      tiltedRing.rotation.y = .28;
      rings.add(tiltedRing);

      const pulseRing = new THREE.Mesh(
        new THREE.RingGeometry(data.radius * 1.15, data.radius * 1.24, 72),
        new THREE.MeshBasicMaterial({ color: data.accent || data.color, transparent: true, opacity: .36, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      pulseRing.rotation.x = Math.PI / 2;
      rings.add(pulseRing);

      /* Clean satellite orbit track */
      const orbits = new THREE.Group();
      group.add(orbits);
      this.addOrbitLines(orbits, 1, data.color);
      const satGroup = new THREE.Group();
      group.add(satGroup);
      const center = { data, group, mesh, glow, rings, pulseRing, tiltedRing, orbits, satGroup };
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
        label: '双层护盾 · 守护中'
      };
      const group = new THREE.Group();
      group.position.fromArray(data.position);
      this.world.add(group);

      /* Event Horizon Core + Photon Sphere Rim */
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(data.radius, 48, 36),
        new THREE.MeshBasicMaterial({ color: 0x010206 })
      );
      mesh.userData.data = data;
      group.add(mesh);
      this.selectable.push(mesh);

      const photonSphere = new THREE.Mesh(
        new THREE.SphereGeometry(data.radius * 1.06, 40, 28),
        new THREE.MeshBasicMaterial({
          color: 0xffb86c,
          transparent: true,
          opacity: .30,
          side: THREE.BackSide,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        })
      );
      group.add(photonSphere);

      /* Textured Relativistic Accretion Disk (Gargantua style) */
      const disk = new THREE.Mesh(
        new THREE.RingGeometry(1.12, 2.88, 140, 1),
        new THREE.MeshBasicMaterial({
          map: this.accretionTexture,
          color: 0xffb26b,
          transparent: true,
          opacity: .82,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        })
      );
      disk.rotation.x = 1.22;
      disk.rotation.y = .2;
      group.add(disk);

      const rings = new THREE.Group();
      group.add(rings);
      const torus = new THREE.Mesh(
        new THREE.TorusGeometry(1.36, .038, 12, 140),
        new THREE.MeshBasicMaterial({ color: 0xffcf86, transparent: true, opacity: .85, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      torus.rotation.x = 1.22;
      torus.rotation.y = .2;
      rings.add(torus);

      /* Gravitational Lensing Vertical Arch */
      const lensingArch = new THREE.Mesh(
        new THREE.TorusGeometry(1.22, .024, 10, 120),
        new THREE.MeshBasicMaterial({ color: 0xff9e54, transparent: true, opacity: .52, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      lensingArch.rotation.y = .2;
      rings.add(lensingArch);

      const glow = this.glow(0xff8542, 7.4, .56, true);
      group.add(glow);

      /* Data-driven inward-spiraling intercepted request particles */
      const particleCount = 220;
      const pos = new Float32Array(particleCount * 3);
      this.bhParticleMeta = [];
      for (let i = 0; i < particleCount; i++) {
        const a = (i / particleCount) * Math.PI * 2;
        const r = 1.15 + (i % 12) * 0.20;
        const y = ((i % 5) - 2) * .03;
        pos[i * 3] = Math.cos(a) * r;
        pos[i * 3 + 1] = y;
        pos[i * 3 + 2] = Math.sin(a) * r;
        this.bhParticleMeta.push({ a, r, y, speed: .68 + (i % 4) * .20 });
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      const particles = new THREE.Points(
        geo,
        new THREE.PointsMaterial({ color: 0xffb36b, size: .062, transparent: true, opacity: .84, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      particles.rotation.x = 1.22;
      group.add(particles);

      const orbits = new THREE.Group();
      group.add(orbits);
      this.addOrbitLines(orbits, 1, 0xf2a558);
      const satGroup = new THREE.Group();
      group.add(satGroup);
      const center = { data, group, mesh, glow, rings, orbits, satGroup, disk, particles, lensingArch };
      this.addLabel(mesh, data, true);
      return center;
    }

    addOrbitLines(targetGroup, count, color) {
      for (let j = 0; j < count; j++) {
        const r = 2.28 + j * .55;
        const points = [];
        for (let i = 0; i <= 140; i++) {
          const a = i / 140 * Math.PI * 2;
          points.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
        }
        const line = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(points),
          new THREE.LineBasicMaterial({ color, transparent: true, opacity: .22, blending: THREE.AdditiveBlending, depthWrite: false })
        );
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
        { id: 'gl-telegram', name: 'Telegram 通讯', short: 'Telegram', domain: 'telegram.org', subtitle: '海外代理 · Shunt_Outside_CN', meta: '148 ms', rtt: 148, down_rate: 8192, up_rate: 2048, conns: 2, kind: 'service', region: 'global', status: 'ok', topRank: 4 },
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
        const ch = center.satGroup.children[0];
        center.satGroup.remove(ch);
        if (ch.traverse) {
          ch.traverse(o => {
            if (o.geometry && o.geometry.dispose) o.geometry.dispose();
            if (o.material && o.material.dispose) o.material.dispose();
          });
        }
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

        const radius = isBh ? .12 : (isCore ? .155 : .145);
        const geo = isBh ? new THREE.OctahedronGeometry(radius * 1.18, 0) : new THREE.SphereGeometry(radius, 12, 10);
        const mat = new THREE.MeshLambertMaterial({
          color: col,
          emissive: col,
          emissiveIntensity: .44,
          transparent: true,
          opacity: .96
        });
        const mesh = new THREE.Mesh(geo, mat);

        const orbitR = isBh ? 2.18 : (isCore ? 2.38 : 2.28);
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
        mesh.add(this.glow(col, isBh ? .95 : 1.15, .54));
        center.satGroup.add(mesh);

        const curve = new THREE.QuadraticBezierCurve3(
          new THREE.Vector3(0, 0, 0),
          new THREE.Vector3(mesh.position.x * .5, mesh.position.y + (isBh ? -.2 : .24), mesh.position.z * .5),
          mesh.position.clone()
        );
        const tether = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(curve.getPoints(24)),
          new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: isBh ? .28 : .24, blending: THREE.AdditiveBlending, depthWrite: false })
        );
        center.satGroup.add(tether);

        const tetherPackets = [];
        const sphereCount = gearInfo.gear === 'high' ? 2 : 1;
        for (let pIdx = 0; pIdx < sphereCount; pIdx++) {
          const pMesh = new THREE.Mesh(
            new THREE.SphereGeometry(.040 * gearInfo.scale, 10, 8),
            new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: .95, blending: THREE.AdditiveBlending })
          );
          pMesh.add(this.glow(col, .38 * gearInfo.scale, .68));
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
        if (this.selected && this.selected.id === dataObj.id) {
          this.selectedMesh = mesh;
        }
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
      this.createBeam('core_blackhole', '双层护盾阻断', this.centers.core, this.centers.blackhole, 0xf2a558, 5, 2.9, { rateBps: 0, conns: 4, hits: 0 });
    }

    createBeam(key, title, from, to, color, packetCount, lift, initStats) {
      const a = from.group.position.clone();
      const b = to.group.position.clone();
      const mid = a.clone().lerp(b, .5);
      mid.y += lift;
      mid.z -= 1.2;
      const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(curve.getPoints(96)),
        new THREE.LineBasicMaterial({ color, transparent: true, opacity: .42, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      this.world.add(line);
      this.beams.push(line);

      /* Volumetric energy sheath tube around main trunk */
      const sheathGeo = new THREE.TubeGeometry(curve, 64, 0.048, 8, false);
      const sheathMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: .12,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      });
      const sheath = new THREE.Mesh(sheathGeo, sheathMat);
      this.world.add(sheath);

      const gearInfo = computeSpeedGear(initStats ? initStats.rateBps : 32768, initStats ? initStats.conns : 4);
      const beamPackets = [];
      for (let i = 0; i < packetCount; i++) {
        const packet = new THREE.Mesh(
          new THREE.SphereGeometry(.058, 12, 10),
          new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: .98, blending: THREE.AdditiveBlending })
        );
        packet.add(this.glow(color, .68, .85));

        /* 3-stage luminous comet tail sprites trailing along the curve */
        const trailSprites = [];
        for (let tIdx = 1; tIdx <= 3; tIdx++) {
          const tSprite = this.glow(color, (.48 - tIdx * .11), (.52 - tIdx * .14));
          this.world.add(tSprite);
          trailSprites.push({ sprite: tSprite, lag: tIdx * 0.017 });
        }

        this.world.add(packet);
        const pktObj = {
          mesh: packet,
          trailSprites,
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
        sheath,
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
        beam.line.material.opacity = gearInfo.gear === 'high' ? 0.54 : (gearInfo.gear === 'med' ? 0.38 : 0.24);
      }
      if (beam.sheath && beam.sheath.material) {
        beam.sheath.material.opacity = gearInfo.gear === 'high' ? 0.17 : (gearInfo.gear === 'med' ? 0.11 : 0.06);
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
        const ch = this.liveConnGroup.children[0];
        this.liveConnGroup.remove(ch);
        if (ch.traverse) {
          ch.traverse(o => {
            if (o.geometry && o.geometry.dispose) o.geometry.dispose();
            if (o.material && o.material.dispose) o.material.dispose();
          });
        }
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

        const arcOpacity = gearInfo.gear === 'high' ? 0.62 : (gearInfo.gear === 'med' ? 0.45 : 0.30);
        const arcLine = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(curve.getPoints(72)),
          new THREE.LineBasicMaterial({ color: arcColor, transparent: true, opacity: arcOpacity, blending: THREE.AdditiveBlending, depthWrite: false })
        );
        this.liveConnGroup.add(arcLine);

        const sphereCount = gearInfo.gear === 'high' ? 3 : (gearInfo.gear === 'med' ? 2 : 1);
        const arcPackets = [];
        for (let sIdx = 0; sIdx < sphereCount; sIdx++) {
          const pMesh = new THREE.Mesh(
            new THREE.SphereGeometry(0.058 * gearInfo.scale, 10, 8),
            new THREE.MeshBasicMaterial({ color: arcColor, transparent: true, opacity: 0.98, blending: THREE.AdditiveBlending })
          );
          pMesh.add(this.glow(arcColor, 0.62 * gearInfo.scale, 0.82));
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
        wallpaperMode: this.wallpaperMode,
        liveConnSummary: this.liveConnSummary,
        liveConnArcsCount: this.liveConnArcs.length
      };
    }

    buildSelectionHalo() {
      this.selectionHalo = this.glow(0x8df3ff, 2.5, .78, true);
      this.selectionHalo.visible = false;
      this.world.add(this.selectionHalo);
      this.selectionRing = new THREE.Mesh(
        new THREE.TorusGeometry(.52, .020, 6, 90),
        new THREE.MeshBasicMaterial({ color: 0x8df3ff, transparent: true, opacity: .82, blending: THREE.AdditiveBlending, depthWrite: false })
      );
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
        if (event.key === 'Escape' && this.options.page === 'galaxy') {
          if (this.wallpaperMode && this.options.onWallpaperToggle) {
            this.options.onWallpaperToggle(false);
          } else {
            this.reset();
          }
        }
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
      this.tooltip.querySelector('b').textContent = data.name + (data.speedGearLabel ? (' · ' + data.speedGearLabel + '速') : '');
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
      const insp = document.getElementById('inspector');
      const inspOpen = insp && insp.classList.contains('open') && !this.wallpaperMode && !narrow;
      const views = {
        panorama: { target: inspOpen ? [2.25, -0.15, 0] : [0, -0.1, 0], radius: narrow ? 33 : (this.wallpaperMode ? 22.2 : 25.2), theta: .16, phi: 1.18 },
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
        center.glow.material.opacity = active ? (id === 'blackhole' ? .56 : (id === 'cn' ? .48 : .42)) : .14;
      });
    }

    setWallpaperMode(value) {
      this.wallpaperMode = Boolean(value);
      if (this.wallpaperMode) {
        this.autoRotate = !reducedMotion;
      }
      if (this.mode === 'panorama') {
        this.setMode('panorama');
      }
      setTimeout(() => this.resize(), 60);
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
    startLoop() {
      if (this._loopRunning) return;
      const pageEl = document.getElementById("page-galaxy");
      if (!this.active || document.hidden || (pageEl && !pageEl.classList.contains("active"))) return;
      if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches && !this.dragging) {
        this.render();
        return;
      }
      this._loopRunning = true;
      this._rafId = requestAnimationFrame(this._tickBound);
    }
    stopLoop() {
      this._loopRunning = false;
      if (this._swTimer) {
        clearTimeout(this._swTimer);
        this._swTimer = 0;
      }
      if (this._rafId) {
        cancelAnimationFrame(this._rafId);
        this._rafId = 0;
      }
      if (this.renderer && this.renderer.setAnimationLoop) {
        this.renderer.setAnimationLoop(null);
      }
    }
    setActive(value) {
      this.active = Boolean(value);
      if (this.active) this.startLoop();
      else this.stopLoop();
    }

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
      if (Array.isArray(payload.blackholeSatellites)) {
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
      const elGl = document.getElementById('wp-stat-global');
      const elCn = document.getElementById('wp-stat-cn');
      const elBh = document.getElementById('wp-stat-bh');
      if (elGl && this.beamsByKey.core_global) elGl.textContent = this.beamsByKey.core_global.gearFullLabel + ' · ↓' + fmtRateShort(this.beamsByKey.core_global.rateBps);
      if (elCn && this.beamsByKey.core_cn) elCn.textContent = this.beamsByKey.core_cn.gearFullLabel + ' · ↓' + fmtRateShort(this.beamsByKey.core_cn.rateBps);
      if (elBh && this.beamsByKey.core_blackhole) elBh.textContent = (this.beamsByKey.core_blackhole.conns || 0) + ' 规则簇';
    }

    resize() {
      const width = Math.min(3840, Math.max(1, this.shell.clientWidth || 1280));
      const height = Math.min(2160, Math.max(1, this.shell.clientHeight || 720));
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      if (this._lastW === width && this._lastH === height && this._lastDpr === dpr) return;
      this._lastW = width;
      this._lastH = height;
      this._lastDpr = dpr;
      if (this.renderer) this.renderer.setSize(width, height, false);
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
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
        const topAllowed = !item.cluster && (item.data.topRank != null ? item.data.topRank < (isFocusedGalaxy ? 8 : (this.surge || this.wallpaperMode ? 5 : 3)) : false);
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
      const captionVisible = caption && !caption.classList.contains('dimmed') && !this.wallpaperMode;
      const safeZone = captionVisible ? { x: 8, y: 54, w: Math.min(width * .56, 360), h: width < 720 ? 140 : 170 } : null;
      const occupied = [];
      const shellRect = this.shell.getBoundingClientRect();
      const inspector = document.getElementById('inspector');
      if (inspector && inspector.classList.contains('open') && !this.wallpaperMode) {
        const inspectorRect = inspector.getBoundingClientRect();
        occupied.push({ x: inspectorRect.left - shellRect.left - 12, y: inspectorRect.top - shellRect.top - 12, w: inspectorRect.width + 24, h: inspectorRect.height + 24 });
      }
      const dockEl = this.shell.querySelector('.control-dock');
      if (dockEl && !this.wallpaperMode) {
        const dr = dockEl.getBoundingClientRect();
        occupied.push({ x: dr.left - shellRect.left - 12, y: dr.top - shellRect.top - 14, w: dr.width + 24, h: dr.height + 28 });
      }
      ctx.textBaseline = 'middle';
      projected.forEach(({ item, selected, x, y }) => {
        const data = item.data;
        const isCluster = item.cluster;
        const title = data.short || data.name;
        const gearSuffix = (!isCluster && data.speedGearLabel) ? (' · ' + data.speedGearLabel) : '';
        const rawClusterMeta = String(data.label || data.subtitle || '');
        const cleanClusterMeta = rawClusterMeta.startsWith(title) ? (rawClusterMeta.slice(title.length).replace(/^[\s·•|-]+/, '') || data.subtitle || rawClusterMeta) : rawClusterMeta;
        const meta = isCluster ? cleanClusterMeta : ((data.meta || (data.rtt != null ? data.rtt + ' ms' : '活跃')) + gearSuffix);
        ctx.font = (isCluster ? '600 11.5px ' : '500 10px ') + '-apple-system, "SF Pro Text", "PingFang SC", sans-serif';
        const titleWidth = ctx.measureText(title).width;
        ctx.font = '500 9.5px -apple-system, "SF Pro Text", "PingFang SC", sans-serif';
        const metaWidth = ctx.measureText(meta).width;
        const boxWidth = Math.min(242, (isCluster ? Math.max(titleWidth, metaWidth) + 38 : titleWidth + metaWidth + 32));
        const boxHeight = isCluster ? 40 : 24;
        const onRight = x + boxWidth + 24 < width - 10;
        const bx = clamp(onRight ? x + 14 : x - boxWidth - 14, 8, width - boxWidth - 8);
        const by = clamp(y - boxHeight / 2, 64, Math.max(68, height - boxHeight - 88));
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

        /* Precision VisionOS Spatial Callout Leader Line */
        ctx.strokeStyle = selected
          ? 'rgba(110,231,245,.90)'
          : isCluster
            ? (isCnNode ? 'rgba(249,168,212,.58)' : 'rgba(136,163,205,.45)')
            : 'rgba(126,148,184,.25)';
        ctx.lineWidth = selected ? 1.4 : 1.0;
        ctx.beginPath();
        const edgeX = onRight ? bx : bx + boxWidth;
        ctx.moveTo(x, y);
        ctx.lineTo(edgeX, by + boxHeight / 2);
        ctx.stroke();

        /* VisionOS Glass Pill Body */
        this.roundedRect(ctx, bx, by, boxWidth, boxHeight, isCluster ? 11 : 7);
        const bgGrad = ctx.createLinearGradient(bx, by, bx, by + boxHeight);
        if (selected) {
          bgGrad.addColorStop(0, 'rgba(14, 32, 48, 0.96)');
          bgGrad.addColorStop(1, 'rgba(8, 18, 30, 0.96)');
        } else if (isCluster) {
          bgGrad.addColorStop(0, 'rgba(13, 21, 38, 0.94)');
          bgGrad.addColorStop(1, 'rgba(6, 11, 22, 0.94)');
        } else {
          bgGrad.addColorStop(0, 'rgba(9, 15, 28, 0.89)');
          bgGrad.addColorStop(1, 'rgba(5, 9, 18, 0.89)');
        }
        ctx.fillStyle = bgGrad;
        ctx.fill();
        ctx.stroke();

        /* Cluster Left Accent Pill Bar */
        if (isCluster) {
          ctx.fillStyle = color;
          this.roundedRect(ctx, bx + 4, by + 6, 3, boxHeight - 12, 1.5);
          ctx.fill();
        }

        /* Target Anchor Reticle */
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, selected ? 3.5 : 2.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(bx + (isCluster ? 13 : 10), by + (isCluster ? 13.5 : boxHeight / 2), isCluster ? 3.2 : 2.5, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = (isCluster ? '600 11.5px ' : '500 10px ') + '-apple-system, "SF Pro Text", "PingFang SC", sans-serif';
        ctx.fillStyle = selected ? '#f8fdff' : isCluster ? '#f2f7ff' : '#d6e2f5';
        ctx.fillText(title, bx + (isCluster ? 21 : 18), by + (isCluster ? 13.5 : boxHeight / 2));

        ctx.font = '500 9.5px -apple-system, "SF Pro Text", "PingFang SC", sans-serif';
        ctx.fillStyle = data.region === 'blackhole' ? '#f7bd68' : isCnNode ? '#f9a8d4' : (data.status === 'suspect' ? '#e5a95c' : '#94a7c4');
        if (isCluster) {
          ctx.fillText(meta, bx + 21, by + 28.5);
        } else {
          ctx.fillText(meta, bx + boxWidth - metaWidth - 8, by + boxHeight / 2);
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
        ctx.font = '600 9.5px -apple-system, "SF Pro Text", "PingFang SC", sans-serif';
        const pw = ctx.measureText(pillTxt).width + 18;
        const ph = 21;
        const px = clamp(mx - pw / 2, 8, width - pw - 8);
        const py = clamp(my - ph / 2, 8, height - ph - 8);
        const rect = { x: px, y: py, w: pw, h: ph };
        const collides = occupied.some(other => !(rect.x + rect.w < other.x || rect.x > other.x + other.w || rect.y + rect.h < other.y || rect.y > other.y + other.h));
        if (collides) return;
        occupied.push(rect);
        const pillColor = bKey === 'core_cn' ? '#f9a8d4' : (bKey === 'core_blackhole' ? '#f7bd68' : '#6ee7f5');
        this.roundedRect(ctx, px, py, pw, ph, 10.5);
        ctx.fillStyle = 'rgba(7, 14, 27, 0.93)';
        ctx.fill();
        ctx.strokeStyle = bm.gear === 'high' ? pillColor : 'rgba(156, 176, 212, 0.38)';
        ctx.lineWidth = 1.0;
        ctx.stroke();
        ctx.fillStyle = pillColor;
        ctx.fillText(pillTxt, px + 9, py + ph / 2);
      });

      /* When 流量激增 (Real 3D Connection Expression) is active, render HUD banner + readable flow tags */
      if (this.surge && this.liveConnSummary) {
        const s = this.liveConnSummary;
        const bannerTxt = ' 真实连接 3D 表达已激活 · 实时映射 ' + s.totalArcs + ' 条跨星系轨迹 (' + s.totalConns + ' 并发连接) · 挡位: 高[' + s.highCount + '] / 中[' + s.medCount + '] / 低[' + s.lowCount + ']';
        ctx.font = '600 10.5px -apple-system, "SF Pro Text", "PingFang SC", sans-serif';
        const bw = Math.min(width - 24, ctx.measureText(bannerTxt).width + 30);
        const bh = 28;
        const bx = (width - bw) / 2;
        const by = 22;
        this.roundedRect(ctx, bx, by, bw, bh, 14);
        ctx.fillStyle = 'rgba(8, 16, 30, 0.94)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(249, 168, 212, 0.62)';
        ctx.lineWidth = 1.15;
        ctx.stroke();
        ctx.fillStyle = '#f8fbff';
        ctx.fillText(bannerTxt, bx + 15, by + bh / 2);
      }
    }

    render() {
      const dt = Math.min(this.clock.getDelta(), .05);
      if (!this.active || document.hidden) return;
      const elapsed = this.clock.elapsedTime;
      if (this.autoRotate && !this.dragging) {
        this.desired.theta += dt * (this.wallpaperMode ? .038 : .028);
        if (this.wallpaperMode && this.mode === 'panorama') {
          this.desired.phi = 1.14 + Math.sin(elapsed * 0.22) * 0.08;
        }
      }
      this.updateCamera(dt);
      if (this.stars) this.stars.rotation.y += dt * .0018;
      if (this.eclipticPlane) this.eclipticPlane.rotation.y -= dt * .004;
      Object.entries(this.centers).forEach(([id, center], index) => {
        const rotSpeed = (.03 + index * .006);
        if (center.satGroup) {
          center.satGroup.rotation.y += dt * (id === 'blackhole' ? -rotSpeed * 1.2 : rotSpeed * .75);
        }
        center.mesh.rotation.y += dt * .12;
        if (center.tiltedRing) {
          center.tiltedRing.rotation.z += dt * .18;
        }
        if (center.pulseRing) {
          const pWave = (elapsed * 0.45 + index * 0.3) % 1;
          center.pulseRing.scale.setScalar(1 + pWave * 0.65);
          center.pulseRing.material.opacity = (1 - pWave) * 0.36;
        }
        if (center.disk && center.particles && this.bhParticleMeta) {
          center.disk.rotation.z -= dt * .28;
          if (center.lensingArch) center.lensingArch.rotation.z += dt * .16;
          const posAttr = center.particles.geometry.getAttribute('position');
          const arr = posAttr.array;
          const bhBeam = this.beamsByKey.core_blackhole;
          const pullMult = bhBeam && bhBeam.gear === 'high' ? 1.85 : (bhBeam && bhBeam.gear === 'med' ? 1.35 : 1.0);
          for (let i = 0; i < this.bhParticleMeta.length; i++) {
            const m = this.bhParticleMeta[i];
            m.a += dt * m.speed * (2.5 / Math.max(1.05, m.r)) * pullMult;
            m.r -= dt * .20 * m.speed * pullMult;
            if (m.r < 1.06) {
              m.r = 2.75 + (i % 5) * .15;
            }
            arr[i * 3] = Math.cos(m.a) * m.r;
            arr[i * 3 + 1] = m.y * ((m.r - 1.0) / 2.2);
            arr[i * 3 + 2] = Math.sin(m.a) * m.r;
          }
          posAttr.needsUpdate = true;
        }
      });

      /* Animate trunk beam spheres + comet tails at their real 3-tier speed gear (高: 0.56 / 中: 0.26 / 低: 0.095) */
      this.packets.forEach((packet, i) => {
        const visibleCount = Math.max(2, Math.round(packet.totalOnBeam * (packet.activeRatio || 0.6)));
        const vis = packet.index < visibleCount || this.surge;
        packet.mesh.visible = vis;
        if (packet.trailSprites) {
          packet.trailSprites.forEach(ts => { ts.sprite.visible = vis; });
        }
        if (!vis) return;
        const speed = packet.speed || 0.26;
        const p = (elapsed * speed + packet.offset) % 1;
        packet.mesh.position.copy(packet.curve.getPoint(p));
        const pulse = (packet.baseScale || 1.0) * (1 + Math.sin(elapsed * 5 + i) * .12);
        packet.mesh.scale.setScalar(pulse);
        if (packet.trailSprites) {
          packet.trailSprites.forEach((ts, tIdx) => {
            const tp = (p - ts.lag * (packet.gear === 'high' ? 1.45 : 1.0) + 1) % 1;
            ts.sprite.position.copy(packet.curve.getPoint(tp));
            ts.sprite.scale.setScalar((0.46 - tIdx * 0.10) * pulse);
          });
        }
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
    lastErrorReason: null,
    create(canvas, options) {
      if (!window.THREE) {
        this.lastErrorReason = 'ASSET_LOAD_FAILED';
        console.error('Nexus 3D asset three.min.js not loaded.');
        return null;
      }
      try {
        const instance = new NexusUniverse(canvas, options);
        window.__nexusScene = instance;
        this.lastErrorReason = null;
        return instance;
      } catch (error) {
        this.lastErrorReason = 'WEBGL_CONTEXT_FAILED';
        console.error('Nexus 3D WebGL initialization failed:', error);
        return null;
      }
    }
  };
})();
