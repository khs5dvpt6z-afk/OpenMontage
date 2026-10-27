import React from "react";
import {
  AbsoluteFill,
  Audio,
  Composition,
  Easing,
  Sequence,
  interpolate,
  random,
  registerRoot,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const W = 1920;
const H = 1080;
const FPS = 30;
const SCENE = 75; // 2.5 s per beat, one bar at 96 BPM

const C = {
  paper: "#EFE3C8",
  paperDark: "#E2D2AE",
  ink: "#1C2B44",
  inkDeep: "#111B2E",
  red: "#B5352A",
  gold: "#C9962E",
};

const fontCss = `
@font-face{font-family:'Abril';src:url(${staticFile("abril-ext.woff2")}) format('woff2');unicode-range:U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF;}
@font-face{font-family:'Abril';src:url(${staticFile("abril.woff2")}) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD;}
@font-face{font-family:'PF';font-style:italic;font-weight:600;src:url(${staticFile("pf-ext.woff2")}) format('woff2');unicode-range:U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF;}
@font-face{font-family:'PF';font-style:italic;font-weight:600;src:url(${staticFile("pf.woff2")}) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD;}
@font-face{font-family:'Osw';font-weight:500;src:url(${staticFile("osw-ext.woff2")}) format('woff2');unicode-range:U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF;}
@font-face{font-family:'Osw';font-weight:500;src:url(${staticFile("osw.woff2")}) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD;}
`;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0.22, 1, 0.36, 1);

// ------------------------------------------------------------ shared bits --

const Caption: React.FC<{
  year: string;
  text: string;
  color?: string;
  accent?: string;
  x?: number;
  y?: number;
  align?: "left" | "center" | "right";
  yearFont?: string;
  yearSize?: number;
}> = ({ year, text, color = C.ink, accent = C.red, x = 110, y = 110, align = "left", yearFont = "Abril", yearSize = 230 }) => {
  const f = useCurrentFrame();
  const inY = interpolate(f, [2, 16], [60, 0], { ...clamp, easing: ease });
  const op = interpolate(f, [2, 12], [0, 1], clamp);
  const capOp = interpolate(f, [10, 22], [0, 1], clamp);
  const rule = interpolate(f, [8, 26], [0, 1], { ...clamp, easing: ease });
  return (
    <div
      style={{
        position: "absolute",
        left: align === "center" ? 0 : x,
        right: align === "right" ? x : align === "center" ? 0 : undefined,
        top: y,
        textAlign: align,
        color,
      }}
    >
      <div
        style={{
          fontFamily: yearFont,
          fontSize: yearSize,
          lineHeight: 0.9,
          letterSpacing: yearFont === "Osw" ? 6 : -4,
          transform: `translateY(${inY}px)`,
          opacity: op,
        }}
      >
        {year}
      </div>
      <div
        style={{
          height: 8,
          background: accent,
          width: 420 * rule,
          margin: align === "center" ? "22px auto 18px" : align === "right" ? "22px 0 18px auto" : "22px 0 18px",
        }}
      />
      <div style={{ fontFamily: "PF", fontStyle: "italic", fontWeight: 600, fontSize: 58, opacity: capOp }}>{text}</div>
    </div>
  );
};

const Grain: React.FC = () => {
  const f = useCurrentFrame();
  const seed = Math.floor(f / 2) % 12;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "multiply", opacity: 0.38 }}>
      <svg width={W} height={H}>
        <filter id={`g${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={seed} />
          <feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.38  0 0 0 0 0.28  0 0 0 0.55 0" />
        </filter>
        <rect width={W} height={H} filter={`url(#g${seed})`} />
      </svg>
    </AbsoluteFill>
  );
};

const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{ pointerEvents: "none", background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(30,18,5,0.42) 100%)" }}
  />
);

// Diagonal ink band that sweeps across each scene boundary.
const InkWipe: React.FC<{ at: number }> = ({ at }) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [at - 7, at + 7], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  if (p <= 0 || p >= 1) return null;
  const x = interpolate(p, [0, 1], [-3200, W + 400]);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: x, top: -400, width: 2600, height: H + 800, background: C.ink, transform: "skewX(-18deg)" }} />
      <div style={{ position: "absolute", left: x + 2600, top: -400, width: 60, height: H + 800, background: C.red, transform: "skewX(-18deg)" }} />
      <div style={{ position: "absolute", left: x - 60, top: -400, width: 30, height: H + 800, background: C.gold, transform: "skewX(-18deg)" }} />
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------- scene 1 1492 --

const Ship: React.FC<{ x: number; y: number; s: number; phase: number }> = ({ x, y, s, phase }) => {
  const f = useCurrentFrame();
  const bob = Math.sin(f / 9 + phase) * 8;
  const rock = Math.sin(f / 11 + phase) * 3;
  return (
    <g transform={`translate(${x} ${y + bob}) rotate(${rock}) scale(${s})`}>
      <path d="M-140 0 L140 0 L105 48 L-110 48 Z" fill={C.ink} />
      <path d="M-150 -22 L-95 -22 L-95 2 L-140 2 Z" fill={C.ink} />
      <path d="M95 -14 L150 -14 L140 2 L95 2 Z" fill={C.ink} />
      <rect x={-4} y={-230} width={8} height={232} fill={C.ink} />
      <rect x={-84} y={-170} width={6} height={172} fill={C.ink} />
      <rect x={76} y={-150} width={6} height={152} fill={C.ink} />
      <path d="M-70 -215 Q0 -195 70 -215 L60 -110 Q0 -95 -60 -110 Z" fill={C.paper} stroke={C.ink} strokeWidth={6} />
      <path d="M-55 -95 Q0 -80 55 -95 L50 -20 Q0 -10 -50 -20 Z" fill={C.paper} stroke={C.ink} strokeWidth={6} />
      <path d="M-24 -170 L24 -170 L24 -130 L-24 -130 Z" fill={C.red} opacity={0.9} />
      <path d="M-120 -160 Q-80 -150 -50 -160 L-58 -60 Q-85 -55 -112 -60 Z" fill={C.paper} stroke={C.ink} strokeWidth={5} />
      <path d="M80 -140 L80 -40 L140 -40 Z" fill={C.paper} stroke={C.ink} strokeWidth={5} />
      <path d="M0 -232 L40 -244 L0 -256 Z" fill={C.red} />
    </g>
  );
};

const wavePath = (y: number, amp: number, len: number, shift: number) => {
  let d = `M -40 ${H + 40} L -40 ${y}`;
  for (let x = -40; x <= W + 40; x += 20) {
    d += ` L ${x} ${y + Math.sin((x + shift) / len) * amp}`;
  }
  return d + ` L ${W + 40} ${H + 40} Z`;
};

const Scene1492: React.FC = () => {
  const f = useCurrentFrame();
  const sunY = interpolate(f, [0, SCENE], [610, 560], clamp);
  const drift = interpolate(f, [0, SCENE], [-80, 120]);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <svg width={W} height={H}>
        <defs>
          <clipPath id="sunclip">
            <circle cx={1300} cy={sunY} r={300} />
          </clipPath>
        </defs>
        <g clipPath="url(#sunclip)">
          {Array.from({ length: 14 }).map((_, i) => (
            <rect key={i} x={950} y={sunY - 300 + i * 46} width={700} height={46 - Math.max(0, i - 4) * 3.2} fill={C.red} />
          ))}
        </g>
        {[0, 1, 2].map((i) => (
          <path key={i} d={`M ${720 + i * 70 + drift * 0.4} ${150 + i * 34} q 30 -18 60 0 q 30 -18 60 0`} stroke={C.ink} strokeWidth={5} fill="none" opacity={0.8} />
        ))}
        <path d={wavePath(720, 14, 90, f * 6)} fill={C.ink} opacity={0.35} />
        <Ship x={520 + drift} y={735} s={0.95} phase={0} />
        <Ship x={1020 + drift * 0.8} y={760} s={0.7} phase={1.7} />
        <Ship x={1520 + drift * 0.6} y={745} s={0.55} phase={3.1} />
        <path d={wavePath(790, 18, 110, -f * 8)} fill={C.ink} />
        <path d={wavePath(880, 14, 70, f * 10 + 200)} fill={C.inkDeep} />
        {Array.from({ length: 10 }).map((_, i) => {
          const x = ((i * 233 + f * 7) % (W + 200)) - 100;
          return <path key={i} d={`M ${x} ${830 + (i % 3) * 60} q 25 -14 50 0`} stroke={C.paper} strokeWidth={5} fill="none" opacity={0.6} />;
        })}
      </svg>
      <Caption year="1492" text="Okyanusun ötesinde Yeni Dünya" x={110} y={90} />
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------- scene 2 1776 --

const Scene1776: React.FC = () => {
  const f = useCurrentFrame();
  // quill writes 6 lines over frames 3..30; bell lands at ~42 (3.9 s)
  const lines = [0, 1, 2, 3, 4, 5];
  const writeP = (i: number) => interpolate(f, [3 + i * 3.8, 8 + i * 3.8], [0, 1], clamp);
  const curLine = Math.min(5, Math.max(0, Math.floor((f - 3) / 3.8)));
  const qx = 560 + 760 * writeP(curLine);
  const qy = 330 + curLine * 70;
  const bellIn = spring({ frame: f - 36, fps: FPS, config: { damping: 9, stiffness: 120 } });
  const swing = f > 40 ? Math.sin((f - 40) / 3.2) * 14 * Math.exp(-(f - 40) / 22) : -10;
  const ring = interpolate(f, [42, 70], [0, 1], clamp);
  const sheetOut = interpolate(f, [30, 42], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{ transform: `translate(${sheetOut * -300}px, ${sheetOut * 1200}px) rotate(${-3 - sheetOut * 25}deg)` }}>
        <div style={{ position: "absolute", left: 460, top: 120, width: 1000, height: 860, background: C.paper, boxShadow: "0 30px 60px rgba(0,0,0,0.45)" }} />
        <div style={{ position: "absolute", left: 460, top: 175, width: 1000, textAlign: "center", fontFamily: "Abril", fontSize: 64, color: C.ink }}>
          In Congress, July 4, 1776
        </div>
        <svg width={W} height={H} style={{ position: "absolute" }}>
          {lines.map((i) => {
            const len = 760 - (i === 5 ? 300 : (i * 37) % 120);
            let d = `M 560 ${330 + i * 70}`;
            for (let x = 0; x <= len; x += 12) d += ` L ${560 + x} ${330 + i * 70 + Math.sin(x / 7 + i) * 6 + Math.sin(x / 23) * 4}`;
            return (
              <path key={i} d={d} stroke={C.inkDeep} strokeWidth={5} fill="none" strokeLinecap="round" strokeDasharray={len * 1.6} strokeDashoffset={len * 1.6 * (1 - writeP(i))} />
            );
          })}
          <path d="M 1150 760 q 40 -60 80 0 q 40 60 80 -10 q 30 -40 50 10" stroke={C.inkDeep} strokeWidth={6} fill="none" strokeDasharray={400} strokeDashoffset={interpolate(f, [24, 30], [400, 0], clamp)} />
          {f < 32 && (
            <g transform={`translate(${f < 24 ? qx : 1300} ${f < 24 ? qy : 755}) rotate(-35)`}>
              <path d="M0 0 L8 -40 Q30 -200 120 -330 Q70 -180 30 -40 Z" fill={C.paper} stroke={C.ink} strokeWidth={5} />
              <path d="M8 -40 L60 -260" stroke={C.ink} strokeWidth={3} />
            </g>
          )}
        </svg>
      </AbsoluteFill>
      {/* Liberty Bell */}
      <AbsoluteFill style={{ transform: `translate(-220px, ${(1 - bellIn) * -900}px)` }}>
        <svg width={W} height={H}>
          {[0, 1, 2].map((k) => {
            const r = interpolate(ring, [0, 1], [180, 620]) - k * 120;
            return r > 160 ? <circle key={k} cx={960} cy={560} r={r} fill="none" stroke={C.gold} strokeWidth={10} opacity={(1 - ring) * 0.9} /> : null;
          })}
          <rect x={780} y={120} width={360} height={46} fill={C.gold} />
          <g transform={`rotate(${swing} 960 160)`}>
            <rect x={940} y={160} width={40} height={60} fill={C.inkDeep} />
            <path d="M 960 210 C 870 210 850 280 845 380 C 840 480 820 560 760 640 L 1160 640 C 1100 560 1080 480 1075 380 C 1070 280 1050 210 960 210 Z" fill={C.gold} stroke={C.inkDeep} strokeWidth={8} />
            <rect x={772} y={622} width={376} height={26} rx={10} fill={C.gold} stroke={C.inkDeep} strokeWidth={8} />
            <path d="M 850 300 L 1070 300" stroke={C.inkDeep} strokeWidth={6} />
            <path d="M 990 500 L 1005 560 L 995 600" stroke={C.inkDeep} strokeWidth={6} fill="none" />
            <circle cx={960 + swing * -2} cy={668} r={22} fill={C.inkDeep} />
          </g>
        </svg>
      </AbsoluteFill>
      <Sequence from={42} layout="none">
        <Caption year="1776" text="Bağımsızlık ilan edildi" color={C.paper} accent={C.red} align="right" x={110} y={640} yearSize={200} />
      </Sequence>
    </AbsoluteFill>
  );
};

// -------------------------------------------------------- scene 3 1861-65 --

const Smoke: React.FC<{ start: number; x: number; y: number }> = ({ start, x, y }) => {
  const f = useCurrentFrame();
  const t = f - start;
  if (t < 0) return null;
  return (
    <g>
      {t < 4 && <circle cx={x} cy={y} r={60 + t * 50} fill={C.gold} opacity={1 - t / 4} />}
      {Array.from({ length: 9 }).map((_, i) => {
        const a = random(`a${start}${i}`) * 0.9 - 0.2;
        const sp = 9 + random(`s${start}${i}`) * 10;
        const r = 30 + t * (2.4 + random(`r${start}${i}`) * 2);
        return (
          <circle
            key={i}
            cx={x + Math.cos(a) * t * sp}
            cy={y - Math.sin(a) * t * sp * 0.5 - t * 1.5}
            r={r}
            fill={C.paper}
            opacity={interpolate(t, [0, 50], [0.95, 0], clamp)}
          />
        );
      })}
    </g>
  );
};

const Scene1861: React.FC = () => {
  const f = useCurrentFrame();
  const shots = [13, 46];
  const recoil = shots.reduce((acc, s) => acc + (f >= s ? Math.exp(-(f - s) / 4) * 26 : 0), 0);
  const shake = shots.reduce((acc, s) => acc + (f >= s && f < s + 8 ? (random(`k${f}`) - 0.5) * 22 * (1 - (f - s) / 8) : 0), 0);
  return (
    <AbsoluteFill style={{ background: C.red, transform: `translate(${shake}px, ${shake * 0.6}px)` }}>
      <svg width={W} height={H}>
        {Array.from({ length: 13 }).map((_, i) => (
          <rect key={i} x={0} y={i * (H / 13)} width={W} height={H / 26} fill={C.inkDeep} opacity={0.12} />
        ))}
        <path d={`M -50 ${H} L -50 760 Q 400 600 900 760 T 2000 720 L 2000 ${H} Z`} fill={C.ink} />
        {/* cannon */}
        <g transform={`translate(${470 - recoil} 690)`}>
          <g transform="rotate(-14)">
            <rect x={-40} y={-44} width={400} height={74} rx={28} fill={C.inkDeep} />
            <rect x={340} y={-52} width={34} height={90} rx={8} fill={C.inkDeep} />
            <circle cx={-40} cy={-7} r={44} fill={C.inkDeep} />
          </g>
          <circle cx={30} cy={60} r={78} fill="none" stroke={C.inkDeep} strokeWidth={20} />
          {[0, 1, 2, 3, 4, 5].map((k) => (
            <rect key={k} x={26} y={-14} width={8} height={148} fill={C.inkDeep} transform={`rotate(${k * 30} 30 60)`} />
          ))}
          <path d="M -60 70 L -240 140 L -230 160 L -40 100 Z" fill={C.inkDeep} />
        </g>
        <Smoke start={shots[0]} x={850} y={570} />
        <Smoke start={shots[1]} x={850} y={570} />
        {/* soldiers silhouetted on far ridge */}
        {Array.from({ length: 11 }).map((_, i) => {
          const x = 1150 + i * 64;
          const y = 745 - Math.sin((x - 900) / 300) * 20;
          return (
            <g key={i} transform={`translate(${x} ${y})`}>
              <circle cx={0} cy={-58} r={11} fill={C.inkDeep} />
              <rect x={-9} y={-48} width={18} height={48} fill={C.inkDeep} />
              <rect x={10} y={-90} width={4} height={60} fill={C.inkDeep} />
            </g>
          );
        })}
        {f > 20 && (
          <g transform={`translate(1500 ${interpolate(f, [20, 40], [745, 560], { ...clamp, easing: ease })})`}>
            <rect x={-4} y={0} width={8} height={200} fill={C.inkDeep} />
            <rect x={4} y={0} width={150} height={92} fill={C.paper} />
            <rect x={4} y={0} width={64} height={50} fill={C.ink} />
            {[1, 3, 5].map((k) => (
              <rect key={k} x={68} y={k * 7.7} width={86} height={7.7} fill={C.red} />
            ))}
            {[7, 9, 11].map((k) => (
              <rect key={k} x={4} y={k * 7.7} width={150} height={7.7} fill={C.red} />
            ))}
          </g>
        )}
      </svg>
      <Caption year="1861–1865" text="İç Savaş · Birlik korundu, kölelik kaldırıldı" color={C.paper} accent={C.gold} x={110} y={90} yearFont="Osw" yearSize={190} />
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------- scene 4 1869 --

const Scene1869: React.FC = () => {
  const f = useCurrentFrame();
  const trainX = interpolate(f, [0, SCENE], [-500, 1150], { easing: Easing.out(Easing.quad) });
  const scroll = f * 14;
  const whistle = f >= 25 && f < 52;
  return (
    <AbsoluteFill style={{ background: C.gold }}>
      <svg width={W} height={H}>
        <circle cx={1500} cy={300} r={150} fill={C.paper} opacity={0.85} />
        <path d={`M -100 700 L 200 420 L 380 560 L 640 300 L 900 620 L 1100 470 L 1350 640 L 1600 380 L 2000 700 Z`} fill={C.red} opacity={0.85} transform={`translate(${-scroll * 0.1} 0)`} />
        <path d={`M -100 760 L 300 560 L 600 700 L 1000 520 L 1400 720 L 1800 560 L 2200 760 Z`} fill={C.ink} opacity={0.55} transform={`translate(${-scroll * 0.25} 0)`} />
        <rect x={0} y={760} width={W} height={H - 760} fill={C.ink} />
        {Array.from({ length: 9 }).map((_, i) => {
          const x = ((i * 300 - scroll * 0.9) % (W + 300) + W + 300) % (W + 300) - 150;
          return (
            <g key={i}>
              <rect x={x} y={520} width={10} height={250} fill={C.inkDeep} />
              <rect x={x - 40} y={540} width={90} height={8} fill={C.inkDeep} />
            </g>
          );
        })}
        <path d={`M -10 548 ${Array.from({ length: 12 }).map((_, i) => `Q ${i * 175 + 87 - (scroll * 0.9) % 300} 580 ${i * 175 + 175 - (scroll * 0.9) % 300} 548`).join(" ")}`} stroke={C.inkDeep} strokeWidth={3} fill="none" />
        <rect x={0} y={826} width={W} height={10} fill={C.paper} opacity={0.8} />
        {Array.from({ length: 40 }).map((_, i) => (
          <rect key={i} x={((i * 60 - scroll) % W + W) % W} y={836} width={30} height={16} fill={C.paper} opacity={0.45} />
        ))}
        {/* steam */}
        {Array.from({ length: 14 }).map((_, i) => {
          const born = Math.floor(f / 3) * 3 - i * 3;
          if (born < 0) return null;
          const age = f - born;
          const bx = trainX + 300 - age * 22;
          return <circle key={i} cx={bx} cy={560 - age * 7} r={28 + age * 4} fill={C.paper} opacity={Math.max(0, 0.9 - age / 40)} />;
        })}
        {whistle && <circle cx={trainX + 360} cy={600} r={18 + (f - 25) * 3} fill="none" stroke={C.paper} strokeWidth={6} opacity={1 - (f - 25) / 27} />}
        <g transform={`translate(${trainX} 600)`}>
          {[-640, -360].map((cx) => (
            <g key={cx}>
              <rect x={cx} y={90} width={250} height={120} fill={C.red} stroke={C.inkDeep} strokeWidth={8} />
              <rect x={cx + 20} y={110} width={60} height={40} fill={C.paper} />
              <rect x={cx + 100} y={110} width={60} height={40} fill={C.paper} />
              <rect x={cx + 180} y={110} width={50} height={40} fill={C.paper} />
              <rect x={cx - 10} y={70} width={270} height={24} fill={C.inkDeep} />
              <rect x={cx + 250} y={180} width={30} height={10} fill={C.inkDeep} />
            </g>
          ))}
          <rect x={-90} y={60} width={150} height={160} fill={C.inkDeep} />
          <rect x={-70} y={80} width={60} height={50} fill={C.gold} />
          <rect x={60} y={110} width={290} height={110} rx={50} fill={C.inkDeep} />
          <rect x={280} y={30} width={44} height={90} fill={C.inkDeep} />
          <path d="M 260 30 L 344 30 L 330 0 L 274 0 Z" fill={C.inkDeep} />
          <rect x={180} y={80} width={34} height={34} rx={14} fill={C.gold} />
          <path d="M 350 200 L 420 238 L 350 238 Z" fill={C.red} />
          {[-40, 60, 170, 280, -590, -440, -310, -160].map((wx, k) => (
            <g key={k} transform={`translate(${wx} 222) rotate(${f * 18})`}>
              <circle r={k < 4 ? 36 : 26} fill={C.paper} stroke={C.inkDeep} strokeWidth={10} />
              <rect x={-3} y={k < 4 ? -34 : -24} width={6} height={k < 4 ? 68 : 48} fill={C.inkDeep} />
            </g>
          ))}
          <rect x={-40} y={218} width={330} height={10} fill={C.gold} transform={`translate(0 ${Math.sin(f * 0.31) * 10})`} />
        </g>
      </svg>
      <Caption year="1869" text="Demiryolu kıtayı birleştirdi" color={C.inkDeep} accent={C.red} x={110} y={80} />
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------- scene 5 1969 --

const Scene1969: React.FC = () => {
  const f = useCurrentFrame();
  const lift = f >= 30 ? Math.pow((f - 30) / 45, 2) : 0;
  const rocketY = interpolate(lift, [0, 1], [0, -560]);
  const rocketX = interpolate(lift, [0, 1], [0, 640]);
  const tilt = interpolate(lift, [0, 1], [0, 40]);
  const rScale = interpolate(lift, [0, 1], [1, 0.32]);
  const camShake = f >= 30 && f < 60 ? (random(`c${f}`) - 0.5) * 12 : 0;
  const count = f < 3 ? null : f < 12 ? "3" : f < 21 ? "2" : f < 30 ? "1" : null;
  const countP = f < 30 ? ((f - 3) % 9) / 9 : 0;
  return (
    <AbsoluteFill style={{ background: C.inkDeep, transform: `translate(${camShake}px, 0)` }}>
      <svg width={W} height={H}>
        {Array.from({ length: 90 }).map((_, i) => (
          <circle key={i} cx={random(`x${i}`) * W} cy={random(`y${i}`) * 700} r={1.5 + random(`r${i}`) * 3} fill={C.paper} opacity={0.4 + 0.6 * Math.abs(Math.sin(f / 8 + i))} />
        ))}
        <g transform={`translate(1560 300) scale(${interpolate(f, [0, SCENE], [1, 1.12])})`}>
          <circle r={170} fill={C.paper} />
          <circle cx={-50} cy={-40} r={34} fill={C.paperDark} />
          <circle cx={60} cy={30} r={46} fill={C.paperDark} />
          <circle cx={-20} cy={80} r={22} fill={C.paperDark} />
          {f > 62 && (
            <g transform="translate(40 -150)">
              <rect x={0} y={-60} width={4} height={60} fill={C.red} />
              <rect x={4} y={-60} width={34} height={22} fill={C.red} />
            </g>
          )}
        </g>
        {/* launch tower */}
        <g opacity={interpolate(f, [30, 60], [1, 0.9])}>
          <rect x={560} y={330} width={44} height={600} fill="none" stroke={C.ink} strokeWidth={8} />
          {Array.from({ length: 12 }).map((_, i) => (
            <path key={i} d={`M 560 ${330 + i * 50} L 604 ${380 + i * 50}`} stroke={C.ink} strokeWidth={5} />
          ))}
        </g>
        <rect x={0} y={920} width={W} height={160} fill={C.ink} />
        <g transform={`translate(${730 + rocketX} ${925 + rocketY}) rotate(${tilt}) scale(${rScale})`}>
          {f >= 26 && (
            <g>
              <path d={`M -40 0 Q 0 ${220 + Math.sin(f) * 40} 40 0 Z`} fill={C.gold} />
              <path d={`M -22 0 Q 0 ${120 + Math.cos(f) * 30} 22 0 Z`} fill={C.paper} />
            </g>
          )}
          <path d="M -50 0 L -50 -400 L 50 -400 L 50 0 Z" fill={C.paper} stroke={C.ink} strokeWidth={6} />
          <rect x={-50} y={-120} width={100} height={30} fill={C.ink} />
          <rect x={-50} y={-280} width={100} height={20} fill={C.ink} />
          <path d="M -40 -400 L -28 -480 L 28 -480 L 40 -400 Z" fill={C.paper} stroke={C.ink} strokeWidth={6} />
          <path d="M -16 -480 L 0 -560 L 16 -480 Z" fill={C.red} />
          <path d="M -50 0 L -90 30 L -50 -60 Z" fill={C.red} />
          <path d="M 50 0 L 90 30 L 50 -60 Z" fill={C.red} />
          <text x={-12} y={-180} fill={C.ink} fontFamily="Osw" fontSize={40} transform="rotate(90 -12 -180)">USA</text>
        </g>
        {f >= 28 &&
          Array.from({ length: 16 }).map((_, i) => {
            const age = f - 28;
            const dir = i % 2 === 0 ? -1 : 1;
            const spread = (i / 2 + 1) * age * 4.5;
            return <circle key={i} cx={730 + dir * spread} cy={930 - (i % 3) * 20} r={40 + age * 2.2} fill={C.paper} opacity={interpolate(age, [0, 45], [0.95, 0.15], clamp)} />;
          })}
      </svg>
      {count && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 300, textAlign: "center", fontFamily: "Osw", fontSize: 380, color: C.gold, opacity: 1 - countP, transform: `scale(${1 + countP * 0.4})` }}>
          {count}
        </div>
      )}
      <Sequence from={30} layout="none">
        <Caption year="1969" text="İnsanlık Ay’a ayak bastı" color={C.paper} accent={C.gold} x={110} y={90} />
      </Sequence>
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------- scene 6 2026 --

const Star: React.FC<{ x: number; y: number; r: number; fill: string; rot?: number }> = ({ x, y, r, fill, rot = 0 }) => {
  const pts = Array.from({ length: 10 })
    .map((_, i) => {
      const a = (Math.PI / 5) * i - Math.PI / 2 + rot;
      const rr = i % 2 === 0 ? r : r * 0.4;
      return `${x + Math.cos(a) * rr},${y + Math.sin(a) * rr}`;
    })
    .join(" ");
  return <polygon points={pts} fill={fill} />;
};

const Firework: React.FC<{ at: number; x: number; y: number; color: string }> = ({ at, x, y, color }) => {
  const f = useCurrentFrame();
  const t = f - at;
  if (t < 0 || t > 40) return null;
  const r = interpolate(t, [0, 18], [10, 230], { ...clamp, easing: Easing.out(Easing.cubic) });
  const op = interpolate(t, [10, 40], [1, 0], clamp);
  return (
    <g opacity={op}>
      {Array.from({ length: 18 }).map((_, i) => {
        const a = (Math.PI * 2 * i) / 18;
        return (
          <line key={i} x1={x + Math.cos(a) * r * 0.55} y1={y + Math.sin(a) * r * 0.55 + t * 1.2} x2={x + Math.cos(a) * r} y2={y + Math.sin(a) * r + t * 1.5} stroke={color} strokeWidth={8} strokeLinecap="round" />
        );
      })}
      <circle cx={x} cy={y} r={interpolate(t, [0, 6], [30, 0], clamp)} fill={C.paper} />
    </g>
  );
};

const Scene2026: React.FC = () => {
  const f = useCurrentFrame();
  const fx = 300;
  const fy = 260;
  const fw = 1320;
  const fh = 700;
  const sh = fh / 13;
  const cw = fw * 0.4;
  const ch = sh * 7;
  const year = Math.round(interpolate(f, [8, 50], [1776, 2026], { ...clamp, easing: Easing.inOut(Easing.cubic) }));
  const wave = (x: number) => Math.sin(x / 160 - f / 5) * 14 * (x / fw);
  const flagOut = interpolate(f, [44, 60], [1, 0.42], { ...clamp, easing: ease });
  const titleOp = interpolate(f, [48, 60], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ background: C.inkDeep }}>
      <svg width={W} height={H}>
        <Firework at={7} x={300} y={240} color={C.red} />
        <Firework at={21} x={1600} y={200} color={C.gold} />
        <Firework at={33} x={960} y={160} color={C.paper} />
        <Firework at={45} x={1650} y={700} color={C.red} />
        <Firework at={45} x={270} y={720} color={C.gold} />
        <g transform={`translate(${960 * (1 - flagOut)} ${(fy + fh / 2) * (1 - flagOut) - 120 * (1 - flagOut)}) scale(${flagOut})`} opacity={interpolate(f, [52, 66], [1, 0.55], clamp)}>
          <g transform={`translate(${(960 - fx - fw / 2) * (1 - flagOut) * 0} 0)`}>
            {Array.from({ length: 13 }).map((_, i) => {
              const p = interpolate(f, [i * 1.6, i * 1.6 + 10], [0, 1], { ...clamp, easing: ease });
              let d = `M ${fx} ${fy + i * sh + wave(0)}`;
              for (let x = 0; x <= fw * p; x += 40) d += ` L ${fx + x} ${fy + i * sh + wave(x)}`;
              d += ` L ${fx + fw * p} ${fy + (i + 1) * sh + wave(fw * p)}`;
              for (let x = fw * p; x >= 0; x -= 40) d += ` L ${fx + x} ${fy + (i + 1) * sh + wave(x)}`;
              return <path key={i} d={d + " Z"} fill={i % 2 === 0 ? C.red : C.paper} />;
            })}
            <rect x={fx} y={fy + wave(0)} width={cw * interpolate(f, [12, 24], [0, 1], { ...clamp, easing: ease })} height={ch} fill={C.ink} />
            {Array.from({ length: 50 }).map((_, i) => {
              // 9 rows alternating 6 and 5 stars
              let row = 0;
              let idx = i;
              while (idx >= (row % 2 === 0 ? 6 : 5)) {
                idx -= row % 2 === 0 ? 6 : 5;
                row++;
              }
              const cols = row % 2 === 0 ? 6 : 5;
              const sx = fx + (cw / 12) * (cols === 6 ? 1 + idx * 2 : 2 + idx * 2);
              const sy = fy + (ch / 10) * (row + 1);
              const pop = spring({ frame: f - 20 - i * 0.45, fps: FPS, config: { damping: 10, stiffness: 200 } });
              return pop > 0.01 ? <Star key={i} x={sx} y={sy + wave(sx - fx)} r={17 * pop} fill={C.paper} rot={(1 - pop) * 2} /> : null;
            })}
          </g>
        </g>
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: interpolate(f, [44, 60], [380, 600], { ...clamp, easing: ease }), textAlign: "center", fontFamily: "Abril", fontSize: interpolate(f, [44, 60], [300, 230], clamp), color: C.paper, textShadow: `0 8px 0 ${C.red}`, opacity: interpolate(f, [4, 10], [0, 1], clamp) }}>
        {year}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 860, textAlign: "center", opacity: titleOp, transform: `translateY(${(1 - titleOp) * 30}px)` }}>
        <div style={{ fontFamily: "PF", fontStyle: "italic", fontWeight: 600, fontSize: 64, color: C.gold }}>Amerika Birleşik Devletleri · 250 yıl</div>
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ main --

const AmerikaTarihi: React.FC = () => {
  const scenes = [Scene1492, Scene1776, Scene1861, Scene1869, Scene1969, Scene2026];
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <style>{fontCss}</style>
      {scenes.map((S, i) => (
        <Sequence key={i} from={i * SCENE} durationInFrames={SCENE}>
          <S />
        </Sequence>
      ))}
      {[1, 2, 3, 4, 5].map((k) => (
        <InkWipe key={k} at={k * SCENE} />
      ))}
      <Grain />
      <Vignette />
      <Audio src={staticFile("mix.wav")} />
    </AbsoluteFill>
  );
};

const Root: React.FC = () => (
  <Composition id="AmerikaTarihi" component={AmerikaTarihi} durationInFrames={SCENE * 6} fps={FPS} width={W} height={H} />
);

registerRoot(Root);
