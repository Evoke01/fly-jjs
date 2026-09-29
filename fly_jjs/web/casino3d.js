// The casino's 3D scenes: the tin robot across the card table, the slot machine, and the
// racetrack. three.js with physically based materials, soft shadows and image lighting.
// Every model is built here from simple shapes; nothing is downloaded.
import * as THREE from "three";
import { RoomEnvironment } from "./vendor/RoomEnvironment.js";
import { RoundedBoxGeometry } from "./vendor/RoundedBoxGeometry.js";

const TAU = Math.PI * 2;
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (t) => t * t * (3 - 2 * t);

// ------------------------------------------------------------------ materials and helpers
const paint = (color, o = {}) => new THREE.MeshPhysicalMaterial({ color, metalness: 0.3, roughness: 0.34, clearcoat: 0.7,
  clearcoatRoughness: 0.22, ...o });
const matte = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0, ...o });
const CHROME = new THREE.MeshStandardMaterial({ color: 0xd8dde2, metalness: 1, roughness: 0.14 });
const BRASS = new THREE.MeshStandardMaterial({ color: 0xc19a4b, metalness: 1, roughness: 0.28 });
const DARK = new THREE.MeshStandardMaterial({ color: 0x1b1c1f, metalness: 0.4, roughness: 0.5 });

function canvasTexture(w, h, draw, { repeat = null, srgb = true } = {}) {
  const cv = document.createElement("canvas");
  cv.width = w; cv.height = h;
  draw(cv.getContext("2d"), w, h);
  const tex = new THREE.CanvasTexture(cv);
  if (srgb) tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  if (repeat) { tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(repeat[0], repeat[1]); }
  return tex;
}
function noise(ctx, w, h, base, spread, n = 9000, size = 2) {
  ctx.fillStyle = base; ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < n; i++) {
    const v = (Math.random() - 0.5) * spread;
    ctx.fillStyle = `rgba(${v > 0 ? 255 : 0},${v > 0 ? 255 : 0},${v > 0 ? 255 : 0},${Math.abs(v)})`;
    ctx.fillRect(Math.random() * w, Math.random() * h, size, size);
  }
}
function shadows(obj, cast = true, receive = true) {
  obj.traverse((o) => { if (o.isMesh) { o.castShadow = cast; o.receiveShadow = receive; } });
  return obj;
}
function mesh(geo, material, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geo, material);
  m.position.set(x, y, z);
  return m;
}
function ellipsoid(rx, ry, rz, material, seg = 28) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(1, seg, Math.round(seg * 0.7)), material);
  m.scale.set(rx, ry, rz);
  return m;
}
// A tube along a curve in the x-y plane whose radius changes along it, flattened sideways
// (z) by `flat`: necks, heads, legs, tails, arms.
function taper(points, radii, { flat = 1, segments = 28, radial = 18, caps = true } = {}) {
  const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(p[0], p[1], p[2] || 0)));
  const pos = [], idx = [];
  const side = new THREE.Vector3(0, 0, 1);
  const radiusAt = (u) => {
    const f = u * (radii.length - 1), i = Math.min(Math.floor(f), radii.length - 2);
    return lerp(radii[i], radii[i + 1], smooth(f - i));
  };
  for (let i = 0; i <= segments; i++) {
    const u = i / segments, p = curve.getPointAt(u), t = curve.getTangentAt(u);
    const n = new THREE.Vector3().crossVectors(side, t).normalize();
    const b = new THREE.Vector3().crossVectors(t, n).normalize();
    const r = radiusAt(u);
    for (let j = 0; j <= radial; j++) {
      const a = (j / radial) * TAU, c = Math.cos(a) * r, s = Math.sin(a) * r * flat;
      pos.push(p.x + n.x * c + b.x * s, p.y + n.y * c + b.y * s, p.z + n.z * c + b.z * s);
    }
  }
  for (let i = 0; i < segments; i++) {
    for (let j = 0; j < radial; j++) {
      const a = i * (radial + 1) + j, b = a + radial + 1;
      idx.push(a, b, a + 1, b, b + 1, a + 1);
    }
  }
  if (caps) {
    for (const end of [0, segments]) {
      const u = end / segments, p = curve.getPointAt(u), centre = pos.length / 3;
      pos.push(p.x, p.y, p.z);
      for (let j = 0; j < radial; j++) {
        const a = end * (radial + 1) + j;
        if (end === 0) idx.push(centre, a + 1, a); else idx.push(centre, a, a + 1);
      }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}
function roundedRect(w, h, r, path = new THREE.Shape(), cx = 0, cy = 0) {
  const x = cx - w / 2, y = cy - h / 2;
  path.moveTo(x + r, y);
  path.lineTo(x + w - r, y); path.quadraticCurveTo(x + w, y, x + w, y + r);
  path.lineTo(x + w, y + h - r); path.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  path.lineTo(x + r, y + h); path.quadraticCurveTo(x, y + h, x, y + h - r);
  path.lineTo(x, y + r); path.quadraticCurveTo(x, y, x + r, y);
  return path;
}
function gradientSky(top, bottom) {
  return canvasTexture(8, 512, (ctx, w, h) => {
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, top); g.addColorStop(1, bottom);
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  });
}
function softDot() {
  return canvasTexture(64, 64, (ctx) => {
    const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, 64, 64);
  });
}
// Free what a model removed from its scene holds on the GPU (the shared metals stay).
const SHARED = new Set([CHROME, BRASS, DARK]);
function dispose(root) {
  root.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    for (const m of o.material ? [].concat(o.material) : []) {
      if (SHARED.has(m)) continue;
      if (m.map) m.map.dispose();
      m.dispose();
    }
  });
}
function keyLight(scene, color, intensity, pos, size = 6, mapSize = 2048) {
  const light = new THREE.DirectionalLight(color, intensity);
  light.position.set(...pos);
  light.castShadow = true;
  light.shadow.mapSize.set(mapSize, mapSize);
  Object.assign(light.shadow.camera, { left: -size, right: size, top: size, bottom: -size, near: 0.5, far: 80 });
  light.shadow.bias = -0.0004;
  light.shadow.normalBias = 0.02;
  light.shadow.radius = 4;
  scene.add(light, light.target);
  return light;
}

// ------------------------------------------------------------------ the tin robot
const ROBOT_PAINT = {
  rookie: { body: 0xb8392f, trim: 0xefe2c6, head: 0x9ca8b0, iris: 0xe8b53a },
  pro: { body: 0x2f5a4b, trim: 0xe6d6a8, head: 0xb49a5c, iris: 0x7fd0a0 },
  random: { body: 0xd9a521, trim: 0xf3ead2, head: 0x6f9aa8, iris: 0xe0503c },
};

function dialFace() {
  return canvasTexture(256, 256, (ctx, w) => {
    ctx.fillStyle = "#f3ecd8"; ctx.beginPath(); ctx.arc(w / 2, w / 2, w / 2, 0, TAU); ctx.fill();
    ctx.strokeStyle = "#2a2a2a"; ctx.lineWidth = 6;
    for (let i = 0; i <= 10; i++) {
      const a = Math.PI * (0.8 + 1.4 * i / 10);
      ctx.beginPath(); ctx.moveTo(w / 2 + Math.cos(a) * 96, w / 2 + Math.sin(a) * 96);
      ctx.lineTo(w / 2 + Math.cos(a) * (i % 5 ? 108 : 116), w / 2 + Math.sin(a) * (i % 5 ? 108 : 116)); ctx.stroke();
    }
    ctx.strokeStyle = "#b8392f"; ctx.lineWidth = 12;
    ctx.beginPath(); ctx.arc(w / 2, w / 2, 102, Math.PI * 1.9, Math.PI * 2.2); ctx.stroke();
  });
}

class Robot {
  constructor(level = "rookie") {
    const pal = ROBOT_PAINT[level] || ROBOT_PAINT.rookie;
    this.root = new THREE.Group();
    const body = paint(pal.body), trim = paint(pal.trim, { metalness: 0.1 }), head = paint(pal.head, { metalness: 0.6 });
    this.paints = { body, trim, head };
    this.torso = new THREE.Group();
    this.root.add(this.torso);
    this.torso.add(mesh(new RoundedBoxGeometry(0.78, 0.86, 0.56, 5, 0.09), body, 0, 0.95, 0));
    this.torso.add(mesh(new RoundedBoxGeometry(0.58, 0.44, 0.05, 4, 0.03), trim, 0, 1.04, 0.28));
    // two gauges on the chest; the needles show how it feels
    const face = new THREE.MeshStandardMaterial({ map: dialFace(), roughness: 0.4 });
    this.needles = [];
    for (const x of [-0.13, 0.13]) {
      const dial = new THREE.Group();
      dial.position.set(x, 1.08, 0.31);
      const rim = mesh(new THREE.TorusGeometry(0.085, 0.012, 12, 40), CHROME);
      const disc = mesh(new THREE.CircleGeometry(0.085, 40), face, 0, 0, 0.002);
      const needle = new THREE.Group();
      needle.add(mesh(new THREE.BoxGeometry(0.008, 0.07, 0.004), DARK, 0, 0.032, 0.006));
      dial.add(rim, disc, needle);
      this.torso.add(dial);
      this.needles.push(needle);
    }
    this.torso.add(mesh(new THREE.BoxGeometry(0.16, 0.025, 0.02), DARK, 0, 0.9, 0.305));      // the coin slot
    const rivet = new THREE.SphereGeometry(0.013, 10, 8);
    for (let i = 0; i < 9; i++) for (const y of [0.83, 1.25]) this.torso.add(mesh(rivet, CHROME, -0.26 + i * 0.065, y, 0.305));
    for (const x of [-0.44, 0.44]) this.torso.add(mesh(new THREE.SphereGeometry(0.1, 24, 18), CHROME, x, 1.26, 0));
    // the wind-up key on its back
    this.key = new THREE.Group();
    this.key.position.set(0, 1.0, -0.3);
    this.key.add(mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.14, 12).rotateX(Math.PI / 2), BRASS, 0, 0, -0.06));
    for (const x of [-0.075, 0.075]) this.key.add(mesh(new THREE.TorusGeometry(0.07, 0.022, 12, 28), BRASS, x, 0, -0.14));
    this.torso.add(this.key);
    // arms: accordion hoses ending in pincers
    this.arms = [-1, 1].map((side) => {
      const rings = [];
      for (let i = 0; i < 9; i++) {
        const r = mesh(new THREE.TorusGeometry(0.052, 0.02, 10, 22), i % 2 ? CHROME : DARK);
        this.torso.add(r); rings.push(r);
      }
      const hand = new THREE.Group();
      hand.add(mesh(new THREE.CylinderGeometry(0.045, 0.05, 0.06, 18), CHROME));
      for (const s of [-1, 1]) {
        const claw = mesh(new THREE.TorusGeometry(0.045, 0.014, 10, 16, Math.PI), body, s * 0.03, -0.06, 0);
        claw.rotation.set(0, Math.PI / 2, s > 0 ? -0.5 : Math.PI + 0.5);
        hand.add(claw);
      }
      this.torso.add(hand);
      return { side, rings, hand, target: new THREE.Vector3(side * 0.33, 0.95, 0.34), now: new THREE.Vector3(side * 0.33, 0.95, 0.34) };
    });
    // the head, on a neck that hides a spring
    this.neck = mesh(new THREE.CylinderGeometry(0.075, 0.09, 0.1, 20), DARK, 0, 1.43, 0);
    this.torso.add(this.neck);
    const coil = [];
    for (let i = 0; i <= 120; i++) { const a = i / 120; coil.push(new THREE.Vector3(Math.cos(a * TAU * 6) * 0.07, a, Math.sin(a * TAU * 6) * 0.07)); }
    this.spring = mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(coil), 240, 0.012, 8), CHROME, 0, 1.45, 0);
    this.spring.scale.y = 0.001;
    this.torso.add(this.spring);
    this.head = new THREE.Group();
    this.head.position.set(0, 1.47, 0);
    this.torso.add(this.head);
    this.head.add(mesh(new RoundedBoxGeometry(0.6, 0.46, 0.48, 5, 0.08), head, 0, 0.23, 0));
    this.head.add(mesh(new RoundedBoxGeometry(0.46, 0.3, 0.03, 3, 0.02), trim, 0, 0.22, 0.24));
    const glass = new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 0, roughness: 0.05, transmission: 0, transparent: true,
      opacity: 0.28, clearcoat: 1, clearcoatRoughness: 0.03, depthWrite: false });
    this.irises = [];
    for (const x of [-0.12, 0.12]) {
      const eye = new THREE.Group();
      eye.position.set(x, 0.28, 0.255);
      eye.add(mesh(new THREE.TorusGeometry(0.068, 0.014, 12, 36), CHROME));
      const iris = mesh(new THREE.CircleGeometry(0.058, 36), new THREE.MeshStandardMaterial({ color: pal.iris, roughness: 0.45 }), 0, 0, 0.001);
      const pupil = mesh(new THREE.CircleGeometry(0.026, 28), DARK, 0, 0, 0.003);
      const dome = mesh(new THREE.SphereGeometry(0.062, 28, 14, 0, TAU, 0, Math.PI / 2).rotateX(Math.PI / 2), glass, 0, 0, 0.002);
      eye.add(iris, pupil, dome);
      this.head.add(eye);
      this.irises.push({ eye, iris, pupil });
    }
    this.head.add(mesh(new THREE.BoxGeometry(0.28, 0.07, 0.02), DARK, 0, 0.12, 0.25));
    for (let i = 0; i < 6; i++) this.head.add(mesh(new THREE.BoxGeometry(0.012, 0.066, 0.012), CHROME, -0.1 + i * 0.04, 0.12, 0.262));
    for (const x of [-0.31, 0.31]) {
      const ear = mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.05, 28).rotateZ(Math.PI / 2), CHROME, x, 0.25, 0);
      this.head.add(ear, mesh(new THREE.SphereGeometry(0.022, 12, 10), BRASS, x * 1.1, 0.25, 0));
    }
    this.head.add(mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.2, 10), CHROME, 0, 0.56, 0));
    this.head.add(mesh(new THREE.SphereGeometry(0.035, 16, 12), paint(0xd23b2e), 0, 0.67, 0));
    if (level === "pro") {       // a card sharp's green visor
      const visor = new THREE.MeshPhysicalMaterial({ color: 0x1f8a55, transparent: true, opacity: 0.72, roughness: 0.25, clearcoat: 1 });
      const brim = mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.02, 40, 1, false, -0.9, 1.8), visor, 0, 0.44, 0.05);
      brim.rotation.x = 0.18;
      this.head.add(brim, mesh(new THREE.CylinderGeometry(0.31, 0.31, 0.06, 40, 1, true), visor, 0, 0.44, 0));
    }
    // smoke and sparks for when it gets shot
    this.puffs = [];
    const dot = softDot();
    for (let i = 0; i < 14; i++) {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, color: 0x777777, transparent: true, opacity: 0, depthWrite: false }));
      this.root.add(s); this.puffs.push({ s, v: new THREE.Vector3(), life: 0 });
    }
    shadows(this.root);
    this.mood = "idle";
    this.moodAt = 0;
    this.broken = 0;
    this.popped = 0;
  }
  set(mood, t) {
    if (mood === this.mood) return;
    this.mood = mood; this.moodAt = t;
    if (mood === "shot") {
      this.popped = 1;
      for (const p of this.puffs) {
        p.s.position.set((Math.random() - 0.5) * 0.3, 1.6 + Math.random() * 0.2, (Math.random() - 0.5) * 0.3);
        p.v.set((Math.random() - 0.5) * 0.6, 0.5 + Math.random() * 0.7, (Math.random() - 0.5) * 0.6);
        p.life = 1;
      }
    }
    if (mood === "idle") { this.popped = 0; this.broken = 0; }
  }
  reset(t) {
    // a new game: back on its feet with its head on
    this.mood = "idle"; this.moodAt = t; this.popped = 0; this.broken = 0;
    for (const p of this.puffs) p.life = 0;
  }
  tick(dt, t) {
    const since = t - this.moodAt, m = this.mood;
    const breathe = Math.sin(t * 1.7) * 0.012;
    let lean = 0, turn = Math.sin(t * 0.5) * 0.12, nod = Math.sin(t * 0.9) * 0.04, bounce = 0, shake = 0, gauge = 0.2;
    for (const a of this.arms) a.target.set(a.side * 0.33, 0.95, 0.34);
    if (m === "think") { nod = 0.22 + Math.sin(t * 3) * 0.02; turn = Math.sin(t * 0.8) * 0.2; this.arms[1].target.set(0.26, 0.97 + Math.abs(Math.sin(t * 7)) * 0.05, 0.4); gauge = 0.5 + Math.sin(t * 4) * 0.1; }
    if (m === "bet") { const k = smooth(clamp(since / 0.5, 0, 1)); this.arms[1].target.set(0.18, 0.95, lerp(0.34, 0.62, k)); nod = 0.2; }
    if (m === "win") { const k = smooth(clamp(since / 0.35, 0, 1)); for (const a of this.arms) a.target.set(a.side * 0.52, lerp(0.95, 1.85, k), 0.1); bounce = Math.abs(Math.sin(since * 9)) * 0.05; nod = -0.2; gauge = 0.95; }
    if (m === "lose") { lean = 0.12 * smooth(clamp(since / 0.6, 0, 1)); nod = 0.35; turn = Math.sin(t * 0.7) * 0.25; gauge = 0.02; }
    if (m === "laugh") { bounce = Math.abs(Math.sin(since * 14)) * 0.035; nod = -0.35 + Math.sin(since * 14) * 0.08; gauge = 1; for (const a of this.arms) a.target.set(a.side * 0.3, 0.95, 0.42); }
    if (m === "aim") { shake = 0.018; for (const a of this.arms) a.target.set(a.side * 0.5, 1.9, 0.05); nod = -0.1; gauge = 1; }
    if (m === "shot" || m === "dead") {
      const k = smooth(clamp(since / 0.25, 0, 1));
      lean = -0.32 * k; gauge = 0; turn = 0.1;
      for (const a of this.arms) a.target.set(a.side * 0.62, 0.8, -0.05);
      this.broken = 1;
    }
    this.torso.rotation.x = lean + (shake ? (Math.random() - 0.5) * shake * 2 : 0);
    this.torso.position.set(shake ? (Math.random() - 0.5) * shake : 0, breathe + bounce, 0);
    // the head: on its neck, or up on the spring once shot
    const up = this.popped ? 0.32 + Math.sin(since * 11) * Math.exp(-since * 1.6) * 0.12 : 0;
    this.head.position.y = 1.47 + up;
    this.spring.scale.y = Math.max(0.001, up + 0.02 * this.popped);
    this.head.rotation.set(nod + (this.broken ? Math.sin(since * 7) * Math.exp(-since) * 0.4 : 0), turn, this.broken ? 0.35 : 0);
    for (const { pupil } of this.irises) pupil.scale.setScalar(this.broken ? 2.1 : m === "aim" ? 0.5 : 1);
    for (const [i, n] of this.needles.entries()) n.rotation.z = lerp(n.rotation.z, (0.5 - gauge) * 2.2 + i * 0.1, 0.1);
    this.key.rotation.z += dt * (this.broken ? 0 : 1.2);
    for (const a of this.arms) {
      a.now.lerp(a.target, 1 - Math.exp(-dt * 8));
      const s = new THREE.Vector3(a.side * 0.44, 1.26, 0), e = a.now;
      const mid = new THREE.Vector3(a.side * 0.56, (s.y + e.y) / 2 - 0.12, (s.z + e.z) / 2 + 0.08);
      const curve = new THREE.QuadraticBezierCurve3(s, mid, e);
      a.rings.forEach((r, i) => {
        const u = (i + 0.5) / a.rings.length;
        r.position.copy(curve.getPoint(u));
        r.lookAt(r.position.clone().add(curve.getTangent(u)));
      });
      a.hand.position.copy(e);
      a.hand.lookAt(e.clone().add(curve.getTangent(1)));
      a.hand.rotateX(Math.PI / 2);
    }
    for (const p of this.puffs) {
      if (p.life <= 0) { p.s.material.opacity = 0; continue; }
      p.life -= dt * 0.45;
      p.s.position.addScaledVector(p.v, dt);
      p.v.multiplyScalar(1 - dt * 0.8);
      p.s.scale.setScalar(0.15 + (1 - p.life) * 0.6);
      p.s.material.opacity = Math.max(0, p.life) * 0.55;
    }
  }
}

function chipTextures(color) {
  const side = canvasTexture(256, 32, (ctx, w, h) => {
    ctx.fillStyle = color; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#f4efe4";
    for (let i = 0; i < 8; i++) ctx.fillRect(i * 32 + 8, 0, 12, h);
  });
  const top = canvasTexture(128, 128, (ctx, w) => {
    ctx.fillStyle = color; ctx.fillRect(0, 0, w, w);
    ctx.strokeStyle = "#f4efe4"; ctx.lineWidth = 7; ctx.setLineDash([12, 10]);
    ctx.beginPath(); ctx.arc(64, 64, 52, 0, TAU); ctx.stroke();
    ctx.setLineDash([]); ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(64, 64, 34, 0, TAU); ctx.stroke();
  });
  return [new THREE.MeshStandardMaterial({ map: side, roughness: 0.5 }), new THREE.MeshStandardMaterial({ map: top, roughness: 0.45 }),
    new THREE.MeshStandardMaterial({ map: top, roughness: 0.45 })];
}

class CardsScene {
  constructor(env) {
    const scene = this.scene = new THREE.Scene();
    scene.environment = env;
    scene.environmentIntensity = 0.55;
    scene.background = gradientSky("#1d1712", "#0a0908");
    scene.fog = new THREE.Fog(0x0b0908, 6, 14);
    this.camera = new THREE.PerspectiveCamera(36, 1, 0.1, 40);
    const lamp = new THREE.SpotLight(0xffd9a8, 60, 9, 0.62, 0.55, 1.6);
    lamp.position.set(0.2, 3.4, 0.6);
    lamp.target.position.set(0, 0.9, -0.2);
    lamp.castShadow = true;
    lamp.shadow.mapSize.set(2048, 2048);
    lamp.shadow.bias = -0.0003;
    lamp.shadow.radius = 5;
    scene.add(lamp, lamp.target, new THREE.HemisphereLight(0x8a7a66, 0x1a1410, 0.35));
    const rim = new THREE.DirectionalLight(0x9fb8ff, 0.9);
    rim.position.set(-2.5, 2.5, -3);
    scene.add(rim);
    // the shade over the table
    const shade = mesh(new THREE.CylinderGeometry(0.16, 0.5, 0.32, 40, 1, true), paint(0x1f4d36, { side: THREE.DoubleSide }), 0.2, 3.45, 0.6);
    scene.add(shade, mesh(new THREE.SphereGeometry(0.07, 16, 12), new THREE.MeshBasicMaterial({ color: 0xfff2d6 }), 0.2, 3.35, 0.6));
    // the table: green felt in a wooden rim
    const felt = new THREE.MeshStandardMaterial({ map: canvasTexture(512, 512, (ctx, w, h) => noise(ctx, w, h, "#1d5a39", 0.12, 26000, 1)), roughness: 0.95 });
    const table = mesh(new THREE.CylinderGeometry(1.35, 1.35, 0.06, 72), felt, 0, 0.87, 0);
    const wood = paint(0x5b3620, { metalness: 0, roughness: 0.4, clearcoat: 0.9 });
    const rimMesh = mesh(new THREE.TorusGeometry(1.36, 0.07, 18, 96), wood, 0, 0.9, 0);
    rimMesh.rotation.x = Math.PI / 2;
    const pedestal = mesh(new THREE.CylinderGeometry(0.12, 0.35, 0.84, 32), wood, 0, 0.42, 0);
    scene.add(shadows(table, false, true), shadows(rimMesh), shadows(pedestal));
    const floor = mesh(new THREE.CircleGeometry(12, 64), matte(0x2a1f19), 0, 0, 0);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);
    this.chipMats = { fly: chipTextures("#d88a1a"), bot: chipTextures("#2f6fb8") };
    this.chipGeo = new THREE.CylinderGeometry(0.075, 0.075, 0.02, 40);
    this.stacks = { fly: new THREE.Group(), bot: new THREE.Group() };
    this.stacks.fly.position.set(-0.32, 0.9, 0.62);
    this.stacks.bot.position.set(0.36, 0.9, -0.28);
    scene.add(this.stacks.fly, this.stacks.bot);
    this.counts = { fly: -1, bot: -1 };
    this.level = null;
    this.robot = null;
    this.setLevel("rookie");
  }
  setLevel(level) {
    if (level === this.level && this.robot) return;
    if (this.robot) { this.scene.remove(this.robot.root); dispose(this.robot.root); }
    this.level = level;
    this.robot = new Robot(level || "rookie");
    this.robot.root.position.set(0, 0, -0.95);
    this.scene.add(this.robot.root);
  }
  stack(who, n) {
    n = clamp(Math.round(n), 0, 40);
    if (n === this.counts[who]) return;
    this.counts[who] = n;
    const g = this.stacks[who];
    g.clear();
    for (let i = 0; i < n; i++) {
      const col = i % 10, level = Math.floor(i / 10);
      const c = mesh(this.chipGeo, this.chipMats[who], (level % 2) * 0.17 - (level > 1 ? 0.085 : 0), 0.012 + col * 0.021, (level > 1 ? 0.15 : 0));
      c.rotation.y = Math.random() * TAU;
      c.castShadow = true;
      g.add(c);
    }
  }
  update(c, t) {
    if (c.bot_level !== undefined) this.setLevel(c.bot_level || "rookie");
    if (c.number !== this.number) { this.number = c.number; this.robot.reset(t); }
    this.robot.root.visible = !!c.bot;
    if (c.fly) this.stack("fly", c.fly.chips || 0);
    if (c.bot) this.stack("bot", c.bot.chips || 0);
    const target = c.target || [], phase = c.phase, b = c.bot || {};
    let mood = "idle";
    if (b.shot) mood = phase === "shot" ? "shot" : "dead";
    else if (target.includes("bot") && phase === "aim") mood = "aim";
    else if (target.includes("fly") && ["shot", "dead"].includes(phase)) mood = "laugh";
    else if (phase === "think") mood = "think";
    else if (phase === "wait") mood = "bet";
    else if (phase === "reveal" && b.result) mood = b.result === "win" ? "win" : "lose";
    if (mood === "idle" && this.robot.mood === "dead") return;
    this.robot.set(mood, t);
  }
  tick(dt, t) {
    this.robot.tick(dt, t);
    const a = Math.sin(t * 0.13) * 0.35;
    this.camera.position.set(Math.sin(a) * 2.5, 1.62 + Math.sin(t * 0.21) * 0.05, Math.cos(a) * 2.5);
    this.camera.lookAt(0, 1.18, -0.55);
  }
}

// ------------------------------------------------------------------ the slot machine
const SYMBOLS = ["SEVEN", "BAR", "BELL", "CHERRY", "LEMON"];
const STRIP_COUNTS = { SEVEN: 5, BAR: 5, BELL: 4, CHERRY: 4, LEMON: 8 };
function reelStrip(seed) {
  const strip = [];
  for (const s of SYMBOLS) for (let i = 0; i < STRIP_COUNTS[s]; i++) strip.push(s);
  let x = seed;
  for (let i = strip.length - 1; i > 0; i--) {         // a fixed shuffle per reel
    x = (x * 16807) % 2147483647;
    const j = x % (i + 1);
    [strip[i], strip[j]] = [strip[j], strip[i]];
  }
  return strip;
}
function drawSymbol(ctx, s, cx, cy, size) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineJoin = "round";
  if (s === "SEVEN") {
    ctx.font = `900 ${size * 1.05}px Georgia, 'Times New Roman', serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.lineWidth = size * 0.1; ctx.strokeStyle = "#d9a521"; ctx.strokeText("7", 0, size * 0.04);
    ctx.fillStyle = "#c8262c"; ctx.fillText("7", 0, size * 0.04);
  } else if (s === "BAR") {
    ctx.fillStyle = "#1b1b1f"; ctx.strokeStyle = "#d9a521"; ctx.lineWidth = size * 0.05;
    ctx.beginPath(); ctx.roundRect(-size * 0.62, -size * 0.28, size * 1.24, size * 0.56, size * 0.08); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#f4efe4"; ctx.font = `800 ${size * 0.42}px 'Arial Black', Arial, sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText("BAR", 0, size * 0.02);
  } else if (s === "BELL") {
    const g = ctx.createLinearGradient(-size * 0.4, 0, size * 0.4, 0);
    g.addColorStop(0, "#9c6d12"); g.addColorStop(0.45, "#f6cf4c"); g.addColorStop(1, "#a8791a");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(-size * 0.42, size * 0.28);
    ctx.bezierCurveTo(-size * 0.36, -size * 0.1, -size * 0.3, -size * 0.45, 0, -size * 0.45);
    ctx.bezierCurveTo(size * 0.3, -size * 0.45, size * 0.36, -size * 0.1, size * 0.42, size * 0.28);
    ctx.closePath(); ctx.fill();
    ctx.fillRect(-size * 0.48, size * 0.26, size * 0.96, size * 0.08);
    ctx.beginPath(); ctx.arc(0, size * 0.4, size * 0.08, 0, TAU); ctx.fill();
  } else if (s === "CHERRY") {
    ctx.strokeStyle = "#3f7a2a"; ctx.lineWidth = size * 0.06;
    ctx.beginPath(); ctx.moveTo(-size * 0.2, size * 0.05); ctx.quadraticCurveTo(-size * 0.05, -size * 0.35, size * 0.18, -size * 0.42); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(size * 0.2, size * 0.08); ctx.quadraticCurveTo(size * 0.2, -size * 0.25, size * 0.18, -size * 0.42); ctx.stroke();
    ctx.fillStyle = "#4e9a33"; ctx.beginPath(); ctx.ellipse(size * 0.32, -size * 0.38, size * 0.16, size * 0.07, -0.4, 0, TAU); ctx.fill();
    for (const [x, y] of [[-size * 0.22, size * 0.2], [size * 0.2, size * 0.24]]) {
      const g = ctx.createRadialGradient(x - size * 0.07, y - size * 0.07, size * 0.02, x, y, size * 0.2);
      g.addColorStop(0, "#ff6a5f"); g.addColorStop(1, "#8e1015");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, size * 0.19, 0, TAU); ctx.fill();
    }
  } else if (s === "LEMON") {
    const g = ctx.createRadialGradient(-size * 0.12, -size * 0.1, size * 0.05, 0, 0, size * 0.45);
    g.addColorStop(0, "#fff38a"); g.addColorStop(1, "#d8b313");
    ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(0, 0, size * 0.42, size * 0.29, -0.15, 0, TAU); ctx.fill();
    ctx.beginPath(); ctx.ellipse(size * 0.42, -size * 0.06, size * 0.07, size * 0.05, -0.15, 0, TAU); ctx.fill();
  }
  ctx.restore();
}
function reelTexture(strip) {
  const cell = 150, w = cell * strip.length, h = 300;
  return canvasTexture(w, h, (ctx) => {
    ctx.fillStyle = "#f6f1e3"; ctx.fillRect(0, 0, w, h);
    strip.forEach((s, i) => {
      // around the drum (the canvas's x) is up the screen, and across it (the canvas's
      // y) is to the right: draw each symbol turned a quarter clockwise
      ctx.save();
      ctx.translate(i * cell + cell / 2, h / 2);
      ctx.rotate(Math.PI / 2);
      drawSymbol(ctx, s, 0, 0, cell * 0.86);
      ctx.restore();
      ctx.fillStyle = "rgba(0,0,0,0.06)"; ctx.fillRect(i * cell, 0, 2, h);
    });
  });
}
function signTexture() {
  return canvasTexture(1024, 256, (ctx, w, h) => {
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, "#5a0e12"); g.addColorStop(1, "#2a0507");
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    ctx.font = "900 150px Georgia, 'Times New Roman', serif";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.lineWidth = 14; ctx.strokeStyle = "#7a4e0e"; ctx.strokeText("FLY  SLOTS", w / 2, h / 2 + 8);
    const t = ctx.createLinearGradient(0, 40, 0, 200);
    t.addColorStop(0, "#fff0b0"); t.addColorStop(0.5, "#f2c230"); t.addColorStop(1, "#b8841a");
    ctx.fillStyle = t; ctx.fillText("FLY  SLOTS", w / 2, h / 2 + 8);
  });
}
function carpet() {
  return canvasTexture(512, 512, (ctx, w) => {
    ctx.fillStyle = "#4a0f14"; ctx.fillRect(0, 0, w, w);
    for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) {
      const cx = x * 128 + 64 + (y % 2) * 64, cy = y * 128 + 64;
      ctx.strokeStyle = "#c19a4b"; ctx.lineWidth = 5;
      ctx.beginPath(); ctx.moveTo(cx, cy - 34); ctx.lineTo(cx + 34, cy); ctx.lineTo(cx, cy + 34); ctx.lineTo(cx - 34, cy); ctx.closePath(); ctx.stroke();
      ctx.fillStyle = "#1f3b5c"; ctx.beginPath(); ctx.arc(cx, cy, 12, 0, TAU); ctx.fill();
    }
  }, { repeat: [6, 6] });
}

class SlotsScene {
  constructor(env) {
    const scene = this.scene = new THREE.Scene();
    scene.environment = env;
    scene.environmentIntensity = 0.7;
    scene.background = gradientSky("#2a0d10", "#0b0506");
    scene.fog = new THREE.Fog(0x0b0506, 7, 18);
    this.camera = new THREE.PerspectiveCamera(34, 1, 0.1, 40);
    const key = keyLight(scene, 0xffe3c4, 2.4, [2.2, 4.5, 4.2], 3);
    key.target.position.set(0, 1.2, 0);
    scene.add(new THREE.HemisphereLight(0xffc9a0, 0x220808, 0.4));
    const rim = new THREE.DirectionalLight(0xff8a5a, 1.2);
    rim.position.set(-3, 2.5, -2.5);
    scene.add(rim);
    const floor = mesh(new THREE.PlaneGeometry(30, 30), new THREE.MeshStandardMaterial({ map: carpet(), roughness: 0.95 }));
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);
    const red = paint(0xa8231f), cream = paint(0xf1e4c2, { metalness: 0.15 }), black = paint(0x151414, { metalness: 0.2 });
    const m = this.machine = new THREE.Group();
    scene.add(m);
    m.add(mesh(new RoundedBoxGeometry(1.5, 0.22, 1.0, 4, 0.05), black, 0, 0.11, 0));
    m.add(mesh(new RoundedBoxGeometry(1.36, 1.66, 0.62, 6, 0.08), red, 0, 1.05, -0.2));          // the body, behind
    // the front, with a window cut in it for the reels
    const WIN = { w: 1.0, h: 0.46, y: 0.31 };
    const front = roundedRect(1.4, 1.7, 0.1);
    front.holes.push(roundedRect(WIN.w, WIN.h, 0.03, new THREE.Path(), 0, WIN.y));
    const panel = mesh(new THREE.ExtrudeGeometry(front, { depth: 0.28, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.03,
      bevelSegments: 4, curveSegments: 10 }), [red, paint(0x3a0c0b)], 0, 1.05, 0.12);
    m.add(panel);
    const bezel = roundedRect(WIN.w + 0.14, WIN.h + 0.14, 0.06);
    bezel.holes.push(roundedRect(WIN.w + 0.01, WIN.h + 0.01, 0.03, new THREE.Path()));
    m.add(mesh(new THREE.ExtrudeGeometry(bezel, { depth: 0.02, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.01, bevelSegments: 3 }),
      cream, 0, 1.05 + WIN.y, 0.43));
    m.add(mesh(new RoundedBoxGeometry(1.46, 0.6, 1.0, 6, 0.14), red, 0, 2.12, -0.02));
    const sign = mesh(new THREE.PlaneGeometry(1.2, 0.3), new THREE.MeshBasicMaterial({ map: signTexture(), toneMapped: false }), 0, 2.14, 0.505);
    m.add(sign);
    // chasing bulbs round the sign
    this.bulbs = [];
    const bulbGeo = new THREE.SphereGeometry(0.028, 14, 10);
    const path = [];
    for (let i = 0; i < 16; i++) path.push([-0.66 + i * 0.088, 2.38], [-0.66 + i * 0.088, 1.9]);
    for (let i = 1; i < 5; i++) path.push([-0.7, 1.9 + i * 0.096], [0.7, 1.9 + i * 0.096]);
    for (const [x, y] of path) {
      const b = mesh(bulbGeo, new THREE.MeshStandardMaterial({ color: 0x5a3a10, emissive: 0xffc84a, emissiveIntensity: 0.3 }), x, y, 0.5);
      m.add(b); this.bulbs.push(b);
    }
    // three reels behind the window
    this.reels = [0, 1, 2].map((i) => {
      const strip = reelStrip(7919 * (i + 3));
      const drum = mesh(new THREE.CylinderGeometry(0.55, 0.55, 0.3, 120, 1, false).rotateZ(Math.PI / 2),
        new THREE.MeshStandardMaterial({ map: reelTexture(strip), roughness: 0.62, color: 0xe8e2d4 }), -0.33 + i * 0.33, 1.05 + WIN.y, -0.15);
      m.add(drum);
      return { drum, strip, angle: 0, from: 0, to: 0, start: 0, stop: 0, spinning: false };
    });
    const glass = new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.04, transparent: true, opacity: 0.1, clearcoat: 1,
      depthWrite: false });
    m.add(mesh(new THREE.PlaneGeometry(WIN.w, WIN.h), glass, 0, 1.05 + WIN.y, 0.42));
    for (const x of [-0.165, 0.165]) m.add(mesh(new THREE.BoxGeometry(0.014, WIN.h, 0.03), CHROME, x, 1.05 + WIN.y, 0.4));
    m.add(mesh(new THREE.BoxGeometry(WIN.w, 0.01, 0.01), paint(0xd8262c, { emissive: 0xff2020, emissiveIntensity: 0.8 }), 0, 1.05 + WIN.y, 0.415));
    // the win meter, the tray, the lever
    this.meterTex = null;
    this.meter = mesh(new THREE.PlaneGeometry(0.62, 0.14), new THREE.MeshBasicMaterial({ color: 0xffffff }), 0, 0.98, 0.436);
    m.add(this.meter);
    this.setMeter("PULL THE LEVER");
    m.add(mesh(new RoundedBoxGeometry(0.9, 0.16, 0.3, 4, 0.05), CHROME, 0, 0.42, 0.52));
    m.add(mesh(new THREE.BoxGeometry(0.8, 0.08, 0.2), DARK, 0, 0.47, 0.56));
    this.lever = new THREE.Group();
    this.lever.position.set(0.8, 1.3, 0.1);
    this.lever.add(mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.8, 16), CHROME, 0, 0.4, 0));
    this.lever.add(mesh(new THREE.SphereGeometry(0.085, 28, 20), paint(0xd23b2e), 0, 0.82, 0));
    m.add(this.lever, mesh(new RoundedBoxGeometry(0.12, 0.26, 0.26, 3, 0.04), CHROME, 0.77, 1.3, 0.1));
    shadows(m);
    // coins for a win
    this.coinGeo = new THREE.CylinderGeometry(0.035, 0.035, 0.008, 24);
    this.coins = new THREE.InstancedMesh(this.coinGeo, BRASS, 160);
    this.coins.castShadow = true;
    this.coinState = [];
    this.coins.count = 0;
    scene.add(this.coins);
    this.spinId = null;
    this.lastPhase = "";
    this.flash = 0;
    this.pull = 0;
  }
  setMeter(text, hot = false) {
    const tex = canvasTexture(512, 116, (ctx, w, h) => {
      ctx.fillStyle = "#120b05"; ctx.fillRect(0, 0, w, h);
      ctx.font = "700 58px 'Courier New', monospace"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillStyle = hot ? "#ffd23f" : "#ff8a3a"; ctx.shadowColor = ctx.fillStyle; ctx.shadowBlur = 14;
      ctx.fillText(text, w / 2, h / 2 + 3);
    });
    if (this.meterTex) this.meterTex.dispose();
    this.meterTex = tex;
    this.meter.material.map = tex;
    this.meter.material.needsUpdate = true;
  }
  angleFor(reel, symbol, fromAngle) {
    // The stop that shows `symbol` in the window, at least two turns on from here. Stop i
    // is centred at (i + 0.5) / n of the way round the drum, and turning the drum by that
    // angle about x brings it round to face the window.
    const n = reel.strip.length, choices = [];
    reel.strip.forEach((s, i) => { if (s === symbol) choices.push(i); });
    const i = choices[Math.floor(Math.random() * choices.length)];
    let a = (i + 0.5) / n * TAU;
    while (a < fromAngle + TAU * 2) a += TAU;
    return a;
  }
  update(c, t) {
    const spin = c.spin;
    const id = spin ? `${c.number}:${spin.n}` : null;
    if (spin && spin.n && c.phase === "spin" && this.spinId !== id) {
      this.spinId = id;
      this.pull = t;
      this.reels.forEach((r, i) => {
        r.from = r.angle; r.to = this.angleFor(r, spin.reels[i], r.angle + TAU * (2 + i));
        r.start = t; r.stop = t + spin.stops[i]; r.spinning = true;
      });
      this.setMeter(`BET $${spin.bet}`);
      this.win = spin.win; this.name = spin.name;
    }
    if (c.phase !== this.lastPhase) {
      if (c.phase === "paid" && this.win > 0) { this.setMeter(`WIN $${this.win}`, true); this.burst(Math.min(160, 10 + this.win / 2)); this.flash = t; }
      if (c.phase === "jackpot") { this.setMeter("JACKPOT", true); this.burst(160); this.flash = t + 3; }
      if (c.phase === "walk") this.setMeter("GOODBYE");
      if (c.phase === "think" && this.lastPhase !== "think") this.setMeter(c.spin && c.spin.n ? "AGAIN?" : "PULL THE LEVER");
      this.lastPhase = c.phase;
    }
  }
  burst(n) {
    this.coinState = [];
    for (let i = 0; i < n; i++) {
      this.coinState.push({ p: new THREE.Vector3((Math.random() - 0.5) * 0.6, 0.48, 0.62), v: new THREE.Vector3((Math.random() - 0.5) * 1.6,
        1 + Math.random() * 2.2, 0.6 + Math.random() * 1.4), r: new THREE.Euler(Math.random() * 3, Math.random() * 3, 0),
        w: new THREE.Vector3(Math.random() * 8, Math.random() * 8, 0), delay: i * 0.012 });
    }
    this.coins.count = n;
  }
  tick(dt, t) {
    for (const r of this.reels) {
      if (r.spinning) {
        if (t >= r.stop) { r.angle = r.to; r.spinning = false; r.bounce = t; }
        else {
          const u = (t - r.start) / (r.stop - r.start), speed = 1 - Math.pow(1 - u, 3);
          r.angle = lerp(r.from, r.to, speed);
        }
      }
      const b = r.bounce ? Math.exp(-(t - r.bounce) * 9) * Math.sin((t - r.bounce) * 30) * 0.05 : 0;
      r.drum.rotation.x = r.angle + b;
    }
    const pulled = clamp((t - this.pull) / 0.25, 0, 2);
    this.lever.rotation.x = pulled < 1 ? smooth(pulled) * 1.1 : Math.max(0, 1.1 - (pulled - 1) * 1.5);
    const hot = t - this.flash < 3.5;
    this.bulbs.forEach((b, i) => {
      const on = hot ? (Math.floor(t * 10) + i) % 2 === 0 : (Math.floor(t * 4) + i) % 4 === 0;
      b.material.emissiveIntensity = on ? (hot ? 3 : 1.6) : 0.25;
    });
    const m = new THREE.Matrix4(), q = new THREE.Quaternion();
    this.coinState.forEach((c, i) => {
      if (c.delay > 0) { c.delay -= dt; m.makeScale(0.0001, 0.0001, 0.0001); this.coins.setMatrixAt(i, m); return; }
      c.v.y -= 9.8 * dt;
      c.p.addScaledVector(c.v, dt);
      if (c.p.y < 0.01) { c.p.y = 0.01; c.v.y *= -0.35; c.v.x *= 0.7; c.v.z *= 0.7; c.w.multiplyScalar(0.7); }
      c.r.x += c.w.x * dt; c.r.y += c.w.y * dt;
      q.setFromEuler(c.r);
      m.compose(c.p, q, new THREE.Vector3(1, 1, 1));
      this.coins.setMatrixAt(i, m);
    });
    this.coins.instanceMatrix.needsUpdate = true;
    const spinning = this.reels.some((r) => r.spinning);
    this.dolly = lerp(this.dolly || 4.7, spinning ? 3.9 : 4.7, 1 - Math.exp(-dt * 1.5));
    this.camera.position.set(Math.sin(t * 0.17) * 0.5, 1.4 + Math.sin(t * 0.23) * 0.03, this.dolly);
    this.camera.lookAt(0, 1.42, 0);
  }
}

// ------------------------------------------------------------------ the racetrack
const COATS = {
  bay: { coat: 0x6b3a1c, points: 0x1c1512, mane: 0x16110e },
  chestnut: { coat: 0x8f4a20, points: 0x8f4a20, mane: 0x7a3a18 },
  black: { coat: 0x1e1a18, points: 0x141110, mane: 0x0f0c0b },
  grey: { coat: 0xa9a8a2, points: 0x5c5a57, mane: 0x6f6d69 },
  "dark bay": { coat: 0x3d2416, points: 0x15100d, mane: 0x100c0a },
  palomino: { coat: 0xc79d58, points: 0xc79d58, mane: 0xefe3c2 },
};
function clothTexture(n, color) {
  return canvasTexture(256, 192, (ctx, w, h) => {
    ctx.fillStyle = color; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#f4efe4"; ctx.fillRect(0, h - 22, w, 10);
    ctx.font = "800 120px 'Arial Black', Arial, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.lineWidth = 10; ctx.strokeStyle = "#111"; ctx.strokeText(String(n), w / 2, h / 2 - 6);
    ctx.fillStyle = "#f4efe4"; ctx.fillText(String(n), w / 2, h / 2 - 6);
  });
}
function silkMat(color) { return new THREE.MeshPhysicalMaterial({ color, roughness: 0.38, sheen: 0.6, sheenColor: 0xffffff, sheenRoughness: 0.4 }); }

const NOSE = 1.72;        // from a horse's middle to the tip of its nose
const AFTER = ["finish", "paid", "jackpot", "aim", "shot", "dead"];     // phases after the race

class Horse {
  // A racehorse and jockey, facing +x, feet at y = 0. Legs are chains of pivots so the
  // gallop can swing and fold them.
  constructor({ n, coat, silks }) {
    const c = COATS[coat] || COATS.bay;
    const coatMat = new THREE.MeshPhysicalMaterial({ color: c.coat, roughness: 0.48, sheen: 0.35, sheenColor: 0xffffff, sheenRoughness: 0.5 });
    const pointMat = new THREE.MeshPhysicalMaterial({ color: c.points, roughness: 0.55, sheen: 0.2, sheenColor: 0xffffff });
    const maneMat = matte(c.mane, { roughness: 0.7 });
    const hoofMat = matte(0x2a2420, { roughness: 0.55 });
    this.root = new THREE.Group();
    this.body = new THREE.Group();
    this.body.position.y = 1.18;
    this.root.add(this.body);
    // the barrel: a lathe along the body, deeper than it is wide; the croup, quarters,
    // shoulders, withers and chest sit mostly inside it, so only their crowns shape it
    const prof = [[0, -1.0], [0.17, -0.985], [0.28, -0.93], [0.35, -0.82], [0.385, -0.64], [0.395, -0.4], [0.4, -0.1],
      [0.41, 0.2], [0.415, 0.45], [0.4, 0.65], [0.35, 0.82], [0.26, 0.93], [0.13, 0.985], [0, 1.0]].map(([r, y]) => new THREE.Vector2(r, y));
    const barrel = mesh(new THREE.LatheGeometry(prof, 48).rotateZ(-Math.PI / 2), coatMat);
    barrel.scale.set(1, 1, 0.8);
    this.body.add(barrel);
    const bulge = (x, y, z, rx, ry, rz) => { const e = ellipsoid(rx, ry, rz, coatMat); e.position.set(x, y, z); this.body.add(e); };
    bulge(-0.55, 0.24, 0, 0.46, 0.2, 0.28);                      // croup
    for (const s of [-1, 1]) {
      bulge(-0.6, 0.0, s * 0.2, 0.38, 0.32, 0.14);               // quarters
      bulge(0.5, -0.03, s * 0.22, 0.3, 0.3, 0.11);               // shoulders
    }
    bulge(0.55, 0.35, 0, 0.3, 0.12, 0.13);                       // withers
    bulge(0.8, -0.14, 0, 0.2, 0.25, 0.24);                       // chest
    // neck, head, mane, ears, eyes
    this.neck = new THREE.Group();
    this.neck.position.set(0.66, 0.2, 0);
    this.body.add(this.neck);
    const neckPts = [[0, 0], [0.3, 0.3], [0.52, 0.62], [0.6, 0.76]];
    this.neck.add(mesh(taper(neckPts, [0.27, 0.22, 0.155, 0.13], { flat: 0.62 }), coatMat));
    const crest = neckPts.map(([x, y], i) => [x - 0.07 + i * 0.01, y + 0.13 - i * 0.005]);
    this.neck.add(mesh(taper(crest, [0.03, 0.06, 0.05, 0.03], { flat: 0.45 }), maneMat));
    const headPts = [[0.58, 0.8], [0.74, 0.7], [0.94, 0.5], [1.03, 0.38]];
    this.neck.add(mesh(taper(headPts, [0.135, 0.13, 0.095, 0.078], { flat: 0.72 }), coatMat));
    const jaw = ellipsoid(0.13, 0.12, 0.1, coatMat); jaw.position.set(0.67, 0.7, 0); this.neck.add(jaw);
    for (const s of [-1, 1]) {
      const ear = mesh(new THREE.ConeGeometry(0.035, 0.13, 12), coatMat, 0.57, 0.93, s * 0.06);
      ear.rotation.set(s * -0.15, 0, -0.35);
      this.neck.add(ear);
      this.neck.add(mesh(new THREE.SphereGeometry(0.026, 14, 10), new THREE.MeshPhysicalMaterial({ color: 0x0c0908, roughness: 0.1, clearcoat: 1 }), 0.74, 0.78, s * 0.085));
      this.neck.add(mesh(new THREE.SphereGeometry(0.018, 10, 8), DARK, 1.05, 0.39, s * 0.045));
    }
    const blinker = mesh(new THREE.SphereGeometry(0.075, 18, 12, 0, Math.PI), silkMat(silks[0]), 0.72, 0.8, 0);
    blinker.scale.set(1, 1, 1.35);
    blinker.rotation.y = Math.PI / 2;
    this.neck.add(blinker);
    // tail
    this.tail = new THREE.Group();
    this.tail.position.set(-1.0, 0.24, 0);
    this.body.add(this.tail);
    this.tail.add(mesh(taper([[0, 0], [-0.14, -0.06], [-0.3, -0.28], [-0.38, -0.62]], [0.06, 0.1, 0.075, 0.025], { flat: 0.55 }), maneMat));
    // legs: chains of pivots (shoulder or hip, knee or hock, fetlock) so the gallop can
    // swing and fold them; the forearm and the thigh start inside the body
    this.legs = [];
    const leg = (x, side, front) => {
      const hip = new THREE.Group();
      hip.position.set(x, front ? -0.05 : 0.02, side * 0.2);
      this.body.add(hip);
      const upper = front ? 0.62 : 0.6;
      const pts = front ? [[0.02, 0.12], [0.04, -0.3], [0, -upper]] : [[0.06, 0.14], [-0.06, -0.3], [-0.1, -upper]];
      hip.add(mesh(taper(pts, front ? [0.15, 0.1, 0.062] : [0.21, 0.13, 0.066], { flat: 0.75 }), coatMat));
      const knee = new THREE.Group();
      knee.position.set(front ? 0 : -0.1, -upper, 0);
      hip.add(knee);
      knee.add(ellipsoid(front ? 0.066 : 0.07, 0.07, front ? 0.058 : 0.055, front ? coatMat : pointMat, 18));
      const cannon = front ? 0.32 : 0.4;
      knee.add(mesh(taper([[0, 0], [0, -cannon]], [0.05, 0.043], { flat: 0.8, segments: 6 }), pointMat));
      const fetlock = new THREE.Group();
      fetlock.position.set(0, -cannon, 0);
      knee.add(fetlock);
      fetlock.add(ellipsoid(0.056, 0.05, 0.05, pointMat, 16));
      fetlock.add(mesh(taper([[0, 0], [0.05, -0.11]], [0.046, 0.048], { flat: 0.9, segments: 6 }), pointMat));
      fetlock.add(mesh(new THREE.CylinderGeometry(0.052, 0.068, 0.09, 20), hoofMat, 0.062, -0.15, 0));
      this.legs.push({ hip, knee, fetlock, front, side });
    };
    leg(0.58, 1, true); leg(0.58, -1, true); leg(-0.66, 1, false); leg(-0.66, -1, false);
    // tack: saddle cloths with the number, saddle, and the jockey
    const cloth = new THREE.MeshStandardMaterial({ map: clothTexture(n, silks[0]), roughness: 0.6 });
    for (const s of [-1, 1]) {
      const plate = mesh(new THREE.PlaneGeometry(0.62, 0.42), cloth, 0.06, 0.08, s * 0.325);
      plate.rotation.y = s < 0 ? Math.PI : 0;
      plate.rotation.x = s * -0.35;
      this.body.add(plate);
    }
    this.body.add(mesh(new RoundedBoxGeometry(0.4, 0.07, 0.42, 3, 0.03), matte(0x2a1a12, { roughness: 0.5 }), 0.05, 0.4, 0));
    const jockey = this.jockey = new THREE.Group();
    jockey.position.set(0.05, 0.46, 0);
    this.body.add(jockey);
    const shirt = silkMat(silks[0]), sleeve = silkMat(silks[1]), breeches = matte(0xf2efe6, { roughness: 0.6 });
    const boot = new THREE.MeshPhysicalMaterial({ color: 0x111111, roughness: 0.25, clearcoat: 0.8 });
    const skin = matte(0xc68b64, { roughness: 0.6 });
    jockey.add(mesh(taper([[-0.04, 0.2], [0.22, 0.35], [0.46, 0.42]], [0.15, 0.165, 0.13], { flat: 0.82 }), shirt));
    const helmet = mesh(new THREE.SphereGeometry(0.11, 24, 16, 0, TAU, 0, Math.PI * 0.6), silkMat(silks[1]), 0.56, 0.54, 0);
    jockey.add(helmet, mesh(new THREE.SphereGeometry(0.095, 20, 14), skin, 0.57, 0.5, 0));
    const peak = mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.012, 20, 1, false, -0.9, 1.8), silkMat(silks[1]), 0.6, 0.54, 0);
    jockey.add(peak);
    for (const s of [-1, 1]) {
      jockey.add(mesh(taper([[0.38, 0.4, s * 0.13], [0.5, 0.26, s * 0.17], [0.66, 0.18, s * 0.1]], [0.05, 0.045, 0.035]), sleeve));
      jockey.add(mesh(taper([[0.0, 0.2, s * 0.1], [0.26, 0.1, s * 0.22]], [0.075, 0.06]), breeches));
      jockey.add(mesh(taper([[0.26, 0.1, s * 0.22], [0.08, -0.14, s * 0.26]], [0.055, 0.045]), boot));
    }
    shadows(this.root, true, false);
    this.phase = Math.random();
    this.speed = 0;
    this.pose(0, 0);
  }
  pose(phase, speed) {
    // a rotary gallop: hind legs land a beat before the fore legs, then all four lift
    const run = clamp(speed / 14, 0, 1);
    const offsets = [0.44, 0.52, 0.0, 0.08];
    this.legs.forEach((l, i) => {
      const psi = TAU * (phase - offsets[i]);
      const swing = Math.max(0, Math.cos(psi));
      if (l.front) {
        l.hip.rotation.z = run * 0.62 * Math.sin(psi);
        l.knee.rotation.z = -run * 1.6 * Math.pow(swing, 1.3);
        l.fetlock.rotation.z = run * (0.35 * Math.max(0, -Math.cos(psi)) - 0.5 * swing);
      } else {
        l.hip.rotation.z = run * 0.55 * Math.sin(psi) - 0.08;
        l.knee.rotation.z = 0.1 + run * 1.1 * Math.pow(swing, 1.3);
        l.fetlock.rotation.z = run * (0.4 * Math.max(0, -Math.cos(psi)) - 0.6 * swing) - 0.05;
      }
    });
    this.body.position.y = 1.18 + run * 0.07 * Math.sin(TAU * 2 * phase);
    this.body.rotation.z = run * 0.06 * Math.sin(TAU * phase + 1.2);
    this.neck.rotation.z = -0.28 * run - run * 0.1 * Math.sin(TAU * phase + 0.4);
    this.tail.rotation.z = 0.5 * run + 0.08 * Math.sin(TAU * phase * 2);
    this.jockey.position.y = 0.46 - run * 0.04 * Math.sin(TAU * 2 * phase);
  }
  tick(dt, speed) {
    this.speed = lerp(this.speed, speed, 1 - Math.exp(-dt * 4));
    this.phase = (this.phase + dt * this.speed / 7.0) % 1;
    this.pose(this.phase, this.speed);
  }
}

class RaceScene {
  constructor(env) {
    const scene = this.scene = new THREE.Scene();
    scene.environment = env;
    scene.environmentIntensity = 0.45;
    scene.background = gradientSky("#6f9ccf", "#dfe8ee");
    scene.fog = new THREE.Fog(0xdfe8ee, 70, 360);
    this.camera = new THREE.PerspectiveCamera(32, 1, 0.1, 800);
    this.sun = keyLight(scene, 0xfff1dc, 3.0, [30, 50, 25], 14, 2048);
    scene.add(new THREE.HemisphereLight(0xcfe3ff, 0x5b6e3a, 0.9));
    this.track = 320;
    const grass = new THREE.MeshStandardMaterial({ map: canvasTexture(256, 256, (ctx, w, h) => noise(ctx, w, h, "#4d7a3a", 0.18, 9000, 2), { repeat: [80, 30] }), roughness: 0.95 });
    const ground = mesh(new THREE.PlaneGeometry(900, 400), grass, 160, 0, -40);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);
    const dirt = new THREE.MeshStandardMaterial({ map: canvasTexture(512, 512, (ctx, w, h) => {
      noise(ctx, w, h, "#8b6444", 0.22, 30000, 2);
      ctx.strokeStyle = "rgba(60,40,25,0.25)"; ctx.lineWidth = 2;
      for (let i = 0; i < 40; i++) { const y = Math.random() * h; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y + (Math.random() - 0.5) * 20); ctx.stroke(); }
    }, { repeat: [60, 3] }), roughness: 0.97 });
    const strip = mesh(new THREE.PlaneGeometry(460, 13), dirt, 150, 0.01, 0);
    strip.rotation.x = -Math.PI / 2;
    strip.receiveShadow = true;
    scene.add(strip);
    // white rails on posts, both sides
    const white = paint(0xf4f4f0, { metalness: 0, roughness: 0.4 });
    for (const z of [-6.8, 6.8]) {
      const rail = mesh(new THREE.BoxGeometry(460, 0.08, 0.1), white, 150, 1.05, z);
      rail.castShadow = true;
      scene.add(rail);
      const posts = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.04, 0.05, 1.05, 8), white, 190);
      const m4 = new THREE.Matrix4();
      for (let i = 0; i < 190; i++) { m4.makeTranslation(-80 + i * 2.4, 0.52, z); posts.setMatrixAt(i, m4); }
      posts.castShadow = true;
      scene.add(posts);
    }
    // distance poles and the finish
    for (let x = 40; x < this.track; x += 40) {
      scene.add(mesh(new THREE.CylinderGeometry(0.06, 0.06, 2.2, 10), paint(0xd8262c, { metalness: 0 }), x, 1.1, 7.3));
    }
    scene.add(mesh(new THREE.PlaneGeometry(0.3, 13), new THREE.MeshBasicMaterial({ color: 0xf6f6f2 }), this.track, 0.02, 0).rotateX(-Math.PI / 2));
    const post = new THREE.Group();
    post.add(mesh(new THREE.CylinderGeometry(0.08, 0.08, 3.4, 12), white, 0, 1.7, 0));
    const disc = mesh(new THREE.CircleGeometry(0.55, 36), new THREE.MeshStandardMaterial({ map: canvasTexture(128, 128, (ctx) => {
      ctx.fillStyle = "#f4f4f0"; ctx.fillRect(0, 0, 128, 128); ctx.fillStyle = "#d8262c"; ctx.beginPath(); ctx.arc(64, 64, 34, 0, TAU); ctx.fill();
    }), side: THREE.DoubleSide }), 0, 3.3, 0);
    disc.rotation.y = Math.PI / 2;
    post.add(disc);
    post.position.set(this.track, 0, -7.4);
    scene.add(shadows(post));
    // the grandstand across the track, full of people
    const stand = new THREE.Group();
    const concrete = matte(0xb9b4aa);
    for (let i = 0; i < 7; i++) stand.add(mesh(new THREE.BoxGeometry(170, 0.55, 1.6), concrete, 0, 0.3 + i * 0.55, -i * 1.6));
    stand.add(mesh(new THREE.BoxGeometry(172, 0.25, 13), paint(0x2c3d52, { metalness: 0.2 }), 0, 7.3, -5));
    for (let x = -80; x <= 80; x += 16) stand.add(mesh(new THREE.CylinderGeometry(0.18, 0.18, 7, 10), white, x, 3.5, -10));
    const crowd = new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.2, 0.45, 4, 8), matte(0xffffff, { roughness: 0.8 }), 1400);
    const m4 = new THREE.Matrix4(), col = new THREE.Color();
    const shirts = [0xd8262c, 0x1f5aa6, 0xf2c230, 0xf4efe4, 0x1f7a4d, 0x222222, 0xe0762b, 0x8fc1e8, 0x6a3d9a];
    for (let i = 0; i < 1400; i++) {
      const row = i % 7;
      m4.makeTranslation(-82 + Math.random() * 164, 0.95 + row * 0.55, -row * 1.6 - 0.3 + (Math.random() - 0.5) * 0.4);
      crowd.setMatrixAt(i, m4);
      crowd.setColorAt(i, col.setHex(shirts[Math.floor(Math.random() * shirts.length)]));
    }
    stand.add(crowd);
    const heads = new THREE.InstancedMesh(new THREE.SphereGeometry(0.13, 10, 8), matte(0xffffff, { roughness: 0.7 }), 1400);
    const skins = [0xf1c9a5, 0xd9a47a, 0xa9744e, 0x7a4f32, 0xe8b894];
    const tmp = new THREE.Matrix4(), place = new THREE.Vector3();
    for (let i = 0; i < 1400; i++) {
      crowd.getMatrixAt(i, tmp);
      place.setFromMatrixPosition(tmp);
      tmp.makeTranslation(place.x, place.y + 0.52, place.z);
      heads.setMatrixAt(i, tmp);
      heads.setColorAt(i, col.setHex(skins[i % skins.length]));
    }
    stand.add(heads);
    stand.position.set(this.track - 60, 0, -16);
    scene.add(shadows(stand, true, true));
    // trees and hills far off
    const trees = new THREE.InstancedMesh(new THREE.ConeGeometry(2.2, 7, 10), matte(0x2f5a2c), 140);
    for (let i = 0; i < 140; i++) {
      const s = 0.7 + Math.random() * 0.8;
      m4.compose(new THREE.Vector3(-120 + Math.random() * 560, 3.5 * s, -60 - Math.random() * 90), new THREE.Quaternion(), new THREE.Vector3(s, s, s));
      trees.setMatrixAt(i, m4);
    }
    scene.add(trees);
    for (let i = 0; i < 6; i++) {
      const hill = ellipsoid(80 + Math.random() * 60, 18 + Math.random() * 14, 40, matte(0x6d8a55));
      hill.position.set(-100 + i * 110, -4, -190);
      scene.add(hill);
    }
    // the starting gate: open steel frames with padded half-height partitions, a header
    // beam over the stalls, and barred doors that swing open at the off
    const gate = this.gate = new THREE.Group();
    const green = paint(0x2f6b4a, { metalness: 0.5 }), pad = matte(0x1f4a35, { roughness: 0.7 });
    const bar = (w, h, d, x, y, z) => gate.add(mesh(new THREE.BoxGeometry(w, h, d), green, x, y, z));
    for (let i = 0; i <= 6; i++) {
      const z = (i - 3) * 1.8;
      for (const x of [-2.6, 0]) bar(0.09, 2.6, 0.09, x, 1.3, z);
      bar(2.7, 0.08, 0.08, -1.3, 2.55, z);
      gate.add(mesh(new RoundedBoxGeometry(2.4, 0.8, 0.14, 3, 0.05), pad, -1.3, 0.85, z));
    }
    bar(2.8, 0.34, 11.2, -1.3, 2.78, 0);
    this.doors = [];
    for (let i = 0; i < 6; i++) {
      for (const s of [-1, 1]) {
        const pivot = new THREE.Group();
        pivot.position.set(0.02, 0, (i - 2.5) * 1.8 + s * 0.84);
        for (const y of [0.55, 1.05, 1.55]) pivot.add(mesh(new THREE.BoxGeometry(0.05, 0.06, 0.8), green, 0, y, -s * 0.42));
        for (const zz of [0.08, 0.76]) pivot.add(mesh(new THREE.BoxGeometry(0.05, 1.1, 0.05), green, 0, 1.05, -s * zz));
        gate.add(pivot);
        this.doors.push({ pivot, s });
      }
    }
    scene.add(shadows(gate));
    // the fly's pick: a ring on the ground under its horse, and a flag above
    this.ring = mesh(new THREE.RingGeometry(1.1, 1.35, 48), new THREE.MeshBasicMaterial({ color: 0xf2ad3a, transparent: true, opacity: 0.85 }), 0, 0.03, 0);
    this.ring.rotation.x = -Math.PI / 2;
    this.flag = new THREE.Sprite(new THREE.SpriteMaterial({ map: canvasTexture(256, 96, (ctx, w, h) => {
      ctx.fillStyle = "#f2ad3a"; ctx.beginPath(); ctx.roundRect(4, 4, w - 8, h - 30, 14); ctx.fill();
      ctx.beginPath(); ctx.moveTo(w / 2 - 16, h - 28); ctx.lineTo(w / 2 + 16, h - 28); ctx.lineTo(w / 2, h - 4); ctx.fill();
      ctx.fillStyle = "#111"; ctx.font = "800 36px Arial, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("FLY'S BET", w / 2, 36);
    }), depthTest: false }));
    this.flag.scale.set(1.5, 0.56, 1);
    scene.add(this.ring, this.flag);
    this.horses = [];
    this.key = "";
    this.race = null;
    this.clock = 0;
    this.phase = "";
    this.camX = 0;
    this.camMode = "gate";
    this.slow = 1;
  }
  setField(horses, number) {
    const key = `${number}:${horses.map((h) => h.name).join(",")}`;
    if (key === this.key) return;
    this.key = key;
    for (const h of this.horses) { this.scene.remove(h.root); dispose(h.root); }
    this.horses = horses.map((h, i) => {
      const horse = new Horse(h);
      horse.root.position.set(-NOSE, 0, (i - 2.5) * 1.8);
      this.scene.add(horse.root);
      return horse;
    });
    this.race = null;
    this.clock = 0;
    this.camMode = "gate";
    for (const d of this.doors) d.pivot.rotation.y = 0;
  }
  update(c, t) {
    if (c.horses) this.setField(c.horses, c.number);
    this.pick = c.pick;
    this.result = c.result;
    if (c.race && this.race !== c.race) { this.race = c.race; }
    if (c.phase !== this.phase) {
      if (c.phase === "race") { this.clock = 0; this.camMode = "track"; this.slow = 1; }
      this.phase = c.phase;
    }
    if (c.phase === "race" && typeof c.race_t === "number") {
      const diff = c.race_t - this.clock;
      if (Math.abs(diff) > 0.4) this.clock = c.race_t; else this.clock += diff * 0.1;
    }
    if (this.race && AFTER.includes(c.phase)) {
      const end = (this.race.x[0].length - 1) * this.race.every;
      if (this.clock < end - 0.5) this.clock = end;        // the page came in after the race
    }
  }
  x(i, time) {
    const r = this.race;
    if (!r) return 0;
    const xs = r.x[i], f = time / r.every, k = Math.floor(f);
    if (k >= xs.length - 1) {                 // past the last sample: pulling up to a stop
      const end = xs[xs.length - 1], v = (end - xs[xs.length - 2]) / r.every, dt = Math.max(0, time - (xs.length - 1) * r.every);
      return end + v * 1.5 * (1 - Math.exp(-dt / 1.5));
    }
    return lerp(xs[Math.max(0, k)], xs[Math.max(0, k) + 1], f - k);
  }
  tick(dt, t) {
    const racing = this.phase === "race" || (this.race && AFTER.includes(this.phase));
    if (this.phase === "race") {
      // the finish in slow motion when it is close
      const leader = Math.max(...this.horses.map((_, i) => this.x(i, this.clock)));
      const close = this.race && this.race.finish ? Math.abs(this.race.finish.slice().sort((a, b) => a - b)[1] - Math.min(...this.race.finish)) < 0.1 : false;
      this.slow = close && leader > this.track - 14 && leader < this.track + 2 ? 0.35 : lerp(this.slow, 1, 0.05);
      this.clock += dt * this.slow;
    } else if (racing) {
      this.clock += dt;
    }
    const opening = this.phase === "race" ? clamp(this.clock / 0.3, 0, 1) : 0;
    for (const d of this.doors) d.pivot.rotation.y = d.s * smooth(opening) * 1.9;
    let sum = 0, lead = -1e9, last = 1e9;
    this.horses.forEach((h, i) => {
      const x = racing ? this.x(i, this.clock) : 0;
      const speed = racing ? (this.x(i, this.clock + 0.05) - this.x(i, this.clock - 0.05)) / 0.1 : 0;
      h.root.position.x = x - NOSE;
      h.tick(dt * (this.phase === "race" ? this.slow : 1), Math.max(0, speed));
      sum += x; lead = Math.max(lead, x); last = Math.min(last, x);
    });
    const mean = this.horses.length ? sum / this.horses.length : 0;
    if (this.pick !== null && this.pick !== undefined && this.horses[this.pick]) {
      const p = this.horses[this.pick].root.position;
      this.ring.visible = this.flag.visible = true;
      this.ring.position.set(p.x + 0.2, 0.03, p.z);
      this.flag.position.set(p.x + 0.4, 3.0, p.z);
      this.ring.material.opacity = 0.6 + 0.3 * Math.sin(t * 6);
    } else {
      this.ring.visible = this.flag.visible = false;
    }
    // the camera: at the gates, then tracking the pack, then at the post for the finish
    let focus, pos, fitted = false;
    const tracking = this.phase === "race" && lead < this.track - 22;
    if (!racing) {
      const a = Math.sin(t * 0.2) * 0.25;
      focus = new THREE.Vector3(-1.4, 1.5, 0.5);
      pos = new THREE.Vector3(7.5 + Math.sin(a) * 2.5, 3.2, 10.5);
    } else if (tracking) {
      // alongside the pack, far enough out to get the whole field in, from the last
      // horse's tail to the leader's nose, even in the nearest lane (no smoothing: the
      // pack itself moves smoothly)
      const half = Math.atan(Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2)) * this.camera.aspect);
      const out = clamp((lead - last + 6) / (2 * Math.tan(half)) + 4.5, 13.5, 60);
      const x = (lead + last) / 2 - 1.5;
      focus = new THREE.Vector3(x + 0.6, 1.1, -6);
      pos = new THREE.Vector3(x + 1.5, 1.1 + out * 0.25, out);
      fitted = true;
    } else {
      // at the post for the finish, then along with the horses as they pull up past it
      const a = this.phase === "race" ? 0 : Math.sin((t % 1000) * 0.15) * 0.3;
      const x = this.phase === "race" ? this.track - 1.5 : Math.max(this.track - 1.5, mean - NOSE);
      focus = new THREE.Vector3(x, 1.2, -3);
      pos = new THREE.Vector3(x + 4.5 + Math.sin(a) * 6, 2.8, 14);
    }
    // the other shots are framed for a wide view; a narrow one pulls back so they still fit
    if (!fitted) pos.sub(focus).multiplyScalar(Math.max(1, 1.35 / Math.max(0.3, this.camera.aspect))).add(focus);
    this.camera.position.lerp(pos, tracking || this.camera.position.distanceTo(pos) > 60 ? 1 : 1 - Math.exp(-dt * 2.5));
    this.camera.lookAt(focus);
    this.sun.position.set(focus.x + 30, 50, 25);
    this.sun.target.position.copy(focus);
  }
}

// ------------------------------------------------------------------ the renderer
export class Casino3D {
  constructor(canvas) {
    this.canvas = canvas;
    const r = this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.0;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFShadowMap;
    const pmrem = new THREE.PMREMGenerator(r);
    this.env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    this.scenes = {};
    this.game = null;
    this.t = 0;
    this.last = performance.now();
    const loop = (now) => {
      requestAnimationFrame(loop);
      const dt = Math.min(0.05, (now - this.last) / 1000);
      this.last = now;
      this.t += dt;
      this.frame(dt);
    };
    requestAnimationFrame(loop);
  }
  scene(game) {
    if (!this.scenes[game]) {
      const S = { cards: CardsScene, slots: SlotsScene, race: RaceScene }[game];
      if (!S) return null;
      this.scenes[game] = new S(this.env);
    }
    return this.scenes[game];
  }
  update(c) {
    if (!c || !c.game) return;
    this.game = c.game;
    const s = this.scene(c.game);
    if (s) s.update(c, this.t);
  }
  frame(dt) {
    const s = this.game && this.scenes[this.game];
    if (!s || !this.canvas.clientWidth) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    if (this.canvas.width !== Math.floor(w * dpr) || this.canvas.height !== Math.floor(h * dpr)) {
      this.renderer.setPixelRatio(dpr);
      this.renderer.setSize(w, h, false);
    }
    s.camera.aspect = w / Math.max(1, h);
    s.camera.updateProjectionMatrix();
    s.tick(dt, this.t);
    this.renderer.render(s.scene, s.camera);
  }
}
window.Casino3D = Casino3D;
window.dispatchEvent(new Event("casino3d-ready"));
