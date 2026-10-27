# The Stranger — procedural Old-West 3D short

A 24-second American Old-West 3D animated short built entirely from code around one
supplied narration clip (`assets/narration.mp3`, ElevenLabs "Grandpa" voice):

> "By sundown, the whole town knew a stranger had arrived. He tied his horse outside
> the saloon, brushed the dust from his coat, and stepped inside. The piano stopped.
> Nobody said a word."

Everything else is generated locally. There are no image, video, or music model calls.

| Layer | How it is made |
|---|---|
| 3D world | Three.js (`hyperframes/film.js`): procedural desert, mesas, cacti, a false-front main street (saloon, bank, sheriff…), saloon interior, canvas-generated wood/sand/sign textures, sky shader with sun and clouds |
| Characters | Primitive-built rigs for people (hips/spine/neck/head, shoulders/elbows, hips/knees, duster coat, hats) and a horse (4 two-segment legs, neck, head, tail), animated with walk/gait cycles and keyframed acting |
| Camera | 11 shots, each a pure function of time (crane, low dolly, over-the-shoulder, push-ins), with deterministic handheld micro-shake |
| Look | HalfFloat render target, then a post shader (ACES tone map, warm western grade, chromatic fringe, vignette, film grain, fades) plus 2.39:1 letterbox bars |
| Score | `sound/sound_design.py`: Karplus-Strong guitar, gliding whistle lead (spaghetti-western theme in E minor), timpani, tremolo drones |
| Diegetic music | Detuned honky-tonk ragtime piano that is muffled through the saloon walls, opens up when we cut inside, and stops dead on "The piano stopped." |
| Foley / SFX | Desert wind, hawk cry, hoof-falls, horse snorts, tack and rope, coat-brush swishes, boots and spurs on the boardwalk, batwing-door creaks and thuds, crowd murmur, glass clinks, a chair scrape, and a wall clock ticking in the silence |
| Mix | Narration ducks the music; convolution reverbs; loudness-normalised to -16 LUFS |

## Timeline

| t (s) | Shot | Narration |
|---|---|---|
| 0–3 | Title: a rider comes out of the setting sun | — |
| 3–5 | Crane down the main street | "By sundown, the whole town knew…" |
| 5–7.75 | Low dolly: the silhouette on horseback | "…a stranger had arrived." |
| 7.75–10.3 | Leads the horse to the rail and ties it | "He tied his horse outside the saloon," |
| 10.3–11.6 | Brushes dust from his coat | "brushed the dust from his coat," |
| 11.6–13.6 | Boardwalk, then through the batwing doors | "and stepped inside." |
| 13.6–15.7 | Saloon interior, then the pianist freezes | "The piano stopped." |
| 15.7–19.5 | Backlit in the doorway; every face turns to him | "Nobody said a word." |
| 19.5–24 | Dusk on the street, end title | — |

## Rebuild

```bash
# 1. score + SFX + mix  ->  <out>/soundtrack.wav (plus stems)
pip install numpy scipy
python3 sound/sound_design.py assets/narration.mp3 build/audio

# 2. HyperFrames workspace: vendor three + gsap locally (no CDN at render time)
mkdir -p hyperframes/vendor hyperframes/assets
npm i --prefix /tmp/stranger-npm three@0.181.2 gsap@3.14.2
cp /tmp/stranger-npm/node_modules/three/build/three.{module,core}.js hyperframes/vendor/
cp /tmp/stranger-npm/node_modules/gsap/dist/gsap.min.js hyperframes/vendor/
cp build/audio/soundtrack.wav hyperframes/assets/

# 3. check + render
cd hyperframes
npx hyperframes lint && npx hyperframes validate
npx hyperframes render --quality delivery --fps 30 --output the-stranger.mp4
```

Every frame is a function of HyperFrames time (`hf-seek`), so renders are deterministic.
With software WebGL (SwiftShader) a frame takes about 2–3 s per worker.
