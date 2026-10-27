// THE STRANGER — a procedural Old-West 3D short.
// Every frame is a pure function of HyperFrames time: renderAt(t).
import * as THREE from "./vendor/three.module.js";

const W = 1920;
const H = 1080;
const canvas = document.getElementById("film-canvas");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

// ------------------------------------------------------------------ utils
function mulberry32(seed) {
  let v = seed >>> 0;
  return () => {
    v += 0x6d2b79f5;
    let t = v;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(1873);
const R = (a, b) => a + (b - a) * rand();
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const ease = (t) => {
  t = clamp(t);
  return t * t * (3 - 2 * t);
};
const seg = (t, a, b) => clamp((t - a) / (b - a));
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const TAU = Math.PI * 2;

// keyframed vector: ks = [[time, [x,y,z]], ...], eased between keys
function kv(t, ks) {
  if (t <= ks[0][0]) return V(...ks[0][1]);
  for (let i = 0; i < ks.length - 1; i++) {
    const [ta, a] = ks[i];
    const [tb, b] = ks[i + 1];
    if (t <= tb) {
      const u = ease((t - ta) / (tb - ta));
      return V(lerp(a[0], b[0], u), lerp(a[1], b[1], u), lerp(a[2], b[2], u));
    }
  }
  return V(...ks[ks.length - 1][1]);
}

// ---------------------------------------------------------- materials
const matCache = new Map();
function mat(color, o = {}) {
  const key = JSON.stringify([color, o.r, o.m, o.flat, o.e, o.ei, o.side, o.map?.uuid, o.op]);
  if (matCache.has(key)) return matCache.get(key);
  const m = new THREE.MeshStandardMaterial({
    color,
    roughness: o.r ?? 0.85,
    metalness: o.m ?? 0,
    flatShading: o.flat ?? false,
    map: o.map ?? null,
    emissive: o.e ?? 0x000000,
    emissiveIntensity: o.ei ?? 1,
    side: o.side ?? THREE.FrontSide,
    transparent: o.op !== undefined,
    opacity: o.op ?? 1,
  });
  matCache.set(key, m);
  return m;
}

function canvasTex(w, h, draw, rep = [1, 1]) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(rep[0], rep[1]);
  t.anisotropy = 8;
  return t;
}

function woodTex(base, rep = [1, 1], planks = 8, vertical = true) {
  return canvasTex(256, 256, (g, w, h) => {
    g.fillStyle = base;
    g.fillRect(0, 0, w, h);
    const n = planks;
    for (let i = 0; i < n; i++) {
      const s = i * (w / n);
      const shade = R(-0.18, 0.12);
      g.fillStyle = shade < 0 ? `rgba(0,0,0,${-shade})` : `rgba(255,230,190,${shade})`;
      if (vertical) g.fillRect(s, 0, w / n, h);
      else g.fillRect(0, s, w, h / n);
      for (let k = 0; k < 14; k++) {
        g.strokeStyle = `rgba(40,20,5,${R(0.05, 0.16)})`;
        g.lineWidth = R(0.5, 1.5);
        g.beginPath();
        const o = s + R(2, w / n - 2);
        if (vertical) {
          g.moveTo(o, 0);
          g.bezierCurveTo(o + R(-3, 3), h * 0.3, o + R(-3, 3), h * 0.7, o + R(-2, 2), h);
        } else {
          g.moveTo(0, o);
          g.bezierCurveTo(w * 0.3, o + R(-3, 3), w * 0.7, o + R(-3, 3), w, o + R(-2, 2));
        }
        g.stroke();
      }
      g.fillStyle = "rgba(20,10,2,0.55)";
      if (vertical) g.fillRect(s, 0, 2, h);
      else g.fillRect(0, s, w, 2);
      // nail heads + a knot
      g.fillStyle = "rgba(30,20,10,0.6)";
      for (let k = 0; k < 2; k++) {
        if (vertical) g.fillRect(s + w / n / 2 - 1, R(0, h), 3, 3);
        else g.fillRect(R(0, w), s + h / n / 2 - 1, 3, 3);
      }
      if (rand() < 0.4) {
        g.beginPath();
        g.fillStyle = "rgba(50,25,8,0.35)";
        if (vertical) g.ellipse(s + R(6, w / n - 6), R(0, h), 3, 6, 0, 0, TAU);
        else g.ellipse(R(0, w), s + R(6, h / n - 6), 6, 3, 0, 0, TAU);
        g.fill();
      }
    }
  }, rep);
}

function signTex(text, bg, fg, sub = "") {
  const t = canvasTex(1024, 256, (g, w, h) => {
    g.fillStyle = bg;
    g.fillRect(0, 0, w, h);
    for (let i = 0; i < 4; i++) {
      g.fillStyle = `rgba(0,0,0,${R(0.05, 0.15)})`;
      g.fillRect(0, i * 64, w, 2);
    }
    g.strokeStyle = fg;
    g.lineWidth = 8;
    g.strokeRect(14, 14, w - 28, h - 28);
    g.fillStyle = fg;
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.font = `bold ${sub ? 128 : 150}px "DejaVu Serif", serif`;
    g.save();
    g.translate(w / 2, sub ? h / 2 - 22 : h / 2 + 6);
    g.scale(1.0, 1.15);
    g.fillText(text, 0, 0);
    g.restore();
    if (sub) {
      g.font = `bold 44px "DejaVu Serif", serif`;
      g.fillText(sub, w / 2, h - 46);
    }
    // weathering
    for (let i = 0; i < 900; i++) {
      g.fillStyle = `rgba(${rand() < 0.5 ? "0,0,0" : "255,240,210"},${R(0.03, 0.12)})`;
      g.fillRect(R(0, w), R(0, h), R(1, 6), R(1, 3));
    }
  });
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  return t;
}

function sandTex(base, rep) {
  return canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = base;
    g.fillRect(0, 0, w, h);
    for (let i = 0; i < 26000; i++) {
      const v = R(-1, 1);
      g.fillStyle = v < 0 ? `rgba(70,35,10,${-v * 0.13})` : `rgba(255,225,180,${v * 0.11})`;
      g.fillRect(R(0, w), R(0, h), R(1, 3), R(1, 3));
    }
    for (let i = 0; i < 40; i++) {
      g.fillStyle = `rgba(90,50,20,0.07)`;
      g.beginPath();
      g.ellipse(R(0, w), R(0, h), R(10, 60), R(4, 20), R(0, 3), 0, TAU);
      g.fill();
    }
  }, rep);
}

function softDot() {
  const t = canvasTex(64, 64, (g, w) => {
    const gr = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    gr.addColorStop(0, "rgba(255,255,255,1)");
    gr.addColorStop(0.4, "rgba(255,255,255,0.45)");
    gr.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = gr;
    g.fillRect(0, 0, w, w);
  });
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  return t;
}
const DOT = softDot();

function mesh(geo, material, cast = true, recv = true) {
  const m = new THREE.Mesh(geo, material);
  m.castShadow = cast;
  m.receiveShadow = recv;
  return m;
}
function box(w, h, d, material, x = 0, y = 0, z = 0, cast = true) {
  const m = mesh(new THREE.BoxGeometry(w, h, d), material, cast);
  m.position.set(x, y, z);
  return m;
}
function cyl(rt, rb, h, material, seg = 12, x = 0, y = 0, z = 0) {
  const m = mesh(new THREE.CylinderGeometry(rt, rb, h, seg), material);
  m.position.set(x, y, z);
  return m;
}
function capsule(r, len, material, x = 0, y = 0, z = 0) {
  const m = mesh(new THREE.CapsuleGeometry(r, len, 6, 12), material);
  m.position.set(x, y, z);
  return m;
}
function sphere(r, material, x = 0, y = 0, z = 0, ws = 18, hs = 14) {
  const m = mesh(new THREE.SphereGeometry(r, ws, hs), material);
  m.position.set(x, y, z);
  return m;
}
function pivot(parent, x, y, z) {
  const p = new THREE.Group();
  p.position.set(x, y, z);
  parent.add(p);
  return p;
}
// orient a unit-Y cylinder between two world points
const _up = V(0, 1, 0);
function stick(m, a, b) {
  const d = b.clone().sub(a);
  const len = d.length();
  m.position.copy(a).addScaledVector(d, 0.5);
  m.scale.set(1, Math.max(len, 1e-3), 1);
  m.quaternion.setFromUnitVectors(_up, d.normalize());
}

// ------------------------------------------------------------- humans
function makeHuman(o) {
  const skin = mat(o.skin ?? 0xc68a62, { r: 0.7 });
  const shirt = mat(o.shirt ?? 0xd9cdb0);
  const pants = mat(o.pants ?? 0x4a3a2c);
  const bootM = mat(0x2a1a10, { r: 0.55 });
  const hatM = mat(o.hat ?? 0x3a2a1c, { r: 0.9 });
  const dark = mat(0x140c08, { r: 0.4 });
  const root = new THREE.Group();
  const hips = pivot(root, 0, 0.98, 0);
  hips.add(box(0.36, 0.2, 0.22, pants, 0, 0, 0));
  const spine = pivot(hips, 0, 0.08, 0);
  const torso = capsule(0.17, 0.32, o.vest ? mat(o.vest) : shirt, 0, 0.27, 0);
  torso.scale.set(1.12, 1, 0.78);
  spine.add(torso);
  // shirt sleeves visible above vest
  if (o.vest) {
    const sh = capsule(0.12, 0.2, shirt, 0, 0.42, 0);
    sh.scale.set(1.9, 0.6, 0.9);
    spine.add(sh);
  }
  if (o.belt !== false) {
    spine.add(box(0.37, 0.07, 0.26, mat(0x2c1a0e, { r: 0.5 }), 0, -0.02, 0));
    spine.add(box(0.06, 0.05, 0.02, mat(0xb8973c, { m: 0.8, r: 0.35 }), 0, -0.02, 0.135));
    if (o.gun) {
      const hol = box(0.08, 0.22, 0.06, mat(0x3a2210), 0.22, -0.13, 0.02);
      hol.rotation.z = 0.12;
      spine.add(hol);
      spine.add(box(0.05, 0.12, 0.04, mat(0x6b4a2a, { r: 0.4 }), 0.225, 0.02, -0.01));
    }
  }
  if (o.badge) spine.add(sphere(0.03, mat(0xd9b450, { m: 0.9, r: 0.25, e: 0x302000 }), -0.09, 0.4, 0.13, 6, 4));
  if (o.apron) spine.add(box(0.34, 0.6, 0.02, mat(0xe8e0cc), 0, -0.2, 0.15));
  if (o.bandana) {
    const bd = cyl(0.11, 0.13, 0.07, mat(o.bandana), 12, 0, 0.6, 0.0);
    spine.add(bd);
    const tri = mesh(new THREE.ConeGeometry(0.08, 0.13, 3), mat(o.bandana));
    tri.position.set(0, 0.52, 0.1);
    tri.rotation.set(Math.PI, 0, 0);
    spine.add(tri);
  }
  // duster coat: flared open tube from shoulders to shins
  let coat = null;
  if (o.coat) {
    const cm = mat(o.coat, { r: 0.95, side: THREE.DoubleSide });
    coat = new THREE.Group();
    const upper = mesh(new THREE.CylinderGeometry(0.2, 0.25, 0.55, 16, 1, true), cm);
    upper.scale.set(1.1, 1, 0.8);
    upper.position.y = 0.33;
    coat.add(upper);
    const lower = mesh(new THREE.CylinderGeometry(0.255, 0.36, 0.78, 16, 1, true, 0.35, TAU - 0.7), cm);
    lower.scale.set(1.1, 1, 0.85);
    lower.position.y = -0.33;
    coat.add(lower);
    const collar = mesh(new THREE.TorusGeometry(0.15, 0.04, 6, 16), cm);
    collar.rotation.x = Math.PI / 2;
    collar.position.y = 0.58;
    coat.add(collar);
    // cape-like shoulder yoke
    const yoke = mesh(new THREE.CylinderGeometry(0.17, 0.27, 0.18, 16, 1, true), cm);
    yoke.scale.set(1.15, 1, 0.85);
    yoke.position.y = 0.5;
    coat.add(yoke);
    spine.add(coat);
  }
  const neck = pivot(spine, 0, 0.6, 0);
  neck.add(cyl(0.06, 0.07, 0.1, skin, 10, 0, 0.04, 0));
  const head = pivot(neck, 0, 0.1, 0);
  const skull = sphere(0.125, skin, 0, 0.1, 0);
  skull.scale.set(0.92, 1.1, 1);
  head.add(skull);
  const jaw = sphere(0.1, skin, 0, 0.03, 0.025);
  jaw.scale.set(0.95, 0.8, 1);
  head.add(jaw);
  head.add(sphere(0.026, skin, 0, 0.09, 0.125, 8, 6)); // nose
  head.add(sphere(0.016, dark, -0.045, 0.125, 0.105, 8, 6));
  head.add(sphere(0.016, dark, 0.045, 0.125, 0.105, 8, 6));
  const browM = mat(o.hair ?? 0x2a1a10);
  const bl = box(0.05, 0.012, 0.02, browM, -0.045, 0.155, 0.112);
  const br = box(0.05, 0.012, 0.02, browM, 0.045, 0.155, 0.112);
  bl.rotation.z = -0.15;
  br.rotation.z = 0.15;
  head.add(bl, br);
  head.add(sphere(0.022, skin, -0.122, 0.1, 0, 8, 6), sphere(0.022, skin, 0.122, 0.1, 0, 8, 6));
  if (o.mustache) {
    const mm = mat(o.hair ?? 0x2a1a10);
    const m1 = capsule(0.015, 0.06, mm, -0.03, 0.055, 0.118);
    const m2 = capsule(0.015, 0.06, mm, 0.03, 0.055, 0.118);
    m1.rotation.z = 1.2;
    m2.rotation.z = -1.2;
    head.add(m1, m2);
  }
  if (o.stubble) {
    const st = sphere(0.104, mat(0x3a2a20, { r: 1, op: 0.55 }), 0, 0.028, 0.03);
    st.scale.set(0.97, 0.78, 1.0);
    head.add(st);
  }
  if (o.beard) {
    const bd = sphere(0.09, mat(o.hair ?? 0x5a4a3a), 0, 0.0, 0.06);
    bd.scale.set(1, 1.1, 0.8);
    head.add(bd);
  }
  if (o.hat !== null) {
    const back = mesh(new THREE.SphereGeometry(0.132, 18, 12, Math.PI, Math.PI, 0, Math.PI * 0.8), browM);
    back.position.set(0, 0.105, -0.004);
    back.scale.set(0.93, 1.1, 1.02);
    head.add(back);
    const hat = new THREE.Group();
    const brim = cyl(o.brim ?? 0.27, o.brim ?? 0.27, 0.02, hatM, 24, 0, 0, 0);
    brim.scale.set(1, 1, 0.92);
    hat.add(brim);
    const crown = cyl(0.11, 0.135, o.crown ?? 0.15, hatM, 16, 0, (o.crown ?? 0.15) / 2, 0);
    hat.add(crown);
    hat.add(cyl(0.137, 0.137, 0.03, mat(0x1a120a), 16, 0, 0.025, 0));
    const dent = box(0.03, 0.03, 0.18, mat(0x1a120a), 0, o.crown ?? 0.15, 0);
    hat.add(dent);
    hat.position.set(0, 0.2, 0);
    hat.rotation.x = o.hatTilt ?? -0.08;
    head.add(hat);
  } else {
    const hair = sphere(0.13, browM, 0, 0.13, -0.01);
    hair.scale.set(0.95, 0.95, 1);
    head.add(hair);
  }
  const arm = (side) => {
    const sh = pivot(spine, side * 0.215, 0.5, 0);
    const sleeve = o.coat ? mat(o.coat, { r: 0.95 }) : shirt;
    const up = capsule(0.055, 0.22, sleeve, 0, -0.15, 0);
    sh.add(up);
    const el = pivot(sh, 0, -0.31, 0);
    el.add(capsule(0.047, 0.2, sleeve, 0, -0.13, 0));
    const hand = sphere(0.045, skin, 0, -0.29, 0.0, 10, 8);
    hand.scale.set(0.9, 1.2, 0.7);
    el.add(hand);
    const tip = pivot(el, 0, -0.3, 0.0);
    return { sh, el, tip };
  };
  const leg = (side) => {
    const hp = pivot(hips, side * 0.1, -0.04, 0);
    hp.add(capsule(0.075, 0.33, pants, 0, -0.22, 0));
    const kn = pivot(hp, 0, -0.45, 0);
    kn.add(capsule(0.062, 0.32, pants, 0, -0.21, 0));
    const boot = box(0.1, 0.12, 0.25, bootM, 0, -0.44, 0.05);
    kn.add(boot);
    kn.add(cyl(0.07, 0.065, 0.14, bootM, 10, 0, -0.33, 0));
    if (o.spurs) kn.add(cyl(0.028, 0.028, 0.008, mat(0xaaaaaa, { m: 0.9, r: 0.3 }), 8, 0, -0.44, -0.09));
    return { hp, kn };
  };
  const L = arm(-1), Rr = arm(1);
  const LL = leg(-1), RL = leg(1);
  const j = { root, hips, spine, neck, head, coat, shL: L.sh, elL: L.el, tipL: L.tip, shR: Rr.sh, elR: Rr.el, tipR: Rr.tip, hipL: LL.hp, knL: LL.kn, hipR: RL.hp, knR: RL.kn };
  root.traverse((c) => {
    if (c.isMesh) c.castShadow = c.receiveShadow = true;
  });
  root.scale.setScalar(o.scale ?? 1);
  return j;
}

function rest(j) {
  for (const k of ["hips", "spine", "neck", "head", "shL", "elL", "shR", "elR", "hipL", "knL", "hipR", "knR"]) j[k].rotation.set(0, 0, 0);
  j.hips.position.y = 0.98;
  j.shL.rotation.z = -0.08;
  j.shR.rotation.z = 0.08;
  j.elL.rotation.x = -0.12;
  j.elR.rotation.x = -0.12;
}

// phase in cycles; contact of left foot at phase 0.25, right at 0.75
function walk(j, phase, amt = 1) {
  const s = Math.sin(TAU * phase);
  const c = Math.cos(TAU * phase);
  j.hipL.rotation.x = -0.42 * s * amt;
  j.hipR.rotation.x = 0.42 * s * amt;
  j.knL.rotation.x = amt * (0.08 + 0.75 * Math.max(0, c));
  j.knR.rotation.x = amt * (0.08 + 0.75 * Math.max(0, -c));
  j.shL.rotation.x = 0.32 * s * amt;
  j.shR.rotation.x = -0.32 * s * amt;
  j.elL.rotation.x = -0.25 * amt;
  j.elR.rotation.x = -0.25 * amt;
  j.hips.position.y = 0.98 - 0.03 * amt + 0.03 * amt * Math.abs(c);
  j.hips.rotation.y = 0.06 * s * amt;
  j.spine.rotation.y = -0.1 * s * amt;
  if (j.coat) j.coat.rotation.x = 0.04 * amt * Math.abs(c);
}

function sit(j) {
  j.hips.position.y = 0.5;
  j.hipL.rotation.x = -1.5;
  j.hipR.rotation.x = -1.5;
  j.knL.rotation.x = 1.5;
  j.knR.rotation.x = 1.5;
}

// --------------------------------------------------------------- horse
function makeHorse(coatHex = 0x5a3320) {
  const coatM = mat(coatHex, { r: 0.6 });
  const darkM = mat(0x1c120c, { r: 0.7 });
  const root = new THREE.Group();
  const body = pivot(root, 0, 1.42, 0);
  const barrel = capsule(0.38, 1.05, coatM, 0, 0, 0);
  barrel.rotation.x = Math.PI / 2;
  barrel.scale.set(0.95, 1, 1.05);
  body.add(barrel);
  const chest = sphere(0.4, coatM, 0, 0.04, 0.62);
  chest.scale.set(0.9, 1.0, 0.8);
  const rump = sphere(0.42, coatM, 0, 0.06, -0.62);
  rump.scale.set(1.0, 0.95, 0.85);
  body.add(chest, rump);
  // saddle + blanket
  const blanket = box(0.86, 0.04, 0.7, mat(0x8a2a1c), 0, 0.37, 0.05);
  blanket.scale.set(1, 1, 1);
  body.add(blanket);
  const saddleM = mat(0x4a2a12, { r: 0.45 });
  body.add(box(0.5, 0.12, 0.55, saddleM, 0, 0.44, 0.05));
  body.add(box(0.46, 0.18, 0.08, saddleM, 0, 0.53, -0.2));
  body.add(cyl(0.035, 0.035, 0.16, saddleM, 8, 0, 0.56, 0.3));
  for (const s of [-1, 1]) {
    body.add(box(0.03, 0.42, 0.1, saddleM, s * 0.33, 0.18, 0.08));
    body.add(box(0.08, 0.04, 0.12, mat(0x8a6a3a, { m: 0.5 }), s * 0.36, -0.06, 0.08));
  }
  // bedroll
  const roll = cyl(0.09, 0.09, 0.62, mat(0x6b5a40), 10, 0, 0.5, -0.37);
  roll.rotation.z = Math.PI / 2;
  body.add(roll);
  const neck = pivot(body, 0, 0.2, 0.72);
  const neckM = capsule(0.2, 0.55, coatM, 0, 0.32, 0.12);
  neckM.rotation.x = 0.55;
  neckM.scale.set(0.8, 1, 1.15);
  neck.add(neckM);
  const mane = box(0.06, 0.62, 0.14, darkM, 0, 0.42, -0.02);
  mane.rotation.x = 0.55;
  neck.add(mane);
  const head = pivot(neck, 0, 0.66, 0.36);
  const skull = capsule(0.13, 0.42, coatM, 0, -0.14, 0.2);
  skull.rotation.x = 2.2;
  skull.scale.set(0.95, 1, 0.85);
  head.add(skull);
  head.add(sphere(0.115, mat(0x2a1a12), 0, -0.36, 0.46));
  head.add(sphere(0.022, darkM, -0.11, 0.0, 0.14, 8, 6), sphere(0.022, darkM, 0.11, 0.0, 0.14, 8, 6));
  for (const s of [-1, 1]) {
    const ear = mesh(new THREE.ConeGeometry(0.04, 0.14, 6), coatM);
    ear.position.set(s * 0.07, 0.13, 0.0);
    ear.rotation.set(-0.2, 0, s * -0.2);
    head.add(ear);
  }
  head.add(box(0.06, 0.1, 0.12, darkM, 0, 0.12, 0.06)); // forelock
  const bit = pivot(head, 0, -0.36, 0.42);
  const tail = pivot(body, 0, 0.22, -0.98);
  const tailM = mesh(new THREE.ConeGeometry(0.1, 0.85, 8), darkM);
  tailM.position.set(0, -0.36, -0.06);
  tailM.rotation.x = Math.PI + 0.2;
  tail.add(tailM);
  const legs = {};
  for (const [name, x, z] of [["LF", -0.2, 0.6], ["RF", 0.2, 0.6], ["LH", -0.2, -0.62], ["RH", 0.2, -0.62]]) {
    const hp = pivot(body, x, -0.14, z);
    const up = capsule(0.125, 0.4, coatM, 0, -0.26, 0);
    hp.add(up);
    const kn = pivot(hp, 0, -0.55, 0);
    kn.add(capsule(0.07, 0.42, coatM, 0, -0.24, 0));
    kn.add(cyl(0.07, 0.085, 0.1, darkM, 10, 0, -0.62, 0.01));
    kn.add(cyl(0.065, 0.07, 0.08, mat(0xe8dfd0), 10, 0, -0.54, 0)); // socks
    legs[name] = { hp, kn };
  }
  root.traverse((c) => {
    if (c.isMesh) c.castShadow = c.receiveShadow = true;
  });
  return { root, body, neck, head, tail, bit, legs };
}

function horseGait(h, phase, amt = 1, t = 0) {
  const offs = { LH: 0, LF: 0.25, RH: 0.5, RF: 0.75 };
  for (const [k, l] of Object.entries(h.legs)) {
    const p = TAU * (phase + offs[k]);
    const front = k.endsWith("F");
    l.hp.rotation.x = amt * 0.32 * Math.sin(p);
    const lift = Math.max(0, Math.cos(p));
    l.kn.rotation.x = amt * (front ? 0.85 : -0.7) * lift * lift;
  }
  h.body.position.y = 1.42 + amt * 0.025 * Math.sin(TAU * phase * 2);
  h.neck.rotation.x = amt * 0.06 * Math.sin(TAU * phase * 2 + 1);
  h.tail.rotation.x = 0.12 + 0.05 * Math.sin(t * 2.1);
  h.tail.rotation.z = 0.08 * Math.sin(t * 1.3);
}
function horseIdle(h, t) {
  for (const l of Object.values(h.legs)) {
    l.hp.rotation.x = 0;
    l.kn.rotation.x = 0;
  }
  h.legs.RH.kn.rotation.x = -0.18; // resting hind leg
  h.legs.RH.hp.rotation.x = 0.05;
  h.body.position.y = 1.42 + 0.006 * Math.sin(t * 1.6);
  h.neck.rotation.x = 0.1 + 0.04 * Math.sin(t * 0.7);
  h.head.rotation.x = 0.08;
  h.tail.rotation.x = 0.12 + 0.06 * Math.sin(t * 1.7);
  h.tail.rotation.z = 0.15 * Math.sin(t * 1.1);
}

// ------------------------------------------------------------- props
function cactus(scale = 1) {
  const g = new THREE.Group();
  const m = mat(0x56713d, { r: 0.8 });
  const h = 3.2 * scale;
  g.add(capsule(0.28 * scale, h, m, 0, h / 2 + 0.2, 0));
  for (const s of [-1, 1]) {
    if (rand() < 0.85) {
      const y = R(0.35, 0.6) * h;
      const len = R(0.5, 1.2) * scale;
      const hz = capsule(0.18 * scale, 0.5 * scale, m, s * 0.45 * scale, y, 0);
      hz.rotation.z = Math.PI / 2;
      g.add(hz);
      g.add(capsule(0.18 * scale, len, m, s * 0.75 * scale, y + len / 2 + 0.1, 0));
    }
  }
  g.rotation.y = R(0, TAU);
  return g;
}

function barrel(x, y, z) {
  const g = new THREE.Group();
  const b = cyl(0.32, 0.3, 0.85, mat(0x7a4a26, { map: woodTex("#7a4a26", [3, 1], 10, true) }), 14, 0, 0.43, 0);
  g.add(b);
  for (const yy of [0.15, 0.7]) g.add(cyl(0.33, 0.33, 0.05, mat(0x2a2420, { m: 0.6, r: 0.5 }), 14, 0, yy, 0));
  g.position.set(x, y, z);
  return g;
}

function tumbleweed(r = 0.5) {
  const g = new THREE.Group();
  const m = mat(0x8a6a3e, { r: 1 });
  const geo = new THREE.CylinderGeometry(0.012, 0.012, 1, 4);
  for (let i = 0; i < 70; i++) {
    const a = V(R(-1, 1), R(-1, 1), R(-1, 1)).normalize().multiplyScalar(r * R(0.6, 1));
    const b = V(R(-1, 1), R(-1, 1), R(-1, 1)).normalize().multiplyScalar(r * R(0.6, 1));
    const s = mesh(geo, m, true, false);
    stick(s, a, b);
    g.add(s);
  }
  return g;
}

// building with facade facing local +z, front plane at z=0
function building(o) {
  const g = new THREE.Group();
  const w = o.w ?? 9, h = o.h ?? 5.5, d = o.d ?? 10;
  const ex = o.extra ?? 1.8;
  const wallMat = mat(0xffffff, { map: woodTex(o.color, [w / 4, h / 4], 10, !o.horizontal), r: 0.9 });
  const trimM = mat(o.trim ?? 0xe8d8b8, { r: 0.8 });
  if (o.hollow) {
    g.add(box(0.3, h, d, wallMat, -w / 2 + 0.15, h / 2, -d / 2));
    g.add(box(0.3, h, d, wallMat, w / 2 - 0.15, h / 2, -d / 2));
    g.add(box(w, h, 0.3, wallMat, 0, h / 2, -d + 0.15));
    g.add(box(w, 0.3, d, wallMat, 0, h, -d / 2));
    const dw = 1.7, dh = 2.6;
    const fm = wallMat;
    g.add(box((w - dw) / 2, h, 0.3, fm, -(w + dw) / 4, h / 2, -0.15));
    g.add(box((w - dw) / 2, h, 0.3, fm, (w + dw) / 4, h / 2, -0.15));
    g.add(box(dw, h - dh, 0.3, fm, 0, dh + (h - dh) / 2, -0.15));
    // warm interior glow behind the batwing doors
    const glow = mesh(new THREE.PlaneGeometry(w - 0.8, h - 0.4), new THREE.MeshBasicMaterial({ map: interiorGlowTex(), fog: false }), false, false);
    glow.position.set(0, h / 2, -3.2);
    g.add(glow);
    g.add(box(w - 0.6, 0.1, d - 0.6, mat(0x3a2414), 0, 0.05, -d / 2, false));
    const warm = new THREE.PointLight(0xffa860, 7, 7, 1.6);
    warm.position.set(0, 2.2, -1.4);
    g.add(warm);
  } else {
    g.add(box(w, h, d, wallMat, 0, h / 2, -d / 2));
  }
  const roof = box(w + 0.3, 0.2, d + 0.3, mat(0x4a3428, { flat: true }), 0, h + 0.1, -d / 2);
  roof.rotation.x = 0.06;
  g.add(roof);
  // false front
  const ff = box(w + 0.3, ex, 0.25, wallMat, 0, h + ex / 2, 0.05);
  g.add(ff);
  g.add(box(w + 0.7, 0.28, 0.5, trimM, 0, h + ex + 0.1, 0.1));
  if (o.step) {
    g.add(box(w * 0.45, 0.6, 0.25, wallMat, 0, h + ex + 0.5, 0.05));
    g.add(box(w * 0.45 + 0.4, 0.2, 0.45, trimM, 0, h + ex + 0.85, 0.1));
  }
  for (const s of [-1, 1]) g.add(box(0.22, h + ex, 0.35, trimM, s * (w / 2 + 0.05), (h + ex) / 2, 0.12));
  // sign
  if (o.sign) {
    const sg = mesh(new THREE.PlaneGeometry(Math.min(w * 0.82, 7.4), Math.min(w * 0.82, 7.4) / 4), mat(0xffffff, { map: signTex(o.sign, o.signBg ?? "#e9dcc0", o.signFg ?? "#3a1f12", o.sub), r: 0.8 }), false, true);
    sg.position.set(0, h + ex * 0.45, 0.2);
    g.add(sg);
  }
  // windows
  const glass = mat(0x1a1410, { r: 0.15, m: 0.3, e: o.lit ? 0xffb060 : 0x000000, ei: o.lit ? 0.12 : 0 });
  const frame = trimM;
  const winRow = (y, n, skipMid) => {
    for (let i = 0; i < n; i++) {
      const x = (i - (n - 1) / 2) * (w / n);
      if (skipMid && Math.abs(x) < 1.4) continue;
      g.add(box(1.05, 1.35, 0.08, glass, x, y, 0.06, false));
      g.add(box(1.25, 0.1, 0.14, frame, x, y + 0.72, 0.08));
      g.add(box(1.25, 0.1, 0.14, frame, x, y - 0.72, 0.08));
      g.add(box(0.08, 1.35, 0.12, frame, x, y, 0.08, false));
      g.add(box(1.05, 0.06, 0.1, frame, x, y, 0.08, false));
      if (o.shutters) {
        const sm = mat(o.shutters);
        g.add(box(0.5, 1.4, 0.06, sm, x - 0.85, y, 0.1));
        g.add(box(0.5, 1.4, 0.06, sm, x + 0.85, y, 0.1));
      }
    }
  };
  winRow(1.8, o.win ?? 2, true);
  if (h > 6) winRow(h - 1.5, o.win2 ?? 3, false);
  // door
  if (!o.hollow) {
    g.add(box(1.3, 2.4, 0.1, mat(o.door ?? 0x3a2416, { map: woodTex("#5a3a22", [1, 1], 4) }), 0, 1.45, 0.05));
    g.add(sphere(0.04, mat(0xb8973c, { m: 0.8, r: 0.3 }), 0.45, 1.35, 0.12, 8, 6));
  }
  // boardwalk + porch
  const deck = mat(0xffffff, { map: woodTex("#8a6440", [w / 3, 1], 12, true), r: 0.9 });
  g.add(box(w + 0.4, 0.25, 3.0, deck, 0, 0.125, 1.5));
  if (o.porch !== false) {
    const pr = box(w + 0.6, 0.12, 3.3, mat(0x5a4030, { flat: true }), 0, 3.25, 1.55);
    pr.rotation.x = 0.08;
    g.add(pr);
    for (const x of [-w / 2, -w / 6, w / 6, w / 2]) g.add(cyl(0.08, 0.09, 3.1, mat(0xd8c8a8), 8, x, 1.7, 2.85));
    if (o.balcony) {
      for (let x = -w / 2; x <= w / 2 + 0.01; x += 0.45) g.add(box(0.05, 0.8, 0.05, trimM, x, 3.75, 3.05));
      g.add(box(w + 0.1, 0.08, 0.1, trimM, 0, 4.15, 3.05));
    }
  }
  return g;
}

let interiorGlow = null;
function interiorGlowTex() {
  if (interiorGlow) return interiorGlow;
  interiorGlow = canvasTex(256, 256, (g, w, h) => {
    const gr = g.createLinearGradient(0, 0, 0, h);
    gr.addColorStop(0, "#2a1408");
    gr.addColorStop(0.5, "#b0642a");
    gr.addColorStop(0.8, "#6a3414");
    gr.addColorStop(1, "#2a1206");
    g.fillStyle = gr;
    g.fillRect(0, 0, w, h);
    for (let i = 0; i < 3; i++) {
      const rg = g.createRadialGradient(w * (0.25 + i * 0.25), h * 0.55, 0, w * (0.25 + i * 0.25), h * 0.55, 40);
      rg.addColorStop(0, "rgba(255,190,90,0.9)");
      rg.addColorStop(1, "rgba(255,150,60,0)");
      g.fillStyle = rg;
      g.fillRect(0, 0, w, h);
    }
    // silhouettes of patrons
    g.fillStyle = "rgba(10,5,2,0.85)";
    for (let i = 0; i < 12; i++) {
      const x = R(20, w - 20), y = R(h * 0.8, h * 0.87);
      g.beginPath();
      g.ellipse(x, y, 6, 11, 0, 0, TAU);
      g.fill();
      g.beginPath();
      g.arc(x, y - 14, 4, 0, TAU);
      g.fill();
      g.fillRect(x - 7, y - 19, 14, 2);
    }
  });
  interiorGlow.wrapS = interiorGlow.wrapT = THREE.ClampToEdgeWrapping;
  return interiorGlow;
}

function batwing(width = 0.78) {
  const pv = new THREE.Group();
  const m = mat(0xffffff, { map: woodTex("#7a4a2a", [1, 1], 6), r: 0.75 });
  const panel = box(width, 1.0, 0.05, m, width / 2, 1.3, 0);
  pv.add(panel);
  for (let i = 0; i < 5; i++) pv.add(box(0.04, 0.6, 0.06, mat(0x3a2414), 0.12 + i * (width - 0.2) / 4, 1.3, 0.0));
  const top = box(width, 0.12, 0.07, mat(0x8a5a32), width / 2, 1.85, 0);
  pv.add(top);
  return pv;
}

function hitchRail(len) {
  const g = new THREE.Group();
  const m = mat(0x6a4a30, { flat: true, r: 0.95 });
  for (const s of [-1, 1]) g.add(cyl(0.07, 0.08, 1.15, m, 6, s * len / 2, 0.57, 0));
  const bar = cyl(0.06, 0.06, len + 0.3, m, 6, 0, 1.05, 0);
  bar.rotation.z = Math.PI / 2;
  g.add(bar);
  return g;
}

// =============================================================== EXTERIOR
const ext = new THREE.Scene();
const SUN_DIR = V(-0.13, 0.12, -1).normalize();
ext.fog = new THREE.Fog(0xd4805a, 60, 560);

const skyMat = new THREE.ShaderMaterial({
  side: THREE.BackSide,
  depthWrite: false,
  fog: false,
  uniforms: { sunDir: { value: SUN_DIR.clone() }, dusk: { value: 0 } },
  vertexShader: `varying vec3 vDir; void main(){ vDir = normalize(position); vec4 p = modelViewMatrix*vec4(position,1.0); gl_Position = projectionMatrix*p; }`,
  fragmentShader: `
    varying vec3 vDir; uniform vec3 sunDir; uniform float dusk;
    float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
    float noise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
      return mix(mix(hash(i),hash(i+vec2(1,0)),f.x), mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x), f.y); }
    float fbm(vec2 p){ float v=0.0, a=0.5; for(int i=0;i<5;i++){ v+=a*noise(p); p*=2.03; a*=0.5;} return v; }
    void main(){
      vec3 d = normalize(vDir);
      float h = clamp(d.y, -0.2, 1.0);
      float s = max(dot(d, sunDir), 0.0);
      vec3 horizon = mix(vec3(1.0,0.56,0.26), vec3(0.95,0.36,0.2), dusk);
      vec3 mid = mix(vec3(0.85,0.42,0.38), vec3(0.55,0.22,0.3), dusk);
      vec3 top = mix(vec3(0.17,0.16,0.36), vec3(0.08,0.07,0.2), dusk);
      vec3 col = mix(horizon, mid, smoothstep(0.0, 0.18, h));
      col = mix(col, top, smoothstep(0.15, 0.75, h));
      col += vec3(1.0,0.6,0.25) * pow(s, 8.0) * 0.55 * (1.0 - dusk*0.5);
      col += vec3(1.0,0.75,0.4) * pow(s, 90.0) * 1.2;
      // sun disc
      col = mix(col, vec3(4.0,2.6,1.3), smoothstep(0.99955, 0.99975, s));
      // high streaky clouds lit from below
      vec2 uv = d.xz / max(d.y + 0.08, 0.04);
      float c = fbm(uv * vec2(0.9, 2.6) + vec2(3.0, 1.0));
      float cl = smoothstep(0.52, 0.8, c) * smoothstep(0.02, 0.2, h) * (1.0 - smoothstep(0.5, 0.9, h));
      vec3 cloudCol = mix(vec3(0.55,0.25,0.3), vec3(1.0,0.62,0.35), pow(s, 3.0) + 0.25);
      col = mix(col, cloudCol, cl * 0.75);
      if (d.y < 0.0) col = mix(col, vec3(0.75,0.45,0.28), smoothstep(0.0, -0.1, d.y));
      gl_FragColor = vec4(col, 1.0);
    }`,
});
const sky = new THREE.Mesh(new THREE.SphereGeometry(900, 48, 24), skyMat);
ext.add(sky);

const sun = new THREE.DirectionalLight(0xffb27a, 3.4);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.03;
ext.add(sun, sun.target);
const hemi = new THREE.HemisphereLight(0x9b8ad0, 0x8a4a28, 1.05);
ext.add(hemi);
const fill = new THREE.DirectionalLight(0x8a7ad8, 0.35);
fill.position.set(30, 20, 60);
ext.add(fill);

// ground: desert with gentle dunes, flat compacted street
const groundGeo = new THREE.PlaneGeometry(1400, 1400, 220, 220);
groundGeo.rotateX(-Math.PI / 2);
{
  const p = groundGeo.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i);
    const town = clamp((Math.abs(x) - 26) / 40) * 1;
    const road = clamp((Math.abs(x) - 5) / 18);
    const dunes = Math.sin(x * 0.03 + Math.sin(z * 0.02)) * 1.6 + Math.sin(z * 0.045 + x * 0.01) * 1.2 + Math.sin(x * 0.11 + z * 0.07) * 0.35;
    const zt = z < -110 ? road : town;
    p.setY(i, Math.max(dunes, -0.5) * Math.max(zt, z < -110 ? road : town) - 0.02);
  }
  groundGeo.computeVertexNormals();
}
const ground = mesh(groundGeo, mat(0xffffff, { map: sandTex("#c88b58", [120, 120]), r: 1 }), false, true);
ext.add(ground);
const street = mesh(new THREE.PlaneGeometry(17, 420), mat(0xffffff, { map: canvasTex(256, 1024, (g, w, h) => {
  g.fillStyle = "#a9734a";
  g.fillRect(0, 0, w, h);
  for (let i = 0; i < 16000; i++) {
    const v = R(-1, 1);
    g.fillStyle = v < 0 ? `rgba(60,30,10,${-v * 0.16})` : `rgba(255,220,170,${v * 0.1})`;
    g.fillRect(R(0, w), R(0, h), R(1, 3), R(1, 4));
  }
  for (const x of [0.33, 0.43, 0.57, 0.67]) {
    g.fillStyle = "rgba(60,32,14,0.22)";
    g.fillRect(x * w - 5, 0, 10, h);
  }
  for (let i = 0; i < 160; i++) {
    g.fillStyle = "rgba(70,40,20,0.18)";
    g.beginPath();
    g.ellipse(R(w * 0.3, w * 0.7), R(0, h), 5, 7, 0, 0, TAU);
    g.fill();
  }
}, [1, 10]), r: 1 }), false, true);
street.rotation.x = -Math.PI / 2;
street.position.set(0, 0.01, -150);
ext.add(street);

// distant mesas and buttes
const mesaM = mat(0xa04e34, { flat: true, r: 1 });
const mesaM2 = mat(0x8a4232, { flat: true, r: 1 });
for (let i = 0; i < 26; i++) {
  const ang = R(-1.4, 1.4) + (i % 3 === 0 ? Math.PI : 0);
  const dist = R(300, 520);
  const r = R(18, 60);
  const hgt = R(25, 70);
  const geo = new THREE.CylinderGeometry(r * R(0.55, 0.85), r, hgt, Math.floor(R(6, 10)), 3);
  const pp = geo.attributes.position;
  for (let k = 0; k < pp.count; k++) {
    if (pp.getY(k) > -hgt / 2 + 0.1) {
      pp.setX(k, pp.getX(k) * R(0.9, 1.1));
      pp.setZ(k, pp.getZ(k) * R(0.9, 1.1));
    }
  }
  geo.computeVertexNormals();
  const m = mesh(geo, i % 2 ? mesaM : mesaM2, false, false);
  m.position.set(Math.sin(ang) * dist, hgt / 2 - 3, -Math.cos(ang) * dist);
  m.scale.set(R(1, 2.2), 1, 1);
  m.rotation.y = R(0, TAU);
  ext.add(m);
  // talus skirt
  const sk = mesh(new THREE.ConeGeometry(r * 1.6, hgt * 0.35, 9), mesaM2, false, false);
  sk.position.set(m.position.x, hgt * 0.17 - 3, m.position.z);
  sk.scale.copy(m.scale);
  ext.add(sk);
}

// cacti, rocks, scrub outside the town
const rockM = mat(0x8a5a40, { flat: true });
const scrubM = mat(0x6f7040, { flat: true });
for (let i = 0; i < 170; i++) {
  const x = R(-260, 260), z = R(-330, 120);
  if (Math.abs(x) < 26 && z > -100) continue;
  if (Math.abs(x) < 9) continue;
  const k = rand();
  if (k < 0.35) {
    const c = cactus(R(0.6, 1.25));
    c.position.set(x, 0, z);
    ext.add(c);
  } else if (k < 0.65) {
    const r = mesh(new THREE.DodecahedronGeometry(R(0.4, 2.2), 0), rockM, true, true);
    r.position.set(x, 0.2, z);
    r.scale.y = R(0.4, 0.8);
    r.rotation.y = R(0, TAU);
    ext.add(r);
  } else {
    const s = mesh(new THREE.IcosahedronGeometry(R(0.4, 0.9), 0), scrubM, true, true);
    s.position.set(x, 0.2, z);
    s.scale.y = 0.6;
    ext.add(s);
  }
}
// title-shot foreground cacti beside the trail
for (const [x, z, s] of [[-7.5, -146, 1.1], [9, -170, 0.9], [-12, -175, 1.3], [6, -128, 0.7]]) {
  const c = cactus(s);
  c.position.set(x, 0, z);
  ext.add(c);
}
// telegraph poles along the road into town
for (let z = -330; z < -60; z += 28) {
  const p = cyl(0.12, 0.14, 7.5, mat(0x4a3424), 6, -9.5, 3.75, z);
  ext.add(p);
  const cb = box(1.6, 0.12, 0.12, mat(0x4a3424), -9.5, 7.1, z);
  ext.add(cb);
}

// ---------------------------------------------------------------- town
const town = new THREE.Group();
ext.add(town);
const RIGHT = [
  { z: -42, sign: "HOTEL", color: "#9a6a4a", h: 7.2, w: 11, balcony: true, step: true, lit: true, win2: 4 },
  { z: -28, sign: "GENERAL STORE", color: "#b58a5a", w: 10, shutters: 0x3f5a4a },
  { z: -15, sign: "BANK", color: "#8a5040", w: 9, step: true, signBg: "#2a3a30", signFg: "#e8d8a0" },
  { z: 0, sign: "SALOON", color: "#a0603a", h: 7.4, w: 11, hollow: true, balcony: true, step: true, lit: true, signBg: "#5a1a12", signFg: "#f0d79a", win2: 4, sub: "WHISKEY · CARDS · PIANO" },
  { z: 14, sign: "BARBER", color: "#c49a6a", w: 8 },
  { z: 27, sign: "LIVERY STABLE", color: "#7a4a30", w: 12, h: 6.5 },
];
const LEFT = [
  { z: -40, sign: "SHERIFF", color: "#7a5a40", w: 9, signBg: "#1e1a16", signFg: "#e8c870", shutters: 0x5a3020 },
  { z: -26, sign: "POST OFFICE", color: "#b07850", w: 10 },
  { z: -12, sign: "ASSAY OFFICE", color: "#9a7050", w: 9, step: true },
  { z: 2, sign: "GUNSMITH", color: "#6a4a38", w: 10, signBg: "#e0c8a0", lit: true },
  { z: 16, sign: "DRY GOODS", color: "#b88a60", w: 11, h: 7, balcony: true, win2: 3 },
  { z: 30, sign: "UNDERTAKER", color: "#5a4a40", w: 8, signBg: "#1a1a1a", signFg: "#d8d0c0" },
];
let saloonDoors = null;
for (const b of RIGHT) {
  const g = building(b);
  g.rotation.y = -Math.PI / 2;
  g.position.set(12, 0, b.z);
  town.add(g);
  if (b.hollow) {
    const dl = batwing();
    const dr = batwing();
    dl.position.set(-0.8, 0, 0);
    dr.position.set(0.8, 0, 0);
    dr.scale.x = -1;
    g.add(dl, dr);
    saloonDoors = { dl, dr };
    const rail = hitchRail(3.6);
    rail.position.set(3.0, 0, 3.45);
    g.add(rail);
    const trough = new THREE.Group();
    trough.add(box(2.0, 0.5, 0.6, mat(0x5a3a22), 0, 0.25, 0));
    trough.add(box(1.85, 0.05, 0.45, mat(0x3a4a52, { r: 0.1, m: 0.2 }), 0, 0.46, 0, false));
    trough.position.set(-3.6, 0, 3.6);
    g.add(trough);
    g.add(barrel(4.6, 0.25, 0.6), barrel(5.1, 0.25, 1.1));
    // lanterns either side of the doors
    for (const s of [-1, 1]) {
      g.add(box(0.18, 0.28, 0.18, mat(0x2a2010, { e: 0xffa040, ei: 1.6 }), s * 1.4, 2.75, 0.25, false));
    }
  }
}
for (const b of LEFT) {
  const g = building(b);
  g.rotation.y = Math.PI / 2;
  g.position.set(-12, 0, b.z);
  town.add(g);
}
// water tower behind the left row
{
  const wt = new THREE.Group();
  const leg = mat(0x5a4030);
  for (const [x, z] of [[-1.6, -1.6], [1.6, -1.6], [-1.6, 1.6], [1.6, 1.6]]) {
    const l = cyl(0.12, 0.14, 9, leg, 6, x, 4.5, z);
    l.rotation.z = x * -0.02;
    wt.add(l);
  }
  wt.add(cyl(2.4, 2.4, 3.4, mat(0xffffff, { map: woodTex("#7a5236", [6, 1], 14, true) }), 18, 0, 10.6, 0));
  const cone = mesh(new THREE.ConeGeometry(2.7, 1.6, 18), mat(0x4a3428, { flat: true }));
  cone.position.y = 13.1;
  wt.add(cone);
  wt.position.set(-30, 0, -20);
  ext.add(wt);
}
// church steeple at the far end
{
  const ch = building({ w: 8, h: 6, d: 12, color: "#d8cdb8", porch: false, extra: 0.5 });
  ch.position.set(-6, 0, 62);
  ext.add(ch);
  const st = box(2.2, 6, 2.2, mat(0xe8dfcc), -6, 9, 60.5);
  ext.add(st);
  const sp = mesh(new THREE.ConeGeometry(1.7, 4.5, 4), mat(0x3a2e28, { flat: true }));
  sp.position.set(-6, 14.2, 60.5);
  sp.rotation.y = Math.PI / 4;
  ext.add(sp);
}
// street dressing
const wagon = new THREE.Group();
{
  const wm = mat(0x7a5232, { map: woodTex("#7a5232", [2, 1], 6, false) });
  wagon.add(box(1.7, 0.6, 3.4, wm, 0, 1.0, 0));
  for (const [x, z] of [[-0.95, 1.2], [0.95, 1.2], [-0.95, -1.2], [0.95, -1.2]]) {
    const wh = mesh(new THREE.TorusGeometry(0.5, 0.05, 6, 18), mat(0x3a2414));
    wh.position.set(x, 0.55, z);
    wh.rotation.y = Math.PI / 2;
    wagon.add(wh);
    for (let k = 0; k < 6; k++) {
      const sp = box(0.03, 0.95, 0.03, mat(0x5a3a22), x, 0.55, z);
      sp.rotation.x = (k * Math.PI) / 6;
      wagon.add(sp);
    }
  }
  const cover = mesh(new THREE.CylinderGeometry(1.0, 1.0, 3.0, 14, 1, true, -Math.PI / 2, Math.PI), mat(0xe6dcc6, { side: THREE.DoubleSide }));
  cover.rotation.x = Math.PI / 2;
  cover.rotation.y = Math.PI / 2;
  cover.position.set(0, 1.3, 0);
  cover.scale.set(1, 1, 0.9);
  wagon.add(cover);
  wagon.position.set(-7.2, 0, -21);
  wagon.rotation.y = 0.12;
  wagon.traverse((c) => c.isMesh && (c.castShadow = c.receiveShadow = true));
  ext.add(wagon);
}
ext.add(barrel(-9.4, 0.25, -33), barrel(-9.0, 0.25, -32.3), barrel(9.3, 0.25, -24));
for (const [x, z] of [[-9.2, 8], [9.4, 20]]) {
  const r = hitchRail(3);
  r.rotation.y = Math.PI / 2;
  r.position.set(x, 0, z);
  ext.add(r);
}

// a second horse already tied across the street
const horse2 = makeHorse(0x8a6a4a);
horse2.root.position.set(-7.4, 0, 8.2);
horse2.root.rotation.y = -Math.PI / 2;
ext.add(horse2.root);

// ------------------------------------------------------- the stranger
const stranger = makeHuman({ coat: 0x7a6248, shirt: 0x6a5a48, pants: 0x3a3028, hat: 0x2a1e16, bandana: 0x8a2a1c, stubble: true, gun: true, spurs: true, hair: 0x2a1c12, brim: 0.3, crown: 0.16, hatTilt: -0.14 });
const horse = makeHorse(0x3a2216);
ext.add(horse.root, stranger.root);
const rein = mesh(new THREE.CylinderGeometry(0.008, 0.008, 1, 4), mat(0x2a1a0e), true, false);
const rein2 = mesh(new THREE.CylinderGeometry(0.008, 0.008, 1, 4), mat(0x2a1a0e), true, false);
ext.add(rein, rein2);

// ------------------------------------------------- townsfolk on porches
const folk = [
  { o: { vest: 0x2a2a2a, shirt: 0xd8d0c0, badge: true, mustache: true, gun: true, hat: 0x5a4a3a, hair: 0x6a5a4a }, p: [-10.2, 0.25, -39], ry: Math.PI / 2 },
  { o: { shirt: 0x8a5a5a, hat: null, apron: true, hair: 0x4a2a1a, mustache: true }, p: [9.9, 0.25, -27.5], ry: -Math.PI / 2 },
  { o: { vest: 0x4a3a5a, shirt: 0xe0d8c8, hat: 0x2a2a2a, beard: true, hair: 0x9a8a7a }, p: [-10.4, 0.25, -11], ry: Math.PI / 2 },
  { o: { shirt: 0x5a6a8a, hat: 0x8a7050, mustache: true }, p: [9.8, 0.25, -14], ry: -Math.PI / 2 },
  { o: { shirt: 0xb8a070, vest: 0x5a3a2a, hat: 0x3a2a1a, gun: true, stubble: true }, p: [-10.1, 0.25, 3.5], ry: Math.PI / 2 },
  { o: { shirt: 0x9a4a3a, hat: 0x6a5a40 }, p: [-9.6, 0.25, 15], ry: Math.PI / 2 },
];
for (const f of folk) {
  f.j = makeHuman(f.o);
  f.j.root.position.set(...f.p);
  f.j.root.rotation.y = f.ry;
  ext.add(f.j.root);
}

// tumbleweeds
const tw1 = tumbleweed(0.55);
const tw2 = tumbleweed(0.45);
ext.add(tw1, tw2);

// dust: puffs from the coat + hoof dust, all derived from time
function makeDust(n, color, size) {
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(n * 3);
  const alpha = new Float32Array(n);
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("alpha", new THREE.BufferAttribute(alpha, 1));
  const m = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: { map: { value: DOT }, color: { value: new THREE.Color(color) }, size: { value: size } },
    vertexShader: `attribute float alpha; varying float vA; uniform float size;
      void main(){ vA = alpha; vec4 mv = modelViewMatrix*vec4(position,1.0); gl_PointSize = size * 1080.0 / -mv.z; gl_Position = projectionMatrix*mv; }`,
    fragmentShader: `uniform sampler2D map; uniform vec3 color; varying float vA;
      void main(){ vec4 t = texture2D(map, gl_PointCoord); gl_FragColor = vec4(color, t.a * vA); }`,
  });
  const pts = new THREE.Points(geo, m);
  pts.frustumCulled = false;
  const seeds = [];
  for (let i = 0; i < n; i++) seeds.push([R(-1, 1), R(-1, 1), R(-1, 1), R(0, 1), R(0, 1)]);
  return { pts, pos, alpha, seeds, geo, n };
}
const coatDust = makeDust(420, 0xc8a07a, 0.2);
ext.add(coatDust.pts);
const hoofDust = makeDust(300, 0xd8a070, 0.35);
ext.add(hoofDust.pts);

// =============================================================== INTERIOR
const inn = new THREE.Scene();
inn.fog = new THREE.Fog(0x2a160a, 6, 30);
inn.background = new THREE.Color(0x120904);
{
  const floor = mesh(new THREE.PlaneGeometry(18, 16), mat(0xffffff, { map: woodTex("#6a4428", [5, 5], 8, true), r: 0.7 }), false, true);
  floor.rotation.x = -Math.PI / 2;
  inn.add(floor);
  const wallM = mat(0xffffff, { map: woodTex("#5a3a24", [5, 2], 10, true), r: 0.85 });
  inn.add(box(18, 5, 0.3, wallM, 0, 2.5, -8));
  inn.add(box(0.3, 5, 16, wallM, -9, 2.5, 0));
  inn.add(box(0.3, 5, 16, wallM, 9, 2.5, 0));
  inn.add(box(18, 0.3, 16, mat(0x2a1a10), 0, 5, 0));
  // front wall with door opening (door at z=7, x in [-0.85, 0.85])
  inn.add(box(8.15, 5, 0.3, wallM, -4.93, 2.5, 7));
  inn.add(box(8.15, 5, 0.3, wallM, 4.93, 2.5, 7));
  inn.add(box(1.7, 2.4, 0.3, wallM, 0, 3.8, 7));
  // wainscot + beams
  for (const z of [-4, 0, 4]) inn.add(box(18, 0.3, 0.3, mat(0x3a2414), 0, 4.7, z));
  inn.add(box(0.1, 1.0, 16, mat(0x4a2c18), -8.84, 0.5, 0));
  inn.add(box(0.1, 1.0, 16, mat(0x4a2c18), 8.84, 0.5, 0));
  // front windows (glowing sunset)
  for (const x of [-5, 5]) {
    inn.add(box(1.8, 1.6, 0.05, new THREE.MeshBasicMaterial({ color: 0xffa060, fog: false }), x, 2.1, 7.17));
    inn.add(box(0.08, 1.6, 0.1, mat(0x2a1a10), x, 2.1, 7.1));
    inn.add(box(1.8, 0.08, 0.1, mat(0x2a1a10), x, 2.1, 7.1));
  }
  // sunset beyond the doorway
  const outside = mesh(new THREE.PlaneGeometry(6, 5), new THREE.MeshBasicMaterial({ map: canvasTex(256, 256, (g, w, h) => {
    const gr = g.createLinearGradient(0, 0, 0, h);
    gr.addColorStop(0, "#c86a50");
    gr.addColorStop(0.5, "#ffb070");
    gr.addColorStop(0.62, "#ffd090");
    gr.addColorStop(0.64, "#a86a48");
    gr.addColorStop(1, "#8a5a3a");
    g.fillStyle = gr;
    g.fillRect(0, 0, w, h);
    g.fillStyle = "rgba(60,30,20,0.85)";
    g.fillRect(0, h * 0.28, w * 0.3, h * 0.36);
    g.fillRect(w * 0.75, h * 0.22, w * 0.25, h * 0.42);
  }), fog: false }), false, false);
  outside.position.set(0, 2.2, 8.5);
  outside.rotation.y = Math.PI;
  inn.add(outside);
}
// bar along the left wall
{
  const barM = mat(0xffffff, { map: woodTex("#4a2814", [6, 1], 14, true), r: 0.45 });
  inn.add(box(1.0, 1.15, 10, barM, -6.2, 0.58, -1.5));
  inn.add(box(1.3, 0.1, 10.3, mat(0x2a140a, { r: 0.25, m: 0.1 }), -6.2, 1.2, -1.5));
  const rail = cyl(0.03, 0.03, 10, mat(0xb8973c, { m: 0.9, r: 0.3 }), 8, -5.55, 0.2, -1.5);
  rail.rotation.x = Math.PI / 2;
  inn.add(rail);
  // back bar: shelves, bottles, mirror
  inn.add(box(0.5, 3, 9, mat(0x3a2010), -8.6, 1.5, -1.5));
  inn.add(box(0.05, 1.4, 5, mat(0x9aa0a0, { m: 0.9, r: 0.1 }), -8.33, 2.7, -1.5));
  const bottleCols = [0x2a5a2a, 0x6a3a10, 0x8a6a20, 0x3a2a5a, 0x5a1a1a];
  for (let i = 0; i < 28; i++) {
    const c = bottleCols[i % 5];
    const b = cyl(0.05, 0.06, R(0.25, 0.38), mat(c, { r: 0.1, m: 0.1, e: c, ei: 0.25 }), 8, -8.25, i < 14 ? 1.75 : 3.6, -5.5 + (i % 14) * 0.62 + R(-0.1, 0.1));
    inn.add(b);
  }
  inn.add(box(0.45, 0.05, 9, mat(0x3a2010), -8.4, 1.55, -1.5));
  inn.add(box(0.45, 0.05, 9, mat(0x3a2010), -8.4, 3.4, -1.5));
  // glasses on the bar
  for (let i = 0; i < 5; i++) inn.add(cyl(0.04, 0.035, 0.1, mat(0xc0a060, { r: 0.05, op: 0.6 }), 8, -6.0, 1.3, -4 + i * 1.6));
}
// wanted posters
for (const [z, name] of [[-3.5, "WANTED"], [1.5, "REWARD"]]) {
  const p = mesh(new THREE.PlaneGeometry(0.8, 1.05), mat(0xffffff, { map: canvasTex(256, 336, (g, w, h) => {
    g.fillStyle = "#e0cfa8";
    g.fillRect(0, 0, w, h);
    g.fillStyle = "#2a1a10";
    g.textAlign = "center";
    g.font = 'bold 54px "DejaVu Serif", serif';
    g.fillText(name, w / 2, 62);
    g.fillStyle = "#6a5a40";
    g.fillRect(48, 86, w - 96, 150);
    g.fillStyle = "#2a1a10";
    g.font = 'bold 34px "DejaVu Serif", serif';
    g.fillText("$ 500", w / 2, 290);
  }), r: 1 }), false, true);
  p.position.set(8.83, 2.4, z);
  p.rotation.y = -Math.PI / 2;
  inn.add(p);
}
// piano against the right wall, keys facing -x
const piano = new THREE.Group();
{
  const pm = mat(0x2a140a, { r: 0.35, m: 0.05 });
  piano.add(box(0.65, 1.45, 1.7, pm, 0, 0.72, 0));
  piano.add(box(0.35, 0.08, 1.55, mat(0xeee6d4, { r: 0.4 }), -0.45, 0.88, 0));
  for (let k = 0; k < 18; k++) piano.add(box(0.2, 0.06, 0.04, mat(0x101010), -0.38, 0.93, -0.72 + k * 0.085));
  piano.add(box(0.4, 0.05, 1.7, pm, -0.4, 0.8, 0));
  piano.add(box(0.05, 0.4, 1.4, mat(0xe0d0b0, { r: 0.8 }), -0.34, 1.15, 0)); // sheet music
  piano.add(cyl(0.06, 0.08, 0.2, mat(0x9a7a3a, { m: 0.6 }), 8, 0.1, 1.55, 0.5));
  piano.position.set(8.4, 0, -2.8);
  inn.add(piano);
  inn.add(cyl(0.22, 0.22, 0.08, mat(0x5a2a1a), 12, 7.15, 0.55, -2.8));
  inn.add(cyl(0.05, 0.08, 0.52, mat(0x3a2010), 8, 7.15, 0.26, -2.8));
}
// tables, chairs, patrons
const tables = [[-2.2, -3.2], [2.6, 1.6], [-2.6, 2.6], [3.4, -4.6]];
const patrons = [];
const patronLooks = [
  { shirt: 0xc8b898, vest: 0x3a2a2a, hat: 0x4a3a2a, mustache: true },
  { shirt: 0x7a5a4a, hat: 0x2a2a2a, beard: true, hair: 0x5a4a3a },
  { shirt: 0xd8d0c0, vest: 0x5a2a2a, hat: 0x6a5a40, stubble: true },
  { shirt: 0x5a6a5a, hat: 0x3a2a1a, mustache: true, hair: 0x2a1a10 },
  { shirt: 0xa08060, hat: null, hair: 0x6a4a2a, mustache: true },
  { shirt: 0x6a4a6a, vest: 0x2a2a2a, hat: 0x2a1a10, gun: true },
  { shirt: 0xe0d4b8, hat: 0x8a7050, beard: true, hair: 0x8a8070 },
];
let pi = 0;
for (const [tx, tz] of tables) {
  const tm = mat(0xffffff, { map: woodTex("#6a4026", [1, 1], 6, false), r: 0.5 });
  inn.add(cyl(0.75, 0.75, 0.06, tm, 20, tx, 0.78, tz));
  inn.add(cyl(0.07, 0.12, 0.75, mat(0x2a1a10), 8, tx, 0.38, tz));
  // cards, glasses, a bottle
  for (let k = 0; k < 5; k++) {
    const c = box(0.09, 0.005, 0.13, mat(0xf0e8d8), tx + R(-0.3, 0.3), 0.815, tz + R(-0.3, 0.3), false);
    c.rotation.y = R(0, TAU);
    inn.add(c);
  }
  inn.add(cyl(0.05, 0.06, 0.3, mat(0x5a3a10, { r: 0.1, e: 0x3a1a00, ei: 0.4 }), 8, tx + 0.15, 0.96, tz - 0.1));
  const seats = tz < 0 ? [0.3, 2.4, 4.3] : [0.9, 3.3];
  for (const a of seats) {
    const cx = tx + Math.sin(a) * 1.05, cz = tz + Math.cos(a) * 1.05;
    const ch = new THREE.Group();
    const cm = mat(0x4a2c18);
    ch.add(box(0.45, 0.05, 0.45, cm, 0, 0.47, 0));
    for (const [lx, lz] of [[-0.2, -0.2], [0.2, -0.2], [-0.2, 0.2], [0.2, 0.2]]) ch.add(box(0.04, 0.47, 0.04, cm, lx, 0.235, lz));
    ch.add(box(0.45, 0.5, 0.04, cm, 0, 0.75, -0.21));
    ch.position.set(cx, 0, cz);
    ch.rotation.y = Math.atan2(tx - cx, tz - cz);
    inn.add(ch);
    if (pi < patronLooks.length) {
      const j = makeHuman(patronLooks[pi]);
      j.root.position.set(cx, 0, cz);
      j.root.rotation.y = Math.atan2(tx - cx, tz - cz);
      inn.add(j.root);
      patrons.push({ j, delay: 0.08 * pi + R(0, 0.15), side: R(-0.2, 0.2) });
      pi++;
    }
  }
}
const pianist = makeHuman({ shirt: 0xe8e0d0, vest: 0x2a3a2a, hat: 0x3a3a3a, crown: 0.08, brim: 0.18, mustache: true, hair: 0x3a2a1a, belt: false });
pianist.root.position.set(7.15, 0.05, -2.8);
pianist.root.rotation.y = Math.PI / 2;
inn.add(pianist.root);
const bartender = makeHuman({ shirt: 0xf0ece0, vest: 0x1a1a1a, hat: null, apron: true, mustache: true, hair: 0x1a1210 });
bartender.root.position.set(-7.2, 0, -2.0);
bartender.root.rotation.y = Math.PI / 2;
inn.add(bartender.root);
const rag = sphere(0.07, mat(0xe8e0d0), 0, 0, 0, 8, 6);
inn.add(rag);
// interior stranger doubles (the same rig is moved between scenes)

// interior lighting
inn.add(new THREE.HemisphereLight(0xa08060, 0x2a1a10, 0.8));
const lamps = [];
for (const [x, z] of [[-3, -3], [3, 0], [-2, 3]]) {
  const l = new THREE.PointLight(0xffc488, 14, 14, 1.5);
  l.position.set(x, 3.6, z);
  inn.add(l);
  lamps.push(l);
  inn.add(cyl(0.01, 0.01, 1.2, mat(0x1a1a1a), 4, x, 4.25, z));
  inn.add(sphere(0.16, new THREE.MeshBasicMaterial({ color: 0xffd08a }), x, 3.6, z));
  inn.add(cyl(0.3, 0.12, 0.15, mat(0x3a2a1a, { m: 0.5 }), 10, x, 3.78, z));
}
const doorSpot = new THREE.SpotLight(0xffa060, 60, 30, 0.5, 0.45, 1.3);
doorSpot.position.set(0.5, 3.0, 11);
doorSpot.target.position.set(-0.6, 0, 0);
doorSpot.castShadow = true;
doorSpot.shadow.mapSize.set(2048, 2048);
doorSpot.shadow.bias = -0.0005;
inn.add(doorSpot, doorSpot.target);
const innDoors = { dl: batwing(), dr: batwing() };
innDoors.dl.position.set(0.85, 0, 7);
innDoors.dl.rotation.y = Math.PI;
innDoors.dr.position.set(-0.85, 0, 7);
innDoors.dr.rotation.y = Math.PI;
innDoors.dr.scale.x = -1;
inn.add(innDoors.dl, innDoors.dr);
const motes = makeDust(260, 0xffd8a8, 0.02);
inn.add(motes.pts);
inn.traverse((c) => {
  if (c.isMesh && c.castShadow === false && !(c.material instanceof THREE.MeshBasicMaterial) && c.material.type !== "ShaderMaterial") c.castShadow = c.receiveShadow = true;
});

// =========================================================== post-process
const rt = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: 4 });
const postScene = new THREE.Scene();
const postCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
const post = new THREE.ShaderMaterial({
  uniforms: { tex: { value: rt.texture }, time: { value: 0 }, exposure: { value: 1 }, warm: { value: 1 }, fade: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
  fragmentShader: `
    precision highp float;
    varying vec2 vUv; uniform sampler2D tex; uniform float time, exposure, warm, fade;
    vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14), 0.0, 1.0); }
    float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)) + time*17.0)*43758.5453); }
    vec3 toSRGB(vec3 c){ return mix(c*12.92, 1.055*pow(c, vec3(1.0/2.4)) - 0.055, step(0.0031308, c)); }
    void main(){
      vec2 uv = vUv; vec2 cc = uv - 0.5;
      float ca = 0.0016 * dot(cc, cc) * 4.0;
      vec3 col;
      col.r = texture2D(tex, uv + cc*ca).r;
      col.g = texture2D(tex, uv).g;
      col.b = texture2D(tex, uv - cc*ca).b;
      // cheap bloom from bright neighbours
      col *= exposure;
      col = aces(col);
      // warm western grade: amber highlights, teal-ish lifted shadows
      float l = dot(col, vec3(0.299,0.587,0.114));
      col = mix(col, col * vec3(1.05, 0.99, 0.9), warm * 0.6);
      col += vec3(0.02, 0.012, 0.0) * (1.0 - l);
      col = mix(vec3(l), col, 1.1);
      col = (col - 0.5) * 1.06 + 0.5;
      col = toSRGB(col);
      col *= 1.0 - smoothstep(0.35, 0.95, length(cc * vec2(1.25, 1.0))) * 0.55;
      col += (hash(uv * vec2(1920.0,1080.0)) - 0.5) * 0.045;
      col *= 1.0 - fade;
      gl_FragColor = vec4(col, 1.0);
    }`,
});
postScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), post));

const camera = new THREE.PerspectiveCamera(35, W / H, 0.05, 1500);

// ================================================================ SHOTS
const FPS = 30;
const SHOTS = [
  ["title", 0.0, 3.0],
  ["street", 3.0, 5.0],
  ["rider", 5.0, 7.75],
  ["tie", 7.75, 10.3],
  ["brush", 10.3, 11.6],
  ["doors", 11.6, 13.6],
  ["room", 13.6, 14.55],
  ["pianist", 14.55, 15.7],
  ["doorway", 15.7, 17.6],
  ["faces", 17.6, 19.5],
  ["finale", 19.5, 24.0],
];
const shotAt = (t) => SHOTS.find(([, a, b]) => t >= a && t < b) ?? SHOTS[SHOTS.length - 1];

function placeSun(focus, extent) {
  sun.target.position.copy(focus);
  sun.position.copy(focus).addScaledVector(SUN_DIR, 160);
  const c = sun.shadow.camera;
  c.left = -extent;
  c.right = extent;
  c.top = extent;
  c.bottom = -extent;
  c.near = 1;
  c.far = 400;
  c.updateProjectionMatrix();
  sun.target.updateMatrixWorld();
}

function setCam(pos, look, fov = 35, roll = 0) {
  camera.position.copy(pos);
  camera.fov = fov;
  camera.updateProjectionMatrix();
  camera.up.set(Math.sin(roll), Math.cos(roll), 0);
  camera.lookAt(look);
}

// handheld micro-shake, deterministic
function shake(t, amt) {
  return V(Math.sin(t * 1.7) * 0.6 + Math.sin(t * 3.1 + 1) * 0.3, Math.sin(t * 2.3 + 2) * 0.5 + Math.sin(t * 4.7) * 0.2, Math.sin(t * 1.3 + 4) * 0.4).multiplyScalar(amt);
}

function riderMount(t, hx, hz, phase, amt) {
  // stranger seated in the saddle of `horse`
  horse.root.position.set(hx, 0, hz);
  horse.root.rotation.y = 0;
  horseGait(horse, phase, amt, t);
  rest(stranger);
  const sy = horse.body.position.y + 0.5 - 0.98 + 0.02;
  stranger.root.position.set(hx, sy, hz + 0.02);
  stranger.root.rotation.y = 0;
  stranger.hipL.rotation.set(-1.25, 0, -0.42);
  stranger.hipR.rotation.set(-1.25, 0, 0.42);
  stranger.knL.rotation.x = 1.35;
  stranger.knR.rotation.x = 1.35;
  stranger.shL.rotation.set(-0.55, 0, -0.12);
  stranger.shR.rotation.set(-0.7, 0, 0.12);
  stranger.elL.rotation.x = -0.75;
  stranger.elR.rotation.x = -0.6;
  stranger.spine.rotation.x = 0.06 + 0.03 * Math.sin(TAU * phase * 2);
  stranger.head.rotation.y = 0.18 * Math.sin(t * 0.6);
  stranger.root.updateMatrixWorld(true);
  horse.root.updateMatrixWorld(true);
  const a = new THREE.Vector3(), b = new THREE.Vector3();
  horse.bit.getWorldPosition(a);
  stranger.tipL.getWorldPosition(b);
  stick(rein, a, b);
  rein2.visible = false;
  rein.visible = true;
}

function folkWatch(t, target) {
  for (const f of folk) {
    rest(f.j);
    const p = f.j.root.position;
    const yaw = Math.atan2(target.x - p.x, target.z - p.z) - f.ry;
    const y = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    f.j.spine.rotation.y = clamp(y * 0.4, -0.7, 0.7);
    f.j.head.rotation.y = clamp(y * 0.6, -0.9, 0.9);
    f.j.shL.rotation.x = -0.05;
    f.j.head.rotation.x = 0.05 * Math.sin(t + p.z);
  }
}

function hoofDustAt(t, src, active) {
  // deterministic emitter: each particle has a birth slot on a looping 1.2 s cycle
  const { pos, alpha, seeds, n } = hoofDust;
  for (let i = 0; i < n; i++) {
    const s = seeds[i];
    const life = 1.2;
    const age = (t + s[3] * life) % life;
    const born = t - age;
    const o = src(born, s);
    if (!active || !o) {
      alpha[i] = 0;
      continue;
    }
    pos[i * 3] = o.x + s[0] * 0.3 + s[0] * age * 0.5;
    pos[i * 3 + 1] = 0.05 + age * 0.35 * (0.5 + s[4]);
    pos[i * 3 + 2] = o.z + s[2] * 0.3 - age * 0.6;
    alpha[i] = 0.22 * Math.sin(Math.PI * age / life);
  }
  hoofDust.geo.attributes.position.needsUpdate = true;
  hoofDust.geo.attributes.alpha.needsUpdate = true;
}

function coatDustAt(t, j, times) {
  const { pos, alpha, seeds, n } = coatDust;
  const per = Math.floor(n / times.length);
  j.root.updateMatrixWorld(true);
  const chest = new THREE.Vector3();
  j.spine.localToWorld(chest.set(0, 0.32, 0.12));
  const fwd = V(0, 0, 1).applyQuaternion(j.root.quaternion);
  for (let i = 0; i < n; i++) {
    const k = Math.min(times.length - 1, Math.floor(i / per));
    const s = seeds[i];
    const age = t - times[k] - s[3] * 0.12;
    if (age < 0 || age > 2.2) {
      alpha[i] = 0;
      continue;
    }
    const drag = 1 - Math.exp(-age * 2.2);
    const v = V(s[0] * 0.55, 0.15 + s[1] * 0.3, s[2] * 0.4).addScaledVector(fwd, 0.25);
    pos[i * 3] = chest.x + s[0] * 0.15 + v.x * drag + age * 0.12;
    pos[i * 3 + 1] = chest.y - 0.1 + s[1] * 0.25 + v.y * drag - age * 0.02;
    pos[i * 3 + 2] = chest.z + s[2] * 0.12 + v.z * drag;
    alpha[i] = 0.16 * Math.exp(-age * 1.2) * Math.min(1, age * 12);
  }
  coatDust.geo.attributes.position.needsUpdate = true;
  coatDust.geo.attributes.alpha.needsUpdate = true;
}

function hideDust() {
  coatDust.alpha.fill(0);
  hoofDust.alpha.fill(0);
  coatDust.geo.attributes.alpha.needsUpdate = true;
  hoofDust.geo.attributes.alpha.needsUpdate = true;
}

function rollWeed(tw, t, t0, from, to, r) {
  const u = (t - t0);
  const p = from.clone().lerp(to, clamp(u / 6));
  const dist = from.distanceTo(p);
  tw.position.set(p.x, r + Math.abs(Math.sin(u * 3.2)) * 0.35, p.z);
  const dir = to.clone().sub(from).normalize();
  tw.rotation.set(dist / r * dir.z, 0, -dist / r * dir.x);
}

// stranger standing / leading / tying / brushing / walking — exterior
function strangerOnFoot(t) {
  rest(stranger);
  stranger.root.rotation.y = Math.PI / 2; // facing +x (toward the saloon)
  rein.visible = true;
  rein2.visible = false;
}

function swingDoors(t) {
  // pushed open at 12.5, swing back with damped oscillation
  if (t < 12.5) return 0;
  const u = t - 12.5;
  const open = 1.25 * ease(u / 0.25);
  if (u < 0.45) return open;
  const v = u - 0.45;
  return 1.25 * Math.exp(-v * 1.6) * Math.cos(v * 5.2);
}

function setPatrons(t, look) {
  // patrons playing cards until the piano stops, then turn to the door
  const turnT = 14.62;
  for (const p of patrons) {
    rest(p.j);
    sit(p.j);
    const base = p.j.root.position;
    const yawTo = Math.atan2(0 - base.x, 7 - base.z) - p.j.root.rotation.y;
    const yt = Math.atan2(Math.sin(yawTo), Math.cos(yawTo));
    const u = ease((t - turnT - p.delay) / 0.55);
    p.j.spine.rotation.y = clamp(yt * 0.45, -0.8, 0.8) * u;
    p.j.head.rotation.y = clamp(yt * 0.55, -1.0, 1.0) * u + (1 - u) * (0.2 * Math.sin(t * 1.3 + p.delay * 9));
    p.j.head.rotation.x = (1 - u) * 0.25 + u * -0.04;
    // card hands
    p.j.shL.rotation.x = -0.9 + 0.3 * u;
    p.j.shR.rotation.x = -0.75 + (1 - u) * 0.08 * Math.sin(t * 3 + p.delay * 20);
    p.j.elL.rotation.x = -0.8;
    p.j.elR.rotation.x = -0.6 - 0.4 * u * (p.side > 0 ? 1 : 0);
    p.j.shR.rotation.z = 0.2;
    p.j.shL.rotation.z = -0.2;
  }
  // bartender wiping a glass, freezes
  rest(bartender);
  const bu = ease((t - 14.7) / 0.5);
  const wipe = (1 - bu) * Math.sin(t * 9);
  bartender.shR.rotation.set(-1.1, 0, 0.3 + 0.15 * wipe);
  bartender.elR.rotation.x = -0.9 - 0.2 * wipe;
  bartender.shL.rotation.set(-1.0, 0, -0.35);
  bartender.elL.rotation.x = -1.0;
  bartender.head.rotation.x = 0.35 * (1 - bu);
  bartender.head.rotation.y = bu * 0.9;
  bartender.spine.rotation.y = bu * 0.25;
  bartender.root.updateMatrixWorld(true);
  bartender.tipR.getWorldPosition(rag.position);
  // pianist
  rest(pianist);
  sit(pianist);
  pianist.hips.position.y = 0.55;
  const stop = 14.58;
  const playing = t < stop;
  const lift = ease((t - stop) / 0.2);
  const bounceL = playing ? Math.max(0, Math.sin(t * 13.8)) : 0;
  const bounceR = playing ? Math.max(0, Math.sin(t * 27.6 + 1)) : 0;
  pianist.shL.rotation.set(-1.05 + 0.08 * bounceL - 0.25 * lift, 0, -0.1);
  pianist.shR.rotation.set(-1.05 + 0.06 * bounceR - 0.25 * lift, 0, 0.1);
  pianist.elL.rotation.x = -0.55 - 0.1 * bounceL + 0.15 * lift;
  pianist.elR.rotation.x = -0.55 - 0.1 * bounceR + 0.15 * lift;
  pianist.spine.rotation.x = playing ? 0.05 * Math.sin(t * 6.9) : 0;
  const tu = ease((t - stop - 0.25) / 0.6);
  pianist.spine.rotation.y = -tu * 0.35;
  pianist.head.rotation.y = -tu * 1.05;
  pianist.head.rotation.x = playing ? 0.12 * Math.sin(t * 6.9) : 0;
}

function renderAt(timeValue) {
  const t = Math.max(0, Number(timeValue) || 0);
  const [shot, s0, s1] = shotAt(t);
  const st = t - s0;
  let scene = ext;
  let exposure = 1.0;
  let fade = 0;
  skyMat.uniforms.dusk.value = 0;
  sun.intensity = 3.4;
  hemi.intensity = 1.05;
  tw1.visible = tw2.visible = false;
  hideDust();
  // doors default closed
  saloonDoors.dl.rotation.y = 0;
  saloonDoors.dr.rotation.y = 0;
  horseIdle(horse2, t + 3);
  folkWatch(t, V(1.5, 1.6, -40));

  if (shot === "title") {
    // rider emerges from the sun on the trail toward town
    const z = -168 + t * 1.7;
    const phase = t / 1.15;
    riderMount(t, 0.6, z, phase, 1);
    hoofDustAt(t, (b) => V(0.6, 0, -168 + b * 1.7), true);
    const c = kv(t, [[0, [-3.2, 0.9, -146]], [3, [-2.6, 1.15, -148.5]]]);
    setCam(c.add(shake(t, 0.02)), V(0.4, 2.3, z - 4), 30, 0.01);
    placeSun(V(0, 0, z), 30);
    exposure = 0.95;
    fade = 1 - ease(t / 1.2);
  } else if (shot === "street") {
    const z = -64 + st * 1.9;
    riderMount(t, 1.2, z, t / 1.15, 1);
    hoofDustAt(t, (b) => V(1.2, 0, -64 + (b - s0) * 1.9), true);
    folkWatch(t, V(1.2, 2, z));
    const c = kv(st, [[0, [-3.8, 15, 14]], [2.0, [-3.2, 8.5, 8]]]);
    setCam(c, V(0.8, 3.0 - st * 0.3, -46), 34);
    placeSun(V(0, 0, -25), 60);
    tw1.visible = true;
    rollWeed(tw1, t, 2.6, V(-11, 0, -20), V(13, 0, -27), 0.55);
  } else if (shot === "rider") {
    const z = -15 + st * 2.0;
    riderMount(t, 3.0, z, t / 1.15, 1);
    hoofDustAt(t, (b) => V(3.0, 0, -15 + (b - s0) * 2.0), true);
    folkWatch(t, V(3, 2, z));
    // low dolly in front of the horse, tilting up to the silhouette
    const camZ = z + 5.2;
    const c = V(0.6 + st * 0.15, 0.45 + st * 0.25, camZ).add(shake(t, 0.025));
    const look = V(2.7, lerp(1.4, 2.55, ease(st / 2.4)), z - 0.2);
    setCam(c, look, lerp(42, 30, ease(st / 2.7)));
    placeSun(V(3, 0, z), 18);
    tw2.visible = true;
    rollWeed(tw2, t, 5.0, V(-12, 0, -7), V(10, 0, -12), 0.45);
  } else if (shot === "tie") {
    // leads the horse to the rail and ties the reins (rail world x=8.55, z -4.8..-1.2)
    const arrive = ease((t - 7.75) / 0.9);
    const hx = lerp(4.0, 6.3, arrive);
    horse.root.position.set(hx, 0, -3.3);
    horse.root.rotation.y = Math.PI / 2;
    if (t < 8.65) horseGait(horse, t / 1.4, 1 - arrive * 0.8, t);
    else horseIdle(horse, t);
    if (t > 8.7 && t < 9.2) horse.head.rotation.x = -0.25 * Math.sin((t - 8.7) / 0.5 * Math.PI); // snort toss
    horse.root.updateMatrixWorld(true);
    rest(stranger);
    stranger.root.rotation.y = Math.PI / 2;
    const sx = lerp(5.2, 7.75, arrive);
    stranger.root.position.set(sx, 0, -2.25);
    if (t < 8.65) walk(stranger, 0.25 + (t - 7.75) / 0.8, 1 - arrive * 0.6);
    // tying: both hands at the rail, looping motion
    const tie = seg(t, 8.9, 9.95);
    const loop = Math.sin(tie * TAU * 2.5);
    const reach = ease((t - 8.6) / 0.3) * (1 - ease((t - 10.0) / 0.25));
    stranger.shR.rotation.x = lerp(-0.1, -1.0 + 0.15 * loop, reach);
    stranger.shR.rotation.z = lerp(0.08, -0.35, reach);
    stranger.elR.rotation.x = lerp(-0.12, -0.5 - 0.25 * loop, reach);
    stranger.shL.rotation.x = lerp(-0.1, -0.95 - 0.12 * loop, reach);
    stranger.shL.rotation.z = lerp(-0.08, 0.3, reach);
    stranger.elL.rotation.x = lerp(-0.12, -0.6 + 0.2 * loop, reach);
    stranger.spine.rotation.x = 0.18 * reach;
    stranger.head.rotation.x = 0.3 * reach;
    stranger.head.rotation.y = -0.2 * reach;
    stranger.root.updateMatrixWorld(true);
    const a = new THREE.Vector3(), b = new THREE.Vector3();
    horse.bit.getWorldPosition(a);
    stranger.tipR.getWorldPosition(b);
    if (t > 9.95) b.set(8.55, 1.05, -2.6);
    stick(rein, a, b);
    rein.visible = true;
    rein2.visible = false;
    const c = kv(st, [[0, [4.4, 1.25, 2.6]], [2.55, [5.1, 1.35, 1.0]]]).add(shake(t, 0.012));
    setCam(c, V(7.6, 1.35, -2.8), 36);
    placeSun(V(7, 0, -2), 14);
  } else if (shot === "brush" || shot === "doors") {
    // horse tied at the rail
    horse.root.position.set(6.3, 0, -3.3);
    horse.root.rotation.y = Math.PI / 2;
    horseIdle(horse, t);
    if (t > 11.2 && t < 11.7) horse.head.rotation.x = 0.08 - 0.2 * Math.sin((t - 11.2) / 0.5 * Math.PI);
    horse.root.updateMatrixWorld(true);
    const a = new THREE.Vector3();
    horse.bit.getWorldPosition(a);
    stick(rein, a, V(8.55, 1.05, -2.6));
    rein.visible = true;
    rein2.visible = false;
    rest(stranger);
    stranger.root.rotation.y = Math.PI / 2;
    if (shot === "brush") {
      stranger.root.position.set(9.7, 0.25, -0.55);
      stranger.root.rotation.y = Math.PI / 2 + 0.3;
      // three downward swipes across the coat
      const swipes = [10.4, 10.78, 11.15];
      let sw = 0;
      for (const s of swipes) sw = Math.max(sw, Math.sin(Math.PI * clamp((t - s + 0.08) / 0.3)));
      const k = swipes.findIndex((s) => t < s + 0.22);
      const right = k !== 1;
      const ph = swipes.reduce((acc, s) => (t > s - 0.08 && t < s + 0.22 ? clamp((t - s + 0.08) / 0.3) : acc), 0);
      if (right) {
        stranger.shR.rotation.set(lerp(-1.2, -0.35, ph), 0, lerp(-0.6, -0.15, ph) * (sw > 0 ? 1 : 0.3));
        stranger.elR.rotation.x = lerp(-1.3, -0.4, ph);
        stranger.shL.rotation.x = -0.1;
      } else {
        stranger.shL.rotation.set(lerp(-1.2, -0.35, ph), 0, lerp(0.6, 0.15, ph));
        stranger.elL.rotation.x = lerp(-1.3, -0.4, ph);
      }
      stranger.head.rotation.x = 0.32;
      stranger.head.rotation.y = right ? -0.25 : 0.25;
      stranger.spine.rotation.x = 0.1;
      coatDustAt(t, stranger, swipes);
      const c = kv(st, [[0, [11.75, 1.55, 0.75]], [1.3, [11.6, 1.6, 0.55]]]).add(shake(t, 0.008));
      setCam(c, V(9.7, 1.82, -0.55), 40);
      placeSun(V(10, 0, -1), 10);
    } else {
      // walk to the batwing doors and push through
      const u = seg(t, 11.6, 13.3);
      const p = V(lerp(9.7, 13.1, u), 0.25, lerp(-0.55, 0, ease(u * 1.6)));
      stranger.root.position.copy(p);
      stranger.root.rotation.y = Math.PI / 2 + 0.35 * (1 - ease(u * 2));
      walk(stranger, 0.25 + (t - 11.72) / 0.72, 1);
      const push = ease((t - 12.3) / 0.2) * (1 - ease((t - 12.9) / 0.3));
      stranger.shL.rotation.x = lerp(stranger.shL.rotation.x, -1.1, push);
      stranger.shR.rotation.x = lerp(stranger.shR.rotation.x, -1.1, push);
      stranger.shL.rotation.z = lerp(-0.08, -0.5, push);
      stranger.shR.rotation.z = lerp(0.08, 0.5, push);
      const sw = swingDoors(t);
      saloonDoors.dl.rotation.y = -sw;
      saloonDoors.dr.rotation.y = sw;
      coatDustAt(t, stranger, [10.4, 10.78, 11.15]);
      const c = kv(st, [[0, [6.2, 1.75, 1.3]], [2.0, [8.1, 1.65, 0.7]]]).add(shake(t, 0.015));
      setCam(c, V(12.4, 1.45, -0.1), 38);
      placeSun(V(10, 0, -1), 12);
    }
  } else if (shot === "finale") {
    skyMat.uniforms.dusk.value = ease(st / 4);
    sun.intensity = lerp(3.0, 1.6, ease(st / 4));
    hemi.intensity = lerp(1.0, 0.6, ease(st / 4));
    horse.root.position.set(6.3, 0, -3.3);
    horse.root.rotation.y = Math.PI / 2;
    horseIdle(horse, t);
    horse.root.updateMatrixWorld(true);
    const a = new THREE.Vector3();
    horse.bit.getWorldPosition(a);
    stick(rein, a, V(8.55, 1.05, -2.6));
    stranger.root.position.set(0, -50, 0);
    const sw = 0.08 * Math.sin(t * 2.2) * Math.exp(-st * 0.6);
    saloonDoors.dl.rotation.y = -sw;
    saloonDoors.dr.rotation.y = sw;
    for (const f of folk) rest(f.j);
    folkWatch(t, V(12, 1.6, 0));
    const c = kv(st, [[0, [1.2, 1.3, 7.5]], [4.5, [-2.5, 4.6, 17]]]);
    setCam(c, V(7.6, lerp(2.0, 3.2, ease(st / 4.5)), -2.6), 38);
    placeSun(V(4, 0, 0), 30);
    tw1.visible = true;
    rollWeed(tw1, t, 19.4, V(-12, 0, 4), V(12, 0, -2), 0.55);
    exposure = lerp(1.0, 0.62, ease(st / 3.5));
    fade = ease((t - 22.6) / 1.1);
  } else {
    // ======================= interior shots =======================
    scene = inn;
    exposure = 1.0;
    setPatrons(t);
    rest(stranger);
    inn.add(stranger.root);
    stranger.root.rotation.y = Math.PI; // facing into the room (-z)
    const sw = 0.9 * Math.exp(-(t - 13.35) * 1.4) * Math.cos((t - 13.35) * 5.2);
    const dsw = t > 13.35 ? sw : 0;
    innDoors.dl.rotation.y = Math.PI + dsw;
    innDoors.dr.rotation.y = Math.PI - dsw;
    // dust motes drifting in the shaft
    for (let i = 0; i < motes.n; i++) {
      const s = motes.seeds[i];
      motes.pos[i * 3] = s[0] * 2.4 - 0.4 + Math.sin(t * 0.3 + s[3] * 20) * 0.2;
      motes.pos[i * 3 + 1] = 0.3 + (s[1] + 1) * 1.6 + Math.sin(t * 0.25 + s[4] * 30) * 0.15;
      motes.pos[i * 3 + 2] = 6.8 - (s[2] + 1) * 3.2;
      motes.alpha[i] = 0.5 * (0.4 + 0.6 * Math.abs(Math.sin(t * 0.8 + s[3] * 40)));
    }
    motes.geo.attributes.position.needsUpdate = true;
    motes.geo.attributes.alpha.needsUpdate = true;
    if (shot === "room") {
      stranger.root.position.set(0, -50, 0);
      const c = kv(st, [[0, [-4.4, 3.1, 6.2]], [0.95, [-3.9, 2.95, 5.6]]]);
      setCam(c, V(3.2, 0.9, -3.4), 42);
    } else if (shot === "pianist") {
      stranger.root.position.set(0, -50, 0);
      const c = kv(st, [[0, [8.15, 1.5, -0.55]], [1.15, [8.05, 1.48, -0.75]]]);
      setCam(c, V(7.25, 1.3, -2.75), 36);
    } else if (shot === "doorway") {
      stranger.root.position.set(0, 0, 6.3);
      stranger.head.rotation.x = 0.06;
      stranger.shR.rotation.z = 0.15;
      stranger.shL.rotation.z = -0.15;
      stranger.head.rotation.y = 0.12 * ease(st / 1.8);
      const c = kv(st, [[0, [0.3, 1.35, -1.5]], [1.9, [0.2, 1.4, 1.0]]]).add(shake(t, 0.006));
      setCam(c, V(0.0, 1.45, 6.3), 32);
    } else if (shot === "faces") {
      const step = ease((t - 18.25) / 0.4);
      stranger.root.position.set(0.15, 0, 5.8 - 0.45 * step);
      if (t > 18.2 && t < 18.7) walk(stranger, 0.75 + (t - 18.2) * 0.9, 0.5);
      const c = kv(st, [[0, [0.75, 1.95, 6.95]], [1.9, [0.65, 1.9, 6.75]]]);
      setCam(c, V(-0.7, 1.3, 2.0), 48);
    }
  }
  if (scene === ext && stranger.root.parent !== ext) ext.add(stranger.root);
  if (scene === inn && shot !== "doorway" && shot !== "faces") {
    // nothing extra
  }
  post.uniforms.time.value = Math.floor(t * FPS) / FPS;
  post.uniforms.exposure.value = exposure;
  post.uniforms.fade.value = fade;
  renderer.setRenderTarget(rt);
  renderer.render(scene, camera);
  renderer.setRenderTarget(null);
  renderer.render(postScene, postCam);
}

window.addEventListener("hf-seek", (e) => renderAt(e.detail.time));
window.__filmRenderAt = renderAt;
renderAt(window.__hfThreeTime || 0);
window.__filmReady = true;
