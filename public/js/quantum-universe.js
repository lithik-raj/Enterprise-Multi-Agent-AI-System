/**
 * ============================================================================
 * Enterprise Multi-Agent AI — Ultra-Premium Quantum Energy Universe
 * ============================================================================
 * Cinematic Real-Time 3D WebGL Background:
 * - Living quantum singularity energy core with 3D simplex noise displacement
 * - Iridescent liquid distortion shell with thin-film chromatic dispersion (RGB split)
 * - Relativistic quantum accretion disk ring with Keplerian velocity gradients
 * - Flowing plasma filaments with dual traveling soliton light pulses
 * - 6,000+ GPU-computed orbital accretion particles & 3D curl turbulence
 * - Cinematic depth-of-field with optical bokeh disc defocusing
 * - Volumetric light rays, radiant corona, and deep cosmic dust
 * - Interactive camera parallax responding smoothly to cursor movement
 * - Interactive pointer shockwave ripples with gravitational fluid response
 * - Adaptive DPR, mobile optimization, reduced-motion preferences, WebGL resilience
 * ============================================================================
 */

(function () {
  "use strict";

  // Check for reduced motion preference and mobile devices
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isMobile =
    window.innerWidth <= 768 ||
    /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

  // Performance budget tuned for high responsiveness and 60fps rendering
  const CONFIG = {
    particleCount: isMobile ? 1200 : 2400,
    dustCount: isMobile ? 400 : 800,
    filamentCount: isMobile ? 4 : 7,
    coreSubdivisions: isMobile ? 18 : 28,
    speedMultiplier: prefersReducedMotion ? 0.25 : 1.0,
    parallaxStrength: isMobile ? 0.8 : 1.5,
    maxDPR: isMobile ? 1.0 : Math.min(window.devicePixelRatio || 1, 1.25),
  };

  // ── Color Palette Definition ─────────────────────────────────────────────
  // Deep obsidian black: #03050c
  // Electric cyan: #00f0ff / #38bdf8
  // Ultraviolet purple: #8b5cf6 / #6366f1
  // Restrained magenta: #f43f5e / #ec4899
  // Core white-gold: #ffffff / #fef08a

  const PALETTE = {
    obsidian: 0x03050c,
    cyan: new Float32Array([0.0, 0.94, 1.0]),
    purple: new Float32Array([0.54, 0.36, 0.96]),
    magenta: new Float32Array([0.96, 0.25, 0.45]),
    whiteGold: new Float32Array([1.0, 0.97, 0.88]),
  };

  // ── GLSL 3D Simplex Noise Library ─────────────────────────────────────────
  const GLSL_SIMPLEX_NOISE = `
    // Simplex 3D noise (Stefan Gustavson & Ian McEwan)
    vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
    vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}

    float snoise(vec3 v){
      const vec2 C = vec2(1.0/6.0, 1.0/3.0);
      const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

      // First corner
      vec3 i  = floor(v + dot(v, C.yyy));
      vec3 x0 = v - i + dot(i, C.xxx);

      // Other corners
      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min(g.xyz, l.zxy);
      vec3 i2 = max(g.xyz, l.zxy);

      vec3 x1 = x0 - i1 + 1.0 * C.xxx;
      vec3 x2 = x0 - i2 + 2.0 * C.xxx;
      vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;

      // Permutations
      i = mod(i, 289.0);
      vec4 p = permute(permute(permute(
                i.z + vec4(0.0, i1.z, i2.z, 1.0))
              + i.y + vec4(0.0, i1.y, i2.y, 1.0))
              + i.x + vec4(0.0, i1.x, i2.x, 1.0));

      // Gradients
      float n_ = 0.142857142857; // 1.0/7.0
      vec3  ns = n_ * D.wyz - D.xzx;

      vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

      vec4 x_ = floor(j * ns.z);
      vec4 y_ = floor(j - 7.0 * x_);

      vec4 x = x_ * ns.x + ns.yyyy;
      vec4 y = y_ * ns.x + ns.yyyy;
      vec4 h = 1.0 - abs(x) - abs(y);

      vec4 b0 = vec4(x.xy, y.xy);
      vec4 b1 = vec4(x.zw, y.zw);

      vec4 s0 = floor(b0) * 2.0 + 1.0;
      vec4 s1 = floor(b1) * 2.0 + 1.0;
      vec4 sh = -step(h, vec4(0.0));

      vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
      vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

      vec3 p0 = vec3(a0.xy, h.x);
      vec3 p1 = vec3(a0.zw, h.y);
      vec3 p2 = vec3(a1.xy, h.z);
      vec3 p3 = vec3(a1.zw, h.w);

      // Normalise gradients
      vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
      p0 *= norm.x;
      p1 *= norm.y;
      p2 *= norm.z;
      p3 *= norm.w;

      // Mix contributions
      vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
      m = m * m;
      return 42.0 * dot(m * m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
    }
  `;

  // Fallback trigger for 2D Neural Canvas
  function triggerFallback() {
    window.QUANTUM_UNIVERSE_ACTIVE = false;
    const fallbackCanvas = document.getElementById("neural-motion-canvas");
    if (fallbackCanvas) {
      fallbackCanvas.style.display = "block";
      if (typeof window.setupNeuralMotionCanvas === "function") {
        window.setupNeuralMotionCanvas(true);
      }
    }
  }

  // ── Main Initializer ─────────────────────────────────────────────────────
  let initRetries = 0;
  function initQuantumUniverse() {
    const canvas = document.getElementById("quantum-universe-canvas");
    if (!canvas) return;

    // Fixed background setup sitting cleanly behind all UI
    canvas.style.position = "fixed";
    canvas.style.top = "0";
    canvas.style.left = "0";
    canvas.style.width = "100vw";
    canvas.style.height = "100vh";
    canvas.style.zIndex = "0";
    canvas.style.pointerEvents = "none";
    canvas.style.display = "block";
    canvas.style.backgroundColor = "#03050c";

    if (typeof THREE === "undefined") {
      initRetries++;
      if (initRetries < 25) {
        setTimeout(initQuantumUniverse, 100);
      } else {
        console.warn("[QuantumUniverse] THREE.js failed to load. Triggering 2D fallback.");
        triggerFallback();
      }
      return;
    }

    let renderer, scene, camera;
    let coreMesh, outerShellMesh, accretionDiskMesh, coronaMesh;
    let particlePoints, dustPoints;
    let filamentMeshes = [];
    let godRayMeshes = [];
    let animationFrameId = null;
    let isVisible = true;
    let clock = new THREE.Clock();

    // Mouse & Parallax tracking with smooth spring damping
    const mouse = {
      x: 0,
      y: 0,
      targetX: 0,
      targetY: 0,
    };

    // Interactive Shockwave State
    let shockwaveStartTime = -100.0;
    function triggerShockwave() {
      if (prefersReducedMotion) return;
      shockwaveStartTime = clock.getElapsedTime();
    }
    window.addEventListener("pointerdown", triggerShockwave, { passive: true });

    // 1. Scene & Camera Setup
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(PALETTE.obsidian, 0.015);

    camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 150);
    camera.position.set(0, 0, 18.5);

    // 2. WebGL Renderer with graceful error capture
    try {
      renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: !isMobile,
        alpha: true,
        powerPreference: "high-performance",
      });
    } catch (e) {
      console.warn("[QuantumUniverse] WebGL not supported, falling back:", e);
      triggerFallback();
      return;
    }

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, CONFIG.maxDPR));
    renderer.setClearColor(PALETTE.obsidian, 1.0);

    // Context loss & recovery protection
    canvas.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      console.warn("[QuantumUniverse] WebGL context lost! Switching to 2D neural fallback.");
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
      }
      triggerFallback();
    }, false);

    canvas.addEventListener("webglcontextrestored", () => {
      console.info("[QuantumUniverse] WebGL context restored. Rebuilding 3D universe...");
      initQuantumUniverse();
    }, false);

    // ── Layer 1: Living Quantum Singularity Energy Core ─────────────────────
    const coreVertexShader = `
      ${GLSL_SIMPLEX_NOISE}
      uniform float uTime;
      uniform vec2 uMouse;
      uniform float uShockwave;
      varying vec3 vNormal;
      varying vec3 vPosition;
      varying float vNoise;
      varying vec3 vViewPosition;

      void main() {
        vNormal = normalize(normalMatrix * normal);
        vPosition = position;

        // Multi-frequency noise displacement for undulating plasma surface
        float t = uTime * 0.45;
        float n1 = snoise(position * 0.85 + vec3(0.0, t * 0.7, 0.0));
        float n2 = snoise(position * 2.1 - vec3(t * 0.5, 0.0, t * 0.3)) * 0.35;
        float n3 = snoise(position * 4.2 + vec3(t * 0.9, t * 0.4, 0.0)) * 0.15;
        float totalNoise = n1 + n2 + n3;
        vNoise = totalNoise;

        // Cursor perturbation
        float distToMouse = length(position.xy - uMouse * 4.0);
        float mouseAttract = smoothstep(6.0, 0.0, distToMouse) * 0.25;

        // Shockwave ripple displacement
        float shockDist = length(position);
        float shockFront = uShockwave * 10.0;
        float shockRipple = 0.0;
        if (uShockwave >= 0.0 && uShockwave < 2.5) {
          shockRipple = exp(-pow(shockDist - shockFront, 2.0) / 0.8) * 0.45;
        }

        // Displace along normal
        float displacement = totalNoise * 0.42 + mouseAttract + shockRipple;
        vec3 newPosition = position + normal * displacement;

        vec4 mvPosition = modelViewMatrix * vec4(newPosition, 1.0);
        vViewPosition = -mvPosition.xyz;
        gl_Position = projectionMatrix * mvPosition;
      }
    `;

    const coreFragmentShader = `
      uniform float uTime;
      varying vec3 vNormal;
      varying vec3 vPosition;
      varying float vNoise;
      varying vec3 vViewPosition;

      void main() {
        vec3 normal = normalize(vNormal);
        vec3 viewDir = normalize(vViewPosition);

        // Cinematic Fresnel rim lighting
        float fresnel = pow(1.0 - max(0.0, dot(normal, viewDir)), 3.0);

        // Core colors
        vec3 deepObsidian = vec3(0.015, 0.035, 0.08);
        vec3 electricCyan = vec3(0.0, 0.94, 1.0);
        vec3 ultraPurple  = vec3(0.55, 0.24, 0.98);
        vec3 magenta      = vec3(0.96, 0.20, 0.54);
        vec3 whiteGold    = vec3(1.0, 0.98, 0.92);

        // Dynamic plasma turbulence
        float pulse = 0.5 + 0.5 * sin(uTime * 1.8 + vPosition.y * 1.4);
        float plasmaMask = smoothstep(-0.4, 0.6, vNoise);
        float veinMask = smoothstep(0.35, 0.55, abs(vNoise));

        // Color blend based on depth, noise, and fresnel
        vec3 color = mix(deepObsidian, ultraPurple, plasmaMask);
        color = mix(color, electricCyan, veinMask * 0.85);
        color = mix(color, magenta, fresnel * 0.65);
        color += whiteGold * pow(fresnel, 4.0) * 0.9;
        color += electricCyan * pulse * 0.25;

        // Alpha falloff
        float alpha = clamp(0.55 + fresnel * 0.45 + veinMask * 0.2, 0.0, 0.95);

        gl_FragColor = vec4(color, alpha);
      }
    `;

    const coreMaterial = new THREE.ShaderMaterial({
      vertexShader: coreVertexShader,
      fragmentShader: coreFragmentShader,
      uniforms: {
        uTime: { value: 0.0 },
        uMouse: { value: new THREE.Vector2(0, 0) },
        uShockwave: { value: 999.0 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    const coreGeometry = new THREE.IcosahedronGeometry(2.5, CONFIG.coreSubdivisions);
    coreMesh = new THREE.Mesh(coreGeometry, coreMaterial);
    scene.add(coreMesh);

    // ── Layer 2: Iridescent Liquid Distortion Quantum Shell ────────────────
    const shellVertexShader = `
      ${GLSL_SIMPLEX_NOISE}
      uniform float uTime;
      varying vec3 vNormal;
      varying vec3 vViewPosition;
      varying vec3 vWorldPosition;

      void main() {
        vNormal = normalize(normalMatrix * normal);
        float t = uTime * 0.25;

        // Multi-layered domain-warped liquid distortion
        vec3 p = position * 0.55;
        float warp1 = snoise(p + vec3(0.0, t * 0.6, 0.0));
        float warp2 = snoise(p + vec3(warp1 * 0.4, 0.0, t * 0.4));
        float liquid = snoise(p + vec3(warp1, warp2, t * 0.3)) * 0.3;

        vec3 newPos = position + normal * liquid;
        vec4 worldPos = modelMatrix * vec4(newPos, 1.0);
        vWorldPosition = worldPos.xyz;

        vec4 mvPosition = modelViewMatrix * vec4(newPos, 1.0);
        vViewPosition = -mvPosition.xyz;
        gl_Position = projectionMatrix * mvPosition;
      }
    `;

    const shellFragmentShader = `
      uniform float uTime;
      varying vec3 vNormal;
      varying vec3 vViewPosition;
      varying vec3 vWorldPosition;

      void main() {
        vec3 normal = normalize(vNormal);
        vec3 viewDir = normalize(vViewPosition);

        float fresnel = pow(1.0 - max(0.0, dot(normal, viewDir)), 2.6);

        // Thin-film iridescent chromatic dispersion (RGB channel split)
        float shiftR = sin(vWorldPosition.y * 1.4 + uTime * 0.8) * 0.5 + 0.5;
        float shiftG = sin(vWorldPosition.y * 1.4 + uTime * 0.8 + 1.05) * 0.5 + 0.5;
        float shiftB = sin(vWorldPosition.y * 1.4 + uTime * 0.8 + 2.10) * 0.5 + 0.5;

        vec3 cCyan = vec3(0.0, 0.94, 1.0);
        vec3 cPurple = vec3(0.55, 0.24, 0.98);
        vec3 cMagenta = vec3(0.96, 0.22, 0.52);

        vec3 colR = mix(cMagenta, cCyan, shiftR);
        vec3 colG = mix(cCyan, cPurple, shiftG);
        vec3 colB = mix(cPurple, cMagenta, shiftB);
        vec3 liquidColor = vec3(colR.r, colG.g, colB.b);

        vec3 finalColor = mix(liquidColor * 0.7, cCyan, fresnel);
        finalColor += cMagenta * pow(fresnel, 3.8) * 0.85;

        float alpha = clamp(fresnel * 0.48 + 0.08, 0.0, 0.85);
        gl_FragColor = vec4(finalColor, alpha);
      }
    `;

    const shellMaterial = new THREE.ShaderMaterial({
      vertexShader: shellVertexShader,
      fragmentShader: shellFragmentShader,
      uniforms: {
        uTime: { value: 0.0 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      depthWrite: false,
    });

    const shellGeometry = new THREE.IcosahedronGeometry(3.3, 24);
    outerShellMesh = new THREE.Mesh(shellGeometry, shellMaterial);
    scene.add(outerShellMesh);

    // ── Layer 2.5: Relativistic Quantum Accretion Disk Ring ─────────────────
    const diskVertexShader = `
      varying vec2 vUv;
      varying vec3 vWorldPosition;
      varying vec3 vViewPosition;

      void main() {
        vUv = uv;
        vec4 worldPos = modelMatrix * vec4(position, 1.0);
        vWorldPosition = worldPos.xyz;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        vViewPosition = -mvPosition.xyz;
        gl_Position = projectionMatrix * mvPosition;
      }
    `;

    const diskFragmentShader = `
      uniform float uTime;
      varying vec2 vUv;
      varying vec3 vWorldPosition;
      varying vec3 vViewPosition;

      void main() {
        // Polar coordinates for RingGeometry: UV normalized [-1, 1]
        vec2 p = vUv * 2.0 - 1.0;
        float r = length(p);
        if (r < 0.42 || r > 0.98) discard;

        float theta = atan(p.y, p.x);

        // Keplerian differential rotation (inner material orbits faster)
        float speed = 1.0 / (r * 0.85 + 0.18);
        float angle = theta + uTime * speed * 0.45;

        // Multi-arm logarithmic spiral density waves
        float spiral1 = sin(angle * 4.0 - r * 15.0 + uTime * 0.6) * 0.5 + 0.5;
        float spiral2 = cos(angle * 6.0 - r * 22.0 - uTime * 0.4) * 0.5 + 0.5;
        float density = pow(spiral1 * spiral2, 1.3) * 1.8;

        // Smooth radial edge falloff
        float radialFalloff = smoothstep(0.42, 0.50, r) * smoothstep(0.98, 0.72, r);

        // Relativistic Doppler beaming
        float doppler = 1.0 + 0.42 * sin(theta + 0.5);

        // Palette blending
        vec3 colCyan    = vec3(0.0, 0.94, 1.0);
        vec3 colPurple  = vec3(0.55, 0.24, 0.98);
        vec3 colMagenta = vec3(0.96, 0.20, 0.54);
        vec3 colWhite   = vec3(1.0, 0.98, 0.92);

        float tCol = (r - 0.42) / 0.56;
        vec3 diskColor = mix(colCyan, colPurple, smoothstep(0.0, 0.55, tCol));
        diskColor = mix(diskColor, colMagenta, smoothstep(0.45, 1.0, tCol));
        diskColor = mix(diskColor, colWhite, pow(density, 2.5) * (1.0 - tCol) * 0.9);

        diskColor *= doppler;
        float alpha = clamp(density * radialFalloff * 0.85 * doppler, 0.0, 0.9);

        gl_FragColor = vec4(diskColor, alpha);
      }
    `;

    const diskMaterial = new THREE.ShaderMaterial({
      vertexShader: diskVertexShader,
      fragmentShader: diskFragmentShader,
      uniforms: {
        uTime: { value: 0.0 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    const diskGeometry = new THREE.RingGeometry(2.8, 6.6, 96, 10);
    accretionDiskMesh = new THREE.Mesh(diskGeometry, diskMaterial);
    accretionDiskMesh.rotation.x = Math.PI * 0.42; // Cinematic tilt
    accretionDiskMesh.rotation.z = Math.PI * 0.15;
    scene.add(accretionDiskMesh);

    // ── Layer 3: Flowing Plasma Filaments with Traveling Light Solitons ──────
    function createPlasmaFilaments() {
      const filamentMatVertex = `
        uniform float uTime;
        varying vec2 vUv;
        varying vec3 vPosition;

        void main() {
          vUv = uv;
          vPosition = position;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `;

      const filamentMatFragment = `
        uniform float uTime;
        uniform vec3 uColorBase;
        uniform vec3 uColorPulse;
        uniform float uSpeed;
        varying vec2 vUv;
        varying vec3 vPosition;

        void main() {
          // Traveling energy soliton waves along the curve coordinate vUv.x
          float p1 = exp(-pow(mod(vUv.x * 3.0 - uTime * uSpeed, 1.0) - 0.5, 2.0) / 0.016);
          float p2 = exp(-pow(mod(vUv.x * 2.0 + uTime * (uSpeed * 0.75), 1.0) - 0.5, 2.0) / 0.022);
          float combinedPulse = p1 + p2 * 0.7;

          // Base subtle glow + intense pulse
          vec3 color = mix(uColorBase, uColorPulse, combinedPulse);
          color += vec3(1.0, 1.0, 1.0) * pow(combinedPulse, 3.0) * 0.85;

          float edgeGlow = sin(vUv.y * 3.14159);
          float alpha = clamp((0.2 + combinedPulse * 0.85) * edgeGlow, 0.0, 1.0);

          gl_FragColor = vec4(color, alpha);
        }
      `;

      for (let i = 0; i < CONFIG.filamentCount; i++) {
        const points = [];
        const numPoints = 84;
        const radius = 3.6 + (i % 3) * 0.9;
        const tiltAngle = (i / CONFIG.filamentCount) * Math.PI * 2;
        const pitch = (i % 2 === 0 ? 1 : -1) * (0.8 + i * 0.3);

        for (let j = 0; j <= numPoints; j++) {
          const t = (j / numPoints) * Math.PI * 2;
          const r = radius * (1.0 + 0.22 * Math.sin(t * 3.0 + i));
          const x = r * Math.cos(t);
          const y = r * Math.sin(t) * Math.cos(tiltAngle) + Math.sin(t * 2.0) * pitch;
          const z = r * Math.sin(t) * Math.sin(tiltAngle) + Math.cos(t * 2.0) * pitch;
          points.push(new THREE.Vector3(x, y, z));
        }

        const curve = new THREE.CatmullRomCurve3(points, true);
        const tubeGeom = new THREE.TubeGeometry(curve, 100, 0.028 + (i % 2) * 0.016, 6, true);

        const isMagenta = i % 3 === 0;
        const isCyan = i % 3 === 1;

        const baseCol = isMagenta
          ? new THREE.Vector3(0.4, 0.1, 0.35)
          : isCyan
          ? new THREE.Vector3(0.0, 0.3, 0.45)
          : new THREE.Vector3(0.25, 0.15, 0.5);

        const pulseCol = isMagenta
          ? new THREE.Vector3(0.96, 0.25, 0.55)
          : isCyan
          ? new THREE.Vector3(0.0, 0.95, 1.0)
          : new THREE.Vector3(0.65, 0.4, 1.0);

        const mat = new THREE.ShaderMaterial({
          vertexShader: filamentMatVertex,
          fragmentShader: filamentMatFragment,
          uniforms: {
            uTime: { value: 0.0 },
            uColorBase: { value: baseCol },
            uColorPulse: { value: pulseCol },
            uSpeed: { value: 0.8 + (i % 4) * 0.25 },
          },
          transparent: true,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        });

        const mesh = new THREE.Mesh(tubeGeom, mat);
        mesh.rotation.x = Math.random() * Math.PI;
        mesh.rotation.y = Math.random() * Math.PI;
        scene.add(mesh);
        filamentMeshes.push(mesh);
      }
    }

    try {
      createPlasmaFilaments();
    } catch (filErr) {
      console.warn("[QuantumUniverse] Filaments fallback notice:", filErr);
    }

    // ── Layer 4: GPU-Animated Orbital Quantum Particle Swarm ────────────────
    const particleCount = CONFIG.particleCount;
    const particleGeometry = new THREE.BufferGeometry();

    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const orbitParams = new Float32Array(particleCount * 4); // [radius, speed, tilt, phase]
    const sizes = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      // Stratified orbital distribution (dense near core, tapering out to accretion disc)
      const u = Math.random();
      const radius = 2.8 + Math.pow(u, 1.8) * 11.5;
      const angle = Math.random() * Math.PI * 2;
      const speed = (0.35 + 1.0 / (radius * 0.35)) * (Math.random() < 0.12 ? -1 : 1) * 0.55;
      const tilt = (Math.random() - 0.5) * 1.2;
      const phase = Math.random() * Math.PI * 2;

      // Base coordinate
      positions[i * 3 + 0] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = (Math.random() - 0.5) * (radius * 0.45);
      positions[i * 3 + 2] = Math.sin(angle) * radius;

      orbitParams[i * 4 + 0] = radius;
      orbitParams[i * 4 + 1] = speed;
      orbitParams[i * 4 + 2] = tilt;
      orbitParams[i * 4 + 3] = phase;

      // Palette blending
      const colorChoice = Math.random();
      if (colorChoice < 0.46) {
        // Cyan
        colors[i * 3 + 0] = PALETTE.cyan[0];
        colors[i * 3 + 1] = PALETTE.cyan[1];
        colors[i * 3 + 2] = PALETTE.cyan[2];
      } else if (colorChoice < 0.8) {
        // Ultraviolet
        colors[i * 3 + 0] = PALETTE.purple[0];
        colors[i * 3 + 1] = PALETTE.purple[1];
        colors[i * 3 + 2] = PALETTE.purple[2];
      } else if (colorChoice < 0.94) {
        // Magenta
        colors[i * 3 + 0] = PALETTE.magenta[0];
        colors[i * 3 + 1] = PALETTE.magenta[1];
        colors[i * 3 + 2] = PALETTE.magenta[2];
      } else {
        // White-gold energy spark
        colors[i * 3 + 0] = PALETTE.whiteGold[0];
        colors[i * 3 + 1] = PALETTE.whiteGold[1];
        colors[i * 3 + 2] = PALETTE.whiteGold[2];
      }

      sizes[i] = 1.2 + Math.random() * 2.8;
    }

    particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    particleGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    particleGeometry.setAttribute("aOrbit", new THREE.BufferAttribute(orbitParams, 4));
    particleGeometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));

    const particleVertexShader = `
      ${GLSL_SIMPLEX_NOISE}
      uniform float uTime;
      uniform vec2 uMouse;
      uniform float uShockwave;
      attribute vec4 aOrbit; // [radius, speed, tilt, phase]
      attribute vec3 color;
      attribute float aSize;
      varying vec3 vColor;
      varying float vDist;
      varying float vCoc;

      void main() {
        vColor = color;

        float radius = aOrbit.x;
        float speed  = aOrbit.y;
        float tilt   = aOrbit.z;
        float phase  = aOrbit.w;

        // Orbital physics: Angle evolves over time
        float currentAngle = phase + uTime * speed * 0.45;

        // Turbulence via 3D Simplex curl-like vector field
        vec3 seedPos = vec3(cos(currentAngle) * radius, sin(currentAngle) * radius * 0.3, sin(currentAngle) * radius);
        float noiseY = snoise(seedPos * 0.28 + vec3(0.0, uTime * 0.15, 0.0)) * 1.2;
        float noiseR = snoise(seedPos * 0.35 + vec3(uTime * 0.1, 0.0, 0.0)) * 0.8;

        float dynamicR = radius + noiseR;

        // Coordinates with relativistic inclination
        vec3 p = vec3(
          cos(currentAngle) * dynamicR,
          sin(currentAngle) * dynamicR * tilt * 0.5 + noiseY,
          sin(currentAngle) * dynamicR * cos(tilt * 0.4)
        );

        // Interactive mouse gravitational pull
        vec3 mouseWorld = vec3(uMouse.x * 9.0, uMouse.y * 6.0, 0.0);
        float distToMouse = length(p - mouseWorld);
        if (distToMouse < 6.5) {
          float pull = (1.0 - distToMouse / 6.5) * 1.2;
          p += normalize(mouseWorld - p) * pull;
        }

        // Interactive shockwave radial impulse
        if (uShockwave >= 0.0 && uShockwave < 2.5) {
          float waveFront = uShockwave * 12.0;
          float waveDist = length(p);
          float ripple = exp(-pow(waveDist - waveFront, 2.0) / 2.2);
          p += normalize(p) * (ripple * 0.95);
        }

        vDist = length(p);

        vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mvPosition;

        // Cinematic Depth of Field: Circle of Confusion (CoC)
        float focalDist = abs(p.z);
        float coc = clamp(focalDist * 0.07, 0.0, 2.2);
        vCoc = coc;

        // Perspective size attenuation with subtle breathing + bokeh expansion
        gl_PointSize = (aSize * (240.0 / -mvPosition.z)) * (1.0 + coc * 0.5) * (1.0 + 0.22 * sin(uTime * 2.0 + phase));
      }
    `;

    const particleFragmentShader = `
      varying vec3 vColor;
      varying float vDist;
      varying float vCoc;

      void main() {
        // High-precision Gaussian particle sprite with optical bokeh defocusing
        vec2 coord = gl_PointCoord - vec2(0.5);
        float distSq = dot(coord, coord);
        if (distSq > 0.25) discard;

        // Adaptive sharpness based on depth-of-field circle of confusion
        float sharpness = mix(18.0, 7.0, clamp(vCoc / 2.0, 0.0, 1.0));
        float alpha = exp(-distSq * sharpness);

        // Bokeh disc rim enhancement
        if (vCoc > 0.75) {
          float rim = smoothstep(0.14, 0.24, distSq);
          alpha = mix(alpha, rim * 0.4, 0.32);
        }

        // Core brightening: center glows white-hot
        vec3 finalColor = mix(vColor, vec3(1.0, 1.0, 1.0), pow(alpha, 3.5) * 0.75);

        gl_FragColor = vec4(finalColor, alpha * 0.94);
      }
    `;

    const particleMaterial = new THREE.ShaderMaterial({
      vertexShader: particleVertexShader,
      fragmentShader: particleFragmentShader,
      uniforms: {
        uTime: { value: 0.0 },
        uMouse: { value: new THREE.Vector2(0, 0) },
        uShockwave: { value: 999.0 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    particlePoints = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particlePoints);

    // ── Layer 5: Deep Cosmic Dust & Spatial Depth Field ──────────────────────
    const dustGeometry = new THREE.BufferGeometry();
    const dustCount = CONFIG.dustCount;
    const dustPositions = new Float32Array(dustCount * 3);
    const dustColors = new Float32Array(dustCount * 3);
    const dustSizes = new Float32Array(dustCount);

    for (let i = 0; i < dustCount; i++) {
      dustPositions[i * 3 + 0] = (Math.random() - 0.5) * 62;
      dustPositions[i * 3 + 1] = (Math.random() - 0.5) * 40;
      dustPositions[i * 3 + 2] = (Math.random() - 0.5) * 52 - 8;

      const isCyanDust = Math.random() < 0.6;
      dustColors[i * 3 + 0] = isCyanDust ? 0.0 : 0.45;
      dustColors[i * 3 + 1] = isCyanDust ? 0.8 : 0.25;
      dustColors[i * 3 + 2] = isCyanDust ? 1.0 : 0.95;

      dustSizes[i] = 0.8 + Math.random() * 1.6;
    }

    dustGeometry.setAttribute("position", new THREE.BufferAttribute(dustPositions, 3));
    dustGeometry.setAttribute("color", new THREE.BufferAttribute(dustColors, 3));
    dustGeometry.setAttribute("aSize", new THREE.BufferAttribute(dustSizes, 1));

    const dustVertexShader = `
      uniform float uTime;
      attribute vec3 color;
      attribute float aSize;
      varying vec3 vColor;

      void main() {
        vColor = color;
        vec3 p = position;

        // Subtle cosmic drifting
        p.y += sin(uTime * 0.15 + p.x * 0.08) * 0.8;
        p.x += cos(uTime * 0.12 + p.z * 0.08) * 0.8;

        vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        gl_PointSize = aSize * (150.0 / -mvPosition.z);
      }
    `;

    const dustFragmentShader = `
      varying vec3 vColor;

      void main() {
        vec2 coord = gl_PointCoord - vec2(0.5);
        float dist = length(coord);
        if (dist > 0.5) discard;
        float alpha = pow(1.0 - dist * 2.0, 2.0) * 0.45;
        gl_FragColor = vec4(vColor, alpha);
      }
    `;

    const dustMaterial = new THREE.ShaderMaterial({
      vertexShader: dustVertexShader,
      fragmentShader: dustFragmentShader,
      uniforms: {
        uTime: { value: 0.0 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    dustPoints = new THREE.Points(dustGeometry, dustMaterial);
    scene.add(dustPoints);

    // ── Layer 6: Volumetric Light Rays & Energy Corona Billboard ─────────────
    const coronaVertexShader = `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `;

    const coronaFragmentShader = `
      uniform float uTime;
      varying vec2 vUv;

      void main() {
        vec2 center = vUv - vec2(0.5);
        float dist = length(center);
        if (dist > 0.5) discard;

        float angle = atan(center.y, center.x);

        // Procedural volumetric god rays & shimmering corona
        float rays1 = sin(angle * 12.0 + uTime * 0.7) * 0.5 + 0.5;
        float rays2 = cos(angle * 7.0 - uTime * 0.5) * 0.5 + 0.5;
        float combinedRays = pow(rays1 * rays2, 1.5);

        // Radial falloff with pulsating breathing
        float pulse = 0.9 + 0.1 * sin(uTime * 1.5);
        float glow = pow(1.0 - (dist * 2.0), 2.2) * pulse;

        vec3 innerCyan = vec3(0.0, 0.95, 1.0);
        vec3 outerPurple = vec3(0.58, 0.22, 0.98);

        vec3 color = mix(outerPurple, innerCyan, glow);
        color += vec3(0.96, 0.25, 0.5) * combinedRays * glow * 0.6;

        float alpha = clamp(glow * (0.35 + combinedRays * 0.35), 0.0, 0.7);

        gl_FragColor = vec4(color, alpha);
      }
    `;

    const coronaMaterial = new THREE.ShaderMaterial({
      vertexShader: coronaVertexShader,
      fragmentShader: coronaFragmentShader,
      uniforms: {
        uTime: { value: 0.0 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const coronaGeom = new THREE.PlaneGeometry(16, 16);
    coronaMesh = new THREE.Mesh(coronaGeom, coronaMaterial);
    coronaMesh.position.set(0, 0, -2.5);
    scene.add(coronaMesh);

    // ── Layer 6.5: 3D Volumetric Light Shafts ───────────────────────────────
    const rayVertexShader = `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `;

    const rayFragmentShader = `
      uniform float uTime;
      varying vec2 vUv;

      void main() {
        float dist = abs(vUv.y - 0.5) * 2.0;
        float lateral = sin(vUv.x * 3.14159);

        float rayNoise = sin(vUv.x * 16.0 + uTime * 0.7) * cos(vUv.x * 10.0 - uTime * 0.4);
        rayNoise = pow(rayNoise * 0.5 + 0.5, 2.0);

        float intensity = pow(1.0 - dist, 2.2) * lateral * (0.3 + 0.7 * rayNoise);
        vec3 col = mix(vec3(0.0, 0.94, 1.0), vec3(0.62, 0.24, 0.98), dist);

        gl_FragColor = vec4(col, intensity * 0.22);
      }
    `;

    for (let r = 0; r < 4; r++) {
      const rayMat = new THREE.ShaderMaterial({
        vertexShader: rayVertexShader,
        fragmentShader: rayFragmentShader,
        uniforms: { uTime: { value: 0.0 } },
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      const rayPlane = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), rayMat);
      rayPlane.rotation.z = (r / 4) * Math.PI;
      scene.add(rayPlane);
      godRayMeshes.push(rayPlane);
    }

    // ── Interactive Cursor & Camera Parallax Events ──────────────────────────
    function onMouseMove(e) {
      mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
    }

    function onTouchMove(e) {
      if (e.touches && e.touches.length > 0) {
        mouse.targetX = (e.touches[0].clientX / window.innerWidth) * 2 - 1;
        mouse.targetY = -(e.touches[0].clientY / window.innerHeight) * 2 + 1;
      }
    }

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });

    // Optional Gyroscope for Mobile Devices
    if (window.DeviceOrientationEvent && isMobile) {
      window.addEventListener(
        "deviceorientation",
        (e) => {
          if (e.gamma !== null && e.beta !== null) {
            mouse.targetX = Math.max(-1, Math.min(1, e.gamma / 30));
            mouse.targetY = Math.max(-1, Math.min(1, (e.beta - 45) / 30));
          }
        },
        { passive: true }
      );
    }

    // ── Window Resize Handler ──────────────────────────────────────────────
    function onWindowResize() {
      const width = window.innerWidth;
      const height = window.innerHeight;

      camera.aspect = width / height;
      camera.updateProjectionMatrix();

      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, CONFIG.maxDPR));
    }

    window.addEventListener("resize", onWindowResize);

    // ── Tab Visibility Listener (0% CPU/GPU when hidden) ───────────────────
    document.addEventListener("visibilitychange", () => {
      isVisible = !document.hidden;
      if (isVisible && !animationFrameId) {
        clock.start();
        animate();
      }
    });

    // ── Main 60fps Animation Loop ──────────────────────────────────────────
    function animate() {
      if (!isVisible) {
        animationFrameId = null;
        return;
      }

      animationFrameId = requestAnimationFrame(animate);

      const delta = Math.min(clock.getDelta(), 0.1);
      const elapsedTime = clock.getElapsedTime() * CONFIG.speedMultiplier;

      // Shockwave timing
      let shockwaveTime = clock.getElapsedTime() - shockwaveStartTime;
      if (shockwaveTime > 3.0) shockwaveTime = 999.0;

      // 1. Damped Mouse Physics with Smooth Inertia (Lerp)
      const lerpSpeed = isMobile ? 0.03 : 0.045;
      mouse.x += (mouse.targetX - mouse.x) * lerpSpeed;
      mouse.y += (mouse.targetY - mouse.y) * lerpSpeed;

      // Camera Parallax: Smoothly glide around center
      camera.position.x = mouse.x * (CONFIG.parallaxStrength * 2.4);
      camera.position.y = mouse.y * (CONFIG.parallaxStrength * 1.8);
      camera.position.z = 18.5 - Math.abs(mouse.x * mouse.y) * 1.5;
      camera.lookAt(0, 0, 0);

      // 2. Quantum Core Rotations & Pulsations
      if (coreMesh) {
        coreMesh.rotation.y = elapsedTime * 0.18;
        coreMesh.rotation.x = Math.sin(elapsedTime * 0.12) * 0.15;
        coreMesh.rotation.z = Math.cos(elapsedTime * 0.1) * 0.1;
        coreMesh.material.uniforms.uTime.value = elapsedTime;
        coreMesh.material.uniforms.uMouse.value.set(mouse.x, mouse.y);
        coreMesh.material.uniforms.uShockwave.value = shockwaveTime;
      }

      if (outerShellMesh) {
        outerShellMesh.rotation.y = -elapsedTime * 0.14;
        outerShellMesh.rotation.z = Math.sin(elapsedTime * 0.16) * 0.2;
        outerShellMesh.material.uniforms.uTime.value = elapsedTime;
      }

      // 2.5. Accretion Disk Rotation
      if (accretionDiskMesh) {
        accretionDiskMesh.rotation.z = Math.PI * 0.15 + elapsedTime * 0.06;
        accretionDiskMesh.material.uniforms.uTime.value = elapsedTime;
      }

      // 3. Volumetric Corona Pulse
      if (coronaMesh) {
        coronaMesh.material.uniforms.uTime.value = elapsedTime;
        coronaMesh.lookAt(camera.position);
      }

      // 3.5. Volumetric Light Rays
      for (let r = 0; r < godRayMeshes.length; r++) {
        godRayMeshes[r].material.uniforms.uTime.value = elapsedTime;
        godRayMeshes[r].rotation.z += delta * 0.02 * (r % 2 === 0 ? 1 : -1);
      }

      // 4. Plasma Filaments Rotations & Pulse Propagation
      for (let i = 0; i < filamentMeshes.length; i++) {
        const mesh = filamentMeshes[i];
        const dir = i % 2 === 0 ? 1 : -1;
        mesh.rotation.y += delta * 0.08 * dir;
        mesh.rotation.x += delta * 0.05 * dir;
        mesh.material.uniforms.uTime.value = elapsedTime;
      }

      // 5. GPU Particles Swarm Update
      if (particlePoints) {
        particlePoints.rotation.y = elapsedTime * 0.05;
        particlePoints.material.uniforms.uTime.value = elapsedTime;
        particlePoints.material.uniforms.uMouse.value.set(mouse.x, mouse.y);
        particlePoints.material.uniforms.uShockwave.value = shockwaveTime;
      }

      // 6. Cosmic Dust Drift
      if (dustPoints) {
        dustPoints.rotation.y = -elapsedTime * 0.02;
        dustPoints.material.uniforms.uTime.value = elapsedTime;
      }

      renderer.render(scene, camera);
    }

    animate();
    window.QUANTUM_UNIVERSE_ACTIVE = true;
    console.info("⚡ [QuantumUniverse] Ultra-Premium 3D Quantum Energy Universe active.");
  }

  // ── Auto-bootstrap on DOMContentLoaded ───────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initQuantumUniverse);
  } else {
    initQuantumUniverse();
  }

  // Expose global handles
  window.initQuantumUniverse = initQuantumUniverse;
  window.triggerFallback = triggerFallback;
})();
