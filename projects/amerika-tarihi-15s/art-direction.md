# Art direction — Amerika Tarihi (15 s)

**Design read:** a 15-second "poster parade" of American history — each beat is a
letterpress / WPA-style travel poster that comes alive.

- **Palette (3 inks on paper):** paper `#EFE3C8`, navy ink `#1C2B44`, brick red `#B5352A`,
  accent gold `#C9962E`. No gradients except sky washes; flat shapes, hard edges.
- **Type:** Abril Fatface for years (display), Playfair Display italic for captions,
  Oswald for stencil/technical moments (war, countdown). Turkish copy, latin-ext fonts.
- **Texture:** animated paper grain (feTurbulence) + soft vignette over everything.
- **Motion character:** poster-print physics — shapes slide in like screens being pulled,
  gentle bob for ships, hard cuts of impact (cannon, liftoff) synced to SFX.
- **Signature device:** the rolling year counter `1776 → 2026` — used only in the finale.
- **Transitions:** a navy ink band sweeps diagonally between scenes (on the whoosh).

## Scene inventory (each with a different primary subject)

| # | Time | Year | Subject | Composition |
|---|------|------|---------|-------------|
| 1 | 0.0–2.5 | 1492 | Three ships, striped sun, waves | wide landscape, horizon low |
| 2 | 2.5–5.0 | 1776 | Quill on parchment → Liberty Bell rings | centered object close-up |
| 3 | 5.0–7.5 | 1861–65 | Cannon on hill, smoke, red sky | left-weighted silhouette |
| 4 | 7.5–10.0 | 1869 | Steam train on transcontinental rail | horizontal parallax |
| 5 | 10.0–12.5 | 1969 | Countdown → rocket liftoff → Moon | vertical, night palette |
| 6 | 12.5–15.0 | 2026 | Flag assembles, fireworks, 250 years | full-bleed, counter |

## Audio (all synthesized procedurally — `assets/synth_audio.py`)
Original march in D major at 96 BPM (one bar per scene): string pad, horn melody, timpani,
military snare (war + rail), glockenspiel finale. SFX: waves + gulls, quill + bell, cannons,
train chuffs + whistle, countdown beeps + rocket rumble, fireworks, scene whooshes.
